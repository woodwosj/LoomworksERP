# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import fields, models


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    visibility = fields.Selection(
        selection=[('visible', "Visible"), ('hidden', "Hidden")],
        default='visible',
    )
