# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_add_mode = fields.Selection(related='product_template_id.product_add_mode', depends=['product_template_id'])
