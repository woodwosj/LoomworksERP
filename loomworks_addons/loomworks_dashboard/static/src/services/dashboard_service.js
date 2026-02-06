/** @loomworks-module **/
/**
 * Dashboard Service
 *
 * Provides dashboard-related functionality to Owl components:
 * - Dashboard CRUD operations
 * - Widget data fetching
 * - Template management
 * - Caching
 */

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export const dashboardService = {
    dependencies: ["notification"],

    start(env, { notification }) {
        // Cache for dashboard data
        const cache = new Map();
        const CACHE_TTL = 60000; // 1 minute

        /**
         * Get cached data or fetch from server
         */
        function getCached(key) {
            const cached = cache.get(key);
            if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
                return cached.data;
            }
            return null;
        }

        /**
         * Set cache data
         */
        function setCache(key, data) {
            cache.set(key, { data, timestamp: Date.now() });
        }

        /**
         * Clear cache
         */
        function clearCache(keyPrefix = null) {
            if (keyPrefix) {
                for (const key of cache.keys()) {
                    if (key.startsWith(keyPrefix)) {
                        cache.delete(key);
                    }
                }
            } else {
                cache.clear();
            }
        }

        return {
            /**
             * Load a dashboard by ID
             */
            async loadDashboard(dashboardId, useCache = true) {
                const cacheKey = `dashboard_${dashboardId}`;

                if (useCache) {
                    const cached = getCached(cacheKey);
                    if (cached) return cached;
                }

                try {
                    const data = await rpc("/loomworks/dashboard/" + dashboardId);
                    if (!data.error) {
                        setCache(cacheKey, data);
                    }
                    return data;
                } catch (error) {
                    notification.add("Failed to load dashboard: " + error.message, {
                        type: "danger",
                    });
                    throw error;
                }
            },

            /**
             * Create a new dashboard
             */
            async createDashboard(name, options = {}) {
                try {
                    const data = await rpc("/loomworks/dashboard/create", {
                        name,
                        description: options.description,
                        layout_columns: options.layoutColumns || 12,
                        auto_refresh: options.autoRefresh || 0,
                        template_id: options.templateId,
                    });

                    if (data.error) {
                        throw new Error(data.error);
                    }

                    return data;
                } catch (error) {
                    notification.add("Failed to create dashboard: " + error.message, {
                        type: "danger",
                    });
                    throw error;
                }
            },

            /**
             * Save dashboard state
             */
            async saveDashboard(dashboardId, canvasData) {
                try {
                    const data = await rpc(
                        "/loomworks/dashboard/" + dashboardId + "/save",
                        canvasData
                    );

                    if (data.error) {
                        throw new Error(data.error);
                    }

                    // Invalidate cache
                    clearCache(`dashboard_${dashboardId}`);

                    return data;
                } catch (error) {
                    notification.add("Failed to save dashboard: " + error.message, {
                        type: "danger",
                    });
                    throw error;
                }
            },

            /**
             * Delete a dashboard
             */
            async deleteDashboard(dashboardId) {
                try {
                    const data = await rpc(
                        "/loomworks/dashboard/" + dashboardId + "/delete"
                    );

                    if (data.error) {
                        throw new Error(data.error);
                    }

                    // Clear cache
                    clearCache(`dashboard_${dashboardId}`);

                    return data;
                } catch (error) {
                    notification.add("Failed to delete dashboard: " + error.message, {
                        type: "danger",
                    });
                    throw error;
                }
            },

            /**
             * Add a widget to a dashboard
             */
            async addWidget(dashboardId, widgetConfig) {
                try {
                    const data = await rpc(
                        "/loomworks/dashboard/" + dashboardId + "/widget",
                        widgetConfig
                    );

                    if (data.error) {
                        throw new Error(data.error);
                    }

                    // Invalidate dashboard cache
                    clearCache(`dashboard_${dashboardId}`);

                    return data;
                } catch (error) {
                    notification.add("Failed to add widget: " + error.message, {
                        type: "danger",
                    });
                    throw error;
                }
            },

            /**
             * Update a widget
             */
            async updateWidget(widgetId, widgetConfig) {
                try {
                    const data = await rpc(
                        "/loomworks/dashboard/widget/" + widgetId,
                        widgetConfig
                    );

                    if (data.error) {
                        throw new Error(data.error);
                    }

                    return data;
                } catch (error) {
                    notification.add("Failed to update widget: " + error.message, {
                        type: "danger",
                    });
                    throw error;
                }
            },

            /**
             * Delete a widget
             */
            async deleteWidget(widgetId) {
                try {
                    const data = await rpc(
                        "/loomworks/dashboard/widget/" + widgetId,
                        {},
                        { method: "DELETE" }
                    );

                    if (data.error) {
                        throw new Error(data.error);
                    }

                    return data;
                } catch (error) {
                    notification.add("Failed to delete widget: " + error.message, {
                        type: "danger",
                    });
                    throw error;
                }
            },

            /**
             * Fetch widget data
             */
            async fetchWidgetData(widgetId, filters = {}) {
                try {
                    const data = await rpc(
                        "/loomworks/dashboard/widget/" + widgetId + "/data",
                        { filters }
                    );

                    if (data.error) {
                        throw new Error(data.error);
                    }

                    return data.data;
                } catch (error) {
                    console.error("Failed to fetch widget data:", error);
                    return null;
                }
            },

            /**
             * Fetch data source
             */
            async fetchDataSource(sourceId, filters = {}) {
                try {
                    const data = await rpc(
                        "/loomworks/dashboard/data/" + sourceId,
                        { filters }
                    );

                    if (data.error) {
                        throw new Error(data.error);
                    }

                    return data.data;
                } catch (error) {
                    console.error("Failed to fetch data source:", error);
                    return null;
                }
            },

            /**
             * Generate dashboard from AI prompt
             */
            async generateFromPrompt(prompt, name = null) {
                try {
                    const data = await rpc("/loomworks/dashboard/generate", {
                        prompt,
                        name,
                    });

                    if (data.error) {
                        throw new Error(data.error);
                    }

                    notification.add(
                        `Dashboard generated with ${data.widget_count || 0} widgets`,
                        { type: "success" }
                    );

                    return data;
                } catch (error) {
                    notification.add("Failed to generate dashboard: " + error.message, {
                        type: "danger",
                    });
                    throw error;
                }
            },

            /**
             * Get available templates
             */
            async getTemplates() {
                const cacheKey = "templates";
                const cached = getCached(cacheKey);
                if (cached) return cached;

                try {
                    const data = await rpc("/loomworks/dashboard/templates");
                    setCache(cacheKey, data.templates);
                    return data.templates;
                } catch (error) {
                    console.error("Failed to fetch templates:", error);
                    return [];
                }
            },

            /**
             * Get available Odoo models for data sources
             */
            async getAvailableModels() {
                const cacheKey = "models";
                const cached = getCached(cacheKey);
                if (cached) return cached;

                try {
                    const data = await rpc("/loomworks/dashboard/models");
                    setCache(cacheKey, data.models);
                    return data.models;
                } catch (error) {
                    console.error("Failed to fetch models:", error);
                    return [];
                }
            },

            /**
             * Get fields for a model
             */
            async getModelFields(modelName) {
                const cacheKey = `model_fields_${modelName}`;
                const cached = getCached(cacheKey);
                if (cached) return cached;

                try {
                    const data = await rpc(
                        "/loomworks/dashboard/model/" + modelName + "/fields"
                    );
                    if (!data.error) {
                        setCache(cacheKey, data.fields);
                    }
                    return data.fields || [];
                } catch (error) {
                    console.error("Failed to fetch model fields:", error);
                    return [];
                }
            },

            /**
             * Share a dashboard
             */
            async shareDashboard(dashboardId, shareConfig) {
                try {
                    const data = await rpc(
                        "/loomworks/dashboard/" + dashboardId + "/share",
                        shareConfig
                    );

                    if (data.error) {
                        throw new Error(data.error);
                    }

                    return data;
                } catch (error) {
                    notification.add("Failed to share dashboard: " + error.message, {
                        type: "danger",
                    });
                    throw error;
                }
            },

            /**
             * Clear all cache
             */
            clearCache,
        };
    },
};

registry.category("services").add("dashboard", dashboardService);
