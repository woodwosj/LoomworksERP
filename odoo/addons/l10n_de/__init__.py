# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from . import models


def _post_init_hook(env):
    env['res.groups']._activate_group_account_secured()
