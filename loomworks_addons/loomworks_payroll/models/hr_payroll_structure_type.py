# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from loomworks import fields, models


class HrPayrollStructureType(models.Model):
    """Extension of hr.payroll.structure.type for payroll integration."""
    _inherit = 'hr.payroll.structure.type'

    wage_type = fields.Selection([
        ('monthly', 'Monthly Fixed Wage'),
        ('hourly', 'Hourly Wage'),
    ], default='monthly', required=True, string='Wage Type',
        help="Determines how wages are computed - fixed monthly or based on hours worked")
    default_struct_id = fields.Many2one(
        'hr.payroll.structure',
        string='Default Structure',
        help="Default payroll structure for contracts of this type")
