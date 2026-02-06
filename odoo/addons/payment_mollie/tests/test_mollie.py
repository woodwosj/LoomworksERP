# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from loomworks.tests import tagged
from loomworks.tools import mute_logger

from loomworks.addons.payment.tests.http_common import PaymentHttpCommon
from loomworks.addons.payment_mollie.controllers.main import MollieController
from loomworks.addons.payment_mollie.tests.common import MollieCommon


@tagged('post_install', '-at_install')
class MollieTest(MollieCommon, PaymentHttpCommon):

    def test_payment_request_payload_values(self):
        tx = self._create_transaction(flow='redirect')

        payload = tx._mollie_prepare_payment_request_payload()

        self.assertDictEqual(payload['amount'], {'currency': 'EUR', 'value': '1111.11'})
        self.assertEqual(payload['description'], tx.reference)

    @mute_logger(
        'loomworks.addons.payment_mollie.controllers.main',
        'loomworks.addons.payment_mollie.models.payment_transaction',
    )
    def test_webhook_notification_confirms_transaction(self):
        """ Test the processing of a webhook notification. """
        tx = self._create_transaction('redirect')
        url = self._build_url(MollieController._webhook_url)
        with patch(
            'loomworks.addons.payment_mollie.models.payment_provider.PaymentProvider'
            '._mollie_make_request',
            return_value={'status': 'paid'},
        ):
            self._make_http_post_request(url, data=self.notification_data)
        self.assertEqual(tx.state, 'done')
