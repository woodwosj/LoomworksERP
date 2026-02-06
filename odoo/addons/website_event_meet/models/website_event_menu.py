# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import fields, models


class EventMenu(models.Model):
    _inherit = "website.event.menu"

    menu_type = fields.Selection(
        selection_add=[("meeting_room", "Event Meeting Room Menus")],
        ondelete={'meeting_room': 'cascade'})
