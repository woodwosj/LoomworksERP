# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.


from loomworks import fields, models


class EtaActivityType(models.Model):
    _name = 'l10n_eg_edi.activity.type'
    _description = 'ETA code for activity type'
    _rec_name = 'name'
    _rec_names_search = ['name', 'code']

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
