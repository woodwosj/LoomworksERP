# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

import loomworks.tests

@loomworks.tests.tagged("post_install", "-at_install")
class TestOdooEditor(loomworks.tests.HttpCase):

    def test_odoo_editor_suite(self):
        self.browser_js('/web_editor/tests', "", "", login='admin', timeout=1800)
