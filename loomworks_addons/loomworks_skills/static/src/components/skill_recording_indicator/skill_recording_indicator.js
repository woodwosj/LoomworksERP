/** @loomworks-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

/**
 * Skill Recording Indicator Component
 *
 * Displays in the systray when skill recording is active.
 * Shows recording duration and action count, with stop button.
 */
export class SkillRecordingIndicator extends Component {
    static template = "loomworks_skills.SkillRecordingIndicator";
    static props = {};

    setup() {
        this.skillRecorder = useService("skillRecorder");
        this.action = useService("action");

        this.state = useState({
            recording: false,
            frameCount: 0,
            duration: 0,
        });

        this.interval = null;

        onMounted(() => {
            this.startPolling();
        });

        onWillUnmount(() => {
            this.stopPolling();
        });
    }

    startPolling() {
        this.interval = setInterval(() => this.updateState(), 500);
    }

    stopPolling() {
        if (this.interval) {
            clearInterval(this.interval);
            this.interval = null;
        }
    }

    updateState() {
        try {
            const recordingState = this.skillRecorder.getRecordingState();
            if (recordingState) {
                this.state.recording = true;
                this.state.frameCount = recordingState.frameCount || 0;
                this.state.duration = Math.floor((recordingState.duration || 0) / 1000);
            } else {
                this.state.recording = false;
                this.state.frameCount = 0;
                this.state.duration = 0;
            }
        } catch (e) {
            // Service might not be ready yet
            this.state.recording = false;
        }
    }

    formatDuration(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return mins > 0
            ? `${mins}:${secs.toString().padStart(2, '0')}`
            : `${secs}s`;
    }

    async onStopClick() {
        try {
            const recording = await this.skillRecorder.stopRecording();

            // Navigate to skill creation wizard with recording data
            await this.action.doAction({
                type: 'ir.actions.act_window',
                res_model: 'loomworks.skill.creation.wizard',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    default_creation_method: 'recording',
                    default_recording_data: JSON.stringify(recording),
                },
            });
        } catch (e) {
            console.error("Failed to stop recording:", e);
        }
    }

    async onStartClick() {
        try {
            await this.skillRecorder.startRecording();
        } catch (e) {
            console.error("Failed to start recording:", e);
        }
    }
}

// Register as systray item
registry.category("systray").add("skillRecordingIndicator", {
    Component: SkillRecordingIndicator,
}, { sequence: 5 });
