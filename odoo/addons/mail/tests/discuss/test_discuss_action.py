# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.
from loomworks.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestDiscussAction(HttpCase):
    def test_go_back_to_thread_from_breadcrumbs(self):
        self.start_tour(
            "/loomworks/discuss?active_id=mail.box_inbox",
            "discuss_go_back_to_thread_from_breadcrumbs.js",
            login="admin",
        )
