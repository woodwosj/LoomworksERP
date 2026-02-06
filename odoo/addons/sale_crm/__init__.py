# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard

def uninstall_hook(env):
    teams = env['crm.team'].search([('use_opportunities', '=', False)])
    teams.write({'use_opportunities': True})