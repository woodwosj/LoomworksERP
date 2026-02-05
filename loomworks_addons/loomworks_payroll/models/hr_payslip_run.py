# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from datetime import date, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrPayslipRun(models.Model):
    """
    Payslip Run - Batch processing for multiple payslips.

    Allows generating and processing multiple payslips at once:
    - Select employees or departments
    - Generate payslips for all
    - Compute all payslips
    - Confirm all at once
    """
    _name = 'hr.payslip.run'
    _description = 'Payslip Batch'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, id desc'

    name = fields.Char(
        string='Name',
        required=True,
        default=lambda self: _('Payslip Batch - %s') % date.today().strftime('%B %Y'))
    date_start = fields.Date(
        string='Date From',
        required=True,
        default=lambda self: date.today().replace(day=1))
    date_end = fields.Date(
        string='Date To',
        required=True,
        default=lambda self: (date.today().replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1))

    # Payslips in batch
    slip_ids = fields.One2many(
        'hr.payslip',
        'payslip_run_id',
        string='Payslips')
    slip_count = fields.Integer(
        string='Payslip Count',
        compute='_compute_slip_count')

    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Waiting'),
        ('close', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True)

    # Optional filters
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        help="Generate payslips only for employees in this department")
    struct_id = fields.Many2one(
        'hr.payroll.structure',
        string='Salary Structure',
        help="Force this structure for all generated payslips")

    @api.depends('slip_ids')
    def _compute_slip_count(self):
        for run in self:
            run.slip_count = len(run.slip_ids)

    def action_draft(self):
        """Reset batch to draft."""
        self.slip_ids.action_payslip_draft()
        return self.write({'state': 'draft'})

    def action_verify(self):
        """Compute all payslips and mark as waiting."""
        self.slip_ids.compute_sheet()
        self.slip_ids.action_payslip_verify()
        return self.write({'state': 'verify'})

    def action_close(self):
        """Confirm all payslips."""
        self.slip_ids.action_payslip_done()
        return self.write({'state': 'close'})

    def action_cancel(self):
        """Cancel batch and all payslips."""
        self.slip_ids.action_payslip_cancel()
        return self.write({'state': 'cancel'})

    def action_open_payslips(self):
        """Open payslips in this batch."""
        self.ensure_one()
        return {
            'name': _('Payslips'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip',
            'view_mode': 'list,form',
            'domain': [('payslip_run_id', '=', self.id)],
            'context': {
                'default_payslip_run_id': self.id,
                'default_date_from': self.date_start,
                'default_date_to': self.date_end,
            },
        }

    def unlink(self):
        if any(run.state not in ('draft', 'cancel') for run in self):
            raise UserError(_("You cannot delete a confirmed batch. Cancel it first."))
        return super().unlink()
