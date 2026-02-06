/** @odoo-module */
/**
 * Studio Service - Core service for Studio functionality.
 *
 * This service manages Studio edit mode, field palette, and view customization
 * operations. It communicates with the backend to persist changes.
 *
 * Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
 */

import { registry } from "@web/core/registry";
import { user } from "@web/core/user";

export const studioService = {
    dependencies: ["orm", "notification", "action"],

    start(env, { orm, notification, action }) {
        let currentEditSession = null;
        let hasAccess = null;

        /**
         * Check if current user has Studio access.
         * @returns {Promise<boolean>}
         */
        async function checkAccess() {
            if (hasAccess !== null) return hasAccess;

            try {
                hasAccess = await user.hasGroup("loomworks_studio.group_studio_user");
            } catch {
                hasAccess = false;
            }
            return hasAccess;
        }

        /**
         * Enter Studio edit mode for a model/view.
         * @param {string} resModel - Model name
         * @param {string} viewType - View type (form, list, kanban)
         */
        function enterEditMode(resModel, viewType) {
            currentEditSession = {
                model: resModel,
                viewType,
                changes: [],
                startTime: Date.now(),
            };
            env.bus.trigger("STUDIO:EDIT_MODE_ENTERED", currentEditSession);
            notification.add("Studio mode activated", { type: "info", sticky: false });
        }

        /**
         * Exit Studio edit mode.
         */
        function exitEditMode() {
            if (currentEditSession) {
                env.bus.trigger("STUDIO:EDIT_MODE_EXITED", currentEditSession);
                currentEditSession = null;
            }
        }

        /**
         * Check if currently in edit mode.
         * @returns {boolean}
         */
        function isInEditMode() {
            return currentEditSession !== null;
        }

        /**
         * Get current edit session.
         * @returns {Object|null}
         */
        function getEditSession() {
            return currentEditSession;
        }

        /**
         * Get model information for Studio editing.
         * @param {string} modelName - Technical model name
         * @returns {Promise<Object>}
         */
        async function getModelInfo(modelName) {
            const result = await orm.call(
                "studio.view.customization",
                "get_model_info",
                [],
                { model_name: modelName }
            );
            return result;
        }

        /**
         * Get available field types for the field palette.
         * @returns {Promise<Array>}
         */
        async function getFieldTypes() {
            // Could be fetched from backend, but for now use static list
            return [
                { type: "char", label: "Text", icon: "fa-font", description: "Single line text" },
                { type: "text", label: "Long Text", icon: "fa-align-left", description: "Multi-line text" },
                { type: "html", label: "Rich Text", icon: "fa-code", description: "HTML content" },
                { type: "integer", label: "Integer", icon: "fa-hashtag", description: "Whole numbers" },
                { type: "float", label: "Decimal", icon: "fa-percent", description: "Decimal numbers" },
                { type: "monetary", label: "Monetary", icon: "fa-dollar", description: "Currency values" },
                { type: "boolean", label: "Checkbox", icon: "fa-check-square", description: "Yes/No" },
                { type: "date", label: "Date", icon: "fa-calendar", description: "Date picker" },
                { type: "datetime", label: "Date & Time", icon: "fa-clock-o", description: "Date and time" },
                { type: "selection", label: "Dropdown", icon: "fa-list", description: "Choose from options" },
                { type: "many2one", label: "Link", icon: "fa-link", description: "Link to another record" },
                { type: "one2many", label: "Related List", icon: "fa-list-ul", description: "Related records" },
                { type: "many2many", label: "Tags", icon: "fa-tags", description: "Multiple links" },
                { type: "binary", label: "File", icon: "fa-file", description: "File attachment" },
                { type: "image", label: "Image", icon: "fa-image", description: "Image with preview" },
            ];
        }

        /**
         * Get existing fields for a model.
         * @param {number} modelId - ir.model ID
         * @returns {Promise<Array>}
         */
        async function getExistingFields(modelId) {
            const fields = await orm.searchRead(
                "ir.model.fields",
                [["model_id", "=", modelId]],
                ["id", "name", "field_description", "ttype", "state"]
            );
            return fields;
        }

        /**
         * Add a field to a view.
         * @param {Object} params - Field parameters
         * @returns {Promise<Object>}
         */
        async function addFieldToView({ model, viewType, field, position, afterField }) {
            // Create field if needed
            let fieldId = field.existingFieldId;

            if (!fieldId && field.type) {
                // Create new field
                const newField = await orm.create("ir.model.fields", [{
                    model_id: field.modelId,
                    name: `x_${field.name}`,
                    field_description: field.label,
                    ttype: field.type,
                    state: "manual",
                    required: field.required || false,
                    ...getFieldTypeAttrs(field),
                }]);
                fieldId = newField[0];
            }

            // Add to view
            const result = await orm.call(
                "studio.view.customization",
                "add_field_to_view",
                [model, viewType, fieldId, position, afterField]
            );

            if (result) {
                notification.add("Field added successfully", { type: "success" });
                env.bus.trigger("STUDIO:VIEW_UPDATED", { model, viewType });
            }

            return result;
        }

        /**
         * Get type-specific field attributes.
         * @param {Object} field - Field definition
         * @returns {Object}
         */
        function getFieldTypeAttrs(field) {
            const attrs = {};
            switch (field.type) {
                case "selection":
                    if (field.selection) {
                        attrs.selection_ids = field.selection.map((opt, idx) => [
                            0, 0, { value: opt[0], name: opt[1], sequence: idx * 10 }
                        ]);
                    }
                    break;
                case "many2one":
                case "many2many":
                    if (field.relation) {
                        attrs.relation = field.relation;
                    }
                    break;
                case "one2many":
                    if (field.relation) {
                        attrs.relation = field.relation;
                        attrs.relation_field = field.relationField;
                    }
                    break;
            }
            return attrs;
        }

        /**
         * Remove a field from a view.
         * @param {string} model - Model name
         * @param {string} viewType - View type
         * @param {string} fieldName - Field to remove
         * @returns {Promise<void>}
         */
        async function removeFieldFromView(model, viewType, fieldName) {
            await orm.call(
                "studio.view.customization",
                "remove_list_column",
                [model, fieldName]
            );
            notification.add("Field removed", { type: "success" });
            env.bus.trigger("STUDIO:VIEW_UPDATED", { model, viewType });
        }

        /**
         * Reorder fields in a view.
         * @param {string} model - Model name
         * @param {string} viewType - View type
         * @param {Array<string>} fieldOrder - Fields in desired order
         * @returns {Promise<void>}
         */
        async function reorderFields(model, viewType, fieldOrder) {
            const customization = await orm.searchRead(
                "studio.view.customization",
                [["model_name", "=", model], ["view_type", "=", viewType]],
                ["id"],
                { limit: 1 }
            );

            if (customization.length) {
                await orm.call(
                    "studio.view.customization",
                    "reorder_fields",
                    [[customization[0].id], fieldOrder]
                );
                env.bus.trigger("STUDIO:VIEW_UPDATED", { model, viewType });
            }
        }

        /**
         * Create a new Studio app.
         * @param {Object} appData - App definition
         * @returns {Promise<number>} - Created app ID
         */
        async function createApp(appData) {
            const appId = await orm.create("studio.app", [appData]);
            notification.add(`App "${appData.name}" created`, { type: "success" });
            return appId[0];
        }

        /**
         * Create a model in an app.
         * @param {number} appId - App ID
         * @param {Object} modelData - Model definition
         * @returns {Promise<Object>}
         */
        async function createModelInApp(appId, modelData) {
            const result = await orm.call(
                "studio.app",
                "action_create_model",
                [[appId], modelData]
            );
            notification.add(`Model "${modelData.name}" created`, { type: "success" });
            return result;
        }

        /**
         * Open the Studio visual builder.
         * @param {number} appId - App ID to edit
         */
        function openBuilder(appId) {
            action.doAction({
                type: "ir.actions.client",
                tag: "loomworks_studio_builder",
                params: { app_id: appId },
            });
        }

        return {
            // Access control
            hasAccess: checkAccess,

            // Edit mode
            enterEditMode,
            exitEditMode,
            isInEditMode,
            getEditSession,

            // Data retrieval
            getModelInfo,
            getFieldTypes,
            getExistingFields,

            // View customization
            addFieldToView,
            removeFieldFromView,
            reorderFields,

            // App management
            createApp,
            createModelInApp,
            openBuilder,
        };
    },
};

registry.category("services").add("studio", studioService);
