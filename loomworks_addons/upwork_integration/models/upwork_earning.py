# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Upwork Earning model - Represents earnings from an Upwork contract.
"""

import logging

from loomworks import api, fields, models, _
from loomworks.exceptions import UserError

_logger = logging.getLogger(__name__)


class UpworkEarning(models.Model):
    """Upwork Earning synced from the Upwork API."""
    _name = 'upwork.earning'
    _description = 'Upwork Earning'
    _order = 'date desc'

    name = fields.Char(
        string='Description',
        required=True,
    )
    upwork_earning_id = fields.Char(
        string='Upwork Earning ID',
        index=True,
    )
    date = fields.Date(
        string='Date',
        required=True,
        index=True,
    )
    period_start = fields.Date(
        string='Period Start',
    )
    period_end = fields.Date(
        string='Period End',
    )
    gross_amount = fields.Monetary(
        string='Gross Amount',
        currency_field='currency_id',
        required=True,
    )
    upwork_fee = fields.Monetary(
        string='Upwork Fee',
        currency_field='currency_id',
    )
    upwork_fee_percent = fields.Float(
        string='Fee %',
    )
    net_amount = fields.Monetary(
        string='Net Amount',
        currency_field='currency_id',
    )
    total_hours = fields.Float(
        string='Total Hours',
    )
    contract_id = fields.Many2one(
        'upwork.contract',
        string='Contract',
        required=True,
        ondelete='cascade',
        index=True,
    )
    upwork_account_id = fields.Many2one(
        'upwork.account',
        string='Upwork Account',
        ondelete='set null',
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Client',
        ondelete='set null',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        ondelete='set null',
        index=True,
        copy=False,
    )
    journal_entry_id = fields.Many2one(
        'account.move',
        string='Fee Journal Entry',
        ondelete='set null',
        copy=False,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        (
            'upwork_earning_upwork_earning_unique',
            'UNIQUE(upwork_earning_id, contract_id)',
            'Earning ID must be unique per contract.',
        ),
        (
            'upwork_earning_invoice_unique',
            'UNIQUE(invoice_id)',
            'An invoice can only be linked to one earning.',
        ),
    ]

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_create_invoice(self):
        """Create a customer invoice from this earning."""
        self.ensure_one()
        if self.invoice_id:
            raise UserError(_("An invoice already exists for this earning."))

        partner = self.partner_id or self.contract_id.partner_id
        if not partner:
            raise UserError(_("Please set a client on the earning or the related contract."))

        # Get income account from settings
        ICP = self.env['ir.config_parameter'].sudo()
        income_account_id = int(ICP.get_param('upwork_integration.upwork_income_account_id', '0'))
        income_account = self.env['account.account'].browse(income_account_id) if income_account_id else False

        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': self.date,
            'currency_id': self.currency_id.id,
            'company_id': self.company_id.id,
            'ref': f'Upwork: {self.name}',
            'invoice_line_ids': [(0, 0, {
                'name': self.name or f'Upwork Earning - {self.contract_id.name}',
                'quantity': self.total_hours or 1.0,
                'price_unit': (
                    self.contract_id.hourly_rate
                    if self.contract_id.contract_type == 'hourly' and self.total_hours
                    else self.gross_amount
                ),
                'account_id': income_account.id if income_account else False,
            })],
        }

        invoice = self.env['account.move'].create(invoice_vals)
        self.write({'invoice_id': invoice.id})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Invoice Created"),
                'message': _("Draft invoice created for %s.", self.name),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_create_invoices(self):
        """Batch create invoices for multiple earnings. Called by server action."""
        created_count = 0
        errors = []
        for record in self:
            if record.invoice_id:
                continue
            try:
                record.action_create_invoice()
                created_count += 1
            except UserError as e:
                errors.append(f"{record.name}: {e}")

        if errors:
            _logger.warning("Invoice creation errors: %s", errors)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Invoices Created"),
                'message': _("Created %d invoices.", created_count),
                'type': 'success' if not errors else 'warning',
                'sticky': bool(errors),
            }
        }

    def action_create_fee_entry(self):
        """Create a journal entry for the Upwork service fee."""
        self.ensure_one()
        if self.journal_entry_id:
            raise UserError(_("A fee journal entry already exists for this earning."))

        if not self.upwork_fee or self.upwork_fee == 0:
            raise UserError(_("No Upwork fee to record."))

        # Get fee accounts from settings
        ICP = self.env['ir.config_parameter'].sudo()
        expense_account_id = int(ICP.get_param('upwork_integration.upwork_fee_expense_account_id', '0'))
        payable_account_id = int(ICP.get_param('upwork_integration.upwork_fee_payable_account_id', '0'))

        expense_account = self.env['account.account'].browse(expense_account_id) if expense_account_id else False
        payable_account = self.env['account.account'].browse(payable_account_id) if payable_account_id else False

        if not expense_account or not payable_account:
            raise UserError(_(
                "Please configure Upwork fee accounts in Settings > Upwork Integration."
            ))

        journal = self.env['account.journal'].search([
            ('type', '=', 'general'),
            ('company_id', '=', self.company_id.id),
        ], limit=1)

        if not journal:
            raise UserError(_("No miscellaneous journal found for this company."))

        entry_vals = {
            'move_type': 'entry',
            'journal_id': journal.id,
            'date': self.date,
            'ref': f'Upwork Fee: {self.name}',
            'company_id': self.company_id.id,
            'line_ids': [
                (0, 0, {
                    'name': f'Upwork Service Fee - {self.name}',
                    'account_id': expense_account.id,
                    'debit': abs(self.upwork_fee),
                    'credit': 0.0,
                    'currency_id': self.currency_id.id,
                }),
                (0, 0, {
                    'name': f'Upwork Fee Payable - {self.name}',
                    'account_id': payable_account.id,
                    'debit': 0.0,
                    'credit': abs(self.upwork_fee),
                    'currency_id': self.currency_id.id,
                }),
            ],
        }

        entry = self.env['account.move'].create(entry_vals)
        self.write({'journal_entry_id': entry.id})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Fee Entry Created"),
                'message': _("Journal entry created for Upwork fee of %s.", self.upwork_fee),
                'type': 'success',
                'sticky': False,
            }
        }
