# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.
from loomworks import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    # ------------------
    # Fields declaration
    # ------------------

    l10n_my_tax_exemption_reason = fields.Char(
        string="Malaysian Tax Exemption Reason",
        help="The reason for tax exemption, used when submitting consolidated invoices including this tax.",
    )
