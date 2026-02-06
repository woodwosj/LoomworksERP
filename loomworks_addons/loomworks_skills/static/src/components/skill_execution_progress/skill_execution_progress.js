/** @loomworks-module **/

import { Component, useState, onWillStart, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Skill Execution Progress Component
 *
 * Shows real-time progress of a skill execution, including:
 * - Current step being executed
 * - Progress bar
 * - Step results
 * - Input prompts when needed
 */
export class SkillExecutionProgress extends Component {
    static template = "loomworks_skills.SkillExecutionProgress";
    static props = {
        executionId: { type: Number },
        onComplete: { type: Function, optional: true },
        onCancel: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            execution: null,
            loading: true,
            error: null,
            userInput: "",
        });

        this.pollInterval = null;

        onWillStart(async () => {
            await this.loadExecution();
            this.startPolling();
        });

        onWillUnmount(() => {
            this.stopPolling();
        });
    }

    async loadExecution() {
        try {
            const executions = await this.orm.searchRead(
                'loomworks.skill.execution',
                [['id', '=', this.props.executionId]],
                [
                    'skill_id', 'skill_name', 'state', 'steps_completed',
                    'steps_total', 'pending_input_prompt', 'pending_input_type',
                    'pending_input_options', 'error_message', 'result_summary',
                    'duration_ms'
                ]
            );

            if (executions.length > 0) {
                this.state.execution = executions[0];

                // Check if completed
                if (['completed', 'failed', 'cancelled', 'rolled_back'].includes(this.state.execution.state)) {
                    this.stopPolling();
                    if (this.props.onComplete) {
                        this.props.onComplete(this.state.execution);
                    }
                }
            } else {
                this.state.error = "Execution not found";
            }
        } catch (e) {
            console.error("Failed to load execution:", e);
            this.state.error = e.message;
        } finally {
            this.state.loading = false;
        }
    }

    startPolling() {
        if (this.pollInterval) return;

        this.pollInterval = setInterval(async () => {
            if (this.state.execution && !this.isCompleted) {
                await this.loadExecution();
            }
        }, 1000);
    }

    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }

    get isCompleted() {
        const finalStates = ['completed', 'failed', 'cancelled', 'rolled_back'];
        return this.state.execution && finalStates.includes(this.state.execution.state);
    }

    get isWaitingInput() {
        return this.state.execution?.state === 'waiting_input';
    }

    get progressPercent() {
        const exec = this.state.execution;
        if (!exec || !exec.steps_total) return 0;
        return Math.round((exec.steps_completed / exec.steps_total) * 100);
    }

    get stateClass() {
        const stateClasses = {
            pending: 'text-secondary',
            running: 'text-primary',
            waiting_input: 'text-warning',
            completed: 'text-success',
            failed: 'text-danger',
            cancelled: 'text-secondary',
            rolled_back: 'text-warning',
        };
        return stateClasses[this.state.execution?.state] || '';
    }

    get stateIcon() {
        const stateIcons = {
            pending: 'fa-clock-o',
            running: 'fa-spinner fa-spin',
            waiting_input: 'fa-question-circle',
            completed: 'fa-check-circle',
            failed: 'fa-times-circle',
            cancelled: 'fa-ban',
            rolled_back: 'fa-undo',
        };
        return stateIcons[this.state.execution?.state] || 'fa-circle';
    }

    get inputOptions() {
        if (!this.state.execution?.pending_input_options) return [];
        try {
            return JSON.parse(this.state.execution.pending_input_options);
        } catch {
            return [];
        }
    }

    onInputChange(ev) {
        this.state.userInput = ev.target.value;
    }

    onOptionSelect(option) {
        this.state.userInput = option;
        this.submitInput();
    }

    async submitInput() {
        if (!this.state.userInput && this.state.execution?.pending_input_type !== 'boolean') {
            return;
        }

        let value = this.state.userInput;

        // Type conversion
        const inputType = this.state.execution?.pending_input_type;
        if (inputType === 'number') {
            value = parseFloat(value);
        } else if (inputType === 'boolean') {
            value = this.state.userInput === 'true' || this.state.userInput === true;
        }

        try {
            await this.orm.call(
                'loomworks.skill.execution',
                'provide_input',
                [[this.props.executionId], value]
            );

            this.state.userInput = "";
            await this.loadExecution();
        } catch (e) {
            console.error("Failed to submit input:", e);
            this.notification.add(`Failed to submit: ${e.message}`, { type: "danger" });
        }
    }

    async cancelExecution() {
        try {
            await this.orm.call(
                'loomworks.skill.execution',
                'cancel_execution',
                [[this.props.executionId], "Cancelled by user"]
            );

            await this.loadExecution();

            if (this.props.onCancel) {
                this.props.onCancel();
            }
        } catch (e) {
            console.error("Failed to cancel:", e);
            this.notification.add(`Failed to cancel: ${e.message}`, { type: "danger" });
        }
    }

    formatDuration(ms) {
        if (!ms) return '-';
        if (ms < 1000) return `${ms}ms`;
        return `${(ms / 1000).toFixed(1)}s`;
    }
}
