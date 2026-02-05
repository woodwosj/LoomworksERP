/** @odoo-module **/
/**
 * Data Source Dialog Component
 *
 * Dialog for configuring and inserting Odoo data into spreadsheets.
 */

import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class DataSourceDialog extends Component {
    static template = "loomworks_spreadsheet.DataSourceDialog";
    static props = {
        onConfirm: { type: Function },
        onClose: { type: Function },
        documentId: { type: Number },
    };

    setup() {
        this.spreadsheetService = useService("spreadsheet");
        this.notification = useService("notification");
        this.orm = useService("orm");

        this.state = useState({
            // Model selection
            models: [],
            selectedModelId: null,
            selectedModelName: "",
            modelSearch: "",

            // Field selection
            fields: [],
            selectedFieldIds: [],

            // Filter
            domain: "[]",

            // Target
            targetCell: "A1",
            includeHeaders: true,
            limit: 1000,

            // Preview
            previewData: null,
            isLoadingModels: true,
            isLoadingFields: false,
            isLoadingPreview: false,
        });

        onMounted(async () => {
            await this.loadModels();
        });
    }

    /**
     * Load available Odoo models.
     */
    async loadModels() {
        this.state.isLoadingModels = true;
        try {
            const models = await this.spreadsheetService.listModels();
            this.state.models = models;
        } catch (error) {
            this.notification.add("Failed to load models", { type: "danger" });
        } finally {
            this.state.isLoadingModels = false;
        }
    }

    /**
     * Filter models based on search.
     */
    get filteredModels() {
        const search = this.state.modelSearch.toLowerCase();
        if (!search) return this.state.models.slice(0, 50);

        return this.state.models.filter(m =>
            m.name.toLowerCase().includes(search) ||
            m.model.toLowerCase().includes(search)
        ).slice(0, 50);
    }

    /**
     * Handle model selection.
     */
    async selectModel(model) {
        this.state.selectedModelId = model.id;
        this.state.selectedModelName = model.model;
        this.state.selectedFieldIds = [];
        this.state.previewData = null;

        await this.loadFields(model.model);
    }

    /**
     * Load fields for selected model.
     */
    async loadFields(modelName) {
        this.state.isLoadingFields = true;
        try {
            const fields = await this.spreadsheetService.getModelFields(modelName);
            this.state.fields = fields;
        } catch (error) {
            this.notification.add("Failed to load fields", { type: "danger" });
        } finally {
            this.state.isLoadingFields = false;
        }
    }

    /**
     * Toggle field selection.
     */
    toggleField(field) {
        const idx = this.state.selectedFieldIds.indexOf(field.id);
        if (idx === -1) {
            this.state.selectedFieldIds.push(field.id);
        } else {
            this.state.selectedFieldIds.splice(idx, 1);
        }
    }

    /**
     * Check if field is selected.
     */
    isFieldSelected(field) {
        return this.state.selectedFieldIds.includes(field.id);
    }

    /**
     * Get selected field names.
     */
    get selectedFieldNames() {
        return this.state.fields
            .filter(f => this.state.selectedFieldIds.includes(f.id))
            .map(f => f.name);
    }

    /**
     * Load preview data.
     */
    async loadPreview() {
        if (!this.state.selectedModelName || this.selectedFieldNames.length === 0) {
            this.notification.add("Please select a model and fields", { type: "warning" });
            return;
        }

        this.state.isLoadingPreview = true;
        try {
            const data = await this.spreadsheetService.previewModelData(
                this.state.selectedModelName,
                this.selectedFieldNames,
                this.state.domain,
                10
            );
            this.state.previewData = data;
        } catch (error) {
            this.notification.add(`Preview failed: ${error.message}`, { type: "danger" });
        } finally {
            this.state.isLoadingPreview = false;
        }
    }

    /**
     * Select all fields.
     */
    selectAllFields() {
        this.state.selectedFieldIds = this.state.fields.map(f => f.id);
    }

    /**
     * Clear field selection.
     */
    clearFieldSelection() {
        this.state.selectedFieldIds = [];
    }

    /**
     * Validate cell reference format.
     */
    isValidCellRef(ref) {
        return /^[A-Z]+\d+$/i.test(ref);
    }

    /**
     * Confirm and insert data.
     */
    async confirm() {
        if (!this.state.selectedModelId) {
            this.notification.add("Please select a model", { type: "warning" });
            return;
        }

        if (this.state.selectedFieldIds.length === 0) {
            this.notification.add("Please select at least one field", { type: "warning" });
            return;
        }

        if (!this.isValidCellRef(this.state.targetCell)) {
            this.notification.add("Invalid cell reference", { type: "warning" });
            return;
        }

        this.props.onConfirm({
            modelId: this.state.selectedModelId,
            modelName: this.state.selectedModelName,
            fieldIds: this.state.selectedFieldIds,
            fieldNames: this.selectedFieldNames,
            domain: this.state.domain,
            targetCell: this.state.targetCell.toUpperCase(),
            includeHeaders: this.state.includeHeaders,
            limit: this.state.limit,
        });
    }

    /**
     * Get field type badge class.
     */
    getFieldTypeBadge(type) {
        const badges = {
            char: "bg-primary",
            text: "bg-primary",
            integer: "bg-success",
            float: "bg-success",
            monetary: "bg-warning",
            boolean: "bg-info",
            date: "bg-secondary",
            datetime: "bg-secondary",
            many2one: "bg-purple",
            one2many: "bg-purple",
            many2many: "bg-purple",
            selection: "bg-dark",
        };
        return badges[type] || "bg-secondary";
    }
}

DataSourceDialog.template = "loomworks_spreadsheet.DataSourceDialog";
