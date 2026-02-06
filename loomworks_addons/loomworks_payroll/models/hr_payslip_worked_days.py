# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from loomworks import api, fields, models


class HrPayslipWorkedDays(models.Model):
    """
    Payslip Worked Days - Records the days/hours worked during a pay period.

    Used as input for salary calculations, particularly for:
    - Hourly employees (wage * hours)
    - Attendance-based deductions/additions
    - Leave without pay calculations
    """
    _name = 'hr.payslip.worked_days'
    _description = 'Payslip Worked Days'
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
        help="Code for referencing in rule computations (e.g., WORK100, LEAVE)")
    sequence = fields.Integer(
        string='Sequence',
        default=10)

    # Work quantities
    number_of_days = fields.Float(
        string='Number of Days',
        help="Number of days worked or on leave")
    number_of_hours = fields.Float(
        string='Number of Hours',
        help="Number of hours worked or on leave")

    # Optional monetary value
    amount = fields.Float(
        string='Amount',
        help="Pre-computed amount (if applicable)")

    # Work entry type (if using work entries)
    work_entry_type_id = fields.Many2one(
        'hr.work.entry.type',
        string='Work Entry Type',
        help="Type of work entry (if integrated with hr_work_entry)")

    @api.depends('name', 'code')
    def _compute_display_name(self):
        for wd in self:
            wd.display_name = f"[{wd.code}] {wd.name}"
