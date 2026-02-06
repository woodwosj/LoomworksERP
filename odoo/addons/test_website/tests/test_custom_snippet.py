# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

import loomworks.tests
from loomworks.tools import mute_logger


@loomworks.tests.common.tagged('post_install', '-at_install')
class TestCustomSnippet(loomworks.tests.HttpCase):

    @mute_logger('loomworks.addons.http_routing.models.ir_http', 'loomworks.http')
    def test_01_run_tour(self):
        self.start_tour(self.env['website'].get_client_action_url('/'), 'test_custom_snippet', login="admin")
