/** @loomworks-module **/
// Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
// License: LGPL-3

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { AIMessage } from "../ai_message/ai_message";

/**
 * Main AI Chat component providing conversational interface.
 *
 * Features:
 * - Message history display
 * - Streaming response rendering
 * - Tool call visualization
 * - Session management
 * - Keyboard shortcuts
 */
export class AIChat extends Component {
    static template = "loomworks_ai.AIChat";
    static components = { AIMessage };
    static props = {
        ...standardActionServiceProps,
        sessionUuid: { type: String, optional: true },
        agentId: { type: Number, optional: true },
        onClose: { type: Function, optional: true },
    };

    setup() {
        // Services
        this.notification = useService("notification");

        // Extract initial message from client action params (if opened via doAction)
        const actionParams = this.props.action?.params || {};
        this.initialMessage = actionParams.initialMessage || null;

        // State
        this.state = useState({
            messages: [],
            inputText: "",
            isLoading: false,
            isConnected: false,
            sessionUuid: this.props.sessionUuid || null,
            agentName: "",
            error: null,
            streamingContent: "",
            operations: [],
            hasUncommittedChanges: false,
        });

        // Refs
        this.messagesRef = useRef("messages");
        this.inputRef = useRef("input");

        // Lifecycle
        onMounted(() => this.onMounted());
        onWillUnmount(() => this.onWillUnmount());
    }

    async onMounted() {
        // Initialize or resume session
        if (this.state.sessionUuid) {
            await this.loadSession();
        } else {
            await this.createSession();
        }

        // If we have an initial message (from navbar input), send it automatically
        if (this.initialMessage && this.state.isConnected) {
            const message = this.initialMessage;
            this.initialMessage = null; // Clear to prevent re-send
            // Use a short delay so the welcome message renders first
            setTimeout(() => {
                this.state.inputText = message;
                this.sendMessage();
            }, 300);
        }

        // Focus input
        if (this.inputRef.el) {
            this.inputRef.el.focus();
        }

        // Keyboard shortcut handler
        this.keyHandler = (e) => this.handleKeyboard(e);
        document.addEventListener("keydown", this.keyHandler);
    }

    onWillUnmount() {
        // Cleanup
        document.removeEventListener("keydown", this.keyHandler);
    }

    // =========================================================================
    // SESSION MANAGEMENT
    // =========================================================================

    async createSession() {
        try {
            const result = await rpc("/loomworks/ai/session/create", {
                agent_id: this.props.agentId,
            });

            if (result.error) {
                this.state.error = result.error;
                return;
            }

            this.state.sessionUuid = result.uuid;
            this.state.agentName = result.agent_name;
            this.state.isConnected = true;

            // Add welcome message
            this.addSystemMessage(
                `Connected to ${result.agent_name}. How can I help you today?`
            );

        } catch (error) {
            this.state.error = "Failed to create session";
            console.error("Session creation error:", error);
        }
    }

    async loadSession() {
        try {
            const result = await rpc(
                `/loomworks/ai/session/${this.state.sessionUuid}`,
                {}
            );

            if (result.error) {
                this.state.error = result.error;
                return;
            }

            this.state.agentName = result.agent_name;
            this.state.messages = result.messages.map(m => ({
                id: m.id,
                role: m.role,
                content: m.content,
                timestamp: new Date(m.timestamp),
                hasToolCalls: m.has_tool_calls,
            }));
            this.state.hasUncommittedChanges = result.has_uncommitted_changes;
            this.state.isConnected = true;

            this.scrollToBottom();

        } catch (error) {
            this.state.error = "Failed to load session";
            console.error("Session load error:", error);
        }
    }

    async closeSession() {
        if (!this.state.sessionUuid) return;

        try {
            await rpc(
                `/loomworks/ai/session/${this.state.sessionUuid}/close`,
                {}
            );

            if (this.props.onClose) {
                this.props.onClose();
            }

        } catch (error) {
            console.error("Session close error:", error);
        }
    }

    // =========================================================================
    // MESSAGE HANDLING
    // =========================================================================

    async sendMessage() {
        const text = this.state.inputText.trim();
        if (!text || this.state.isLoading) return;

        // Add user message
        this.addMessage("user", text);
        this.state.inputText = "";
        this.state.isLoading = true;
        this.state.error = null;

        try {
            // Use streaming endpoint
            await this.sendMessageStreaming(text);
        } catch (error) {
            this.state.error = "Failed to send message";
            console.error("Send message error:", error);
        } finally {
            this.state.isLoading = false;
        }
    }

    async sendMessageStreaming(text) {
        return new Promise((resolve, reject) => {
            // Start with empty streaming content
            this.state.streamingContent = "";

            // Create fetch request for SSE
            fetch("/loomworks/ai/chat/stream", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    session_uuid: this.state.sessionUuid,
                    message: text,
                }),
                credentials: "same-origin",
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const reader = response.body.getReader();
                const decoder = new TextDecoder();

                const processStream = async () => {
                    let buffer = "";
                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;

                        buffer += decoder.decode(value, { stream: true });
                        const lines = buffer.split("\n");
                        buffer = lines.pop() || "";  // Keep incomplete line in buffer

                        for (const line of lines) {
                            if (line.startsWith("data: ")) {
                                try {
                                    const data = JSON.parse(line.slice(6));
                                    this.handleStreamChunk(data);
                                } catch (e) {
                                    console.error("Error parsing SSE data:", e);
                                }
                            }
                        }
                    }
                };

                return processStream();
            })
            .then(() => {
                // Finalize message
                if (this.state.streamingContent) {
                    this.addMessage("assistant", this.state.streamingContent);
                    this.state.streamingContent = "";
                }
                resolve();
            })
            .catch(error => {
                // Fallback to sync endpoint
                console.warn("Streaming failed, falling back to sync:", error);
                this.sendMessageSync(text).then(resolve).catch(reject);
            });
        });
    }

    async sendMessageSync(text) {
        const result = await rpc("/loomworks/ai/chat", {
            session_uuid: this.state.sessionUuid,
            message: text,
        });

        if (result.error) {
            this.state.error = result.error;
            return;
        }

        this.addMessage("assistant", result.response);
        this.state.operations = result.operations || [];
        this.state.hasUncommittedChanges = result.has_uncommitted_changes || false;
    }

    handleStreamChunk(data) {
        switch (data.type) {
            case "text":
                this.state.streamingContent += data.content;
                this.scrollToBottom();
                break;

            case "tool_call":
                // Show tool call indicator
                this.addSystemMessage(
                    `Executing: ${data.tool}`,
                    { isToolCall: true, toolInput: data.input }
                );
                break;

            case "tool_result":
                // Could show tool result if needed
                break;

            case "error":
                this.state.error = data.content;
                break;

            case "done":
                // Handle completion
                if (data.operations) {
                    this.state.operations = data.operations;
                }
                break;
        }
    }

    addMessage(role, content, metadata = {}) {
        this.state.messages.push({
            id: Date.now(),
            role,
            content,
            timestamp: new Date(),
            ...metadata,
        });
        this.scrollToBottom();
    }

    addSystemMessage(content, metadata = {}) {
        this.addMessage("system", content, metadata);
    }

    // =========================================================================
    // ROLLBACK
    // =========================================================================

    async rollback() {
        if (!this.state.hasUncommittedChanges) {
            this.notification.add("No changes to rollback", { type: "warning" });
            return;
        }

        try {
            const result = await rpc(
                `/loomworks/ai/session/${this.state.sessionUuid}/rollback`,
                {}
            );

            if (result.success) {
                this.notification.add("Changes rolled back successfully", { type: "success" });
                this.state.hasUncommittedChanges = false;
                this.addSystemMessage("All recent changes have been rolled back.");
            } else {
                this.notification.add(result.error, { type: "danger" });
            }

        } catch (error) {
            this.notification.add("Rollback failed", { type: "danger" });
        }
    }

    // =========================================================================
    // UI HELPERS
    // =========================================================================

    scrollToBottom() {
        requestAnimationFrame(() => {
            if (this.messagesRef.el) {
                this.messagesRef.el.scrollTop = this.messagesRef.el.scrollHeight;
            }
        });
    }

    handleKeyboard(e) {
        // Ctrl+Enter to send
        if (e.ctrlKey && e.key === "Enter") {
            this.sendMessage();
        }

        // Escape to close
        if (e.key === "Escape" && this.props.onClose) {
            this.closeSession();
        }

        // Ctrl+Z for rollback
        if (e.ctrlKey && e.key === "z" && this.state.hasUncommittedChanges) {
            e.preventDefault();
            this.rollback();
        }
    }

    onInputKeydown(e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            this.sendMessage();
        }
    }

    onInputChange(e) {
        this.state.inputText = e.target.value;
    }

    get formattedOperations() {
        return this.state.operations.map(op => ({
            ...op,
            icon: this.getOperationIcon(op.type),
            label: `${op.type} ${op.record_count || ''} ${op.model || ''}`.trim(),
        }));
    }

    getOperationIcon(type) {
        const icons = {
            search: "fa-search",
            create: "fa-plus",
            write: "fa-edit",
            unlink: "fa-trash",
            action: "fa-play",
            report: "fa-chart-bar",
        };
        return icons[type] || "fa-cog";
    }
}

// Register as a client action so it can be opened via doAction({ tag: 'loomworks_ai_chat' })
registry.category("actions").add("loomworks_ai_chat", AIChat);
