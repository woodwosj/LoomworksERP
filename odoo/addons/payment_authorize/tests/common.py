# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks.fields import Command

from loomworks.addons.payment.tests.common import PaymentCommon


class AuthorizeCommon(PaymentCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.authorize = cls._prepare_provider('authorize', update_values={
            'authorize_login': 'dummy',
            'authorize_transaction_key': 'dummy',
            'authorize_signature_key': '00000000',
            'available_currency_ids': [Command.set(cls.currency_usd.ids)]
        })

        cls.provider = cls.authorize
        cls.currency = cls.currency_usd
