# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from datetime import date, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrPayslipEmployees(models.TransientModel):
    """
    Wizard to generate payslips for multiple employees at once.
    """
    _name = 'hr.payslip.employees'
    _description = 'Generate Payslips for Employees'

    employee_ids = fields.Many2many(
        'hr.employee',
        string='Employees',
        domain="[('company_id', '=', company_id)]",
        required=True)
    date_start = fields.Date(
        string='Date From',
        required=True,
        default=lambda self: date.today().replace(day=1))
    date_end = fields.Date(
        string='Date To',
        required=True,
        default=lambda self: (date.today().replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1))
    struct_id = fields.Many2one(
        'hr.payroll.structure',
        string='Salary Structure',
        help="Force this structure for all payslips (optional)")
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True)

    # Optional batch
    payslip_run_id = fields.Many2one(
        'hr.payslip.run',
        string='Add to Batch',
        help="Optionally add generated payslips to an existing batch")
    create_batch = fields.Boolean(
        string='Create New Batch',
        default=True,
        help="Create a new batch for generated payslips")

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            self.employee_ids = False
            return {
                'domain': {
                    'employee_ids': [('company_id', '=', self.company_id.id)],
                }
            }

    def action_generate_payslips(self):
        """Generate payslips for selected employees."""
        self.ensure_one()

        if not self.employee_ids:
            raise UserError(_("Please select at least one employee."))

        # Create batch if requested
        batch = self.payslip_run_id
        if self.create_batch and not batch:
            batch = self.env['hr.payslip.run'].create({
                'name': _('Payslip Batch - %s') % self.date_start.strftime('%B %Y'),
                'date_start': self.date_start,
                'date_end': self.date_end,
                'company_id': self.company_id.id,
            })

        # Generate payslips
        payslips = self.env['hr.payslip']
        errors = []

        for employee in self.employee_ids:
            try:
                # Find contract
                contract = self.env['hr.contract'].search([
                    ('employee_id', '=', employee.id),
                    ('state', 'in', ['open', 'close']),
                    ('date_start', '<=', self.date_end),
                    '|',
                    ('date_end', '=', False),
                    ('date_end', '>=', self.date_start),
                ], limit=1)

                if not contract:
                    errors.append(_("%s: No active contract") % employee.name)
                    continue

                # Prepare values
                vals = {
                    'employee_id': employee.id,
                    'date_from': self.date_start,
                    'date_to': self.date_end,
                    'contract_id': contract.id,
                    'company_id': self.company_id.id,
                }

                if self.struct_id:
                    vals['struct_id'] = self.struct_id.id

                if batch:
                    vals['payslip_run_id'] = batch.id

                payslip = self.env['hr.payslip'].create(vals)
                payslips |= payslip

            except Exception as e:
                errors.append(_("%s: %s") % (employee.name, str(e)))

        # Compute all payslips
        if payslips:
            payslips.compute_sheet()

        # Build message
        message = _("Generated %d payslips.") % len(payslips)
        if errors:
            message += _("\n\nErrors:\n%s") % "\n".join(errors)

        # Return action
        if batch:
            return {
                'name': _('Payslip Batch'),
                'type': 'ir.actions.act_window',
                'res_model': 'hr.payslip.run',
                'view_mode': 'form',
                'res_id': batch.id,
            }
        elif payslips:
            return {
                'name': _('Payslips'),
                'type': 'ir.actions.act_window',
                'res_model': 'hr.payslip',
                'view_mode': 'list,form',
                'domain': [('id', 'in', payslips.ids)],
            }
        else:
            raise UserError(message)
