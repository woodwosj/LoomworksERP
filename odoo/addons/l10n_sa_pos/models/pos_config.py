# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.
from loomworks import models
from loomworks.exceptions import UserError
from loomworks.tools.translate import _


class pos_config(models.Model):
    _inherit = 'pos.config'

    def open_ui(self):
        for config in self:
            if not config.company_id.country_id:
                raise UserError(_("You have to set a country in your company setting."))
        return super(pos_config, self).open_ui()
