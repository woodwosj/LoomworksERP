# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

from loomworks.tests.common import TransactionCase
from loomworks.exceptions import AccessError, UserError


class TestAISandbox(TransactionCase):
    """Test cases for the AI Sandbox security model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Sandbox = cls.env['loomworks.ai.sandbox']
        cls.Agent = cls.env['loomworks.ai.agent']
        cls.Session = cls.env['loomworks.ai.session']

        # Create test agent
        cls.test_agent = cls.Agent.create({
            'name': 'Sandbox Test Agent',
            'technical_name': 'sandbox_test_agent',
            'model_id': 'claude-sonnet-4-20250514',
            'can_create': True,
            'can_write': True,
            'can_unlink': False,
        })

        # Create test session
        cls.test_session = cls.Session.create({
            'agent_id': cls.test_agent.id,
        })

    def test_validate_forbidden_models(self):
        """Test that forbidden models raise AccessError."""
        forbidden_models = [
            'res.users',
            'res.users.log',
            'ir.config_parameter',
            'ir.rule',
            'ir.model.access',
        ]

        for model in forbidden_models:
            with self.assertRaises(AccessError, msg=f"Model {model} should be forbidden"):
                self.Sandbox.validate_model_access(model, 'read', self.test_agent)

    def test_validate_nonexistent_model(self):
        """Test that non-existent model raises AccessError."""
        with self.assertRaises(AccessError):
            self.Sandbox.validate_model_access('fake.model.name', 'read', self.test_agent)

    def test_sanitize_values_removes_forbidden_fields(self):
        """Test that forbidden fields are removed from values."""
        values = {
            'name': 'Test',
            'email': 'test@example.com',
            'password': 'secret123',
            'api_key': 'key123',
            'token': 'token123',
        }
        sanitized = self.Sandbox.sanitize_values('res.partner', values, 'write')

        self.assertIn('name', sanitized)
        self.assertIn('email', sanitized)
        self.assertNotIn('password', sanitized)
        self.assertNotIn('api_key', sanitized)
        self.assertNotIn('token', sanitized)

    def test_sanitize_values_removes_nonexistent_fields(self):
        """Test that non-existent fields are removed."""
        values = {
            'name': 'Test',
            'fake_field_123': 'value',
        }
        sanitized = self.Sandbox.sanitize_values('res.partner', values, 'write')

        self.assertIn('name', sanitized)
        self.assertNotIn('fake_field_123', sanitized)

    def test_sanitize_domain_valid(self):
        """Test domain sanitization with valid operators."""
        domain = [
            ('name', '=', 'Test'),
            ('email', 'ilike', '@example.com'),
            '|',
            ('active', '=', True),
            ('customer_rank', '>', 0),
        ]
        sanitized = self.Sandbox.sanitize_domain('res.partner', domain)

        self.assertEqual(len(sanitized), 5)
        self.assertIn(('name', '=', 'Test'), sanitized)
        self.assertIn('|', sanitized)

    def test_sanitize_domain_removes_forbidden_fields(self):
        """Test that forbidden fields are removed from domain."""
        domain = [
            ('name', '=', 'Test'),
            ('password', '=', 'secret'),  # Should be removed
        ]
        sanitized = self.Sandbox.sanitize_domain('res.partner', domain)

        self.assertEqual(len(sanitized), 1)
        self.assertIn(('name', '=', 'Test'), sanitized)

    def test_sanitize_domain_invalid_operator(self):
        """Test that invalid operators are removed."""
        domain = [
            ('name', '=', 'Test'),
            ('email', 'INVALID_OP', 'value'),  # Invalid operator
        ]
        sanitized = self.Sandbox.sanitize_domain('res.partner', domain)

        self.assertEqual(len(sanitized), 1)

    def test_sanitize_fields(self):
        """Test field list sanitization."""
        fields = ['name', 'email', 'password', 'api_key', 'phone']
        sanitized = self.Sandbox.sanitize_fields('res.partner', fields)

        self.assertIn('name', sanitized)
        self.assertIn('email', sanitized)
        self.assertIn('phone', sanitized)
        self.assertNotIn('password', sanitized)
        self.assertNotIn('api_key', sanitized)

    def test_capture_record_state(self):
        """Test record state capture."""
        partner = self.env['res.partner'].create({
            'name': 'State Test',
            'email': 'state@example.com',
        })

        state = self.Sandbox.capture_record_state('res.partner', [partner.id])

        self.assertIn(partner.id, state)
        self.assertEqual(state[partner.id]['name'], 'State Test')
        self.assertEqual(state[partner.id]['email'], 'state@example.com')
        # Should not capture forbidden fields
        self.assertNotIn('password', state[partner.id])

    def test_capture_record_state_specific_fields(self):
        """Test capturing specific fields only."""
        partner = self.env['res.partner'].create({
            'name': 'State Test 2',
            'email': 'state2@example.com',
            'phone': '123-456',
        })

        state = self.Sandbox.capture_record_state(
            'res.partner',
            [partner.id],
            fields_to_capture=['name', 'phone']
        )

        self.assertIn(partner.id, state)
        self.assertIn('name', state[partner.id])
        self.assertIn('phone', state[partner.id])
        self.assertNotIn('email', state[partner.id])

    def test_execute_with_limits(self):
        """Test operation limit enforcement."""
        # Set turn operation count near limit
        self.test_session.update_context('turn_operation_count', 9)

        # Create agent with limit of 10
        agent = self.Agent.create({
            'name': 'Limited Agent',
            'technical_name': 'limited_agent',
            'model_id': 'claude-sonnet-4-20250514',
            'max_operations_per_turn': 10,
        })

        # First operation should succeed
        result = self.Sandbox.execute_with_limits(
            self.test_session,
            agent,
            lambda: 'success'
        )
        self.assertEqual(result, 'success')

        # Next operation should fail (at limit)
        with self.assertRaises(UserError) as context:
            self.Sandbox.execute_with_limits(
                self.test_session,
                agent,
                lambda: 'should fail'
            )
        self.assertIn('Maximum operations', str(context.exception))
