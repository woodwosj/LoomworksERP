# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.
from loomworks import fields, models


class Uom(models.Model):

    _inherit = 'uom.uom'

    l10n_ar_afip_code = fields.Char('Code', help='Argentina: This code will be used on electronic invoice.')
