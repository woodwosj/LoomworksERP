# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Skill Execution Service - Orchestrates Skill Workflow Execution

This service is the main entry point for executing skills. It:
1. Creates execution records
2. Sets up rollback points (snapshot or savepoint)
3. Executes steps sequentially with state management
4. Handles user input pauses and resumption
5. Manages rollback on failure
6. Records execution statistics

Usage:
    service = SkillExecutionService(env)
    result = service.execute_skill(skill, context, params)
"""

from odoo.exceptions import UserError, ValidationError
from .rollback_manager import RollbackManager
from .step_executor import StepExecutor
import json
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class SkillExecutionService:
    """
    Orchestrates skill discovery, matching, and execution.

    This is the core runtime for skill workflows, handling:
    - Parameter validation
    - Step-by-step execution
    - Transaction/snapshot management
    - User input handling
    - Error recovery and rollback
    """

    def __init__(self, env):
        """
        Initialize the execution service.

        :param env: Odoo environment
        """
        self.env = env
        self.rollback_manager = RollbackManager(env)
        self.step_executor = StepExecutor(env)

    def execute_skill(self, skill, context=None, params=None):
        """
        Execute a skill workflow.

        :param skill: loomworks.skill record
        :param context: Dict of extracted parameters
        :param params: Additional runtime parameters
        :return: Dict with execution result or follow-up action
        """
        context = context or {}
        params = params or {}

        # Create execution record
        execution = self._create_execution(skill, context)

        # Create rollback point
        savepoint = None
        if skill.auto_snapshot:
            savepoint = self.rollback_manager.create_savepoint(
                skill.technical_name
            )
            # Store savepoint reference
            if isinstance(savepoint, str):
                execution.savepoint_name = savepoint
            elif hasattr(savepoint, 'id'):
                execution.snapshot_id = savepoint

        try:
            # Check required context
            missing = self._check_required_context(skill, context)
            if missing:
                execution.request_input(
                    prompt=f"Please provide: {', '.join(missing)}",
                    input_type='text',
                    variable=missing[0]
                )
                return {
                    'type': 'skill.input_required',
                    'skill_id': skill.id,
                    'execution_id': execution.id,
                    'missing_params': missing,
                    'prompt': f"I need some information to proceed: {', '.join(missing)}",
                }

            # Start execution
            execution.start_execution()
            execution.set_current_context(context)

            # Execute workflow steps
            result = self._execute_steps(skill, context, execution)

            # Check if paused for input
            if result.get('requires_input'):
                return {
                    'type': 'skill.input_required',
                    'skill_id': skill.id,
                    'execution_id': execution.id,
                    **result
                }

            # Success - commit and finalize
            if savepoint:
                self.rollback_manager.release_savepoint(savepoint)

            execution.complete_execution(
                output_data=result.get('data'),
                result_summary=self._generate_summary(skill, result)
            )

            return {
                'type': 'skill.completed',
                'skill_id': skill.id,
                'execution_id': execution.id,
                'result': result.get('data'),
                'summary': execution.result_summary,
            }

        except Exception as e:
            _logger.exception(
                "Skill execution failed: %s (%s)",
                skill.technical_name, e
            )

            # Rollback on failure if configured
            if skill.rollback_on_failure and savepoint:
                try:
                    self.rollback_manager.rollback_to_savepoint(savepoint)
                    _logger.info("Rolled back skill execution: %s", skill.technical_name)
                except Exception as rollback_error:
                    _logger.error("Rollback failed: %s", rollback_error)

            execution.fail_execution(str(e), execution.current_step_id)

            raise UserError(f"Skill '{skill.name}' failed: {e}")

    def resume_execution(self, execution, user_input):
        """
        Resume a paused execution with user input.

        :param execution: loomworks.skill.execution record
        :param user_input: User-provided input value
        :return: Dict with execution result or next input request
        """
        if execution.state != 'waiting_input':
            raise UserError("Execution is not waiting for input")

        # Provide input and get updated context
        context = execution.provide_input(user_input)

        # Validate confirmation if needed
        if execution.pending_input_type == 'confirmation' and not user_input:
            execution.cancel_execution("User declined to confirm")
            return {
                'type': 'skill.cancelled',
                'skill_id': execution.skill_id.id,
                'execution_id': execution.id,
                'reason': 'User cancelled',
            }

        # Continue execution from current step
        skill = execution.skill_id
        result = self._execute_steps(
            skill, context, execution,
            start_step=execution.current_step
        )

        # Check if paused again
        if result.get('requires_input'):
            return {
                'type': 'skill.input_required',
                'skill_id': skill.id,
                'execution_id': execution.id,
                **result
            }

        # Completed
        execution.complete_execution(
            output_data=result.get('data'),
            result_summary=self._generate_summary(skill, result)
        )

        return {
            'type': 'skill.completed',
            'skill_id': skill.id,
            'execution_id': execution.id,
            'result': result.get('data'),
            'summary': execution.result_summary,
        }

    def _create_execution(self, skill, context):
        """
        Create execution record.

        :param skill: Skill to execute
        :param context: Initial context
        :return: loomworks.skill.execution record
        """
        return self.env['loomworks.skill.execution'].create({
            'skill_id': skill.id,
            'user_id': self.env.uid,
            'input_data': json.dumps(context),
            'trigger_text': context.get('_trigger_text', ''),
        })

    def _check_required_context(self, skill, context):
        """
        Check for missing required parameters.

        :param skill: Skill to check
        :param context: Provided context
        :return: List of missing parameter names
        """
        required = skill.get_required_context()
        return [p for p in required if p not in context or context[p] is None]

    def _execute_steps(self, skill, context, execution, start_step=0):
        """
        Execute workflow steps sequentially.

        :param skill: Skill being executed
        :param context: Current context
        :param execution: Execution record
        :param start_step: Step index to start from
        :return: Result dict
        """
        steps = skill.step_ids.sorted('sequence')
        current_context = dict(context)
        result = None
        operation_count = 0

        step_index = start_step
        while step_index < len(steps):
            step = steps[step_index]
            execution.advance_step(step)

            # Safety check: max operations
            if operation_count >= skill.max_operations:
                _logger.warning(
                    "Skill %s exceeded max operations (%d)",
                    skill.technical_name, skill.max_operations
                )
                raise UserError(
                    f"Skill exceeded maximum operations limit ({skill.max_operations})"
                )

            # Execute step
            step_result = self.step_executor.execute(step, current_context, execution)

            # Handle step failure
            if not step_result.get('success', True):
                if step.is_critical:
                    raise ValidationError(
                        step_result.get('error', 'Step execution failed')
                    )
                else:
                    _logger.warning(
                        "Non-critical step '%s' failed: %s",
                        step.name, step_result.get('error')
                    )
                    step_index += 1
                    continue

            # Handle user input request
            if step_result.get('requires_input'):
                execution.request_input(
                    prompt=step_result.get('prompt'),
                    input_type=step_result.get('input_type', 'text'),
                    variable=step_result.get('variable'),
                    options=step_result.get('options')
                )
                execution.set_current_context(current_context)
                return step_result

            # Handle AI decision request
            if step_result.get('requires_ai'):
                # For now, treat as requiring input from the AI chat
                return step_result

            # Store output in context
            if step.output_variable and step_result.get('data') is not None:
                current_context[step.output_variable] = step_result['data']

            # Handle conditional branching
            if step_result.get('next_step_id'):
                # Find the target step index
                for idx, s in enumerate(steps):
                    if s.id == step_result['next_step_id']:
                        step_index = idx
                        break
                else:
                    step_index += 1
            # Handle loop
            elif step_result.get('type') == 'loop':
                collection = step_result.get('collection', [])
                var_name = step_result.get('variable_name', 'item')
                body_step_ids = step_result.get('body_step_ids', [])

                # Execute loop body for each item
                for item in collection:
                    loop_context = dict(current_context)
                    loop_context[var_name] = item

                    # Execute body steps
                    for body_step in step.loop_body_step_ids.sorted('sequence'):
                        body_result = self.step_executor.execute(
                            body_step, loop_context, execution
                        )
                        operation_count += 1

                        if body_result.get('requires_input'):
                            execution.set_current_context(loop_context)
                            return body_result

                        if body_step.output_variable and body_result.get('data'):
                            loop_context[body_step.output_variable] = body_result['data']

                step_index += 1
            else:
                step_index += 1

            # Track operation count
            if step.step_type == 'tool_call':
                operation_count += 1

            result = step_result

        # Update context in execution
        execution.set_current_context(current_context)

        return result or {
            'type': 'skill.completed',
            'message': 'Skill completed successfully',
            'data': current_context,
        }

    def _generate_summary(self, skill, result):
        """
        Generate human-readable summary of execution.

        :param skill: Executed skill
        :param result: Execution result
        :return: Summary string
        """
        if not result:
            return f"Skill '{skill.name}' completed."

        data = result.get('data', {})
        if isinstance(data, dict):
            # Try to extract meaningful info
            if 'created_id' in data:
                return f"Created new record (ID: {data['created_id']})"
            if 'updated_count' in data:
                return f"Updated {data['updated_count']} record(s)"
            if 'result' in data:
                return f"Result: {data['result']}"

        return f"Skill '{skill.name}' completed successfully."


class SkillExecutionServiceFactory:
    """Factory for creating SkillExecutionService instances."""

    @staticmethod
    def create(env):
        """Create a new service instance."""
        return SkillExecutionService(env)
