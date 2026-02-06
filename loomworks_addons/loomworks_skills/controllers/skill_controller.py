# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Skill Controller - HTTP Endpoints for Skills Framework

Provides REST-like endpoints for:
- Skill execution
- Intent matching
- Recording management
- Skill listing and search

All endpoints require authentication.
"""

import json
import logging

from loomworks import http
from loomworks.http import request, Response

_logger = logging.getLogger(__name__)


class SkillController(http.Controller):
    """HTTP controller for skill operations."""

    # =====================
    # Skill Execution
    # =====================

    @http.route('/loomworks_skills/execute', type='json', auth='user', methods=['POST'])
    def execute_skill(self, skill_name=None, skill_id=None, context=None, **kwargs):
        """
        Execute a skill by name or ID.

        Args:
            skill_name: Technical name of the skill
            skill_id: ID of the skill (alternative to skill_name)
            context: Dict of context parameters

        Returns:
            Execution result dict
        """
        context = context or {}

        try:
            # Find skill
            if skill_id:
                skill = request.env['loomworks.skill'].browse(skill_id)
            elif skill_name:
                skill = request.env['loomworks.skill'].search([
                    ('technical_name', '=', skill_name),
                    ('state', '=', 'active'),
                ], limit=1)
            else:
                return {'error': 'skill_name or skill_id required'}

            if not skill.exists():
                return {'error': f"Skill not found: {skill_name or skill_id}"}

            # Execute
            result = skill.action_execute(context=context)
            return result

        except Exception as e:
            _logger.exception("Skill execution failed")
            return {
                'error': str(e),
                'success': False,
            }

    @http.route('/loomworks_skills/resume', type='json', auth='user', methods=['POST'])
    def resume_execution(self, execution_id, user_input, **kwargs):
        """
        Resume a paused execution with user input.

        Args:
            execution_id: ID of the execution to resume
            user_input: User provided input value

        Returns:
            Continued execution result
        """
        try:
            execution = request.env['loomworks.skill.execution'].browse(execution_id)
            if not execution.exists():
                return {'error': 'Execution not found'}

            if execution.state != 'waiting_input':
                return {'error': f"Execution not waiting for input (state: {execution.state})"}

            # Use execution service to resume
            from ..services.skill_execution_service import SkillExecutionService
            service = SkillExecutionService(request.env)
            result = service.resume_execution(execution, user_input)

            return result

        except Exception as e:
            _logger.exception("Resume execution failed")
            return {
                'error': str(e),
                'success': False,
            }

    @http.route('/loomworks_skills/cancel', type='json', auth='user', methods=['POST'])
    def cancel_execution(self, execution_id, reason=None, **kwargs):
        """
        Cancel a running execution.

        Args:
            execution_id: ID of the execution to cancel
            reason: Optional cancellation reason

        Returns:
            Cancellation result
        """
        try:
            execution = request.env['loomworks.skill.execution'].browse(execution_id)
            if not execution.exists():
                return {'error': 'Execution not found'}

            execution.cancel_execution(reason)

            return {
                'success': True,
                'execution_id': execution_id,
                'state': 'cancelled',
            }

        except Exception as e:
            _logger.exception("Cancel execution failed")
            return {
                'error': str(e),
                'success': False,
            }

    # =====================
    # Intent Matching
    # =====================

    @http.route('/loomworks_skills/match', type='json', auth='user', methods=['POST'])
    def match_intent(self, user_input, model=None, **kwargs):
        """
        Match user input against available skills.

        Args:
            user_input: Natural language text
            model: Optional model context for filtering

        Returns:
            Match result with skill, confidence, and params
        """
        try:
            domain = None
            if model:
                model_rec = request.env['ir.model'].search([('model', '=', model)], limit=1)
                if model_rec:
                    domain = [('trigger_model_ids', 'in', model_rec.id)]

            result = request.env['loomworks.skill'].match_intent(user_input, domain)
            return result

        except Exception as e:
            _logger.exception("Intent matching failed")
            return {
                'error': str(e),
                'skill_id': None,
                'confidence': 0,
            }

    @http.route('/loomworks_skills/suggest', type='json', auth='user', methods=['POST'])
    def suggest_skills(self, user_input=None, model=None, limit=5, **kwargs):
        """
        Get skill suggestions for context.

        Args:
            user_input: Optional natural language hint
            model: Current model for context-aware suggestions
            limit: Maximum suggestions to return

        Returns:
            List of suggested skills
        """
        try:
            domain = [('state', '=', 'active')]

            if model:
                model_rec = request.env['ir.model'].search([('model', '=', model)], limit=1)
                if model_rec:
                    domain.extend([
                        '|',
                        ('trigger_model_ids', 'in', model_rec.id),
                        ('model_id', '=', model_rec.id),
                    ])

            skills = request.env['loomworks.skill'].search(
                domain, limit=limit
            )

            return [{
                'id': s.id,
                'name': s.name,
                'technical_name': s.technical_name,
                'category': s.category,
                'description': s.description or '',
            } for s in skills]

        except Exception as e:
            _logger.exception("Skill suggestion failed")
            return []

    # =====================
    # Skill Listing
    # =====================

    @http.route('/loomworks_skills/list', type='json', auth='user', methods=['POST'])
    def list_skills(self, category=None, search=None, limit=50, **kwargs):
        """
        List available skills.

        Args:
            category: Filter by category
            search: Search term for name/description
            limit: Maximum results

        Returns:
            List of skill info dicts
        """
        try:
            domain = [('state', '=', 'active')]

            if category:
                domain.append(('category', '=', category))

            if search:
                domain.extend([
                    '|',
                    ('name', 'ilike', search),
                    ('description', 'ilike', search),
                ])

            skills = request.env['loomworks.skill'].search(
                domain, limit=limit, order='category, name'
            )

            return [{
                'id': s.id,
                'name': s.name,
                'technical_name': s.technical_name,
                'category': s.category,
                'description': s.description or '',
                'is_builtin': s.is_builtin,
                'success_rate': s.success_rate,
                'execution_count': s.execution_count,
            } for s in skills]

        except Exception as e:
            _logger.exception("Skill listing failed")
            return []

    @http.route('/loomworks_skills/get/<int:skill_id>', type='json', auth='user', methods=['POST'])
    def get_skill(self, skill_id, **kwargs):
        """
        Get detailed skill information.

        Args:
            skill_id: Skill ID

        Returns:
            Skill details dict
        """
        try:
            skill = request.env['loomworks.skill'].browse(skill_id)
            if not skill.exists():
                return {'error': 'Skill not found'}

            return {
                'id': skill.id,
                'name': skill.name,
                'technical_name': skill.technical_name,
                'category': skill.category,
                'description': skill.description or '',
                'version': skill.version,
                'state': skill.state,
                'is_builtin': skill.is_builtin,
                'trigger_phrases': skill.get_trigger_phrases(),
                'context_schema': skill.get_context_schema(),
                'required_context': skill.get_required_context(),
                'requires_confirmation': skill.requires_confirmation,
                'step_count': skill.step_count,
                'success_rate': skill.success_rate,
                'execution_count': skill.execution_count,
                'avg_duration_ms': skill.avg_duration_ms,
            }

        except Exception as e:
            _logger.exception("Get skill failed")
            return {'error': str(e)}

    # =====================
    # Recording Management
    # =====================

    @http.route('/loomworks_skills/recording/start', type='json', auth='user', methods=['POST'])
    def start_recording(self, name=None, **kwargs):
        """
        Start a new recording session.

        Args:
            name: Optional name for the recording

        Returns:
            Recording session info
        """
        try:
            recording = request.env['loomworks.skill.recording'].start_recording({
                'name': name,
            })

            return {
                'success': True,
                'recording_id': recording.id,
                'name': recording.name,
            }

        except Exception as e:
            _logger.exception("Start recording failed")
            return {
                'error': str(e),
                'success': False,
            }

    @http.route('/loomworks_skills/recording/stop', type='json', auth='user', methods=['POST'])
    def stop_recording(self, recording_id=None, convert=False, skill_name=None, **kwargs):
        """
        Stop a recording session.

        Args:
            recording_id: ID of recording to stop (optional, uses active)
            convert: Whether to convert to skill
            skill_name: Name for converted skill

        Returns:
            Recording summary and optional skill info
        """
        try:
            if recording_id:
                recording = request.env['loomworks.skill.recording'].browse(recording_id)
            else:
                recording = request.env['loomworks.skill.recording'].search([
                    ('user_id', '=', request.env.uid),
                    ('state', '=', 'recording'),
                ], limit=1)

            if not recording:
                return {'error': 'No active recording found'}

            recording.stop_recording()

            result = {
                'success': True,
                'recording_id': recording.id,
                'action_count': recording.action_count,
                'duration_seconds': recording.duration_seconds,
            }

            if convert:
                skill = recording.convert_to_skill(
                    skill_name=skill_name,
                    category='custom'
                )
                result['skill'] = {
                    'id': skill.id,
                    'name': skill.name,
                    'technical_name': skill.technical_name,
                }

            return result

        except Exception as e:
            _logger.exception("Stop recording failed")
            return {
                'error': str(e),
                'success': False,
            }

    @http.route('/loomworks_skills/recording/action', type='json', auth='user', methods=['POST'])
    def record_action(self, recording_id, action_type, action_data, **kwargs):
        """
        Record an action during a recording session.

        Args:
            recording_id: Recording session ID
            action_type: Type of action
            action_data: Action details

        Returns:
            Success status
        """
        try:
            recording = request.env['loomworks.skill.recording'].browse(recording_id)
            if not recording.exists() or recording.state != 'recording':
                return {'error': 'Recording not active'}

            recording.record_action(action_type, action_data)

            return {'success': True}

        except Exception as e:
            _logger.exception("Record action failed")
            return {
                'error': str(e),
                'success': False,
            }

    @http.route('/loomworks_skills/recording/status', type='json', auth='user', methods=['POST'])
    def recording_status(self, **kwargs):
        """
        Get current recording status for the user.

        Returns:
            Active recording info or None
        """
        try:
            recording = request.env['loomworks.skill.recording'].search([
                ('user_id', '=', request.env.uid),
                ('state', '=', 'recording'),
            ], limit=1)

            if recording:
                return {
                    'active': True,
                    'recording_id': recording.id,
                    'name': recording.name,
                    'action_count': recording.action_count,
                    'duration_seconds': recording.duration_seconds,
                }

            return {'active': False}

        except Exception as e:
            _logger.exception("Recording status failed")
            return {'active': False, 'error': str(e)}

    # =====================
    # Execution History
    # =====================

    @http.route('/loomworks_skills/executions', type='json', auth='user', methods=['POST'])
    def list_executions(self, skill_id=None, limit=20, **kwargs):
        """
        List recent skill executions for current user.

        Args:
            skill_id: Optional filter by skill
            limit: Maximum results

        Returns:
            List of execution summaries
        """
        try:
            domain = [('user_id', '=', request.env.uid)]

            if skill_id:
                domain.append(('skill_id', '=', skill_id))

            executions = request.env['loomworks.skill.execution'].search(
                domain, limit=limit, order='started_at desc'
            )

            return [{
                'id': e.id,
                'skill_name': e.skill_name,
                'state': e.state,
                'started_at': e.started_at.isoformat() if e.started_at else None,
                'duration_ms': e.duration_ms,
                'result_summary': e.result_summary,
            } for e in executions]

        except Exception as e:
            _logger.exception("List executions failed")
            return []

    # =====================
    # Rollback Status
    # =====================

    @http.route('/loomworks_skills/rollback/status', type='json', auth='user', methods=['POST'])
    def rollback_status(self, **kwargs):
        """
        Get rollback capability status.

        Returns:
            Dict with rollback mode and availability info
        """
        try:
            from ..services.rollback_manager import RollbackManager
            manager = RollbackManager(request.env)

            return {
                'snapshot_available': manager.snapshot_available,
                'rollback_mode': manager.get_rollback_mode(),
                'warning': manager.get_degradation_warning(),
            }

        except Exception as e:
            _logger.exception("Rollback status failed")
            return {
                'snapshot_available': False,
                'rollback_mode': 'savepoint',
                'error': str(e),
            }
