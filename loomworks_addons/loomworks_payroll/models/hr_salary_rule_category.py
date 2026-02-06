# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from loomworks import api, fields, models


class HrSalaryRuleCategory(models.Model):
    """
    Salary Rule Category - Groups salary rules for organization and reporting.

    Standard categories:
    - BASIC: Base salary/wage
    - ALW: Allowances (housing, transport, etc.)
    - GROSS: Gross wages before deductions
    - DED: Deductions (taxes, benefits, etc.)
    - COMP: Company contributions
    - NET: Net pay after deductions
    """
    _name = 'hr.salary.rule.category'
    _description = 'Salary Rule Category'
    _order = 'sequence, id'

    name = fields.Char(
        string='Name',
        required=True,
        translate=True)
    code = fields.Char(
        string='Code',
        required=True,
        help="Unique code for referencing in computations (e.g., GROSS, NET)")
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Order in which categories appear on payslip")
    parent_id = fields.Many2one(
        'hr.salary.rule.category',
        string='Parent Category',
        index=True,
        help="Parent category for hierarchical organization")
    children_ids = fields.One2many(
        'hr.salary.rule.category',
        'parent_id',
        string='Child Categories')
    note = fields.Text(
        string='Description',
        translate=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company)

    _sql_constraints = [
        ('code_company_uniq', 'unique(code, company_id)',
         'The code of the category must be unique per company!'),
    ]

    @api.depends('name', 'code')
    def _compute_display_name(self):
        for category in self:
            category.display_name = f"[{category.code}] {category.name}"
