# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Tests for Loomworks Tenant functionality.
"""

from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError, UserError


@tagged('post_install', '-at_install', 'loomworks', 'tenant')
class TestTenant(TransactionCase):
    """Test cases for loomworks.tenant model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Tenant = cls.env['loomworks.tenant']

    def test_create_tenant(self):
        """Test creating a basic tenant."""
        tenant = self.Tenant.create({
            'name': 'Acme Corporation',
            'subdomain': 'acme',
        })

        self.assertEqual(tenant.name, 'Acme Corporation')
        self.assertEqual(tenant.subdomain, 'acme')
        # Database name should be auto-generated
        self.assertEqual(tenant.database_name, 'lw_acme')
        self.assertEqual(tenant.state, 'draft')

    def test_subdomain_auto_database_name(self):
        """Test that database name is generated from subdomain."""
        tenant = self.Tenant.create({
            'name': 'Test Company',
            'subdomain': 'test-company',
        })

        # Hyphen should be converted to underscore
        self.assertEqual(tenant.database_name, 'lw_test_company')

    def test_subdomain_validation(self):
        """Test subdomain format validation."""
        # Invalid: starts with number
        with self.assertRaises(ValidationError):
            self.Tenant.create({
                'name': 'Invalid',
                'subdomain': '123test',
            })

        # Invalid: uppercase
        with self.assertRaises(ValidationError):
            self.Tenant.create({
                'name': 'Invalid',
                'subdomain': 'TestCompany',
            })

        # Invalid: too short
        with self.assertRaises(ValidationError):
            self.Tenant.create({
                'name': 'Invalid',
                'subdomain': 'ab',
            })

    def test_reserved_subdomain(self):
        """Test that reserved subdomains are rejected."""
        reserved = ['www', 'api', 'admin', 'app']

        for subdomain in reserved:
            with self.assertRaises(ValidationError):
                self.Tenant.create({
                    'name': f'Reserved {subdomain}',
                    'subdomain': subdomain,
                })

    def test_tenant_state_transitions(self):
        """Test tenant state transitions."""
        tenant = self.Tenant.create({
            'name': 'State Test',
            'subdomain': 'statetest',
        })

        # Draft -> Provisioning
        self.assertEqual(tenant.state, 'draft')
        tenant.action_provision()
        self.assertEqual(tenant.state, 'provisioning')

        # Provisioning -> Active
        tenant.action_activate()
        self.assertEqual(tenant.state, 'active')
        self.assertTrue(tenant.activated_at)

        # Active -> Suspended
        tenant.action_suspend()
        self.assertEqual(tenant.state, 'suspended')
        self.assertTrue(tenant.suspended_at)

        # Suspended -> Active
        tenant.action_activate()
        self.assertEqual(tenant.state, 'active')

    def test_invalid_state_transition(self):
        """Test that invalid state transitions raise errors."""
        tenant = self.Tenant.create({
            'name': 'Invalid Transition',
            'subdomain': 'invalidtrans',
        })

        # Cannot suspend from draft
        with self.assertRaises(UserError):
            tenant.action_suspend()

        # Cannot activate from draft
        with self.assertRaises(UserError):
            tenant.action_activate()

    def test_resource_limits(self):
        """Test resource limit checking."""
        tenant = self.Tenant.create({
            'name': 'Limits Test',
            'subdomain': 'limitstest',
            'max_users': 10,
            'max_storage_gb': 5.0,
            'max_ai_operations_daily': 100,
        })

        # Within limit
        is_within, remaining, limit = tenant.check_resource_limit('users', 5)
        self.assertTrue(is_within)
        self.assertEqual(remaining, 5)
        self.assertEqual(limit, 10)

        # At limit
        is_within, remaining, limit = tenant.check_resource_limit('users', 10)
        self.assertFalse(is_within)
        self.assertEqual(remaining, 0)

    def test_tenant_url(self):
        """Test tenant URL generation."""
        tenant = self.Tenant.create({
            'name': 'URL Test',
            'subdomain': 'urltest',
        })

        url = tenant.get_url()
        self.assertEqual(url, 'https://urltest.loomworks.app')

        url_custom = tenant.get_url(base_domain='custom.domain')
        self.assertEqual(url_custom, 'https://urltest.custom.domain')

    def test_get_tenant_for_subdomain(self):
        """Test looking up tenant by subdomain."""
        tenant = self.Tenant.create({
            'name': 'Lookup Test',
            'subdomain': 'lookuptest',
        })
        tenant.action_provision()
        tenant.action_activate()

        # Should find active tenant
        found = self.Tenant.get_tenant_for_subdomain('lookuptest')
        self.assertEqual(found, tenant)

        # Should not find inactive tenant
        not_found = self.Tenant.get_tenant_for_subdomain('nonexistent')
        self.assertFalse(not_found)

        # Should not find suspended tenant
        tenant.action_suspend()
        not_found = self.Tenant.get_tenant_for_subdomain('lookuptest')
        self.assertFalse(not_found)
