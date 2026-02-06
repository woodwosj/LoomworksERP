# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    gelato_api_key = fields.Char(string="Gelato API Key", groups="base.group_system")
    gelato_webhook_secret = fields.Char(string="Gelato Webhook Secret", groups="base.group_system")
