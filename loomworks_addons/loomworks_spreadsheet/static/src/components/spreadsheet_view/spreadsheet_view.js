/** @loomworks-module **/
/**
 * Spreadsheet View Component
 *
 * Main Owl component for the spreadsheet interface.
 * Integrates Univer wrapper with Odoo view system.
 */

import { Component, onMounted, onWillUnmount, useState, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { UniverWrapper } from "../../univer/univer_wrapper";
import { DataSourceManager, registerOdooFormulas } from "../../univer/odoo_data_plugin";
import { PivotTableManager } from "../../univer/pivot_plugin";
import { ChartManager, ChartOverlay } from "../../univer/chart_plugin";

export class SpreadsheetView extends Component {
    static template = "loomworks_spreadsheet.SpreadsheetView";
    static components = { UniverWrapper };
    static props = {
        documentId: { type: Number },
        readonly: { type: Boolean, optional: true },
    };

    setup() {
        this.spreadsheetService = useService("spreadsheet");
        this.notification = useService("notification");
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.orm = useService("orm");

        this.containerRef = useRef("spreadsheetContainer");
        this.univerWrapperRef = useRef("univerWrapper");

        this.state = useState({
            isLoading: true,
            documentName: "",
            currentSheet: "Sheet 1",
            currentCell: "A1",
            formula: "",
            zoom: 100,
            isDirty: false,
            isSaving: false,
            showDataSourceDialog: false,
            showPivotDialog: false,
            showChartDialog: false,
        });

        // Managers for data, pivots, charts
        this.dataSourceManager = null;
        this.pivotManager = null;
        this.chartManager = null;
        this.chartOverlay = null;

        // Auto-save timer
        this.autoSaveTimer = null;

        onMounted(async () => {
            await this.loadDocument();
            this.setupKeyboardShortcuts();
            this.setupAutoSave();
        });

        onWillUnmount(() => {
            this.cleanup();
        });
    }

    /**
     * Load the spreadsheet document.
     */
    async loadDocument() {
        this.state.isLoading = true;

        try {
            const doc = await this.spreadsheetService.loadDocument(this.props.documentId);
            this.state.documentName = doc.name || "Untitled Spreadsheet";
            this.state.isLoading = false;

            // Initialize managers after Univer is ready
            this.initializeManagers();
        } catch (error) {
            this.notification.add(`Failed to load spreadsheet: ${error.message}`, {
                type: "danger",
            });
            this.state.isLoading = false;
        }
    }

    /**
     * Initialize data managers.
     */
    initializeManagers() {
        const univerWrapper = this.univerWrapperRef.comp;
        if (!univerWrapper) return;

        // Register Odoo formulas
        if (univerWrapper.univerInstance) {
            registerOdooFormulas(univerWrapper.univerInstance);
        }

        // Initialize managers
        this.dataSourceManager = new DataSourceManager(univerWrapper);
        this.pivotManager = new PivotTableManager(univerWrapper, this.spreadsheetService);
        this.chartManager = new ChartManager(univerWrapper, this.spreadsheetService);

        // Initialize chart overlay
        if (this.containerRef.el) {
            this.chartOverlay = new ChartOverlay(this.containerRef.el);
        }
    }

    /**
     * Setup keyboard shortcuts.
     */
    setupKeyboardShortcuts() {
        this.keyHandler = (e) => {
            // Ctrl+S / Cmd+S - Save
            if ((e.ctrlKey || e.metaKey) && e.key === "s") {
                e.preventDefault();
                this.saveDocument();
            }

            // Ctrl+Z / Cmd+Z - Undo
            if ((e.ctrlKey || e.metaKey) && e.key === "z" && !e.shiftKey) {
                // Handled by Univer
            }

            // Ctrl+Shift+Z / Cmd+Shift+Z - Redo
            if ((e.ctrlKey || e.metaKey) && e.key === "z" && e.shiftKey) {
                // Handled by Univer
            }
        };

        document.addEventListener("keydown", this.keyHandler);
    }

    /**
     * Setup auto-save functionality.
     */
    setupAutoSave() {
        this.autoSaveTimer = setInterval(() => {
            if (this.state.isDirty && !this.state.isSaving) {
                this.saveDocument(true);
            }
        }, 60000); // Auto-save every minute
    }

    /**
     * Cleanup on component unmount.
     */
    cleanup() {
        if (this.keyHandler) {
            document.removeEventListener("keydown", this.keyHandler);
        }

        if (this.autoSaveTimer) {
            clearInterval(this.autoSaveTimer);
        }

        if (this.dataSourceManager) {
            this.dataSourceManager.dispose();
        }

        if (this.chartManager) {
            this.chartManager.dispose();
        }
    }

    /**
     * Handle data changes from Univer.
     */
    onDataChange(data) {
        this.state.isDirty = true;
    }

    /**
     * Handle selection changes.
     */
    onSelectionChange(selection) {
        if (selection) {
            this.state.currentCell = selection.cellRef || "A1";
            this.state.formula = selection.formula || "";
        }
    }

    /**
     * Save the document.
     */
    async saveDocument(silent = false) {
        if (this.state.isSaving) return;

        this.state.isSaving = true;

        try {
            const univerWrapper = this.univerWrapperRef.comp;
            if (!univerWrapper) return;

            const data = univerWrapper.getWorkbookData();
            await this.spreadsheetService.saveDocument(this.props.documentId, data);

            this.state.isDirty = false;

            if (!silent) {
                this.notification.add("Spreadsheet saved", {
                    type: "success",
                    sticky: false,
                });
            }
        } catch (error) {
            this.notification.add(`Failed to save: ${error.message}`, {
                type: "danger",
            });
        } finally {
            this.state.isSaving = false;
        }
    }

    /**
     * Open data source dialog.
     */
    openDataSourceDialog() {
        this.state.showDataSourceDialog = true;
    }

    /**
     * Close data source dialog.
     */
    closeDataSourceDialog() {
        this.state.showDataSourceDialog = false;
    }

    /**
     * Add data source to spreadsheet.
     */
    async addDataSource(config) {
        if (!this.dataSourceManager) return;

        try {
            // Create data source in Odoo
            const sourceId = await this.orm.create("spreadsheet.data.source", [{
                name: config.name,
                document_id: this.props.documentId,
                source_type: "model",
                model_id: config.modelId,
                domain: config.domain || "[]",
                field_ids: [[6, 0, config.fieldIds || []]],
                target_sheet: config.sheetId || "sheet1",
                target_cell: config.targetCell || "A1",
                include_headers: config.includeHeaders !== false,
            }]);

            // Fetch and insert data
            const data = await this.spreadsheetService.fetchDataSource(sourceId);

            const univerWrapper = this.univerWrapperRef.comp;
            if (univerWrapper) {
                univerWrapper.insertOdooData(
                    data,
                    config.sheetId || "sheet1",
                    this.parseCellRef(config.targetCell || "A1").row,
                    this.parseCellRef(config.targetCell || "A1").col,
                    config.includeHeaders !== false
                );
            }

            this.notification.add(`Inserted ${data.record_count} records`, {
                type: "success",
            });

            this.closeDataSourceDialog();
        } catch (error) {
            this.notification.add(`Failed to add data source: ${error.message}`, {
                type: "danger",
            });
        }
    }

    /**
     * Open pivot table dialog.
     */
    openPivotDialog() {
        this.state.showPivotDialog = true;
    }

    /**
     * Close pivot dialog.
     */
    closePivotDialog() {
        this.state.showPivotDialog = false;
    }

    /**
     * Add pivot table to spreadsheet.
     */
    async addPivotTable(config) {
        if (!this.pivotManager) return;

        try {
            // Create pivot in Odoo
            const pivotId = await this.orm.create("spreadsheet.pivot", [{
                name: config.name,
                document_id: this.props.documentId,
                model_id: config.modelId,
                domain: config.domain || "[]",
                row_field_ids: [[6, 0, config.rowFieldIds || []]],
                column_field_ids: [[6, 0, config.columnFieldIds || []]],
                target_sheet: config.sheetId || "sheet1",
                target_cell: config.targetCell || "A1",
            }]);

            // Add measures
            for (const measure of config.measures || []) {
                await this.orm.create("spreadsheet.pivot.measure", [{
                    pivot_id: pivotId,
                    field_id: measure.fieldId,
                    aggregator: measure.aggregator || "sum",
                }]);
            }

            // Render pivot
            const cellRef = this.parseCellRef(config.targetCell || "A1");
            await this.pivotManager.addPivot(
                pivotId,
                config.sheetId || "sheet1",
                cellRef.row,
                cellRef.col
            );

            this.notification.add("Pivot table created", { type: "success" });
            this.closePivotDialog();
        } catch (error) {
            this.notification.add(`Failed to create pivot: ${error.message}`, {
                type: "danger",
            });
        }
    }

    /**
     * Open chart dialog.
     */
    openChartDialog() {
        this.state.showChartDialog = true;
    }

    /**
     * Close chart dialog.
     */
    closeChartDialog() {
        this.state.showChartDialog = false;
    }

    /**
     * Add chart to spreadsheet.
     */
    async addChart(config) {
        if (!this.chartManager || !this.chartOverlay) return;

        try {
            // Create chart in Odoo
            const chartId = await this.orm.create("spreadsheet.chart", [{
                name: config.name,
                document_id: this.props.documentId,
                chart_type: config.chartType,
                source_type: config.sourceType || "model",
                model_id: config.modelId,
                domain: config.domain || "[]",
                groupby_field_id: config.groupbyFieldId,
                measure_field_id: config.measureFieldId,
                measure_aggregator: config.aggregator || "sum",
                position_x: config.x || 100,
                position_y: config.y || 100,
                width: config.width || 600,
                height: config.height || 400,
            }]);

            // Create chart overlay
            const container = this.chartOverlay.createOverlay(
                chartId,
                config.x || 100,
                config.y || 100,
                config.width || 600,
                config.height || 400
            );

            // Render chart
            await this.chartManager.addChart(chartId, container.id);

            this.notification.add("Chart created", { type: "success" });
            this.closeChartDialog();
        } catch (error) {
            this.notification.add(`Failed to create chart: ${error.message}`, {
                type: "danger",
            });
        }
    }

    /**
     * Parse cell reference to row/column indices.
     */
    parseCellRef(ref) {
        const match = ref.match(/^([A-Z]+)(\d+)$/i);
        if (!match) return { row: 0, col: 0 };

        const colStr = match[1].toUpperCase();
        const rowStr = match[2];

        let col = 0;
        for (const char of colStr) {
            col = col * 26 + (char.charCodeAt(0) - "A".charCodeAt(0) + 1);
        }
        col--;

        const row = parseInt(rowStr) - 1;

        return { row, col };
    }

    /**
     * Refresh all data sources.
     */
    async refreshAllData() {
        try {
            if (this.dataSourceManager) {
                await this.dataSourceManager.refreshAll();
            }
            if (this.pivotManager) {
                await this.pivotManager.refreshAll();
            }
            this.notification.add("Data refreshed", { type: "success" });
        } catch (error) {
            this.notification.add(`Failed to refresh: ${error.message}`, {
                type: "danger",
            });
        }
    }

    /**
     * Add a new sheet.
     */
    addSheet() {
        const univerWrapper = this.univerWrapperRef.comp;
        if (univerWrapper) {
            univerWrapper.addSheet();
        }
    }

    /**
     * Set zoom level.
     */
    setZoom(level) {
        this.state.zoom = level;
        // Apply zoom to Univer if supported
    }

    /**
     * Export spreadsheet.
     */
    async exportSpreadsheet(format = "xlsx") {
        try {
            window.open(
                `/spreadsheet/document/${this.props.documentId}/export/${format}`,
                "_blank"
            );
        } catch (error) {
            this.notification.add(`Export failed: ${error.message}`, {
                type: "danger",
            });
        }
    }

    /**
     * Go back to document list.
     */
    goBack() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "spreadsheet.document",
            view_mode: "kanban,tree,form",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
        });
    }
}

SpreadsheetView.template = "loomworks_spreadsheet.SpreadsheetView";
