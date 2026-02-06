/** @loomworks-module **/
/**
 * Loomworks Field Service Timer Widget
 * Provides a timer control for tracking time spent on FSM tasks
 */

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class FsmTimerWidget extends Component {
    static template = "loomworks_fsm.FsmTimerWidget";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            elapsed: 0,
            isRunning: false,
            isPaused: false,
        });

        this.intervalId = null;

        onMounted(() => {
            this.initializeTimer();
        });

        onWillUnmount(() => {
            this.clearTimerInterval();
        });
    }

    get recordData() {
        return this.props.record.data;
    }

    get timerStart() {
        return this.recordData.timer_start;
    }

    get timerPause() {
        return this.recordData.timer_pause;
    }

    get totalHoursSpent() {
        return this.recordData.total_hours_spent || 0;
    }

    initializeTimer() {
        if (this.timerStart && !this.timerPause) {
            // Timer is running
            this.state.isRunning = true;
            this.state.isPaused = false;
            this.calculateElapsed();
            this.startTimerInterval();
        } else if (this.timerStart && this.timerPause) {
            // Timer is paused
            this.state.isRunning = false;
            this.state.isPaused = true;
            this.calculateElapsed();
        } else {
            // Timer not started - show total hours spent
            this.state.elapsed = Math.floor(this.totalHoursSpent * 3600);
        }
    }

    calculateElapsed() {
        const now = new Date();
        const startTime = new Date(this.timerStart);

        if (this.timerPause) {
            // If paused, calculate time from start to pause
            const pauseTime = new Date(this.timerPause);
            this.state.elapsed = Math.floor((pauseTime - startTime) / 1000);
        } else {
            // If running, calculate time from start to now
            this.state.elapsed = Math.floor((now - startTime) / 1000);
        }

        // Add any previously recorded hours
        this.state.elapsed += Math.floor(this.totalHoursSpent * 3600);
    }

    startTimerInterval() {
        this.clearTimerInterval();
        this.intervalId = setInterval(() => {
            if (this.state.isRunning) {
                this.state.elapsed++;
            }
        }, 1000);
    }

    clearTimerInterval() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }

    formatTime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;

        return [
            hours.toString().padStart(2, '0'),
            minutes.toString().padStart(2, '0'),
            secs.toString().padStart(2, '0')
        ].join(':');
    }

    get displayTime() {
        return this.formatTime(this.state.elapsed);
    }

    get widgetClass() {
        const classes = ['o_fsm_timer_widget'];
        if (this.state.isRunning) {
            classes.push('is-running');
        }
        if (this.state.isPaused) {
            classes.push('is-paused');
        }
        return classes.join(' ');
    }

    async onStartClick() {
        try {
            await this.orm.call(
                "project.task",
                "action_timer_start",
                [[this.props.record.resId]]
            );

            this.state.isRunning = true;
            this.state.isPaused = false;
            this.startTimerInterval();

            this.notification.add("Timer started", { type: "success" });

            // Reload the record to get updated values
            await this.props.record.load();
        } catch (error) {
            this.notification.add("Failed to start timer: " + error.message, { type: "danger" });
        }
    }

    async onPauseClick() {
        try {
            await this.orm.call(
                "project.task",
                "action_timer_pause",
                [[this.props.record.resId]]
            );

            this.state.isRunning = false;
            this.state.isPaused = true;
            this.clearTimerInterval();

            this.notification.add("Timer paused", { type: "warning" });

            await this.props.record.load();
        } catch (error) {
            this.notification.add("Failed to pause timer: " + error.message, { type: "danger" });
        }
    }

    async onResumeClick() {
        try {
            await this.orm.call(
                "project.task",
                "action_timer_resume",
                [[this.props.record.resId]]
            );

            this.state.isRunning = true;
            this.state.isPaused = false;
            this.startTimerInterval();

            this.notification.add("Timer resumed", { type: "success" });

            await this.props.record.load();
        } catch (error) {
            this.notification.add("Failed to resume timer: " + error.message, { type: "danger" });
        }
    }

    async onStopClick() {
        try {
            const result = await this.orm.call(
                "project.task",
                "action_timer_stop",
                [[this.props.record.resId]],
                { create_timesheet: true }
            );

            this.state.isRunning = false;
            this.state.isPaused = false;
            this.clearTimerInterval();

            if (result && result.duration) {
                const durationStr = this.formatTime(Math.floor(result.duration * 3600));
                this.notification.add(
                    `Timer stopped. Duration: ${durationStr}. Timesheet created.`,
                    { type: "success" }
                );
            } else {
                this.notification.add("Timer stopped", { type: "success" });
            }

            await this.props.record.load();
        } catch (error) {
            this.notification.add("Failed to stop timer: " + error.message, { type: "danger" });
        }
    }

    get showStartButton() {
        return !this.state.isRunning && !this.state.isPaused;
    }

    get showPauseButton() {
        return this.state.isRunning;
    }

    get showResumeButton() {
        return this.state.isPaused;
    }

    get showStopButton() {
        return this.state.isRunning || this.state.isPaused;
    }
}

// Register the widget
registry.category("fields").add("fsm_timer", {
    component: FsmTimerWidget,
    supportedTypes: ["float"],
    extractProps: ({ attrs }) => ({
        readonly: attrs.readonly,
    }),
});
