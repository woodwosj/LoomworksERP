/** @odoo-module **/
/**
 * Loomworks Planning Gantt View Enhancements
 * Extends the core Gantt view with planning-specific functionality
 */

import { Component, useState, useRef, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * Planning Gantt Controller Extension
 * Adds conflict detection highlighting and quick actions
 */
export class PlanningGanttController extends Component {
    static template = "loomworks_planning.PlanningGanttController";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.dialog = useService("dialog");

        this.state = useState({
            showConflicts: true,
            conflictCount: 0,
        });

        onMounted(() => {
            this.loadConflictCount();
        });
    }

    async loadConflictCount() {
        try {
            const count = await this.orm.searchCount(
                "planning.slot",
                [["has_conflict", "=", true], ["state", "not in", ["cancelled", "done"]]]
            );
            this.state.conflictCount = count;
        } catch (error) {
            console.error("Error loading conflict count:", error);
        }
    }

    async onPublishAll() {
        try {
            const domain = this.props.model.domain || [];
            const slots = await this.orm.search("planning.slot", [
                ...domain,
                ["state", "=", "draft"],
                ["has_conflict", "=", false],
            ]);

            if (slots.length === 0) {
                this.notification.add("No draft slots without conflicts to publish", {
                    type: "warning",
                });
                return;
            }

            await this.orm.call("planning.slot", "action_publish", [slots]);
            this.notification.add(`Published ${slots.length} slots`, { type: "success" });

            // Reload the view
            this.props.model.load();
        } catch (error) {
            this.notification.add("Error publishing slots: " + error.message, {
                type: "danger",
            });
        }
    }

    async onQuickCreate() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Quick Create Shifts",
            res_model: "planning.slot.quick.create",
            view_mode: "form",
            target: "new",
        });
    }

    async onViewConflicts() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Scheduling Conflicts",
            res_model: "planning.slot",
            view_mode: "list,form,gantt",
            domain: [["has_conflict", "=", true]],
        });
    }

    toggleConflictHighlight() {
        this.state.showConflicts = !this.state.showConflicts;
        // Trigger re-render with conflict classes
        if (this.props.model) {
            this.props.model.notify();
        }
    }
}

/**
 * Planning Gantt Popup Component
 * Shows detailed slot information on hover/click
 */
export class PlanningGanttPopup extends Component {
    static template = "loomworks_planning.PlanningGanttPopup";
    static props = {
        slot: Object,
        onClose: Function,
    };

    get slot() {
        return this.props.slot;
    }

    get statusClass() {
        const statusClasses = {
            draft: "badge text-bg-info",
            published: "badge text-bg-success",
            done: "badge text-bg-primary",
            cancelled: "badge text-bg-secondary",
        };
        return statusClasses[this.slot.state] || "badge text-bg-secondary";
    }

    get conflictClass() {
        return this.slot.has_conflict ? "text-danger" : "text-success";
    }

    formatDateTime(dt) {
        if (!dt) return "";
        const date = new Date(dt);
        return date.toLocaleString("en-US", {
            weekday: "short",
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
    }

    formatHours(hours) {
        const h = Math.floor(hours);
        const m = Math.round((hours - h) * 60);
        return m > 0 ? `${h}h ${m}m` : `${h}h`;
    }
}

/**
 * Planning utility functions
 */
export const planningUtils = {
    /**
     * Calculate if two time ranges overlap
     */
    hasOverlap(start1, end1, start2, end2) {
        return start1 < end2 && start2 < end1;
    },

    /**
     * Get color class for role
     */
    getRoleColorClass(colorIndex) {
        return `o_gantt_color_${colorIndex || 0}`;
    },

    /**
     * Format duration for display
     */
    formatDuration(hours) {
        if (hours < 1) {
            return `${Math.round(hours * 60)}m`;
        }
        const h = Math.floor(hours);
        const m = Math.round((hours - h) * 60);
        return m > 0 ? `${h}h ${m}m` : `${h}h`;
    },

    /**
     * Get week number from date
     */
    getWeekNumber(date) {
        const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
        const dayNum = d.getUTCDay() || 7;
        d.setUTCDate(d.getUTCDate() + 4 - dayNum);
        const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
        return Math.ceil(((d - yearStart) / 86400000 + 1) / 7);
    },

    /**
     * Generate time slots for a day
     */
    generateTimeSlots(startHour, endHour, intervalMinutes = 30) {
        const slots = [];
        for (let hour = startHour; hour < endHour; hour++) {
            for (let minute = 0; minute < 60; minute += intervalMinutes) {
                slots.push({
                    hour,
                    minute,
                    label: `${hour.toString().padStart(2, "0")}:${minute.toString().padStart(2, "0")}`,
                });
            }
        }
        return slots;
    },
};

// Register components
registry.category("views").add("planning_gantt_controller", PlanningGanttController);
