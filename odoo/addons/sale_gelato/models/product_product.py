# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    gelato_product_uid = fields.Char(name="Gelato Product UID", readonly=True)
