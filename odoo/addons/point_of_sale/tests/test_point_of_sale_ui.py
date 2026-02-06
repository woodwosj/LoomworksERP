# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks.tests import HttpCase, tagged
from loomworks import tools


@tagged('post_install', '-at_install')
class TestUi(HttpCase):

	# Avoid "A Chart of Accounts is not yet installed in your current company."
	# Everything is set up correctly even without installed CoA
    @tools.mute_logger('loomworks.http')
    def test_01_point_of_sale_tour(self):

        self.start_tour("/loomworks", 'point_of_sale_tour', login="admin")
