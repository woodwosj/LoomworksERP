# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import models, _
from loomworks.exceptions import UserError


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def button_unbuild(self):
        if self.subcontractor_id:
            raise UserError(_(
                "You can't unbuild a subcontracted Manufacturing Order.",
            ))
        return super().button_unbuild()
