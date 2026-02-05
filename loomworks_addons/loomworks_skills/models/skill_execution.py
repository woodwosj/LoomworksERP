# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Loomworks Skill Execution Model - Execution Tracking and History

This model tracks the execution of skills, including state management,
input/output data, operation logs, and rollback support.

Execution States:
- pending: Waiting to start
- running: Currently executing
- waiting_input: Paused, waiting for user input
- completed: Successfully finished
- failed: Execution failed
- cancelled: Manually cancelled
- rolled_back: Rolled back due to failure
"""

from odoo import models, fields, api
from odoo.exceptions import UserError
import json
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class LoomworksSkillExecution(models.Model):
    """
    Execution record for a skill run.

    Tracks the complete lifecycle of a skill execution including:
    - Input context and extracted parameters
    - Output data and results
    - Step-by-step execution progress
    - Operation logs for audit
    - Snapshot reference for rollback
    """
    _name = 'loomworks.skill.execution'
    _description = 'Skill Execution Record'
    _order = 'started_at desc'
    _inherit = ['mail.thread']

    # Skill reference
    skill_id = fields.Many2one(
        'loomworks.skill',
        string='Skill',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    skill_name = fields.Char(
        related='skill_id.name',
        string='Skill Name',
        store=True
    )
    skill_technical_name = fields.Char(
        related='skill_id.technical_name',
        string='Technical Name',
        store=True
    )

    # User and session
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        default=lambda self: self.env.uid
    )
    session_id = fields.Many2one(
        'loomworks.ai.session',
        string='AI Session',
        help='AI chat session that triggered this execution'
    )

    # Execution state
    state = fields.Selection([
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('waiting_input', 'Waiting for Input'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('rolled_back', 'Rolled Back'),
    ], string='State', default='pending', required=True, tracking=True)

    # Timing
    started_at = fields.Datetime(
        string='Started At',
        readonly=True
    )
    completed_at = fields.Datetime(
        string='Completed At',
        readonly=True
    )
    duration_ms = fields.Integer(
        string='Duration (ms)',
        compute='_compute_duration',
        store=True
    )

    # Input/Output data
    trigger_text = fields.Text(
        string='Trigger Text',
        help='Original user input that triggered the skill'
    )
    input_data = fields.Text(
        string='Input Data (JSON)',
        help='JSON context provided to the skill'
    )
    output_data = fields.Text(
        string='Output Data (JSON)',
        help='JSON result from skill execution'
    )
    current_context = fields.Text(
        string='Current Context (JSON)',
        help='Current execution context with all variables'
    )

    # Step tracking
    current_step = fields.Integer(
        string='Current Step',
        default=0,
        help='Index of currently executing step'
    )
    current_step_id = fields.Many2one(
        'loomworks.skill.step',
        string='Current Step Record'
    )
    steps_completed = fields.Integer(
        string='Steps Completed',
        default=0
    )
    steps_total = fields.Integer(
        string='Total Steps',
        compute='_compute_steps_total',
        store=True
    )

    # Pending input
    pending_input_prompt = fields.Text(
        string='Pending Input Prompt',
        help='Prompt for user input when state is waiting_input'
    )
    pending_input_type = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('selection', 'Selection'),
        ('boolean', 'Yes/No'),
        ('record', 'Record Selection'),
        ('confirmation', 'Confirmation'),
    ], string='Pending Input Type')
    pending_input_options = fields.Text(
        string='Input Options (JSON)'
    )
    pending_input_variable = fields.Char(
        string='Input Variable',
        help='Context variable to store the input'
    )

    # Rollback support (M3 resolution)
    snapshot_id = fields.Many2one(
        'loomworks.snapshot',
        string='Snapshot',
        help='Pre-execution snapshot for PITR rollback (requires loomworks_snapshot)'
    )
    savepoint_name = fields.Char(
        string='Savepoint Name',
        help='PostgreSQL savepoint for transaction rollback'
    )
    can_rollback = fields.Boolean(
        string='Can Rollback',
        compute='_compute_can_rollback',
        help='Whether this execution can be rolled back'
    )
    rollback_mode = fields.Selection([
        ('snapshot', 'Full Snapshot (PITR)'),
        ('savepoint', 'Transaction Savepoint'),
        ('none', 'No Rollback Available'),
    ], string='Rollback Mode', compute='_compute_rollback_mode')

    # Operation logging
    operation_log_ids = fields.One2many(
        'loomworks.ai.operation.log',
        'execution_id',
        string='Operation Logs'
    )
    operation_count = fields.Integer(
        string='Operation Count',
        compute='_compute_operation_count'
    )

    # Error tracking
    error_message = fields.Text(
        string='Error Message',
        readonly=True
    )
    error_step_id = fields.Many2one(
        'loomworks.skill.step',
        string='Error Step',
        readonly=True
    )

    # Result summary
    result_summary = fields.Text(
        string='Result Summary',
        readonly=True,
        help='Human-readable summary of execution result'
    )

    @api.depends('started_at', 'completed_at')
    def _compute_duration(self):
        for rec in self:
            if rec.started_at and rec.completed_at:
                delta = rec.completed_at - rec.started_at
                rec.duration_ms = int(delta.total_seconds() * 1000)
            else:
                rec.duration_ms = 0

    @api.depends('skill_id.step_ids')
    def _compute_steps_total(self):
        for rec in self:
            rec.steps_total = len(rec.skill_id.step_ids) if rec.skill_id else 0

    def _compute_operation_count(self):
        for rec in self:
            rec.operation_count = len(rec.operation_log_ids)

    def _compute_can_rollback(self):
        for rec in self:
            rec.can_rollback = bool(rec.snapshot_id or rec.savepoint_name)

    def _compute_rollback_mode(self):
        for rec in self:
            if rec.snapshot_id:
                rec.rollback_mode = 'snapshot'
            elif rec.savepoint_name:
                rec.rollback_mode = 'savepoint'
            else:
                rec.rollback_mode = 'none'

    def get_input_data(self):
        """Return parsed input data dict."""
        self.ensure_one()
        if self.input_data:
            try:
                return json.loads(self.input_data)
            except json.JSONDecodeError:
                pass
        return {}

    def get_output_data(self):
        """Return parsed output data dict."""
        self.ensure_one()
        if self.output_data:
            try:
                return json.loads(self.output_data)
            except json.JSONDecodeError:
                pass
        return {}

    def get_current_context(self):
        """Return parsed current context dict."""
        self.ensure_one()
        if self.current_context:
            try:
                return json.loads(self.current_context)
            except json.JSONDecodeError:
                pass
        return {}

    def set_current_context(self, context):
        """Store current context as JSON."""
        self.ensure_one()
        self.current_context = json.dumps(context)

    def start_execution(self):
        """Mark execution as started."""
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(f"Cannot start execution in state '{self.state}'")
        self.write({
            'state': 'running',
            'started_at': fields.Datetime.now(),
        })

    def complete_execution(self, output_data=None, result_summary=None):
        """Mark execution as completed."""
        self.ensure_one()
        if self.state not in ('running', 'waiting_input'):
            raise UserError(f"Cannot complete execution in state '{self.state}'")

        vals = {
            'state': 'completed',
            'completed_at': fields.Datetime.now(),
        }
        if output_data:
            vals['output_data'] = json.dumps(output_data)
        if result_summary:
            vals['result_summary'] = result_summary

        self.write(vals)

        # Update skill statistics
        if self.skill_id:
            self.skill_id.record_execution(True, self.duration_ms)

    def fail_execution(self, error_message, error_step=None):
        """Mark execution as failed."""
        self.ensure_one()

        vals = {
            'state': 'failed',
            'completed_at': fields.Datetime.now(),
            'error_message': error_message,
        }
        if error_step:
            vals['error_step_id'] = error_step.id

        self.write(vals)

        # Update skill statistics
        if self.skill_id:
            self.skill_id.record_execution(False, self.duration_ms)

    def cancel_execution(self, reason=None):
        """Cancel execution."""
        self.ensure_one()
        if self.state in ('completed', 'failed', 'rolled_back'):
            raise UserError(f"Cannot cancel execution in state '{self.state}'")

        self.write({
            'state': 'cancelled',
            'completed_at': fields.Datetime.now(),
            'error_message': reason or 'Cancelled by user',
        })

    def request_input(self, prompt, input_type='text', variable=None, options=None):
        """Pause execution to request user input."""
        self.ensure_one()
        if self.state != 'running':
            raise UserError(f"Cannot request input in state '{self.state}'")

        self.write({
            'state': 'waiting_input',
            'pending_input_prompt': prompt,
            'pending_input_type': input_type,
            'pending_input_variable': variable,
            'pending_input_options': json.dumps(options) if options else None,
        })

    def provide_input(self, value):
        """Provide user input and resume execution."""
        self.ensure_one()
        if self.state != 'waiting_input':
            raise UserError(f"Cannot provide input in state '{self.state}'")

        # Store input in context
        context = self.get_current_context()
        if self.pending_input_variable:
            context[self.pending_input_variable] = value
            self.set_current_context(context)

        # Clear pending input and resume
        self.write({
            'state': 'running',
            'pending_input_prompt': None,
            'pending_input_type': None,
            'pending_input_options': None,
            'pending_input_variable': None,
        })

        return context

    def action_rollback(self):
        """
        Rollback execution changes.

        Uses snapshot if available (Phase 5), otherwise uses savepoint.
        """
        self.ensure_one()

        if self.state not in ('failed', 'completed'):
            raise UserError("Can only rollback completed or failed executions")

        if self.snapshot_id and self.snapshot_id.state == 'ready':
            # Use full PITR rollback
            self.snapshot_id.action_restore()
            self.state = 'rolled_back'
            _logger.info(
                "Execution %s rolled back using snapshot %s",
                self.id, self.snapshot_id.name
            )
        elif self.savepoint_name:
            # Savepoint rollback not possible after commit
            raise UserError(
                "Savepoint rollback is only available during execution. "
                "Install loomworks_snapshot for post-commit rollback."
            )
        else:
            raise UserError("No rollback mechanism available for this execution")

        return True

    def advance_step(self, step=None):
        """
        Advance to next step or specific step.

        :param step: Specific step to advance to (for branching)
        """
        self.ensure_one()

        if step:
            self.current_step_id = step
            # Find step index
            steps = self.skill_id.step_ids.sorted('sequence')
            for idx, s in enumerate(steps):
                if s.id == step.id:
                    self.current_step = idx
                    break
        else:
            self.current_step += 1
            steps = self.skill_id.step_ids.sorted('sequence')
            if self.current_step < len(steps):
                self.current_step_id = steps[self.current_step]
            else:
                self.current_step_id = False

        self.steps_completed = self.current_step

    def log_operation(self, tool_name, operation_type, params=None, result=None, error=None):
        """
        Log an operation performed during execution.

        :param tool_name: Name of the tool/operation
        :param operation_type: Type of operation (create, update, delete, etc.)
        :param params: Operation parameters
        :param result: Operation result
        :param error: Error message if failed
        """
        self.ensure_one()

        # Check if loomworks.ai.operation.log exists
        if 'loomworks.ai.operation.log' in self.env:
            self.env['loomworks.ai.operation.log'].create({
                'execution_id': self.id,
                'session_id': self.session_id.id if self.session_id else False,
                'tool_name': tool_name,
                'operation_type': operation_type,
                'parameters': json.dumps(params) if params else None,
                'result': json.dumps(result) if result else None,
                'error_message': error,
                'state': 'failed' if error else 'completed',
            })


class AIOperationLogExecution(models.Model):
    """Extend AI operation log with execution reference."""
    _inherit = 'loomworks.ai.operation.log'

    execution_id = fields.Many2one(
        'loomworks.skill.execution',
        string='Skill Execution',
        ondelete='cascade',
        help='Skill execution this operation was part of'
    )
