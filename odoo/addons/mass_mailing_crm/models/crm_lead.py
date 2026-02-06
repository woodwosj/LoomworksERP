# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import models


class CrmLead(models.Model):
    _inherit = 'crm.lead'
    _mailing_enabled = True
