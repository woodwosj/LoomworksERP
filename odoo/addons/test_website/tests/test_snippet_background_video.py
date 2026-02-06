# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

import loomworks.tests


@loomworks.tests.common.tagged('post_install', '-at_install')
class TestSnippetBackgroundVideo(loomworks.tests.HttpCase):

    def test_snippet_background_video(self):
        self.start_tour("/", "snippet_background_video", login="admin")
