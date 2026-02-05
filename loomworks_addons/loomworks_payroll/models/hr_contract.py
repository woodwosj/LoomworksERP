# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class HrContract(models.Model):
    """
    Extension of hr.contract for payroll integration.

    Adds relationship to payslips and helper methods for
    wage computation.
    """
    _inherit = 'hr.contract'

    # Tax Filing Status (US)
    filing_status = fields.Selection([
        ('single', 'Single'),
        ('married_jointly', 'Married Filing Jointly'),
        ('married_separately', 'Married Filing Separately'),
        ('head_of_household', 'Head of Household'),
    ], string='Filing Status', default='single',
        help='Federal tax filing status for W-4 withholding')
    federal_allowances = fields.Integer(
        string='Federal Allowances', default=1,
        help='Number of federal withholding allowances')
    state_allowances = fields.Integer(
        string='State Allowances', default=1,
        help='Number of state withholding allowances')
    additional_federal_withholding = fields.Float(
        string='Additional Federal Withholding', default=0.0,
        help='Additional amount to withhold for federal taxes per pay period')
    additional_state_withholding = fields.Float(
        string='Additional State Withholding', default=0.0,
        help='Additional amount to withhold for state taxes per pay period')
    hourly_wage = fields.Float(
        string='Hourly Wage', default=0.0,
        help='Hourly wage rate for hourly employees')

    # Payslips for this contract
    payslip_ids = fields.One2many(
        'hr.payslip',
        'contract_id',
        string='Payslips')
    payslip_count = fields.Integer(
        string='Payslip Count',
        compute='_compute_payslip_count')

    @api.depends('payslip_ids')
    def _compute_payslip_count(self):
        for contract in self:
            contract.payslip_count = len(contract.payslip_ids)

    def action_open_payslips(self):
        """Open payslips for this contract."""
        self.ensure_one()
        return {
            'name': _('Payslips'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip',
            'view_mode': 'list,form',
            'domain': [('contract_id', '=', self.id)],
            'context': {
                'default_contract_id': self.id,
                'default_employee_id': self.employee_id.id,
            },
        }

    def get_wage_for_period(self, date_from, date_to):
        """
        Calculate the wage amount for a given period.

        Handles both monthly and hourly wage types.

        Args:
            date_from: Start date of period
            date_to: End date of period

        Returns:
            float: Wage amount for the period
        """
        self.ensure_one()
        wage_type = self.structure_type_id.wage_type if self.structure_type_id else 'monthly'

        if wage_type == 'hourly':
            # For hourly, wage is per hour - calculation handled by rules
            return self.hourly_wage or 0.0
        else:
            # For monthly, wage is the full monthly amount
            return self.wage or 0.0
