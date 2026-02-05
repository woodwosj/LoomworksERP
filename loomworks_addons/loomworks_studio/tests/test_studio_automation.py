# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

"""
Tests for Studio Automation functionality.
"""

from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestStudioAutomation(TransactionCase):
    """Test cases for studio.automation model."""

    def setUp(self):
        super().setUp()
        self.Automation = self.env['studio.automation']
        self.partner_model = self.env.ref('base.model_res_partner')

    def test_create_automation(self):
        """Test creating a basic automation."""
        automation = self.Automation.create({
            'name': 'Test Automation',
            'model_id': self.partner_model.id,
            'trigger_type': 'on_create',
            'action_type': 'update_record',
        })

        self.assertEqual(automation.name, 'Test Automation')
        self.assertEqual(automation.model_name, 'res.partner')
        self.assertEqual(automation.state, 'draft')

    def test_python_code_validation(self):
        """Test Python code syntax validation."""
        # Valid code
        automation = self.Automation.create({
            'name': 'Valid Code',
            'model_id': self.partner_model.id,
            'trigger_type': 'on_create',
            'action_type': 'python_code',
            'python_code': 'for record in records:\n    pass',
        })
        self.assertTrue(automation.exists())

        # Invalid code should raise
        with self.assertRaises(ValidationError):
            self.Automation.create({
                'name': 'Invalid Code',
                'model_id': self.partner_model.id,
                'trigger_type': 'on_create',
                'action_type': 'python_code',
                'python_code': 'for record in records  # syntax error',
            })

    def test_filter_domain_validation(self):
        """Test filter domain validation."""
        # Valid domain
        automation = self.Automation.create({
            'name': 'Valid Domain',
            'model_id': self.partner_model.id,
            'trigger_type': 'on_create',
            'action_type': 'update_record',
            'filter_domain': "[('active', '=', True)]",
        })
        self.assertTrue(automation.exists())

        # Invalid domain
        with self.assertRaises(ValidationError):
            self.Automation.create({
                'name': 'Invalid Domain',
                'model_id': self.partner_model.id,
                'trigger_type': 'on_create',
                'action_type': 'update_record',
                'filter_domain': "not a valid domain",
            })

    def test_automation_activate_deactivate(self):
        """Test activating and deactivating automation."""
        automation = self.Automation.create({
            'name': 'State Test',
            'model_id': self.partner_model.id,
            'trigger_type': 'on_create',
            'action_type': 'update_record',
        })

        self.assertEqual(automation.state, 'draft')

        automation.action_activate()
        self.assertEqual(automation.state, 'active')

        automation.action_deactivate()
        self.assertEqual(automation.state, 'disabled')

    def test_automation_execution_count(self):
        """Test that execution count starts at zero."""
        automation = self.Automation.create({
            'name': 'Count Test',
            'model_id': self.partner_model.id,
            'trigger_type': 'on_create',
            'action_type': 'update_record',
        })

        self.assertEqual(automation.execution_count, 0)
        self.assertFalse(automation.last_run)
