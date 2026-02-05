# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrPayslipLine(models.Model):
    """
    Payslip Line - Individual computed line item on a payslip.

    Each line represents the result of a salary rule calculation,
    showing the amount, quantity, rate, and total.
    """
    _name = 'hr.payslip.line'
    _description = 'Payslip Line'
    _order = 'sequence, id'

    slip_id = fields.Many2one(
        'hr.payslip',
        string='Payslip',
        required=True,
        ondelete='cascade',
        index=True)
    salary_rule_id = fields.Many2one(
        'hr.salary.rule',
        string='Salary Rule',
        required=True)

    name = fields.Char(
        string='Description',
        required=True)
    code = fields.Char(
        string='Code',
        required=True,
        help="Rule code for reference")
    category_id = fields.Many2one(
        'hr.salary.rule.category',
        string='Category',
        required=True)
    sequence = fields.Integer(
        string='Sequence',
        default=10)

    # Calculation values
    quantity = fields.Float(
        string='Quantity',
        default=1.0,
        help="Multiplier for the amount")
    rate = fields.Float(
        string='Rate (%)',
        default=100.0,
        help="Percentage rate applied to amount")
    amount = fields.Float(
        string='Amount',
        help="Base amount before quantity and rate")
    total = fields.Float(
        string='Total',
        compute='_compute_total',
        store=True,
        help="Computed total: amount * quantity * rate / 100")

    # Related fields for reporting
    employee_id = fields.Many2one(
        related='slip_id.employee_id',
        store=True)
    contract_id = fields.Many2one(
        related='slip_id.contract_id',
        store=True)
    date_from = fields.Date(
        related='slip_id.date_from',
        store=True)
    date_to = fields.Date(
        related='slip_id.date_to',
        store=True)
    company_id = fields.Many2one(
        related='slip_id.company_id',
        store=True)

    @api.depends('quantity', 'rate', 'amount')
    def _compute_total(self):
        for line in self:
            line.total = line.quantity * line.rate * line.amount / 100

    @api.depends('name', 'code')
    def _compute_display_name(self):
        for line in self:
            line.display_name = f"[{line.code}] {line.name}"
