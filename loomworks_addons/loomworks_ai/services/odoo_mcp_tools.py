# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
MCP Tools for Odoo Operations.

This module implements tool functions that can be called by Claude AI
to perform CRUD operations, action execution, and report generation
on Odoo models.

Each tool function follows the MCP (Model Context Protocol) pattern:
- Receives typed parameters
- Returns structured JSON response
- Logs all operations for audit
- Respects security sandbox restrictions
"""

import json
import logging
import time

_logger = logging.getLogger(__name__)


class OdooMCPTools:
    """
    MCP tool implementations for Odoo operations.
    Requires Odoo environment context to be set before use.
    """

    def __init__(self, env, session, agent):
        """
        Initialize tools with Odoo context.

        Args:
            env: Odoo environment
            session: loomworks.ai.session record
            agent: loomworks.ai.agent record
        """
        self.env = env
        self.session = session
        self.agent = agent
        self.sandbox = env['loomworks.ai.sandbox']

    def search_records(
        self,
        model: str,
        domain: list = None,
        fields: list = None,
        limit: int = 80,
        offset: int = 0,
        order: str = None
    ) -> dict:
        """
        Search for records in any Odoo model.

        Args:
            model: The Odoo model name (e.g., 'sale.order', 'res.partner')
            domain: Search filter as list of tuples
            fields: List of field names to return
            limit: Maximum number of records to return (max: 500)
            offset: Number of records to skip for pagination
            order: Sort order (e.g., 'create_date desc, name')

        Returns:
            Dictionary with 'count', 'records', 'model', and 'has_more'
        """
        start_time = time.time()

        try:
            # Validate access
            self.sandbox.validate_model_access(model, 'read', self.agent)

            # Sanitize domain
            safe_domain = self.sandbox.sanitize_domain(model, domain or [])

            # Enforce limits
            limit = min(limit, 500)

            # Execute search
            Model = self.env[model]
            total_count = Model.search_count(safe_domain)
            records = Model.search(safe_domain, limit=limit, offset=offset, order=order)

            # Read specified fields or get default display fields
            if fields:
                safe_fields = self.sandbox.sanitize_fields(model, fields)
            else:
                # Return commonly useful fields
                safe_fields = ['id', 'display_name', 'create_date', 'write_date']
                if 'state' in Model._fields:
                    safe_fields.append('state')
                if 'active' in Model._fields:
                    safe_fields.append('active')

            records_data = records.read(safe_fields)

            # Convert datetime objects to strings for JSON serialization
            for rec in records_data:
                for key, value in rec.items():
                    if hasattr(value, 'isoformat'):
                        rec[key] = value.isoformat()

            execution_time = int((time.time() - start_time) * 1000)

            # Log the operation
            self.env['loomworks.ai.operation.log'].create_log(
                session_id=self.session.id,
                tool_name='search_records',
                operation_type='search',
                model_name=model,
                record_ids=records.ids,
                input_data={'domain': safe_domain, 'fields': safe_fields, 'limit': limit},
                output_data={'count': total_count, 'returned': len(records_data)},
                execution_time_ms=execution_time,
            )

            return {
                'model': model,
                'count': total_count,
                'records': records_data,
                'has_more': total_count > offset + len(records_data)
            }

        except Exception as e:
            _logger.error(f"search_records error: {e}")
            return {'error': str(e), 'model': model}

    def create_record(
        self,
        model: str,
        values: dict,
        context: dict = None
    ) -> dict:
        """
        Create a new record in an Odoo model.

        Args:
            model: The Odoo model name
            values: Dictionary of field values for the new record
            context: Optional Odoo context overrides

        Returns:
            Dictionary with 'id', 'display_name', and 'created' status
        """
        start_time = time.time()

        try:
            # Validate access
            self.sandbox.validate_model_access(model, 'create', self.agent)

            # Sanitize values
            safe_values = self.sandbox.sanitize_values(model, values, 'create')

            # Execute with sandbox
            with self.sandbox.sandboxed_execution(self.session, self.agent, f'create {model}') as sandbox_ctx:
                Model = self.env[model]
                if context:
                    Model = Model.with_context(**context)

                record = Model.create(safe_values)
                sandbox_ctx['records_created'] = record.ids

                # Capture created state
                created_state = self.sandbox.capture_record_state(model, record.ids)

                execution_time = int((time.time() - start_time) * 1000)

                # Log operation
                self.env['loomworks.ai.operation.log'].create_log(
                    session_id=self.session.id,
                    tool_name='create_record',
                    operation_type='create',
                    model_name=model,
                    record_ids=record.ids,
                    input_data=safe_values,
                    values_after=created_state,
                    execution_time_ms=execution_time,
                )

            return {
                'id': record.id,
                'display_name': record.display_name,
                'model': model,
                'created': True
            }

        except Exception as e:
            _logger.error(f"create_record error: {e}")
            return {'error': str(e), 'model': model, 'created': False}

    def update_record(
        self,
        model: str,
        record_id: int,
        values: dict,
        context: dict = None
    ) -> dict:
        """
        Update an existing record in an Odoo model.

        Args:
            model: The Odoo model name
            record_id: ID of the record to update
            values: Dictionary of field values to change
            context: Optional Odoo context overrides

        Returns:
            Dictionary with 'id', 'display_name', and 'updated' status
        """
        start_time = time.time()

        try:
            # Validate access
            self.sandbox.validate_model_access(model, 'write', self.agent)

            # Sanitize values
            safe_values = self.sandbox.sanitize_values(model, values, 'write')

            with self.sandbox.sandboxed_execution(self.session, self.agent, f'update {model}') as sandbox_ctx:
                Model = self.env[model]
                record = Model.browse(record_id)

                if not record.exists():
                    return {'error': f'Record {model}({record_id}) not found', 'updated': False}

                # Capture state before
                state_before = self.sandbox.capture_record_state(model, [record_id])

                # Apply context if provided
                if context:
                    record = record.with_context(**context)

                # Perform update
                record.write(safe_values)
                sandbox_ctx['records_modified'] = [record_id]

                # Capture state after
                state_after = self.sandbox.capture_record_state(model, [record_id])

                execution_time = int((time.time() - start_time) * 1000)

                # Log operation
                self.env['loomworks.ai.operation.log'].create_log(
                    session_id=self.session.id,
                    tool_name='update_record',
                    operation_type='write',
                    model_name=model,
                    record_ids=[record_id],
                    input_data=safe_values,
                    values_before=state_before,
                    values_after=state_after,
                    execution_time_ms=execution_time,
                )

            return {
                'id': record.id,
                'display_name': record.display_name,
                'model': model,
                'updated': True
            }

        except Exception as e:
            _logger.error(f"update_record error: {e}")
            return {'error': str(e), 'model': model, 'updated': False}

    def delete_record(
        self,
        model: str,
        record_id: int,
        confirm: bool = False
    ) -> dict:
        """
        Delete a record from an Odoo model.

        Args:
            model: The Odoo model name
            record_id: ID of the record to delete
            confirm: Must be True to actually delete (safety check)

        Returns:
            Dictionary with 'deleted' status and record info
        """
        start_time = time.time()

        if not confirm:
            return {
                'error': 'Deletion requires confirm=True for safety',
                'deleted': False,
                'hint': 'Set confirm=True to proceed with deletion'
            }

        try:
            # Validate access
            self.sandbox.validate_model_access(model, 'unlink', self.agent)

            with self.sandbox.sandboxed_execution(self.session, self.agent, f'delete {model}') as sandbox_ctx:
                Model = self.env[model]
                record = Model.browse(record_id)

                if not record.exists():
                    return {'error': f'Record {model}({record_id}) not found', 'deleted': False}

                # Capture state before deletion for potential undo
                state_before = self.sandbox.capture_record_state(model, [record_id])
                display_name = record.display_name

                # Perform deletion
                record.unlink()
                sandbox_ctx['records_deleted'] = [record_id]

                execution_time = int((time.time() - start_time) * 1000)

                # Log operation
                self.env['loomworks.ai.operation.log'].create_log(
                    session_id=self.session.id,
                    tool_name='delete_record',
                    operation_type='unlink',
                    model_name=model,
                    record_ids=[record_id],
                    values_before=state_before,
                    execution_time_ms=execution_time,
                )

            return {
                'id': record_id,
                'display_name': display_name,
                'model': model,
                'deleted': True
            }

        except Exception as e:
            _logger.error(f"delete_record error: {e}")
            return {'error': str(e), 'model': model, 'deleted': False}

    def execute_action(
        self,
        model: str,
        record_ids: list,
        action: str,
        parameters: dict = None
    ) -> dict:
        """
        Execute a business action or workflow on records.

        Args:
            model: The Odoo model name
            record_ids: List of record IDs to act on
            action: Method name to call (e.g., 'action_confirm')
            parameters: Optional parameters to pass to the action

        Returns:
            Dictionary with 'success' status and any action results
        """
        start_time = time.time()

        try:
            # Validate access
            self.sandbox.validate_model_access(model, 'write', self.agent)

            # Security: only allow known safe actions
            SAFE_ACTIONS = {
                'sale.order': ['action_confirm', 'action_cancel', 'action_draft', 'action_quotation_send'],
                'purchase.order': ['button_confirm', 'button_cancel', 'button_draft'],
                'account.move': ['action_post', 'button_draft', 'button_cancel'],
                'stock.picking': ['action_confirm', 'action_assign', 'button_validate'],
                'mrp.production': ['action_confirm', 'action_assign', 'button_mark_done'],
                'project.task': ['action_assign_to_me', 'action_open_task_form'],
            }

            allowed_actions = SAFE_ACTIONS.get(model, [])
            if action not in allowed_actions and not action.startswith('action_'):
                return {
                    'error': f"Action '{action}' is not in the allowed list for {model}",
                    'allowed_actions': allowed_actions,
                    'success': False
                }

            with self.sandbox.sandboxed_execution(self.session, self.agent, f'{action} on {model}') as sandbox_ctx:
                Model = self.env[model]
                records = Model.browse(record_ids)

                if not records.exists():
                    return {'error': 'No valid records found', 'success': False}

                # Capture state before
                state_before = self.sandbox.capture_record_state(model, record_ids)

                # Execute the action
                method = getattr(records, action, None)
                if not method or not callable(method):
                    return {'error': f"Method '{action}' not found on {model}", 'success': False}

                if parameters:
                    result = method(**parameters)
                else:
                    result = method()

                # Capture state after
                state_after = self.sandbox.capture_record_state(model, record_ids)

                execution_time = int((time.time() - start_time) * 1000)

                # Log operation
                self.env['loomworks.ai.operation.log'].create_log(
                    session_id=self.session.id,
                    tool_name='execute_action',
                    operation_type='action',
                    model_name=model,
                    record_ids=record_ids,
                    input_data={'action': action, 'parameters': parameters},
                    values_before=state_before,
                    values_after=state_after,
                    execution_time_ms=execution_time,
                )

            return {
                'model': model,
                'record_ids': record_ids,
                'action': action,
                'success': True,
                'result': str(result) if result else None
            }

        except Exception as e:
            _logger.error(f"execute_action error: {e}")
            return {'error': str(e), 'model': model, 'success': False}

    def generate_report(
        self,
        report_type: str,
        model: str = None,
        domain: list = None,
        date_from: str = None,
        date_to: str = None,
        group_by: list = None,
        measures: list = None
    ) -> dict:
        """
        Generate business reports and analytics.

        Args:
            report_type: Type of report ('summary', 'trend', 'breakdown', 'comparison')
            model: Odoo model to analyze
            domain: Filter criteria
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)
            group_by: Fields to group results by
            measures: Numeric fields to aggregate

        Returns:
            Dictionary with report data including aggregations and breakdowns
        """
        start_time = time.time()

        if not model:
            return {'error': 'Model is required for reports', 'success': False}

        try:
            # Validate access
            self.sandbox.validate_model_access(model, 'read', self.agent)

            # Build domain with date filters
            safe_domain = self.sandbox.sanitize_domain(model, domain or [])

            if date_from:
                safe_domain.append(('create_date', '>=', date_from))
            if date_to:
                safe_domain.append(('create_date', '<=', date_to))

            Model = self.env[model]

            # Execute read_group for aggregations
            if group_by and measures:
                # Validate fields exist
                valid_measures = [m for m in measures if m in Model._fields]
                valid_groups = []
                for g in group_by:
                    field_name = g.split(':')[0]
                    if field_name in Model._fields:
                        valid_groups.append(g)

                if valid_measures and valid_groups:
                    report_data = Model.read_group(
                        safe_domain,
                        fields=valid_measures,
                        groupby=valid_groups,
                        lazy=False
                    )
                    # Convert date fields for JSON
                    for item in report_data:
                        for key, value in item.items():
                            if hasattr(value, 'isoformat'):
                                item[key] = value.isoformat()
                else:
                    report_data = []
            else:
                # Simple count and totals
                report_data = {
                    'total_count': Model.search_count(safe_domain),
                }

                # Add sums for numeric fields if measures specified
                if measures:
                    records = Model.search(safe_domain, limit=10000)
                    for measure in measures:
                        if measure in Model._fields:
                            field = Model._fields[measure]
                            if field.type in ('integer', 'float', 'monetary'):
                                report_data[f'{measure}_sum'] = sum(records.mapped(measure))

            execution_time = int((time.time() - start_time) * 1000)

            # Log operation
            self.env['loomworks.ai.operation.log'].create_log(
                session_id=self.session.id,
                tool_name='generate_report',
                operation_type='report',
                model_name=model,
                input_data={
                    'report_type': report_type,
                    'domain': safe_domain,
                    'group_by': group_by,
                    'measures': measures
                },
                output_data={'record_count': len(report_data) if isinstance(report_data, list) else 1},
                execution_time_ms=execution_time,
            )

            return {
                'report_type': report_type,
                'model': model,
                'data': report_data,
                'success': True
            }

        except Exception as e:
            _logger.error(f"generate_report error: {e}")
            return {'error': str(e), 'model': model, 'success': False}


def get_tool_schemas():
    """Return all tool schemas for Claude API registration."""
    return [
        {
            'name': 'search_records',
            'description': '''Search for records in any Odoo model.

Use this tool to find existing records before creating new ones, to check if data exists, or to retrieve information for reports.

Examples:
- Find all draft sales orders: search_records(model='sale.order', domain=[['state', '=', 'draft']])
- Get customer list: search_records(model='res.partner', domain=[['customer_rank', '>', 0]], fields=['name', 'email'])''',
            'input_schema': {
                'type': 'object',
                'properties': {
                    'model': {'type': 'string', 'description': 'Odoo model name (e.g., sale.order, res.partner)'},
                    'domain': {'type': 'array', 'description': 'Search domain as list of tuples'},
                    'fields': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Fields to return'},
                    'limit': {'type': 'integer', 'default': 80, 'description': 'Max records (max 500)'},
                    'offset': {'type': 'integer', 'default': 0, 'description': 'Skip records for pagination'},
                    'order': {'type': 'string', 'description': 'Sort order (e.g., create_date desc)'}
                },
                'required': ['model']
            }
        },
        {
            'name': 'create_record',
            'description': '''Create a new record in an Odoo model.

Use this tool to create new business data like sales orders, invoices, products, contacts, etc.

Examples:
- Create contact: create_record(model='res.partner', values={'name': 'John Doe', 'email': 'john@example.com'})
- Create product: create_record(model='product.product', values={'name': 'Widget', 'list_price': 99.99})''',
            'input_schema': {
                'type': 'object',
                'properties': {
                    'model': {'type': 'string', 'description': 'Odoo model name'},
                    'values': {'type': 'object', 'description': 'Field values for new record'},
                    'context': {'type': 'object', 'description': 'Optional context overrides'}
                },
                'required': ['model', 'values']
            }
        },
        {
            'name': 'update_record',
            'description': '''Update an existing record in an Odoo model.

Always search for records first to confirm they exist before updating.

Examples:
- Update contact email: update_record(model='res.partner', record_id=42, values={'email': 'new@example.com'})''',
            'input_schema': {
                'type': 'object',
                'properties': {
                    'model': {'type': 'string', 'description': 'Odoo model name'},
                    'record_id': {'type': 'integer', 'description': 'ID of record to update'},
                    'values': {'type': 'object', 'description': 'Field values to change'},
                    'context': {'type': 'object', 'description': 'Optional context overrides'}
                },
                'required': ['model', 'record_id', 'values']
            }
        },
        {
            'name': 'delete_record',
            'description': '''Delete a record from an Odoo model.

WARNING: This is a destructive operation. The record will be permanently removed.

Example:
- Delete draft order: delete_record(model='sale.order', record_id=99, confirm=True)''',
            'input_schema': {
                'type': 'object',
                'properties': {
                    'model': {'type': 'string', 'description': 'Odoo model name'},
                    'record_id': {'type': 'integer', 'description': 'ID of record to delete'},
                    'confirm': {'type': 'boolean', 'default': False, 'description': 'Must be True to delete'}
                },
                'required': ['model', 'record_id']
            }
        },
        {
            'name': 'execute_action',
            'description': '''Execute a business action or workflow on records.

Common actions by model:
- sale.order: action_confirm, action_cancel, action_draft
- purchase.order: button_confirm, button_cancel
- account.move: action_post, button_draft

Example:
- Confirm sale: execute_action(model='sale.order', record_ids=[15], action='action_confirm')''',
            'input_schema': {
                'type': 'object',
                'properties': {
                    'model': {'type': 'string', 'description': 'Odoo model name'},
                    'record_ids': {'type': 'array', 'items': {'type': 'integer'}, 'description': 'Record IDs'},
                    'action': {'type': 'string', 'description': 'Method name to call'},
                    'parameters': {'type': 'object', 'description': 'Optional action parameters'}
                },
                'required': ['model', 'record_ids', 'action']
            }
        },
        {
            'name': 'generate_report',
            'description': '''Generate business reports and analytics.

Examples:
- Sales by month: generate_report(report_type='trend', model='sale.order', group_by=['create_date:month'], measures=['amount_total'])
- Revenue by customer: generate_report(report_type='breakdown', model='account.move.line', group_by=['partner_id'], measures=['balance'])''',
            'input_schema': {
                'type': 'object',
                'properties': {
                    'report_type': {
                        'type': 'string',
                        'enum': ['summary', 'trend', 'breakdown', 'comparison'],
                        'description': 'Type of report'
                    },
                    'model': {'type': 'string', 'description': 'Odoo model to analyze'},
                    'domain': {'type': 'array', 'description': 'Filter criteria'},
                    'date_from': {'type': 'string', 'format': 'date', 'description': 'Start date YYYY-MM-DD'},
                    'date_to': {'type': 'string', 'format': 'date', 'description': 'End date YYYY-MM-DD'},
                    'group_by': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Fields to group by'},
                    'measures': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Fields to aggregate'}
                },
                'required': ['report_type']
            }
        }
    ]
