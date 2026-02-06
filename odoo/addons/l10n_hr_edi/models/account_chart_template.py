# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.
from loomworks import models
from loomworks.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('hr', 'account.tax')
    def _get_hr_edi_account_tax(self):
        return self._parse_csv('hr', 'account.tax', module='l10n_hr_edi')
