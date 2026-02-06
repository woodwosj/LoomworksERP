# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import models
from loomworks.osv.expression import AND


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_valid_moves_domain(self):
        domain = super()._get_valid_moves_domain()
        # If anglo-saxon accounting enabled: we do not generate AALs for the reinvoiced products
        if self.env.user.company_id.anglo_saxon_accounting:
            domain = AND([domain, [('product_id.expense_policy', 'not in', ('sales_price', 'cost'))]])
        return domain
