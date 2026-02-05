# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval, datetime, dateutil, time
import logging

_logger = logging.getLogger(__name__)


class HrSalaryRule(models.Model):
    """
    Salary Rule - Individual computation rule for payslip calculations.

    Rules can compute amounts using:
    - Fixed amount
    - Percentage of a base
    - Python code expression

    The Python code has access to:
    - categories: Dict of computed category totals
    - rules: Dict of other rule results by code
    - payslip: Current payslip record
    - employee: Employee record
    - contract: Contract record (with filing_status, wage, etc.)
    - worked_days: Dict of worked days by code
    - inputs: Dict of input lines by code
    - result: Set the computed amount
    - result_qty: Set quantity (default 1.0)
    - result_rate: Set rate percentage (default 100.0)
    """
    _name = 'hr.salary.rule'
    _description = 'Salary Rule'
    _order = 'sequence, id'

    name = fields.Char(
        string='Name',
        required=True,
        translate=True)
    code = fields.Char(
        string='Code',
        required=True,
        help="Unique code for referencing in computations (e.g., BASIC, FED_INC)")
    sequence = fields.Integer(
        string='Sequence',
        default=100,
        help="Determines the order of rule evaluation. Lower numbers compute first.")
    active = fields.Boolean(
        string='Active',
        default=True)

    # Category
    category_id = fields.Many2one(
        'hr.salary.rule.category',
        string='Category',
        required=True,
        help="Category groups rules for organization and reporting")

    # Computation method
    amount_select = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage'),
        ('code', 'Python Code'),
    ], string='Amount Type', default='fixed', required=True,
        help="How the rule amount is computed")

    amount_fix = fields.Float(
        string='Fixed Amount',
        default=0.0,
        help="Fixed amount when Amount Type is 'Fixed Amount'")
    amount_percentage = fields.Float(
        string='Percentage (%)',
        default=0.0,
        help="Percentage when Amount Type is 'Percentage'")
    amount_percentage_base = fields.Char(
        string='Percentage Based On',
        help="Python expression that returns the base amount for percentage calculation. "
             "Example: categories.GROSS")
    amount_python_compute = fields.Text(
        string='Python Code',
        default='''
# Available variables:
# - categories: BrowsableObject of computed category totals
# - rules: BrowsableObject of other rule results by code
# - payslip: Current payslip record
# - employee: Employee record
# - contract: Contract record (wage, filing_status, etc.)
# - worked_days: BrowsableObject of worked days by code
# - inputs: BrowsableObject of input lines by code
#
# Set these variables:
# - result: The computed amount
# - result_qty: Quantity multiplier (default 1.0)
# - result_rate: Rate percentage (default 100.0)

result = contract.wage
''',
        help="Python code to compute the rule amount")

    # Conditions
    condition_select = fields.Selection([
        ('none', 'Always True'),
        ('range', 'Range'),
        ('python', 'Python Expression'),
    ], string='Condition Type', default='none', required=True,
        help="When this rule should be applied")
    condition_range = fields.Char(
        string='Range Based On',
        default='contract.wage',
        help="Python expression returning a value to compare against the range")
    condition_range_min = fields.Float(
        string='Minimum Range',
        help="Minimum value for range condition (inclusive)")
    condition_range_max = fields.Float(
        string='Maximum Range',
        help="Maximum value for range condition (inclusive)")
    condition_python = fields.Text(
        string='Python Condition',
        default='# Return True to include this rule\nresult = True',
        help="Python code returning True/False to determine if rule applies")

    # Tax configuration
    is_tax = fields.Boolean(
        string='Is Tax Rule',
        help="Mark rules that compute tax amounts")
    tax_type = fields.Selection([
        ('federal_income', 'Federal Income Tax'),
        ('state_income', 'State Income Tax'),
        ('social_security', 'Social Security'),
        ('medicare', 'Medicare'),
        ('state_disability', 'State Disability Insurance'),
        ('state_unemployment', 'State Unemployment'),
        ('local', 'Local Tax'),
    ], string='Tax Type',
        help="Type of tax for reporting purposes")

    # Display options
    appears_on_payslip = fields.Boolean(
        string='Appears on Payslip',
        default=True,
        help="Whether this rule appears on the printed payslip")
    note = fields.Html(
        string='Description',
        translate=True,
        help="Documentation for this rule")

    # Structure link
    struct_ids = fields.Many2many(
        'hr.payroll.structure',
        'hr_structure_salary_rule_rel',
        'rule_id',
        'struct_id',
        string='Salary Structures')

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company)

    _sql_constraints = [
        ('code_company_uniq', 'unique(code, company_id)',
         'The code of the rule must be unique per company!'),
    ]

    @api.constrains('condition_range_min', 'condition_range_max')
    def _check_range(self):
        for rule in self:
            if rule.condition_select == 'range':
                if rule.condition_range_min > rule.condition_range_max:
                    raise ValidationError(_(
                        "The minimum range must be less than or equal to the maximum range."
                    ))

    def _satisfy_condition(self, localdict):
        """
        Check if the rule condition is satisfied.

        Returns:
            bool: True if the rule should be computed, False otherwise
        """
        self.ensure_one()

        if self.condition_select == 'none':
            return True

        elif self.condition_select == 'range':
            try:
                result = safe_eval(self.condition_range, localdict)
                return self.condition_range_min <= result <= self.condition_range_max
            except Exception as e:
                _logger.warning("Error evaluating range condition for %s: %s", self.code, e)
                return False

        elif self.condition_select == 'python':
            try:
                safe_eval(self.condition_python, localdict, mode='exec', nocopy=True)
                return localdict.get('result', False)
            except Exception as e:
                _logger.warning("Error evaluating python condition for %s: %s", self.code, e)
                return False

        return False

    def _compute_rule(self, localdict):
        """
        Compute the rule amount.

        Args:
            localdict: Dictionary with computation context

        Returns:
            tuple: (amount, quantity, rate)
        """
        self.ensure_one()

        amount = 0.0
        qty = 1.0
        rate = 100.0

        if self.amount_select == 'fixed':
            amount = self.amount_fix

        elif self.amount_select == 'percentage':
            try:
                base = safe_eval(self.amount_percentage_base, localdict)
                amount = float(base) * self.amount_percentage / 100
            except Exception as e:
                _logger.error("Error computing percentage base for %s: %s", self.code, e)
                amount = 0.0

        elif self.amount_select == 'code':
            try:
                # Reset result variables
                localdict['result'] = 0.0
                localdict['result_qty'] = 1.0
                localdict['result_rate'] = 100.0

                safe_eval(self.amount_python_compute, localdict, mode='exec', nocopy=True)

                amount = float(localdict.get('result', 0.0))
                qty = float(localdict.get('result_qty', 1.0))
                rate = float(localdict.get('result_rate', 100.0))
            except Exception as e:
                _logger.error("Error computing rule %s: %s", self.code, e)
                raise UserError(_(
                    "Error computing salary rule '%s':\n%s"
                ) % (self.name, str(e)))

        return amount, qty, rate

    @api.depends('name', 'code')
    def _compute_display_name(self):
        for rule in self:
            rule.display_name = f"[{rule.code}] {rule.name}"
