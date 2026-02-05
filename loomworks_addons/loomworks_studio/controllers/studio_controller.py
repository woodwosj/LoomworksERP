# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Studio REST Controller - HTTP endpoints for Studio operations.

Provides JSON-RPC endpoints for the Studio frontend components.
"""

import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class StudioController(http.Controller):
    """HTTP Controller for Studio operations."""

    @http.route('/loomworks_studio/get_model_info', type='json', auth='user')
    def get_model_info(self, model_name):
        """
        Get detailed information about a model for Studio editing.

        Args:
            model_name: Technical model name

        Returns:
            dict: Model info including fields, views, and customizations
        """
        IrModel = request.env['ir.model']
        IrModelFields = request.env['ir.model.fields']
        IrUIView = request.env['ir.ui.view']

        model = IrModel.search([('model', '=', model_name)], limit=1)
        if not model:
            return {'error': f"Model '{model_name}' not found"}

        # Get fields
        fields = IrModelFields.search([
            ('model_id', '=', model.id)
        ], order='name')

        field_data = []
        for field in fields:
            field_data.append({
                'id': field.id,
                'name': field.name,
                'label': field.field_description,
                'type': field.ttype,
                'required': field.required,
                'readonly': field.readonly,
                'state': field.state,
                'relation': field.relation,
                'help': field.help,
            })

        # Get views
        views = IrUIView.search([
            ('model', '=', model_name),
            ('type', 'in', ['form', 'list', 'kanban', 'search']),
        ])

        view_data = []
        for view in views:
            view_data.append({
                'id': view.id,
                'name': view.name,
                'type': view.type,
                'priority': view.priority,
                'studio_customized': view.studio_customized,
            })

        return {
            'model': {
                'id': model.id,
                'name': model.name,
                'model': model.model,
                'state': model.state,
                'studio_origin': model.studio_origin,
                'studio_app_id': model.studio_app_id.id if model.studio_app_id else None,
            },
            'fields': field_data,
            'views': view_data,
        }

    @http.route('/loomworks_studio/get_view_arch', type='json', auth='user')
    def get_view_arch(self, model, view_type):
        """
        Get the current view architecture for a model/view_type combination.

        Args:
            model: Model name
            view_type: View type (form, list, kanban, etc.)

        Returns:
            dict: View ID and architecture
        """
        View = request.env['ir.ui.view']

        # Get the combined view
        view_id, arch = View.get_view(
            view_id=False,
            view_type=view_type,
            model=model
        )

        return {
            'view_id': view_id,
            'arch': arch,
            'view_type': view_type,
            'model': model,
        }

    @http.route('/loomworks_studio/add_field', type='json', auth='user')
    def add_field(self, model, view_type, field_id, position='inside', after_field=None):
        """
        Add a field to a view via Studio.

        Args:
            model: Model name
            view_type: View type
            field_id: ID of ir.model.fields
            position: Insertion position
            after_field: Field name to insert after

        Returns:
            dict: Operation result
        """
        ViewCustomization = request.env['studio.view.customization']

        try:
            customization = ViewCustomization._get_or_create_customization(model, view_type)
            view_field = customization.add_field_to_view(field_id, position, after_field)

            return {
                'success': True,
                'customization_id': customization.id,
                'view_field_id': view_field.id,
            }
        except Exception as e:
            _logger.exception("Failed to add field to view")
            return {'success': False, 'error': str(e)}

    @http.route('/loomworks_studio/remove_field', type='json', auth='user')
    def remove_field(self, model, view_type, field_name):
        """
        Remove a field from a view.

        Args:
            model: Model name
            view_type: View type
            field_name: Field to remove

        Returns:
            dict: Operation result
        """
        ViewCustomization = request.env['studio.view.customization']

        try:
            customization = ViewCustomization.search([
                ('model_name', '=', model),
                ('view_type', '=', view_type),
                ('active', '=', True),
            ], limit=1)

            if customization:
                customization.remove_field_from_view(field_name)

            return {'success': True}
        except Exception as e:
            _logger.exception("Failed to remove field from view")
            return {'success': False, 'error': str(e)}

    @http.route('/loomworks_studio/reorder_fields', type='json', auth='user')
    def reorder_fields(self, model, view_type, field_order):
        """
        Reorder fields in a view.

        Args:
            model: Model name
            view_type: View type
            field_order: List of field names in order

        Returns:
            dict: Operation result
        """
        ViewCustomization = request.env['studio.view.customization']

        try:
            customization = ViewCustomization.search([
                ('model_name', '=', model),
                ('view_type', '=', view_type),
                ('active', '=', True),
            ], limit=1)

            if customization:
                customization.reorder_fields(field_order)

            return {'success': True}
        except Exception as e:
            _logger.exception("Failed to reorder fields")
            return {'success': False, 'error': str(e)}

    @http.route('/loomworks_studio/create_field', type='json', auth='user')
    def create_field(self, model, field_data):
        """
        Create a new field on a model.

        Args:
            model: Model name
            field_data: Field definition dict

        Returns:
            dict: Created field info
        """
        IrModel = request.env['ir.model']
        IrModelFields = request.env['ir.model.fields']

        try:
            ir_model = IrModel.search([('model', '=', model)], limit=1)
            if not ir_model:
                return {'success': False, 'error': f"Model '{model}' not found"}

            # Prepare field name
            field_name = field_data.get('name', '')
            if not field_name.startswith('x_'):
                field_name = f"x_{field_name}"

            # Create field
            vals = {
                'model_id': ir_model.id,
                'name': field_name,
                'field_description': field_data.get('label', field_name),
                'ttype': field_data.get('type', 'char'),
                'state': 'manual',
                'required': field_data.get('required', False),
                'help': field_data.get('help', ''),
            }

            # Handle selection
            if vals['ttype'] == 'selection' and field_data.get('selection'):
                vals['selection_ids'] = [
                    (0, 0, {'value': s[0], 'name': s[1], 'sequence': i * 10})
                    for i, s in enumerate(field_data['selection'])
                ]

            # Handle relations
            if vals['ttype'] in ('many2one', 'many2many', 'one2many'):
                vals['relation'] = field_data.get('relation')

            field = IrModelFields.sudo().create(vals)

            return {
                'success': True,
                'field_id': field.id,
                'field_name': field.name,
            }
        except Exception as e:
            _logger.exception("Failed to create field")
            return {'success': False, 'error': str(e)}

    @http.route('/loomworks_studio/get_field_types', type='json', auth='user')
    def get_field_types(self):
        """
        Get available field types for the field palette.

        Returns:
            list: Field type definitions
        """
        return [
            {'type': 'char', 'label': 'Text', 'icon': 'fa-font',
             'description': 'Single line text'},
            {'type': 'text', 'label': 'Long Text', 'icon': 'fa-align-left',
             'description': 'Multi-line text'},
            {'type': 'html', 'label': 'Rich Text', 'icon': 'fa-code',
             'description': 'HTML formatted text'},
            {'type': 'integer', 'label': 'Integer', 'icon': 'fa-hashtag',
             'description': 'Whole numbers'},
            {'type': 'float', 'label': 'Decimal', 'icon': 'fa-percent',
             'description': 'Decimal numbers'},
            {'type': 'monetary', 'label': 'Monetary', 'icon': 'fa-dollar',
             'description': 'Currency values'},
            {'type': 'boolean', 'label': 'Checkbox', 'icon': 'fa-check-square',
             'description': 'Yes/No toggle'},
            {'type': 'date', 'label': 'Date', 'icon': 'fa-calendar',
             'description': 'Date picker'},
            {'type': 'datetime', 'label': 'Date & Time', 'icon': 'fa-clock-o',
             'description': 'Date and time'},
            {'type': 'selection', 'label': 'Dropdown', 'icon': 'fa-list',
             'description': 'Choose from options'},
            {'type': 'many2one', 'label': 'Link', 'icon': 'fa-link',
             'description': 'Link to another record'},
            {'type': 'one2many', 'label': 'Related List', 'icon': 'fa-list-ul',
             'description': 'List of related records'},
            {'type': 'many2many', 'label': 'Tags', 'icon': 'fa-tags',
             'description': 'Multiple links'},
            {'type': 'binary', 'label': 'File', 'icon': 'fa-file',
             'description': 'File attachment'},
            {'type': 'image', 'label': 'Image', 'icon': 'fa-image',
             'description': 'Image with preview'},
        ]

    @http.route('/loomworks_studio/export_app', type='http', auth='user')
    def export_app(self, app_id):
        """
        Export a Studio app as JSON file.

        Args:
            app_id: Studio app ID

        Returns:
            JSON file download
        """
        StudioApp = request.env['studio.app']
        app = StudioApp.browse(int(app_id))

        if not app.exists():
            return request.not_found()

        export_data = app._get_export_dict()
        content = json.dumps(export_data, indent=2)

        return request.make_response(
            content,
            headers=[
                ('Content-Type', 'application/json'),
                ('Content-Disposition', f'attachment; filename={app.technical_name}_export.json'),
            ]
        )

    @http.route('/loomworks_studio/import_app', type='json', auth='user')
    def import_app(self, json_data):
        """
        Import a Studio app from JSON data.

        Args:
            json_data: JSON string or dict

        Returns:
            dict: Import result
        """
        StudioApp = request.env['studio.app']

        try:
            result = StudioApp.action_import(json_data)
            return {'success': True, 'result': result}
        except Exception as e:
            _logger.exception("Failed to import app")
            return {'success': False, 'error': str(e)}
