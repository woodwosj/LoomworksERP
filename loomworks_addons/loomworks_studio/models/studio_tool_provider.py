# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Studio AI Tool Provider - Implements M4 pattern for AI tool registration.

This provider registers Studio-specific tools that allow AI agents to:
- Create and manage Studio apps
- Add fields to models
- Customize views
- Create automations
"""

import json
import logging

from loomworks import api, models

_logger = logging.getLogger(__name__)


class StudioToolProvider(models.AbstractModel):
    """
    AI Tool Provider for Loomworks Studio.

    Provides tools for AI-assisted no-code development:
    - studio_create_app: Create new custom applications
    - studio_add_field: Add fields to models
    - studio_customize_view: Modify view layouts
    - studio_create_automation: Define workflow rules
    - studio_list_apps: List existing Studio apps
    - studio_get_model_fields: Get fields for a model
    """
    _name = 'loomworks.studio.tool.provider'
    _inherit = 'loomworks.ai.tool.provider'
    _description = 'Studio AI Tool Provider'

    @api.model
    def _get_tool_definitions(self):
        """Return Studio tool definitions for AI registration."""
        return [
            # App Management
            {
                'name': 'Create Studio App',
                'technical_name': 'studio_create_app',
                'category': 'action',
                'description': (
                    'Create a new custom application in Loomworks Studio. '
                    'Use this to create a container for related models, menus, and views. '
                    'The technical_name will be used as a prefix for all models in the app.'
                ),
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'name': {
                            'type': 'string',
                            'description': 'Display name for the application'
                        },
                        'technical_name': {
                            'type': 'string',
                            'description': 'Technical name (lowercase, underscores only)'
                        },
                        'description': {
                            'type': 'string',
                            'description': 'Description of what the app does'
                        },
                        'icon': {
                            'type': 'string',
                            'description': 'FontAwesome icon class (e.g., fa-users)',
                            'default': 'fa-cube'
                        },
                    },
                    'required': ['name', 'technical_name']
                },
                'implementation_method': 'loomworks_studio.tool_provider._execute_create_app',
                'risk_level': 'moderate',
                'requires_confirmation': True,
                'returns_description': 'Created app ID and details',
            },
            # Model/Field Management
            {
                'name': 'Create Model in App',
                'technical_name': 'studio_create_model',
                'category': 'action',
                'description': (
                    'Create a new model (database table) within a Studio app. '
                    'Models store data and can have fields, views, and automations.'
                ),
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'app_id': {
                            'type': 'integer',
                            'description': 'ID of the Studio app'
                        },
                        'name': {
                            'type': 'string',
                            'description': 'Display name for the model'
                        },
                        'model_name': {
                            'type': 'string',
                            'description': 'Technical model suffix (will be prefixed with app name)'
                        },
                        'fields': {
                            'type': 'array',
                            'description': 'List of field definitions',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'name': {'type': 'string'},
                                    'type': {'type': 'string'},
                                    'label': {'type': 'string'},
                                    'required': {'type': 'boolean'},
                                }
                            }
                        },
                        'create_menu': {
                            'type': 'boolean',
                            'description': 'Create menu item for this model',
                            'default': True
                        },
                    },
                    'required': ['app_id', 'name']
                },
                'implementation_method': 'loomworks_studio.tool_provider._execute_create_model',
                'risk_level': 'moderate',
                'requires_confirmation': True,
                'returns_description': 'Created model technical name and ID',
            },
            {
                'name': 'Add Field to Model',
                'technical_name': 'studio_add_field',
                'category': 'action',
                'description': (
                    'Add a new field to an existing model. '
                    'Supported types: char, text, integer, float, boolean, date, '
                    'datetime, selection, many2one, one2many, many2many, binary, html.'
                ),
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'model': {
                            'type': 'string',
                            'description': 'Technical model name (e.g., x_myapp_contacts)'
                        },
                        'field_name': {
                            'type': 'string',
                            'description': 'Field name (will be prefixed with x_)'
                        },
                        'field_type': {
                            'type': 'string',
                            'enum': ['char', 'text', 'integer', 'float', 'boolean',
                                    'date', 'datetime', 'selection', 'many2one',
                                    'one2many', 'many2many', 'binary', 'html', 'monetary'],
                            'description': 'Type of field'
                        },
                        'label': {
                            'type': 'string',
                            'description': 'Display label for the field'
                        },
                        'required': {
                            'type': 'boolean',
                            'default': False
                        },
                        'help': {
                            'type': 'string',
                            'description': 'Help text shown on hover'
                        },
                        'selection': {
                            'type': 'array',
                            'description': 'For selection fields: list of [value, label] pairs',
                            'items': {
                                'type': 'array',
                                'items': {'type': 'string'}
                            }
                        },
                        'relation': {
                            'type': 'string',
                            'description': 'For relational fields: target model name'
                        },
                    },
                    'required': ['model', 'field_name', 'field_type', 'label']
                },
                'implementation_method': 'loomworks_studio.tool_provider._execute_add_field',
                'risk_level': 'moderate',
                'requires_confirmation': True,
                'returns_description': 'Created field name and ID',
            },
            # View Customization
            {
                'name': 'Customize View',
                'technical_name': 'studio_customize_view',
                'category': 'action',
                'description': (
                    'Modify the layout of a view (form, list, kanban). '
                    'Add or remove fields, change field order, or update field attributes.'
                ),
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'model': {
                            'type': 'string',
                            'description': 'Model technical name'
                        },
                        'view_type': {
                            'type': 'string',
                            'enum': ['form', 'list', 'kanban', 'search'],
                            'description': 'Type of view to customize'
                        },
                        'action': {
                            'type': 'string',
                            'enum': ['add_field', 'remove_field', 'reorder_fields', 'update_field'],
                            'description': 'Type of customization'
                        },
                        'field_name': {
                            'type': 'string',
                            'description': 'Field to act on'
                        },
                        'field_order': {
                            'type': 'array',
                            'items': {'type': 'string'},
                            'description': 'For reorder: list of field names in order'
                        },
                        'attributes': {
                            'type': 'object',
                            'description': 'For update_field: attributes to change'
                        },
                    },
                    'required': ['model', 'view_type', 'action']
                },
                'implementation_method': 'loomworks_studio.tool_provider._execute_customize_view',
                'risk_level': 'moderate',
                'requires_confirmation': False,
                'returns_description': 'View customization status',
            },
            # Automation
            {
                'name': 'Create Automation',
                'technical_name': 'studio_create_automation',
                'category': 'action',
                'description': (
                    'Create a workflow automation rule. Automations can trigger '
                    'on record creation, update, deletion, or time conditions, '
                    'and can update records, send emails, or execute code.'
                ),
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'name': {
                            'type': 'string',
                            'description': 'Name for the automation'
                        },
                        'app_id': {
                            'type': 'integer',
                            'description': 'Studio app ID (optional)'
                        },
                        'model': {
                            'type': 'string',
                            'description': 'Model to attach automation to'
                        },
                        'trigger_type': {
                            'type': 'string',
                            'enum': ['on_create', 'on_write', 'on_create_or_write',
                                    'on_unlink', 'on_time'],
                            'description': 'When to trigger'
                        },
                        'filter_domain': {
                            'type': 'string',
                            'description': 'Domain to filter records (default: [])'
                        },
                        'action_type': {
                            'type': 'string',
                            'enum': ['update_record', 'send_email', 'create_activity',
                                    'python_code'],
                            'description': 'What action to perform'
                        },
                        'python_code': {
                            'type': 'string',
                            'description': 'For python_code action: code to execute'
                        },
                        'email_template_id': {
                            'type': 'integer',
                            'description': 'For send_email: template ID'
                        },
                    },
                    'required': ['name', 'model', 'trigger_type', 'action_type']
                },
                'implementation_method': 'loomworks_studio.tool_provider._execute_create_automation',
                'risk_level': 'high',
                'requires_confirmation': True,
                'returns_description': 'Created automation ID',
            },
            # Read Operations
            {
                'name': 'List Studio Apps',
                'technical_name': 'studio_list_apps',
                'category': 'data',
                'description': 'List all Studio applications with their models and status.',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'include_archived': {
                            'type': 'boolean',
                            'default': False
                        },
                    },
                },
                'implementation_method': 'loomworks_studio.tool_provider._execute_list_apps',
                'risk_level': 'safe',
                'returns_description': 'List of apps with details',
            },
            {
                'name': 'Get Model Fields',
                'technical_name': 'studio_get_model_fields',
                'category': 'data',
                'description': 'Get all fields defined on a model, including custom fields.',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'model': {
                            'type': 'string',
                            'description': 'Model technical name'
                        },
                        'include_system': {
                            'type': 'boolean',
                            'description': 'Include system fields (id, create_date, etc.)',
                            'default': False
                        },
                    },
                    'required': ['model']
                },
                'implementation_method': 'loomworks_studio.tool_provider._execute_get_model_fields',
                'risk_level': 'safe',
                'returns_description': 'List of field definitions',
            },
        ]

    # ---------------------------------
    # Tool Implementation Methods
    # ---------------------------------

    @api.model
    def _execute_create_app(self, params):
        """Create a new Studio application."""
        StudioApp = self.env['studio.app']

        app = StudioApp.create({
            'name': params['name'],
            'technical_name': params['technical_name'],
            'description': params.get('description', ''),
            'icon': params.get('icon', 'fa-cube'),
        })

        return {
            'success': True,
            'app_id': app.id,
            'name': app.name,
            'technical_name': app.technical_name,
            'message': f"Created Studio app '{app.name}' (ID: {app.id})"
        }

    @api.model
    def _execute_create_model(self, params):
        """Create a model within a Studio app."""
        StudioApp = self.env['studio.app']

        app = StudioApp.browse(params['app_id'])
        if not app.exists():
            return {'success': False, 'error': f"App ID {params['app_id']} not found"}

        model = app.action_create_model({
            'name': params['name'],
            'model': params.get('model_name', ''),
            'fields': params.get('fields', []),
            'create_menu': params.get('create_menu', True),
        })

        return {
            'success': True,
            'model_id': model.id,
            'model_name': model.model,
            'message': f"Created model '{model.model}' in app '{app.name}'"
        }

    @api.model
    def _execute_add_field(self, params):
        """Add a field to an existing model."""
        model_name = params['model']

        # Find the model
        ir_model = self.env['ir.model'].search([
            ('model', '=', model_name)
        ], limit=1)

        if not ir_model:
            return {'success': False, 'error': f"Model '{model_name}' not found"}

        # Prepare field name
        field_name = params['field_name']
        if not field_name.startswith('x_'):
            field_name = f"x_{field_name}"

        # Check if field already exists
        existing = self.env['ir.model.fields'].search([
            ('model_id', '=', ir_model.id),
            ('name', '=', field_name),
        ])
        if existing:
            return {'success': False, 'error': f"Field '{field_name}' already exists"}

        # Create field
        field_vals = {
            'model_id': ir_model.id,
            'name': field_name,
            'field_description': params['label'],
            'ttype': params['field_type'],
            'state': 'manual',
            'required': params.get('required', False),
            'help': params.get('help', ''),
        }

        # Handle selection
        if params['field_type'] == 'selection' and params.get('selection'):
            field_vals['selection_ids'] = [
                (0, 0, {'value': s[0], 'name': s[1], 'sequence': i * 10})
                for i, s in enumerate(params['selection'])
            ]

        # Handle relational fields
        if params['field_type'] in ('many2one', 'many2many', 'one2many'):
            if not params.get('relation'):
                return {'success': False, 'error': "Relational fields require 'relation' parameter"}
            field_vals['relation'] = params['relation']

        field = self.env['ir.model.fields'].sudo().create(field_vals)

        return {
            'success': True,
            'field_id': field.id,
            'field_name': field.name,
            'message': f"Added field '{field.name}' to model '{model_name}'"
        }

    @api.model
    def _execute_customize_view(self, params):
        """Customize a view."""
        ViewCustomization = self.env['studio.view.customization']

        model = params['model']
        view_type = params['view_type']
        action = params['action']

        customization = ViewCustomization._get_or_create_customization(model, view_type)

        if action == 'add_field':
            field = self.env['ir.model.fields'].search([
                ('model', '=', model),
                ('name', '=', params['field_name']),
            ], limit=1)
            if not field:
                return {'success': False, 'error': f"Field '{params['field_name']}' not found"}
            customization.add_field_to_view(field.id)
            message = f"Added field '{params['field_name']}' to {view_type} view"

        elif action == 'remove_field':
            customization.remove_field_from_view(params['field_name'])
            message = f"Removed field '{params['field_name']}' from {view_type} view"

        elif action == 'reorder_fields':
            customization.reorder_fields(params['field_order'])
            message = f"Reordered fields in {view_type} view"

        elif action == 'update_field':
            customization.update_field_attributes(
                params['field_name'],
                params.get('attributes', {})
            )
            message = f"Updated field '{params['field_name']}' attributes"

        else:
            return {'success': False, 'error': f"Unknown action: {action}"}

        return {
            'success': True,
            'customization_id': customization.id,
            'message': message
        }

    @api.model
    def _execute_create_automation(self, params):
        """Create a workflow automation."""
        Automation = self.env['studio.automation']

        # Find model
        ir_model = self.env['ir.model'].search([
            ('model', '=', params['model'])
        ], limit=1)

        if not ir_model:
            return {'success': False, 'error': f"Model '{params['model']}' not found"}

        automation_vals = {
            'name': params['name'],
            'model_id': ir_model.id,
            'trigger_type': params['trigger_type'],
            'action_type': params['action_type'],
            'filter_domain': params.get('filter_domain', '[]'),
        }

        if params.get('app_id'):
            automation_vals['app_id'] = params['app_id']

        if params.get('python_code'):
            automation_vals['python_code'] = params['python_code']

        if params.get('email_template_id'):
            automation_vals['email_template_id'] = params['email_template_id']

        automation = Automation.create(automation_vals)

        return {
            'success': True,
            'automation_id': automation.id,
            'name': automation.name,
            'message': f"Created automation '{automation.name}'"
        }

    @api.model
    def _execute_list_apps(self, params):
        """List all Studio applications."""
        StudioApp = self.env['studio.app']

        domain = []
        if not params.get('include_archived'):
            domain.append(('active', '=', True))

        apps = StudioApp.search(domain)

        result = []
        for app in apps:
            result.append({
                'id': app.id,
                'name': app.name,
                'technical_name': app.technical_name,
                'state': app.state,
                'model_count': app.model_count,
                'record_count': app.record_count,
                'automation_count': app.automation_count,
                'icon': app.icon,
                'models': [
                    {'name': m.name, 'model': m.model}
                    for m in app.model_ids
                ],
            })

        return {
            'success': True,
            'apps': result,
            'count': len(result),
        }

    @api.model
    def _execute_get_model_fields(self, params):
        """Get fields for a model."""
        model_name = params['model']

        ir_model = self.env['ir.model'].search([
            ('model', '=', model_name)
        ], limit=1)

        if not ir_model:
            return {'success': False, 'error': f"Model '{model_name}' not found"}

        # Get fields
        domain = [('model_id', '=', ir_model.id)]
        if not params.get('include_system'):
            # Filter out common system fields
            domain.append(('name', 'not in', [
                'id', 'create_uid', 'create_date', 'write_uid', 'write_date',
                '__last_update', 'display_name'
            ]))

        fields = self.env['ir.model.fields'].search(domain, order='name')

        result = []
        for field in fields:
            result.append({
                'name': field.name,
                'label': field.field_description,
                'type': field.ttype,
                'required': field.required,
                'readonly': field.readonly,
                'state': field.state,  # 'base' or 'manual'
                'relation': field.relation,
                'help': field.help,
            })

        return {
            'success': True,
            'model': model_name,
            'fields': result,
            'count': len(result),
        }
