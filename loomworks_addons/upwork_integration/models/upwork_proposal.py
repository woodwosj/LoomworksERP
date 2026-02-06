# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Upwork Proposal model - Manages proposals sent via Upwork.
"""

import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class UpworkProposal(models.Model):
    """Upwork Proposal with rich HTML content for professional presentations."""
    _name = 'upwork.proposal'
    _description = 'Upwork Proposal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'submitted_date desc, name'

    name = fields.Char(
        string='Proposal Name',
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('hired', 'Hired'),
            ('declined', 'Declined'),
        ],
        string='Status',
        default='draft',
        tracking=True,
    )
    title = fields.Char(
        string='Job Title',
    )
    module_list = fields.Char(
        string='Relevant Modules',
        help='Comma-separated list of Odoo modules relevant to this proposal.',
    )
    client_industry = fields.Char(
        string='Client Industry',
    )
    submitted_date = fields.Date(
        string='Submitted Date',
    )
    job_requirements = fields.Text(
        string='Job Requirements',
    )
    html_content = fields.Html(
        string='Proposal Content',
        sanitize=False,
    )
    hourly_rate = fields.Float(
        string='Hourly Rate',
    )
    estimated_hours = fields.Float(
        string='Estimated Hours',
    )
    upwork_account_id = fields.Many2one(
        'upwork.account',
        string='Upwork Account',
        required=True,
        ondelete='cascade',
    )
    contract_id = fields.Many2one(
        'upwork.contract',
        string='Contract',
        ondelete='set null',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
