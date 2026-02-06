/** @loomworks-module **/
// Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
// License: LGPL-3

/**
 * AI Suggestion Engine Service
 *
 * Generates proactive suggestions based on user context.
 * Respects throttling, priority levels, and user preferences.
 *
 * Suggestion priorities:
 * - critical: Urgent issues like errors or overdue payments
 * - helpful: Useful suggestions that improve workflow
 * - info: Informational tips
 *
 * Based on: FEATURE_CONTEXTUAL_AI_NAVBAR.md
 */

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export const aiSuggestionService = {
    dependencies: ["aiContext", "orm", "notification"],

    start(env, { aiContext, orm, notification }) {
        // Note: aiContext is our custom service, orm and notification are Odoo 18 services
        // Active suggestions
        let activeSuggestions = [];
        let suggestionIdCounter = 0;

        // Registered triggers
        const triggers = new Map();

        // ==========================================
        // PUBLIC API
        // ==========================================

        const service = {
            /**
             * Get active suggestions
             */
            getSuggestions() {
                return [...activeSuggestions];
            },

            /**
             * Dismiss a suggestion
             */
            dismissSuggestion(id) {
                const index = activeSuggestions.findIndex(s => s.id === id);
                if (index > -1) {
                    activeSuggestions.splice(index, 1);
                    env.bus.trigger("AI_SUGGESTIONS:UPDATED", this.getSuggestions());
                }
            },

            /**
             * Accept a suggestion (execute its action)
             */
            async acceptSuggestion(id) {
                const suggestion = activeSuggestions.find(s => s.id === id);
                if (!suggestion) return;

                try {
                    if (suggestion.action) {
                        await this._executeAction(suggestion.action);
                    }
                    this.dismissSuggestion(id);
                } catch (error) {
                    console.error("Failed to execute suggestion:", error);
                    notification.add(_t("Failed to execute suggestion"), {
                        type: "danger",
                    });
                }
            },

            /**
             * Add a suggestion manually
             */
            addSuggestion(suggestion) {
                this._addSuggestion(suggestion);
            },

            /**
             * Register a suggestion trigger
             *
             * @param {string} name - Unique trigger name
             * @param {object} config - Trigger configuration
             * @param {function} config.condition - Function(context) -> boolean
             * @param {function} config.generate - Async function(context) -> suggestion or null
             * @param {string} config.priority - 'critical', 'helpful', or 'info'
             * @param {number} config.cooldownMs - Minimum time between trigger activations
             */
            registerTrigger(name, config) {
                triggers.set(name, {
                    name,
                    condition: config.condition,
                    generate: config.generate,
                    priority: config.priority || 'helpful',
                    cooldownMs: config.cooldownMs || 60000,
                    lastTriggered: 0,
                });
            },

            /**
             * Unregister a trigger
             */
            unregisterTrigger(name) {
                triggers.delete(name);
            },

            /**
             * Analyze context and generate suggestions
             * Called when AI_CONTEXT:ANALYZE event fires
             */
            async analyzeAndSuggest(trigger, context) {
                if (!aiContext.canShowSuggestion()) return;

                const now = Date.now();

                for (const [name, triggerConfig] of triggers) {
                    // Check cooldown
                    if (now - triggerConfig.lastTriggered < triggerConfig.cooldownMs) {
                        continue;
                    }

                    // Check condition
                    try {
                        if (!triggerConfig.condition(context)) {
                            continue;
                        }
                    } catch (error) {
                        console.warn(`Trigger condition error (${name}):`, error);
                        continue;
                    }

                    // Generate suggestion
                    try {
                        const suggestion = await triggerConfig.generate(context);
                        if (suggestion) {
                            this._addSuggestion({
                                ...suggestion,
                                source: name,
                                priority: triggerConfig.priority,
                            });
                            triggerConfig.lastTriggered = now;
                            aiContext.recordSuggestionShown();

                            // Only add one suggestion per analysis cycle
                            break;
                        }
                    } catch (error) {
                        console.warn(`Trigger generation error (${name}):`, error);
                    }
                }
            },

            /**
             * Clear all suggestions
             */
            clearAll() {
                activeSuggestions = [];
                env.bus.trigger("AI_SUGGESTIONS:UPDATED", []);
            },

            /**
             * Get critical suggestion count (for badge)
             */
            getCriticalCount() {
                return activeSuggestions.filter(s => s.priority === 'critical').length;
            },

            // ==========================================
            // PRIVATE METHODS
            // ==========================================

            _addSuggestion(suggestion) {
                const id = ++suggestionIdCounter;
                const settings = aiContext.getSettings();

                const newSuggestion = {
                    id,
                    title: suggestion.title,
                    description: suggestion.description,
                    priority: suggestion.priority || 'helpful',
                    action: suggestion.action,
                    source: suggestion.source,
                    autoDismissMs: suggestion.autoDismissMs ||
                        (settings.notificationStyle === 'badge' ? null : 8000),
                    createdAt: Date.now(),
                };

                // Add to list (sorted by priority)
                activeSuggestions.push(newSuggestion);
                activeSuggestions.sort((a, b) => {
                    const priorityOrder = { critical: 0, helpful: 1, info: 2 };
                    return (priorityOrder[a.priority] || 2) - (priorityOrder[b.priority] || 2);
                });

                // Limit active suggestions
                if (activeSuggestions.length > 10) {
                    activeSuggestions = activeSuggestions.slice(0, 10);
                }

                env.bus.trigger("AI_SUGGESTIONS:UPDATED", this.getSuggestions());

                // Show notification if configured
                if (settings.notificationStyle === 'popup') {
                    const notifType = newSuggestion.priority === 'critical' ? 'warning' : 'info';
                    notification.add(newSuggestion.title, {
                        type: notifType,
                        sticky: newSuggestion.priority === 'critical',
                    });
                }

                // Auto-dismiss if configured
                if (newSuggestion.autoDismissMs && newSuggestion.priority !== 'critical') {
                    setTimeout(() => {
                        this.dismissSuggestion(id);
                    }, newSuggestion.autoDismissMs);
                }
            },

            async _executeAction(action) {
                switch (action.type) {
                    case 'navigate':
                        await env.services.action.doAction(action.actionId);
                        break;

                    case 'open_record':
                        await env.services.action.doAction({
                            type: 'ir.actions.act_window',
                            res_model: action.model,
                            res_id: action.resId,
                            views: [[false, 'form']],
                        });
                        break;

                    case 'run_action':
                        await orm.call(action.model, action.method, action.args || []);
                        break;

                    case 'show_dialog':
                        env.services.dialog.add(action.component, action.props);
                        break;

                    case 'ask_ai':
                        env.bus.trigger("AI:OPEN_CHAT", { query: action.query });
                        break;

                    case 'url':
                        window.open(action.url, action.target || '_blank');
                        break;

                    default:
                        console.warn('Unknown suggestion action type:', action.type);
                }
            },
        };

        // ==========================================
        // REGISTER DEFAULT TRIGGERS
        // ==========================================

        // Trigger: User seems stuck (idle on view)
        service.registerTrigger('user_stuck', {
            condition: (ctx) => ctx.timeOnViewSeconds > 30 && !ctx.hasUnsavedChanges,
            generate: async (ctx) => ({
                title: _t("Need help getting started?"),
                description: _t("I can help you with this %s", ctx.model || 'view'),
                action: { type: 'ask_ai', query: `Help me with ${ctx.model || 'this'}` },
            }),
            priority: 'helpful',
            cooldownMs: 120000, // 2 minutes
        });

        // Trigger: Empty search results
        service.registerTrigger('empty_search', {
            condition: (ctx) =>
                ctx.recentActionTypes.includes('search_performed') &&
                ctx.searchResultCount === 0,
            generate: async (ctx) => ({
                title: _t("No results found"),
                description: _t("Try a broader search or let me help find what you need"),
                action: { type: 'ask_ai', query: `Help me search for ${ctx.searchQuery || 'records'}` },
            }),
            priority: 'helpful',
            cooldownMs: 60000,
        });

        // Trigger: Error encountered
        service.registerTrigger('error_recovery', {
            condition: (ctx) => ctx.lastErrorType !== null,
            generate: async (ctx) => ({
                title: _t("I can help with that error"),
                description: _t("Let me help you resolve this issue"),
                action: { type: 'ask_ai', query: `Help me fix error: ${ctx.lastErrorType}` },
            }),
            priority: 'critical',
            cooldownMs: 30000,
        });

        // Trigger: New sales order - check customer status
        service.registerTrigger('customer_context', {
            condition: (ctx) =>
                ctx.model === 'sale.order' &&
                ctx.recordId &&
                ctx.recentActionTypes.includes('record_selected'),
            generate: async (ctx) => {
                try {
                    // Check for overdue invoices
                    const overdueInfo = await orm.call(
                        'sale.order',
                        'get_partner_overdue_summary',
                        [[ctx.recordId]]
                    );

                    if (overdueInfo?.total > 0) {
                        return {
                            title: _t("Customer has overdue balance"),
                            description: _t("Outstanding: %s", overdueInfo.formattedTotal || overdueInfo.total),
                            action: {
                                type: 'ask_ai',
                                query: 'Show me this customer\'s overdue invoices',
                            },
                        };
                    }
                } catch (error) {
                    // API may not exist, ignore
                }
                return null;
            },
            priority: 'critical',
            cooldownMs: 300000, // 5 minutes
        });

        // Trigger: Inventory low stock warning
        service.registerTrigger('low_stock_warning', {
            condition: (ctx) =>
                (ctx.model === 'product.product' || ctx.model === 'product.template') &&
                ctx.recordId,
            generate: async (ctx) => {
                try {
                    const stockInfo = await orm.call(
                        'product.product',
                        'get_stock_level',
                        [[ctx.recordId]]
                    );

                    if (stockInfo?.is_low_stock) {
                        return {
                            title: _t("Low stock alert"),
                            description: _t("Only %s units available", stockInfo.quantity),
                            action: {
                                type: 'ask_ai',
                                query: 'Help me create a purchase order for this product',
                            },
                        };
                    }
                } catch (error) {
                    // API may not exist, ignore
                }
                return null;
            },
            priority: 'helpful',
            cooldownMs: 180000, // 3 minutes
        });

        // Trigger: Task overdue
        service.registerTrigger('task_overdue', {
            condition: (ctx) =>
                ctx.model === 'project.task' &&
                ctx.recordId &&
                ctx.recordState === 'in_progress',
            generate: async (ctx) => {
                try {
                    const taskInfo = await orm.call(
                        'project.task',
                        'read',
                        [[ctx.recordId], ['date_deadline', 'name']]
                    );

                    if (taskInfo?.[0]?.date_deadline) {
                        const deadline = new Date(taskInfo[0].date_deadline);
                        if (deadline < new Date()) {
                            return {
                                title: _t("Task is overdue"),
                                description: _t("Deadline was %s", deadline.toLocaleDateString()),
                                action: {
                                    type: 'ask_ai',
                                    query: 'Help me reschedule or complete this task',
                                },
                            };
                        }
                    }
                } catch (error) {
                    // Ignore
                }
                return null;
            },
            priority: 'helpful',
            cooldownMs: 300000,
        });

        // Subscribe to context analysis events
        env.bus.addEventListener("AI_CONTEXT:ANALYZE", async (ev) => {
            const { trigger, context } = ev.detail;
            await service.analyzeAndSuggest(trigger, context);
        });

        return service;
    },
};

registry.category("services").add("aiSuggestion", aiSuggestionService);
