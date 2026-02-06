/** @loomworks-module */
/**
 * View Designer Component - Visual editor for view layouts.
 *
 * This component provides a WYSIWYG editor for customizing form, list,
 * and kanban views using drag-and-drop.
 *
 * Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
 */

import { Component, useState, useRef, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { FieldPalette } from "../field_palette/field_palette";

export class ViewDesigner extends Component {
    static template = "loomworks_studio.ViewDesigner";
    static components = { FieldPalette };
    static props = {
        modelId: { type: Number },
        modelName: { type: String },
        viewType: { type: String },
        viewId: { type: Number, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.studioService = useService("studio");

        this.canvasRef = useRef("canvas");

        this.state = useState({
            loading: true,
            showPalette: true,
            viewArch: null,
            fields: [],
            selectedField: null,
            dragOverIndex: -1,
        });

        onMounted(() => {
            this.loadViewData();
        });
    }

    async loadViewData() {
        this.state.loading = true;
        try {
            // Get model info including fields
            const modelInfo = await this.studioService.getModelInfo(this.props.modelName);
            this.state.fields = modelInfo.fields || [];

            // Get view architecture
            // This would be loaded from the backend
            this.state.viewArch = await this.loadViewArch();
        } finally {
            this.state.loading = false;
        }
    }

    async loadViewArch() {
        // In a full implementation, this would fetch the actual view arch
        // For now, return a simple representation
        return {
            viewType: this.props.viewType,
            fields: this.state.fields.slice(0, 10).map(f => ({
                name: f.name,
                label: f.label,
                type: f.type,
            })),
        };
    }

    togglePalette() {
        this.state.showPalette = !this.state.showPalette;
    }

    onFieldSelect(field) {
        this.state.selectedField = field;
    }

    onFieldDrop(fieldData) {
        // Add field to view
        this.addFieldToView(fieldData);
    }

    async addFieldToView(fieldData) {
        try {
            await this.studioService.addFieldToView({
                model: this.props.modelName,
                viewType: this.props.viewType,
                field: fieldData,
                position: "inside",
            });

            // Reload view
            await this.loadViewData();
        } catch (error) {
            this.notification.add(
                `Failed to add field: ${error.message}`,
                { type: "danger" }
            );
        }
    }

    async removeField(fieldName) {
        try {
            await this.studioService.removeFieldFromView(
                this.props.modelName,
                this.props.viewType,
                fieldName
            );

            // Reload view
            await this.loadViewData();
        } catch (error) {
            this.notification.add(
                `Failed to remove field: ${error.message}`,
                { type: "danger" }
            );
        }
    }

    onDragOver(ev, index) {
        ev.preventDefault();
        this.state.dragOverIndex = index;
    }

    onDragLeave() {
        this.state.dragOverIndex = -1;
    }

    onDrop(ev, index) {
        ev.preventDefault();
        this.state.dragOverIndex = -1;

        try {
            const data = JSON.parse(ev.dataTransfer.getData("application/json"));
            this.addFieldToView(data);
        } catch {
            // Invalid data
        }
    }

    async onReorder(fromIndex, toIndex) {
        const fields = [...this.state.viewArch.fields];
        const [moved] = fields.splice(fromIndex, 1);
        fields.splice(toIndex, 0, moved);

        try {
            await this.studioService.reorderFields(
                this.props.modelName,
                this.props.viewType,
                fields.map(f => f.name)
            );

            this.state.viewArch.fields = fields;
        } catch (error) {
            this.notification.add(
                `Failed to reorder: ${error.message}`,
                { type: "danger" }
            );
        }
    }

    async saveChanges() {
        this.notification.add("Changes saved", { type: "success" });
    }
}
