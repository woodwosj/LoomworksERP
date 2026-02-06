# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import models, fields


class SaleReport(models.Model):
    _inherit = 'sale.report'

    project_id = fields.Many2one(comodel_name='project.project', readonly=True)

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res['project_id'] = 's.project_id'
        return res
