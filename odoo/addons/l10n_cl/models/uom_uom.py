# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import fields, models, api, _


class UomUom(models.Model):
    _inherit = 'uom.uom'

    l10n_cl_sii_code = fields.Char('SII Code')
