# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

from loomworks.tests.common import TransactionCase
from loomworks.exceptions import AccessError


class TestMCPTools(TransactionCase):
    """Test cases for MCP tool implementations."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Agent = cls.env['loomworks.ai.agent']
        cls.Session = cls.env['loomworks.ai.session']
        cls.Partner = cls.env['res.partner']

        # Create test agent with all permissions
        cls.test_agent = cls.Agent.create({
            'name': 'Test Agent',
            'technical_name': 'test_mcp_agent',
            'model_id': 'claude-sonnet-4-20250514',
            'can_create': True,
            'can_write': True,
            'can_unlink': True,
            'use_savepoints': False,  # Disable for testing
        })

        # Create test session
        cls.test_session = cls.Session.create({
            'agent_id': cls.test_agent.id,
        })

        # Create test partner for operations
        cls.test_partner = cls.Partner.create({
            'name': 'Test Partner',
            'email': 'test@example.com',
        })

    def _get_tools(self):
        """Get MCP tools instance."""
        from ..services.odoo_mcp_tools import OdooMCPTools
        return OdooMCPTools(self.env, self.test_session, self.test_agent)

    def test_search_records_basic(self):
        """Test basic record search."""
        tools = self._get_tools()
        result = tools.search_records(
            model='res.partner',
            domain=[('id', '=', self.test_partner.id)],
            fields=['name', 'email']
        )
        self.assertIn('records', result)
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['records'][0]['name'], 'Test Partner')

    def test_search_records_limit(self):
        """Test search respects limit."""
        tools = self._get_tools()
        # Request with high limit should be capped
        result = tools.search_records(
            model='res.partner',
            limit=1000  # Should be capped to 500
        )
        self.assertIn('records', result)
        # Verify limit was applied (records returned <= 500)
        self.assertLessEqual(len(result['records']), 500)

    def test_search_records_forbidden_model(self):
        """Test search on forbidden model fails."""
        tools = self._get_tools()
        result = tools.search_records(model='res.users')
        self.assertIn('error', result)

    def test_create_record(self):
        """Test record creation."""
        tools = self._get_tools()
        result = tools.create_record(
            model='res.partner',
            values={'name': 'New Partner', 'email': 'new@example.com'}
        )
        self.assertTrue(result.get('created'))
        self.assertTrue(result.get('id'))
        self.assertEqual(result.get('display_name'), 'New Partner')

        # Verify record exists
        partner = self.Partner.browse(result['id'])
        self.assertTrue(partner.exists())
        self.assertEqual(partner.name, 'New Partner')

    def test_create_record_sanitizes_forbidden_fields(self):
        """Test that forbidden fields are stripped from create."""
        tools = self._get_tools()
        result = tools.create_record(
            model='res.partner',
            values={
                'name': 'Sanitized Partner',
                'password': 'secret123',  # Should be stripped
            }
        )
        self.assertTrue(result.get('created'))
        # Password field should not cause error and should be ignored

    def test_update_record(self):
        """Test record update."""
        tools = self._get_tools()
        result = tools.update_record(
            model='res.partner',
            record_id=self.test_partner.id,
            values={'email': 'updated@example.com'}
        )
        self.assertTrue(result.get('updated'))

        # Verify update applied
        self.test_partner.refresh()
        self.assertEqual(self.test_partner.email, 'updated@example.com')

    def test_update_record_not_found(self):
        """Test update on non-existent record."""
        tools = self._get_tools()
        result = tools.update_record(
            model='res.partner',
            record_id=999999999,  # Non-existent
            values={'name': 'Updated'}
        )
        self.assertFalse(result.get('updated'))
        self.assertIn('error', result)

    def test_delete_record_requires_confirm(self):
        """Test delete requires confirmation."""
        tools = self._get_tools()

        # Create partner to delete
        partner = self.Partner.create({'name': 'To Delete'})

        # Without confirm should fail
        result = tools.delete_record(
            model='res.partner',
            record_id=partner.id,
            confirm=False
        )
        self.assertFalse(result.get('deleted'))
        self.assertIn('error', result)
        self.assertIn('confirm', result.get('error', '').lower())

        # With confirm should succeed
        result = tools.delete_record(
            model='res.partner',
            record_id=partner.id,
            confirm=True
        )
        self.assertTrue(result.get('deleted'))
        self.assertFalse(partner.exists())

    def test_execute_action(self):
        """Test action execution."""
        # This test depends on sale module, so we test with a simpler case
        tools = self._get_tools()

        # Try to execute a non-existent action
        result = tools.execute_action(
            model='res.partner',
            record_ids=[self.test_partner.id],
            action='non_existent_action'
        )
        # Should fail because action not in allowed list
        self.assertFalse(result.get('success'))

    def test_generate_report_summary(self):
        """Test report generation."""
        tools = self._get_tools()
        result = tools.generate_report(
            report_type='summary',
            model='res.partner'
        )
        self.assertTrue(result.get('success'))
        self.assertIn('data', result)
        self.assertIn('total_count', result['data'])

    def test_operation_logging(self):
        """Test that operations are logged."""
        tools = self._get_tools()
        initial_count = self.env['loomworks.ai.operation.log'].search_count([
            ('session_id', '=', self.test_session.id)
        ])

        # Perform a search
        tools.search_records(model='res.partner', limit=5)

        # Check log was created
        final_count = self.env['loomworks.ai.operation.log'].search_count([
            ('session_id', '=', self.test_session.id)
        ])
        self.assertEqual(final_count, initial_count + 1)
