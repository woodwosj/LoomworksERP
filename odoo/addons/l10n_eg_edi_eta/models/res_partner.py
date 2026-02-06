# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.


from loomworks import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_eg_building_no = fields.Char('Building No.')

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ['l10n_eg_building_no']

    def _address_fields(self):
        return super()._address_fields() + ['l10n_eg_building_no']
