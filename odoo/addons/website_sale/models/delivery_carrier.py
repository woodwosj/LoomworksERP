# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import fields, models


class DeliveryCarrier(models.Model):
    _name = 'delivery.carrier'
    _inherit = ['delivery.carrier', 'website.published.multi.mixin']

    website_description = fields.Text(
        string="Description for Online Quotations",
        related='product_id.description_sale',
        readonly=False,
    )
