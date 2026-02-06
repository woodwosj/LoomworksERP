# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Upwork OAuth2 callback controller.

Handles the redirect from Upwork after user authorizes the application.
Route: /upwork/oauth/callback
"""

import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class UpworkOAuthController(http.Controller):
    """Handle Upwork OAuth2 callback."""

    @http.route('/upwork/oauth/callback', type='http', auth='user', website=False)
    def upwork_oauth_callback(self, code=None, state=None, error=None, error_description=None, **kwargs):
        """Process the OAuth2 callback from Upwork.

        Args:
            code: Authorization code from Upwork
            state: CSRF state token
            error: Error code if authorization failed
            error_description: Human-readable error description

        Returns:
            Redirect to the Upwork account form or error page
        """
        # Handle authorization errors
        if error:
            _logger.warning("Upwork OAuth error: %s - %s", error, error_description)
            # Find the account by state to update its status
            if state:
                account = request.env['upwork.account'].sudo().search([
                    ('oauth_state', '=', state),
                ], limit=1)
                if account:
                    account.write({
                        'state': 'error',
                        'is_connected': False,
                        'last_error': error_description or error,
                        'oauth_state': False,
                    })
                    return request.redirect(f'/odoo/upwork-accounts/{account.id}')
            return request.redirect('/odoo/upwork-accounts')

        # Validate required parameters
        if not code or not state:
            _logger.error("Upwork OAuth callback missing code or state")
            return request.redirect('/odoo/upwork-accounts')

        # Find the account by state token (CSRF validation)
        account = request.env['upwork.account'].sudo().search([
            ('oauth_state', '=', state),
        ], limit=1)

        if not account:
            _logger.error("Upwork OAuth callback: no account found for state %s", state)
            return request.redirect('/odoo/upwork-accounts')

        # Exchange the code for tokens
        try:
            api_service = request.env['upwork.api.service']
            api_service._exchange_code_for_tokens(account, code)
            _logger.info("Upwork OAuth successful for account %s", account.name)
        except Exception as e:
            _logger.error("Upwork OAuth token exchange failed: %s", e)
            account.sudo().write({
                'state': 'error',
                'is_connected': False,
                'last_error': str(e),
                'oauth_state': False,
            })

        return request.redirect(f'/odoo/upwork-accounts/{account.id}')
