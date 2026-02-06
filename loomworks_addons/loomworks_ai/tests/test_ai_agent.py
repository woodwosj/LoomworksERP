# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

from loomworks.tests.common import TransactionCase
from loomworks.exceptions import UserError


class TestAIAgent(TransactionCase):
    """Test cases for the AI Agent model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Agent = cls.env['loomworks.ai.agent']
        cls.Tool = cls.env['loomworks.ai.tool']

    def test_create_agent(self):
        """Test basic agent creation."""
        agent = self.Agent.create({
            'name': 'Test Agent',
            'technical_name': 'test_agent',
            'model_id': 'claude-sonnet-4-20250514',
        })
        self.assertTrue(agent.id)
        self.assertEqual(agent.name, 'Test Agent')
        self.assertEqual(agent.permission_mode, 'accept_reads')  # default
        self.assertTrue(agent.can_create)  # default
        self.assertFalse(agent.can_unlink)  # default is False

    def test_temperature_constraint(self):
        """Test that temperature must be between 0 and 1."""
        with self.assertRaises(UserError):
            self.Agent.create({
                'name': 'Test Agent',
                'technical_name': 'test_agent_temp',
                'model_id': 'claude-sonnet-4-20250514',
                'temperature': 1.5,  # Invalid
            })

    def test_unique_technical_name_per_company(self):
        """Test technical name uniqueness constraint."""
        self.Agent.create({
            'name': 'Test Agent 1',
            'technical_name': 'unique_name',
            'model_id': 'claude-sonnet-4-20250514',
        })
        with self.assertRaises(Exception):  # IntegrityError wrapped
            self.Agent.create({
                'name': 'Test Agent 2',
                'technical_name': 'unique_name',  # Duplicate
                'model_id': 'claude-sonnet-4-20250514',
            })

    def test_check_model_access_forbidden(self):
        """Test that sensitive models are always blocked."""
        agent = self.Agent.create({
            'name': 'Test Agent',
            'technical_name': 'test_forbidden',
            'model_id': 'claude-sonnet-4-20250514',
        })
        # These should always be blocked
        self.assertFalse(agent.check_model_access('res.users', 'read'))
        self.assertFalse(agent.check_model_access('ir.config_parameter', 'read'))
        self.assertFalse(agent.check_model_access('ir.rule', 'read'))
        self.assertFalse(agent.check_model_access('ir.model.access', 'read'))

    def test_check_model_access_operation_permissions(self):
        """Test operation-level permissions."""
        agent = self.Agent.create({
            'name': 'Test Agent',
            'technical_name': 'test_ops',
            'model_id': 'claude-sonnet-4-20250514',
            'can_create': True,
            'can_write': True,
            'can_unlink': False,
        })
        # Should allow create and write
        self.assertTrue(agent.check_model_access('res.partner', 'create'))
        self.assertTrue(agent.check_model_access('res.partner', 'write'))
        # Should block unlink
        self.assertFalse(agent.check_model_access('res.partner', 'unlink'))

    def test_check_model_access_blocked_models(self):
        """Test explicit model blocking."""
        partner_model = self.env['ir.model'].search([('model', '=', 'res.partner')], limit=1)

        agent = self.Agent.create({
            'name': 'Test Agent',
            'technical_name': 'test_blocked',
            'model_id': 'claude-sonnet-4-20250514',
            'blocked_model_ids': [(6, 0, [partner_model.id])],
        })
        self.assertFalse(agent.check_model_access('res.partner', 'read'))

    def test_get_effective_system_prompt(self):
        """Test system prompt generation."""
        agent = self.Agent.create({
            'name': 'Test Agent',
            'technical_name': 'test_prompt',
            'model_id': 'claude-sonnet-4-20250514',
            'system_prompt': 'Custom prompt.',
        })
        prompt = agent.get_effective_system_prompt()
        self.assertIn('Custom prompt.', prompt)
        self.assertIn('Odoo ERP Context', prompt)
        self.assertIn('Tool Usage Guidelines', prompt)

    def test_get_tool_schemas(self):
        """Test tool schema retrieval."""
        tool = self.Tool.create({
            'name': 'Test Tool',
            'technical_name': 'test_tool',
            'description': 'A test tool',
            'category': 'data',
            'risk_level': 'safe',
            'parameters_schema': '{"type": "object", "properties": {}}',
        })
        agent = self.Agent.create({
            'name': 'Test Agent',
            'technical_name': 'test_tools',
            'model_id': 'claude-sonnet-4-20250514',
            'tool_ids': [(6, 0, [tool.id])],
        })
        schemas = agent.get_tool_schemas()
        self.assertEqual(len(schemas), 1)
        self.assertEqual(schemas[0]['name'], 'test_tool')
