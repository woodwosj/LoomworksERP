# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.
from loomworks import models
from loomworks.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('mc')
    def _get_mc_template_data(self):
        return {
            'code_digits': '6',
            'parent': 'fr',
        }

    def _deref_account_tags(self, template_code, tax_data):
        if template_code == 'mc':
            template_code = 'fr'
        return super()._deref_account_tags(template_code, tax_data)
