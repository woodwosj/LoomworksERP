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

    @http.route('/loomworks/ai/chat/stream', type='http', auth='user', methods=['GET'])
    def send_message_stream(self, session_uuid=None, message=None, **kwargs):
        """
        Send a message and receive streaming response via Server-Sent Events.

        Uses GET method since the browser EventSource API only supports GET.
        auth='user' ensures authentication; GET requests do not need CSRF
        protection because they are not subject to CSRF attacks by design.

        Query parameters:
            session_uuid: Session UUID string
            message: Message text (URL-encoded)

        Response: SSE stream with events:
            - data: {"type": "text", "content": "..."}
            - data: {"type": "tool_call", "tool": "...", "input": {...}}
            - data: {"type": "done"}
        """
        try:
            # Support both query params (GET) and body (POST fallback)
            if not session_uuid or not message:
                data = json.loads(request.httprequest.data or '{}')
                session_uuid = session_uuid or data.get('session_uuid')
                message = message or data.get('message')
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
    # TOOLS
    # =========================================================================

    @http.route('/loomworks/ai/tools', type='json', auth='user', methods=['POST'])
    def list_tools(self, agent_id=None, category=None, **kwargs):
        """
        List available AI tools.

        Request:
            {
                "agent_id": 1,  // Optional - filter by agent
                "category": "data"  // Optional - filter by category
            }

        Response:
            {
                "tools": [
                    {
                        "id": 1,
                        "name": "Search Records",
                        "technical_name": "search_records",
                        "category": "data",
                        "description": "...",
                        "risk_level": "safe"
                    }
                ]
            }
        """
        Tool = request.env['loomworks.ai.tool']
        domain = [('active', '=', True)]

        if agent_id:
            agent = request.env['loomworks.ai.agent'].browse(agent_id)
            if agent.exists() and agent.tool_ids:
                domain.append(('id', 'in', agent.tool_ids.ids))

        if category:
            domain.append(('category', '=', category))

        tools = Tool.search(domain, order='category, sequence, name')

        return {
            'tools': [{
                'id': t.id,
                'name': t.name,
                'technical_name': t.technical_name,
                'category': t.category,
                'description': t.description,
                'risk_level': t.risk_level,
                'requires_confirmation': t.requires_confirmation,
                'usage_count': t.usage_count,
            } for t in tools],
            'total': len(tools),
        }

    @http.route('/loomworks/ai/tools/<string:technical_name>', type='json', auth='user', methods=['POST'])
    def get_tool(self, technical_name, **kwargs):
        """
        Get detailed information about a specific tool.
        """
        tool = request.env['loomworks.ai.tool'].search([
            ('technical_name', '=', technical_name),
            ('active', '=', True)
        ], limit=1)

        if not tool:
            return {'error': 'Tool not found'}

        import json
        return {
            'id': tool.id,
            'name': tool.name,
            'technical_name': tool.technical_name,
            'category': tool.category,
            'description': tool.description,
            'parameters_schema': json.loads(tool.parameters_schema),
            'returns_description': tool.returns_description,
            'risk_level': tool.risk_level,
            'requires_confirmation': tool.requires_confirmation,
            'usage_count': tool.usage_count,
            'last_used': tool.last_used.isoformat() if tool.last_used else None,
        }

    # =========================================================================
    # FEEDBACK
    # =========================================================================

    @http.route('/loomworks/ai/feedback', type='json', auth='user', methods=['POST'])
    def submit_feedback(self, session_uuid, message_id=None, rating=None, feedback_text=None, feedback_type='general', **kwargs):
        """
        Submit feedback on AI responses.

        Request:
            {
                "session_uuid": "abc-123-...",
                "message_id": 42,  // Optional - specific message
                "rating": 5,  // 1-5 scale
                "feedback_text": "This was very helpful!",
                "feedback_type": "helpful"  // 'helpful', 'unhelpful', 'incorrect', 'general'
            }

        Response:
            {
                "success": true,
                "feedback_id": 1
            }
        """
        session = request.env['loomworks.ai.session'].search([
            ('uuid', '=', session_uuid),
            ('user_id', '=', request.env.user.id)
        ], limit=1)

        if not session:
            return {'error': 'Session not found'}

        # The loomworks.ai.feedback model does not exist yet.
        # Log feedback to the AI operation log as a structured record instead.
        try:
            request.env['loomworks.ai.operation.log'].create_log(
                session_id=session.id,
                tool_name='user_feedback',
                operation_type='other',
                input_data={
                    'message_id': message_id,
                    'rating': rating,
                    'feedback_text': feedback_text,
                    'feedback_type': feedback_type,
                },
                state='success',
            )
            return {
                'success': True,
                'feedback_id': None,
                'note': 'Feedback logged to operation log'
            }
        except Exception as e:
            _logger.error("Failed to log feedback: %s", e)
            return {'error': str(e)}

    # =========================================================================
    # USER SETTINGS
    # =========================================================================

    @http.route('/loomworks/ai/settings', type='json', auth='user', methods=['POST'])
    def get_user_settings(self, **kwargs):
        """
        Get current user's AI settings.
        """
        settings = request.env['loomworks.ai.user.settings'].get_user_settings()
        return settings.get_settings_dict()

    @http.route('/loomworks/ai/settings/update', type='json', auth='user', methods=['POST'])
    def update_user_settings(self, **kwargs):
        """
        Update current user's AI settings.

        Request:
            {
                "enableSuggestions": true,
                "suggestionFrequency": "normal",
                "notificationStyle": "popup"
            }
        """
        # Remove non-setting keys
        values = {k: v for k, v in kwargs.items() if k not in ['csrf_token']}
        result = request.env['loomworks.ai.user.settings'].update_user_settings(values)
        return result

    # =========================================================================
    # CONTEXT QUICK ACTIONS
    # =========================================================================

    @http.route('/loomworks/ai/quick_actions', type='json', auth='user', methods=['POST'])
    def get_quick_actions(self, model=None, record_id=None, view_type=None, **kwargs):
        """
        Get context-specific quick actions for the AI navbar.

        Request:
            {
                "model": "sale.order",
                "record_id": 42,
                "view_type": "form"
            }

        Response:
            {
                "actions": [
                    {"id": "confirm", "label": "Confirm Order", "icon": "fa-check"}
                ]
            }
        """
        if not model:
            return {'actions': []}

        actions = []

        # Model-specific quick actions
        if model == 'sale.order':
            actions = [
                {'id': 'create_quote', 'label': 'New Quote', 'icon': 'fa-plus', 'query': 'Create a new sales quotation'},
                {'id': 'check_inventory', 'label': 'Check Stock', 'icon': 'fa-cubes', 'query': 'Check inventory for this order'},
            ]
            if record_id:
                actions.append({'id': 'order_status', 'label': 'Order Status', 'icon': 'fa-info', 'query': f'What is the status of order {record_id}?'})

        elif model == 'purchase.order':
            actions = [
                {'id': 'create_po', 'label': 'New PO', 'icon': 'fa-plus', 'query': 'Create a new purchase order'},
                {'id': 'check_deliveries', 'label': 'Deliveries', 'icon': 'fa-truck', 'query': 'Show pending deliveries'},
            ]

        elif model == 'res.partner':
            actions = [
                {'id': 'create_contact', 'label': 'New Contact', 'icon': 'fa-user-plus', 'query': 'Create a new contact'},
                {'id': 'contact_history', 'label': 'History', 'icon': 'fa-history', 'query': 'Show transaction history for this contact'},
            ]

        elif model == 'account.move':
            actions = [
                {'id': 'create_invoice', 'label': 'New Invoice', 'icon': 'fa-file-text', 'query': 'Create a new invoice'},
                {'id': 'overdue_invoices', 'label': 'Overdue', 'icon': 'fa-exclamation-triangle', 'query': 'Show overdue invoices'},
            ]

        else:
            # Generic actions
            actions = [
                {'id': 'search', 'label': 'Search', 'icon': 'fa-search', 'query': f'Search {model}'},
                {'id': 'create', 'label': 'Create', 'icon': 'fa-plus', 'query': f'Create a new {model} record'},
            ]

        # Always include dashboard
        actions.append({'id': 'dashboard', 'label': 'Dashboard', 'icon': 'fa-tachometer', 'query': 'Show business dashboard'})

        return {'actions': actions[:5]}  # Limit to 5

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
