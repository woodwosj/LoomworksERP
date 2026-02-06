# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    siret = fields.Char(string='SIRET', size=14)

    def _deduce_country_code(self):
        if self.siret:
            return 'FR'
        return super()._deduce_country_code()

    def _peppol_eas_endpoint_depends(self):
        # extends account_edi_ubl_cii
        return super()._peppol_eas_endpoint_depends() + ['siret']
