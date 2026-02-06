# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Upwork AI Tool Provider - Registers AI tools for Upwork operations.
"""

from odoo import api, models, _
import logging

_logger = logging.getLogger(__name__)


class UpworkToolProvider(models.AbstractModel):
    """AI Tool Provider for Upwork operations."""
    _name = 'upwork.tool.provider'
    _inherit = 'loomworks.ai.tool.provider'
    _description = 'Upwork AI Tool Provider'

    @api.model
    def _get_tool_definitions(self):
        """Return Upwork tool definitions for AI."""
        return [
            {
                'name': 'List Upwork Contracts',
                'technical_name': 'upwork_list_contracts',
                'category': 'data',
                'description': '''List Upwork contracts with optional filters.

Use this tool when:
- User asks about their Upwork contracts
- User wants to see active or ended contracts
- User needs contract details like hourly rate or client''',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'state': {
                            'type': 'string',
                            'enum': ['active', 'paused', 'ended', 'all'],
                            'description': 'Filter by contract state',
                        },
                        'contract_type': {
                            'type': 'string',
                            'enum': ['hourly', 'fixed', 'all'],
                            'description': 'Filter by contract type',
                        },
                        'limit': {
                            'type': 'integer',
                            'description': 'Max number of results (default 20)',
                        },
                    },
                    'required': [],
                },
                'implementation_method': 'upwork.tool.provider._execute_list_contracts',
                'risk_level': 'safe',
                'returns_description': 'List of Upwork contracts with details',
                'sequence': 10,
            },
            {
                'name': 'Get Upwork Earnings Summary',
                'technical_name': 'upwork_earnings_summary',
                'category': 'data',
                'description': '''Get earnings summary from Upwork.

Use this tool when:
- User asks about Upwork income or revenue
- User wants to know how much they earned
- User needs financial overview from Upwork''',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'period': {
                            'type': 'string',
                            'enum': ['week', 'month', 'quarter', 'year', 'all'],
                            'description': 'Time period for summary',
                        },
                        'contract_id': {
                            'type': 'integer',
                            'description': 'Optional contract ID to filter by',
                        },
                    },
                    'required': [],
                },
                'implementation_method': 'upwork.tool.provider._execute_earnings_summary',
                'risk_level': 'safe',
                'returns_description': 'Earnings summary with totals and breakdowns',
                'sequence': 20,
            },
            {
                'name': 'Get Upwork Time Logs',
                'technical_name': 'upwork_time_logs',
                'category': 'data',
                'description': '''Get time tracking logs from Upwork.

Use this tool when:
- User asks about hours worked on Upwork
- User wants time tracking details
- User needs to review logged hours''',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'contract_id': {
                            'type': 'integer',
                            'description': 'Optional contract ID to filter by',
                        },
                        'date_from': {
                            'type': 'string',
                            'description': 'Start date (YYYY-MM-DD)',
                        },
                        'date_to': {
                            'type': 'string',
                            'description': 'End date (YYYY-MM-DD)',
                        },
                    },
                    'required': [],
                },
                'implementation_method': 'upwork.tool.provider._execute_time_logs',
                'risk_level': 'safe',
                'returns_description': 'List of time log entries with hours',
                'sequence': 30,
            },
            {
                'name': 'Sync Upwork Data',
                'technical_name': 'upwork_sync',
                'category': 'action',
                'description': '''Trigger a sync of Upwork data.

Use this tool when:
- User asks to refresh or sync Upwork data
- User wants latest contracts, timelogs or earnings from Upwork''',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'sync_type': {
                            'type': 'string',
                            'enum': ['contracts', 'timelogs', 'earnings', 'all'],
                            'description': 'What to sync',
                        },
                    },
                    'required': ['sync_type'],
                },
                'implementation_method': 'upwork.tool.provider._execute_sync',
                'risk_level': 'moderate',
                'requires_confirmation': True,
                'returns_description': 'Sync result summary',
                'sequence': 40,
            },
            {
                'name': 'Generate Upwork Proposal',
                'technical_name': 'upwork_generate_proposal',
                'category': 'action',
                'description': '''Generate an Upwork proposal for a job posting.

Use this tool when:
- User wants to create a new proposal
- User needs help writing an Upwork bid
- User asks to draft a proposal for a job''',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'job_title': {
                            'type': 'string',
                            'description': 'Title of the Upwork job posting',
                        },
                        'job_requirements': {
                            'type': 'string',
                            'description': 'Job requirements/description',
                        },
                        'hourly_rate': {
                            'type': 'number',
                            'description': 'Proposed hourly rate',
                        },
                        'estimated_hours': {
                            'type': 'number',
                            'description': 'Estimated hours for the project',
                        },
                        'modules': {
                            'type': 'string',
                            'description': 'Comma-separated relevant Odoo modules',
                        },
                    },
                    'required': ['job_title', 'job_requirements'],
                },
                'implementation_method': 'upwork.tool.provider._execute_generate_proposal',
                'risk_level': 'moderate',
                'requires_confirmation': True,
                'returns_description': 'Created proposal details',
                'sequence': 50,
            },
        ]

    # ==================== Tool Implementations ====================

    @api.model
    def _execute_list_contracts(self, params):
        """List Upwork contracts with optional filters."""
        domain = []
        state = params.get('state', 'all')
        if state and state != 'all':
            domain.append(('state', '=', state))

        contract_type = params.get('contract_type', 'all')
        if contract_type and contract_type != 'all':
            domain.append(('contract_type', '=', contract_type))

        limit = params.get('limit', 20)
        contracts = self.env['upwork.contract'].search(domain, limit=limit, order='start_date desc')

        results = []
        for c in contracts:
            results.append({
                'id': c.id,
                'name': c.name,
                'type': c.contract_type,
                'state': c.state,
                'client': c.partner_id.name if c.partner_id else '',
                'hourly_rate': c.hourly_rate,
                'start_date': str(c.start_date) if c.start_date else None,
                'end_date': str(c.end_date) if c.end_date else None,
            })

        return {
            'success': True,
            'count': len(results),
            'contracts': results,
        }

    @api.model
    def _execute_earnings_summary(self, params):
        """Get Upwork earnings summary."""
        from datetime import date, timedelta

        domain = []
        period = params.get('period', 'month')
        today = date.today()

        if period == 'week':
            domain.append(('date', '>=', today - timedelta(days=7)))
        elif period == 'month':
            domain.append(('date', '>=', today.replace(day=1)))
        elif period == 'quarter':
            quarter_start = today.replace(month=((today.month - 1) // 3) * 3 + 1, day=1)
            domain.append(('date', '>=', quarter_start))
        elif period == 'year':
            domain.append(('date', '>=', today.replace(month=1, day=1)))

        contract_id = params.get('contract_id')
        if contract_id:
            domain.append(('contract_id', '=', contract_id))

        earnings = self.env['upwork.earning'].search(domain)

        total_gross = sum(earnings.mapped('gross_amount'))
        total_fees = sum(earnings.mapped('upwork_fee'))
        total_net = sum(earnings.mapped('net_amount'))
        total_hours = sum(earnings.mapped('total_hours'))

        return {
            'success': True,
            'period': period,
            'earning_count': len(earnings),
            'total_gross': total_gross,
            'total_fees': total_fees,
            'total_net': total_net,
            'total_hours': total_hours,
            'avg_fee_percent': (total_fees / total_gross * 100) if total_gross else 0,
        }

    @api.model
    def _execute_time_logs(self, params):
        """Get Upwork time logs."""
        domain = []

        contract_id = params.get('contract_id')
        if contract_id:
            domain.append(('contract_id', '=', contract_id))

        date_from = params.get('date_from')
        if date_from:
            domain.append(('date', '>=', date_from))

        date_to = params.get('date_to')
        if date_to:
            domain.append(('date', '<=', date_to))

        timelogs = self.env['upwork.timelog'].search(domain, limit=50, order='date desc')

        results = []
        for t in timelogs:
            results.append({
                'id': t.id,
                'date': str(t.date),
                'contract': t.contract_id.name,
                'tracked_hours': t.tracked_hours,
                'manual_hours': t.manual_hours,
                'total_hours': t.total_hours,
                'memo': t.memo or '',
                'has_timesheet': bool(t.timesheet_id),
            })

        total_hours = sum(t.total_hours for t in timelogs)

        return {
            'success': True,
            'count': len(results),
            'total_hours': total_hours,
            'timelogs': results,
        }

    @api.model
    def _execute_sync(self, params):
        """Trigger Upwork data sync."""
        sync_type = params.get('sync_type', 'all')
        api_service = self.env['upwork.api.service']

        try:
            if sync_type in ('contracts', 'all'):
                api_service.cron_sync_contracts()
            if sync_type in ('timelogs', 'all'):
                api_service.cron_sync_timelogs()
            if sync_type in ('earnings', 'all'):
                api_service.cron_sync_earnings()

            return {
                'success': True,
                'message': f'Upwork {sync_type} sync completed successfully.',
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }

    @api.model
    def _execute_generate_proposal(self, params):
        """Generate an Upwork proposal."""
        job_title = params.get('job_title', '')
        job_requirements = params.get('job_requirements', '')
        hourly_rate = params.get('hourly_rate', 0)
        estimated_hours = params.get('estimated_hours', 0)
        modules = params.get('modules', '')

        # Find default account
        account = self.env['upwork.account'].search([
            ('state', '=', 'connected'),
            ('active', '=', True),
        ], limit=1)

        if not account:
            account = self.env['upwork.account'].search([
                ('active', '=', True),
            ], limit=1)

        if not account:
            return {
                'success': False,
                'error': 'No Upwork account found. Please create one first.',
            }

        proposal = self.env['upwork.proposal'].create({
            'name': f'Proposal: {job_title}',
            'title': job_title,
            'job_requirements': job_requirements,
            'hourly_rate': hourly_rate,
            'estimated_hours': estimated_hours,
            'module_list': modules,
            'upwork_account_id': account.id,
            'state': 'draft',
        })

        return {
            'success': True,
            'proposal_id': proposal.id,
            'name': proposal.name,
            'message': f"Proposal '{proposal.name}' created in draft state.",
        }
