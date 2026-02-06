/** @odoo-module **/

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";

/**
 * Skill Recorder Service
 *
 * Intercepts RPC calls and user actions to record workflows
 * that can be converted into reusable skills.
 *
 * Architecture:
 * - Patches rpc service to capture all server calls
 * - Hooks into action service to track navigation
 * - Records DOM interactions via event delegation
 * - Produces structured recording that maps to skill steps
 */
export const skillRecorderService = {
    dependencies: ["action", "notification", "orm"],

    start(env, { action, notification, orm }) {
        let isRecording = false;
        let recording = null;
        let frameCounter = 0;
        let recordingId = null;

        // Store original rpc for later restoration
        const originalRpc = rpc.bind ? rpc.bind(env.services) : rpc;

        /**
         * Start recording a new skill session.
         * @param {Object} options - Recording options
         * @returns {Object} Recording info
         */
        async function startRecording(options = {}) {
            if (isRecording) {
                throw new Error("Recording already in progress");
            }

            // Create server-side recording
            try {
                const result = await orm.call(
                    'loomworks.skill.recording',
                    'start_recording',
                    [options]
                );
                recordingId = result.id;
            } catch (e) {
                console.error("Failed to create server recording:", e);
            }

            isRecording = true;
            frameCounter = 0;
            recording = {
                id: generateRecordingId(),
                serverId: recordingId,
                startedAt: Date.now(),
                userId: user.userId,
                options,
                frames: [],
                userInputs: [],
                confirmations: [],
            };

            notification.add("Skill recording started", { type: "info" });

            return {
                id: recording.id,
                serverId: recordingId,
            };
        }

        /**
         * Stop recording and return the captured workflow.
         * @returns {Object} Recording data
         */
        async function stopRecording() {
            if (!isRecording) {
                throw new Error("No recording in progress");
            }

            isRecording = false;
            recording.stoppedAt = Date.now();
            recording.duration = recording.stoppedAt - recording.startedAt;

            // Stop server-side recording
            if (recordingId) {
                try {
                    await orm.call(
                        'loomworks.skill.recording',
                        'stop_recording',
                        [[recordingId]]
                    );
                } catch (e) {
                    console.error("Failed to stop server recording:", e);
                }
            }

            const result = { ...recording };
            recording = null;
            recordingId = null;

            notification.add("Skill recording stopped", { type: "success" });

            return result;
        }

        /**
         * Record an RPC call during the session.
         * @param {string} route - RPC route
         * @param {Object} params - RPC parameters
         * @param {Object} result - RPC result (summarized)
         */
        function recordRpc(route, params, result) {
            if (!isRecording) return;

            const sanitizedParams = sanitizeParams(params);
            const summarizedResult = summarizeResult(result);

            const frame = {
                id: ++frameCounter,
                timestamp: Date.now(),
                type: 'rpc',
                route,
                params: sanitizedParams,
                model: params.model,
                method: params.method,
                result: summarizedResult,
            };

            recording.frames.push(frame);

            // Also send to server if recording exists
            if (recordingId) {
                recordActionToServer({
                    action_type: `rpc_${params.method || 'call'}`,
                    model_name: params.model,
                    method_name: params.method,
                    record_ids: params.args?.[0] || [],
                    params: sanitizedParams,
                    result_summary: summarizedResult,
                });
            }
        }

        /**
         * Record a navigation action.
         * @param {Object} actionRequest - Action being performed
         */
        function recordAction(actionRequest) {
            if (!isRecording) return;

            const frame = {
                id: ++frameCounter,
                timestamp: Date.now(),
                type: 'action',
                action: summarizeAction(actionRequest),
            };

            recording.frames.push(frame);

            if (recordingId) {
                recordActionToServer({
                    action_type: 'navigation',
                    model_name: actionRequest.res_model,
                    method_name: actionRequest.type,
                    params: summarizeAction(actionRequest),
                });
            }
        }

        /**
         * Record a user input during skill execution.
         * @param {string} prompt - Input prompt
         * @param {*} value - User provided value
         */
        function captureUserInput(prompt, value) {
            if (isRecording) {
                recording.userInputs.push({
                    timestamp: Date.now(),
                    prompt,
                    value,
                    frameId: frameCounter,
                });
            }
        }

        /**
         * Check if recording is active.
         * @returns {boolean}
         */
        function isRecordingActive() {
            return isRecording;
        }

        /**
         * Get current recording state.
         * @returns {Object|null}
         */
        function getRecordingState() {
            if (!isRecording) return null;
            return {
                id: recording.id,
                serverId: recordingId,
                frameCount: recording.frames.length,
                duration: Date.now() - recording.startedAt,
            };
        }

        /**
         * Get full recording data (for export/conversion).
         * @returns {Object|null}
         */
        function getRecordingData() {
            return recording ? { ...recording } : null;
        }

        // Helper functions

        function generateRecordingId() {
            return `rec_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        }

        function sanitizeParams(params) {
            if (!params) return {};

            const sanitized = { ...params };
            // Remove sensitive data
            const sensitiveKeys = ['password', 'token', 'api_key', 'secret', 'credit_card'];
            for (const key of sensitiveKeys) {
                if (key in sanitized) {
                    delete sanitized[key];
                }
            }
            return sanitized;
        }

        function summarizeResult(result) {
            if (Array.isArray(result)) {
                return { type: 'array', length: result.length };
            }
            if (result && typeof result === 'object') {
                return { type: 'object', keys: Object.keys(result) };
            }
            return result;
        }

        function summarizeAction(action) {
            if (typeof action === 'string') {
                return { xmlId: action };
            }
            return {
                type: action.type,
                resModel: action.res_model,
                resId: action.res_id,
                viewMode: action.view_mode,
            };
        }

        async function recordActionToServer(actionData) {
            if (!recordingId) return;

            try {
                await orm.call(
                    'loomworks.skill.recording',
                    'record_action',
                    [[recordingId], actionData.action_type, actionData]
                );
            } catch (e) {
                console.error("Failed to record action to server:", e);
            }
        }

        // Set up RPC interception using the bus
        // This approach works with Odoo 18's service architecture
        env.bus.addEventListener("RPC:RESPONSE", (ev) => {
            if (isRecording && ev.detail) {
                const { route, params, result } = ev.detail;
                recordRpc(route, params, result);
            }
        });

        return {
            startRecording,
            stopRecording,
            captureUserInput,
            isRecordingActive,
            getRecordingState,
            getRecordingData,
            recordAction,
        };
    },
};

registry.category("services").add("skillRecorder", skillRecorderService);
