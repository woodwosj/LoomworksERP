/** @loomworks-module */
/**
 * Field Palette Component - Drag-drop field selection for Studio.
 *
 * This component displays available field types and existing model fields
 * that can be dragged onto views for customization.
 *
 * Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
 */

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class FieldPalette extends Component {
    static template = "loomworks_studio.FieldPalette";
    static props = {
        modelId: { type: Number },
        modelName: { type: String },
        onFieldDrop: { type: Function, optional: true },
        onClose: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.studioService = useService("studio");

        this.state = useState({
            activeTab: "new",
            searchQuery: "",
            fieldTypes: [],
            existingFields: [],
            loading: true,
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        try {
            // Load field types
            this.state.fieldTypes = await this.studioService.getFieldTypes();

            // Load existing fields
            if (this.props.modelId) {
                this.state.existingFields = await this.studioService.getExistingFields(
                    this.props.modelId
                );
            }
        } finally {
            this.state.loading = false;
        }
    }

    get filteredFieldTypes() {
        if (!this.state.searchQuery) return this.state.fieldTypes;
        const query = this.state.searchQuery.toLowerCase();
        return this.state.fieldTypes.filter(
            (ft) =>
                ft.label.toLowerCase().includes(query) ||
                ft.description.toLowerCase().includes(query)
        );
    }

    get filteredExistingFields() {
        if (!this.state.searchQuery) return this.state.existingFields;
        const query = this.state.searchQuery.toLowerCase();
        return this.state.existingFields.filter(
            (f) =>
                f.name.toLowerCase().includes(query) ||
                f.field_description.toLowerCase().includes(query)
        );
    }

    setActiveTab(tab) {
        this.state.activeTab = tab;
    }

    onSearchInput(ev) {
        this.state.searchQuery = ev.target.value;
    }

    onDragStart(ev, fieldData) {
        const data = {
            ...fieldData,
            modelId: this.props.modelId,
            modelName: this.props.modelName,
        };
        ev.dataTransfer.setData("application/json", JSON.stringify(data));
        ev.dataTransfer.effectAllowed = "copy";
        document.body.classList.add("studio-dragging");
    }

    onDragEnd() {
        document.body.classList.remove("studio-dragging");
    }

    onFieldTypeClick(fieldType) {
        if (this.props.onFieldDrop) {
            this.props.onFieldDrop({
                type: fieldType.type,
                label: fieldType.label,
                isNew: true,
            });
        }
    }

    onExistingFieldClick(field) {
        if (this.props.onFieldDrop) {
            this.props.onFieldDrop({
                existingFieldId: field.id,
                name: field.name,
                label: field.field_description,
                type: field.ttype,
                isNew: false,
            });
        }
    }

    onClose() {
        if (this.props.onClose) {
            this.props.onClose();
        }
    }
}
