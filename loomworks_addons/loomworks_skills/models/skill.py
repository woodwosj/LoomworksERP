# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Loomworks Skill Model - AI Skill Definitions

This module defines the core LoomworksSkill model that represents reusable
AI workflow definitions. Skills combine trigger phrases, execution steps,
and tool bindings to enable natural language workflow automation.

Architecture:
- Skills are first-class workflow definitions with versioning
- Each skill has trigger phrases for natural language matching
- Steps define the execution flow (tool calls, conditions, user input)
- Skills can reference MCP tools from loomworks_ai
- Execution is handled by the SkillExecutionService
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import json
import logging

_logger = logging.getLogger(__name__)


class LoomworksSkill(models.Model):
    """
    AI Skill Definition for workflow automation.

    A skill represents a reusable workflow that can be triggered by natural
    language input and executed by the AI assistant. Skills combine:
    - Trigger phrases for intent matching
    - Context schema for parameter extraction
    - Workflow steps for execution
    - Tool bindings for MCP integration
    """
    _name = 'loomworks.skill'
    _description = 'AI Skill Definition'
    _order = 'category, sequence, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic identification
    name = fields.Char(
        string='Skill Name',
        required=True,
        tracking=True,
        help='Display name for this skill'
    )
    technical_name = fields.Char(
        string='Technical Name',
        required=True,
        index=True,
        help="Unique kebab-case identifier, e.g., 'create-sales-quote'"
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    # Description and documentation
    description = fields.Text(
        string='Description',
        help='Detailed description of what this skill does'
    )
    version = fields.Char(
        string='Version',
        default='1.0.0',
        help='Semantic version of this skill definition'
    )

    # Classification
    category = fields.Selection([
        ('sales', 'Sales'),
        ('purchase', 'Purchasing'),
        ('inventory', 'Inventory'),
        ('accounting', 'Accounting'),
        ('hr', 'Human Resources'),
        ('manufacturing', 'Manufacturing'),
        ('crm', 'CRM'),
        ('project', 'Project'),
        ('custom', 'Custom'),
    ], string='Category', default='custom', required=True, tracking=True)

    # Natural language triggers
    trigger_phrases = fields.Text(
        string='Trigger Phrases',
        help='JSON array of phrases that activate this skill. '
             'Use {placeholder} for parameter positions.'
    )
    trigger_confidence_threshold = fields.Float(
        string='Confidence Threshold',
        default=0.75,
        help='Minimum confidence score (0-1) for intent matching'
    )

    # Context configuration
    context_schema = fields.Text(
        string='Context Schema',
        help='JSON Schema defining extractable parameters from user input'
    )
    required_context = fields.Text(
        string='Required Context',
        help='JSON array of required parameter names'
    )

    # Skill content and AI instructions
    system_prompt = fields.Text(
        string='System Prompt',
        help='Instructions for Claude AI when executing this skill'
    )
    skill_content = fields.Text(
        string='Skill Content (SKILL.md)',
        help='Full SKILL.md content defining the workflow'
    )

    # Workflow steps
    step_ids = fields.One2many(
        'loomworks.skill.step',
        'skill_id',
        string='Workflow Steps'
    )
    step_count = fields.Integer(
        string='Step Count',
        compute='_compute_step_count'
    )

    # Tool bindings (MCP tools this skill can invoke)
    tool_ids = fields.Many2many(
        'loomworks.ai.tool',
        'skill_tool_rel',
        'skill_id',
        'tool_id',
        string='Available Tools',
        help='MCP tools this skill is allowed to invoke'
    )
    allowed_tools = fields.Text(
        string='Allowed Tools (JSON)',
        help='JSON array of tool technical names (alternative to tool_ids)'
    )

    # Target model (for binding and permissions)
    trigger_model_ids = fields.Many2many(
        'ir.model',
        'skill_trigger_model_rel',
        'skill_id',
        'model_id',
        string='Context Models',
        help='Models this skill operates on'
    )
    model_id = fields.Many2one(
        'ir.model',
        string='Primary Model',
        ondelete='set null',
        help='Main model this skill operates on'
    )

    # Execution settings
    requires_confirmation = fields.Boolean(
        string='Requires Confirmation',
        default=True,
        help='Prompt user before executing skill'
    )
    auto_snapshot = fields.Boolean(
        string='Auto Snapshot',
        default=True,
        help='Create rollback snapshot before execution (requires loomworks_snapshot)'
    )
    max_operations = fields.Integer(
        string='Max Operations',
        default=10,
        help='Maximum tool calls per execution (safety limit)'
    )
    timeout_seconds = fields.Integer(
        string='Timeout (seconds)',
        default=300,
        help='Maximum execution time in seconds'
    )
    rollback_on_failure = fields.Boolean(
        string='Rollback on Failure',
        default=True,
        help='Automatically rollback changes if execution fails'
    )

    # State and access control
    state = fields.Selection([
        ('draft', 'Draft'),
        ('testing', 'Testing'),
        ('active', 'Active'),
        ('deprecated', 'Deprecated'),
    ], string='State', default='draft', required=True, tracking=True)

    is_builtin = fields.Boolean(
        string='Built-in Skill',
        default=False,
        help='True for skills shipped with the module'
    )
    is_published = fields.Boolean(
        string='Published',
        default=False,
        help='True if available to all users'
    )
    owner_id = fields.Many2one(
        'res.users',
        string='Owner',
        default=lambda self: self.env.uid,
        help='User who created this skill'
    )

    # Statistics
    execution_count = fields.Integer(
        string='Execution Count',
        readonly=True,
        default=0
    )
    success_count = fields.Integer(
        string='Success Count',
        readonly=True,
        default=0
    )
    success_rate = fields.Float(
        string='Success Rate',
        compute='_compute_success_rate',
        store=True
    )
    avg_duration_ms = fields.Integer(
        string='Avg Duration (ms)',
        readonly=True,
        default=0
    )
    last_executed = fields.Datetime(
        string='Last Executed',
        readonly=True
    )

    # Related records
    execution_ids = fields.One2many(
        'loomworks.skill.execution',
        'skill_id',
        string='Executions'
    )

    _sql_constraints = [
        ('technical_name_uniq', 'UNIQUE(technical_name)',
         'Technical name must be unique'),
    ]

    @api.constrains('technical_name')
    def _check_technical_name(self):
        """Validate technical name format (kebab-case)."""
        import re
        pattern = re.compile(r'^[a-z][a-z0-9]*(-[a-z0-9]+)*$')
        for skill in self:
            if skill.technical_name and not pattern.match(skill.technical_name):
                raise ValidationError(
                    f"Technical name '{skill.technical_name}' must be kebab-case "
                    "(e.g., 'create-sales-quote')"
                )

    @api.constrains('trigger_phrases')
    def _check_trigger_phrases(self):
        """Validate trigger phrases JSON."""
        for skill in self:
            if skill.trigger_phrases:
                try:
                    phrases = json.loads(skill.trigger_phrases)
                    if not isinstance(phrases, list):
                        raise ValueError('Must be a JSON array')
                except (json.JSONDecodeError, ValueError) as e:
                    raise ValidationError(f'Invalid trigger phrases JSON: {e}')

    @api.constrains('context_schema')
    def _check_context_schema(self):
        """Validate context schema JSON."""
        for skill in self:
            if skill.context_schema:
                try:
                    schema = json.loads(skill.context_schema)
                    if not isinstance(schema, dict):
                        raise ValueError('Must be a JSON object')
                except (json.JSONDecodeError, ValueError) as e:
                    raise ValidationError(f'Invalid context schema JSON: {e}')

    @api.constrains('trigger_confidence_threshold')
    def _check_confidence_threshold(self):
        """Validate confidence threshold range."""
        for skill in self:
            if not 0 <= skill.trigger_confidence_threshold <= 1:
                raise ValidationError(
                    'Confidence threshold must be between 0 and 1'
                )

    def _compute_step_count(self):
        for skill in self:
            skill.step_count = len(skill.step_ids)

    @api.depends('execution_count', 'success_count')
    def _compute_success_rate(self):
        for skill in self:
            if skill.execution_count > 0:
                skill.success_rate = skill.success_count / skill.execution_count
            else:
                skill.success_rate = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        """Generate technical_name if not provided."""
        for vals in vals_list:
            if 'technical_name' not in vals and 'name' in vals:
                vals['technical_name'] = self._generate_technical_name(vals['name'])
        return super().create(vals_list)

    def _generate_technical_name(self, name):
        """Generate kebab-case technical name from display name."""
        import re
        # Convert to lowercase and replace spaces/special chars with hyphens
        technical = re.sub(r'[^a-z0-9]+', '-', name.lower())
        # Remove leading/trailing hyphens
        technical = technical.strip('-')
        # Ensure uniqueness
        base_name = technical
        counter = 1
        while self.search_count([('technical_name', '=', technical)]) > 0:
            technical = f"{base_name}-{counter}"
            counter += 1
        return technical

    def get_trigger_phrases(self):
        """Return parsed trigger phrases list."""
        self.ensure_one()
        if self.trigger_phrases:
            return json.loads(self.trigger_phrases)
        return []

    def get_context_schema(self):
        """Return parsed context schema dict."""
        self.ensure_one()
        if self.context_schema:
            return json.loads(self.context_schema)
        return {}

    def get_required_context(self):
        """Return parsed required context list."""
        self.ensure_one()
        if self.required_context:
            return json.loads(self.required_context)
        return []

    def get_allowed_tool_names(self):
        """Return list of allowed tool technical names."""
        self.ensure_one()
        names = []
        # From tool_ids relation
        if self.tool_ids:
            names.extend(self.tool_ids.mapped('technical_name'))
        # From JSON field
        if self.allowed_tools:
            try:
                names.extend(json.loads(self.allowed_tools))
            except json.JSONDecodeError:
                pass
        return list(set(names))

    def action_activate(self):
        """Activate skill for use."""
        for skill in self:
            if skill.state in ('draft', 'testing'):
                skill.state = 'active'
        return True

    def action_deactivate(self):
        """Deactivate skill."""
        for skill in self:
            if skill.state == 'active':
                skill.state = 'deprecated'
        return True

    def action_test(self):
        """Move skill to testing state."""
        for skill in self:
            if skill.state == 'draft':
                skill.state = 'testing'
        return True

    def action_execute(self, context=None, params=None):
        """
        Execute this skill with given context.

        :param context: Dict of extracted parameters
        :param params: Additional runtime parameters
        :return: Execution result dict
        """
        self.ensure_one()

        if self.state != 'active':
            raise ValidationError(f"Cannot execute skill in state '{self.state}'")

        # Import execution service
        from ..services.skill_execution_service import SkillExecutionService

        service = SkillExecutionService(self.env)
        return service.execute_skill(self, context or {}, params or {})

    @api.model
    def match_intent(self, user_input, domain=None):
        """
        Match user input against available skills.

        :param user_input: Natural language text from user
        :param domain: Optional domain to filter skills
        :return: dict with skill_id, confidence, params, suggestions
        """
        from ..services.skill_matching_service import SkillMatchingService

        service = SkillMatchingService(self.env)
        return service.match_skill(user_input, domain)

    def record_execution(self, success, duration_ms=0):
        """
        Record execution statistics.

        :param success: Whether execution succeeded
        :param duration_ms: Execution duration in milliseconds
        """
        self.ensure_one()

        # Calculate running average duration
        total_duration = self.avg_duration_ms * self.execution_count
        new_count = self.execution_count + 1
        new_avg = (total_duration + duration_ms) // new_count if new_count > 0 else 0

        self.sudo().write({
            'execution_count': new_count,
            'success_count': self.success_count + (1 if success else 0),
            'avg_duration_ms': new_avg,
            'last_executed': fields.Datetime.now(),
        })

    def copy_data(self, default=None):
        """Copy skill with modified technical name."""
        default = dict(default or {})
        if 'technical_name' not in default:
            default['technical_name'] = f"{self.technical_name}-copy"
        if 'name' not in default:
            default['name'] = f"{self.name} (Copy)"
        default['state'] = 'draft'
        default['execution_count'] = 0
        default['success_count'] = 0
        default['avg_duration_ms'] = 0
        return super().copy_data(default)
