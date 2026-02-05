# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Dashboard REST API Controllers

Provides HTTP endpoints for:
- Dashboard CRUD operations
- Widget management
- Data fetching for widgets
- AI-powered dashboard generation
"""

from odoo import http
from odoo.http import request, Response
from odoo.exceptions import AccessError, UserError
import json
import logging

_logger = logging.getLogger(__name__)


class DashboardController(http.Controller):
    """
    REST API controller for dashboard operations.
    """

    # -------------------------------------------------------------------------
    # Dashboard CRUD
    # -------------------------------------------------------------------------

    @http.route('/loomworks/dashboard/<int:dashboard_id>', type='json', auth='user')
    def get_dashboard(self, dashboard_id, **kwargs):
        """
        Get complete dashboard data for React canvas.

        Args:
            dashboard_id: ID of the dashboard

        Returns:
            dict: Dashboard configuration with widgets, filters, tabs
        """
        Dashboard = request.env['dashboard.board']
        dashboard = Dashboard.browse(dashboard_id)

        if not dashboard.exists():
            return {'error': 'Dashboard not found', 'code': 404}

        if not dashboard._check_access('read'):
            return {'error': 'Access denied', 'code': 403}

        return dashboard.get_dashboard_data()

    @http.route('/loomworks/dashboard/create', type='json', auth='user')
    def create_dashboard(self, **kwargs):
        """
        Create a new dashboard.

        Args:
            name: Dashboard name
            description: Optional description
            layout_columns: Grid columns (default 12)
            auto_refresh: Refresh interval in seconds (default 0)
            template_id: Optional template to copy from

        Returns:
            dict: Created dashboard info
        """
        name = kwargs.get('name', 'New Dashboard')
        description = kwargs.get('description')
        template_id = kwargs.get('template_id')

        Dashboard = request.env['dashboard.board']

        if template_id:
            # Copy from template
            template = Dashboard.browse(template_id)
            if not template.exists() or not template.is_template:
                return {'error': 'Invalid template', 'code': 400}

            dashboard = template.copy({
                'name': name,
                'description': description or template.description,
                'is_template': False,
                'user_id': request.env.uid,
            })
        else:
            # Create new dashboard
            dashboard = Dashboard.create({
                'name': name,
                'description': description,
                'layout_columns': kwargs.get('layout_columns', 12),
                'auto_refresh': kwargs.get('auto_refresh', 0),
            })

        return {
            'success': True,
            'dashboard_id': dashboard.id,
            'name': dashboard.name,
        }

    @http.route('/loomworks/dashboard/<int:dashboard_id>/save', type='json', auth='user')
    def save_dashboard(self, dashboard_id, **kwargs):
        """
        Save dashboard state from React canvas.

        Args:
            dashboard_id: ID of the dashboard
            widgets: List of widget configurations
            filters: List of filter configurations
            canvasConfig: Canvas settings

        Returns:
            dict: Success status
        """
        Dashboard = request.env['dashboard.board']
        dashboard = Dashboard.browse(dashboard_id)

        if not dashboard.exists():
            return {'error': 'Dashboard not found', 'code': 404}

        try:
            dashboard.save_from_canvas(kwargs)
            return {'success': True}
        except AccessError as e:
            return {'error': str(e), 'code': 403}
        except Exception as e:
            _logger.exception("Failed to save dashboard: %s", e)
            return {'error': str(e), 'code': 500}

    @http.route('/loomworks/dashboard/<int:dashboard_id>/delete', type='json', auth='user')
    def delete_dashboard(self, dashboard_id, **kwargs):
        """
        Delete a dashboard.

        Args:
            dashboard_id: ID of the dashboard

        Returns:
            dict: Success status
        """
        Dashboard = request.env['dashboard.board']
        dashboard = Dashboard.browse(dashboard_id)

        if not dashboard.exists():
            return {'error': 'Dashboard not found', 'code': 404}

        if not dashboard._check_access('write'):
            return {'error': 'Access denied', 'code': 403}

        dashboard.unlink()
        return {'success': True}

    # -------------------------------------------------------------------------
    # Widget Operations
    # -------------------------------------------------------------------------

    @http.route('/loomworks/dashboard/<int:dashboard_id>/widget', type='json', auth='user', methods=['POST'])
    def add_widget(self, dashboard_id, **kwargs):
        """
        Add a new widget to a dashboard.

        Args:
            dashboard_id: ID of the dashboard
            widget_type: Type of widget (kpi, chart_line, etc.)
            name: Widget name
            position: {x, y} grid position
            size: {w, h} grid size
            config: Widget-specific configuration
            inlineDataSource: Optional inline data source config

        Returns:
            dict: Created widget info
        """
        Dashboard = request.env['dashboard.board']
        dashboard = Dashboard.browse(dashboard_id)

        if not dashboard.exists():
            return {'error': 'Dashboard not found', 'code': 404}

        if not dashboard._check_access('write'):
            return {'error': 'Access denied', 'code': 403}

        Widget = request.env['dashboard.widget']
        widget = Widget.create_from_canvas(dashboard_id, kwargs)

        return {
            'success': True,
            'widget_id': widget.id,
            'widget': widget.get_widget_data(),
        }

    @http.route('/loomworks/dashboard/widget/<int:widget_id>', type='json', auth='user', methods=['PUT'])
    def update_widget(self, widget_id, **kwargs):
        """
        Update a widget configuration.

        Args:
            widget_id: ID of the widget
            ... widget properties to update

        Returns:
            dict: Updated widget info
        """
        Widget = request.env['dashboard.widget']
        widget = Widget.browse(widget_id)

        if not widget.exists():
            return {'error': 'Widget not found', 'code': 404}

        if not widget.dashboard_id._check_access('write'):
            return {'error': 'Access denied', 'code': 403}

        widget.update_from_canvas(kwargs)

        return {
            'success': True,
            'widget': widget.get_widget_data(),
        }

    @http.route('/loomworks/dashboard/widget/<int:widget_id>', type='json', auth='user', methods=['DELETE'])
    def delete_widget(self, widget_id, **kwargs):
        """
        Delete a widget from a dashboard.

        Args:
            widget_id: ID of the widget

        Returns:
            dict: Success status
        """
        Widget = request.env['dashboard.widget']
        widget = Widget.browse(widget_id)

        if not widget.exists():
            return {'error': 'Widget not found', 'code': 404}

        if not widget.dashboard_id._check_access('write'):
            return {'error': 'Access denied', 'code': 403}

        widget.unlink()
        return {'success': True}

    # -------------------------------------------------------------------------
    # Data Fetching
    # -------------------------------------------------------------------------

    @http.route('/loomworks/dashboard/data/<int:source_id>', type='json', auth='user')
    def fetch_data_source(self, source_id, **kwargs):
        """
        Fetch data from a data source.

        Args:
            source_id: ID of the data source
            filters: Optional filter values

        Returns:
            dict: Data source results
        """
        DataSource = request.env['dashboard.data.source']

        try:
            filters = kwargs.get('filters', {})
            data = DataSource.fetch_data(source_id, filters)
            return {'success': True, 'data': data}
        except AccessError as e:
            return {'error': str(e), 'code': 403}
        except Exception as e:
            _logger.exception("Failed to fetch data source: %s", e)
            return {'error': str(e), 'code': 500}

    @http.route('/loomworks/dashboard/widget/<int:widget_id>/data', type='json', auth='user')
    def fetch_widget_data(self, widget_id, **kwargs):
        """
        Fetch data for a specific widget.

        Args:
            widget_id: ID of the widget
            filters: Optional filter values

        Returns:
            dict: Widget data for visualization
        """
        AIService = request.env['dashboard.ai.service']
        filters = kwargs.get('filters', {})

        result = AIService.get_widget_data(widget_id, filters)
        return result

    # -------------------------------------------------------------------------
    # AI Generation
    # -------------------------------------------------------------------------

    @http.route('/loomworks/dashboard/generate', type='json', auth='user')
    def generate_dashboard(self, **kwargs):
        """
        Generate a dashboard from natural language prompt.

        Args:
            prompt: Natural language description
            name: Optional dashboard name

        Returns:
            dict: Generated dashboard info
        """
        prompt = kwargs.get('prompt', '')
        name = kwargs.get('name')

        if not prompt:
            return {'error': 'Prompt is required', 'code': 400}

        AIService = request.env['dashboard.ai.service']

        try:
            result = AIService.generate_from_prompt(prompt, name)
            return result
        except Exception as e:
            _logger.exception("Dashboard generation failed: %s", e)
            return {'error': str(e), 'code': 500}

    # -------------------------------------------------------------------------
    # Templates
    # -------------------------------------------------------------------------

    @http.route('/loomworks/dashboard/templates', type='json', auth='user')
    def get_templates(self, **kwargs):
        """
        Get available dashboard templates.

        Returns:
            list: Template dashboards
        """
        Dashboard = request.env['dashboard.board']

        templates = Dashboard.search_read(
            [('is_template', '=', True), ('active', '=', True)],
            ['id', 'name', 'description', 'widget_count'],
            order='name',
        )

        return {'templates': templates}

    # -------------------------------------------------------------------------
    # Sharing
    # -------------------------------------------------------------------------

    @http.route('/loomworks/dashboard/<int:dashboard_id>/share', type='json', auth='user', methods=['POST'])
    def share_dashboard(self, dashboard_id, **kwargs):
        """
        Share a dashboard with users/groups or create public link.

        Args:
            dashboard_id: ID of the dashboard
            share_type: 'user', 'group', or 'link'
            user_id: User ID for user share
            group_ids: Group IDs for group share
            can_edit: Allow editing
            link_expires: Expiration datetime for link
            link_password: Password protection

        Returns:
            dict: Share info
        """
        Dashboard = request.env['dashboard.board']
        dashboard = Dashboard.browse(dashboard_id)

        if not dashboard.exists():
            return {'error': 'Dashboard not found', 'code': 404}

        if not dashboard._check_access('write'):
            return {'error': 'Access denied', 'code': 403}

        Share = request.env['dashboard.share']

        share_vals = {
            'dashboard_id': dashboard_id,
            'share_type': kwargs.get('share_type', 'link'),
            'can_edit': kwargs.get('can_edit', False),
        }

        if kwargs.get('share_type') == 'user':
            share_vals['user_id'] = kwargs.get('user_id')
        elif kwargs.get('share_type') == 'group':
            share_vals['group_ids'] = [(6, 0, kwargs.get('group_ids', []))]
        elif kwargs.get('share_type') == 'link':
            share_vals['link_expires'] = kwargs.get('link_expires')
            share_vals['link_password'] = kwargs.get('link_password')

        share = Share.create(share_vals)

        return {
            'success': True,
            'share_id': share.id,
            'share_url': share.share_url,
        }

    @http.route('/dashboard/public/<string:token>', type='http', auth='public')
    def public_dashboard(self, token, password=None, **kwargs):
        """
        View a publicly shared dashboard.

        Args:
            token: Public share token
            password: Optional password

        Returns:
            HTTP response with dashboard page
        """
        Share = request.env['dashboard.share'].sudo()
        share = Share.search([('public_token', '=', token)], limit=1)

        if not share.exists():
            return request.not_found()

        if not share.check_access(password):
            # TODO: Render password form or error page
            return request.not_found()

        share.record_view()

        # Render public dashboard view
        return request.render('loomworks_dashboard.public_dashboard', {
            'dashboard': share.dashboard_id,
            'share': share,
        })

    # -------------------------------------------------------------------------
    # Model Discovery
    # -------------------------------------------------------------------------

    @http.route('/loomworks/dashboard/models', type='json', auth='user')
    def get_available_models(self, **kwargs):
        """
        Get Odoo models available for data sources.

        Returns:
            list: Accessible models with field info
        """
        IrModel = request.env['ir.model']

        # Common business models
        common_models = [
            'sale.order', 'sale.order.line',
            'purchase.order', 'purchase.order.line',
            'account.move', 'account.move.line',
            'stock.picking', 'stock.move',
            'crm.lead', 'crm.team',
            'project.project', 'project.task',
            'hr.employee', 'hr.department',
            'product.product', 'product.template',
            'res.partner', 'res.users',
        ]

        accessible_models = []
        for model_name in common_models:
            try:
                Model = request.env.get(model_name)
                if Model and Model.check_access_rights('read', raise_exception=False):
                    model_info = IrModel.search([('model', '=', model_name)], limit=1)
                    if model_info:
                        fields = Model.fields_get()
                        numeric_fields = [
                            {'name': f, 'label': info.get('string', f)}
                            for f, info in fields.items()
                            if info.get('type') in ('integer', 'float', 'monetary')
                            and not f.startswith('_')
                        ][:15]
                        date_fields = [
                            {'name': f, 'label': info.get('string', f)}
                            for f, info in fields.items()
                            if info.get('type') in ('date', 'datetime')
                        ][:10]

                        accessible_models.append({
                            'model': model_name,
                            'name': model_info.name,
                            'numericFields': numeric_fields,
                            'dateFields': date_fields,
                        })
            except Exception:
                continue

        return {'models': accessible_models}

    @http.route('/loomworks/dashboard/model/<string:model>/fields', type='json', auth='user')
    def get_model_fields(self, model, **kwargs):
        """
        Get field details for a specific model.

        Args:
            model: Model name

        Returns:
            dict: Field information
        """
        try:
            Model = request.env[model]
            if not Model.check_access_rights('read', raise_exception=False):
                return {'error': 'Access denied', 'code': 403}

            fields = Model.fields_get()

            result = {
                'model': model,
                'fields': [
                    {
                        'name': name,
                        'label': info.get('string', name),
                        'type': info.get('type'),
                        'relation': info.get('relation'),
                        'selection': info.get('selection'),
                    }
                    for name, info in fields.items()
                    if not name.startswith('_') and info.get('type') not in ('binary', 'html')
                ],
            }

            return result
        except Exception as e:
            return {'error': str(e), 'code': 400}
