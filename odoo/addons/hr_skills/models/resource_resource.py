# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.
from loomworks import fields, models


class Resource(models.Model):
    _inherit = ['resource.resource']

    employee_skill_ids = fields.One2many(related='employee_id.employee_skill_ids')
