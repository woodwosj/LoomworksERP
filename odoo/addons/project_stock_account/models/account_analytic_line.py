# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import fields, models


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    category = fields.Selection(selection_add=[('picking_entry', 'Inventory Transfer')])
