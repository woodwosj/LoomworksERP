# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import _, fields, models


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    adyen_shopper_reference = fields.Char(
        string="Shopper Reference", help="The unique reference of the partner owning this token",
        readonly=True)
