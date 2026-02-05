# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Loomworks Skill Step Model - Individual Workflow Steps

Each step in a skill workflow represents a single action or decision point.
Steps can be tool calls, user input requests, conditions, loops, or sub-skills.

Step Types:
- tool_call: Invoke an MCP tool with parameters
- user_input: Request input from user
- condition: Evaluate expression and branch
- loop: Iterate over a collection
- validation: Validate data against rules
- confirmation: Request user confirmation
- subskill: Execute another skill
- action: Execute an Odoo action
- ai_decision: Let AI decide next action
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import json
import logging

_logger = logging.getLogger(__name__)


class LoomworksSkillStep(models.Model):
    """
    Individual step in a skill workflow.

    Steps are executed sequentially (by sequence field) with support for
    conditional branching and loop iterations. Each step can produce output
    that's available to subsequent steps via the output_variable.
    """
    _name = 'loomworks.skill.step'
    _description = 'Skill Workflow Step'
    _order = 'sequence, id'

    # Parent relationship
    skill_id = fields.Many2one(
        'loomworks.skill',
        string='Skill',
        required=True,
        ondelete='cascade'
    )

    # Step identification
    name = fields.Char(
        string='Step Name',
        required=True,
        help='Descriptive name for this step'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order of execution within the skill'
    )
    active = fields.Boolean(default=True)

    # Step type
    step_type = fields.Selection([
        ('tool_call', 'Tool Invocation'),
        ('user_input', 'Request User Input'),
        ('condition', 'Conditional Branch'),
        ('loop', 'Loop/Iteration'),
        ('validation', 'Validate Data'),
        ('confirmation', 'User Confirmation'),
        ('subskill', 'Execute Sub-Skill'),
        ('action', 'Execute Odoo Action'),
        ('ai_decision', 'AI Decision'),
    ], string='Step Type', required=True, default='tool_call')

    # Instructions for AI
    instructions = fields.Text(
        string='Instructions',
        help='Instructions or prompt for this step'
    )

    # =====================
    # Tool Call Configuration
    # =====================
    tool_id = fields.Many2one(
        'loomworks.ai.tool',
        string='Tool',
        help='MCP tool to invoke (for tool_call type)'
    )
    tool_name = fields.Char(
        string='Tool Name',
        help='Alternative: tool technical name if not using tool_id'
    )
    tool_parameters = fields.Text(
        string='Parameters Template',
        help='JSON template with {variable} placeholders for parameter values'
    )

    # =====================
    # Conditional Logic
    # =====================
    condition_expression = fields.Text(
        string='Condition Expression',
        help='Python expression that evaluates to True/False. '
             'Available: context variables, env, user'
    )
    on_success_step_id = fields.Many2one(
        'loomworks.skill.step',
        string='On Success (Jump To)',
        help='Step to jump to when condition is True'
    )
    on_failure_step_id = fields.Many2one(
        'loomworks.skill.step',
        string='On Failure (Jump To)',
        help='Step to jump to when condition is False'
    )

    # =====================
    # Loop Configuration
    # =====================
    loop_collection_expr = fields.Text(
        string='Loop Collection',
        help='Expression returning an iterable to loop over'
    )
    loop_variable_name = fields.Char(
        string='Loop Variable',
        default='item',
        help='Variable name for current iteration item'
    )
    loop_body_step_ids = fields.Many2many(
        'loomworks.skill.step',
        'skill_step_loop_body_rel',
        'parent_step_id',
        'body_step_id',
        string='Loop Body Steps',
        help='Steps to execute for each iteration'
    )

    # =====================
    # Sub-skill Reference
    # =====================
    subskill_id = fields.Many2one(
        'loomworks.skill',
        string='Sub-Skill',
        help='Skill to execute (for subskill type)'
    )
    subskill_context_mapping = fields.Text(
        string='Context Mapping',
        help='JSON mapping of parent context to subskill context'
    )

    # =====================
    # Odoo Action Reference
    # =====================
    action_id = fields.Many2one(
        'ir.actions.actions',
        string='Odoo Action',
        help='Odoo action to execute (for action type)'
    )
    action_context = fields.Text(
        string='Action Context',
        help='JSON context to pass to the action'
    )

    # =====================
    # User Input Configuration
    # =====================
    input_prompt = fields.Text(
        string='Input Prompt',
        help='Prompt to display when requesting user input'
    )
    input_type = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('selection', 'Selection'),
        ('boolean', 'Yes/No'),
        ('record', 'Record Selection'),
    ], string='Input Type', default='text')
    input_options = fields.Text(
        string='Input Options',
        help='JSON array of options for selection type'
    )
    input_model_id = fields.Many2one(
        'ir.model',
        string='Record Model',
        help='Model for record selection input type',
        ondelete='cascade'
    )
    input_domain = fields.Text(
        string='Record Domain',
        help='Domain filter for record selection'
    )
    input_required = fields.Boolean(
        string='Input Required',
        default=True
    )
    input_default = fields.Text(
        string='Default Value',
        help='Default value for the input'
    )

    # =====================
    # Output Configuration
    # =====================
    output_variable = fields.Char(
        string='Output Variable',
        help='Variable name to store step result in context'
    )
    output_transform = fields.Text(
        string='Output Transform',
        help='Python expression to transform output before storing'
    )

    # =====================
    # Error Handling
    # =====================
    is_critical = fields.Boolean(
        string='Critical Step',
        default=True,
        help='If True, failure stops execution. If False, execution continues.'
    )
    retry_count = fields.Integer(
        string='Retry Count',
        default=0,
        help='Number of retries on failure (0 = no retry)'
    )
    retry_delay_seconds = fields.Integer(
        string='Retry Delay (s)',
        default=1,
        help='Seconds to wait between retries'
    )
    rollback_on_failure = fields.Boolean(
        string='Rollback on Failure',
        default=True,
        help='Rollback to savepoint if this step fails'
    )
    error_message_template = fields.Text(
        string='Error Message Template',
        help='Custom error message with {variable} placeholders'
    )

    # =====================
    # Validation Configuration
    # =====================
    validation_rules = fields.Text(
        string='Validation Rules',
        help='JSON array of validation rules for validation step type'
    )

    @api.constrains('condition_expression')
    def _check_condition_expression(self):
        """Basic validation of condition expression."""
        for step in self:
            if step.step_type == 'condition' and not step.condition_expression:
                raise ValidationError(
                    "Condition step must have a condition expression"
                )

    @api.constrains('tool_name', 'tool_id')
    def _check_tool_configuration(self):
        """Validate tool call configuration."""
        for step in self:
            if step.step_type == 'tool_call':
                if not step.tool_id and not step.tool_name:
                    raise ValidationError(
                        "Tool call step must have either tool_id or tool_name set"
                    )

    @api.constrains('subskill_id')
    def _check_subskill_configuration(self):
        """Validate subskill configuration."""
        for step in self:
            if step.step_type == 'subskill' and not step.subskill_id:
                raise ValidationError(
                    "Subskill step must have a subskill selected"
                )

    @api.constrains('loop_collection_expr')
    def _check_loop_configuration(self):
        """Validate loop configuration."""
        for step in self:
            if step.step_type == 'loop' and not step.loop_collection_expr:
                raise ValidationError(
                    "Loop step must have a collection expression"
                )

    @api.constrains('tool_parameters')
    def _check_tool_parameters_json(self):
        """Validate tool parameters JSON."""
        for step in self:
            if step.tool_parameters:
                try:
                    # Allow {variable} placeholders by temporarily replacing them
                    import re
                    temp = re.sub(r'\{[^}]+\}', '"placeholder"', step.tool_parameters)
                    json.loads(temp)
                except json.JSONDecodeError as e:
                    raise ValidationError(
                        f"Invalid tool parameters JSON: {e}"
                    )

    def get_tool_parameters(self, context):
        """
        Resolve tool parameters template with context values.

        :param context: Dict of available context variables
        :return: Resolved parameters dict
        """
        self.ensure_one()
        if not self.tool_parameters:
            return {}

        import re

        def replace_var(match):
            var_name = match.group(1)
            value = context.get(var_name)
            if value is None:
                return match.group(0)  # Keep original if not found
            if isinstance(value, str):
                return f'"{value}"'
            return json.dumps(value)

        resolved = re.sub(r'\{(\w+)\}', replace_var, self.tool_parameters)

        try:
            return json.loads(resolved)
        except json.JSONDecodeError:
            _logger.warning(
                "Failed to parse resolved parameters for step %s: %s",
                self.name, resolved
            )
            return {}

    def get_condition_result(self, context):
        """
        Evaluate condition expression with context.

        :param context: Dict of available context variables
        :return: Boolean result of condition
        """
        self.ensure_one()
        if not self.condition_expression:
            return True

        from odoo.tools.safe_eval import safe_eval

        try:
            return bool(safe_eval(
                self.condition_expression,
                {
                    'env': self.env,
                    'user': self.env.user,
                    **context
                }
            ))
        except Exception as e:
            _logger.warning(
                "Condition evaluation failed for step %s: %s",
                self.name, e
            )
            return False

    def get_loop_collection(self, context):
        """
        Evaluate loop collection expression.

        :param context: Dict of available context variables
        :return: Iterable collection
        """
        self.ensure_one()
        if not self.loop_collection_expr:
            return []

        from odoo.tools.safe_eval import safe_eval

        try:
            result = safe_eval(
                self.loop_collection_expr,
                {
                    'env': self.env,
                    'user': self.env.user,
                    **context
                }
            )
            return list(result) if result else []
        except Exception as e:
            _logger.warning(
                "Loop collection evaluation failed for step %s: %s",
                self.name, e
            )
            return []

    def transform_output(self, output, context):
        """
        Apply output transform expression.

        :param output: Raw output from step execution
        :param context: Current context
        :return: Transformed output
        """
        self.ensure_one()
        if not self.output_transform:
            return output

        from odoo.tools.safe_eval import safe_eval

        try:
            return safe_eval(
                self.output_transform,
                {
                    'output': output,
                    'env': self.env,
                    'user': self.env.user,
                    **context
                }
            )
        except Exception as e:
            _logger.warning(
                "Output transform failed for step %s: %s",
                self.name, e
            )
            return output

    def get_effective_tool_name(self):
        """Get the tool name to use (from tool_id or tool_name field)."""
        self.ensure_one()
        if self.tool_id:
            return self.tool_id.technical_name
        return self.tool_name

    def get_input_prompt(self, context):
        """
        Get resolved input prompt.

        :param context: Context for placeholder resolution
        :return: Resolved prompt string
        """
        self.ensure_one()
        prompt = self.input_prompt or self.instructions or f"Please provide input for {self.name}"

        import re

        def replace_var(match):
            var_name = match.group(1)
            return str(context.get(var_name, match.group(0)))

        return re.sub(r'\{(\w+)\}', replace_var, prompt)

    def get_input_options(self):
        """Get parsed input options for selection type."""
        self.ensure_one()
        if self.input_options:
            try:
                return json.loads(self.input_options)
            except json.JSONDecodeError:
                pass
        return []

    def copy_data(self, default=None):
        """Copy step with parent skill reference."""
        default = dict(default or {})
        default['name'] = f"{self.name} (Copy)"
        return super().copy_data(default)
