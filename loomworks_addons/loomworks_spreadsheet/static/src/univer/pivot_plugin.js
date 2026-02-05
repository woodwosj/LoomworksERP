/** @odoo-module **/
/**
 * Pivot Plugin for Univer
 *
 * Extends Univer with pivot table functionality:
 * - Render pivot tables from Odoo data
 * - Expandable/collapsible rows
 * - Formatting and styling
 */

/**
 * PivotRenderer - Renders pivot table data into spreadsheet cells.
 */
export class PivotRenderer {
    constructor(univerWrapper) {
        this.univerWrapper = univerWrapper;
    }

    /**
     * Render a pivot table into the spreadsheet.
     * @param {Object} pivotData - Computed pivot data
     * @param {string} sheetId - Target sheet ID
     * @param {number} startRow - Start row (0-based)
     * @param {number} startCol - Start column (0-based)
     * @param {Object} options - Rendering options
     */
    render(pivotData, sheetId = "sheet1", startRow = 0, startCol = 0, options = {}) {
        if (!pivotData || pivotData.error) {
            console.error("Invalid pivot data:", pivotData?.error);
            return;
        }

        const {
            showTotals = true,
            showRowHeaders = true,
            showColumnHeaders = true,
            headerStyle = { bold: true, bgColor: "#f0f0f0" },
        } = options;

        const { rows, columns, measures, data, totals } = pivotData;

        let currentRow = startRow;
        let currentCol = startCol;

        // Render column headers
        if (showColumnHeaders && columns.values.length > 0) {
            // Leave space for row field labels
            const rowFieldCount = rows.fields.length;
            currentCol = startCol + rowFieldCount;

            // Column values header
            columns.values.forEach((colValue, colIdx) => {
                const label = Array.isArray(colValue) ? colValue.join(" / ") : colValue;
                this.setCellWithStyle(sheetId, currentRow, currentCol + colIdx, label, headerStyle);
            });

            // Total column header
            if (showTotals) {
                this.setCellWithStyle(
                    sheetId,
                    currentRow,
                    currentCol + columns.values.length,
                    "Total",
                    headerStyle
                );
            }

            currentRow++;
        }

        // Render measure headers (if multiple measures)
        if (measures.length > 1) {
            currentCol = startCol + rows.fields.length;
            columns.values.forEach((_, colIdx) => {
                measures.forEach((measure, measureIdx) => {
                    this.setCellWithStyle(
                        sheetId,
                        currentRow,
                        currentCol + colIdx * measures.length + measureIdx,
                        measure.label,
                        { ...headerStyle, fontSize: 10 }
                    );
                });
            });
            currentRow++;
        }

        // Render row field headers
        if (showRowHeaders) {
            rows.fields.forEach((field, idx) => {
                this.setCellWithStyle(
                    sheetId,
                    startRow,
                    startCol + idx,
                    this.formatFieldName(field),
                    headerStyle
                );
            });
        }

        // Render data rows
        rows.values.forEach((rowValue, rowIdx) => {
            currentCol = startCol;

            // Row labels
            if (Array.isArray(rowValue)) {
                rowValue.forEach((val, idx) => {
                    this.univerWrapper.setCellValue(sheetId, currentRow, currentCol + idx, val);
                });
                currentCol += rowValue.length;
            } else {
                this.univerWrapper.setCellValue(sheetId, currentRow, currentCol, rowValue);
                currentCol++;
            }

            // Data values
            columns.values.forEach((_, colIdx) => {
                const cellKey = `${rowIdx},${colIdx}`;
                const cellData = data[cellKey] || {};

                measures.forEach((measure, measureIdx) => {
                    const value = cellData[measure.field] || 0;
                    this.univerWrapper.setCellValue(
                        sheetId,
                        currentRow,
                        currentCol + colIdx * measures.length + measureIdx,
                        this.formatValue(value, measure)
                    );
                });
            });

            // Row total
            if (showTotals && totals?.row?.[rowIdx]) {
                measures.forEach((measure, measureIdx) => {
                    const totalValue = totals.row[rowIdx][measure.field] || 0;
                    this.setCellWithStyle(
                        sheetId,
                        currentRow,
                        currentCol + columns.values.length * measures.length + measureIdx,
                        this.formatValue(totalValue, measure),
                        { bold: true }
                    );
                });
            }

            currentRow++;
        });

        // Render column totals
        if (showTotals && totals?.column) {
            currentCol = startCol;

            // "Total" label
            this.setCellWithStyle(sheetId, currentRow, currentCol, "Total", headerStyle);
            currentCol += rows.fields.length;

            // Column total values
            Object.keys(totals.column).forEach((colIdx) => {
                measures.forEach((measure, measureIdx) => {
                    const totalValue = totals.column[colIdx][measure.field] || 0;
                    this.setCellWithStyle(
                        sheetId,
                        currentRow,
                        currentCol + parseInt(colIdx) * measures.length + measureIdx,
                        this.formatValue(totalValue, measure),
                        { bold: true }
                    );
                });
            });

            // Grand total
            if (totals?.grand) {
                measures.forEach((measure, measureIdx) => {
                    const grandTotal = totals.grand[measure.field] || 0;
                    this.setCellWithStyle(
                        sheetId,
                        currentRow,
                        currentCol + columns.values.length * measures.length + measureIdx,
                        this.formatValue(grandTotal, measure),
                        { bold: true, bgColor: "#e0e0e0" }
                    );
                });
            }
        }

        return {
            endRow: currentRow,
            endCol: currentCol + columns.values.length * measures.length + (showTotals ? 1 : 0),
        };
    }

    /**
     * Set cell value with styling.
     * @param {string} sheetId - Sheet ID
     * @param {number} row - Row index
     * @param {number} col - Column index
     * @param {*} value - Cell value
     * @param {Object} style - Style options
     */
    setCellWithStyle(sheetId, row, col, value, style = {}) {
        // Set value
        this.univerWrapper.setCellValue(sheetId, row, col, value);

        // Apply styling if Univer supports it
        // Note: Style application depends on Univer's command API
        if (style && this.univerWrapper.commandService) {
            try {
                const styleData = {};
                if (style.bold) styleData.bl = 1;
                if (style.bgColor) styleData.bg = { rgb: style.bgColor };
                if (style.fontSize) styleData.fs = style.fontSize;

                this.univerWrapper.commandService.executeCommand(
                    "sheet.command.set-style-command",
                    {
                        unitId: this.univerWrapper.workbook.getUnitId(),
                        subUnitId: sheetId,
                        range: {
                            startRow: row,
                            startColumn: col,
                            endRow: row,
                            endColumn: col,
                        },
                        style: styleData,
                    }
                );
            } catch (error) {
                // Style command may not be available
            }
        }
    }

    /**
     * Format a field name for display.
     * @param {string} fieldName - Technical field name
     * @returns {string} Formatted name
     */
    formatFieldName(fieldName) {
        return fieldName
            .replace(/_/g, " ")
            .replace(/\b\w/g, char => char.toUpperCase());
    }

    /**
     * Format a value based on measure configuration.
     * @param {*} value - Raw value
     * @param {Object} measure - Measure definition
     * @returns {string|number} Formatted value
     */
    formatValue(value, measure) {
        if (value === null || value === undefined) {
            return "";
        }

        const formatType = measure.format_type || "number";
        const decimals = measure.decimal_places ?? 2;

        switch (formatType) {
            case "currency":
                return new Intl.NumberFormat(undefined, {
                    style: "currency",
                    currency: "USD",
                    minimumFractionDigits: decimals,
                    maximumFractionDigits: decimals,
                }).format(value);

            case "percentage":
                return new Intl.NumberFormat(undefined, {
                    style: "percent",
                    minimumFractionDigits: decimals,
                    maximumFractionDigits: decimals,
                }).format(value / 100);

            case "number":
            default:
                if (Number.isInteger(value)) {
                    return value;
                }
                return parseFloat(value.toFixed(decimals));
        }
    }
}

/**
 * PivotTableManager - Manages pivot tables in a spreadsheet.
 */
export class PivotTableManager {
    constructor(univerWrapper, spreadsheetService) {
        this.univerWrapper = univerWrapper;
        this.spreadsheetService = spreadsheetService;
        this.renderer = new PivotRenderer(univerWrapper);
        this.pivots = new Map();
    }

    /**
     * Add a pivot table to the spreadsheet.
     * @param {number} pivotId - Odoo pivot ID
     * @param {string} sheetId - Target sheet ID
     * @param {number} startRow - Start row
     * @param {number} startCol - Start column
     * @param {Object} options - Rendering options
     */
    async addPivot(pivotId, sheetId, startRow, startCol, options = {}) {
        try {
            const pivotData = await this.spreadsheetService.computePivot(pivotId);

            if (pivotData.error) {
                console.error("Pivot computation error:", pivotData.error);
                return null;
            }

            const bounds = this.renderer.render(
                pivotData,
                sheetId,
                startRow,
                startCol,
                options
            );

            const pivotInfo = {
                pivotId,
                sheetId,
                startRow,
                startCol,
                bounds,
                options,
            };

            this.pivots.set(pivotId, pivotInfo);
            return pivotInfo;
        } catch (error) {
            console.error("Failed to add pivot:", error);
            return null;
        }
    }

    /**
     * Refresh a pivot table.
     * @param {number} pivotId - Pivot ID
     */
    async refreshPivot(pivotId) {
        const pivotInfo = this.pivots.get(pivotId);
        if (!pivotInfo) return;

        // Clear existing cells
        this.clearPivotArea(pivotInfo);

        // Re-render
        await this.addPivot(
            pivotId,
            pivotInfo.sheetId,
            pivotInfo.startRow,
            pivotInfo.startCol,
            pivotInfo.options
        );
    }

    /**
     * Clear pivot table area.
     * @param {Object} pivotInfo - Pivot info
     */
    clearPivotArea(pivotInfo) {
        // Clear cells in the pivot area
        // This would iterate through the bounds and clear each cell
        const { sheetId, startRow, startCol, bounds } = pivotInfo;
        if (!bounds) return;

        for (let row = startRow; row <= bounds.endRow; row++) {
            for (let col = startCol; col <= bounds.endCol; col++) {
                this.univerWrapper.setCellValue(sheetId, row, col, "");
            }
        }
    }

    /**
     * Remove a pivot table.
     * @param {number} pivotId - Pivot ID
     */
    removePivot(pivotId) {
        const pivotInfo = this.pivots.get(pivotId);
        if (pivotInfo) {
            this.clearPivotArea(pivotInfo);
            this.pivots.delete(pivotId);
        }
    }

    /**
     * Refresh all pivot tables.
     */
    async refreshAll() {
        const promises = Array.from(this.pivots.keys()).map(id => this.refreshPivot(id));
        await Promise.all(promises);
    }
}
