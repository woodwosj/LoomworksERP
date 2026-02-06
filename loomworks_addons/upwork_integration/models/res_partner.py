# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Extend res.partner with Upwork-specific fields.
"""

from loomworks import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    upwork_client_id = fields.Char(
        string='Upwork Client ID',
        help='Upwork user/company ID for this partner.',
    )
    upwork_contract_ids = fields.One2many(
        'upwork.contract',
        'partner_id',
        string='Upwork Contracts',
    )
    upwork_contract_count = fields.Integer(
        string='Upwork Contract Count',
        compute='_compute_upwork_contract_count',
        store=True,
    )

    @api.depends('upwork_contract_ids')
    def _compute_upwork_contract_count(self):
        for partner in self:
            partner.upwork_contract_count = len(partner.upwork_contract_ids)
