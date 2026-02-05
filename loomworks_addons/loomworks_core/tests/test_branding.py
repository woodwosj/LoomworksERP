# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestLoomworksBranding(TransactionCase):
    """Test cases for Loomworks Core branding module."""

    def test_module_installed(self):
        """Test that loomworks_core module is properly installed."""
        module = self.env['ir.module.module'].search([
            ('name', '=', 'loomworks_core'),
            ('state', '=', 'installed'),
        ])
        self.assertTrue(module, "loomworks_core module should be installed")

    def test_company_model_extension(self):
        """Test that res.company model is accessible."""
        company = self.env['res.company'].search([], limit=1)
        self.assertTrue(company, "Should be able to query res.company")

    def test_template_inheritance(self):
        """Test that template overrides are registered."""
        # Check that our templates exist in the database
        templates = self.env['ir.ui.view'].search([
            ('key', 'like', 'loomworks_core.%'),
        ])
        # We should have our template overrides registered
        self.assertTrue(
            len(templates) >= 1,
            "Loomworks template overrides should be registered"
        )
