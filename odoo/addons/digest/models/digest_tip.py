# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.
from loomworks import fields, models
from loomworks.tools.translate import html_translate


class DigestTip(models.Model):
    _name = 'digest.tip'
    _description = 'Digest Tips'
    _order = 'sequence'

    sequence = fields.Integer(
        'Sequence', default=1,
        help='Used to display digest tip in email template base on order')
    name = fields.Char('Name', translate=True)
    user_ids = fields.Many2many(
        'res.users', string='Recipients',
        help='Users having already received this tip')
    tip_description = fields.Html('Tip description', translate=html_translate, sanitize=False)
    group_id = fields.Many2one(
        'res.groups', string='Authorized Group',
        default=lambda self: self.env.ref('base.group_user'))
