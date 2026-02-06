# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    last_lunch_location_id = fields.Many2one('lunch.location')
    favorite_lunch_product_ids = fields.Many2many('lunch.product', 'lunch_product_favorite_user_rel', 'user_id', 'product_id')
