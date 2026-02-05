/** @odoo-module */
/**
 * Automation Builder Component - Visual workflow rule editor.
 *
 * This component provides a visual interface for creating automation rules
 * with triggers, conditions, and actions.
 *
 * Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
 */

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class AutomationBuilder extends Component {
    static template = "loomworks_studio.AutomationBuilder";
    static props = {
        automationId: { type: Number, optional: true },
        modelId: { type: Number, optional: true },
        appId: { type: Number, optional: true },
        onSave: { type: Function, optional: true },
        onCancel: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            name: "",
            trigger: "on_create",
            filterDomain: "[]",
            actionType: "update_record",
            pythonCode: "",
            loading: false,
            models: [],
            selectedModel: this.props.modelId || null,
        });

        this.triggerOptions = [
            { value: "on_create", label: "When a record is created" },
            { value: "on_write", label: "When a record is updated" },
            { value: "on_create_or_write", label: "When created or updated" },
            { value: "on_unlink", label: "When a record is deleted" },
            { value: "on_time", label: "Based on time condition" },
        ];

        this.actionOptions = [
            { value: "update_record", label: "Update the record" },
            { value: "create_record", label: "Create a new record" },
            { value: "send_email", label: "Send an email" },
            { value: "create_activity", label: "Create an activity" },
            { value: "python_code", label: "Execute Python code" },
        ];

        if (this.props.automationId) {
            this.loadAutomation();
        }
        this.loadModels();
    }

    async loadModels() {
        const models = await this.orm.searchRead(
            "ir.model",
            [["transient", "=", false]],
            ["id", "name", "model"],
            { order: "name" }
        );
        this.state.models = models;
    }

    async loadAutomation() {
        this.state.loading = true;
        try {
            const [automation] = await this.orm.read(
                "studio.automation",
                [this.props.automationId],
                ["name", "trigger_type", "filter_domain", "action_type", "python_code", "model_id"]
            );

            if (automation) {
                this.state.name = automation.name;
                this.state.trigger = automation.trigger_type;
                this.state.filterDomain = automation.filter_domain || "[]";
                this.state.actionType = automation.action_type;
                this.state.pythonCode = automation.python_code || "";
                this.state.selectedModel = automation.model_id[0];
            }
        } finally {
            this.state.loading = false;
        }
    }

    onNameChange(ev) {
        this.state.name = ev.target.value;
    }

    onTriggerChange(ev) {
        this.state.trigger = ev.target.value;
    }

    onModelChange(ev) {
        this.state.selectedModel = parseInt(ev.target.value) || null;
    }

    onActionChange(ev) {
        this.state.actionType = ev.target.value;
    }

    onCodeChange(ev) {
        this.state.pythonCode = ev.target.value;
    }

    onDomainChange(ev) {
        this.state.filterDomain = ev.target.value;
    }

    async save() {
        if (!this.state.name) {
            this.notification.add("Please enter a name", { type: "warning" });
            return;
        }

        if (!this.state.selectedModel) {
            this.notification.add("Please select a model", { type: "warning" });
            return;
        }

        this.state.loading = true;
        try {
            const vals = {
                name: this.state.name,
                model_id: this.state.selectedModel,
                trigger_type: this.state.trigger,
                filter_domain: this.state.filterDomain,
                action_type: this.state.actionType,
                python_code: this.state.pythonCode,
            };

            if (this.props.appId) {
                vals.app_id = this.props.appId;
            }

            let automationId;
            if (this.props.automationId) {
                await this.orm.write("studio.automation", [this.props.automationId], vals);
                automationId = this.props.automationId;
            } else {
                [automationId] = await this.orm.create("studio.automation", [vals]);
            }

            this.notification.add("Automation saved", { type: "success" });

            if (this.props.onSave) {
                this.props.onSave(automationId);
            }
        } catch (error) {
            this.notification.add(`Failed to save: ${error.message}`, { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    cancel() {
        if (this.props.onCancel) {
            this.props.onCancel();
        }
    }
}
