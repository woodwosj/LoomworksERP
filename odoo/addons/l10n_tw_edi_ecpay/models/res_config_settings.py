# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_tw_edi_ecpay_staging_mode = fields.Boolean(related="company_id.l10n_tw_edi_ecpay_staging_mode", readonly=False)
    l10n_tw_edi_ecpay_merchant_id = fields.Char(related="company_id.l10n_tw_edi_ecpay_merchant_id", readonly=False)
    l10n_tw_edi_ecpay_hashkey = fields.Char(related="company_id.l10n_tw_edi_ecpay_hashkey", readonly=False)
    l10n_tw_edi_ecpay_hashIV = fields.Char(related="company_id.l10n_tw_edi_ecpay_hashIV", readonly=False)
