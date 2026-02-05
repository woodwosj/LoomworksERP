/** @odoo-module **/
/**
 * Dashboard Action Component
 *
 * Owl component that serves as the bridge between Odoo's action system
 * and the React dashboard canvas. Handles:
 * - Loading dashboard data from server
 * - Mounting the React DashboardApp component
 * - Coordinating between Owl services and React
 */

import { Component, onMounted, onWillUnmount, useState, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class DashboardAction extends Component {
    static template = "loomworks_dashboard.DashboardAction";
    static props = {
        action: { type: Object, optional: true },
        actionId: { type: Number, optional: true },
        // Allow passing dashboard_id directly
        "*": true,
    };

    setup() {
        // Services
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.action = useService("action");
        this.orm = useService("orm");
        this.user = useService("user");

        // Refs
        this.containerRef = useRef("dashboardContainer");
        this.reactRoot = null;

        // State
        this.state = useState({
            isLoading: true,
            dashboardId: null,
            dashboardData: null,
            error: null,
            isEditing: false,
        });

        // Get dashboard ID from action params
        this.state.dashboardId = this._getDashboardId();

        onMounted(async () => {
            await this.loadDashboard();
            this.mountReactApp();
        });

        onWillUnmount(() => {
            this.unmountReactApp();
        });
    }

    /**
     * Extract dashboard ID from various sources
     */
    _getDashboardId() {
        // From action params
        if (this.props.action?.params?.dashboard_id) {
            return this.props.action.params.dashboard_id;
        }
        // From context
        if (this.props.action?.context?.dashboard_id) {
            return this.props.action.context.dashboard_id;
        }
        // Direct prop
        if (this.props.dashboard_id) {
            return this.props.dashboard_id;
        }
        return null;
    }

    /**
     * Load dashboard data from server
     */
    async loadDashboard() {
        this.state.isLoading = true;
        this.state.error = null;

        try {
            if (!this.state.dashboardId) {
                // Show dashboard selector or create new
                this.state.isLoading = false;
                return;
            }

            const response = await this.rpc("/loomworks/dashboard/" + this.state.dashboardId);

            if (response.error) {
                throw new Error(response.error);
            }

            this.state.dashboardData = response;
            this.state.isLoading = false;
        } catch (error) {
            this.state.error = error.message || "Failed to load dashboard";
            this.state.isLoading = false;
            this.notification.add(this.state.error, { type: "danger" });
        }
    }

    /**
     * Mount the React dashboard app
     */
    mountReactApp() {
        if (!this.containerRef.el || this.state.error) {
            return;
        }

        // Check if React is available (loaded by loomworks_spreadsheet)
        if (typeof React === "undefined" || typeof ReactDOM === "undefined") {
            console.error("React not loaded. Ensure loomworks_spreadsheet is installed.");
            this.state.error = "React library not available";
            return;
        }

        try {
            // Create React root
            this.reactRoot = ReactDOM.createRoot(this.containerRef.el);

            // Render the React dashboard app
            const props = {
                dashboardId: this.state.dashboardId,
                dashboardData: this.state.dashboardData,
                mode: this.state.isEditing ? "edit" : "view",
                onSave: this.handleSave.bind(this),
                onWidgetAction: this.handleWidgetAction.bind(this),
                onFetchData: this.fetchWidgetData.bind(this),
                onModeChange: this.handleModeChange.bind(this),
                odooServices: {
                    rpc: this.rpc,
                    notification: this.notification,
                    action: this.action,
                    orm: this.orm,
                    user: this.user,
                },
            };

            // DashboardApp should be registered globally by the React bundle
            if (typeof window.LoomworksDashboardApp !== "undefined") {
                this.reactRoot.render(
                    React.createElement(window.LoomworksDashboardApp, props)
                );
            } else {
                console.warn("LoomworksDashboardApp not found, using fallback");
                this.renderFallback();
            }
        } catch (error) {
            console.error("Failed to mount React app:", error);
            this.state.error = "Failed to initialize dashboard";
        }
    }

    /**
     * Render fallback when React app is not available
     */
    renderFallback() {
        if (!this.containerRef.el) return;

        this.containerRef.el.innerHTML = `
            <div class="lw-dashboard-fallback">
                <div class="lw-dashboard-fallback-content">
                    <i class="fa fa-tachometer fa-4x text-muted mb-3"></i>
                    <h3>Dashboard: ${this.state.dashboardData?.name || "Loading..."}</h3>
                    <p class="text-muted">
                        ${this.state.dashboardData?.description || "Interactive dashboard canvas"}
                    </p>
                    <p class="text-warning">
                        <i class="fa fa-exclamation-triangle"></i>
                        React dashboard components are loading...
                    </p>
                </div>
            </div>
        `;
    }

    /**
     * Unmount React app
     */
    unmountReactApp() {
        if (this.reactRoot) {
            this.reactRoot.unmount();
            this.reactRoot = null;
        }
    }

    /**
     * Handle save from React canvas
     */
    async handleSave(canvasData) {
        try {
            const response = await this.rpc(
                "/loomworks/dashboard/" + this.state.dashboardId + "/save",
                canvasData
            );

            if (response.error) {
                throw new Error(response.error);
            }

            this.notification.add("Dashboard saved", { type: "success" });
            return true;
        } catch (error) {
            this.notification.add("Failed to save dashboard: " + error.message, {
                type: "danger",
            });
            return false;
        }
    }

    /**
     * Handle widget actions (drill-down, open record, etc.)
     */
    async handleWidgetAction(actionData) {
        if (actionData.type === "open_record") {
            await this.action.doAction({
                type: "ir.actions.act_window",
                res_model: actionData.model,
                res_id: actionData.resId,
                views: [[false, "form"]],
            });
        } else if (actionData.type === "open_list") {
            await this.action.doAction({
                type: "ir.actions.act_window",
                res_model: actionData.model,
                domain: actionData.domain || [],
                views: [[false, "list"], [false, "form"]],
            });
        } else if (actionData.type === "custom_action") {
            await this.action.doAction(actionData.actionId);
        }
    }

    /**
     * Fetch data for a widget
     */
    async fetchWidgetData(widgetId, filters = {}) {
        try {
            const response = await this.rpc(
                "/loomworks/dashboard/widget/" + widgetId + "/data",
                { filters }
            );

            if (response.error) {
                throw new Error(response.error);
            }

            return response.data;
        } catch (error) {
            console.error("Failed to fetch widget data:", error);
            return null;
        }
    }

    /**
     * Handle mode change (view/edit)
     */
    handleModeChange(mode) {
        this.state.isEditing = mode === "edit";
    }

    /**
     * Toggle edit mode
     */
    toggleEditMode() {
        this.state.isEditing = !this.state.isEditing;
        // Re-mount React with new mode
        this.unmountReactApp();
        this.mountReactApp();
    }

    /**
     * Create new dashboard
     */
    async createDashboard() {
        try {
            const response = await this.rpc("/loomworks/dashboard/create", {
                name: "New Dashboard",
            });

            if (response.error) {
                throw new Error(response.error);
            }

            this.state.dashboardId = response.dashboard_id;
            await this.loadDashboard();
            this.unmountReactApp();
            this.mountReactApp();
        } catch (error) {
            this.notification.add("Failed to create dashboard: " + error.message, {
                type: "danger",
            });
        }
    }

    /**
     * Generate dashboard from prompt
     */
    async generateFromPrompt(prompt) {
        try {
            const response = await this.rpc("/loomworks/dashboard/generate", {
                prompt,
            });

            if (response.error) {
                throw new Error(response.error);
            }

            this.state.dashboardId = response.dashboard_id;
            await this.loadDashboard();
            this.unmountReactApp();
            this.mountReactApp();

            this.notification.add(
                `Generated dashboard with ${response.widget_count || 0} widgets`,
                { type: "success" }
            );
        } catch (error) {
            this.notification.add("Failed to generate dashboard: " + error.message, {
                type: "danger",
            });
        }
    }

    /**
     * Refresh dashboard data
     */
    async refreshDashboard() {
        await this.loadDashboard();
        this.unmountReactApp();
        this.mountReactApp();
    }

    /**
     * Open dashboard settings
     */
    openSettings() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "dashboard.board",
            res_id: this.state.dashboardId,
            views: [[false, "form"]],
            target: "new",
        });
    }

    /**
     * Export dashboard
     */
    async exportDashboard(format = "png") {
        this.notification.add("Export feature coming soon", { type: "info" });
    }
}

// Register as an action
registry.category("actions").add("loomworks_dashboard_action", DashboardAction);
