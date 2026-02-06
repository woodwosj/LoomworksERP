# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.
from loomworks import fields, models


class ResBank(models.Model):
    _name = 'res.bank'
    _inherit = 'res.bank'

    def _get_fiscal_country_codes(self):
        return ','.join(self.env.companies.mapped('account_fiscal_country_id.code'))

    l10n_cl_sbif_code = fields.Char('Cod. SBIF', size=10)
    fiscal_country_codes = fields.Char(store=False, default=_get_fiscal_country_codes)
