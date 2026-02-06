/** @odoo-module **/
// Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
// License: LGPL-3

/**
 * AI Context Detection Service (Event-Driven)
 *
 * Tracks user context for proactive AI suggestions.
 * Only analyzes context when triggered by user actions - NOT through constant polling.
 *
 * Key Principles:
 * - Event-driven, not polling-based
 * - 2.5 second debounce for context updates
 * - Privacy-conscious: only metadata, not actual field values
 *
 * Based on: FEATURE_CONTEXTUAL_AI_NAVBAR.md
 *
 * Context Triggers:
 * - view_loaded: User opens a form/list/kanban view
 * - record_created: User clicks "Create" button
 * - record_selected: User clicks into a record
 * - action_executed: User runs a workflow action
 * - error_occurred: Something failed
 * - idle_threshold: User paused for 10+ seconds
 * - search_performed: User searched for something
 * - tab_switched: User switched browser tab back to Odoo
 */

import { registry } from "@web/core/registry";
import { debounce } from "@web/core/utils/timing";
import { user } from "@web/core/user";

export const aiContextService = {
    dependencies: ["orm", "notification"],

    start(env, { orm, notification }) {
        // Context state - only metadata, not actual values
        let currentContext = {
            // View state
            model: null,
            viewType: null,
            recordId: null,
            recordState: null,
            modifiedFields: [],

            // Action buffer (recent actions for context)
            recentActions: [],
            lastError: null,
            searchQuery: null,
            searchResults: null,

            // State flags
            hasUnsavedChanges: false,
            viewLoadedAt: null,
        };

        // User settings (loaded async)
        let settings = {
            enableSuggestions: true,
            suggestionFrequency: 'normal',
            notificationStyle: 'popup',
            showContextIndicator: true,
            enableQuickActions: true,
            cooldownSeconds: 60,
            maxSuggestionsPerSession: 10,
        };

        // Suggestion tracking
        let suggestionCount = 0;
        let lastSuggestionTime = 0;
        let idleTimer = null;
        const IDLE_THRESHOLD_MS = 10000; // 10 seconds

        // Debounced analysis function (2.5 second delay)
        const debouncedAnalysis = debounce((trigger) => {
            if (!settings.enableSuggestions) return;
            if (!canShowSuggestion()) return;

            // Emit event for suggestion service to handle
            env.bus.trigger("AI_CONTEXT:ANALYZE", {
                trigger,
                context: service.getContext(),
            });
        }, 2500);

        // ==========================================
        // PUBLIC API
        // ==========================================

        const service = {
            /**
             * Get current context (privacy-filtered)
             * Never returns actual field values, only metadata
             */
            getContext() {
                return {
                    model: currentContext.model,
                    viewType: currentContext.viewType,
                    recordId: currentContext.recordId,
                    recordState: currentContext.recordState,
                    modifiedFieldNames: currentContext.modifiedFields.map(f => f.name),
                    hasUnsavedChanges: currentContext.hasUnsavedChanges,
                    recentActionTypes: currentContext.recentActions.slice(-5).map(a => a.type),
                    lastErrorType: currentContext.lastError?.type || null,
                    searchQuery: currentContext.searchQuery,
                    searchResultCount: currentContext.searchResults?.length ?? null,
                    timeOnViewSeconds: currentContext.viewLoadedAt
                        ? Math.floor((Date.now() - currentContext.viewLoadedAt) / 1000)
                        : 0,
                };
            },

            /**
             * Get context summary for display
             */
            getContextSummary() {
                if (!currentContext.model) {
                    return "Ready to help";
                }

                const modelName = this._getModelDisplayName(currentContext.model);
                const viewType = currentContext.viewType;

                if (currentContext.recordId) {
                    const state = currentContext.recordState;
                    const stateText = state ? ` (${state})` : '';
                    return `Editing ${modelName}${stateText}`;
                }

                if (viewType === 'list' || viewType === 'kanban') {
                    const count = currentContext.searchResults?.length;
                    return count !== null && count !== undefined
                        ? `Viewing ${count} ${modelName}${count !== 1 ? 's' : ''}`
                        : `Browsing ${modelName}`;
                }

                return `Working with ${modelName}`;
            },

            /**
             * Get settings
             */
            getSettings() {
                return { ...settings };
            },

            /**
             * Update settings from backend or user preference
             */
            updateSettings(newSettings) {
                settings = { ...settings, ...newSettings };
            },

            /**
             * Load settings from backend
             */
            async loadSettings() {
                try {
                    const result = await orm.call(
                        'loomworks.ai.user.settings',
                        'get_user_settings',
                        []
                    );
                    if (result && result.id) {
                        const settingsDict = await orm.call(
                            'loomworks.ai.user.settings',
                            'get_settings_dict',
                            [[result.id]]
                        );
                        if (settingsDict) {
                            this.updateSettings(settingsDict);
                        }
                    }
                } catch (error) {
                    console.warn('Failed to load AI settings:', error);
                }
            },

            // ==========================================
            // EVENT TRIGGERS (call these on user actions)
            // ==========================================

            /**
             * Trigger: User loaded a view
             */
            onViewLoaded(viewInfo) {
                currentContext.model = viewInfo.resModel || null;
                currentContext.viewType = viewInfo.viewType || null;
                currentContext.recordId = viewInfo.resId || null;
                currentContext.recordState = null;
                currentContext.modifiedFields = [];
                currentContext.hasUnsavedChanges = false;
                currentContext.viewLoadedAt = Date.now();

                this._logAction({ type: 'view_loaded', model: currentContext.model });
                this._resetIdleTimer();
                debouncedAnalysis('view_loaded');

                // Emit context update
                env.bus.trigger("AI_CONTEXT:UPDATED", this.getContext());
            },

            /**
             * Trigger: User selected/opened a record
             */
            onRecordSelected(recordInfo) {
                currentContext.recordId = recordInfo.id;
                currentContext.recordState = recordInfo.state || null;

                this._logAction({ type: 'record_selected', model: currentContext.model });
                this._resetIdleTimer();
                debouncedAnalysis('record_selected');

                env.bus.trigger("AI_CONTEXT:UPDATED", this.getContext());
            },

            /**
             * Trigger: User clicked Create button
             */
            onRecordCreated() {
                currentContext.recordId = null;
                currentContext.recordState = 'draft';
                currentContext.hasUnsavedChanges = true;

                this._logAction({ type: 'record_created', model: currentContext.model });
                this._resetIdleTimer();
                debouncedAnalysis('record_created');

                env.bus.trigger("AI_CONTEXT:UPDATED", this.getContext());
            },

            /**
             * Trigger: User executed an action/workflow
             */
            onActionExecuted(actionName) {
                this._logAction({ type: 'action_executed', action: actionName });
                this._resetIdleTimer();
                debouncedAnalysis('action_executed');
            },

            /**
             * Trigger: An error occurred
             */
            onErrorOccurred(error) {
                currentContext.lastError = {
                    type: error.type || error.name || 'unknown',
                    message: error.message,
                    timestamp: Date.now(),
                };

                this._logAction({ type: 'error_occurred', errorType: currentContext.lastError.type });

                // Errors trigger immediately (no debounce)
                if (settings.enableSuggestions) {
                    env.bus.trigger("AI_CONTEXT:ANALYZE", {
                        trigger: 'error_occurred',
                        context: this.getContext(),
                    });
                }
            },

            /**
             * Trigger: User performed a search
             */
            onSearchPerformed(query, resultCount) {
                currentContext.searchQuery = query;
                currentContext.searchResults = { length: resultCount };

                this._logAction({ type: 'search_performed', hasResults: resultCount > 0 });
                this._resetIdleTimer();
                debouncedAnalysis('search_performed');

                env.bus.trigger("AI_CONTEXT:UPDATED", this.getContext());
            },

            /**
             * Trigger: User returned to tab after being away
             */
            onTabReturned() {
                this._logAction({ type: 'tab_switched' });
                debouncedAnalysis('tab_switched');
            },

            /**
             * Trigger: User has been idle
             */
            onIdleThreshold() {
                if (!currentContext.model) return;

                this._logAction({ type: 'idle_threshold' });
                debouncedAnalysis('idle_threshold');
            },

            /**
             * Track field modification (for context, not a trigger)
             */
            trackFieldModification(fieldName, fieldType) {
                const existing = currentContext.modifiedFields.find(f => f.name === fieldName);
                if (!existing) {
                    currentContext.modifiedFields.push({
                        name: fieldName,
                        type: fieldType,
                    });
                }
                currentContext.hasUnsavedChanges = true;
                this._resetIdleTimer();

                env.bus.trigger("AI_CONTEXT:UPDATED", this.getContext());
            },

            /**
             * Mark record as saved
             */
            markSaved() {
                currentContext.hasUnsavedChanges = false;
                currentContext.modifiedFields = [];
                this._logAction({ type: 'record_saved', model: currentContext.model });

                env.bus.trigger("AI_CONTEXT:UPDATED", this.getContext());
            },

            /**
             * Record that a suggestion was shown
             */
            recordSuggestionShown() {
                suggestionCount++;
                lastSuggestionTime = Date.now();
            },

            /**
             * Check if we can show another suggestion
             */
            canShowSuggestion() {
                return canShowSuggestion();
            },

            /**
             * Reset session counters (e.g., on page reload)
             */
            resetSession() {
                suggestionCount = 0;
                lastSuggestionTime = 0;
                currentContext.recentActions = [];
            },

            // ==========================================
            // PRIVATE METHODS
            // ==========================================

            _logAction(action) {
                currentContext.recentActions.push({
                    ...action,
                    timestamp: Date.now(),
                });

                // Keep only last 20 actions
                if (currentContext.recentActions.length > 20) {
                    currentContext.recentActions.shift();
                }
            },

            _getModelDisplayName(model) {
                const displayNames = {
                    'sale.order': 'Sales Order',
                    'purchase.order': 'Purchase Order',
                    'account.move': 'Invoice',
                    'res.partner': 'Contact',
                    'product.product': 'Product',
                    'product.template': 'Product',
                    'stock.picking': 'Transfer',
                    'stock.quant': 'Inventory',
                    'mrp.production': 'Manufacturing Order',
                    'project.project': 'Project',
                    'project.task': 'Task',
                    'hr.employee': 'Employee',
                    'hr.leave': 'Time Off',
                    'crm.lead': 'Lead',
                    'helpdesk.ticket': 'Ticket',
                };

                return displayNames[model] || model?.split('.').pop() || 'record';
            },

            _resetIdleTimer() {
                if (idleTimer) {
                    clearTimeout(idleTimer);
                }
                idleTimer = setTimeout(() => {
                    this.onIdleThreshold();
                }, IDLE_THRESHOLD_MS);
            },
        };

        // Helper to check suggestion throttling
        function canShowSuggestion() {
            const maxPerSession = settings.maxSuggestionsPerSession || 10;
            const cooldownMs = (settings.cooldownSeconds || 60) * 1000;

            // Adjust based on frequency setting
            const frequencyMultipliers = {
                'minimal': { max: 0.5, cooldown: 2 },
                'normal': { max: 1, cooldown: 1 },
                'frequent': { max: 2, cooldown: 0.5 },
            };
            const mult = frequencyMultipliers[settings.suggestionFrequency] || frequencyMultipliers['normal'];

            const effectiveMax = Math.floor(maxPerSession * mult.max);
            const effectiveCooldown = cooldownMs * mult.cooldown;

            if (suggestionCount >= effectiveMax) return false;
            if (Date.now() - lastSuggestionTime < effectiveCooldown) return false;
            return true;
        }

        // Set up visibility change listener for tab switching
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                service.onTabReturned();
            }
        });

        // Load settings on start
        service.loadSettings();

        return service;
    },
};

registry.category("services").add("aiContext", aiContextService);
