# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import models


class ResGroups(models.Model):
    _name = "res.groups"
    _inherit = ["res.groups", "bus.listener.mixin"]
