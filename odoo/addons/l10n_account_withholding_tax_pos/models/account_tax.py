# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.
from loomworks import api, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields = super()._load_pos_data_fields(config_id)
        # Adding the field in the data so that it is available in batch_for_taxes_computation
        fields.append('is_withholding_tax_on_payment')
        return fields
