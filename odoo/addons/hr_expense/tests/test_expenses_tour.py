# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.
from loomworks.tests import tagged, HttpCase


@tagged('post_install', '-at_install')
class TestExpensesTour(HttpCase):
    def test_tour_expenses(self):
        self.start_tour("/loomworks", "hr_expense_test_tour", login="admin")
