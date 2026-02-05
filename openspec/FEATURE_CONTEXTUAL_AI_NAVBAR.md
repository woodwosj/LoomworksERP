# Feature: Contextual AI Navbar

## Feature ID: `contextual-ai-navbar`
## Version: 1.0.0
## Status: Proposed
## Target Phase: Phase 2 (AI Integration Layer)

---

## Executive Summary

The Contextual AI Navbar transforms the basic AI button in Loomworks ERP's navigation bar into an intelligent, context-aware assistant dropdown. Instead of users needing to explicitly ask for help, the AI proactively offers relevant suggestions based on what the user is currently doing and their recent actions.

This is a **flagship differentiator** for Loomworks ERP - turning the AI from a reactive chatbot into a proactive business partner that anticipates user needs.

### Key Design Principles

1. **Event-Driven, Not Polling**: The AI only analyzes context when triggered by user actions, not through constant monitoring
2. **Efficient and Lightweight**: No background intervals, no continuous screenshot capture
3. **Privacy by Design**: Data processed by Anthropic's Claude AI with strict privacy policies (no training on user data)
4. **User Control**: Simple settings to adjust suggestion frequency and style

---

## Research Citations

### Claude Vision API
- **Source**: [Claude Vision Documentation](https://platform.claude.com/docs/en/build-with-claude/vision)
- **Key Findings**:
  - Supports PNG, JPEG, GIF, and WebP formats
  - Base64 encoding or URL-based image submission
  - Up to 100 images per API request
  - Best practices: Place images before text prompts
  - Limitations: Accuracy diminishes with small fonts, dense tables, low contrast

### Odoo 18 Navbar Architecture
- **Source**: [Odoo 18 Owl Components](https://www.odoo.com/documentation/18.0/developer/reference/frontend/owl_components.html)
- **Source**: [Odoo 18 Registries](https://www.odoo.com/documentation/18.0/developer/reference/frontend/registries.html)
- **Key Findings**:
  - Systray is the right zone of navbar for widgets/notifications
  - Components registered via `registry.category("systray").add()`
  - Sequence numbers control ordering (lower = right, higher = left)
  - Standard pattern: JS file, XML template, optional SCSS

### Proactive AI UX Patterns
- **Source**: [AI UX Patterns Guide](https://www.aiuxpatterns.com/)
- **Source**: [Developer Interaction Patterns with Proactive AI (arXiv)](https://arxiv.org/html/2601.10253)
- **Key Findings**:
  - Predictive Assistance: Anticipate needs using historical data + real-time context
  - Non-intrusive presentation: Suggestions at key moments, easy override
  - Trust-building: Preview, explanation ("Here's why"), easy undo
  - Business impact: 34% reduction in task completion time, 28% fewer errors

### Event-Driven Architecture Patterns
- **Source**: [JavaScript Debounce vs Throttle](https://www.syncfusion.com/blogs/post/javascript-debounce-vs-throttle)
- **Key Findings**:
  - Debouncing: Delay execution until pause in activity (best for user input)
  - Event-driven: Only trigger analysis on specific user actions
  - For AI suggestions: Use debounced event triggers (2-3 second delay after action)

### Anthropic Privacy & Data Handling
- **Source**: [Anthropic Privacy Policy](https://www.anthropic.com/privacy)
- **Key Findings**:
  - Anthropic does not train on API customer data by default
  - Data submitted via API is not used to improve Claude models
  - Enterprise-grade data protection and security
  - Clear data retention policies with customer control

---

## Feature Specification

### 1. AI Navbar Dropdown Component

Replace the simple AI button with an intelligent dropdown:

```
+------------------------------------------+
|  [Logo] Home | Sales | Inventory    [AI] |  <- Navbar
+------------------------------------------+
                                        |
                                        v
                    +-----------------------------------+
                    |  Loomworks AI                 [X] |
                    +-----------------------------------+
                    | [Context Indicator]               |
                    | You're editing a quote for        |
                    | Acme Corp ($12,450)          [?]  |
                    +-----------------------------------+
                    | SUGGESTIONS (3)              [<>] |
                    | +-------------------------------+ |
                    | | ! Customer has $5,200 overdue | |
                    | |   View overdue invoices ->    | |
                    | +-------------------------------+ |
                    | | + Add their usual items?      | |
                    | |   They ordered Widget X 3x    | |
                    | +-------------------------------+ |
                    | | ? Need help with pricing?     | |
                    | |   Suggest bulk discount       | |
                    | +-------------------------------+ |
                    +-----------------------------------+
                    | QUICK ACTIONS                     |
                    | [Validate] [Send Quote] [...]     |
                    +-----------------------------------+
                    | [        Ask Loomworks AI      ] |
                    |                            [-->] |
                    +-----------------------------------+
                    | [Full Chat] [Settings]           |
                    +-----------------------------------+
```

### 2. Component Architecture

```
AINavbarDropdown (Owl Component)
├── AIContextIndicator
│   ├── currentModel: string
│   ├── currentRecord: { id, name, state }
│   ├── timeOnView: number
│   └── contextSummary: string
├── AISuggestionList
│   ├── suggestions: AISuggestion[]
│   ├── onDismiss(id)
│   ├── onAccept(id)
│   └── AISuggestionItem
│       ├── severity: 'critical' | 'helpful' | 'info'
│       ├── title: string
│       ├── description: string
│       ├── action: { type, payload }
│       └── autoDismissSeconds: number
├── AIQuickActions
│   ├── actions: QuickAction[]
│   └── contextActions: QuickAction[] (dynamic)
├── AIQuickInput
│   ├── placeholder: "Ask Loomworks AI..."
│   ├── onSubmit(query)
│   └── expandToFullChat: boolean
├── AIChatPanel (collapsible)
│   └── AIChat (existing component)
└── AISettingsButton
    └── onClick: () => openSettingsModal()
```

### 3. Event-Driven Context Detection Service

**File**: `odoo/addons/web/static/src/core/ai/ai_context_service.js`

The context service is **event-driven** - it only performs analysis when triggered by specific user actions, not through constant polling or intervals.

#### Context Triggers

```javascript
/**
 * Events that trigger context analysis.
 * The AI only "thinks" about context when these occur.
 */
const CONTEXT_TRIGGERS = {
    'view_loaded':       // User opens a form/list/kanban view
    'record_created':    // User clicks "Create" button
    'record_selected':   // User clicks into a record
    'action_executed':   // User runs a workflow action
    'error_occurred':    // Something failed
    'idle_threshold':    // User paused for 10+ seconds (thinking?)
    'search_performed':  // User searched for something
    'tab_switched':      // User switched browser tab back to Odoo
};

/**
 * What does NOT trigger analysis (no constant monitoring):
 * - No polling intervals
 * - No continuous screenshot capture
 * - No always-on pattern analysis
 * - No background timers checking user activity
 */
```

#### Event-Driven Architecture

```
User Action (trigger)
       │
       ▼
   Debounce (2-3 seconds)
       │
       ▼
   Capture Context
   - Current view state
   - Screenshot (if helpful for the context)
   - Recent actions buffer
       │
       ▼
   AI Analysis (single call)
   - "User just started a quote for Acme Corp"
   - "Should I suggest anything?"
       │
       ▼
   Show suggestion (if any)
   or stay quiet
```

#### Service Implementation

```javascript
/** @odoo-module **/

import { registry } from "@web/core/registry";
import { debounce } from "@web/core/utils/timing";

/**
 * AI Context Detection Service (Event-Driven)
 *
 * Tracks user context for proactive AI suggestions.
 * Only analyzes context when triggered by user actions.
 *
 * Key Principle: NO constant polling or intervals.
 * Analysis happens on-demand when events fire.
 */
export const aiContextService = {
    dependencies: ["user", "action", "orm", "notification"],

    start(env, { user, action, orm, notification }) {
        // Context state
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
        };

        // User preferences (simplified)
        let settings = {
            enableSuggestions: true,
            suggestionFrequency: 'normal',
            notificationStyle: 'popup',
        };

        // Suggestion tracking
        let suggestionCount = 0;
        let lastSuggestionTime = 0;

        // Debounced analysis function (2-3 second delay)
        const debouncedAnalysis = debounce(async (trigger) => {
            if (!settings.enableSuggestions) return;
            if (!canShowSuggestion()) return;

            // Emit event for suggestion service to handle
            env.bus.trigger("AI_CONTEXT:ANALYZE", {
                trigger,
                context: service.getContext(),
            });
        }, 2500); // 2.5 second debounce

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
                    return count !== null
                        ? `Viewing ${count} ${modelName}${count !== 1 ? 's' : ''}`
                        : `Browsing ${modelName}`;
                }

                return `Working with ${modelName}`;
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

                this._logAction({ type: 'view_loaded', model: currentContext.model });
                debouncedAnalysis('view_loaded');
            },

            /**
             * Trigger: User selected/opened a record
             */
            onRecordSelected(recordInfo) {
                currentContext.recordId = recordInfo.id;
                currentContext.recordState = recordInfo.state || null;

                this._logAction({ type: 'record_selected', model: currentContext.model });
                debouncedAnalysis('record_selected');
            },

            /**
             * Trigger: User clicked Create button
             */
            onRecordCreated() {
                this._logAction({ type: 'record_created', model: currentContext.model });
                debouncedAnalysis('record_created');
            },

            /**
             * Trigger: User executed an action/workflow
             */
            onActionExecuted(actionName) {
                this._logAction({ type: 'action_executed', action: actionName });
                debouncedAnalysis('action_executed');
            },

            /**
             * Trigger: An error occurred
             */
            onErrorOccurred(error) {
                currentContext.lastError = {
                    type: error.type || 'unknown',
                    message: error.message,
                    timestamp: Date.now(),
                };

                this._logAction({ type: 'error_occurred', errorType: error.type });
                // Errors trigger immediately (no debounce)
                env.bus.trigger("AI_CONTEXT:ANALYZE", {
                    trigger: 'error_occurred',
                    context: this.getContext(),
                });
            },

            /**
             * Trigger: User performed a search
             */
            onSearchPerformed(query, resultCount) {
                currentContext.searchQuery = query;
                currentContext.searchResults = { length: resultCount };

                this._logAction({ type: 'search_performed', hasResults: resultCount > 0 });
                debouncedAnalysis('search_performed');
            },

            /**
             * Trigger: User returned to tab after being away
             */
            onTabReturned() {
                this._logAction({ type: 'tab_switched' });
                debouncedAnalysis('tab_switched');
            },

            /**
             * Trigger: User has been idle (called by idle detector)
             */
            onIdleThreshold() {
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
            },

            /**
             * Mark record as saved
             */
            markSaved() {
                currentContext.hasUnsavedChanges = false;
                currentContext.modifiedFields = [];
                this._logAction({ type: 'record_saved', model: currentContext.model });
            },

            /**
             * Update user settings
             */
            updateSettings(newSettings) {
                settings = { ...settings, ...newSettings };
            },

            /**
             * Get current settings
             */
            getSettings() {
                return { ...settings };
            },

            /**
             * Record that a suggestion was shown
             */
            recordSuggestionShown() {
                suggestionCount++;
                lastSuggestionTime = Date.now();
            },

            /**
             * Reset session (e.g., on page reload)
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
                    'stock.picking': 'Transfer',
                    'mrp.production': 'Manufacturing Order',
                    'project.task': 'Task',
                    'hr.employee': 'Employee',
                    'crm.lead': 'Lead',
                };

                return displayNames[model] || model?.split('.').pop() || 'record';
            },
        };

        // Helper to check suggestion throttling
        function canShowSuggestion() {
            const maxPerSession = settings.suggestionFrequency === 'minimal' ? 5 :
                                  settings.suggestionFrequency === 'frequent' ? 20 : 10;
            const cooldownMs = settings.suggestionFrequency === 'minimal' ? 120000 :
                               settings.suggestionFrequency === 'frequent' ? 30000 : 60000;

            if (suggestionCount >= maxPerSession) return false;
            if (Date.now() - lastSuggestionTime < cooldownMs) return false;
            return true;
        }

        // Set up visibility change listener for tab switching
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                service.onTabReturned();
            }
        });

        return service;
    },
};

registry.category("services").add("aiContext", aiContextService);
```

### 4. Suggestion Engine Service

**File**: `odoo/addons/web/static/src/core/ai/ai_suggestion_service.js`

```javascript
/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

/**
 * AI Suggestion Engine
 *
 * Generates proactive suggestions based on user context.
 * Respects throttling, priority levels, and user preferences.
 */
export const aiSuggestionService = {
    dependencies: ["aiContext", "orm", "notification"],

    start(env, { aiContext, orm, notification }) {
        // Active suggestions
        let activeSuggestions = [];
        let suggestionIdCounter = 0;

        // Suggestion triggers
        const triggers = new Map();

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
                    notification.add(_t("Failed to execute suggestion"), {
                        type: "danger",
                    });
                }
            },

            /**
             * Register a suggestion trigger
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
             * Check triggers against current context
             */
            async checkTriggers() {
                if (!aiContext.canShowSuggestion()) return;

                const context = aiContext.getContext();
                const now = Date.now();

                for (const [name, trigger] of triggers) {
                    // Check cooldown
                    if (now - trigger.lastTriggered < trigger.cooldownMs) continue;

                    // Check condition
                    if (!trigger.condition(context)) continue;

                    // Generate suggestion
                    try {
                        const suggestion = await trigger.generate(context);
                        if (suggestion) {
                            this._addSuggestion({
                                ...suggestion,
                                source: name,
                                priority: trigger.priority,
                            });
                            trigger.lastTriggered = now;
                            aiContext.recordSuggestionShown();
                        }
                    } catch (error) {
                        console.warn(`Trigger ${name} failed:`, error);
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
                    autoDismissMs: suggestion.autoDismissMs ||
                        (settings.notificationStyle === 'subtle' ? 5000 : null),
                    createdAt: Date.now(),
                };

                // Add to list (sorted by priority)
                activeSuggestions.push(newSuggestion);
                activeSuggestions.sort((a, b) => {
                    const priorityOrder = { critical: 0, helpful: 1, info: 2 };
                    return priorityOrder[a.priority] - priorityOrder[b.priority];
                });

                // Limit active suggestions
                if (activeSuggestions.length > 10) {
                    activeSuggestions = activeSuggestions.slice(0, 10);
                }

                env.bus.trigger("AI_SUGGESTIONS:UPDATED", this.getSuggestions());

                // Auto-dismiss if configured
                if (newSuggestion.autoDismissMs) {
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
                    default:
                        console.warn('Unknown action type:', action.type);
                }
            },
        };

        // ==========================================
        // REGISTER DEFAULT TRIGGERS
        // ==========================================

        // Trigger: User seems stuck
        service.registerTrigger('user_stuck', {
            condition: (ctx) => ctx.seemsStuck && ctx.timeOnViewSeconds > 30,
            generate: async (ctx) => ({
                title: _t("Need help getting started?"),
                description: _t("I can help you with this %s", ctx.model),
                action: { type: 'ask_ai', query: `Help me with ${ctx.model}` },
            }),
            priority: 'helpful',
            cooldownMs: 120000, // 2 minutes
        });

        // Trigger: Empty search results
        service.registerTrigger('empty_search', {
            condition: (ctx) => ctx.recentActionTypes.includes('search') &&
                               ctx.searchResults?.length === 0,
            generate: async (ctx) => ({
                title: _t("No results found"),
                description: _t("Try a broader search or let me help find what you need"),
                action: { type: 'ask_ai', query: 'Help me search for...' },
            }),
            priority: 'helpful',
        });

        // Trigger: Error encountered
        service.registerTrigger('error_recovery', {
            condition: (ctx) => ctx.lastErrorType !== null,
            generate: async (ctx) => ({
                title: _t("I can help fix that"),
                description: _t("I noticed an error occurred"),
                action: { type: 'ask_ai', query: `Help me fix: ${ctx.lastErrorType}` },
            }),
            priority: 'critical',
            cooldownMs: 30000,
        });

        // Trigger: Customer context (requires backend check)
        service.registerTrigger('customer_context', {
            condition: (ctx) => ctx.model === 'sale.order' && ctx.recordId,
            generate: async (ctx) => {
                // Check for overdue invoices
                const overdueInfo = await orm.call(
                    'res.partner',
                    'get_overdue_summary',
                    [ctx.recordId]
                );

                if (overdueInfo?.total > 0) {
                    return {
                        title: _t("Customer has overdue balance"),
                        description: _t("%s overdue", overdueInfo.formattedTotal),
                        action: {
                            type: 'navigate',
                            actionId: 'account.action_move_out_invoice_type',
                        },
                    };
                }
                return null;
            },
            priority: 'critical',
            cooldownMs: 300000, // 5 minutes
        });

        // Trigger: Customer history suggestions
        service.registerTrigger('customer_history', {
            condition: (ctx) => ctx.model === 'sale.order' &&
                               ctx.viewType === 'form' &&
                               ctx.hasUnsavedChanges,
            generate: async (ctx) => {
                const history = await orm.call(
                    'sale.order',
                    'get_customer_purchase_patterns',
                    [ctx.recordId]
                );

                if (history?.frequentProducts?.length > 0) {
                    return {
                        title: _t("Add their usual items?"),
                        description: _t("This customer frequently orders: %s",
                            history.frequentProducts.slice(0, 3).join(', ')),
                        action: {
                            type: 'ask_ai',
                            query: `Add the customer's usual items to this order`,
                        },
                    };
                }
                return null;
            },
            priority: 'helpful',
            cooldownMs: 180000, // 3 minutes
        });

        // Subscribe to context analysis events (event-driven, not polling)
        env.bus.addEventListener("AI_CONTEXT:ANALYZE", async (ev) => {
            const { trigger, context } = ev.detail;
            await service.analyzeAndSuggest(trigger, context);
        });

        return service;
    },
};

registry.category("services").add("aiSuggestion", aiSuggestionService);
```

### 5. User Settings Model (Simplified)

**File**: `loomworks_addons/loomworks_ai/models/ai_user_settings.py`

The user settings model is intentionally simple. Privacy and vision analysis consent is covered in the EULA at signup, so we don't need separate opt-in toggles.

```python
# -*- coding: utf-8 -*-
"""
AI User Settings Model (Simplified)

Stores user preferences for proactive AI assistance.
Simple controls: suggestions on/off, frequency, and notification style.

Privacy Note: Vision/screenshot analysis consent is covered in the EULA
at signup. Anthropic has strict data privacy policies - user data is not
used for AI training.
"""

from odoo import models, fields, api


class AIUserSettings(models.Model):
    _name = 'loomworks.ai.user.settings'
    _description = 'AI User Preferences'
    _rec_name = 'user_id'

    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        ondelete='cascade',
        default=lambda self: self.env.user,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    # ==========================================
    # CORE SETTINGS (Simple)
    # ==========================================

    enable_suggestions = fields.Boolean(
        string='Enable Proactive Suggestions',
        default=True,
        help="Allow AI to offer helpful suggestions based on your actions"
    )

    suggestion_frequency = fields.Selection([
        ('minimal', 'Minimal - Only critical issues'),
        ('normal', 'Normal - Helpful suggestions'),
        ('frequent', 'Frequent - More proactive'),
    ], string='Suggestion Frequency', default='normal', required=True,
       help="""How often the AI offers suggestions:
       - Minimal: Only critical issues like errors or overdue payments
       - Normal: Helpful suggestions without being intrusive
       - Frequent: More proactive assistance""")

    notification_style = fields.Selection([
        ('badge', 'Badge only'),
        ('popup', 'Popup notification'),
    ], string='Notification Style', default='popup', required=True,
       help="""How suggestions appear:
       - Badge: Unobtrusive dot on AI button
       - Popup: Brief popup notification""")

    # ==========================================
    # CONSTRAINTS
    # ==========================================

    _sql_constraints = [
        ('user_company_uniq', 'UNIQUE(user_id, company_id)',
         'Settings already exist for this user in this company'),
    ]

    # ==========================================
    # PUBLIC METHODS
    # ==========================================

    @api.model
    def get_user_settings(self, user_id=None):
        """
        Get settings for a user, creating defaults if needed.
        """
        user_id = user_id or self.env.uid

        settings = self.search([
            ('user_id', '=', user_id),
            ('company_id', '=', self.env.company.id),
        ], limit=1)

        if not settings:
            settings = self.create({
                'user_id': user_id,
                'company_id': self.env.company.id,
            })

        return settings

    def get_settings_dict(self):
        """
        Return settings as a dictionary for frontend consumption.
        """
        self.ensure_one()
        return {
            'enableSuggestions': self.enable_suggestions,
            'suggestionFrequency': self.suggestion_frequency,
            'notificationStyle': self.notification_style,
        }

    @api.model
    def update_user_settings(self, values):
        """
        Update settings for current user.
        """
        settings = self.get_user_settings()

        # Map frontend keys to model fields
        field_map = {
            'enableSuggestions': 'enable_suggestions',
            'suggestionFrequency': 'suggestion_frequency',
            'notificationStyle': 'notification_style',
        }

        write_vals = {}
        for frontend_key, backend_field in field_map.items():
            if frontend_key in values:
                write_vals[backend_field] = values[frontend_key]

        if write_vals:
            settings.write(write_vals)

        return settings.get_settings_dict()
```

### 6. AI Navbar Dropdown Component

**File**: `odoo/addons/web/static/src/core/ai/ai_navbar_dropdown/ai_navbar_dropdown.js`

```javascript
/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { _t } from "@web/core/l10n/translation";

/**
 * AI Navbar Dropdown Component
 *
 * Intelligent dropdown that shows:
 * - Current context awareness
 * - Proactive suggestions
 * - Quick actions
 * - Expandable chat interface
 */
export class AINavbarDropdown extends Component {
    static template = "web.AINavbarDropdown";
    static components = { Dropdown };
    static props = {};

    setup() {
        // Services
        this.aiContext = useService("aiContext");
        this.aiSuggestion = useService("aiSuggestion");
        this.orm = useService("orm");
        this.dialog = useService("dialog");

        // State
        this.state = useState({
            isOpen: false,
            contextSummary: "",
            suggestions: [],
            quickActions: [],
            isLoading: false,
            chatExpanded: false,
            settings: null,
            unreadCount: 0,
        });

        // Refs
        this.inputRef = useRef("quickInput");

        onMounted(async () => {
            await this.loadSettings();
            this.subscribeToUpdates();
            this.updateContext();
        });

        onWillUnmount(() => {
            this.unsubscribeFromUpdates();
        });
    }

    // ==========================================
    // LIFECYCLE
    // ==========================================

    async loadSettings() {
        try {
            const settings = await this.orm.call(
                'loomworks.ai.user.settings',
                'get_user_settings',
                []
            );
            this.state.settings = settings.get_settings_dict
                ? await settings.get_settings_dict()
                : settings;

            this.aiContext.updateSettings(this.state.settings);
        } catch (error) {
            console.warn('Failed to load AI settings:', error);
            // Use defaults
            this.state.settings = {
                proactiveLevel: 'balanced',
                showContextIndicator: true,
                enableQuickActions: true,
            };
        }
    }

    subscribeToUpdates() {
        this.env.bus.addEventListener("AI_CONTEXT:UPDATED", this.onContextUpdate);
        this.env.bus.addEventListener("AI_SUGGESTIONS:UPDATED", this.onSuggestionsUpdate);
        this.env.bus.addEventListener("AI:OPEN_CHAT", this.onOpenChat);
    }

    unsubscribeFromUpdates() {
        this.env.bus.removeEventListener("AI_CONTEXT:UPDATED", this.onContextUpdate);
        this.env.bus.removeEventListener("AI_SUGGESTIONS:UPDATED", this.onSuggestionsUpdate);
        this.env.bus.removeEventListener("AI:OPEN_CHAT", this.onOpenChat);
    }

    // ==========================================
    // EVENT HANDLERS
    // ==========================================

    onContextUpdate = () => {
        this.updateContext();
    };

    onSuggestionsUpdate = (ev) => {
        this.state.suggestions = ev.detail || [];
        this.state.unreadCount = this.state.suggestions.filter(
            s => s.priority === 'critical'
        ).length;
    };

    onOpenChat = (ev) => {
        this.state.isOpen = true;
        this.state.chatExpanded = true;
        if (ev.detail?.query) {
            // Pre-fill chat with query
            this.pendingQuery = ev.detail.query;
        }
    };

    updateContext() {
        this.state.contextSummary = this.aiContext.getContextSummary();
        this.updateQuickActions();
    }

    async updateQuickActions() {
        const context = this.aiContext.getContext();
        if (!context.model || !this.state.settings?.enableQuickActions) {
            this.state.quickActions = [];
            return;
        }

        // Get context-specific quick actions
        try {
            const actions = await this.orm.call(
                'loomworks.ai.agent',
                'get_context_quick_actions',
                [context]
            );
            this.state.quickActions = actions || [];
        } catch (error) {
            this.state.quickActions = [];
        }
    }

    // ==========================================
    // ACTIONS
    // ==========================================

    onDropdownToggle(isOpen) {
        this.state.isOpen = isOpen;
        if (isOpen) {
            // Clear unread on open
            this.state.unreadCount = 0;
        }
    }

    dismissSuggestion(suggestion) {
        this.aiSuggestion.dismissSuggestion(suggestion.id);
    }

    async acceptSuggestion(suggestion) {
        await this.aiSuggestion.acceptSuggestion(suggestion.id);
    }

    async executeQuickAction(action) {
        this.state.isLoading = true;
        try {
            await this.env.services.action.doAction(action.actionId);
        } finally {
            this.state.isLoading = false;
        }
    }

    async onQuickInputSubmit(ev) {
        if (ev.key !== 'Enter') return;

        const query = ev.target.value.trim();
        if (!query) return;

        ev.target.value = '';
        this.state.chatExpanded = true;

        // Send to AI chat
        this.env.bus.trigger("AI_CHAT:SEND_MESSAGE", { content: query });
    }

    toggleChat() {
        this.state.chatExpanded = !this.state.chatExpanded;
    }

    openSettings() {
        this.dialog.add(AISettingsDialog, {
            settings: this.state.settings,
            onSave: async (newSettings) => {
                this.state.settings = await this.orm.call(
                    'loomworks.ai.user.settings',
                    'update_user_settings',
                    [newSettings]
                );
                this.aiContext.updateSettings(this.state.settings);
            },
        });
    }

    // ==========================================
    // GETTERS
    // ==========================================

    get suggestionBadgeClass() {
        const hasCritical = this.state.suggestions.some(s => s.priority === 'critical');
        if (hasCritical) return 'bg-danger';
        if (this.state.suggestions.length > 0) return 'bg-primary';
        return '';
    }

    get showContextIndicator() {
        return this.state.settings?.showContextIndicator !== false;
    }

    get priorityIcon() {
        return (priority) => {
            switch (priority) {
                case 'critical': return 'fa-exclamation-circle text-danger';
                case 'helpful': return 'fa-lightbulb-o text-warning';
                case 'info': return 'fa-info-circle text-info';
                default: return 'fa-comment text-muted';
            }
        };
    }
}
```

**File**: `odoo/addons/web/static/src/core/ai/ai_navbar_dropdown/ai_navbar_dropdown.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<templates xml:space="preserve">

    <t t-name="web.AINavbarDropdown">
        <Dropdown
            class="'o_ai_navbar_dropdown'"
            togglerClass="'btn btn-sm'"
            menuClass="'o_ai_dropdown_menu'"
            onStateChanged.bind="onDropdownToggle"
        >
            <t t-set-slot="toggler">
                <span class="d-flex align-items-center">
                    <i class="fa fa-robot me-1"/>
                    <span class="d-none d-md-inline">AI</span>
                    <t t-if="state.suggestions.length > 0">
                        <span
                            class="badge rounded-pill ms-1"
                            t-attf-class="{{ suggestionBadgeClass }}"
                        >
                            <t t-esc="state.suggestions.length"/>
                        </span>
                    </t>
                </span>
            </t>

            <!-- Dropdown Menu Content -->
            <div class="o_ai_dropdown_content" style="min-width: 320px; max-width: 400px;">

                <!-- Header -->
                <div class="o_ai_dropdown_header d-flex justify-content-between align-items-center p-3 border-bottom">
                    <span class="fw-bold">
                        <i class="fa fa-robot me-2"/>
                        Loomworks AI
                    </span>
                    <div class="d-flex gap-2">
                        <button
                            class="btn btn-sm btn-link p-0"
                            t-on-click="openSettings"
                            title="Settings"
                        >
                            <i class="fa fa-cog"/>
                        </button>
                    </div>
                </div>

                <!-- Context Indicator -->
                <t t-if="showContextIndicator and state.contextSummary">
                    <div class="o_ai_context_indicator p-3 bg-light border-bottom">
                        <small class="text-muted d-block mb-1">Currently:</small>
                        <span class="fw-medium" t-esc="state.contextSummary"/>
                    </div>
                </t>

                <!-- Suggestions -->
                <t t-if="state.suggestions.length > 0">
                    <div class="o_ai_suggestions p-2">
                        <small class="text-muted px-2 mb-2 d-block">
                            SUGGESTIONS (<t t-esc="state.suggestions.length"/>)
                        </small>

                        <t t-foreach="state.suggestions" t-as="suggestion" t-key="suggestion.id">
                            <div class="o_ai_suggestion_item card mb-2">
                                <div class="card-body p-2">
                                    <div class="d-flex align-items-start">
                                        <i
                                            t-attf-class="fa {{ priorityIcon(suggestion.priority) }} me-2 mt-1"
                                        />
                                        <div class="flex-grow-1">
                                            <div class="fw-medium small" t-esc="suggestion.title"/>
                                            <div class="text-muted small" t-esc="suggestion.description"/>
                                        </div>
                                        <button
                                            class="btn btn-sm btn-link p-0 text-muted"
                                            t-on-click="() => this.dismissSuggestion(suggestion)"
                                        >
                                            <i class="fa fa-times"/>
                                        </button>
                                    </div>
                                    <div class="mt-2">
                                        <button
                                            class="btn btn-sm btn-primary"
                                            t-on-click="() => this.acceptSuggestion(suggestion)"
                                        >
                                            <t t-if="suggestion.action?.type === 'ask_ai'">
                                                Ask AI
                                            </t>
                                            <t t-else="">
                                                Go <i class="fa fa-arrow-right ms-1"/>
                                            </t>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </t>
                    </div>
                </t>

                <!-- Quick Actions -->
                <t t-if="state.quickActions.length > 0">
                    <div class="o_ai_quick_actions p-2 border-top">
                        <small class="text-muted px-2 mb-2 d-block">QUICK ACTIONS</small>
                        <div class="d-flex flex-wrap gap-1 px-2">
                            <t t-foreach="state.quickActions" t-as="action" t-key="action.id">
                                <button
                                    class="btn btn-sm btn-outline-secondary"
                                    t-on-click="() => this.executeQuickAction(action)"
                                    t-att-disabled="state.isLoading"
                                >
                                    <i t-if="action.icon" t-attf-class="fa {{ action.icon }} me-1"/>
                                    <t t-esc="action.label"/>
                                </button>
                            </t>
                        </div>
                    </div>
                </t>

                <!-- Quick Input -->
                <div class="o_ai_quick_input p-3 border-top">
                    <div class="input-group">
                        <input
                            type="text"
                            class="form-control form-control-sm"
                            placeholder="Ask Loomworks AI..."
                            t-on-keypress="onQuickInputSubmit"
                            t-ref="quickInput"
                        />
                        <button
                            class="btn btn-sm btn-primary"
                            t-on-click="toggleChat"
                            title="Full Chat"
                        >
                            <i class="fa fa-expand"/>
                        </button>
                    </div>
                </div>

                <!-- Expandable Chat Panel -->
                <t t-if="state.chatExpanded">
                    <div class="o_ai_chat_panel border-top" style="height: 300px;">
                        <AIChat embedded="true"/>
                    </div>
                </t>

                <!-- Footer -->
                <div class="o_ai_dropdown_footer p-2 border-top bg-light d-flex justify-content-between">
                    <button
                        class="btn btn-sm btn-link"
                        t-on-click="toggleChat"
                    >
                        <t t-if="state.chatExpanded">
                            <i class="fa fa-compress me-1"/>Collapse
                        </t>
                        <t t-else="">
                            <i class="fa fa-comments me-1"/>Full Chat
                        </t>
                    </button>
                    <button
                        class="btn btn-sm btn-link"
                        t-on-click="openSettings"
                    >
                        <i class="fa fa-sliders me-1"/>Settings
                    </button>
                </div>
            </div>
        </Dropdown>
    </t>

</templates>
```

**File**: `odoo/addons/web/static/src/core/ai/ai_navbar_dropdown/ai_navbar_dropdown.scss`

```scss
// AI Navbar Dropdown Styles

.o_ai_navbar_dropdown {
    .o_ai_dropdown_menu {
        min-width: 320px;
        max-width: 420px;
        max-height: 80vh;
        overflow-y: auto;
    }

    .o_ai_dropdown_header {
        background: linear-gradient(135deg, var(--lw-primary) 0%, var(--lw-primary-dark) 100%);
        color: white;

        .btn-link {
            color: rgba(255, 255, 255, 0.8);

            &:hover {
                color: white;
            }
        }
    }

    .o_ai_context_indicator {
        font-size: 0.875rem;
    }

    .o_ai_suggestion_item {
        transition: transform 0.15s ease, box-shadow 0.15s ease;

        &:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }

        &.priority-critical {
            border-left: 3px solid var(--bs-danger);
        }

        &.priority-helpful {
            border-left: 3px solid var(--bs-warning);
        }
    }

    .o_ai_quick_actions {
        .btn {
            font-size: 0.75rem;
        }
    }

    .o_ai_chat_panel {
        overflow: hidden;

        .loomworks-ai-chat {
            height: 100%;
        }
    }

    // Badge animation for new suggestions
    .badge {
        animation: pulse 2s infinite;

        @keyframes pulse {
            0%, 100% {
                opacity: 1;
            }
            50% {
                opacity: 0.7;
            }
        }
    }

    // Danger badge for critical suggestions
    .badge.bg-danger {
        animation: pulse-danger 1s infinite;

        @keyframes pulse-danger {
            0%, 100% {
                transform: scale(1);
            }
            50% {
                transform: scale(1.1);
            }
        }
    }
}
```

---

## UX Mockups (ASCII)

### Collapsed State (Badge indicates suggestions)

```
+------------------------------------------------------------------+
|  [L] Home | Sales | Inventory | Mfg     [Search]  [AI(3)] [User] |
+------------------------------------------------------------------+
                                                     ^
                                              Badge shows 3
                                              pending suggestions
```

### Dropdown Open - With Suggestions

```
+------------------------------------------------------------------+
|  [L] Home | Sales | Inventory | Mfg     [Search]  [AI(3)] [User] |
+------------------------------------------------------------------+
                                           |
                                           v
                              +----------------------------+
                              |  [robot] Loomworks AI  [X] |
                              +----------------------------+
                              | Currently:                  |
                              | Editing Sales Order (draft) |
                              +----------------------------+
                              | SUGGESTIONS (3)             |
                              | +------------------------+  |
                              | | [!] Customer overdue   |  |
                              | |     $5,200 outstanding |  |
                              | |            [View ->]   |  |
                              | +------------------------+  |
                              | | [*] Add usual items?   |  |
                              | |     Widget X, Part Y   |  |
                              | |            [Ask AI]    |  |
                              | +------------------------+  |
                              | | [i] Bulk discount?     |  |
                              | |     Order > $10K       |  |
                              | |            [Ask AI]    |  |
                              | +------------------------+  |
                              +----------------------------+
                              | QUICK ACTIONS               |
                              | [Validate] [Send] [Print]   |
                              +----------------------------+
                              | [     Ask Loomworks AI   ] |
                              +----------------------------+
                              | [Full Chat]    [Settings]  |
                              +----------------------------+
```

### Expanded Chat View

```
+----------------------------+
|  [robot] Loomworks AI  [X] |
+----------------------------+
| Currently:                  |
| Editing Sales Order (draft) |
+----------------------------+
| +------------------------+  |
| | User: Add the usual    |  |
| |       items please     |  |
| +------------------------+  |
| | AI: I've added 3 items |  |
| |     based on history:  |  |
| |     - Widget X (10)    |  |
| |     - Part Y (5)       |  |
| |     - Supply Z (20)    |  |
| |     Total: $3,450      |  |
| +------------------------+  |
| | User: Apply bulk       |  |
| |       discount         |  |
| +------------------------+  |
| | AI: Applied 10%        |  |
| |     discount.          |  |
| |     New total: $3,105  |  |
| +------------------------+  |
+----------------------------+
| [                        ] |
| [       Send Message     ] |
+----------------------------+
| [Collapse]    [Settings]   |
+----------------------------+
```

### Settings Modal (Simplified)

```
+----------------------------------------------+
|           AI Assistant Settings              |
+----------------------------------------------+
|                                              |
| SUGGESTIONS                                  |
| +------------------------------------------+ |
| |  [x] Enable proactive suggestions        | |
| +------------------------------------------+ |
|                                              |
| SUGGESTION FREQUENCY                         |
| +------------------------------------------+ |
| |  ( ) Minimal - Only critical issues      | |
| |  (*) Normal - Helpful suggestions        | |
| |  ( ) Frequent - More proactive           | |
| +------------------------------------------+ |
|                                              |
| NOTIFICATION STYLE                           |
| +------------------------------------------+ |
| |  ( ) Badge only                          | |
| |  (*) Popup notification                  | |
| +------------------------------------------+ |
|                                              |
| PRIVACY INFO                                 |
| +------------------------------------------+ |
| |  Your data is processed by Anthropic's   | |
| |  Claude AI. Anthropic has strict data    | |
| |  privacy policies - your data is not     | |
| |  used for training. Context analysis     | |
| |  only happens when you perform actions.  | |
| |                                          | |
| |  [View Privacy Policy]                   | |
| +------------------------------------------+ |
|                                              |
|                   [Cancel]  [Save Settings]  |
+----------------------------------------------+
```

---

## Privacy & Data Handling

### Anthropic's Data Privacy Commitment

Your data is processed by Anthropic's Claude AI, which has **strict data privacy policies**:

- **No training on your data**: Anthropic does not use API customer data to train Claude models
- **Data protection**: Enterprise-grade security and data handling
- **Compliance ready**: SOC 2 Type II certified, GDPR compliant
- **Data retention**: Clear retention policies with customer control

### What Data is Sent for Context Analysis

| Data Type | When Sent | Purpose |
|-----------|-----------|---------|
| Model name | On trigger events | Identify what you're working on |
| View type | On trigger events | Understand the interface context |
| Record ID | On trigger events | Reference for suggestions |
| Record state | On trigger events | E.g., "draft", "confirmed" |
| Field names modified | On trigger events | Know which fields you touched |
| Recent action types | On trigger events | Understand your workflow |
| Error types | When errors occur | Help troubleshoot issues |
| Screenshots | When helpful for context | Visual understanding of screen |

**What is NOT sent:**
- Actual field values (only field names)
- Complete record content
- Passwords or sensitive credentials
- Personal identification data

### Event-Driven, Not Constant Monitoring

The AI only analyzes context when you perform specific actions:

- **Triggers analysis**: Opening views, selecting records, clicking actions, errors
- **Does NOT constantly poll**: No background monitoring or periodic checks
- **No surveillance**: The AI is dormant until you do something

### User Controls

1. **Suggestions On/Off**: Completely disable proactive suggestions
2. **Frequency Control**: Choose minimal, normal, or frequent suggestions
3. **Notification Style**: Badge only or popup notifications

### Privacy Summary (for Settings UI)

> Your data is processed by Anthropic's Claude AI. Anthropic has strict data privacy policies - your data is not used for training AI models. Context analysis only happens when you perform actions in the system. Full privacy details are available in our Terms of Service.

---

## Implementation Tasks

### Phase 2.7: Contextual AI Navbar (Weeks 11-12)

| Task | Description | Estimate |
|------|-------------|----------|
| 2.7.1 | Create `ai_context_service.js` (event-driven) | 6h |
| 2.7.2 | Create `ai_suggestion_service.js` | 6h |
| 2.7.3 | Create `AINavbarDropdown` Owl component | 10h |
| 2.7.4 | Create `loomworks.ai.user.settings` model (simplified) | 2h |
| 2.7.5 | Create settings modal component (simplified) | 3h |
| 2.7.6 | Integrate with existing `AIChat` component | 4h |
| 2.7.7 | Add backend suggestion triggers | 6h |
| 2.7.8 | Hook context triggers into view controllers | 4h |
| 2.7.9 | Add idle detection (10s threshold) | 2h |
| 2.7.10 | Write tests (unit + integration) | 6h |
| 2.7.11 | Documentation and UX testing | 3h |
| **Total** | | **52h** |

### Files to Create

```
odoo/addons/web/static/src/core/ai/
├── ai_context_service.js        # Event-driven context detection
├── ai_suggestion_service.js     # Suggestion generation
├── ai_idle_detector.js          # Simple idle detection (10s threshold)
├── ai_navbar_dropdown/
│   ├── ai_navbar_dropdown.js
│   ├── ai_navbar_dropdown.xml
│   └── ai_navbar_dropdown.scss
└── ai_settings_dialog/
    ├── ai_settings_dialog.js    # Simplified settings modal
    └── ai_settings_dialog.xml

loomworks_addons/loomworks_ai/models/
└── ai_user_settings.py          # Simplified 3-field model
```

### Files to Modify

| File | Change |
|------|--------|
| `odoo/addons/web/static/src/webclient/navbar/navbar.xml` | Add `AINavbarDropdown` to systray |
| `odoo/addons/web/views/webclient_templates.xml` | Register new assets |
| `odoo/addons/web/static/src/views/form/form_controller.js` | Hook context triggers |
| `odoo/addons/web/static/src/views/list/list_controller.js` | Hook context triggers |
| `loomworks_ai/__manifest__.py` | Add `ai_user_settings` to data files |
| `loomworks_ai/models/__init__.py` | Import `ai_user_settings` |
| `loomworks_ai/security/ir.model.access.csv` | Add access rights for settings |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Suggestion acceptance rate | > 30% | Clicks on suggestion actions |
| Task completion time | -20% | A/B test with/without proactive AI |
| User satisfaction | > 4/5 | Survey after 1 week usage |
| Error recovery time | -40% | Time from error to resolution |
| Settings adjustment rate | < 10% | Users who change defaults |

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Suggestions feel intrusive | User disables AI | Conservative defaults, easy disable, frequency control |
| Privacy concerns | User distrust | Clear Anthropic privacy info, event-driven (not constant), EULA coverage |
| Too many API calls | Cost/performance | Event-driven triggers, debouncing, frequency settings |
| Suggestions not relevant | User ignores | ML feedback loop, A/B testing |
| Context detection errors | Wrong suggestions | Fallback to generic, user feedback |

---

## Future Enhancements

1. **ML-Based Suggestion Ranking** - Learn from user acceptance/dismissal patterns
2. **Cross-Session Learning** - Remember user preferences across sessions
3. **Team Suggestions** - "Your team usually does X at this step"
4. **Predictive Actions** - Pre-fill forms based on patterns
5. **Voice Input** - "Hey Loomworks, create a PO for..."
6. **Smart Idle Detection** - More sophisticated idle patterns based on view complexity

---

## Appendix: Trigger Examples

| Trigger Event | Context | Suggestion |
|---------------|---------|------------|
| `view_loaded` (sales order form) | model: sale.order, viewType: form | Check customer credit status |
| `record_created` (new quote) | model: sale.order, state: draft | "Customer has overdue invoices" |
| `record_selected` (customer) | model: res.partner | Show purchase history summary |
| `error_occurred` | lastError: validation_error | "I can help fix that" |
| `search_performed` (no results) | searchResults: 0 | "Try broader search?" |
| `idle_threshold` (10s on empty form) | hasUnsavedChanges: false | "Need help getting started?" |
| `action_executed` (confirm order) | model: sale.order, state: sale | "Order confirmed. Create invoice?" |
| `tab_switched` (returned to Odoo) | model: purchase.order | Resume context, check for updates |
