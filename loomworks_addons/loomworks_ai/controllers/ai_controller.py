# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
HTTP/JSON-RPC controllers for AI chat functionality.

Provides REST and JSON-RPC endpoints for:
- Session management
- Message sending/receiving
- Operation history
- Rollback operations

Based on Odoo 18 controller patterns:
https://www.odoo.com/documentation/18.0/developer/reference/backend/http.html
"""

from odoo import http
from odoo.http import request, Response
import json
import logging

_logger = logging.getLogger(__name__)


class AIController(http.Controller):
    """
    Main controller for AI chat API endpoints.
    All endpoints require user authentication.
    """

    # =========================================================================
    # SESSION MANAGEMENT
    # =========================================================================

    @http.route('/loomworks/ai/session/create', type='json', auth='user', methods=['POST'])
    def create_session(self, agent_id=None, **kwargs):
        """
        Create a new AI chat session.

        Request:
            {
                "agent_id": 1  // Optional, uses default if not provided
            }

        Response:
            {
                "session_id": 1,
                "uuid": "abc-123-...",
                "agent_name": "Loomworks Assistant"
            }
        """
        Agent = request.env['loomworks.ai.agent']
        Session = request.env['loomworks.ai.session']

        # Get or find default agent
        if agent_id:
            agent = Agent.browse(agent_id)
            if not agent.exists():
                return {'error': 'Agent not found'}
        else:
            agent = Agent.search([
                ('company_id', '=', request.env.company.id),
                ('active', '=', True)
            ], limit=1)
            if not agent:
                return {'error': 'No active AI agent configured'}

        # Create session
        session = Session.create({
            'agent_id': agent.id,
            'user_id': request.env.user.id,
        })

        return {
            'session_id': session.id,
            'uuid': session.uuid,
            'agent_name': agent.name,
            'agent_id': agent.id,
        }

    @http.route('/loomworks/ai/session/<string:uuid>', type='json', auth='user', methods=['POST'])
    def get_session(self, uuid, **kwargs):
        """
        Get session details and recent messages.

        Response:
            {
                "session_id": 1,
                "state": "active",
                "messages": [...],
                "operations": [...]
            }
        """
        session = request.env['loomworks.ai.session'].search([
            ('uuid', '=', uuid),
            ('user_id', '=', request.env.user.id)
        ], limit=1)

        if not session:
            return {'error': 'Session not found'}

        return {
            'session_id': session.id,
            'uuid': session.uuid,
            'state': session.state,
            'agent_name': session.agent_id.name,
            'message_count': session.message_count,
            'operation_count': session.operation_count,
            'messages': self._format_messages(session.message_ids[-50:]),
            'has_uncommitted_changes': session.has_uncommitted_changes,
        }

    @http.route('/loomworks/ai/session/<string:uuid>/close', type='json', auth='user', methods=['POST'])
    def close_session(self, uuid, **kwargs):
        """
        Close an active session.
        """
        session = request.env['loomworks.ai.session'].search([
            ('uuid', '=', uuid),
            ('user_id', '=', request.env.user.id)
        ], limit=1)

        if not session:
            return {'error': 'Session not found'}

        # Release any savepoints
        if session.has_uncommitted_changes:
            session.release_savepoint()

        session.write({'state': 'completed'})

        return {'success': True, 'session_id': session.id}

    @http.route('/loomworks/ai/sessions', type='json', auth='user', methods=['POST'])
    def list_sessions(self, limit=20, offset=0, **kwargs):
        """
        List user's recent chat sessions.

        Response:
            {
                "sessions": [
                    {"id": 1, "uuid": "...", "state": "active", ...}
                ],
                "total": 42
            }
        """
        Session = request.env['loomworks.ai.session']
        domain = [('user_id', '=', request.env.user.id)]

        total = Session.search_count(domain)
        sessions = Session.search(domain, limit=limit, offset=offset, order='create_date desc')

        return {
            'sessions': [{
                'id': s.id,
                'uuid': s.uuid,
                'name': s.name,
                'state': s.state,
                'agent_name': s.agent_id.name,
                'message_count': s.message_count,
                'created_at': s.create_date.isoformat() if s.create_date else None,
                'last_activity': s.last_activity.isoformat() if s.last_activity else None,
            } for s in sessions],
            'total': total,
        }

    # =========================================================================
    # CHAT MESSAGING
    # =========================================================================

    @http.route('/loomworks/ai/chat', type='json', auth='user', methods=['POST'])
    def send_message(self, session_uuid, message, **kwargs):
        """
        Send a message to the AI and get response.

        Request:
            {
                "session_uuid": "abc-123-...",
                "message": "Create a new customer named John Doe"
            }

        Response:
            {
                "response": "I'll create that customer for you...",
                "tool_calls": [...],
                "operations": [...]
            }
        """
        session = request.env['loomworks.ai.session'].search([
            ('uuid', '=', session_uuid),
            ('user_id', '=', request.env.user.id),
            ('state', '=', 'active')
        ], limit=1)

        if not session:
            return {'error': 'Active session not found'}

        agent = session.agent_id

        # Create Claude client
        from ..services.claude_client import create_claude_client
        client = create_claude_client(request.env, session, agent)

        # Process message synchronously
        try:
            result = client.send_message_sync(message)

            if 'error' in result:
                return {'error': result['error']}

            # Get operations performed in this turn
            recent_ops = request.env['loomworks.ai.operation.log'].search([
                ('session_id', '=', session.id)
            ], order='create_date desc', limit=10)

            return {
                'response': result.get('response', ''),
                'tool_calls': result.get('tool_calls', []),
                'operations': self._format_operations(recent_ops),
                'session_state': session.state,
                'has_uncommitted_changes': session.has_uncommitted_changes,
            }

        except Exception as e:
            _logger.error(f"Chat error: {e}")
            return {'error': str(e)}

    @http.route('/loomworks/ai/chat/stream', type='http', auth='user', methods=['POST'], csrf=False)
    def send_message_stream(self, **kwargs):
        """
        Send a message and receive streaming response via Server-Sent Events.

        Request body (JSON):
            {
                "session_uuid": "abc-123-...",
                "message": "..."
            }

        Response: SSE stream with events:
            - data: {"type": "text", "content": "..."}
            - data: {"type": "tool_call", "tool": "...", "input": {...}}
            - data: {"type": "done"}
        """
        try:
            data = json.loads(request.httprequest.data)
            session_uuid = data.get('session_uuid')
            message = data.get('message')
        except json.JSONDecodeError:
            return Response(
                json.dumps({'error': 'Invalid JSON'}),
                content_type='application/json',
                status=400
            )

        if not session_uuid or not message:
            return Response(
                json.dumps({'error': 'session_uuid and message are required'}),
                content_type='application/json',
                status=400
            )

        session = request.env['loomworks.ai.session'].search([
            ('uuid', '=', session_uuid),
            ('user_id', '=', request.env.user.id),
            ('state', '=', 'active')
        ], limit=1)

        if not session:
            return Response(
                json.dumps({'error': 'Session not found'}),
                content_type='application/json',
                status=404
            )

        def generate():
            """Generator for SSE stream."""
            from ..services.claude_client import create_claude_client
            client = create_claude_client(request.env, session, session.agent_id)

            try:
                for chunk in client.send_message(message):
                    yield f"data: {json.dumps(chunk)}\n\n"
            except Exception as e:
                _logger.error(f"Streaming error: {e}")
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        return Response(
            generate(),
            content_type='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',
            }
        )

    # =========================================================================
    # ROLLBACK OPERATIONS
    # =========================================================================

    @http.route('/loomworks/ai/session/<string:uuid>/rollback', type='json', auth='user', methods=['POST'])
    def rollback_session(self, uuid, **kwargs):
        """
        Rollback all uncommitted changes in the session.
        """
        session = request.env['loomworks.ai.session'].search([
            ('uuid', '=', uuid),
            ('user_id', '=', request.env.user.id)
        ], limit=1)

        if not session:
            return {'error': 'Session not found'}

        if not session.has_uncommitted_changes:
            return {'error': 'No uncommitted changes to rollback'}

        try:
            session.rollback_to_savepoint()
            return {
                'success': True,
                'message': 'Changes rolled back successfully'
            }
        except Exception as e:
            return {'error': str(e)}

    @http.route('/loomworks/ai/operation/<int:operation_id>/undo', type='json', auth='user', methods=['POST'])
    def undo_operation(self, operation_id, **kwargs):
        """
        Undo a specific operation from the log.
        """
        operation = request.env['loomworks.ai.operation.log'].browse(operation_id)

        if not operation.exists():
            return {'error': 'Operation not found'}

        # Verify user owns this operation
        if operation.user_id.id != request.env.user.id:
            return {'error': 'Access denied'}

        if not operation.can_undo():
            return {'error': 'This operation cannot be undone'}

        undo_ops = operation.get_undo_operations()
        if not undo_ops:
            return {'error': 'This operation cannot be undone'}

        try:
            # Execute undo
            Model = request.env[undo_ops['model']]
            if undo_ops['type'] == 'unlink':
                Model.browse(undo_ops['ids']).unlink()
            elif undo_ops['type'] == 'write':
                for rec_id, values in undo_ops['values'].items():
                    Model.browse(int(rec_id)).write(values)
            elif undo_ops['type'] == 'create':
                Model.create(undo_ops['values'])

            operation.write({'state': 'rolled_back'})

            return {'success': True, 'operation_id': operation_id}

        except Exception as e:
            return {'error': str(e)}

    @http.route('/loomworks/ai/session/<string:uuid>/operations', type='json', auth='user', methods=['POST'])
    def get_operations(self, uuid, limit=50, **kwargs):
        """
        Get operation history for a session.
        """
        session = request.env['loomworks.ai.session'].search([
            ('uuid', '=', uuid),
            ('user_id', '=', request.env.user.id)
        ], limit=1)

        if not session:
            return {'error': 'Session not found'}

        operations = request.env['loomworks.ai.operation.log'].search([
            ('session_id', '=', session.id)
        ], order='create_date desc', limit=limit)

        return {
            'operations': self._format_operations(operations),
            'total': len(session.operation_ids),
        }

    # =========================================================================
    # AGENT INFO
    # =========================================================================

    @http.route('/loomworks/ai/agents', type='json', auth='user', methods=['POST'])
    def list_agents(self, **kwargs):
        """
        List available AI agents for the current company.
        """
        agents = request.env['loomworks.ai.agent'].search([
            ('company_id', '=', request.env.company.id),
            ('active', '=', True)
        ])

        return {
            'agents': [{
                'id': a.id,
                'name': a.name,
                'technical_name': a.technical_name,
                'model': a.model_id,
                'permission_mode': a.permission_mode,
            } for a in agents]
        }

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _format_messages(self, messages):
        """Format message records for JSON response."""
        return [{
            'id': msg.id,
            'role': msg.role,
            'content': msg.content,
            'timestamp': msg.create_date.isoformat() if msg.create_date else None,
            'has_tool_calls': bool(msg.tool_calls_json),
        } for msg in messages]

    def _format_operations(self, operations):
        """Format operation records for JSON response."""
        return [{
            'id': op.id,
            'tool': op.tool_name,
            'type': op.operation_type,
            'model': op.model_name,
            'record_count': op.record_count,
            'state': op.state,
            'can_undo': op.can_undo(),
            'timestamp': op.create_date.isoformat() if op.create_date else None,
        } for op in operations]
