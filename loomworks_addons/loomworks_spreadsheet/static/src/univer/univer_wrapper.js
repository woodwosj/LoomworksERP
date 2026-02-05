/** @odoo-module **/
/**
 * Univer Wrapper for Loomworks Spreadsheet
 *
 * Wraps the Univer spreadsheet library for integration with Odoo/Owl.
 * Provides initialization, data binding, and event handling.
 */

import { Component, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * UniverWrapper - Owl component that hosts the Univer spreadsheet instance.
 */
export class UniverWrapper extends Component {
    static template = "loomworks_spreadsheet.UniverWrapper";
    static props = {
        documentId: { type: Number, optional: true },
        data: { type: Object, optional: true },
        readonly: { type: Boolean, optional: true },
        onDataChange: { type: Function, optional: true },
        onSelectionChange: { type: Function, optional: true },
    };

    setup() {
        this.containerRef = useRef("univerContainer");
        this.spreadsheetService = useService("spreadsheet");
        this.notification = useService("notification");

        this.state = useState({
            isReady: false,
            currentCell: "A1",
            formula: "",
        });

        // Univer instances
        this.univerInstance = null;
        this.workbook = null;
        this.commandService = null;

        onMounted(() => {
            this.initializeUniver();
        });

        onWillUnmount(() => {
            this.destroyUniver();
        });
    }

    /**
     * Initialize Univer spreadsheet instance.
     */
    async initializeUniver() {
        const container = this.containerRef.el;
        if (!container) {
            console.error("Univer container not found");
            return;
        }

        try {
            // Check if Univer is available
            if (typeof window.Univer === "undefined") {
                throw new Error("Univer library not loaded");
            }

            const { Univer, UniverInstanceType, LocaleType } = window.Univer;
            const { UniverSheetsPlugin } = window.UniverSheets;
            const { UniverSheetsUIPlugin } = window.UniverSheetsUI;
            const { UniverDocsPlugin } = window.UniverDocs;
            const { UniverDocsUIPlugin } = window.UniverDocsUI;
            const { UniverRenderEnginePlugin } = window.UniverRenderEngine;
            const { UniverUIPlugin } = window.UniverUI;

            // Create Univer instance
            this.univerInstance = new Univer({
                theme: {},
                locale: LocaleType.EN_US,
            });

            // Register plugins
            this.univerInstance.registerPlugin(UniverRenderEnginePlugin);
            this.univerInstance.registerPlugin(UniverUIPlugin, {
                container,
            });

            // Documents plugins (required for rich text in cells)
            this.univerInstance.registerPlugin(UniverDocsPlugin);
            this.univerInstance.registerPlugin(UniverDocsUIPlugin);

            // Sheets plugins
            this.univerInstance.registerPlugin(UniverSheetsPlugin);
            this.univerInstance.registerPlugin(UniverSheetsUIPlugin);

            // Load data if provided
            const data = this.props.data || this.getDefaultWorkbookData();
            this.workbook = this.univerInstance.createUnit(
                UniverInstanceType.UNIVER_SHEET,
                data
            );

            // Get services
            this.commandService = this.univerInstance.__getInjector().get("ICommandService");

            // Set up event listeners
            this.setupEventListeners();

            this.state.isReady = true;
            console.log("Univer initialized successfully");

        } catch (error) {
            console.error("Failed to initialize Univer:", error);
            this.notification.add(
                `Failed to initialize spreadsheet: ${error.message}`,
                { type: "danger" }
            );
        }
    }

    /**
     * Destroy Univer instance on unmount.
     */
    destroyUniver() {
        if (this.univerInstance) {
            try {
                this.univerInstance.dispose();
            } catch (error) {
                console.warn("Error disposing Univer:", error);
            }
            this.univerInstance = null;
            this.workbook = null;
            this.commandService = null;
        }
    }

    /**
     * Set up event listeners for Univer events.
     */
    setupEventListeners() {
        if (!this.commandService) return;

        // Listen for data changes
        this.commandService.onCommandExecuted((command) => {
            // Track commands that modify data
            const modifyCommands = [
                "sheet.mutation.set-cell-value",
                "sheet.mutation.set-range-values",
                "sheet.mutation.insert-row",
                "sheet.mutation.insert-col",
                "sheet.mutation.remove-row",
                "sheet.mutation.remove-col",
            ];

            if (modifyCommands.some(c => command.id.includes(c))) {
                this.handleDataChange();
            }
        });
    }

    /**
     * Handle data changes in the spreadsheet.
     */
    handleDataChange() {
        if (this.props.onDataChange && this.workbook) {
            const data = this.getWorkbookData();
            this.props.onDataChange(data);
        }

        // Mark as dirty in service
        this.spreadsheetService.markDirty();
    }

    /**
     * Get current workbook data.
     * @returns {Object} Workbook data
     */
    getWorkbookData() {
        if (!this.workbook) return null;
        return this.workbook.save();
    }

    /**
     * Load data into the workbook.
     * @param {Object} data - Workbook data
     */
    loadData(data) {
        if (!this.univerInstance || !data) return;

        // Destroy existing workbook
        if (this.workbook) {
            this.univerInstance.disposeUnit(this.workbook.getUnitId());
        }

        // Create new workbook with data
        const { UniverInstanceType } = window.Univer;
        this.workbook = this.univerInstance.createUnit(
            UniverInstanceType.UNIVER_SHEET,
            data
        );
    }

    /**
     * Get default empty workbook data.
     * @returns {Object} Default workbook data
     */
    getDefaultWorkbookData() {
        return {
            id: "workbook_" + Date.now(),
            name: "New Spreadsheet",
            appVersion: "1.0.0",
            locale: "en",
            styles: {},
            sheetOrder: ["sheet1"],
            sheets: {
                sheet1: {
                    id: "sheet1",
                    name: "Sheet 1",
                    rowCount: 1000,
                    columnCount: 26,
                    zoomRatio: 1,
                    scrollTop: 0,
                    scrollLeft: 0,
                    defaultColumnWidth: 88,
                    defaultRowHeight: 24,
                    cellData: {},
                    rowData: {},
                    columnData: {},
                    mergeData: [],
                    tabColor: "",
                    hidden: 0,
                    freeze: {
                        startRow: -1,
                        startColumn: -1,
                        ySplit: 0,
                        xSplit: 0,
                    },
                },
            },
        };
    }

    /**
     * Set cell value programmatically.
     * @param {string} sheetId - Sheet ID
     * @param {number} row - Row index
     * @param {number} col - Column index
     * @param {*} value - Cell value
     */
    setCellValue(sheetId, row, col, value) {
        if (!this.commandService) return;

        this.commandService.executeCommand("sheet.command.set-cell-value", {
            unitId: this.workbook.getUnitId(),
            subUnitId: sheetId,
            row,
            col,
            value: {
                v: value,
            },
        });
    }

    /**
     * Set range values programmatically.
     * @param {string} sheetId - Sheet ID
     * @param {number} startRow - Start row
     * @param {number} startCol - Start column
     * @param {Array} values - 2D array of values
     */
    setRangeValues(sheetId, startRow, startCol, values) {
        if (!this.commandService || !values.length) return;

        const cellValue = {};
        values.forEach((row, rowIndex) => {
            row.forEach((value, colIndex) => {
                const r = startRow + rowIndex;
                const c = startCol + colIndex;
                if (!cellValue[r]) cellValue[r] = {};
                cellValue[r][c] = { v: value };
            });
        });

        this.commandService.executeCommand("sheet.command.set-range-values", {
            unitId: this.workbook.getUnitId(),
            subUnitId: sheetId,
            range: {
                startRow,
                startColumn: startCol,
                endRow: startRow + values.length - 1,
                endColumn: startCol + (values[0]?.length || 1) - 1,
            },
            value: cellValue,
        });
    }

    /**
     * Insert Odoo data into the spreadsheet.
     * @param {Object} data - Data with headers and rows
     * @param {string} sheetId - Target sheet ID
     * @param {number} startRow - Start row (0-based)
     * @param {number} startCol - Start column (0-based)
     * @param {boolean} includeHeaders - Include headers row
     */
    insertOdooData(data, sheetId = "sheet1", startRow = 0, startCol = 0, includeHeaders = true) {
        if (!data || !data.rows) return;

        const allValues = [];

        // Add headers
        if (includeHeaders && data.headers) {
            allValues.push(data.headers);
        }

        // Add data rows
        allValues.push(...data.rows);

        this.setRangeValues(sheetId, startRow, startCol, allValues);
    }

    /**
     * Get active sheet ID.
     * @returns {string} Active sheet ID
     */
    getActiveSheetId() {
        if (!this.workbook) return null;
        return this.workbook.getActiveSheet()?.getSheetId() || null;
    }

    /**
     * Add a new sheet.
     * @param {string} name - Sheet name
     * @returns {string} New sheet ID
     */
    addSheet(name = "New Sheet") {
        if (!this.commandService) return null;

        const sheetId = "sheet_" + Date.now();

        this.commandService.executeCommand("sheet.command.insert-sheet", {
            unitId: this.workbook.getUnitId(),
            index: this.workbook.getSheetSize(),
            sheet: {
                id: sheetId,
                name,
            },
        });

        return sheetId;
    }

    /**
     * Export current data as JSON.
     * @returns {string} JSON string
     */
    exportAsJson() {
        const data = this.getWorkbookData();
        return JSON.stringify(data, null, 2);
    }
}

UniverWrapper.template = "loomworks_spreadsheet.UniverWrapper";
