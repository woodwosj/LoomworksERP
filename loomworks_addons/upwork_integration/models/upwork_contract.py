# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Upwork Contract model - Represents an Upwork contract (hourly or fixed price).
"""

import logging

from loomworks import api, fields, models, _

_logger = logging.getLogger(__name__)


class UpworkContract(models.Model):
    """Upwork Contract synced from the Upwork API."""
    _name = 'upwork.contract'
    _description = 'Upwork Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc, name'

    name = fields.Char(
        string='Contract Title',
        required=True,
        tracking=True,
    )
    upwork_contract_id = fields.Char(
        string='Upwork Contract ID',
        required=True,
        index=True,
    )
    contract_type = fields.Selection(
        selection=[
            ('hourly', 'Hourly'),
            ('fixed', 'Fixed Price'),
        ],
        string='Contract Type',
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ('active', 'Active'),
            ('paused', 'Paused'),
            ('ended', 'Ended'),
        ],
        string='Status',
        tracking=True,
    )
    start_date = fields.Date(
        string='Start Date',
    )
    end_date = fields.Date(
        string='End Date',
    )
    hourly_rate = fields.Monetary(
        string='Hourly Rate',
        currency_field='currency_id',
    )
    upwork_account_id = fields.Many2one(
        'upwork.account',
        string='Upwork Account',
        required=True,
        ondelete='cascade',
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Client',
        ondelete='set null',
    )
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        ondelete='set null',
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

    # One2many relations
    earning_ids = fields.One2many(
        'upwork.earning',
        'contract_id',
        string='Earnings',
    )
    timelog_ids = fields.One2many(
        'upwork.timelog',
        'contract_id',
        string='Time Logs',
    )
    milestone_ids = fields.One2many(
        'upwork.milestone',
        'contract_id',
        string='Milestones',
    )

    _sql_constraints = [
        (
            'upwork_contract_unique_contract_per_account',
            'UNIQUE(upwork_contract_id, upwork_account_id)',
            'Contract ID must be unique per Upwork account.',
        ),
    ]
