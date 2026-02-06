# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    project_id = fields.Many2one('project.project')
