# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import fields, models


class ResourceResource(models.Model):
    _inherit = 'resource.resource'

    im_status = fields.Char(related='user_id.im_status')

    def get_avatar_card_data(self, fields):
        return self._read_format(fields)
