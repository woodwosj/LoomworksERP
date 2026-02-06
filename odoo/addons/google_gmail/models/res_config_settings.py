# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    google_gmail_client_identifier = fields.Char('Gmail Client Id', config_parameter='google_gmail_client_id')
    google_gmail_client_secret = fields.Char('Gmail Client Secret', config_parameter='google_gmail_client_secret')
