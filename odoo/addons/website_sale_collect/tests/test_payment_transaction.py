# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks.tests import HttpCase, tagged
from loomworks.tools import mute_logger

from loomworks.addons.website_sale_collect.tests.common import ClickAndCollectCommon


@tagged('post_install', '-at_install')
class TestOnSitePaymentTransaction(HttpCase, ClickAndCollectCommon):

    def test_choosing_on_site_payment_confirms_order(self):
        order = self._create_so(carrier_id=self.carrier.id, state='draft')
        tx = self._create_transaction(
            flow='direct',
            sale_order_ids=[order.id],
            state='pending',
            payment_method_id=self.provider.payment_method_ids.id,
        )
        with mute_logger('loomworks.addons.sale.models.payment_transaction'):
            tx._post_process()

        self.assertEqual(order.state, 'sale')
