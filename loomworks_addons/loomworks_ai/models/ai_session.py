# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

from odoo import models, fields, api
from odoo.exceptions import UserError
import json
import re
import uuid
from datetime import timedelta


def _sanitize_savepoint_name(name):
    """Sanitize savepoint name to prevent SQL injection.

    SAVEPOINT identifiers must be valid SQL identifiers. Since psycopg2's
    sql.Identifier does not work with SAVEPOINT commands, we strip all
    characters that are not alphanumeric or underscores.

    Args:
        name: Raw savepoint name string.

    Returns:
        Sanitized string safe for use as a PostgreSQL identifier (max 63 chars).
    """
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '', str(name))
    if not sanitized:
        sanitized = 'sp_default'
    return sanitized[:63]


class AISession(models.Model):
    """
    Tracks conversation sessions between users and AI agents.
    Each session maintains context across multiple message exchanges.
    """
    _name = 'loomworks.ai.session'
    _description = 'AI Conversation Session'
    _order = 'create_date desc'

    name = fields.Char(
        string='Session Name',
        compute='_compute_name',
        store=True
    )
    uuid = fields.Char(
        string='Session UUID',
        required=True,
        readonly=True,
        default=lambda self: str(uuid.uuid4()),
        copy=False
    )
    agent_id = fields.Many2one(
        'loomworks.ai.agent',
        string='AI Agent',
        required=True,
        ondelete='cascade'
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        default=lambda self: self.env.user,
        ondelete='cascade'
    )
    company_id = fields.Many2one(
        'res.company',
        related='agent_id.company_id',
        store=True
    )

    # Session State
    state = fields.Selection([
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('error', 'Error'),
        ('rolled_back', 'Rolled Back'),
    ], string='State', default='active', required=True)

    # Message History
    message_ids = fields.One2many(
        'loomworks.ai.message',
        'session_id',
        string='Messages'
    )
    message_count = fields.Integer(
        compute='_compute_message_count'
    )

    # Operation Tracking
    operation_ids = fields.One2many(
        'loomworks.ai.operation.log',
        'session_id',
        string='Operations'
    )
    operation_count = fields.Integer(
        compute='_compute_operation_count'
    )

    # Context Storage
    context_data = fields.Text(
        string='Session Context (JSON)',
        default='{}',
        help='Stores conversation context for continuity'
    )
    last_model_context = fields.Char(
        string='Last Active Model',
        help='The Odoo model user was working with'
    )
    last_record_ids = fields.Char(
        string='Last Record IDs (JSON)',
        help='Record IDs from last operation'
    )

    # Timestamps
    last_activity = fields.Datetime(
        string='Last Activity',
        default=fields.Datetime.now
    )
    duration_minutes = fields.Float(
        compute='_compute_duration'
    )

    # Rollback Support
    has_uncommitted_changes = fields.Boolean(
        string='Has Uncommitted Changes',
        default=False
    )
    savepoint_name = fields.Char(
        string='Current Savepoint'
    )

    _sql_constraints = [
        ('uuid_uniq', 'UNIQUE(uuid)', 'Session UUID must be unique'),
    ]

    @api.depends('create_date', 'user_id')
    def _compute_name(self):
        for session in self:
            date_str = session.create_date.strftime('%Y-%m-%d %H:%M') if session.create_date else ''
            session.name = f"{session.user_id.name} - {date_str}"

    def _compute_message_count(self):
        for session in self:
            session.message_count = len(session.message_ids)

    def _compute_operation_count(self):
        for session in self:
            session.operation_count = len(session.operation_ids)

    @api.depends('create_date', 'last_activity')
    def _compute_duration(self):
        for session in self:
            if session.create_date and session.last_activity:
                delta = session.last_activity - session.create_date
                session.duration_minutes = delta.total_seconds() / 60
            else:
                session.duration_minutes = 0

    def add_message(self, role, content, tool_calls=None, tool_results=None):
        """Add a message to the session history."""
        self.ensure_one()
        return self.env['loomworks.ai.message'].create({
            'session_id': self.id,
            'role': role,
            'content': content,
            'tool_calls_json': json.dumps(tool_calls) if tool_calls else False,
            'tool_results_json': json.dumps(tool_results) if tool_results else False,
        })

    def get_conversation_history(self, limit=50):
        """
        Retrieve conversation history formatted for Claude API.
        Returns list of message dicts with role and content.
        """
        self.ensure_one()
        messages = self.message_ids.sorted('create_date')[-limit:]

        history = []
        for msg in messages:
            entry = {
                'role': msg.role if msg.role != 'tool' else 'user',
                'content': msg.content,
            }
            # Include tool calls/results if present
            if msg.tool_calls_json:
                entry['tool_calls'] = json.loads(msg.tool_calls_json)
            if msg.tool_results_json:
                entry['tool_results'] = json.loads(msg.tool_results_json)
            history.append(entry)

        return history

    def update_context(self, key, value):
        """Update session context data."""
        self.ensure_one()
        context = json.loads(self.context_data or '{}')
        context[key] = value
        self.context_data = json.dumps(context)

    def get_context(self, key=None):
        """Retrieve session context data."""
        self.ensure_one()
        context = json.loads(self.context_data or '{}')
        if key:
            return context.get(key)
        return context

    def create_savepoint(self):
        """Create a database savepoint for rollback capability."""
        self.ensure_one()
        timestamp = fields.Datetime.now().strftime('%Y%m%d%H%M%S')
        savepoint_name = _sanitize_savepoint_name(
            f"ai_session_{self.uuid.replace('-', '_')[:8]}_{timestamp}"
        )
        self.env.cr.execute(f"SAVEPOINT {savepoint_name}")
        self.write({
            'savepoint_name': savepoint_name,
            'has_uncommitted_changes': True
        })
        return savepoint_name

    def rollback_to_savepoint(self):
        """Rollback all changes since last savepoint."""
        self.ensure_one()
        if not self.savepoint_name:
            raise UserError('No savepoint available for rollback')

        safe_name = _sanitize_savepoint_name(self.savepoint_name)
        self.env.cr.execute(f"ROLLBACK TO SAVEPOINT {safe_name}")
        self.write({
            'state': 'rolled_back',
            'has_uncommitted_changes': False,
            'savepoint_name': False
        })

        # Log the rollback
        self.add_message(
            role='system',
            content=f'Session rolled back to savepoint'
        )

    def release_savepoint(self):
        """Release savepoint and commit changes."""
        self.ensure_one()
        if self.savepoint_name:
            safe_name = _sanitize_savepoint_name(self.savepoint_name)
            self.env.cr.execute(f"RELEASE SAVEPOINT {safe_name}")
            self.write({
                'savepoint_name': False,
                'has_uncommitted_changes': False
            })

    def touch(self):
        """Update last activity timestamp."""
        self.write({'last_activity': fields.Datetime.now()})

    @api.model
    def cleanup_stale_sessions(self, hours=24):
        """Archive sessions inactive for specified hours."""
        cutoff = fields.Datetime.now() - timedelta(hours=hours)
        stale_sessions = self.search([
            ('state', '=', 'active'),
            ('last_activity', '<', cutoff)
        ])
        stale_sessions.write({'state': 'completed'})
        return len(stale_sessions)


class AIMessage(models.Model):
    """Individual messages within an AI session."""
    _name = 'loomworks.ai.message'
    _description = 'AI Chat Message'
    _order = 'create_date asc'

    session_id = fields.Many2one(
        'loomworks.ai.session',
        string='Session',
        required=True,
        ondelete='cascade'
    )
    role = fields.Selection([
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
        ('tool', 'Tool Result'),
    ], string='Role', required=True)

    content = fields.Text(
        string='Content',
        required=True
    )

    # Tool interaction data
    tool_calls_json = fields.Text(
        string='Tool Calls (JSON)',
        help='JSON array of tool calls made by assistant'
    )
    tool_results_json = fields.Text(
        string='Tool Results (JSON)',
        help='JSON array of tool execution results'
    )

    # Metadata
    token_count = fields.Integer(
        string='Token Count'
    )
    processing_time_ms = fields.Integer(
        string='Processing Time (ms)'
    )
