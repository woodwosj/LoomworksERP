# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from . import models
from . import report


def uninstall_hook(env):
    # Uninstalling the module will archive the dropshipping picking type.
    env['stock.picking.type'].search([('code', '=', 'dropship')]).active = False
