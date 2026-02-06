# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Upwork Milestone model - Represents milestones on fixed-price contracts.
"""

from loomworks import api, fields, models


class UpworkMilestone(models.Model):
    """Upwork Contract Milestone."""
    _name = 'upwork.milestone'
    _description = 'Upwork Milestone'
    _order = 'due_date, name'

    name = fields.Char(
        string='Milestone',
        required=True,
    )
    state = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('active', 'Active'),
            ('completed', 'Completed'),
            ('paid', 'Paid'),
        ],
        string='Status',
    )
    due_date = fields.Date(
        string='Due Date',
    )
    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
    )
    contract_id = fields.Many2one(
        'upwork.contract',
        string='Contract',
        required=True,
        ondelete='cascade',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
