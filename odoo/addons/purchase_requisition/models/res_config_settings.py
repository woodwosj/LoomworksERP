# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_purchase_alternatives = fields.Boolean("Purchase Alternatives", implied_group='purchase_requisition.group_purchase_alternatives')
