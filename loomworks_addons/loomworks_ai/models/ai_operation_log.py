# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

from odoo import models, fields, api
import json


class AIOperationLog(models.Model):
    """
    Comprehensive audit log of all AI operations.
    Stores before/after state for rollback and compliance.
    """
    _name = 'loomworks.ai.operation.log'
    _description = 'AI Operation Log'
    _order = 'create_date desc'

    session_id = fields.Many2one(
        'loomworks.ai.session',
        string='Session',
        required=True,
        ondelete='cascade'
    )
    agent_id = fields.Many2one(
        'loomworks.ai.agent',
        related='session_id.agent_id',
        store=True
    )
    user_id = fields.Many2one(
        'res.users',
        related='session_id.user_id',
        store=True
    )

    # Operation details
    tool_name = fields.Char(
        string='Tool Name',
        required=True
    )
    operation_type = fields.Selection([
        ('search', 'Search'),
        ('read', 'Read'),
        ('create', 'Create'),
        ('write', 'Update'),
        ('unlink', 'Delete'),
        ('action', 'Execute Action'),
        ('report', 'Generate Report'),
        ('other', 'Other'),
    ], string='Operation Type', required=True)

    # Target model and records
    model_name = fields.Char(
        string='Model Name'
    )
    record_ids = fields.Char(
        string='Record IDs (JSON)',
        help='JSON array of affected record IDs'
    )
    record_count = fields.Integer(
        string='Record Count',
        compute='_compute_record_count',
        store=True
    )

    # Input/Output data
    input_data = fields.Text(
        string='Input Parameters (JSON)'
    )
    output_data = fields.Text(
        string='Output Data (JSON)'
    )

    # Before/After state for rollback
    values_before = fields.Text(
        string='Values Before (JSON)',
        help='Record state before modification'
    )
    values_after = fields.Text(
        string='Values After (JSON)',
        help='Record state after modification'
    )

    # Execution status
    state = fields.Selection([
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('error', 'Error'),
        ('rolled_back', 'Rolled Back'),
        ('skipped', 'Skipped'),
    ], string='State', default='pending', required=True)

    error_message = fields.Text(
        string='Error Message'
    )

    # Performance metrics
    execution_time_ms = fields.Integer(
        string='Execution Time (ms)'
    )

    # AI reasoning
    ai_reasoning = fields.Text(
        string='AI Reasoning',
        help='Why the AI chose this operation'
    )

    @api.depends('record_ids')
    def _compute_record_count(self):
        for log in self:
            if log.record_ids:
                try:
                    ids = json.loads(log.record_ids)
                    log.record_count = len(ids) if isinstance(ids, list) else 1
                except json.JSONDecodeError:
                    log.record_count = 0
            else:
                log.record_count = 0

    def get_undo_operations(self):
        """
        Generate operations to undo this change.
        Returns dict with model, operation, and values.
        """
        self.ensure_one()
        if self.operation_type == 'create':
            # Undo create = delete
            return {
                'type': 'unlink',
                'model': self.model_name,
                'ids': json.loads(self.record_ids) if self.record_ids else []
            }
        elif self.operation_type == 'write':
            # Undo write = restore previous values
            return {
                'type': 'write',
                'model': self.model_name,
                'ids': json.loads(self.record_ids) if self.record_ids else [],
                'values': json.loads(self.values_before) if self.values_before else {}
            }
        elif self.operation_type == 'unlink':
            # Undo delete = recreate (if we have the data)
            if self.values_before:
                return {
                    'type': 'create',
                    'model': self.model_name,
                    'values': json.loads(self.values_before)
                }
        return None

    def can_undo(self):
        """Check if this operation can be undone."""
        self.ensure_one()
        if self.state != 'success':
            return False
        if self.operation_type in ('search', 'read', 'report'):
            return False  # Read operations don't need undo
        if self.operation_type == 'unlink' and not self.values_before:
            return False  # Can't recreate without captured state
        return True

    @api.model
    def create_log(self, session_id, tool_name, operation_type, **kwargs):
        """Convenience method to create operation logs."""
        return self.create({
            'session_id': session_id,
            'tool_name': tool_name,
            'operation_type': operation_type,
            'model_name': kwargs.get('model_name'),
            'record_ids': json.dumps(kwargs.get('record_ids', [])),
            'input_data': json.dumps(kwargs.get('input_data', {})),
            'output_data': json.dumps(kwargs.get('output_data', {})),
            'values_before': json.dumps(kwargs.get('values_before', {})),
            'values_after': json.dumps(kwargs.get('values_after', {})),
            'state': kwargs.get('state', 'success'),
            'error_message': kwargs.get('error_message'),
            'execution_time_ms': kwargs.get('execution_time_ms'),
            'ai_reasoning': kwargs.get('ai_reasoning'),
        })
