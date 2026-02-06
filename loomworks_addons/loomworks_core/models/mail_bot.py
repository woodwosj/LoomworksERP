# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

from markupsafe import Markup
from loomworks import models


class MailBotLoomworks(models.AbstractModel):
    """Override mail.bot to replace OdooBot references with LoomBot.

    This ensures all bot onboarding messages and help links reference
    Loomworks instead of Odoo.
    """
    _inherit = 'mail.bot'

    @staticmethod
    def _get_style_dict():
        """Override style dict to point documentation links to Loomworks."""
        return {
            "new_line": Markup("<br>"),
            "bold_start": Markup("<b>"),
            "bold_end": Markup("</b>"),
            "command_start": Markup("<span class='o_odoobot_command'>"),
            "command_end": Markup("</span>"),
            "document_link_start": Markup(
                "<a href='https://www.loomworks.solutions/documentation' target='_blank'>"
            ),
            "document_link_end": Markup("</a>"),
            "slides_link_start": Markup(
                "<a href='https://www.loomworks.solutions/resources' target='_blank'>"
            ),
            "slides_link_end": Markup("</a>"),
            "paperclip_icon": Markup(
                "<i class='fa fa-paperclip' aria-hidden='true'/>"
            ),
        }
