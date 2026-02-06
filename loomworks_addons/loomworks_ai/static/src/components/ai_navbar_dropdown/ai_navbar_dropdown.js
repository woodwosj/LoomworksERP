/** @loomworks-module **/
// Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
// License: LGPL-3

/**
 * AI Navbar Dropdown Component
 *
 * Intelligent dropdown in the navbar that shows:
 * - Current context awareness
 * - Proactive suggestions
 * - Quick actions
 * - Expandable chat interface
 *
 * Based on: FEATURE_CONTEXTUAL_AI_NAVBAR.md
 */

import { Component, useState, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";

export class AINavbarDropdown extends Component {
    static template = "loomworks_ai.AINavbarDropdown";
    static components = { Dropdown };
    static props = {};

    setup() {
        // Services
        this.aiContext = useService("aiContext");
        this.aiSuggestion = useService("aiSuggestion");
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

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
            inputValue: "",
        });

        // Refs
        this.inputRef = useRef("quickInput");

        // Pending query from external trigger
        this.pendingQuery = null;

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
            const result = await this.orm.call(
                'loomworks.ai.user.settings',
                'get_user_settings',
                []
            );
            if (result && result.id) {
                this.state.settings = await this.orm.call(
                    'loomworks.ai.user.settings',
                    'get_settings_dict',
                    [[result.id]]
                );
            } else {
                // Use defaults
                this.state.settings = {
                    enableSuggestions: true,
                    showContextIndicator: true,
                    enableQuickActions: true,
                };
            }

            if (this.aiContext) {
                this.aiContext.updateSettings(this.state.settings);
            }
        } catch (error) {
            console.warn('Failed to load AI settings:', error);
            this.state.settings = {
                enableSuggestions: true,
                showContextIndicator: true,
                enableQuickActions: true,
            };
        }
    }

    subscribeToUpdates() {
        this.onContextUpdate = () => this.updateContext();
        this.onSuggestionsUpdate = (ev) => {
            this.state.suggestions = ev.detail || [];
            this.state.unreadCount = this.state.suggestions.filter(
                s => s.priority === 'critical'
            ).length;
        };
        this.onOpenChat = (ev) => {
            this.state.isOpen = true;
            this.state.chatExpanded = true;
            if (ev.detail?.query) {
                this.pendingQuery = ev.detail.query;
            }
        };

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
    // CONTEXT & QUICK ACTIONS
    // ==========================================

    updateContext() {
        if (this.aiContext) {
            this.state.contextSummary = this.aiContext.getContextSummary();
            this.updateQuickActions();
        }
    }

    async updateQuickActions() {
        if (!this.state.settings?.enableQuickActions) {
            this.state.quickActions = [];
            return;
        }

        const context = this.aiContext?.getContext();
        if (!context?.model) {
            this.state.quickActions = [];
            return;
        }

        // Generate context-specific quick actions
        const actions = [];

        // Model-specific quick actions
        switch (context.model) {
            case 'sale.order':
                actions.push(
                    { id: 'so_create', label: _t('New Quote'), icon: 'fa-plus', query: 'Create a new sales quotation' },
                    { id: 'so_status', label: _t('Order Status'), icon: 'fa-info-circle', query: 'Show me the status of recent sales orders' },
                );
                break;
            case 'purchase.order':
                actions.push(
                    { id: 'po_create', label: _t('New PO'), icon: 'fa-plus', query: 'Create a new purchase order' },
                    { id: 'po_pending', label: _t('Pending'), icon: 'fa-clock-o', query: 'Show pending purchase orders' },
                );
                break;
            case 'res.partner':
                actions.push(
                    { id: 'contact_create', label: _t('New Contact'), icon: 'fa-user-plus', query: 'Create a new contact' },
                    { id: 'contact_search', label: _t('Find'), icon: 'fa-search', query: 'Help me find a contact' },
                );
                break;
            case 'product.product':
            case 'product.template':
                actions.push(
                    { id: 'product_stock', label: _t('Stock'), icon: 'fa-cubes', query: 'Show stock levels for this product' },
                    { id: 'product_sales', label: _t('Sales'), icon: 'fa-chart-line', query: 'Show sales history for this product' },
                );
                break;
            case 'account.move':
                actions.push(
                    { id: 'invoice_overdue', label: _t('Overdue'), icon: 'fa-exclamation-triangle', query: 'Show overdue invoices' },
                    { id: 'invoice_create', label: _t('New Invoice'), icon: 'fa-plus', query: 'Create a new invoice' },
                );
                break;
            case 'project.task':
                actions.push(
                    { id: 'task_my', label: _t('My Tasks'), icon: 'fa-user', query: 'Show my open tasks' },
                    { id: 'task_overdue', label: _t('Overdue'), icon: 'fa-clock-o', query: 'Show overdue tasks' },
                );
                break;
            default:
                actions.push(
                    { id: 'generic_search', label: _t('Search'), icon: 'fa-search', query: `Search ${context.model}` },
                    { id: 'generic_create', label: _t('Create'), icon: 'fa-plus', query: `Create new ${context.model}` },
                );
        }

        // Always add dashboard action
        actions.push(
            { id: 'dashboard', label: _t('Dashboard'), icon: 'fa-tachometer', query: 'Show me the business dashboard' }
        );

        this.state.quickActions = actions.slice(0, 4); // Limit to 4
    }

    // ==========================================
    // ACTIONS
    // ==========================================

    onDropdownToggle(isOpen) {
        this.state.isOpen = isOpen;
        if (isOpen) {
            this.state.unreadCount = 0;
            this.updateContext();

            // Focus input when opened
            setTimeout(() => {
                if (this.inputRef.el) {
                    this.inputRef.el.focus();
                }
            }, 100);
        }
    }

    dismissSuggestion(suggestion) {
        this.aiSuggestion.dismissSuggestion(suggestion.id);
    }

    async acceptSuggestion(suggestion) {
        await this.aiSuggestion.acceptSuggestion(suggestion.id);
    }

    async executeQuickAction(action) {
        // Open full AI chat client action with the query
        this.action.doAction({
            type: 'ir.actions.client',
            tag: 'loomworks_ai_chat',
            name: _t('AI Assistant'),
            target: 'current',
            params: { initialMessage: action.query },
        });
        this.state.isOpen = false;
    }

    onQuickInputChange(ev) {
        this.state.inputValue = ev.target.value;
    }

    onQuickInputKeydown(ev) {
        if (ev.key === 'Enter' && !ev.shiftKey) {
            ev.preventDefault();
            this.submitQuickInput();
        }
    }

    submitQuickInput() {
        const query = this.state.inputValue.trim();
        if (!query) return;

        this.state.inputValue = "";

        // Open full AI chat client action with the query
        this.action.doAction({
            type: 'ir.actions.client',
            tag: 'loomworks_ai_chat',
            name: _t('AI Assistant'),
            target: 'current',
            params: { initialMessage: query },
        });
        this.state.isOpen = false;
    }

    toggleChat() {
        this.state.chatExpanded = !this.state.chatExpanded;
    }

    openFullChat() {
        // Open full chat in side panel or new view
        this.action.doAction({
            type: 'ir.actions.client',
            tag: 'loomworks_ai_chat',
            name: _t('AI Assistant'),
            target: 'current',
        });
        this.state.isOpen = false;
    }

    openSettings() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'loomworks.ai.user.settings',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: {
                default_user_id: user.userId,
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

    get badgeCount() {
        return this.state.unreadCount || this.state.suggestions.length;
    }

    getPriorityIcon(priority) {
        switch (priority) {
            case 'critical': return 'fa-exclamation-circle text-danger';
            case 'helpful': return 'fa-lightbulb-o text-warning';
            case 'info': return 'fa-info-circle text-info';
            default: return 'fa-comment text-muted';
        }
    }

    getPriorityClass(priority) {
        switch (priority) {
            case 'critical': return 'border-danger';
            case 'helpful': return 'border-warning';
            default: return '';
        }
    }
}

// Register as systray item
export const aiNavbarDropdownItem = {
    Component: AINavbarDropdown,
    isDisplayed: (env) => true,
};

registry.category("systray").add("AINavbarDropdown", aiNavbarDropdownItem, { sequence: 1 });
