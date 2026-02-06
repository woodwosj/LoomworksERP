/** @loomworks-module **/
/**
 * Odoo Data Plugin for Univer
 *
 * Extends Univer with Odoo-specific functionality:
 * - Data source connections
 * - Live data formulas (ODOO.DATA, ODOO.PIVOT, etc.)
 * - Automatic refresh capabilities
 */

import { registry } from "@web/core/registry";

/**
 * Custom function definitions for Odoo data access.
 */
export const OdooFunctions = {
    /**
     * ODOO.DATA - Fetch data from an Odoo model
     * Usage: =ODOO.DATA("res.partner", "name", "[('active', '=', True)]", 10)
     */
    "ODOO.DATA": {
        name: "ODOO.DATA",
        description: "Fetch data from an Odoo model",
        parameters: [
            { name: "model", description: "Model name (e.g., 'res.partner')" },
            { name: "field", description: "Field name to fetch" },
            { name: "domain", description: "Filter domain (optional)", optional: true },
            { name: "limit", description: "Maximum records (optional)", optional: true },
        ],
        async execute(model, field, domain = "[]", limit = 100) {
            try {
                const rpc = window.__odoo_rpc__;
                if (!rpc) {
                    return "#ERROR: RPC not available";
                }

                const result = await rpc("/spreadsheet/datasource/preview", {
                    model,
                    fields: [field],
                    domain,
                    limit,
                });

                if (result.error) {
                    return `#ERROR: ${result.error}`;
                }

                // Return as array for spilling
                return result.rows.map(row => row[0]);
            } catch (error) {
                return `#ERROR: ${error.message}`;
            }
        },
    },

    /**
     * ODOO.FIELD - Get a single field value from a record
     * Usage: =ODOO.FIELD("res.partner", 1, "name")
     */
    "ODOO.FIELD": {
        name: "ODOO.FIELD",
        description: "Get a field value from a specific record",
        parameters: [
            { name: "model", description: "Model name" },
            { name: "id", description: "Record ID" },
            { name: "field", description: "Field name" },
        ],
        async execute(model, id, field) {
            try {
                const rpc = window.__odoo_rpc__;
                if (!rpc) {
                    return "#ERROR: RPC not available";
                }

                const result = await rpc("/web/dataset/call_kw", {
                    model,
                    method: "read",
                    args: [[id], [field]],
                    kwargs: {},
                });

                if (!result || !result.length) {
                    return "#NOT_FOUND";
                }

                const value = result[0][field];
                if (Array.isArray(value) && value.length === 2) {
                    return value[1]; // Return display name for many2one
                }
                return value;
            } catch (error) {
                return `#ERROR: ${error.message}`;
            }
        },
    },

    /**
     * ODOO.COUNT - Count records in a model
     * Usage: =ODOO.COUNT("res.partner", "[('active', '=', True)]")
     */
    "ODOO.COUNT": {
        name: "ODOO.COUNT",
        description: "Count records matching a domain",
        parameters: [
            { name: "model", description: "Model name" },
            { name: "domain", description: "Filter domain (optional)", optional: true },
        ],
        async execute(model, domain = "[]") {
            try {
                const rpc = window.__odoo_rpc__;
                if (!rpc) {
                    return "#ERROR: RPC not available";
                }

                const result = await rpc("/web/dataset/call_kw", {
                    model,
                    method: "search_count",
                    args: [JSON.parse(domain)],
                    kwargs: {},
                });

                return result;
            } catch (error) {
                return `#ERROR: ${error.message}`;
            }
        },
    },

    /**
     * ODOO.SUM - Sum a field across records
     * Usage: =ODOO.SUM("account.move.line", "debit", "[('parent_state', '=', 'posted')]")
     */
    "ODOO.SUM": {
        name: "ODOO.SUM",
        description: "Sum a numeric field across records",
        parameters: [
            { name: "model", description: "Model name" },
            { name: "field", description: "Numeric field to sum" },
            { name: "domain", description: "Filter domain (optional)", optional: true },
        ],
        async execute(model, field, domain = "[]") {
            try {
                const rpc = window.__odoo_rpc__;
                if (!rpc) {
                    return "#ERROR: RPC not available";
                }

                const result = await rpc("/web/dataset/call_kw", {
                    model,
                    method: "read_group",
                    args: [JSON.parse(domain), [`${field}:sum`], []],
                    kwargs: {},
                });

                if (!result || !result.length) {
                    return 0;
                }

                return result[0][field] || 0;
            } catch (error) {
                return `#ERROR: ${error.message}`;
            }
        },
    },

    /**
     * ODOO.AVG - Average a field across records
     * Usage: =ODOO.AVG("sale.order", "amount_total", "[('state', '=', 'sale')]")
     */
    "ODOO.AVG": {
        name: "ODOO.AVG",
        description: "Average a numeric field across records",
        parameters: [
            { name: "model", description: "Model name" },
            { name: "field", description: "Numeric field to average" },
            { name: "domain", description: "Filter domain (optional)", optional: true },
        ],
        async execute(model, field, domain = "[]") {
            try {
                const rpc = window.__odoo_rpc__;
                if (!rpc) {
                    return "#ERROR: RPC not available";
                }

                const result = await rpc("/web/dataset/call_kw", {
                    model,
                    method: "read_group",
                    args: [JSON.parse(domain), [`${field}:avg`], []],
                    kwargs: {},
                });

                if (!result || !result.length) {
                    return 0;
                }

                return result[0][field] || 0;
            } catch (error) {
                return `#ERROR: ${error.message}`;
            }
        },
    },

    /**
     * ODOO.PIVOT - Get value from a pivot table
     * Usage: =ODOO.PIVOT(pivot_id, "measure", row_value, col_value)
     */
    "ODOO.PIVOT": {
        name: "ODOO.PIVOT",
        description: "Get a value from an Odoo pivot table",
        parameters: [
            { name: "pivot_id", description: "Pivot table ID" },
            { name: "measure", description: "Measure field name" },
            { name: "row_value", description: "Row grouping value (optional)", optional: true },
            { name: "col_value", description: "Column grouping value (optional)", optional: true },
        ],
        async execute(pivotId, measure, rowValue = null, colValue = null) {
            try {
                const rpc = window.__odoo_rpc__;
                if (!rpc) {
                    return "#ERROR: RPC not available";
                }

                const result = await rpc("/spreadsheet/pivot/" + pivotId + "/compute", {});

                if (result.error) {
                    return `#ERROR: ${result.error}`;
                }

                const pivotData = result.data;

                // Find the cell value
                if (!rowValue && !colValue) {
                    // Grand total
                    return pivotData.totals?.grand?.[measure] || 0;
                }

                // Find row index
                let rowIdx = null;
                if (rowValue) {
                    rowIdx = pivotData.rows.values.findIndex(v =>
                        v.includes(rowValue) || v[0] === rowValue
                    );
                }

                // Find column index
                let colIdx = 0;
                if (colValue) {
                    colIdx = pivotData.columns.values.findIndex(v =>
                        v.includes(colValue) || v[0] === colValue
                    );
                }

                if (rowIdx === null || rowIdx === -1) {
                    return "#NOT_FOUND";
                }

                const cellKey = `${rowIdx},${colIdx}`;
                return pivotData.data[cellKey]?.[measure] || 0;
            } catch (error) {
                return `#ERROR: ${error.message}`;
            }
        },
    },
};

/**
 * Register Odoo formulas with Univer.
 * Call this after Univer is initialized.
 */
export function registerOdooFormulas(univerInstance) {
    if (!univerInstance) {
        console.warn("Cannot register Odoo formulas: Univer not initialized");
        return;
    }

    try {
        const formulaService = univerInstance.__getInjector().get("IFormulaService");

        Object.entries(OdooFunctions).forEach(([name, definition]) => {
            try {
                formulaService.registerFunction({
                    name: definition.name,
                    description: definition.description,
                    abstract: definition.description,
                    functionParameter: definition.parameters.map(p => ({
                        name: p.name,
                        detail: p.description,
                        example: "",
                        require: !p.optional,
                    })),
                    calculate: async (...args) => {
                        return await definition.execute(...args);
                    },
                });
                console.log(`Registered Odoo formula: ${name}`);
            } catch (error) {
                console.warn(`Failed to register formula ${name}:`, error);
            }
        });
    } catch (error) {
        console.warn("Failed to register Odoo formulas:", error);
    }
}

/**
 * Data Source Manager - Manages live data connections.
 */
export class DataSourceManager {
    constructor(univerWrapper) {
        this.univerWrapper = univerWrapper;
        this.dataSources = new Map();
        this.refreshTimers = new Map();
    }

    /**
     * Add a data source.
     * @param {Object} config - Data source configuration
     */
    addDataSource(config) {
        const id = config.id || "ds_" + Date.now();
        this.dataSources.set(id, config);

        // Set up auto-refresh if configured
        if (config.autoRefresh && config.refreshInterval) {
            this.setupAutoRefresh(id, config.refreshInterval);
        }

        return id;
    }

    /**
     * Remove a data source.
     * @param {string} id - Data source ID
     */
    removeDataSource(id) {
        this.dataSources.delete(id);
        this.clearAutoRefresh(id);
    }

    /**
     * Refresh a data source.
     * @param {string} id - Data source ID
     */
    async refreshDataSource(id) {
        const config = this.dataSources.get(id);
        if (!config) return;

        try {
            const rpc = window.__odoo_rpc__;
            const result = await rpc(`/spreadsheet/datasource/${config.sourceId}/fetch`, {
                limit: config.limit,
            });

            if (result.success && result.data) {
                this.univerWrapper.insertOdooData(
                    result.data,
                    config.sheetId,
                    config.startRow,
                    config.startCol,
                    config.includeHeaders
                );
            }
        } catch (error) {
            console.error(`Failed to refresh data source ${id}:`, error);
        }
    }

    /**
     * Set up auto-refresh for a data source.
     * @param {string} id - Data source ID
     * @param {number} interval - Refresh interval in milliseconds
     */
    setupAutoRefresh(id, interval) {
        this.clearAutoRefresh(id);
        const timer = setInterval(() => this.refreshDataSource(id), interval);
        this.refreshTimers.set(id, timer);
    }

    /**
     * Clear auto-refresh timer.
     * @param {string} id - Data source ID
     */
    clearAutoRefresh(id) {
        const timer = this.refreshTimers.get(id);
        if (timer) {
            clearInterval(timer);
            this.refreshTimers.delete(id);
        }
    }

    /**
     * Refresh all data sources.
     */
    async refreshAll() {
        const promises = Array.from(this.dataSources.keys()).map(id =>
            this.refreshDataSource(id)
        );
        await Promise.all(promises);
    }

    /**
     * Dispose all timers.
     */
    dispose() {
        this.refreshTimers.forEach((timer, id) => {
            clearInterval(timer);
        });
        this.refreshTimers.clear();
        this.dataSources.clear();
    }
}
