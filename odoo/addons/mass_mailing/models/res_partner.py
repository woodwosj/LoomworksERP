# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import models


class Partner(models.Model):
    _inherit = 'res.partner'
    _mailing_enabled = True
