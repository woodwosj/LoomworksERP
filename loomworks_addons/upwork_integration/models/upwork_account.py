# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Upwork Account model - Stores OAuth2 credentials and connection state.
"""

import logging

from loomworks import api, fields, models, _
from loomworks.exceptions import UserError

_logger = logging.getLogger(__name__)


class UpworkAccount(models.Model):
    """Upwork OAuth2 Account configuration."""
    _name = 'upwork.account'
    _description = 'Upwork Account'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(
        string='Account Name',
        required=True,
        tracking=True,
    )
    client_id = fields.Char(
        string='Client ID',
        required=True,
        groups='base.group_system',
    )
    client_secret = fields.Char(
        string='Client Secret',
        required=True,
        groups='base.group_system',
    )
    access_token = fields.Char(
        string='Access Token',
        groups='base.group_system',
        copy=False,
    )
    refresh_token = fields.Char(
        string='Refresh Token',
        groups='base.group_system',
        copy=False,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('connecting', 'Connecting'),
            ('connected', 'Connected'),
            ('error', 'Error'),
        ],
        string='State',
        default='draft',
        required=True,
        tracking=True,
        copy=False,
    )
    oauth_state = fields.Char(
        string='OAuth State',
        copy=False,
    )
    last_error = fields.Text(
        string='Last Error',
        copy=False,
    )
    is_connected = fields.Boolean(
        string='Connected',
        default=False,
        copy=False,
    )
    sync_enabled = fields.Boolean(
        string='Sync Enabled',
        default=True,
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )
    token_expiry = fields.Datetime(
        string='Token Expiry',
        copy=False,
    )
    last_sync = fields.Datetime(
        string='Last Sync',
        copy=False,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        (
            'upwork_account_name_company_uniq',
            'UNIQUE(name, company_id)',
            'Account name must be unique per company.',
        ),
    ]

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_authorize(self):
        """Initiate OAuth2 authorization flow with Upwork."""
        self.ensure_one()
        if not self.client_id or not self.client_secret:
            raise UserError(_("Please enter your Upwork Client ID and Client Secret first."))

        api_service = self.env['upwork.api.service']
        auth_url = api_service._get_authorization_url(self)

        return {
            'type': 'ir.actions.act_url',
            'url': auth_url,
            'target': 'self',
        }

    def action_test_connection(self):
        """Test the current Upwork API connection."""
        self.ensure_one()
        api_service = self.env['upwork.api.service']
        success = api_service._test_connection(self)

        if success:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Connection Successful"),
                    'message': _("Successfully connected to Upwork API."),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Connection Failed"),
                    'message': self.last_error or _("Unable to connect to Upwork API."),
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def action_disconnect(self):
        """Disconnect the Upwork account and clear tokens."""
        self.ensure_one()
        self.sudo().write({
            'access_token': False,
            'refresh_token': False,
            'token_expiry': False,
            'oauth_state': False,
            'state': 'draft',
            'is_connected': False,
            'last_error': False,
        })
        self.message_post(body=_("Disconnected from Upwork. OAuth tokens cleared."))
