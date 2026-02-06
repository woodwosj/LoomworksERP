/** @odoo-module **/
/**
 * Loomworks Spreadsheet Service
 *
 * Provides centralized state management and API access for spreadsheets.
 * Handles document operations, data source fetching, and collaboration.
 */

import { registry } from "@web/core/registry";
import { reactive } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";

const serviceRegistry = registry.category("services");

export const spreadsheetService = {
    dependencies: ["orm", "notification"],

    start(env, { orm, notification }) {
        // Reactive state for active spreadsheet
        const state = reactive({
            activeDocumentId: null,
            activeDocument: null,
            isLoading: false,
            isSaving: false,
            isDirty: false,
            lastSaved: null,
            collaborators: [],
        });

        // Cache for loaded documents
        const documentCache = new Map();

        /**
         * Load a spreadsheet document.
         * @param {number} documentId - Document ID
         * @returns {Promise<Object>} Document data
         */
        async function loadDocument(documentId) {
            if (documentCache.has(documentId)) {
                const cached = documentCache.get(documentId);
                if (Date.now() - cached.loadedAt < 60000) {
                    state.activeDocumentId = documentId;
                    state.activeDocument = cached.data;
                    return cached.data;
                }
            }

            state.isLoading = true;
            try {
                const result = await orm.call(
                    "spreadsheet.document",
                    "get_data_for_univer",
                    [[documentId]]
                );

                const doc = {
                    id: documentId,
                    data: result,
                };

                documentCache.set(documentId, {
                    data: doc,
                    loadedAt: Date.now(),
                });

                state.activeDocumentId = documentId;
                state.activeDocument = doc;
                state.isDirty = false;

                return doc;
            } catch (error) {
                notification.add(`Failed to load spreadsheet: ${error.message}`, {
                    type: "danger",
                });
                throw error;
            } finally {
                state.isLoading = false;
            }
        }

        /**
         * Save spreadsheet data.
         * @param {number} documentId - Document ID
         * @param {Object} data - Univer workbook data
         * @returns {Promise<boolean>} Success
         */
        async function saveDocument(documentId, data) {
            state.isSaving = true;
            try {
                await orm.call(
                    "spreadsheet.document",
                    "save_from_univer",
                    [[documentId], data]
                );

                state.isDirty = false;
                state.lastSaved = new Date();

                // Update cache
                if (documentCache.has(documentId)) {
                    const cached = documentCache.get(documentId);
                    cached.data.data = data;
                    cached.loadedAt = Date.now();
                }

                notification.add("Spreadsheet saved", {
                    type: "success",
                    sticky: false,
                });

                return true;
            } catch (error) {
                notification.add(`Failed to save spreadsheet: ${error.message}`, {
                    type: "danger",
                });
                throw error;
            } finally {
                state.isSaving = false;
            }
        }

        /**
         * Create a new spreadsheet document.
         * @param {string} name - Document name
         * @param {Object} options - Additional options
         * @returns {Promise<Object>} Created document
         */
        async function createDocument(name, options = {}) {
            try {
                const vals = {
                    name,
                    description: options.description || "",
                };

                const id = await orm.create("spreadsheet.document", [vals]);

                notification.add(`Spreadsheet "${name}" created`, {
                    type: "success",
                    sticky: false,
                });

                return { id, name };
            } catch (error) {
                notification.add(`Failed to create spreadsheet: ${error.message}`, {
                    type: "danger",
                });
                throw error;
            }
        }

        /**
         * Fetch data from a data source.
         * @param {number} sourceId - Data source ID
         * @param {number} limit - Record limit
         * @returns {Promise<Object>} Data with headers and rows
         */
        async function fetchDataSource(sourceId, limit = null) {
            try {
                const data = await orm.call(
                    "spreadsheet.data.source",
                    "fetch_data",
                    [[sourceId]],
                    { limit }
                );
                return data;
            } catch (error) {
                notification.add(`Failed to fetch data: ${error.message}`, {
                    type: "danger",
                });
                throw error;
            }
        }

        /**
         * Compute pivot table data.
         * @param {number} pivotId - Pivot ID
         * @returns {Promise<Object>} Pivot data
         */
        async function computePivot(pivotId) {
            try {
                const data = await orm.call(
                    "spreadsheet.pivot",
                    "compute_pivot",
                    [[pivotId]]
                );
                return data;
            } catch (error) {
                notification.add(`Failed to compute pivot: ${error.message}`, {
                    type: "danger",
                });
                throw error;
            }
        }

        /**
         * Get chart data.
         * @param {number} chartId - Chart ID
         * @returns {Promise<Object>} Chart data
         */
        async function getChartData(chartId) {
            try {
                const data = await orm.call(
                    "spreadsheet.chart",
                    "get_chart_data",
                    [[chartId]]
                );
                return data;
            } catch (error) {
                notification.add(`Failed to get chart data: ${error.message}`, {
                    type: "danger",
                });
                throw error;
            }
        }

        /**
         * Get ECharts configuration for a chart.
         * @param {number} chartId - Chart ID
         * @returns {Promise<Object>} ECharts option
         */
        async function getEchartsOption(chartId) {
            try {
                const option = await orm.call(
                    "spreadsheet.chart",
                    "get_echarts_option",
                    [[chartId]]
                );
                return option;
            } catch (error) {
                notification.add(`Failed to get chart config: ${error.message}`, {
                    type: "danger",
                });
                throw error;
            }
        }

        /**
         * Preview data from an Odoo model.
         * @param {string} model - Model name
         * @param {Array} fields - Field names
         * @param {string} domain - Domain filter
         * @param {number} limit - Record limit
         * @returns {Promise<Object>} Preview data
         */
        async function previewModelData(model, fields, domain = "[]", limit = 10) {
            try {
                const result = await rpc("/spreadsheet/datasource/preview", {
                    model,
                    fields,
                    domain,
                    limit,
                });
                return result;
            } catch (error) {
                notification.add(`Failed to preview data: ${error.message}`, {
                    type: "danger",
                });
                throw error;
            }
        }

        /**
         * List available Odoo models.
         * @param {string} search - Search term
         * @returns {Promise<Array>} List of models
         */
        async function listModels(search = null) {
            try {
                const result = await rpc("/spreadsheet/models", {
                    search,
                    limit: 50,
                });
                return result.models || [];
            } catch (error) {
                notification.add(`Failed to list models: ${error.message}`, {
                    type: "danger",
                });
                throw error;
            }
        }

        /**
         * Get fields for a model.
         * @param {string} modelName - Model name
         * @returns {Promise<Array>} List of fields
         */
        async function getModelFields(modelName) {
            try {
                const result = await rpc(
                    `/spreadsheet/model/${modelName}/fields`,
                    {}
                );
                return result.fields || [];
            } catch (error) {
                notification.add(`Failed to get fields: ${error.message}`, {
                    type: "danger",
                });
                throw error;
            }
        }

        /**
         * Mark document as dirty (unsaved changes).
         */
        function markDirty() {
            state.isDirty = true;
        }

        /**
         * Clear document cache.
         * @param {number} documentId - Optional specific document
         */
        function clearCache(documentId = null) {
            if (documentId) {
                documentCache.delete(documentId);
            } else {
                documentCache.clear();
            }
        }

        /**
         * Auto-save handler for debounced saves.
         */
        let autoSaveTimeout = null;
        function scheduleAutoSave(documentId, data, delay = 5000) {
            if (autoSaveTimeout) {
                clearTimeout(autoSaveTimeout);
            }
            autoSaveTimeout = setTimeout(async () => {
                if (state.isDirty) {
                    await saveDocument(documentId, data);
                }
            }, delay);
        }

        return {
            state,
            loadDocument,
            saveDocument,
            createDocument,
            fetchDataSource,
            computePivot,
            getChartData,
            getEchartsOption,
            previewModelData,
            listModels,
            getModelFields,
            markDirty,
            clearCache,
            scheduleAutoSave,
        };
    },
};

serviceRegistry.add("spreadsheet", spreadsheetService);
