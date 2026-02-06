# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import fields, models


class FleetVehicleOdometer(models.Model):
    _inherit = 'fleet.vehicle.odometer'

    driver_employee_id = fields.Many2one(
        related='vehicle_id.driver_employee_id', string='Driver (Employee)',
        readonly=True,
    )
