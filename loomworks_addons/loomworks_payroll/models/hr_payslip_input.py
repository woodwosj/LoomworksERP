# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from loomworks import api, fields, models


class HrPayslipInput(models.Model):
    """
    Payslip Input - Additional inputs for payslip calculations.

    Used to add variable amounts that affect the payslip:
    - Bonuses
    - Commissions
    - Expense reimbursements
    - Manual deductions
    - Other adjustments
    """
    _name = 'hr.payslip.input'
    _description = 'Payslip Input'
    _order = 'sequence, id'

    payslip_id = fields.Many2one(
        'hr.payslip',
        string='Payslip',
        required=True,
        ondelete='cascade',
        index=True)
    contract_id = fields.Many2one(
        'hr.contract',
        string='Contract',
        related='payslip_id.contract_id',
        store=True)

    name = fields.Char(
        string='Description',
        required=True)
    code = fields.Char(
        string='Code',
        required=True,
        help="Code for referencing in rule computations (e.g., BONUS, COMMISSION)")
    sequence = fields.Integer(
        string='Sequence',
        default=10)

    # Input values
    amount = fields.Float(
        string='Amount',
        help="The input amount")
    quantity = fields.Float(
        string='Quantity',
        default=1.0,
        help="Quantity multiplier")

    # Input type
    input_type_id = fields.Many2one(
        'hr.payslip.input.type',
        string='Input Type',
        help="Predefined input type for quick entry")

    @api.onchange('input_type_id')
    def _onchange_input_type_id(self):
        if self.input_type_id:
            self.code = self.input_type_id.code
            self.name = self.input_type_id.name

    @api.depends('name', 'code')
    def _compute_display_name(self):
        for inp in self:
            inp.display_name = f"[{inp.code}] {inp.name}"


class HrPayslipInputType(models.Model):
    """
    Payslip Input Type - Predefined input types for quick entry.

    Examples:
    - BONUS: Performance Bonus
    - COMMISSION: Sales Commission
    - REIMBURSE: Expense Reimbursement
    """
    _name = 'hr.payslip.input.type'
    _description = 'Payslip Input Type'

    name = fields.Char(
        string='Name',
        required=True,
        translate=True)
    code = fields.Char(
        string='Code',
        required=True)
    description = fields.Text(
        string='Description',
        translate=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company)

    _sql_constraints = [
        ('code_company_uniq', 'unique(code, company_id)',
         'The code of the input type must be unique per company!'),
    ]
