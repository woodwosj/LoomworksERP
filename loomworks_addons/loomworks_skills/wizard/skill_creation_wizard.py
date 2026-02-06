# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Skill Creation Wizard - Create Skills from Various Sources

This wizard enables users to create skills from:
1. Recording: Convert a recorded session into a skill
2. Natural Language: Describe what the skill should do, AI generates it
3. Manual: Start with a blank skill for manual configuration

The wizard guides users through the skill creation process and provides
previews of the generated skill definition before creation.
"""

from loomworks import models, fields, api
from loomworks.exceptions import UserError
import json
import re
import logging

_logger = logging.getLogger(__name__)


class SkillCreationWizard(models.TransientModel):
    """
    Transient wizard for creating skills.

    Provides a guided interface for creating skills from recordings,
    natural language descriptions, or manual definition.
    """
    _name = 'loomworks.skill.creation.wizard'
    _description = 'Skill Creation Wizard'

    # Creation method
    creation_method = fields.Selection([
        ('recording', 'From Recording'),
        ('natural_language', 'From Description (AI-Assisted)'),
        ('manual', 'Manual Definition'),
    ], string='Creation Method', default='natural_language', required=True)

    # =====================
    # Recording Source
    # =====================
    recording_id = fields.Many2one(
        'loomworks.skill.recording',
        string='Recording',
        domain=[('state', '=', 'stopped')]
    )
    recording_data = fields.Text(
        string='Recording Data (JSON)',
        help='JSON data from skill recorder service'
    )

    # =====================
    # Natural Language Input
    # =====================
    skill_description = fields.Text(
        string='Describe Your Skill',
        help='Describe what this skill should do in natural language. '
             'Be specific about the steps and expected outcomes.'
    )
    example_phrases = fields.Text(
        string='Example Trigger Phrases',
        help='Provide 3-5 examples of how users might ask for this skill. '
             'One phrase per line.'
    )
    example_input = fields.Text(
        string='Example Input',
        help='Provide an example of what information the user would provide'
    )
    example_output = fields.Text(
        string='Expected Outcome',
        help='Describe what should happen when the skill completes'
    )

    # =====================
    # Skill Configuration
    # =====================
    name = fields.Char(
        string='Skill Name',
        help='Display name for the skill'
    )
    technical_name = fields.Char(
        string='Technical Name',
        help='Unique identifier in kebab-case (auto-generated if empty)'
    )
    category = fields.Selection([
        ('sales', 'Sales'),
        ('purchase', 'Purchasing'),
        ('inventory', 'Inventory'),
        ('accounting', 'Accounting'),
        ('hr', 'Human Resources'),
        ('manufacturing', 'Manufacturing'),
        ('crm', 'CRM'),
        ('project', 'Project'),
        ('custom', 'Custom'),
    ], string='Category', default='custom', required=True)
    description = fields.Text(
        string='Description'
    )

    # =====================
    # Preview
    # =====================
    preview_steps = fields.Text(
        string='Preview: Steps',
        readonly=True,
        help='Preview of generated skill steps'
    )
    preview_triggers = fields.Text(
        string='Preview: Triggers',
        readonly=True,
        help='Preview of trigger phrases'
    )
    preview_context_schema = fields.Text(
        string='Preview: Context Schema',
        readonly=True,
        help='Preview of parameter schema'
    )

    # =====================
    # Options
    # =====================
    requires_confirmation = fields.Boolean(
        string='Require Confirmation',
        default=True,
        help='Ask user for confirmation before executing'
    )
    auto_snapshot = fields.Boolean(
        string='Auto Snapshot',
        default=True,
        help='Create rollback snapshot before execution'
    )
    max_operations = fields.Integer(
        string='Max Operations',
        default=10,
        help='Maximum tool calls per execution'
    )
    activate_immediately = fields.Boolean(
        string='Activate Immediately',
        default=False,
        help='Set skill to active state after creation'
    )

    @api.onchange('creation_method')
    def _onchange_creation_method(self):
        """Clear fields when creation method changes."""
        if self.creation_method == 'recording':
            self.skill_description = False
            self.example_phrases = False
        elif self.creation_method == 'natural_language':
            self.recording_id = False
            self.recording_data = False

    @api.onchange('recording_id')
    def _onchange_recording_id(self):
        """Populate fields from selected recording."""
        if not self.recording_id:
            return

        recording = self.recording_id
        if recording.generated_skill_id:
            raise UserError("This recording has already been converted to a skill")

        # Generate name from recording
        if not self.name:
            self.name = self._derive_name_from_recording(recording)

    @api.onchange('recording_data')
    def _onchange_recording_data(self):
        """Parse recording data from JSON."""
        if not self.recording_data:
            return

        try:
            data = json.loads(self.recording_data)
            steps = self._convert_frames_to_steps(data.get('frames', []))

            self.preview_steps = json.dumps(steps, indent=2)
            if not self.name:
                self.name = self._derive_skill_name(steps)
            if not self.technical_name:
                self.technical_name = self._to_technical_name(self.name)

            # Infer triggers from user inputs
            triggers = self._infer_triggers_from_recording(data)
            self.preview_triggers = json.dumps(triggers, indent=2)

        except json.JSONDecodeError as e:
            raise UserError(f"Invalid recording data: {e}")

    @api.onchange('skill_description')
    def _onchange_skill_description(self):
        """Generate preview from description."""
        if not self.skill_description or len(self.skill_description) < 20:
            return

        # Extract skill name
        if not self.name:
            self.name = self._extract_skill_name(self.skill_description)

        # Generate technical name
        if self.name and not self.technical_name:
            self.technical_name = self._to_technical_name(self.name)

        # Generate preview triggers
        if not self.preview_triggers:
            name_lower = self.name.lower() if self.name else ''
            triggers = [
                name_lower,
                f"please {name_lower}",
                f"i need to {name_lower}",
                f"can you {name_lower}",
            ]
            if self.example_phrases:
                triggers.extend(
                    line.strip() for line in self.example_phrases.split('\n')
                    if line.strip()
                )
            self.preview_triggers = json.dumps(triggers[:10], indent=2)

    def action_generate_preview(self):
        """Generate full preview based on inputs."""
        self.ensure_one()

        if self.creation_method == 'recording':
            self._generate_preview_from_recording()
        elif self.creation_method == 'natural_language':
            self._generate_preview_from_description()

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'views': [[False, 'form']],
            'target': 'new',
        }

    def _generate_preview_from_recording(self):
        """Generate preview from recording source."""
        if self.recording_id:
            steps = []
            for action in self.recording_id.action_ids:
                step_data = action._to_step_data()
                if step_data:
                    steps.append(step_data)
            self.preview_steps = json.dumps(steps, indent=2)

        elif self.recording_data:
            try:
                data = json.loads(self.recording_data)
            except (json.JSONDecodeError, TypeError):
                raise UserError("Invalid recording data format. Please re-record.")
            steps = self._convert_frames_to_steps(data.get('frames', []))
            self.preview_steps = json.dumps(steps, indent=2)

    def _generate_preview_from_description(self):
        """Generate preview from natural language description."""
        if not self.skill_description:
            return

        # Basic step generation from description
        # In production, this would call Claude to generate proper steps
        steps = [{
            'name': f"Execute: {self.name or 'Skill'}",
            'step_type': 'ai_decision',
            'instructions': self.skill_description,
        }]

        if self.example_output:
            steps.append({
                'name': 'Confirm Result',
                'step_type': 'confirmation',
                'instructions': f"Expected outcome: {self.example_output}",
            })

        self.preview_steps = json.dumps(steps, indent=2)

        # Generate context schema from description
        context_schema = self._infer_context_schema(self.skill_description)
        self.preview_context_schema = json.dumps(context_schema, indent=2)

    def action_create_skill(self):
        """Create the skill from wizard data."""
        self.ensure_one()

        if not self.name:
            raise UserError("Please provide a skill name")

        if self.creation_method == 'recording':
            return self._create_from_recording()
        elif self.creation_method == 'natural_language':
            return self._create_from_description()
        else:
            return self._create_manual()

    def _create_from_recording(self):
        """Create skill from recorded workflow."""
        if self.recording_id:
            # Use recording model's conversion
            skill = self.recording_id.convert_to_skill(
                skill_name=self.name,
                category=self.category
            )
        elif self.recording_data:
            # Parse JSON recording data
            try:
                data = json.loads(self.recording_data)
            except (json.JSONDecodeError, TypeError):
                raise UserError("Invalid recording data format. Please re-record.")
            steps = self._convert_frames_to_steps(data.get('frames', []))
            triggers = self._infer_triggers_from_recording(data)

            skill = self._create_skill_with_steps(steps, triggers)
        else:
            raise UserError("No recording source specified")

        # Update skill with wizard options
        skill.write({
            'requires_confirmation': self.requires_confirmation,
            'auto_snapshot': self.auto_snapshot,
            'max_operations': self.max_operations,
            'state': 'active' if self.activate_immediately else 'draft',
        })

        return self._return_skill_action(skill)

    def _create_from_description(self):
        """Create skill from natural language description."""
        triggers = []
        if self.example_phrases:
            triggers = [
                line.strip() for line in self.example_phrases.split('\n')
                if line.strip()
            ]

        # Basic triggers from name
        name_lower = self.name.lower()
        triggers.extend([
            name_lower,
            f"please {name_lower}",
            f"i want to {name_lower}",
        ])

        # Parse context schema
        context_schema = None
        if self.preview_context_schema:
            try:
                context_schema = json.loads(self.preview_context_schema)
            except json.JSONDecodeError:
                pass

        if not context_schema:
            context_schema = self._infer_context_schema(self.skill_description)

        # Create skill
        skill = self.env['loomworks.skill'].create({
            'name': self.name,
            'technical_name': self.technical_name or self._to_technical_name(self.name),
            'category': self.category,
            'description': self.description or self.skill_description,
            'trigger_phrases': json.dumps(list(set(triggers))[:10]),
            'context_schema': json.dumps(context_schema) if context_schema else None,
            'system_prompt': self.skill_description,
            'requires_confirmation': self.requires_confirmation,
            'auto_snapshot': self.auto_snapshot,
            'max_operations': self.max_operations,
            'state': 'active' if self.activate_immediately else 'draft',
        })

        # Create AI decision step as placeholder
        self.env['loomworks.skill.step'].create({
            'skill_id': skill.id,
            'name': f"Execute {self.name}",
            'sequence': 10,
            'step_type': 'ai_decision',
            'instructions': self.skill_description,
        })

        return self._return_skill_action(skill)

    def _create_manual(self):
        """Create empty skill for manual configuration."""
        skill = self.env['loomworks.skill'].create({
            'name': self.name or 'New Skill',
            'technical_name': self.technical_name or self._to_technical_name(self.name or 'new-skill'),
            'category': self.category,
            'description': self.description,
            'requires_confirmation': self.requires_confirmation,
            'auto_snapshot': self.auto_snapshot,
            'max_operations': self.max_operations,
            'state': 'draft',
        })

        return self._return_skill_action(skill)

    def _create_skill_with_steps(self, steps, triggers):
        """
        Create skill with given steps and triggers.

        :param steps: List of step data dicts
        :param triggers: List of trigger phrases
        :return: Created skill record
        """
        skill = self.env['loomworks.skill'].create({
            'name': self.name,
            'technical_name': self.technical_name or self._to_technical_name(self.name),
            'category': self.category,
            'description': self.description,
            'trigger_phrases': json.dumps(triggers),
            'state': 'draft',
        })

        for seq, step_data in enumerate(steps):
            self.env['loomworks.skill.step'].create({
                'skill_id': skill.id,
                'sequence': (seq + 1) * 10,
                **step_data,
            })

        return skill

    def _return_skill_action(self, skill):
        """Return action to open created skill."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'loomworks.skill',
            'res_id': skill.id,
            'views': [[False, 'form']],
            'target': 'current',
        }

    def _convert_frames_to_steps(self, frames):
        """
        Convert recording frames to step definitions.

        :param frames: List of frame dicts from recorder
        :return: List of step data dicts
        """
        steps = []

        for frame in frames:
            frame_type = frame.get('type')

            if frame_type == 'rpc':
                method = frame.get('method')
                model = frame.get('model')
                params = frame.get('params', {})

                if method == 'create':
                    steps.append({
                        'name': f"Create {model or 'record'}",
                        'step_type': 'tool_call',
                        'tool_name': 'create_record',
                        'tool_parameters': json.dumps({
                            'model': model,
                            'values': params.get('values', {}),
                        }),
                    })
                elif method == 'write':
                    steps.append({
                        'name': f"Update {model or 'record'}",
                        'step_type': 'tool_call',
                        'tool_name': 'update_record',
                        'tool_parameters': json.dumps({
                            'model': model,
                        }),
                    })
                elif method in ('search_read', 'search'):
                    steps.append({
                        'name': f"Search {model or 'records'}",
                        'step_type': 'tool_call',
                        'tool_name': 'search_records',
                        'tool_parameters': json.dumps({
                            'model': model,
                            'domain': params.get('domain', []),
                        }),
                    })

            elif frame_type == 'action':
                action = frame.get('action', {})
                steps.append({
                    'name': f"Navigate to {action.get('resModel', 'view')}",
                    'step_type': 'action',
                    'instructions': f"Open {action.get('resModel', 'view')}",
                })

        return steps

    def _derive_name_from_recording(self, recording):
        """Derive skill name from recording."""
        if recording.action_ids:
            for action in recording.action_ids:
                if action.action_type in ('rpc_create', 'rpc_write'):
                    model = action.model_name
                    if model:
                        model_display = model.replace('.', ' ').title()
                        verb = 'Create' if action.action_type == 'rpc_create' else 'Update'
                        return f"{verb} {model_display}"

        return f"Recorded Workflow {recording.id}"

    def _derive_skill_name(self, steps):
        """Derive skill name from steps."""
        if not steps:
            return "New Skill"

        for step in steps:
            params = step.get('tool_parameters', '{}')
            if isinstance(params, str):
                try:
                    params = json.loads(params)
                except json.JSONDecodeError:
                    params = {}

            model = params.get('model', '')
            tool_name = step.get('tool_name', '')

            if model:
                model_display = model.replace('.', ' ').title()
                if 'create' in tool_name:
                    return f"Create {model_display}"
                elif 'update' in tool_name:
                    return f"Update {model_display}"

        return "Recorded Workflow"

    def _to_technical_name(self, name):
        """Convert display name to technical name."""
        if not name:
            return 'new-skill'
        technical = re.sub(r'[^a-z0-9]+', '-', name.lower())
        return technical.strip('-')

    def _infer_triggers_from_recording(self, data):
        """Infer trigger phrases from recording data."""
        triggers = []

        # From user inputs in recording
        for user_input in data.get('userInputs', []):
            value = user_input.get('value', '')
            if value and len(value) > 5:
                triggers.append(value.lower())

        # From derived name
        if self.name:
            name_lower = self.name.lower()
            triggers.extend([
                name_lower,
                f"please {name_lower}",
                f"i want to {name_lower}",
            ])

        return list(set(triggers))[:10]

    def _extract_skill_name(self, description):
        """Extract skill name from description."""
        # Take first sentence or first few words
        first_sentence = description.split('.')[0].strip()
        words = first_sentence.split()[:5]
        return ' '.join(words).title()

    def _infer_context_schema(self, description):
        """
        Infer context schema from description.

        :param description: Skill description
        :return: JSON Schema dict
        """
        schema = {
            'type': 'object',
            'properties': {},
            'required': [],
        }

        # Look for common parameter patterns
        patterns = [
            (r'customer\s+name|client|company', 'customer_name', 'string', ['for', 'customer', 'client']),
            (r'product\s*(?:name)?|item', 'product_name', 'string', ['product', 'item', 'for']),
            (r'quantity|amount|number\s+of', 'quantity', 'number', ['quantity', 'amount']),
            (r'price|cost|amount', 'price', 'number', ['price', 'cost', 'at']),
            (r'date|when|by', 'date', 'string', ['date', 'by', 'on']),
            (r'email', 'email', 'string', ['email', 'mail']),
            (r'phone|tel', 'phone', 'string', ['phone', 'tel', 'call']),
        ]

        description_lower = description.lower()

        for pattern, name, param_type, hints in patterns:
            if re.search(pattern, description_lower):
                schema['properties'][name] = {
                    'type': param_type,
                    'extraction_hints': hints,
                }

        return schema
