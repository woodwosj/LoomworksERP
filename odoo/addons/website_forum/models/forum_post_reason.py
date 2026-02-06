# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import fields, models


class PostReason(models.Model):
    _name = "forum.post.reason"
    _description = "Post Closing Reason"
    _order = 'name'

    name = fields.Char(string='Closing Reason', required=True, translate=True)
    reason_type = fields.Selection([('basic', 'Basic'), ('offensive', 'Offensive')], string='Reason Type', default='basic')
