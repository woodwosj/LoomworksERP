# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from random import randint

from loomworks import fields, models


class MeetingType(models.Model):

    _name = 'calendar.event.type'
    _description = 'Event Meeting Type'

    def _default_color(self):
        return randint(1, 11)

    name = fields.Char('Name', required=True)
    color = fields.Integer('Color', default=_default_color)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists!"),
    ]
