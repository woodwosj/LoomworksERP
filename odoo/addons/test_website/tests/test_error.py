import loomworks.tests
from loomworks.tools import mute_logger


@loomworks.tests.common.tagged('post_install', '-at_install')
class TestWebsiteError(loomworks.tests.HttpCase):

    @mute_logger('loomworks.addons.http_routing.models.ir_http', 'loomworks.http')
    def test_01_run_test(self):
        self.start_tour("/test_error_view", 'test_error_website')
