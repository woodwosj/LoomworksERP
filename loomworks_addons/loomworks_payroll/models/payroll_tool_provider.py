# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

"""
Payroll AI Tool Provider - Registers AI tools for payroll operations.

Implements the M4 resolution pattern from PATCH_NOTES_M1_M4.md.
"""

from loomworks import api, models
import json


class PayrollToolProvider(models.AbstractModel):
    """
    AI Tool Provider for Payroll module.

    Provides tools for:
    - Generating payslips
    - Computing salary previews
    - Managing payroll batches
    """
    _name = 'payroll.tool.provider'
    _inherit = 'loomworks.ai.tool.provider'
    _description = 'Payroll AI Tool Provider'

    @api.model
    def _get_tool_definitions(self):
        return [
            {
                'name': 'Generate Payslip',
                'technical_name': 'payroll_generate_payslip',
                'category': 'action',
                'description': (
                    "Generate a payslip for an employee for a specific pay period. "
                    "The payslip will be computed using the employee's contract and "
                    "salary structure. Use this to create payslips individually."
                ),
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'employee_id': {
                            'type': 'integer',
                            'description': 'The ID of the employee to generate payslip for'
                        },
                        'date_from': {
                            'type': 'string',
                            'format': 'date',
                            'description': 'Start date of the pay period (YYYY-MM-DD)'
                        },
                        'date_to': {
                            'type': 'string',
                            'format': 'date',
                            'description': 'End date of the pay period (YYYY-MM-DD)'
                        },
                        'compute': {
                            'type': 'boolean',
                            'description': 'Whether to compute the payslip immediately (default: true)',
                            'default': True
                        }
                    },
                    'required': ['employee_id', 'date_from', 'date_to']
                },
                'implementation_method': 'payroll.tool.provider._execute_generate_payslip',
                'risk_level': 'moderate',
                'requires_confirmation': True,
                'returns_description': 'Generated payslip details including gross, net, and deductions',
            },
            {
                'name': 'Compute Salary Preview',
                'technical_name': 'payroll_compute_salary',
                'category': 'data',
                'description': (
                    "Preview salary computation for an employee without creating a payslip. "
                    "Returns a breakdown of earnings, deductions, and net pay based on the "
                    "employee's contract and salary structure."
                ),
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'employee_id': {
                            'type': 'integer',
                            'description': 'The ID of the employee'
                        },
                        'date_from': {
                            'type': 'string',
                            'format': 'date',
                            'description': 'Start date of the period (YYYY-MM-DD)'
                        },
                        'date_to': {
                            'type': 'string',
                            'format': 'date',
                            'description': 'End date of the period (YYYY-MM-DD)'
                        }
                    },
                    'required': ['employee_id']
                },
                'implementation_method': 'payroll.tool.provider._execute_compute_salary',
                'risk_level': 'safe',
                'returns_description': 'Salary breakdown with earnings and deductions',
            },
            {
                'name': 'Create Payroll Batch',
                'technical_name': 'payroll_create_batch',
                'category': 'action',
                'description': (
                    "Create a payroll batch to process multiple employees at once. "
                    "Can optionally filter by department. Use this for bulk payroll processing."
                ),
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'name': {
                            'type': 'string',
                            'description': 'Name for the payroll batch'
                        },
                        'date_from': {
                            'type': 'string',
                            'format': 'date',
                            'description': 'Start date of the pay period'
                        },
                        'date_to': {
                            'type': 'string',
                            'format': 'date',
                            'description': 'End date of the pay period'
                        },
                        'department_id': {
                            'type': 'integer',
                            'description': 'Optional department to filter employees'
                        }
                    },
                    'required': ['date_from', 'date_to']
                },
                'implementation_method': 'payroll.tool.provider._execute_create_batch',
                'risk_level': 'moderate',
                'requires_confirmation': True,
                'returns_description': 'Created batch with list of included employees',
            },
        ]

    @api.model
    def _execute_generate_payslip(self, employee_id, date_from, date_to, compute=True):
        """Execute the payroll_generate_payslip tool."""
        employee = self.env['hr.employee'].browse(employee_id)
        if not employee.exists():
            return {'error': f'Employee with ID {employee_id} not found'}

        # Create payslip
        payslip = self.env['hr.payslip'].create({
            'employee_id': employee_id,
            'date_from': date_from,
            'date_to': date_to,
        })

        # Compute if requested
        if compute:
            payslip.compute_sheet()

        # Build result
        result = {
            'success': True,
            'payslip_id': payslip.id,
            'employee': employee.name,
            'period': f"{date_from} to {date_to}",
            'state': payslip.state,
        }

        if compute:
            result.update({
                'gross_wage': payslip.gross_wage,
                'total_deductions': payslip.total_deductions,
                'net_wage': payslip.net_wage,
                'line_count': len(payslip.line_ids),
            })

        return result

    @api.model
    def _execute_compute_salary(self, employee_id, date_from=None, date_to=None):
        """Execute the payroll_compute_salary tool (preview only)."""
        from datetime import date as dt_date
        from dateutil.relativedelta import relativedelta

        employee = self.env['hr.employee'].browse(employee_id)
        if not employee.exists():
            return {'error': f'Employee with ID {employee_id} not found'}

        # Default to current month
        if not date_from:
            date_from = dt_date.today().replace(day=1)
        if not date_to:
            date_to = (dt_date.today().replace(day=1) + relativedelta(months=1)) - relativedelta(days=1)

        # Find contract
        contract = self.env['hr.contract'].search([
            ('employee_id', '=', employee_id),
            ('state', 'in', ['open', 'close']),
            ('date_start', '<=', date_to),
            '|',
            ('date_end', '=', False),
            ('date_end', '>=', date_from),
        ], limit=1)

        if not contract:
            return {'error': f'No active contract found for {employee.name}'}

        # Get structure
        struct = self.env['hr.payroll.structure'].search([
            ('type_id', '=', contract.structure_type_id.id),
            ('company_id', '=', contract.company_id.id),
        ], limit=1)

        if not struct:
            return {'error': 'No salary structure found'}

        # Build preview
        result = {
            'employee': employee.name,
            'contract': contract.name,
            'structure': struct.name,
            'period': f"{date_from} to {date_to}",
            'wage_type': contract.structure_type_id.wage_type,
            'base_wage': contract.wage if contract.structure_type_id.wage_type == 'monthly' else contract.hourly_wage,
            'filing_status': contract.filing_status,
            'note': 'This is a preview. Actual amounts may vary based on worked hours and inputs.',
        }

        return result

    @api.model
    def _execute_create_batch(self, date_from, date_to, name=None, department_id=None):
        """Execute the payroll_create_batch tool."""
        from datetime import date as dt_date

        if not name:
            # Parse date_from to get month name
            from_date = dt_date.fromisoformat(date_from) if isinstance(date_from, str) else date_from
            name = f"Payroll Batch - {from_date.strftime('%B %Y')}"

        # Create batch
        batch = self.env['hr.payslip.run'].create({
            'name': name,
            'date_start': date_from,
            'date_end': date_to,
            'department_id': department_id,
        })

        # Find eligible employees
        domain = [('company_id', '=', batch.company_id.id)]
        if department_id:
            domain.append(('department_id', '=', department_id))

        employees = self.env['hr.employee'].search(domain)

        # Create payslips
        payslips_created = 0
        for employee in employees:
            # Check for contract
            contract = self.env['hr.contract'].search([
                ('employee_id', '=', employee.id),
                ('state', 'in', ['open', 'close']),
            ], limit=1)
            if not contract:
                continue

            self.env['hr.payslip'].create({
                'employee_id': employee.id,
                'date_from': date_from,
                'date_to': date_to,
                'payslip_run_id': batch.id,
            })
            payslips_created += 1

        return {
            'success': True,
            'batch_id': batch.id,
            'batch_name': batch.name,
            'employees_count': payslips_created,
            'period': f"{date_from} to {date_to}",
        }
