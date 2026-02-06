# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

from loomworks import models, fields, api
from loomworks.exceptions import AccessError, UserError
import json
import time
from contextlib import contextmanager


class AISandbox(models.AbstractModel):
    """
    Security sandbox for AI operations.
    Provides isolated execution with rollback capability.
    """
    _name = 'loomworks.ai.sandbox'
    _description = 'AI Operation Sandbox'

    # Models that AI cannot access under any circumstances
    FORBIDDEN_MODELS = [
        'res.users',
        'res.users.log',
        'ir.config_parameter',
        'ir.rule',
        'ir.model.access',
        'ir.module.module',
        'ir.cron',
        'ir.mail_server',
        'base.automation',
    ]

    # Fields that should never be exposed to AI
    FORBIDDEN_FIELDS = [
        'password',
        'password_crypt',
        'api_key',
        'secret',
        'token',
        'oauth_access_token',
        'totp_secret',
    ]

    @api.model
    def validate_model_access(self, model_name, operation, agent):
        """
        Validate if the agent can access the specified model.
        Raises AccessError if access is denied.
        """
        # Check forbidden models
        if model_name in self.FORBIDDEN_MODELS:
            raise AccessError(
                f"Access to model '{model_name}' is not permitted for AI agents."
            )

        # Check if model exists
        if model_name not in self.env:
            raise AccessError(
                f"Model '{model_name}' does not exist."
            )

        # Check agent-specific restrictions
        if not agent.check_model_access(model_name, operation):
            raise AccessError(
                f"Agent '{agent.name}' is not permitted to {operation} on '{model_name}'."
            )

        # Verify user has access (AI inherits user permissions)
        try:
            self.env[model_name].check_access_rights(operation)
        except AccessError as e:
            raise AccessError(
                f"User does not have {operation} access to '{model_name}': {str(e)}"
            )

        return True

    @api.model
    def sanitize_values(self, model_name, values, operation='write'):
        """
        Remove forbidden fields from values dict.
        Returns sanitized values.
        """
        if not values:
            return values

        sanitized = dict(values)
        model = self.env[model_name]

        # Remove forbidden fields
        for field_name in list(sanitized.keys()):
            if field_name in self.FORBIDDEN_FIELDS:
                del sanitized[field_name]
                continue

            # Check if field exists
            if field_name not in model._fields:
                del sanitized[field_name]
                continue

            field = model._fields[field_name]

            # Don't allow modifying computed fields
            if field.compute and not field.store:
                del sanitized[field_name]
                continue

            # Don't allow modifying readonly fields (except on create)
            if field.readonly and operation != 'create':
                del sanitized[field_name]

        return sanitized

    @api.model
    def sanitize_domain(self, model_name, domain):
        """
        Validate and sanitize search domain.
        Prevents injection attacks and forbidden field access.
        """
        if not domain:
            return []

        sanitized = []
        model = self.env[model_name]

        for element in domain:
            if isinstance(element, str):
                # Operators like '&', '|', '!'
                if element in ('&', '|', '!'):
                    sanitized.append(element)
            elif isinstance(element, (list, tuple)) and len(element) == 3:
                field_name, operator, value = element

                # Check field is not forbidden
                base_field = field_name.split('.')[0]
                if base_field in self.FORBIDDEN_FIELDS:
                    continue

                # Validate operator
                valid_operators = [
                    '=', '!=', '>', '>=', '<', '<=',
                    'in', 'not in', 'like', 'ilike',
                    '=like', '=ilike', 'child_of', 'parent_of'
                ]
                if operator not in valid_operators:
                    continue

                sanitized.append((field_name, operator, value))

        return sanitized

    @api.model
    def sanitize_fields(self, model_name, field_list):
        """
        Remove forbidden fields from a field list.
        """
        if not field_list:
            return field_list

        return [f for f in field_list if f not in self.FORBIDDEN_FIELDS]

    @api.model
    def capture_record_state(self, model_name, record_ids, fields_to_capture=None):
        """
        Capture current state of records for potential rollback.
        Returns dict mapping record IDs to their field values.
        """
        if not record_ids:
            return {}

        model = self.env[model_name]
        records = model.browse(record_ids).exists()

        if not records:
            return {}

        # Determine which fields to capture
        if fields_to_capture:
            field_names = [f for f in fields_to_capture if f in model._fields]
        else:
            # Capture all stored, non-computed fields
            field_names = [
                name for name, field in model._fields.items()
                if field.store and not (field.compute and not field.store)
                and name not in self.FORBIDDEN_FIELDS
                and name not in ['create_uid', 'create_date', 'write_uid', 'write_date']
            ]

        state = {}
        for record in records:
            record_data = {}
            for field_name in field_names:
                try:
                    value = record[field_name]
                    # Convert to serializable format
                    if hasattr(value, 'ids'):
                        record_data[field_name] = value.ids
                    elif isinstance(value, (int, float, str, bool, type(None))):
                        record_data[field_name] = value
                    else:
                        record_data[field_name] = str(value)
                except Exception:
                    pass
            state[record.id] = record_data

        return state

    @api.model
    @contextmanager
    def sandboxed_execution(self, session, agent, operation_desc=''):
        """
        Context manager for sandboxed AI operation execution.
        Handles savepoints, logging, and error recovery.

        Usage:
            with sandbox.sandboxed_execution(session, agent, 'create sale order') as ctx:
                # Perform operations
                ctx['records_created'] = new_records.ids
        """
        start_time = time.time()
        context = {
            'savepoint': None,
            'records_created': [],
            'records_modified': [],
            'records_deleted': [],
            'error': None,
        }

        # Create savepoint if enabled
        if agent.use_savepoints:
            savepoint_name = session.create_savepoint()
            context['savepoint'] = savepoint_name

        try:
            yield context

            # Success - release savepoint
            if context['savepoint']:
                session.release_savepoint()

        except Exception as e:
            context['error'] = str(e)

            # Rollback on error if enabled
            if agent.auto_rollback_on_error and context['savepoint']:
                try:
                    session.rollback_to_savepoint()
                except Exception:
                    pass  # Savepoint may already be released

            raise

        finally:
            # Log execution time
            execution_time = int((time.time() - start_time) * 1000)
            context['execution_time_ms'] = execution_time

    @api.model
    def execute_with_limits(self, session, agent, func, *args, **kwargs):
        """
        Execute a function with operation limits.
        Tracks operation count and enforces limits.
        """
        # Get current turn's operation count
        turn_ops = session.get_context('turn_operation_count') or 0

        if turn_ops >= agent.max_operations_per_turn:
            raise UserError(
                f"Maximum operations per turn ({agent.max_operations_per_turn}) exceeded. "
                "Please start a new conversation turn."
            )

        # Execute the function
        result = func(*args, **kwargs)

        # Increment counter
        session.update_context('turn_operation_count', turn_ops + 1)

        return result
