# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrPayrollStructure(models.Model):
    """
    Payroll Structure - Defines salary templates that group salary rules.

    A structure contains a set of salary rules that are computed together
    to generate a payslip. Structures can inherit from parent structures
    to share common rules.

    Example structures:
    - US Salaried Employee (Federal)
    - US Hourly Employee (Federal)
    - California Salaried Employee (inherits from US Salaried)
    """
    _name = 'hr.payroll.structure'
    _description = 'Payroll Structure'
    _order = 'sequence, id'

    name = fields.Char(
        string='Name',
        required=True,
        translate=True)
    code = fields.Char(
        string='Reference',
        required=True,
        help="Unique code for this structure")
    sequence = fields.Integer(
        string='Sequence',
        default=10)
    active = fields.Boolean(
        string='Active',
        default=True)

    # Company and localization
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True)
    country_id = fields.Many2one(
        'res.country',
        string='Country',
        related='company_id.country_id',
        store=True)
    country_code = fields.Char(
        related='country_id.code')
    state_id = fields.Many2one(
        'res.country.state',
        string='State/Province',
        domain="[('country_id', '=', country_id)]",
        help="State-specific structure (e.g., California)")

    # Link to structure type (defined in hr_contract core)
    type_id = fields.Many2one(
        'hr.payroll.structure.type',
        string='Structure Type',
        required=True,
        help="Type determines wage calculation (monthly vs hourly)")

    # Rule configuration
    rule_ids = fields.Many2many(
        'hr.salary.rule',
        'hr_structure_salary_rule_rel',
        'struct_id',
        'rule_id',
        string='Salary Rules',
        help="Rules that are computed for this structure")

    # Inheritance
    parent_id = fields.Many2one(
        'hr.payroll.structure',
        string='Parent Structure',
        help="Inherit rules from a parent structure")
    children_ids = fields.One2many(
        'hr.payroll.structure',
        'parent_id',
        string='Child Structures')

    # Pay schedule
    schedule_pay = fields.Selection([
        ('weekly', 'Weekly'),
        ('bi-weekly', 'Bi-Weekly'),
        ('semi-monthly', 'Semi-Monthly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annually', 'Annually'),
    ], string='Scheduled Pay', default='monthly', required=True,
        help="How often employees are paid using this structure")

    # Number of pay periods per year (for annualization)
    pay_periods_per_year = fields.Integer(
        string='Pay Periods Per Year',
        compute='_compute_pay_periods',
        store=True)

    note = fields.Text(
        string='Description',
        translate=True)

    _sql_constraints = [
        ('code_company_uniq', 'unique(code, company_id)',
         'The code of the structure must be unique per company!'),
    ]

    @api.depends('schedule_pay')
    def _compute_pay_periods(self):
        periods_map = {
            'weekly': 52,
            'bi-weekly': 26,
            'semi-monthly': 24,
            'monthly': 12,
            'quarterly': 4,
            'annually': 1,
        }
        for structure in self:
            structure.pay_periods_per_year = periods_map.get(structure.schedule_pay, 12)

    def get_all_rules(self):
        """
        Get all rules for this structure, including inherited from parent.

        Returns:
            recordset: All applicable salary rules, sorted by sequence
        """
        self.ensure_one()
        rules = self.rule_ids
        if self.parent_id:
            rules |= self.parent_id.get_all_rules()
        return rules.sorted('sequence')

    @api.depends('name', 'code')
    def _compute_display_name(self):
        for structure in self:
            structure.display_name = f"[{structure.code}] {structure.name}"

    @api.model
    def _get_default_rule_ids(self):
        """Get default rules for a new structure based on company country."""
        # This can be overridden for specific localizations
        return []
