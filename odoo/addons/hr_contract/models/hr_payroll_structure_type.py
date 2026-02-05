# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
#
# Extended for Loomworks Payroll Integration (Phase 3.3)

from odoo import fields, models


class HrPayrollStructureType(models.Model):
    _name = 'hr.payroll.structure.type'
    _description = 'Salary Structure Type'

    name = fields.Char('Salary Structure Type', required=True)
    default_resource_calendar_id = fields.Many2one(
        'resource.calendar', 'Default Working Hours',
        default=lambda self: self.env.company.resource_calendar_id)
    country_id = fields.Many2one('res.country', string='Country', default=lambda self: self.env.company.country_id)
    country_code = fields.Char(related="country_id.code")

    # Loomworks Payroll Extensions
    wage_type = fields.Selection([
        ('monthly', 'Monthly Fixed Wage'),
        ('hourly', 'Hourly Wage'),
    ], default='monthly', required=True, string='Wage Type',
        help="Determines how wages are computed - fixed monthly or based on hours worked")
    default_struct_id = fields.Many2one(
        'hr.payroll.structure',
        string='Default Structure',
        help="Default payroll structure for contracts of this type. "
             "Requires loomworks_payroll module to be installed."
    )
