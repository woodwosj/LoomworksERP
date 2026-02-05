# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Step Executor - Executes Individual Skill Workflow Steps

Handles execution of each step type:
- tool_call: Invoke MCP tools
- user_input: Request user input
- condition: Evaluate and branch
- loop: Iterate over collections
- validation: Validate data
- confirmation: User confirmation
- subskill: Execute nested skills
- action: Execute Odoo actions
- ai_decision: Let AI decide
"""

from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval
import json
import logging
import re

_logger = logging.getLogger(__name__)


class StepExecutor:
    """
    Executes individual skill workflow steps.

    Each step type has a dedicated execution method that handles
    the specific logic and returns a standardized result dict.
    """

    def __init__(self, env):
        """
        Initialize step executor.

        :param env: Odoo environment
        """
        self.env = env
        self._mcp_tools = None

    @property
    def mcp_tools(self):
        """Lazy load MCP tools service."""
        if self._mcp_tools is None:
            from odoo.addons.loomworks_ai.services.odoo_mcp_tools import OdooMCPTools
            self._mcp_tools = OdooMCPTools(self.env)
        return self._mcp_tools

    def execute(self, step, context, execution=None):
        """
        Execute a single workflow step.

        :param step: loomworks.skill.step record
        :param context: Dict of current context variables
        :param execution: Optional execution record for logging
        :return: Dict with execution result
        """
        method = getattr(self, f'_execute_{step.step_type}', None)
        if not method:
            raise ValidationError(f"Unknown step type: {step.step_type}")

        _logger.debug(
            "Executing step '%s' (type: %s)",
            step.name, step.step_type
        )

        try:
            result = method(step, context)

            # Apply output transform if configured
            if result.get('data') and step.output_transform:
                result['data'] = step.transform_output(result['data'], context)

            # Log operation if execution provided
            if execution and step.step_type == 'tool_call':
                execution.log_operation(
                    tool_name=step.get_effective_tool_name(),
                    operation_type='tool_call',
                    params=step.get_tool_parameters(context),
                    result=result.get('data')
                )

            return result

        except Exception as e:
            _logger.error(
                "Step '%s' failed: %s",
                step.name, e
            )

            # Handle retries
            if step.retry_count > 0:
                return self._retry_step(step, context, execution, e)

            # Build error result
            error_result = {
                'success': False,
                'error': str(e),
                'step_name': step.name,
                'critical': step.is_critical,
            }

            if step.error_message_template:
                error_result['error_message'] = self._resolve_template(
                    step.error_message_template, {**context, 'error': str(e)}
                )

            if execution:
                execution.log_operation(
                    tool_name=step.get_effective_tool_name() or step.step_type,
                    operation_type='step_error',
                    error=str(e)
                )

            return error_result

    def _retry_step(self, step, context, execution, last_error):
        """
        Retry a failed step.

        :param step: Step to retry
        :param context: Execution context
        :param execution: Execution record
        :param last_error: Last exception
        :return: Result dict
        """
        import time

        for attempt in range(step.retry_count):
            _logger.info(
                "Retrying step '%s' (attempt %d/%d)",
                step.name, attempt + 1, step.retry_count
            )

            if step.retry_delay_seconds > 0:
                time.sleep(step.retry_delay_seconds)

            try:
                method = getattr(self, f'_execute_{step.step_type}')
                result = method(step, context)
                _logger.info("Step '%s' succeeded on retry %d", step.name, attempt + 1)
                return result
            except Exception as e:
                last_error = e
                _logger.warning(
                    "Retry %d failed for step '%s': %s",
                    attempt + 1, step.name, e
                )

        # All retries exhausted
        return {
            'success': False,
            'error': f"All {step.retry_count} retries exhausted: {last_error}",
            'step_name': step.name,
            'critical': step.is_critical,
        }

    def _execute_tool_call(self, step, context):
        """
        Execute an MCP tool call.

        :param step: Step record
        :param context: Execution context
        :return: Result dict with tool output
        """
        tool_name = step.get_effective_tool_name()
        if not tool_name:
            raise ValidationError("No tool specified for tool_call step")

        params = step.get_tool_parameters(context)

        _logger.debug(
            "Calling tool '%s' with params: %s",
            tool_name, params
        )

        # Execute via MCP tools service
        result = self.mcp_tools.execute_tool(tool_name, params)

        return {
            'success': True,
            'type': 'tool_call',
            'tool': tool_name,
            'params': params,
            'data': result,
        }

    def _execute_user_input(self, step, context):
        """
        Request input from user.

        Returns a special result that signals the execution engine
        to pause and wait for user input.

        :param step: Step record
        :param context: Execution context
        :return: Result dict requesting input
        """
        prompt = step.get_input_prompt(context)
        options = step.get_input_options()

        return {
            'success': True,
            'requires_input': True,
            'type': 'user_input',
            'prompt': prompt,
            'input_type': step.input_type,
            'options': options,
            'variable': step.output_variable,
            'required': step.input_required,
            'default': step.input_default,
        }

    def _execute_condition(self, step, context):
        """
        Evaluate conditional expression and determine branching.

        :param step: Step record
        :param context: Execution context
        :return: Result dict with branch decision
        """
        result = step.get_condition_result(context)

        next_step = step.on_success_step_id if result else step.on_failure_step_id

        return {
            'success': True,
            'type': 'condition',
            'condition_result': result,
            'next_step_id': next_step.id if next_step else None,
            'data': result,
        }

    def _execute_loop(self, step, context):
        """
        Execute loop iteration setup.

        Returns the collection to iterate over. The execution engine
        handles the actual iteration.

        :param step: Step record
        :param context: Execution context
        :return: Result dict with iteration info
        """
        collection = step.get_loop_collection(context)

        return {
            'success': True,
            'type': 'loop',
            'collection': collection,
            'variable_name': step.loop_variable_name or 'item',
            'body_step_ids': step.loop_body_step_ids.ids,
            'iteration_count': len(collection),
            'data': collection,
        }

    def _execute_validation(self, step, context):
        """
        Validate data against rules.

        :param step: Step record
        :param context: Execution context
        :return: Result dict with validation status
        """
        if step.validation_rules:
            rules = json.loads(step.validation_rules)
            errors = []

            for rule in rules:
                field = rule.get('field')
                rule_type = rule.get('type')
                message = rule.get('message', f"Validation failed for {field}")

                value = context.get(field)

                if rule_type == 'required' and not value:
                    errors.append(message)
                elif rule_type == 'min_length' and len(str(value or '')) < rule.get('value', 0):
                    errors.append(message)
                elif rule_type == 'max_length' and len(str(value or '')) > rule.get('value', 999999):
                    errors.append(message)
                elif rule_type == 'pattern' and value:
                    if not re.match(rule.get('value', ''), str(value)):
                        errors.append(message)
                elif rule_type == 'expression':
                    try:
                        if not safe_eval(rule.get('value', 'True'), context):
                            errors.append(message)
                    except Exception as e:
                        errors.append(f"Validation expression error: {e}")

            if errors:
                raise ValidationError('\n'.join(errors))

        # Also check condition expression for backward compatibility
        if step.condition_expression:
            try:
                result = safe_eval(step.condition_expression, {
                    'env': self.env,
                    'user': self.env.user,
                    **context
                })
                if not result:
                    raise ValidationError(
                        step.instructions or "Validation failed"
                    )
            except ValidationError:
                raise
            except Exception as e:
                raise ValidationError(f"Validation error: {e}")

        return {
            'success': True,
            'type': 'validation',
            'validated': True,
            'data': True,
        }

    def _execute_confirmation(self, step, context):
        """
        Request user confirmation.

        Similar to user_input but specifically for yes/no confirmations.

        :param step: Step record
        :param context: Execution context
        :return: Result dict requesting confirmation
        """
        message = self._resolve_template(
            step.instructions or step.input_prompt or "Please confirm to continue",
            context
        )

        return {
            'success': True,
            'requires_input': True,
            'type': 'confirmation',
            'prompt': message,
            'input_type': 'boolean',
            'variable': step.output_variable or '_confirmed',
        }

    def _execute_subskill(self, step, context):
        """
        Execute a sub-skill.

        :param step: Step record
        :param context: Execution context
        :return: Result dict from sub-skill execution
        """
        if not step.subskill_id:
            raise ValidationError("No subskill configured")

        # Map context if mapping provided
        subskill_context = dict(context)
        if step.subskill_context_mapping:
            mapping = json.loads(step.subskill_context_mapping)
            subskill_context = {}
            for target_key, source_expr in mapping.items():
                if source_expr in context:
                    subskill_context[target_key] = context[source_expr]
                else:
                    try:
                        subskill_context[target_key] = safe_eval(source_expr, context)
                    except Exception:
                        subskill_context[target_key] = source_expr

        # Execute sub-skill
        result = step.subskill_id.action_execute(context=subskill_context)

        return {
            'success': True,
            'type': 'subskill',
            'subskill_name': step.subskill_id.name,
            'data': result,
        }

    def _execute_action(self, step, context):
        """
        Execute an Odoo action.

        :param step: Step record
        :param context: Execution context
        :return: Result dict with action result
        """
        if not step.action_id:
            raise ValidationError("No action configured for step")

        # Build action context
        action_context = dict(self.env.context)
        if step.action_context:
            extra_context = json.loads(step.action_context)
            # Resolve any template variables
            for key, value in extra_context.items():
                if isinstance(value, str) and '{' in value:
                    extra_context[key] = self._resolve_template(value, context)
            action_context.update(extra_context)

        # Add context variables
        action_context.update({
            'active_id': context.get('active_id'),
            'active_ids': context.get('active_ids', []),
            'active_model': context.get('active_model'),
        })

        # Read action and return for client execution
        action_data = step.action_id.read()[0]

        return {
            'success': True,
            'type': 'action',
            'action': action_data,
            'data': action_data,
        }

    def _execute_ai_decision(self, step, context):
        """
        Let AI decide the next action.

        This step type delegates decision-making to the AI based on
        the current context and instructions.

        :param step: Step record
        :param context: Execution context
        :return: Result dict requesting AI decision
        """
        instructions = step.instructions or "Decide the best next action based on the current context"

        return {
            'success': True,
            'type': 'ai_decision',
            'requires_ai': True,
            'instructions': self._resolve_template(instructions, context),
            'context_snapshot': context,
            'available_tools': step.skill_id.get_allowed_tool_names() if step.skill_id else [],
        }

    def _resolve_template(self, template, context):
        """
        Replace {variable} placeholders with context values.

        :param template: String with {variable} placeholders
        :param context: Dict of values
        :return: Resolved string
        """
        if not template:
            return template

        def replace_var(match):
            var_name = match.group(1)
            value = context.get(var_name)
            if value is None:
                return match.group(0)  # Keep original if not found
            return str(value)

        return re.sub(r'\{(\w+)\}', replace_var, template)
