# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import fields, models


class WebsiteTrack(models.Model):
    _inherit = 'website.track'

    product_id = fields.Many2one(
        comodel_name='product.product', ondelete='cascade', readonly=True, index='btree_not_null',
    )
