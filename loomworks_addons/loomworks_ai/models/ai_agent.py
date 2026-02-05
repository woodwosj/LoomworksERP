# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

from odoo import models, fields, api
from odoo.exceptions import UserError


class AIAgent(models.Model):
    """
    Configuration for Claude AI agents.
    Each company can have multiple agents with different capabilities.
    """
    _name = 'loomworks.ai.agent'
    _description = 'AI Agent Configuration'
    _order = 'sequence, id'

    name = fields.Char(
        string='Agent Name',
        required=True,
        help='Display name for this AI agent'
    )
    technical_name = fields.Char(
        string='Technical Name',
        required=True,
        copy=False,
        help='Unique identifier used in API calls'
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    # Claude Configuration
    model_id = fields.Selection([
        ('claude-sonnet-4-20250514', 'Claude Sonnet 4'),
        ('claude-opus-4-5-20251101', 'Claude Opus 4.5'),
    ], string='Claude Model', default='claude-sonnet-4-20250514', required=True)

    system_prompt = fields.Text(
        string='System Prompt',
        help='Base instructions for the AI agent behavior'
    )
    max_tokens = fields.Integer(
        string='Max Response Tokens',
        default=4096,
        help='Maximum tokens in AI response'
    )
    temperature = fields.Float(
        string='Temperature',
        default=0.7,
        help='Creativity level (0.0 = deterministic, 1.0 = creative)'
    )

    # Tool Access Control
    tool_ids = fields.Many2many(
        'loomworks.ai.tool',
        string='Allowed Tools',
        help='MCP tools this agent can use'
    )
    allowed_model_ids = fields.Many2many(
        'ir.model',
        'ai_agent_allowed_models_rel',
        'agent_id',
        'model_id',
        string='Allowed Models',
        help='Odoo models this agent can access. Empty = all accessible models.'
    )
    blocked_model_ids = fields.Many2many(
        'ir.model',
        'ai_agent_blocked_models_rel',
        'agent_id',
        'model_id',
        string='Blocked Models',
        help='Odoo models this agent cannot access (overrides allowed)'
    )

    # Permission Settings
    permission_mode = fields.Selection([
        ('default', 'Default - Prompt for all operations'),
        ('accept_reads', 'Auto-approve read operations'),
        ('accept_edits', 'Auto-approve read and edit operations'),
        ('supervised', 'Require approval for every action'),
    ], string='Permission Mode', default='accept_reads', required=True)

    can_create = fields.Boolean(
        string='Can Create Records',
        default=True
    )
    can_write = fields.Boolean(
        string='Can Update Records',
        default=True
    )
    can_unlink = fields.Boolean(
        string='Can Delete Records',
        default=False,
        help='Dangerous: allows permanent deletion'
    )
    can_execute_actions = fields.Boolean(
        string='Can Execute Actions',
        default=True,
        help='Allow running server actions and workflows'
    )

    # Sandbox Settings
    use_savepoints = fields.Boolean(
        string='Use Database Savepoints',
        default=True,
        help='Create savepoint before each operation for rollback'
    )
    auto_rollback_on_error = fields.Boolean(
        string='Auto-Rollback on Error',
        default=True
    )
    max_operations_per_turn = fields.Integer(
        string='Max Operations per Turn',
        default=10,
        help='Limit operations in single conversation turn'
    )

    # Statistics
    session_count = fields.Integer(
        string='Total Sessions',
        compute='_compute_statistics'
    )
    operation_count = fields.Integer(
        string='Total Operations',
        compute='_compute_statistics'
    )

    _sql_constraints = [
        ('technical_name_company_uniq',
         'UNIQUE(technical_name, company_id)',
         'Technical name must be unique per company'),
    ]

    @api.depends('technical_name')
    def _compute_statistics(self):
        for agent in self:
            agent.session_count = self.env['loomworks.ai.session'].search_count([
                ('agent_id', '=', agent.id)
            ])
            agent.operation_count = self.env['loomworks.ai.operation.log'].search_count([
                ('agent_id', '=', agent.id)
            ])

    @api.constrains('temperature')
    def _check_temperature(self):
        for agent in self:
            if not 0.0 <= agent.temperature <= 1.0:
                raise UserError('Temperature must be between 0.0 and 1.0')

    @api.constrains('max_operations_per_turn')
    def _check_max_operations(self):
        for agent in self:
            if agent.max_operations_per_turn < 1:
                raise UserError('Max operations per turn must be at least 1')

    def get_effective_system_prompt(self):
        """Build complete system prompt with Odoo context."""
        self.ensure_one()
        base_prompt = self.system_prompt or self._get_default_system_prompt()

        # Add Odoo-specific context
        odoo_context = self._build_odoo_context()

        return f"""{base_prompt}

## Odoo ERP Context

You are operating within Loomworks ERP (based on Odoo). Here is your current context:

{odoo_context}

## Tool Usage Guidelines

- Always use search_records before create/update to verify data exists
- Use transactions: operations within a turn are atomic
- Log your reasoning for audit compliance
- Respect user permissions - you inherit the user's access rights
"""

    def _get_default_system_prompt(self):
        return """You are Loomworks AI, an intelligent assistant for enterprise resource planning.

Your role is to help users manage their business operations through natural conversation.
You can search data, create records, update information, and execute business workflows.

Guidelines:
1. Always confirm understanding before making changes
2. Explain what you're doing in simple terms
3. Offer alternatives when requests are ambiguous
4. Warn about potential impacts of destructive operations
5. Suggest related actions that might be helpful
"""

    def _build_odoo_context(self):
        """Build contextual information about the current Odoo environment."""
        user = self.env.user
        company = self.env.company

        return f"""- Current User: {user.name} ({user.login})
- Company: {company.name}
- Timezone: {user.tz or 'UTC'}
- Language: {user.lang or 'en_US'}
- Date: {fields.Date.today()}
"""

    def check_model_access(self, model_name, operation='read'):
        """
        Verify if this agent can access a specific model.
        Returns True if access is allowed, False otherwise.
        """
        self.ensure_one()

        # Always block sensitive models
        SENSITIVE_MODELS = [
            'res.users',
            'res.users.log',
            'ir.config_parameter',
            'ir.rule',
            'ir.model.access',
            'ir.ui.view',
            'ir.attachment',  # Could contain sensitive files
            'mail.mail',      # Email content
        ]

        if model_name in SENSITIVE_MODELS:
            return False

        # Check explicit blocks
        if self.blocked_model_ids:
            blocked_names = self.blocked_model_ids.mapped('model')
            if model_name in blocked_names:
                return False

        # Check explicit allows (if defined)
        if self.allowed_model_ids:
            allowed_names = self.allowed_model_ids.mapped('model')
            if model_name not in allowed_names:
                return False

        # Check operation permissions
        if operation == 'create' and not self.can_create:
            return False
        if operation == 'write' and not self.can_write:
            return False
        if operation == 'unlink' and not self.can_unlink:
            return False

        return True

    def get_tool_schemas(self):
        """Get tool schemas for Claude API registration."""
        self.ensure_one()
        tools = self.tool_ids.filtered('active') if self.tool_ids else \
            self.env['loomworks.ai.tool'].search([('active', '=', True)])
        return [tool.get_mcp_schema() for tool in tools]
