# -*- coding:utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.
from loomworks import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    account_edi_proxy_client_ids = fields.One2many('account_edi_proxy_client.user', inverse_name='company_id', context={'active_test': True})
