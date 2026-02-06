# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

import loomworks.tests
from loomworks.addons.gamification.tests.common import HttpCaseGamification


@loomworks.tests.tagged('post_install', '-at_install')
class TestWebsiteProfile(HttpCaseGamification):
    def test_save_change_description(self):
        loomworks.tests.new_test_user(
            self.env, 'test_user',
            karma=100, website_published=True
        )
        self.start_tour("/", 'website_profile_description', login="admin")
