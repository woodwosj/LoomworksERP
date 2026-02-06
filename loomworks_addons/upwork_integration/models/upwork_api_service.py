# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Upwork API Service - AbstractModel providing API interaction methods.

All cron jobs and API calls are routed through this service. Uses the
requests library for HTTP calls to the Upwork GraphQL API.
"""

import json
import logging
import time
from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

try:
    import requests
except ImportError:
    requests = None

_logger = logging.getLogger(__name__)

UPWORK_AUTH_URL = 'https://www.upwork.com/ab/account-security/oauth2/authorize'
UPWORK_TOKEN_URL = 'https://www.upwork.com/api/v3/oauth2/token'
UPWORK_GRAPHQL_URL = 'https://www.upwork.com/api/graphql'


class UpworkApiService(models.AbstractModel):
    """Abstract service for Upwork API interactions."""
    _name = 'upwork.api.service'
    _description = 'Upwork API Service'

    # ------------------------------------------------------------------
    # OAuth2 helpers
    # ------------------------------------------------------------------

    @api.model
    def _get_oauth_redirect_uri(self):
        """Return the OAuth2 callback URL for the current Odoo instance."""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f'{base_url}/upwork/oauth/callback'

    @api.model
    def _get_authorization_url(self, account):
        """Build the Upwork OAuth2 authorization URL.

        Args:
            account: upwork.account record

        Returns:
            str: Full authorization URL with parameters
        """
        import hashlib
        import os
        state = hashlib.sha256(os.urandom(32)).hexdigest()
        account.sudo().write({'oauth_state': state, 'state': 'connecting'})

        params = {
            'response_type': 'code',
            'client_id': account.client_id,
            'redirect_uri': self._get_oauth_redirect_uri(),
            'state': state,
        }
        query_string = '&'.join(f'{k}={requests.utils.quote(str(v))}' for k, v in params.items())
        return f'{UPWORK_AUTH_URL}?{query_string}'

    @api.model
    def _exchange_code_for_tokens(self, account, code):
        """Exchange an authorization code for access/refresh tokens.

        Args:
            account: upwork.account record
            code: Authorization code from OAuth callback

        Returns:
            dict: Token response data
        """
        if not requests:
            raise UserError(_("Python 'requests' library is required for Upwork integration."))

        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self._get_oauth_redirect_uri(),
            'client_id': account.client_id,
            'client_secret': account.client_secret,
        }

        try:
            response = requests.post(UPWORK_TOKEN_URL, data=data, timeout=30)
            response.raise_for_status()
            token_data = response.json()

            expiry = fields.Datetime.now() + timedelta(seconds=token_data.get('expires_in', 3600))
            account.sudo().write({
                'access_token': token_data.get('access_token'),
                'refresh_token': token_data.get('refresh_token'),
                'token_expiry': expiry,
                'state': 'connected',
                'is_connected': True,
                'last_error': False,
                'oauth_state': False,
            })
            account.message_post(body=_("Successfully connected to Upwork."))
            return token_data

        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            account.sudo().write({
                'state': 'error',
                'is_connected': False,
                'last_error': error_msg,
                'oauth_state': False,
            })
            _logger.error("Upwork token exchange failed for account %s: %s", account.name, error_msg)
            raise UserError(_("Failed to connect to Upwork: %s", error_msg))

    @api.model
    def _refresh_access_token(self, account):
        """Refresh an expired access token using the refresh token.

        Args:
            account: upwork.account record

        Returns:
            str: New access token
        """
        if not requests:
            raise UserError(_("Python 'requests' library is required for Upwork integration."))

        if not account.refresh_token:
            account.sudo().write({
                'state': 'error',
                'is_connected': False,
                'last_error': 'No refresh token available. Please reconnect.',
            })
            return False

        data = {
            'grant_type': 'refresh_token',
            'refresh_token': account.refresh_token,
            'client_id': account.client_id,
            'client_secret': account.client_secret,
        }

        try:
            response = requests.post(UPWORK_TOKEN_URL, data=data, timeout=30)
            response.raise_for_status()
            token_data = response.json()

            expiry = fields.Datetime.now() + timedelta(seconds=token_data.get('expires_in', 3600))
            account.sudo().write({
                'access_token': token_data.get('access_token'),
                'refresh_token': token_data.get('refresh_token', account.refresh_token),
                'token_expiry': expiry,
                'state': 'connected',
                'is_connected': True,
                'last_error': False,
            })
            return token_data.get('access_token')

        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            account.sudo().write({
                'state': 'error',
                'is_connected': False,
                'last_error': f'Token refresh failed: {error_msg}',
            })
            _logger.error("Upwork token refresh failed for account %s: %s", account.name, error_msg)
            return False

    @api.model
    def _ensure_valid_token(self, account):
        """Ensure the account has a valid (non-expired) access token.

        Args:
            account: upwork.account record

        Returns:
            str: Valid access token or False
        """
        if not account.access_token:
            return False

        if account.token_expiry and account.token_expiry <= fields.Datetime.now():
            return self._refresh_access_token(account)

        return account.access_token

    # ------------------------------------------------------------------
    # GraphQL API calls
    # ------------------------------------------------------------------

    @api.model
    def _graphql_query(self, account, query, variables=None):
        """Execute a GraphQL query against the Upwork API.

        Args:
            account: upwork.account record
            query: GraphQL query string
            variables: Optional dict of query variables

        Returns:
            dict: JSON response data
        """
        if not requests:
            raise UserError(_("Python 'requests' library is required for Upwork integration."))

        token = self._ensure_valid_token(account)
        if not token:
            raise UserError(_("No valid Upwork access token. Please reconnect the account."))

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }

        payload = {'query': query}
        if variables:
            payload['variables'] = variables

        try:
            response = requests.post(
                UPWORK_GRAPHQL_URL,
                headers=headers,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            result = response.json()

            if 'errors' in result:
                error_msgs = '; '.join(e.get('message', '') for e in result['errors'])
                _logger.warning("Upwork GraphQL errors for %s: %s", account.name, error_msgs)

            return result

        except requests.exceptions.RequestException as e:
            _logger.error("Upwork GraphQL request failed for %s: %s", account.name, e)
            raise UserError(_("Upwork API request failed: %s", str(e)))

    @api.model
    def _test_connection(self, account):
        """Test the Upwork API connection for an account.

        Args:
            account: upwork.account record

        Returns:
            bool: True if connection is working
        """
        query = '{ user { id npiCompany { id } } }'
        try:
            result = self._graphql_query(account, query)
            if result and 'data' in result:
                account.sudo().write({
                    'state': 'connected',
                    'is_connected': True,
                    'last_error': False,
                })
                return True
        except Exception as e:
            account.sudo().write({
                'state': 'error',
                'is_connected': False,
                'last_error': str(e),
            })
        return False

    # ------------------------------------------------------------------
    # Sync methods (called by cron jobs)
    # ------------------------------------------------------------------

    @api.model
    def _get_active_accounts(self):
        """Return all active, connected accounts with sync enabled."""
        return self.env['upwork.account'].sudo().search([
            ('state', '=', 'connected'),
            ('sync_enabled', '=', True),
            ('active', '=', True),
        ])

    @api.model
    def _sync_contracts_for_account(self, account):
        """Sync contracts from Upwork for a specific account.

        Args:
            account: upwork.account record
        """
        query = """
        {
            contracts {
                edges {
                    node {
                        id
                        title
                        contractType
                        status
                        startDate
                        endDate
                        hourlyRate {
                            amount
                            currencyCode
                        }
                        client {
                            id
                            name
                        }
                    }
                }
            }
        }
        """
        try:
            result = self._graphql_query(account, query)
            data = result.get('data', {})
            contracts_data = data.get('contracts', {}).get('edges', [])

            Contract = self.env['upwork.contract'].sudo()
            for edge in contracts_data:
                node = edge.get('node', {})
                contract_id = node.get('id')
                if not contract_id:
                    continue

                # Find or create partner from client data
                partner_id = False
                client_data = node.get('client', {})
                if client_data and client_data.get('name'):
                    partner = self.env['res.partner'].sudo().search([
                        ('name', '=', client_data['name'])
                    ], limit=1)
                    if not partner:
                        partner = self.env['res.partner'].sudo().create({
                            'name': client_data['name'],
                            'upwork_client_id': client_data.get('id', ''),
                        })
                    partner_id = partner.id

                # Map contract type
                contract_type = 'hourly'
                if node.get('contractType', '').lower() == 'fixed':
                    contract_type = 'fixed'

                # Map state
                status_map = {
                    'active': 'active',
                    'paused': 'paused',
                    'ended': 'ended',
                    'closed': 'ended',
                }
                state = status_map.get(node.get('status', '').lower(), 'active')

                # Hourly rate
                hourly_rate = 0.0
                rate_data = node.get('hourlyRate', {})
                if rate_data:
                    hourly_rate = float(rate_data.get('amount', 0))

                vals = {
                    'name': node.get('title', contract_id),
                    'upwork_contract_id': contract_id,
                    'upwork_account_id': account.id,
                    'contract_type': contract_type,
                    'state': state,
                    'hourly_rate': hourly_rate,
                    'company_id': account.company_id.id,
                }

                if partner_id:
                    vals['partner_id'] = partner_id

                start_date = node.get('startDate')
                if start_date:
                    vals['start_date'] = start_date[:10]

                end_date = node.get('endDate')
                if end_date:
                    vals['end_date'] = end_date[:10]

                existing = Contract.search([
                    ('upwork_contract_id', '=', contract_id),
                    ('upwork_account_id', '=', account.id),
                ], limit=1)

                if existing:
                    existing.write(vals)
                else:
                    Contract.create(vals)

            account.sudo().write({'last_sync': fields.Datetime.now()})
            _logger.info("Synced contracts for Upwork account %s", account.name)

        except Exception as e:
            _logger.error("Failed to sync contracts for Upwork account %s: %s", account.name, e)
            account.sudo().write({
                'last_error': f'Contract sync failed: {e}',
            })

    @api.model
    def _sync_timelogs_for_account(self, account):
        """Sync time logs from Upwork for a specific account.

        Args:
            account: upwork.account record
        """
        contracts = self.env['upwork.contract'].sudo().search([
            ('upwork_account_id', '=', account.id),
            ('state', '=', 'active'),
        ])

        for contract in contracts:
            query = """
            query ($contractId: ID!) {
                timeLogs(contractId: $contractId) {
                    edges {
                        node {
                            id
                            date
                            trackedHours
                            manualHours
                            totalHours
                            memo
                        }
                    }
                }
            }
            """
            try:
                result = self._graphql_query(
                    account, query,
                    variables={'contractId': contract.upwork_contract_id}
                )
                data = result.get('data', {})
                timelogs_data = data.get('timeLogs', {}).get('edges', [])

                Timelog = self.env['upwork.timelog'].sudo()
                for edge in timelogs_data:
                    node = edge.get('node', {})
                    timelog_id = node.get('id')
                    date_str = node.get('date')
                    if not date_str:
                        continue

                    vals = {
                        'contract_id': contract.id,
                        'upwork_account_id': account.id,
                        'upwork_timelog_id': timelog_id,
                        'date': date_str[:10],
                        'tracked_hours': float(node.get('trackedHours', 0)),
                        'manual_hours': float(node.get('manualHours', 0)),
                        'total_hours': float(node.get('totalHours', 0)),
                        'memo': node.get('memo', ''),
                        'company_id': account.company_id.id,
                    }

                    existing = Timelog.search([
                        ('upwork_timelog_id', '=', timelog_id),
                        ('contract_id', '=', contract.id),
                    ], limit=1)

                    if existing:
                        existing.write(vals)
                    elif timelog_id:
                        # Also check by contract+date to avoid unique constraint
                        existing_by_date = Timelog.search([
                            ('contract_id', '=', contract.id),
                            ('date', '=', date_str[:10]),
                        ], limit=1)
                        if existing_by_date:
                            existing_by_date.write(vals)
                        else:
                            Timelog.create(vals)

            except Exception as e:
                _logger.error(
                    "Failed to sync timelogs for contract %s: %s",
                    contract.upwork_contract_id, e
                )

        account.sudo().write({'last_sync': fields.Datetime.now()})
        _logger.info("Synced time logs for Upwork account %s", account.name)

    @api.model
    def _sync_earnings_for_account(self, account):
        """Sync earnings from Upwork for a specific account.

        Args:
            account: upwork.account record
        """
        contracts = self.env['upwork.contract'].sudo().search([
            ('upwork_account_id', '=', account.id),
        ])

        for contract in contracts:
            query = """
            query ($contractId: ID!) {
                earnings(contractId: $contractId) {
                    edges {
                        node {
                            id
                            description
                            date
                            periodStart
                            periodEnd
                            grossAmount {
                                amount
                                currencyCode
                            }
                            serviceFee {
                                amount
                            }
                            serviceFeePercentage
                            netAmount {
                                amount
                            }
                            totalHours
                        }
                    }
                }
            }
            """
            try:
                result = self._graphql_query(
                    account, query,
                    variables={'contractId': contract.upwork_contract_id}
                )
                data = result.get('data', {})
                earnings_data = data.get('earnings', {}).get('edges', [])

                Earning = self.env['upwork.earning'].sudo()
                for edge in earnings_data:
                    node = edge.get('node', {})
                    earning_id = node.get('id')
                    date_str = node.get('date')
                    if not date_str:
                        continue

                    gross_data = node.get('grossAmount', {})
                    fee_data = node.get('serviceFee', {})
                    net_data = node.get('netAmount', {})

                    vals = {
                        'name': node.get('description', f'Earning {earning_id}'),
                        'upwork_earning_id': earning_id,
                        'date': date_str[:10],
                        'contract_id': contract.id,
                        'upwork_account_id': account.id,
                        'partner_id': contract.partner_id.id if contract.partner_id else False,
                        'currency_id': contract.currency_id.id,
                        'gross_amount': float(gross_data.get('amount', 0)),
                        'upwork_fee': float(fee_data.get('amount', 0)) if fee_data else 0.0,
                        'upwork_fee_percent': float(node.get('serviceFeePercentage', 0)),
                        'net_amount': float(net_data.get('amount', 0)) if net_data else 0.0,
                        'total_hours': float(node.get('totalHours', 0)),
                        'company_id': account.company_id.id,
                    }

                    period_start = node.get('periodStart')
                    if period_start:
                        vals['period_start'] = period_start[:10]

                    period_end = node.get('periodEnd')
                    if period_end:
                        vals['period_end'] = period_end[:10]

                    existing = Earning.search([
                        ('upwork_earning_id', '=', earning_id),
                        ('contract_id', '=', contract.id),
                    ], limit=1)

                    if existing:
                        existing.write(vals)
                    elif earning_id:
                        Earning.create(vals)

            except Exception as e:
                _logger.error(
                    "Failed to sync earnings for contract %s: %s",
                    contract.upwork_contract_id, e
                )

        account.sudo().write({'last_sync': fields.Datetime.now()})
        _logger.info("Synced earnings for Upwork account %s", account.name)

    # ------------------------------------------------------------------
    # Cron entry points
    # ------------------------------------------------------------------

    @api.model
    def cron_sync_contracts(self):
        """Cron job: Sync contracts for all active Upwork accounts."""
        accounts = self._get_active_accounts()
        _logger.info("Cron: Syncing contracts for %d Upwork accounts", len(accounts))
        for account in accounts:
            try:
                self._sync_contracts_for_account(account)
            except Exception as e:
                _logger.error("Cron: Contract sync failed for account %s: %s", account.name, e)

    @api.model
    def cron_sync_timelogs(self):
        """Cron job: Sync time logs for all active Upwork accounts."""
        accounts = self._get_active_accounts()
        _logger.info("Cron: Syncing time logs for %d Upwork accounts", len(accounts))
        for account in accounts:
            try:
                self._sync_timelogs_for_account(account)
            except Exception as e:
                _logger.error("Cron: Timelog sync failed for account %s: %s", account.name, e)

    @api.model
    def cron_sync_earnings(self):
        """Cron job: Sync earnings for all active Upwork accounts."""
        accounts = self._get_active_accounts()
        _logger.info("Cron: Syncing earnings for %d Upwork accounts", len(accounts))
        for account in accounts:
            try:
                self._sync_earnings_for_account(account)
            except Exception as e:
                _logger.error("Cron: Earnings sync failed for account %s: %s", account.name, e)

    @api.model
    def cron_refresh_tokens(self):
        """Cron job: Refresh OAuth tokens for all connected accounts."""
        accounts = self.env['upwork.account'].sudo().search([
            ('state', '=', 'connected'),
            ('active', '=', True),
            ('refresh_token', '!=', False),
        ])
        _logger.info("Cron: Refreshing tokens for %d Upwork accounts", len(accounts))
        for account in accounts:
            try:
                # Only refresh if token is expiring within 2 hours
                if account.token_expiry and account.token_expiry <= fields.Datetime.now() + timedelta(hours=2):
                    self._refresh_access_token(account)
                    _logger.info("Refreshed token for Upwork account %s", account.name)
            except Exception as e:
                _logger.error("Cron: Token refresh failed for account %s: %s", account.name, e)
