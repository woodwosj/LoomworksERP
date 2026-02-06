from loomworks.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization
from loomworks.tests import tagged
from loomworks.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericCH(TestGenericLocalization):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('ch')
    def setUpClass(cls):
        super().setUpClass()
