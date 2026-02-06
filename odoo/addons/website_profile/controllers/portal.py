# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks.addons.portal.controllers import portal
from loomworks.http import request


class CustomerPortal(portal.CustomerPortal):

    def on_account_update(self, values, partner):
        super().on_account_update(values, partner)
        # Do not show "Validation Email sent" if the current user changed their email address
        if values["email"] != partner.email:
            request.session['validation_email_sent'] = False
