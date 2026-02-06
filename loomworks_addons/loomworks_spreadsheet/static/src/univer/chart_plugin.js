/** @loomworks-module **/
/**
 * Chart Plugin for Univer
 *
 * Extends Univer with chart functionality using ECharts:
 * - Embed charts in spreadsheets
 * - Data-bound charts from Odoo
 * - Multiple chart types
 */

/**
 * ChartManager - Manages charts in a spreadsheet.
 */
export class ChartManager {
    constructor(univerWrapper, spreadsheetService) {
        this.univerWrapper = univerWrapper;
        this.spreadsheetService = spreadsheetService;
        this.charts = new Map();
        this.chartInstances = new Map();
    }

    /**
     * Add a chart to the spreadsheet.
     * @param {number} chartId - Odoo chart ID
     * @param {string} containerId - DOM container ID
     * @param {Object} options - Chart options
     */
    async addChart(chartId, containerId, options = {}) {
        try {
            // Get chart data from Odoo
            const chartData = await this.spreadsheetService.getChartData(chartId);
            const echartsOption = await this.spreadsheetService.getEchartsOption(chartId);

            if (chartData.error || echartsOption.error) {
                console.error("Chart error:", chartData.error || echartsOption.error);
                return null;
            }

            // Create ECharts instance
            const container = document.getElementById(containerId);
            if (!container) {
                console.error("Chart container not found:", containerId);
                return null;
            }

            // Check if ECharts is available
            if (typeof window.echarts === "undefined") {
                console.error("ECharts library not loaded");
                return null;
            }

            const chart = window.echarts.init(container, options.theme || null);
            chart.setOption(echartsOption);

            // Store chart info
            const chartInfo = {
                chartId,
                containerId,
                options,
                data: chartData,
                echartsOption,
            };

            this.charts.set(chartId, chartInfo);
            this.chartInstances.set(chartId, chart);

            // Handle resize
            window.addEventListener("resize", () => {
                chart.resize();
            });

            return chartInfo;
        } catch (error) {
            console.error("Failed to add chart:", error);
            return null;
        }
    }

    /**
     * Refresh a chart with new data.
     * @param {number} chartId - Chart ID
     */
    async refreshChart(chartId) {
        const chartInfo = this.charts.get(chartId);
        const chart = this.chartInstances.get(chartId);

        if (!chartInfo || !chart) return;

        try {
            const newOption = await this.spreadsheetService.getEchartsOption(chartId);

            if (!newOption.error) {
                chart.setOption(newOption, true);
                chartInfo.echartsOption = newOption;
            }
        } catch (error) {
            console.error("Failed to refresh chart:", error);
        }
    }

    /**
     * Remove a chart.
     * @param {number} chartId - Chart ID
     */
    removeChart(chartId) {
        const chart = this.chartInstances.get(chartId);
        if (chart) {
            chart.dispose();
            this.chartInstances.delete(chartId);
        }
        this.charts.delete(chartId);
    }

    /**
     * Resize all charts.
     */
    resizeAll() {
        this.chartInstances.forEach(chart => {
            chart.resize();
        });
    }

    /**
     * Dispose all charts.
     */
    dispose() {
        this.chartInstances.forEach(chart => {
            chart.dispose();
        });
        this.chartInstances.clear();
        this.charts.clear();
    }

    /**
     * Create a chart from cell range data.
     * @param {string} sheetId - Sheet ID
     * @param {Object} range - Cell range
     * @param {string} chartType - Chart type
     * @param {string} containerId - DOM container ID
     * @returns {Object} Chart instance
     */
    createChartFromRange(sheetId, range, chartType, containerId) {
        const container = document.getElementById(containerId);
        if (!container || typeof window.echarts === "undefined") {
            return null;
        }

        // Extract data from spreadsheet
        const workbook = this.univerWrapper.workbook;
        if (!workbook) return null;

        const sheet = workbook.getSheetBySheetId(sheetId);
        if (!sheet) return null;

        const { startRow, startCol, endRow, endCol } = range;

        // Extract labels (first column) and data (remaining columns)
        const labels = [];
        const datasets = [];

        // Get column headers
        const headerRow = [];
        for (let col = startCol; col <= endCol; col++) {
            const cell = sheet.getCellValue(startRow, col);
            headerRow.push(cell?.v || `Column ${col - startCol + 1}`);
        }

        // Initialize datasets
        for (let col = startCol + 1; col <= endCol; col++) {
            datasets.push({
                label: headerRow[col - startCol],
                data: [],
            });
        }

        // Extract data rows
        for (let row = startRow + 1; row <= endRow; row++) {
            // First column is labels
            const labelCell = sheet.getCellValue(row, startCol);
            labels.push(labelCell?.v || "");

            // Remaining columns are data
            for (let col = startCol + 1; col <= endCol; col++) {
                const cell = sheet.getCellValue(row, col);
                const value = parseFloat(cell?.v) || 0;
                datasets[col - startCol - 1].data.push(value);
            }
        }

        // Build ECharts option
        const option = this.buildEchartsOption(chartType, labels, datasets);

        // Create chart
        const chart = window.echarts.init(container);
        chart.setOption(option);

        const chartId = "range_chart_" + Date.now();
        this.chartInstances.set(chartId, chart);

        return {
            id: chartId,
            chart,
            option,
        };
    }

    /**
     * Build ECharts option from data.
     * @param {string} chartType - Chart type
     * @param {Array} labels - X-axis labels
     * @param {Array} datasets - Data series
     * @returns {Object} ECharts option
     */
    buildEchartsOption(chartType, labels, datasets) {
        const option = {
            tooltip: {
                trigger: chartType === "pie" ? "item" : "axis",
            },
            legend: {
                data: datasets.map(d => d.label),
                bottom: 0,
            },
        };

        switch (chartType) {
            case "pie":
            case "doughnut":
                option.series = [{
                    type: "pie",
                    radius: chartType === "doughnut" ? ["40%", "70%"] : "50%",
                    data: labels.map((label, i) => ({
                        name: label,
                        value: datasets[0]?.data[i] || 0,
                    })),
                }];
                break;

            case "line":
            case "area":
                option.xAxis = {
                    type: "category",
                    data: labels,
                };
                option.yAxis = {
                    type: "value",
                };
                option.series = datasets.map(ds => ({
                    name: ds.label,
                    type: "line",
                    data: ds.data,
                    areaStyle: chartType === "area" ? {} : null,
                }));
                break;

            case "bar":
            default:
                option.xAxis = {
                    type: "category",
                    data: labels,
                };
                option.yAxis = {
                    type: "value",
                };
                option.series = datasets.map(ds => ({
                    name: ds.label,
                    type: "bar",
                    data: ds.data,
                }));
                break;
        }

        return option;
    }

    /**
     * Export chart as image.
     * @param {string|number} chartId - Chart ID
     * @param {string} format - Image format (png, jpg)
     * @returns {string} Data URL
     */
    exportAsImage(chartId, format = "png") {
        const chart = this.chartInstances.get(chartId);
        if (!chart) return null;

        return chart.getDataURL({
            type: format,
            pixelRatio: 2,
            backgroundColor: "#fff",
        });
    }

    /**
     * Download chart as image.
     * @param {string|number} chartId - Chart ID
     * @param {string} filename - File name
     * @param {string} format - Image format
     */
    downloadAsImage(chartId, filename = "chart", format = "png") {
        const dataUrl = this.exportAsImage(chartId, format);
        if (!dataUrl) return;

        const link = document.createElement("a");
        link.download = `${filename}.${format}`;
        link.href = dataUrl;
        link.click();
    }
}

/**
 * ChartOverlay - Renders chart overlays on the spreadsheet.
 */
export class ChartOverlay {
    constructor(containerElement) {
        this.container = containerElement;
        this.overlays = new Map();
    }

    /**
     * Create a chart overlay at specified position.
     * @param {string} id - Overlay ID
     * @param {number} x - X position (pixels)
     * @param {number} y - Y position (pixels)
     * @param {number} width - Width (pixels)
     * @param {number} height - Height (pixels)
     * @returns {HTMLElement} Chart container element
     */
    createOverlay(id, x, y, width, height) {
        const overlay = document.createElement("div");
        overlay.id = `chart_overlay_${id}`;
        overlay.className = "spreadsheet-chart-overlay";
        overlay.style.cssText = `
            position: absolute;
            left: ${x}px;
            top: ${y}px;
            width: ${width}px;
            height: ${height}px;
            background: #fff;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            z-index: 100;
        `;

        // Add resize handle
        const resizeHandle = document.createElement("div");
        resizeHandle.className = "chart-resize-handle";
        resizeHandle.style.cssText = `
            position: absolute;
            right: 0;
            bottom: 0;
            width: 16px;
            height: 16px;
            cursor: se-resize;
            background: linear-gradient(135deg, transparent 50%, #ccc 50%);
        `;
        overlay.appendChild(resizeHandle);

        // Add drag handle
        const dragHandle = document.createElement("div");
        dragHandle.className = "chart-drag-handle";
        dragHandle.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 24px;
            background: #f5f5f5;
            border-bottom: 1px solid #ddd;
            cursor: move;
            display: flex;
            align-items: center;
            padding: 0 8px;
            font-size: 12px;
        `;
        overlay.appendChild(dragHandle);

        // Chart container (inside overlay)
        const chartContainer = document.createElement("div");
        chartContainer.id = `chart_container_${id}`;
        chartContainer.style.cssText = `
            position: absolute;
            top: 24px;
            left: 0;
            right: 0;
            bottom: 0;
        `;
        overlay.appendChild(chartContainer);

        this.container.appendChild(overlay);
        this.overlays.set(id, overlay);

        // Setup drag and resize handlers
        this.setupDragHandler(overlay, dragHandle);
        this.setupResizeHandler(overlay, resizeHandle);

        return chartContainer;
    }

    /**
     * Setup drag handler for overlay.
     * @param {HTMLElement} overlay - Overlay element
     * @param {HTMLElement} handle - Drag handle element
     */
    setupDragHandler(overlay, handle) {
        let isDragging = false;
        let startX, startY, startLeft, startTop;

        handle.addEventListener("mousedown", (e) => {
            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;
            startLeft = parseInt(overlay.style.left) || 0;
            startTop = parseInt(overlay.style.top) || 0;
            e.preventDefault();
        });

        document.addEventListener("mousemove", (e) => {
            if (!isDragging) return;
            overlay.style.left = `${startLeft + e.clientX - startX}px`;
            overlay.style.top = `${startTop + e.clientY - startY}px`;
        });

        document.addEventListener("mouseup", () => {
            isDragging = false;
        });
    }

    /**
     * Setup resize handler for overlay.
     * @param {HTMLElement} overlay - Overlay element
     * @param {HTMLElement} handle - Resize handle element
     */
    setupResizeHandler(overlay, handle) {
        let isResizing = false;
        let startX, startY, startWidth, startHeight;

        handle.addEventListener("mousedown", (e) => {
            isResizing = true;
            startX = e.clientX;
            startY = e.clientY;
            startWidth = parseInt(overlay.style.width) || 400;
            startHeight = parseInt(overlay.style.height) || 300;
            e.preventDefault();
            e.stopPropagation();
        });

        document.addEventListener("mousemove", (e) => {
            if (!isResizing) return;
            overlay.style.width = `${startWidth + e.clientX - startX}px`;
            overlay.style.height = `${startHeight + e.clientY - startY}px`;

            // Trigger resize event for ECharts
            const event = new CustomEvent("chart-resize", {
                detail: { overlayId: overlay.id },
            });
            overlay.dispatchEvent(event);
        });

        document.addEventListener("mouseup", () => {
            isResizing = false;
        });
    }

    /**
     * Remove an overlay.
     * @param {string} id - Overlay ID
     */
    removeOverlay(id) {
        const overlay = this.overlays.get(id);
        if (overlay) {
            overlay.remove();
            this.overlays.delete(id);
        }
    }

    /**
     * Get overlay position and size.
     * @param {string} id - Overlay ID
     * @returns {Object} Position and size
     */
    getOverlayBounds(id) {
        const overlay = this.overlays.get(id);
        if (!overlay) return null;

        return {
            x: parseInt(overlay.style.left) || 0,
            y: parseInt(overlay.style.top) || 0,
            width: parseInt(overlay.style.width) || 400,
            height: parseInt(overlay.style.height) || 300,
        };
    }
}
