# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import models, fields


class View(models.Model):
    _inherit = "ir.ui.view"

    customize_show = fields.Boolean("Show As Optional Inherit", default=False)
