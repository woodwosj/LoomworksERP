# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from . import models
from . import controllers

def _enable_group_uom_post_init(env):
    env['res.config.settings'].create({
        'group_uom': True,  # set units of measure to True by default in mx
    }).execute()
