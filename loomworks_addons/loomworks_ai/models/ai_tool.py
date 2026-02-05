# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

from odoo import models, fields, api
import json


class AITool(models.Model):
    """
    Defines MCP tools available to AI agents.
    Each tool represents a capability the AI can invoke.
    """
    _name = 'loomworks.ai.tool'
    _description = 'AI Tool Definition'
    _order = 'category, sequence, name'

    name = fields.Char(
        string='Tool Name',
        required=True,
        help='Display name for the tool'
    )
    technical_name = fields.Char(
        string='Technical Name',
        required=True,
        help='Name used in MCP protocol (snake_case)'
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    category = fields.Selection([
        ('data', 'Data Operations'),
        ('action', 'Actions & Workflows'),
        ('report', 'Reports & Analytics'),
        ('system', 'System Operations'),
    ], string='Category', required=True, default='data')

    description = fields.Text(
        string='Description',
        required=True,
        help='Detailed description shown to AI for tool selection'
    )

    # JSON Schema for parameters
    parameters_schema = fields.Text(
        string='Parameters Schema (JSON)',
        required=True,
        default='{"type": "object", "properties": {}, "required": []}',
        help='JSON Schema defining tool parameters'
    )

    # Return type documentation
    returns_description = fields.Text(
        string='Returns Description',
        help='Description of what the tool returns'
    )

    # Implementation reference
    implementation_method = fields.Char(
        string='Implementation Method',
        help='Python method path: module.class.method'
    )

    # Risk assessment
    risk_level = fields.Selection([
        ('safe', 'Safe - Read only'),
        ('moderate', 'Moderate - Creates/modifies data'),
        ('high', 'High - Deletes data or runs workflows'),
        ('critical', 'Critical - System-level operations'),
    ], string='Risk Level', required=True, default='safe')

    requires_confirmation = fields.Boolean(
        string='Requires User Confirmation',
        default=False,
        help='Prompt user before executing'
    )

    # Usage statistics
    usage_count = fields.Integer(
        string='Usage Count',
        default=0
    )
    last_used = fields.Datetime(
        string='Last Used'
    )

    _sql_constraints = [
        ('technical_name_uniq', 'UNIQUE(technical_name)',
         'Technical name must be unique'),
    ]

    @api.constrains('parameters_schema')
    def _check_json_schema(self):
        for tool in self:
            try:
                schema = json.loads(tool.parameters_schema)
                if not isinstance(schema, dict):
                    raise ValueError('Schema must be a JSON object')
            except json.JSONDecodeError as e:
                from odoo.exceptions import UserError
                raise UserError(f'Invalid JSON schema: {e}')

    def get_mcp_schema(self):
        """Return tool definition in MCP/Claude format."""
        self.ensure_one()
        return {
            'name': self.technical_name,
            'description': self.description,
            'input_schema': json.loads(self.parameters_schema),
        }

    def record_usage(self):
        """Record that this tool was used."""
        self.write({
            'usage_count': self.usage_count + 1,
            'last_used': fields.Datetime.now()
        })

    @api.model
    def get_tools_for_agent(self, agent):
        """Get all tools available to a specific agent."""
        if agent.tool_ids:
            return agent.tool_ids.filtered('active')
        # Default: return all safe and moderate risk tools
        return self.search([
            ('active', '=', True),
            ('risk_level', 'in', ['safe', 'moderate'])
        ])
