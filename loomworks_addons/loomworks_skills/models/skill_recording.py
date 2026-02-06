# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Loomworks Skill Recording Models - Session Recording for Skill Creation

These models track user actions during recording sessions, enabling
conversion of recorded workflows into reusable skill definitions.

Recording Flow:
1. User starts recording (creates LoomworksSkillRecording)
2. User actions are captured as LoomworksSkillRecordingAction records
3. Recording is stopped
4. AI analyzes actions and converts to skill steps
5. New LoomworksSkill is created with generated steps
"""

from loomworks import models, fields, api
from loomworks.exceptions import UserError
import json
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class LoomworksSkillRecording(models.Model):
    """
    Recording session for capturing user workflows.

    A recording session captures a series of user actions that can be
    analyzed and converted into a reusable skill definition.
    """
    _name = 'loomworks.skill.recording'
    _description = 'Skill Recording Session'
    _order = 'create_date desc'
    _inherit = ['mail.thread']

    # Session identification
    name = fields.Char(
        string='Recording Name',
        default=lambda self: f"Recording {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        help='Name for this recording session'
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        default=lambda self: self.env.uid
    )

    # Recording state
    state = fields.Selection([
        ('recording', 'Recording'),
        ('stopped', 'Stopped'),
        ('analyzing', 'Analyzing'),
        ('converted', 'Converted to Skill'),
        ('failed', 'Conversion Failed'),
    ], string='State', default='recording', required=True, tracking=True)

    # Timing
    started_at = fields.Datetime(
        string='Started At',
        default=fields.Datetime.now,
        readonly=True
    )
    stopped_at = fields.Datetime(
        string='Stopped At',
        readonly=True
    )
    duration_seconds = fields.Integer(
        string='Duration (seconds)',
        compute='_compute_duration'
    )

    # Context
    start_model = fields.Char(
        string='Starting Model',
        help='Model where recording started'
    )
    start_record_id = fields.Integer(
        string='Starting Record ID',
        help='Record ID where recording started'
    )

    # Recorded actions
    action_ids = fields.One2many(
        'loomworks.skill.recording.action',
        'recording_id',
        string='Recorded Actions'
    )
    action_count = fields.Integer(
        string='Action Count',
        compute='_compute_action_count'
    )

    # User inputs captured during recording
    user_inputs = fields.Text(
        string='User Inputs (JSON)',
        help='JSON array of user inputs during recording'
    )

    # Generated skill
    generated_skill_id = fields.Many2one(
        'loomworks.skill',
        string='Generated Skill',
        readonly=True,
        help='Skill created from this recording'
    )

    # Options
    capture_field_changes = fields.Boolean(
        string='Capture Field Changes',
        default=True,
        help='Record individual field changes'
    )
    capture_searches = fields.Boolean(
        string='Capture Searches',
        default=True,
        help='Record search operations'
    )

    # Error tracking
    error_message = fields.Text(
        string='Error Message',
        readonly=True
    )

    @api.depends('started_at', 'stopped_at')
    def _compute_duration(self):
        for rec in self:
            if rec.started_at and rec.stopped_at:
                delta = rec.stopped_at - rec.started_at
                rec.duration_seconds = int(delta.total_seconds())
            elif rec.started_at and rec.state == 'recording':
                delta = fields.Datetime.now() - rec.started_at
                rec.duration_seconds = int(delta.total_seconds())
            else:
                rec.duration_seconds = 0

    def _compute_action_count(self):
        for rec in self:
            rec.action_count = len(rec.action_ids)

    @api.model
    def start_recording(self, options=None):
        """
        Start a new recording session.

        :param options: Dict of recording options
        :return: Created recording record
        """
        options = options or {}

        # Check for existing active recording
        active = self.search([
            ('user_id', '=', self.env.uid),
            ('state', '=', 'recording'),
        ], limit=1)

        if active:
            raise UserError(
                "A recording is already in progress. "
                "Please stop it before starting a new one."
            )

        recording = self.create({
            'name': options.get('name', f"Recording {datetime.now().strftime('%Y-%m-%d %H:%M')}"),
            'start_model': options.get('start_model'),
            'start_record_id': options.get('start_record_id'),
            'capture_field_changes': options.get('capture_field_changes', True),
            'capture_searches': options.get('capture_searches', True),
        })

        _logger.info(
            "Started recording session %s for user %s",
            recording.id, self.env.user.login
        )

        return recording

    def stop_recording(self):
        """
        Stop the recording session.

        :return: Self
        """
        self.ensure_one()

        if self.state != 'recording':
            raise UserError(f"Cannot stop recording in state '{self.state}'")

        self.write({
            'state': 'stopped',
            'stopped_at': fields.Datetime.now(),
        })

        _logger.info(
            "Stopped recording session %s with %d actions",
            self.id, len(self.action_ids)
        )

        return self

    def record_action(self, action_type, action_data):
        """
        Record a single action during the session.

        :param action_type: Type of action (rpc, navigation, etc.)
        :param action_data: Dict of action details
        :return: Created action record
        """
        self.ensure_one()

        if self.state != 'recording':
            return False

        return self.env['loomworks.skill.recording.action'].create({
            'recording_id': self.id,
            'action_type': action_type,
            'timestamp': fields.Datetime.now(),
            'model_name': action_data.get('model'),
            'method_name': action_data.get('method'),
            'record_ids': json.dumps(action_data.get('record_ids', [])),
            'parameters': json.dumps(action_data.get('params', {})),
            'result_summary': json.dumps(action_data.get('result_summary', {})),
        })

    def convert_to_skill(self, skill_name=None, category='custom'):
        """
        Convert recorded actions into a reusable skill.

        Uses AI to analyze the recorded actions and generate
        appropriate skill steps.

        :param skill_name: Name for the generated skill
        :param category: Skill category
        :return: Created skill record
        """
        self.ensure_one()

        if self.state not in ('stopped',):
            raise UserError("Recording must be stopped before conversion")

        if not self.action_ids:
            raise UserError("No actions were recorded")

        self.state = 'analyzing'

        try:
            # Convert actions to steps
            steps = self._convert_actions_to_steps()

            # Derive skill name if not provided
            if not skill_name:
                skill_name = self._derive_skill_name(steps)

            # Infer trigger phrases
            triggers = self._infer_triggers(skill_name)

            # Create skill
            skill = self.env['loomworks.skill'].create({
                'name': skill_name,
                'technical_name': self._to_technical_name(skill_name),
                'category': category,
                'description': f"Skill created from recording on {self.started_at}",
                'trigger_phrases': json.dumps(triggers),
                'state': 'draft',
                'owner_id': self.user_id.id,
            })

            # Create steps
            for seq, step_data in enumerate(steps):
                self.env['loomworks.skill.step'].create({
                    'skill_id': skill.id,
                    'sequence': (seq + 1) * 10,
                    **step_data,
                })

            self.write({
                'state': 'converted',
                'generated_skill_id': skill.id,
            })

            _logger.info(
                "Converted recording %s to skill %s with %d steps",
                self.id, skill.name, len(steps)
            )

            return skill

        except Exception as e:
            self.write({
                'state': 'failed',
                'error_message': str(e),
            })
            _logger.exception("Failed to convert recording %s to skill", self.id)
            raise UserError(f"Failed to convert recording: {e}")

    def _convert_actions_to_steps(self):
        """
        Convert recorded actions to skill step definitions.

        :return: List of step data dicts
        """
        steps = []
        actions = self.action_ids.sorted('timestamp')

        for action in actions:
            step_data = action._to_step_data()
            if step_data:
                steps.append(step_data)

        # Merge consecutive similar steps if appropriate
        steps = self._optimize_steps(steps)

        return steps

    def _optimize_steps(self, steps):
        """
        Optimize step list by merging similar consecutive steps.

        :param steps: List of step dicts
        :return: Optimized list
        """
        if len(steps) < 2:
            return steps

        optimized = []
        current_step = steps[0]

        for next_step in steps[1:]:
            # Check if we can merge
            if (current_step.get('step_type') == 'tool_call' and
                next_step.get('step_type') == 'tool_call' and
                current_step.get('tool_name') == 'search_records' and
                next_step.get('tool_name') == 'search_records'):
                # Skip consecutive searches on same model
                continue

            optimized.append(current_step)
            current_step = next_step

        optimized.append(current_step)
        return optimized

    def _derive_skill_name(self, steps):
        """
        Derive a meaningful skill name from steps.

        :param steps: List of step dicts
        :return: Suggested skill name
        """
        if not steps:
            return "Recorded Workflow"

        # Find the primary action
        for step in steps:
            tool_params = step.get('tool_parameters', '{}')
            if isinstance(tool_params, str):
                try:
                    params = json.loads(tool_params)
                except json.JSONDecodeError:
                    params = {}
            else:
                params = tool_params

            model = params.get('model', '')
            tool_name = step.get('tool_name', '')

            if model:
                model_display = model.replace('.', ' ').title()
                if 'create' in tool_name:
                    return f"Create {model_display}"
                elif 'update' in tool_name:
                    return f"Update {model_display}"
                elif 'delete' in tool_name:
                    return f"Delete {model_display}"

        return "Recorded Workflow"

    def _infer_triggers(self, skill_name):
        """
        Generate trigger phrases from skill name and recorded inputs.

        :param skill_name: Skill name
        :return: List of trigger phrases
        """
        triggers = []

        # From skill name
        name_lower = skill_name.lower()
        triggers.append(name_lower)
        triggers.append(f"please {name_lower}")
        triggers.append(f"i want to {name_lower}")

        # From user inputs
        if self.user_inputs:
            try:
                inputs = json.loads(self.user_inputs)
                for inp in inputs[:5]:  # Limit
                    value = inp.get('value', '')
                    if value and len(value) > 5:
                        triggers.append(value.lower())
            except json.JSONDecodeError:
                pass

        return list(set(triggers))[:10]

    def _to_technical_name(self, name):
        """
        Convert display name to technical name.

        :param name: Display name
        :return: kebab-case technical name
        """
        import re
        if not name:
            return 'recorded-skill'
        technical = re.sub(r'[^a-z0-9]+', '-', name.lower())
        return technical.strip('-')

    def action_view_skill(self):
        """Open generated skill form."""
        self.ensure_one()
        if not self.generated_skill_id:
            raise UserError("No skill has been generated from this recording")

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'loomworks.skill',
            'res_id': self.generated_skill_id.id,
            'views': [[False, 'form']],
            'target': 'current',
        }


class LoomworksSkillRecordingAction(models.Model):
    """
    Individual action recorded during a skill recording session.

    Each action represents a single RPC call, navigation, or user interaction
    that was captured during the recording.
    """
    _name = 'loomworks.skill.recording.action'
    _description = 'Recorded Action'
    _order = 'timestamp'

    recording_id = fields.Many2one(
        'loomworks.skill.recording',
        string='Recording',
        required=True,
        ondelete='cascade'
    )

    # Action details
    action_type = fields.Selection([
        ('rpc_call', 'RPC Call'),
        ('rpc_create', 'Create Record'),
        ('rpc_write', 'Update Record'),
        ('rpc_unlink', 'Delete Record'),
        ('rpc_search', 'Search Records'),
        ('navigation', 'Navigation'),
        ('button_click', 'Button Click'),
        ('field_change', 'Field Change'),
        ('action_execute', 'Action Execute'),
    ], string='Action Type', required=True)

    timestamp = fields.Datetime(
        string='Timestamp',
        default=fields.Datetime.now
    )

    # Model and method
    model_name = fields.Char(
        string='Model',
        help='Loomworks model name'
    )
    method_name = fields.Char(
        string='Method',
        help='Method or action name'
    )

    # Record references
    record_ids = fields.Text(
        string='Record IDs (JSON)',
        help='JSON array of affected record IDs'
    )

    # Parameters and result
    parameters = fields.Text(
        string='Parameters (JSON)',
        help='JSON of method parameters'
    )
    result_summary = fields.Text(
        string='Result Summary (JSON)',
        help='JSON summary of method result'
    )

    def get_parameters(self):
        """Return parsed parameters dict."""
        if self.parameters:
            try:
                return json.loads(self.parameters)
            except json.JSONDecodeError:
                pass
        return {}

    def get_record_ids(self):
        """Return parsed record IDs list."""
        if self.record_ids:
            try:
                return json.loads(self.record_ids)
            except json.JSONDecodeError:
                pass
        return []

    def _to_step_data(self):
        """
        Convert this action to a skill step definition.

        :return: Dict of step data or None if not convertible
        """
        if self.action_type == 'rpc_create':
            return {
                'name': f"Create {self.model_name or 'record'}",
                'step_type': 'tool_call',
                'tool_name': 'create_record',
                'tool_parameters': json.dumps({
                    'model': self.model_name,
                    'values': self._sanitize_values(self.get_parameters().get('values', {})),
                }),
            }

        elif self.action_type == 'rpc_write':
            return {
                'name': f"Update {self.model_name or 'record'}",
                'step_type': 'tool_call',
                'tool_name': 'update_record',
                'tool_parameters': json.dumps({
                    'model': self.model_name,
                    'values': self._sanitize_values(self.get_parameters().get('values', {})),
                }),
            }

        elif self.action_type == 'rpc_search':
            params = self.get_parameters()
            return {
                'name': f"Search {self.model_name or 'records'}",
                'step_type': 'tool_call',
                'tool_name': 'search_records',
                'tool_parameters': json.dumps({
                    'model': self.model_name,
                    'domain': params.get('domain', []),
                    'fields': params.get('fields', []),
                    'limit': params.get('limit', 80),
                }),
            }

        elif self.action_type == 'rpc_unlink':
            return {
                'name': f"Delete {self.model_name or 'record'}",
                'step_type': 'tool_call',
                'tool_name': 'delete_record',
                'tool_parameters': json.dumps({
                    'model': self.model_name,
                }),
            }

        elif self.action_type == 'action_execute':
            return {
                'name': f"Execute {self.method_name or 'action'}",
                'step_type': 'tool_call',
                'tool_name': 'execute_action',
                'tool_parameters': json.dumps({
                    'model': self.model_name,
                    'action': self.method_name,
                }),
            }

        elif self.action_type == 'navigation':
            return {
                'name': f"Navigate to {self.model_name or 'view'}",
                'step_type': 'action',
                'instructions': f"Navigate to {self.model_name}",
            }

        return None

    def _sanitize_values(self, values):
        """
        Sanitize values dict, removing sensitive fields.

        :param values: Dict of field values
        :return: Sanitized dict
        """
        if not values:
            return {}

        sensitive_fields = {
            'password', 'secret', 'api_key', 'token', 'access_token',
            'refresh_token', 'private_key', 'credit_card',
        }

        return {
            k: v for k, v in values.items()
            if k.lower() not in sensitive_fields and not k.startswith('_')
        }
