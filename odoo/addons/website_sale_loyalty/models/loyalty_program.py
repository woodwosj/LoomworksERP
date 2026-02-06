# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import fields, models

class LoyaltyProgram(models.Model):
    _name = 'loyalty.program'
    _inherit = ['loyalty.program', 'website.multi.mixin']

    ecommerce_ok = fields.Boolean("Available on Website", default=True)

    def action_program_share(self):
        self.ensure_one()
        return self.env['coupon.share'].create_share_action(program=self)
