# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Extend res.config.settings with Upwork integration configuration fields.
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    upwork_income_account_id = fields.Many2one(
        'account.account',
        string='Income Account',
        config_parameter='upwork_integration.upwork_income_account_id',
        help='Default account for Upwork invoice lines.',
    )
    upwork_fee_expense_account_id = fields.Many2one(
        'account.account',
        string='Fee Expense Account',
        config_parameter='upwork_integration.upwork_fee_expense_account_id',
        help='Account for recording Upwork service fees.',
    )
    upwork_fee_payable_account_id = fields.Many2one(
        'account.account',
        string='Fee Payable Account',
        config_parameter='upwork_integration.upwork_fee_payable_account_id',
        help='Liability account for fees payable to Upwork.',
    )
    upwork_auto_create_timesheets = fields.Boolean(
        string='Auto-create Timesheets',
        config_parameter='upwork_integration.upwork_auto_create_timesheets',
        help='Automatically create Odoo timesheets when syncing Upwork time logs.',
    )
    upwork_auto_create_invoices = fields.Boolean(
        string='Auto-create Invoices',
        config_parameter='upwork_integration.upwork_auto_create_invoices',
        help='Automatically create draft invoices when syncing Upwork earnings.',
    )

    def action_check_upwork_financial_config(self):
        """Verify that all required financial accounts are configured."""
        self.ensure_one()
        missing = []
        if not self.upwork_income_account_id:
            missing.append(_("Income Account"))
        if not self.upwork_fee_expense_account_id:
            missing.append(_("Fee Expense Account"))
        if not self.upwork_fee_payable_account_id:
            missing.append(_("Fee Payable Account"))

        if missing:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Configuration Incomplete"),
                    'message': _("Missing accounts: %s", ', '.join(missing)),
                    'type': 'warning',
                    'sticky': True,
                }
            }

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Configuration OK"),
                'message': _("All Upwork financial accounts are configured."),
                'type': 'success',
                'sticky': False,
            }
        }
