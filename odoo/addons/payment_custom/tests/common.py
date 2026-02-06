# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks.osv.expression import OR

from loomworks.addons.payment.tests.common import PaymentCommon


class PaymentCustomCommon(PaymentCommon):

    @classmethod
    def _get_provider_domain(cls, code):
        domain = super()._get_provider_domain(code)
        return OR([domain, [('custom_mode', '=', code)]])
