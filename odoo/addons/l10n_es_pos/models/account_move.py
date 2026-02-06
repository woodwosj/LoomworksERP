# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.
from loomworks import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _compute_l10n_es_is_simplified(self):
        super()._compute_l10n_es_is_simplified()
        for move in self:
            if move.pos_order_ids:
                move.l10n_es_is_simplified = move.pos_order_ids[0].is_l10n_es_simplified_invoice
