/** @odoo-module **/
// Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
// License: LGPL-3

import { Component } from "@odoo/owl";

/**
 * AI Message component for displaying individual chat messages.
 *
 * Handles different message types:
 * - user: User-sent messages (right-aligned)
 * - assistant: AI responses (left-aligned)
 * - system: System notifications (centered)
 * - tool: Tool execution results (styled differently)
 */
export class AIMessage extends Component {
    static template = "loomworks_ai.AIMessage";
    static props = {
        role: { type: String },
        content: { type: String },
        timestamp: { type: [Date, { value: null }], optional: true },
        isStreaming: { type: Boolean, optional: true },
        isToolCall: { type: Boolean, optional: true },
        toolInput: { type: Object, optional: true },
    };

    get messageClass() {
        const classes = ["ai-message"];
        classes.push(`ai-message-${this.props.role}`);
        if (this.props.isStreaming) {
            classes.push("streaming");
        }
        if (this.props.isToolCall) {
            classes.push("tool-call");
        }
        return classes.join(" ");
    }

    get formattedTime() {
        if (!this.props.timestamp) return "";
        const date = this.props.timestamp instanceof Date
            ? this.props.timestamp
            : new Date(this.props.timestamp);
        return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    }

    get roleIcon() {
        const icons = {
            user: "fa-user",
            assistant: "fa-robot",
            system: "fa-info-circle",
            tool: "fa-cog",
        };
        return icons[this.props.role] || "fa-comment";
    }

    get roleLabel() {
        const labels = {
            user: "You",
            assistant: "AI",
            system: "System",
            tool: "Tool",
        };
        return labels[this.props.role] || this.props.role;
    }
}
