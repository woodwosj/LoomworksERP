# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.
from loomworks import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ------------------
    # Fields declaration
    # ------------------

    withholding_tax_base_account_id = fields.Many2one(
        related='company_id.withholding_tax_base_account_id',
        readonly=False,
    )
