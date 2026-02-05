/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Skill Intent Service
 *
 * Provides natural language intent matching in the web client,
 * enabling AI chat interfaces and voice commands to trigger skills.
 */
export const skillIntentService = {
    dependencies: ["orm", "action", "notification"],

    start(env, { orm, action, notification }) {

        /**
         * Match user input against available skills.
         * @param {string} userInput - Natural language text
         * @returns {Object} Match result with skill_id, confidence, params
         */
        async function matchIntent(userInput) {
            try {
                const result = await orm.call(
                    'loomworks.skill',
                    'match_intent',
                    [userInput]
                );
                return result;
            } catch (e) {
                console.error("Intent matching failed:", e);
                return {
                    skill_id: null,
                    confidence: 0,
                    params: {},
                    error: e.message,
                };
            }
        }

        /**
         * Execute a skill with given context.
         * @param {number} skillId - Skill ID to execute
         * @param {Object} context - Execution context
         * @returns {Object} Execution result
         */
        async function executeSkill(skillId, context = {}) {
            try {
                const result = await orm.call(
                    'loomworks.skill',
                    'action_execute',
                    [[skillId], context]
                );

                // Handle different result types
                if (result.type === 'skill.input_required') {
                    // Skill needs user input
                    return result;
                } else if (result.type === 'skill.completed') {
                    notification.add(`Skill completed: ${result.summary || 'Success'}`, {
                        type: "success",
                    });
                    return result;
                } else if (result.type === 'ir.actions.act_window') {
                    // Skill returned an action to execute
                    await action.doAction(result);
                    return { type: 'action_executed', action: result };
                }

                return result;
            } catch (e) {
                console.error("Skill execution failed:", e);
                notification.add(`Skill failed: ${e.message || e}`, {
                    type: "danger",
                });
                return {
                    success: false,
                    error: e.message,
                };
            }
        }

        /**
         * Resume a paused execution with user input.
         * @param {number} executionId - Execution ID
         * @param {*} userInput - User provided value
         * @returns {Object} Execution result
         */
        async function resumeExecution(executionId, userInput) {
            try {
                const result = await orm.call(
                    'loomworks.skill.execution',
                    'provide_input',
                    [[executionId], userInput]
                );
                return result;
            } catch (e) {
                console.error("Resume execution failed:", e);
                return {
                    success: false,
                    error: e.message,
                };
            }
        }

        /**
         * Combined: match and execute if found with sufficient confidence.
         * @param {string} userInput - Natural language text
         * @param {number} minConfidence - Minimum confidence threshold
         * @returns {Object} Result
         */
        async function processNaturalLanguage(userInput, minConfidence = 0.75) {
            const match = await matchIntent(userInput);

            if (match && match.skill_id && match.confidence >= minConfidence) {
                // Add trigger text to context
                const context = {
                    ...match.params,
                    _trigger_text: userInput,
                };

                return executeSkill(match.skill_id, context);
            }

            return {
                matched: false,
                confidence: match?.confidence || 0,
                suggestions: match?.suggestions || [],
            };
        }

        /**
         * Get list of available skills.
         * @param {Object} options - Filter options
         * @returns {Array} List of skills
         */
        async function getAvailableSkills(options = {}) {
            const domain = [['state', '=', 'active']];

            if (options.category) {
                domain.push(['category', '=', options.category]);
            }

            try {
                const skills = await orm.searchRead(
                    'loomworks.skill',
                    domain,
                    ['name', 'technical_name', 'category', 'description', 'trigger_phrases'],
                    { limit: options.limit || 50 }
                );
                return skills;
            } catch (e) {
                console.error("Failed to fetch skills:", e);
                return [];
            }
        }

        /**
         * Get suggested skills for current context.
         * @param {string} model - Current model
         * @param {number} recordId - Current record ID
         * @returns {Array} Suggested skills
         */
        async function getSuggestedSkills(model, recordId = null) {
            try {
                const result = await orm.call(
                    'loomworks.skill',
                    'search_read',
                    [[
                        ['state', '=', 'active'],
                        '|',
                        ['trigger_model_ids.model', '=', model],
                        ['model_id.model', '=', model],
                    ]],
                    {
                        fields: ['name', 'technical_name', 'description'],
                        limit: 5,
                    }
                );
                return result;
            } catch (e) {
                console.error("Failed to get suggested skills:", e);
                return [];
            }
        }

        return {
            matchIntent,
            executeSkill,
            resumeExecution,
            processNaturalLanguage,
            getAvailableSkills,
            getSuggestedSkills,
        };
    },
};

registry.category("services").add("skillIntent", skillIntentService);
