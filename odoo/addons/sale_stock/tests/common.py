# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks.addons.sale.tests.common import TestSaleCommon


class TestSaleStockCommon(TestSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse_3_steps_pull = cls.env['stock.warehouse'].create({
            'name': 'Warehouse 3 steps',
            'code': '3S',
            'delivery_steps': 'pick_pack_ship',
        })
        delivery_route_3 = cls.warehouse_3_steps_pull.delivery_route_id
        delivery_route_3.rule_ids[0].write({
            'location_dest_id': delivery_route_3.rule_ids[1].location_src_id.id,
        })
        delivery_route_3.rule_ids[1].write({'action': 'pull'})
        delivery_route_3.rule_ids[2].write({'action': 'pull'})
