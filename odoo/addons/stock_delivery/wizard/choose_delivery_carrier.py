# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import _, api, models


class ChooseDeliveryCarrier(models.TransientModel):
    _inherit = 'choose.delivery.carrier'

    @api.depends('carrier_id')
    def _compute_invoicing_message(self):
        super()._compute_invoicing_message()
        if self.carrier_id.invoice_policy == 'real':
            self.invoicing_message = _('The shipping price will be set once the delivery is done.')
