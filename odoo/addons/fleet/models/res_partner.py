# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    plan_to_change_car = fields.Boolean('Plan To Change Car', default=False, tracking=True)
    plan_to_change_bike = fields.Boolean('Plan To Change Bike', default=False)
