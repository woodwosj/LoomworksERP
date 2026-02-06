# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    property_delivery_carrier_id = fields.Many2one('delivery.carrier', company_dependent=True, string="Delivery Method", help="Default delivery method used in sales orders.")
