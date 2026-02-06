# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Skill Tool Provider - AI Tools for Skill Operations

This module registers AI tools for skill-related operations:
- skill_execute: Execute a skill by name
- skill_list: List available skills
- skill_create: Create new skill from description
- skill_record_start: Start recording user actions
- skill_record_stop: Stop recording and convert to skill
- skill_suggest: Suggest relevant skills for context

These tools enable the AI assistant to work with skills programmatically.
"""

from loomworks import api, models
import json
import logging

_logger = logging.getLogger(__name__)


class SkillToolProvider(models.AbstractModel):
    """
    AI Tool Provider for skill operations.

    Inherits from the loomworks.ai.tool.provider mixin to register
    skill-related tools that can be invoked by AI agents.
    """
    _name = 'loomworks.skill.tool.provider'
    _inherit = 'loomworks.ai.tool.provider'
    _description = 'Skill AI Tool Provider'

    @api.model
    def _get_tool_definitions(self):
        """
        Return tool definitions for skill operations.

        Returns:
            list: Tool definition dicts
        """
        return [
            {
                'name': 'Execute Skill',
                'technical_name': 'skill_execute',
                'category': 'action',
                'description': (
                    'Execute a skill by its technical name. Skills are pre-defined '
                    'workflows that automate common ERP tasks. Provide the skill '
                    'technical name and any required context parameters.'
                ),
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'skill_name': {
                            'type': 'string',
                            'description': 'Technical name of the skill to execute (e.g., "create-sales-quote")',
                        },
                        'context': {
                            'type': 'object',
                            'description': 'Context parameters for the skill execution',
                            'additionalProperties': True,
                        },
                    },
                    'required': ['skill_name'],
                },
                'implementation_method': 'loomworks_skills.models.skill_tool_provider.execute_skill',
                'risk_level': 'moderate',
                'requires_confirmation': True,
                'returns_description': 'Skill execution result with created/modified records',
            },
            {
                'name': 'List Skills',
                'technical_name': 'skill_list',
                'category': 'data',
                'description': (
                    'List available skills that can be executed. Optionally filter '
                    'by category or search by name/description.'
                ),
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'category': {
                            'type': 'string',
                            'description': 'Filter by category (sales, purchase, inventory, accounting, hr, project, custom)',
                            'enum': ['sales', 'purchase', 'inventory', 'accounting', 'hr', 'manufacturing', 'crm', 'project', 'custom'],
                        },
                        'search': {
                            'type': 'string',
                            'description': 'Search term for skill name or description',
                        },
                        'include_triggers': {
                            'type': 'boolean',
                            'description': 'Include trigger phrases in results',
                            'default': False,
                        },
                    },
                },
                'implementation_method': 'loomworks_skills.models.skill_tool_provider.list_skills',
                'risk_level': 'safe',
                'returns_description': 'List of available skills with their names, categories, and descriptions',
            },
            {
                'name': 'Create Skill',
                'technical_name': 'skill_create',
                'category': 'action',
                'description': (
                    'Create a new skill from a natural language description. '
                    'Provide a name, description of what the skill should do, '
                    'and example trigger phrases.'
                ),
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'name': {
                            'type': 'string',
                            'description': 'Display name for the skill',
                        },
                        'description': {
                            'type': 'string',
                            'description': 'What this skill should do',
                        },
                        'category': {
                            'type': 'string',
                            'description': 'Skill category',
                            'enum': ['sales', 'purchase', 'inventory', 'accounting', 'hr', 'manufacturing', 'crm', 'project', 'custom'],
                            'default': 'custom',
                        },
                        'trigger_phrases': {
                            'type': 'array',
                            'items': {'type': 'string'},
                            'description': 'Phrases that should trigger this skill',
                        },
                    },
                    'required': ['name', 'description'],
                },
                'implementation_method': 'loomworks_skills.models.skill_tool_provider.create_skill',
                'risk_level': 'moderate',
                'returns_description': 'Created skill details',
            },
            {
                'name': 'Start Skill Recording',
                'technical_name': 'skill_record_start',
                'category': 'action',
                'description': (
                    'Start recording user actions to create a new skill. '
                    'The recording captures RPC calls, navigation, and user inputs '
                    'that can be converted into a reusable skill.'
                ),
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'name': {
                            'type': 'string',
                            'description': 'Name for the recording session',
                        },
                    },
                },
                'implementation_method': 'loomworks_skills.models.skill_tool_provider.start_recording',
                'risk_level': 'safe',
                'returns_description': 'Recording session ID',
            },
            {
                'name': 'Stop Skill Recording',
                'technical_name': 'skill_record_stop',
                'category': 'action',
                'description': (
                    'Stop an active recording session and optionally convert it to a skill.'
                ),
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'recording_id': {
                            'type': 'integer',
                            'description': 'ID of the recording to stop (optional, uses current user\'s active recording if not specified)',
                        },
                        'convert_to_skill': {
                            'type': 'boolean',
                            'description': 'Whether to automatically convert recording to a skill',
                            'default': False,
                        },
                        'skill_name': {
                            'type': 'string',
                            'description': 'Name for the created skill (if converting)',
                        },
                    },
                },
                'implementation_method': 'loomworks_skills.models.skill_tool_provider.stop_recording',
                'risk_level': 'safe',
                'returns_description': 'Recording summary and optionally created skill',
            },
            {
                'name': 'Suggest Skills',
                'technical_name': 'skill_suggest',
                'category': 'data',
                'description': (
                    'Suggest relevant skills based on user input or current context. '
                    'Uses intent matching to find skills that could help with the task.'
                ),
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'user_input': {
                            'type': 'string',
                            'description': 'User\'s request or description of what they want to do',
                        },
                        'model': {
                            'type': 'string',
                            'description': 'Current model context (e.g., "sale.order")',
                        },
                        'limit': {
                            'type': 'integer',
                            'description': 'Maximum number of suggestions',
                            'default': 5,
                        },
                    },
                    'required': ['user_input'],
                },
                'implementation_method': 'loomworks_skills.models.skill_tool_provider.suggest_skills',
                'risk_level': 'safe',
                'returns_description': 'List of suggested skills with relevance scores',
            },
        ]


# Tool implementation functions
# These are called by the MCP tool executor

def execute_skill(env, params):
    """
    Execute a skill by technical name.

    :param env: Odoo environment
    :param params: Dict with skill_name and context
    :return: Execution result dict
    """
    skill_name = params.get('skill_name')
    context = params.get('context', {})

    if not skill_name:
        return {'error': 'skill_name is required'}

    # Find skill
    skill = env['loomworks.skill'].search([
        ('technical_name', '=', skill_name),
        ('state', '=', 'active'),
    ], limit=1)

    if not skill:
        return {'error': f"Skill '{skill_name}' not found or not active"}

    try:
        result = skill.action_execute(context=context)
        return {
            'success': True,
            'skill': skill.name,
            'result': result,
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
        }


def list_skills(env, params):
    """
    List available skills.

    :param env: Odoo environment
    :param params: Dict with optional category, search, include_triggers
    :return: List of skill info dicts
    """
    domain = [('state', '=', 'active')]

    category = params.get('category')
    if category:
        domain.append(('category', '=', category))

    search_term = params.get('search')
    if search_term:
        domain.extend([
            '|',
            ('name', 'ilike', search_term),
            ('description', 'ilike', search_term),
        ])

    skills = env['loomworks.skill'].search(domain, limit=50)

    include_triggers = params.get('include_triggers', False)

    result = []
    for skill in skills:
        info = {
            'id': skill.id,
            'technical_name': skill.technical_name,
            'name': skill.name,
            'category': skill.category,
            'description': skill.description or '',
            'success_rate': skill.success_rate,
        }
        if include_triggers:
            info['trigger_phrases'] = skill.get_trigger_phrases()
        result.append(info)

    return result


def create_skill(env, params):
    """
    Create a new skill from description.

    :param env: Odoo environment
    :param params: Dict with name, description, category, trigger_phrases
    :return: Created skill info
    """
    name = params.get('name')
    description = params.get('description')
    category = params.get('category', 'custom')
    trigger_phrases = params.get('trigger_phrases', [])

    if not name or not description:
        return {'error': 'name and description are required'}

    # Generate technical name
    import re
    technical_name = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

    # Add default triggers
    if not trigger_phrases:
        name_lower = name.lower()
        trigger_phrases = [
            name_lower,
            f"please {name_lower}",
            f"i want to {name_lower}",
        ]

    try:
        skill = env['loomworks.skill'].create({
            'name': name,
            'technical_name': technical_name,
            'category': category,
            'description': description,
            'trigger_phrases': json.dumps(trigger_phrases),
            'system_prompt': description,
            'state': 'draft',
        })

        # Create AI decision step
        env['loomworks.skill.step'].create({
            'skill_id': skill.id,
            'name': f"Execute {name}",
            'sequence': 10,
            'step_type': 'ai_decision',
            'instructions': description,
        })

        return {
            'success': True,
            'skill_id': skill.id,
            'technical_name': skill.technical_name,
            'name': skill.name,
            'state': 'draft',
            'message': 'Skill created in draft state. Review and activate when ready.',
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
        }


def start_recording(env, params):
    """
    Start a recording session.

    :param env: Odoo environment
    :param params: Dict with optional name
    :return: Recording session info
    """
    name = params.get('name')

    try:
        recording = env['loomworks.skill.recording'].start_recording({
            'name': name,
        })

        return {
            'success': True,
            'recording_id': recording.id,
            'name': recording.name,
            'message': 'Recording started. Perform your workflow actions, then stop recording.',
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
        }


def stop_recording(env, params):
    """
    Stop a recording session.

    :param env: Odoo environment
    :param params: Dict with optional recording_id, convert_to_skill, skill_name
    :return: Recording summary and optional skill info
    """
    recording_id = params.get('recording_id')
    convert_to_skill = params.get('convert_to_skill', False)
    skill_name = params.get('skill_name')

    # Find recording
    if recording_id:
        recording = env['loomworks.skill.recording'].browse(recording_id)
    else:
        recording = env['loomworks.skill.recording'].search([
            ('user_id', '=', env.uid),
            ('state', '=', 'recording'),
        ], limit=1)

    if not recording:
        return {'error': 'No active recording found'}

    try:
        recording.stop_recording()

        result = {
            'success': True,
            'recording_id': recording.id,
            'action_count': recording.action_count,
            'duration_seconds': recording.duration_seconds,
        }

        if convert_to_skill:
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
        return {
            'success': False,
            'error': str(e),
        }


def suggest_skills(env, params):
    """
    Suggest relevant skills for user input.

    :param env: Odoo environment
    :param params: Dict with user_input, optional model, limit
    :return: List of suggested skills
    """
    user_input = params.get('user_input')
    model = params.get('model')
    limit = params.get('limit', 5)

    if not user_input:
        return {'error': 'user_input is required'}

    # Build domain
    domain = None
    if model:
        model_rec = env['ir.model'].search([('model', '=', model)], limit=1)
        if model_rec:
            domain = [('trigger_model_ids', 'in', model_rec.id)]

    # Use matching service
    from ..services.skill_matching_service import SkillMatchingService
    service = SkillMatchingService(env)
    result = service.match_skill(user_input, domain)

    suggestions = result.get('suggestions', [])

    # Include best match if confidence is reasonable
    if result.get('skill_id') and result.get('confidence', 0) >= 0.5:
        best_skill = env['loomworks.skill'].browse(result['skill_id'])
        suggestions.insert(0, {
            'skill_id': best_skill.id,
            'skill_name': best_skill.name,
            'technical_name': best_skill.technical_name,
            'category': best_skill.category,
            'confidence': result['confidence'],
            'params': result.get('params', {}),
        })

    return suggestions[:limit]
