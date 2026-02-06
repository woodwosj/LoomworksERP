# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import date, datetime, timedelta

from loomworks import api, fields, models, _
from loomworks.exceptions import UserError, ValidationError
from loomworks.tools.safe_eval import safe_eval, datetime as safe_datetime, dateutil, time
import logging

_logger = logging.getLogger(__name__)


class BrowsableObject:
    """
    Helper class providing attribute access to dictionary values.
    Used to access rules, categories, worked_days, and inputs by code.
    """
    def __init__(self, employee_id, dict_values, env):
        self.employee_id = employee_id
        self.dict = dict_values
        self.env = env

    def __getattr__(self, attr):
        return self.dict.get(attr, 0.0)

    def __getitem__(self, key):
        return self.dict.get(key, 0.0)

    def __contains__(self, key):
        return key in self.dict


class InputLine:
    """Wrapper for input line values accessed by code."""
    def __init__(self, employee_id, input_dict, env):
        self.employee_id = employee_id
        self.dict = input_dict
        self.env = env

    def __getattr__(self, attr):
        input_line = self.dict.get(attr)
        if input_line:
            return input_line.get('amount', 0.0)
        return 0.0


class WorkedDays:
    """Wrapper for worked days values accessed by code."""
    def __init__(self, employee_id, worked_days_dict, env):
        self.employee_id = employee_id
        self.dict = worked_days_dict
        self.env = env

    def __getattr__(self, attr):
        worked_day = self.dict.get(attr)
        if worked_day:
            return worked_day
        return type('WorkedDay', (), {
            'number_of_days': 0.0,
            'number_of_hours': 0.0,
            'amount': 0.0,
        })()


class Payslips:
    """Wrapper for sum of payslip lines by code across multiple payslips."""
    def __init__(self, employee_id, payslip, env):
        self.employee_id = employee_id
        self.payslip = payslip
        self.env = env

    def sum(self, code, from_date, to_date=None):
        """Sum payslip line totals for a given rule code."""
        if to_date is None:
            to_date = fields.Date.today()

        domain = [
            ('slip_id.employee_id', '=', self.employee_id),
            ('slip_id.state', '=', 'done'),
            ('slip_id.date_from', '>=', from_date),
            ('slip_id.date_to', '<=', to_date),
            ('code', '=', code),
        ]
        lines = self.env['hr.payslip.line'].search(domain)
        return sum(lines.mapped('total'))


class HrPayslip(models.Model):
    """
    Payslip - Employee salary document for a pay period.

    The payslip computes salary based on:
    - Contract wage and type
    - Salary structure rules
    - Worked days (from attendance/timesheet)
    - Input lines (bonuses, deductions, etc.)
    """
    _name = 'hr.payslip'
    _description = 'Payslip'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc, id desc'

    name = fields.Char(
        string='Payslip Name',
        compute='_compute_name',
        store=True,
        readonly=False)
    number = fields.Char(
        string='Reference',
        readonly=True,
        copy=False,
        help="Unique payslip reference number")

    # Employee and contract
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        tracking=True,
        domain="[('company_id', '=', company_id)]")
    contract_id = fields.Many2one(
        'hr.contract',
        string='Contract',
        compute='_compute_contract',
        store=True,
        readonly=False,
        domain="[('employee_id', '=', employee_id), ('state', 'in', ['open', 'close'])]")
    struct_id = fields.Many2one(
        'hr.payroll.structure',
        string='Structure',
        compute='_compute_struct',
        store=True,
        readonly=False,
        required=True)

    # Pay period
    date_from = fields.Date(
        string='Date From',
        required=True,
        default=lambda self: date.today().replace(day=1),
        tracking=True)
    date_to = fields.Date(
        string='Date To',
        required=True,
        default=lambda self: (date.today().replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1),
        tracking=True)

    # State workflow
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Waiting Verification'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, copy=False,
        help="* Draft: Payslip can be modified\n"
             "* Waiting: Payslip computed, waiting for approval\n"
             "* Done: Payslip confirmed and locked\n"
             "* Cancelled: Payslip is voided")

    # Computed lines
    line_ids = fields.One2many(
        'hr.payslip.line',
        'slip_id',
        string='Payslip Lines',
        copy=True,
        readonly=True,
        states={'draft': [('readonly', False)]})
    input_line_ids = fields.One2many(
        'hr.payslip.input',
        'payslip_id',
        string='Input Lines',
        copy=True,
        readonly=True,
        states={'draft': [('readonly', False)]})
    worked_days_line_ids = fields.One2many(
        'hr.payslip.worked_days',
        'payslip_id',
        string='Worked Days',
        copy=True,
        readonly=True,
        states={'draft': [('readonly', False)]})

    # Totals
    gross_wage = fields.Monetary(
        string='Gross',
        compute='_compute_totals',
        store=True)
    net_wage = fields.Monetary(
        string='Net',
        compute='_compute_totals',
        store=True)
    total_deductions = fields.Monetary(
        string='Deductions',
        compute='_compute_totals',
        store=True)

    # Company and currency
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True)
    currency_id = fields.Many2one(
        related='company_id.currency_id',
        readonly=True)

    # Batch processing
    payslip_run_id = fields.Many2one(
        'hr.payslip.run',
        string='Payslip Batch',
        readonly=True,
        copy=False)

    # Notes
    note = fields.Text(
        string='Internal Note')
    credit_note = fields.Boolean(
        string='Credit Note',
        default=False,
        help="Indicates this is a correction/reversal payslip")

    # Paid status
    paid = fields.Boolean(
        string='Paid',
        default=False,
        help="Mark when payment has been processed")
    paid_date = fields.Date(
        string='Paid Date')

    @api.depends('employee_id', 'date_from', 'date_to')
    def _compute_name(self):
        for payslip in self:
            if payslip.employee_id and payslip.date_from and payslip.date_to:
                payslip.name = _("Salary Slip of %s for %s") % (
                    payslip.employee_id.name,
                    payslip.date_from.strftime('%B %Y')
                )
            else:
                payslip.name = _("New Payslip")

    @api.depends('employee_id', 'date_from', 'date_to', 'company_id')
    def _compute_contract(self):
        for payslip in self:
            if not payslip.employee_id:
                payslip.contract_id = False
                continue

            # Find contract valid for the payslip period
            contract = self.env['hr.contract'].search([
                ('employee_id', '=', payslip.employee_id.id),
                ('company_id', '=', payslip.company_id.id),
                ('state', 'in', ['open', 'close']),
                ('date_start', '<=', payslip.date_to),
                '|',
                ('date_end', '=', False),
                ('date_end', '>=', payslip.date_from),
            ], order='date_start desc', limit=1)
            payslip.contract_id = contract

    @api.depends('contract_id')
    def _compute_struct(self):
        for payslip in self:
            if payslip.contract_id and payslip.contract_id.structure_type_id:
                # Find structure matching the type
                struct = self.env['hr.payroll.structure'].search([
                    ('type_id', '=', payslip.contract_id.structure_type_id.id),
                    ('company_id', '=', payslip.company_id.id),
                ], limit=1)
                payslip.struct_id = struct or payslip.struct_id
            elif not payslip.struct_id:
                # Default to first structure for company
                payslip.struct_id = self.env['hr.payroll.structure'].search([
                    ('company_id', '=', payslip.company_id.id),
                ], limit=1)

    @api.depends('line_ids.total')
    def _compute_totals(self):
        for payslip in self:
            gross_lines = payslip.line_ids.filtered(
                lambda l: l.category_id.code == 'GROSS')
            net_lines = payslip.line_ids.filtered(
                lambda l: l.category_id.code == 'NET')
            deduction_lines = payslip.line_ids.filtered(
                lambda l: l.category_id.code == 'DED' or l.total < 0)

            payslip.gross_wage = sum(gross_lines.mapped('total'))
            payslip.net_wage = sum(net_lines.mapped('total'))
            payslip.total_deductions = abs(sum(deduction_lines.mapped('total')))

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for payslip in self:
            if payslip.date_from > payslip.date_to:
                raise ValidationError(_(
                    "The start date must be before or equal to the end date."
                ))

    def action_payslip_draft(self):
        """Reset payslip to draft state."""
        return self.write({'state': 'draft'})

    def action_payslip_done(self):
        """Confirm payslip - generates reference number."""
        for payslip in self:
            if not payslip.number:
                payslip.number = self.env['ir.sequence'].next_by_code(
                    'hr.payslip') or _('New')
        return self.write({'state': 'done'})

    def action_payslip_cancel(self):
        """Cancel payslip."""
        return self.write({'state': 'cancel'})

    def action_payslip_verify(self):
        """Mark as waiting verification after computation."""
        return self.write({'state': 'verify'})

    def compute_sheet(self):
        """
        Main computation method - calculates all salary rule amounts.

        This method:
        1. Computes worked days
        2. Gathers inputs
        3. Evaluates all rules in sequence order
        4. Creates payslip lines
        """
        for payslip in self:
            if payslip.state != 'draft':
                continue

            # Clear existing lines
            payslip.line_ids.unlink()

            # Get contract and structure
            contract = payslip.contract_id
            if not contract:
                raise UserError(_("No contract found for employee %s in the selected period.") % payslip.employee_id.name)

            structure = payslip.struct_id
            if not structure:
                raise UserError(_("No salary structure defined for this payslip."))

            # Compute worked days if not already set
            if not payslip.worked_days_line_ids:
                payslip._compute_worked_days()

            # Get all rules from structure
            rules = structure.get_all_rules()

            # Build computation context
            localdict = payslip._get_localdict()

            # Dictionaries to track computed values
            categories_dict = defaultdict(float)
            rules_dict = {}

            # Create payslip lines
            lines = []
            for rule in rules:
                # Check if rule condition is satisfied
                if not rule._satisfy_condition(localdict):
                    continue

                # Compute rule amount
                amount, qty, rate = rule._compute_rule(localdict)
                total = amount * qty * rate / 100

                # Track values for subsequent rules
                rules_dict[rule.code] = total
                categories_dict[rule.category_id.code] += total

                # Update localdict for next rules
                localdict['rules'] = BrowsableObject(
                    payslip.employee_id.id, rules_dict, self.env)
                localdict['categories'] = BrowsableObject(
                    payslip.employee_id.id, dict(categories_dict), self.env)

                # Create line if it appears on payslip or has amount
                if rule.appears_on_payslip or total:
                    lines.append({
                        'slip_id': payslip.id,
                        'salary_rule_id': rule.id,
                        'name': rule.name,
                        'code': rule.code,
                        'category_id': rule.category_id.id,
                        'sequence': rule.sequence,
                        'quantity': qty,
                        'rate': rate,
                        'amount': amount,
                    })

            # Create all lines
            self.env['hr.payslip.line'].create(lines)

        return True

    def _get_localdict(self):
        """
        Build the local dictionary for rule evaluation.

        Returns:
            dict: Context dictionary with all available variables
        """
        self.ensure_one()
        contract = self.contract_id
        employee = self.employee_id

        # Build worked days dictionary
        worked_days_dict = {}
        for wd in self.worked_days_line_ids:
            worked_days_dict[wd.code] = type('WorkedDay', (), {
                'number_of_days': wd.number_of_days,
                'number_of_hours': wd.number_of_hours,
                'amount': wd.amount,
            })()

        # Build inputs dictionary
        inputs_dict = {}
        for inp in self.input_line_ids:
            inputs_dict[inp.code] = {
                'amount': inp.amount,
                'quantity': inp.quantity,
            }

        return {
            'categories': BrowsableObject(employee.id, {}, self.env),
            'rules': BrowsableObject(employee.id, {}, self.env),
            'payslip': self,
            'employee': employee,
            'contract': contract,
            'worked_days': WorkedDays(employee.id, worked_days_dict, self.env),
            'inputs': InputLine(employee.id, inputs_dict, self.env),
            'payslips': Payslips(employee.id, self, self.env),
            'result': 0.0,
            'result_qty': 1.0,
            'result_rate': 100.0,
        }

    def _compute_worked_days(self):
        """Compute worked days from contract calendar and attendance."""
        for payslip in self:
            contract = payslip.contract_id
            if not contract:
                continue

            # Get resource calendar
            calendar = contract.resource_calendar_id or contract.company_id.resource_calendar_id
            if not calendar:
                continue

            # Calculate standard working days/hours
            date_from = datetime.combine(payslip.date_from, datetime.min.time())
            date_to = datetime.combine(payslip.date_to, datetime.max.time())

            work_data = calendar.get_work_duration_data(
                date_from, date_to,
                compute_leaves=True,
                resource=payslip.employee_id.resource_id)

            days = work_data.get('days', 0)
            hours = work_data.get('hours', 0)

            # Create worked days line
            self.env['hr.payslip.worked_days'].create({
                'payslip_id': payslip.id,
                'name': _('Regular Working Days'),
                'code': 'WORK100',
                'number_of_days': days,
                'number_of_hours': hours,
                'contract_id': contract.id,
            })

    def action_print_payslip(self):
        """Print payslip PDF report."""
        return self.env.ref('loomworks_payroll.action_report_payslip').report_action(self)

    @api.model_create_multi
    def create(self, vals_list):
        payslips = super().create(vals_list)
        return payslips

    def unlink(self):
        if any(payslip.state not in ('draft', 'cancel') for payslip in self):
            raise UserError(_("You cannot delete a confirmed payslip. Cancel it first."))
        return super().unlink()
