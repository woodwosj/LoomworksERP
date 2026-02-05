# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Dashboard AI Tool Provider - M4 Pattern Implementation

Registers AI tools for dashboard creation and management.
Allows natural language dashboard generation via Claude AI.
"""

from odoo import api, models
import json
import logging

_logger = logging.getLogger(__name__)


class DashboardToolProvider(models.AbstractModel):
    """
    AI Tool Provider for Dashboard functionality.

    Implements the M4 pattern from PATCH_NOTES_M1_M4.md to register
    dashboard-related AI tools with the loomworks_ai system.
    """
    _name = 'dashboard.tool.provider'
    _inherit = 'loomworks.ai.tool.provider'
    _description = 'Dashboard AI Tool Provider'

    @api.model
    def _get_tool_definitions(self):
        """
        Return dashboard tool definitions for AI registration.

        Returns:
            list: Tool definitions for dashboard operations
        """
        return [
            {
                'name': 'Create Dashboard',
                'technical_name': 'dashboard_create',
                'category': 'action',
                'description': (
                    'Create a new dashboard with the specified name and configuration. '
                    'Returns the dashboard ID for adding widgets.'
                ),
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'name': {
                            'type': 'string',
                            'description': 'Name of the dashboard',
                        },
                        'description': {
                            'type': 'string',
                            'description': 'Description of what this dashboard shows',
                        },
                        'layout_columns': {
                            'type': 'integer',
                            'description': 'Number of grid columns (default: 12)',
                            'default': 12,
                        },
                        'auto_refresh': {
                            'type': 'integer',
                            'description': 'Auto-refresh interval in seconds (0 = disabled)',
                            'default': 0,
                        },
                    },
                    'required': ['name'],
                },
                'implementation_method': 'loomworks_dashboard.services.ai_dashboard_service.create_dashboard',
                'risk_level': 'moderate',
                'requires_confirmation': False,
                'returns_description': 'Dashboard ID and basic info',
            },
            {
                'name': 'Add KPI Widget',
                'technical_name': 'dashboard_add_kpi',
                'category': 'action',
                'description': (
                    'Add a KPI card widget to a dashboard. KPI cards show a single '
                    'metric value with optional trend indicator and comparison.'
                ),
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'dashboard_id': {
                            'type': 'integer',
                            'description': 'ID of the dashboard to add widget to',
                        },
                        'name': {
                            'type': 'string',
                            'description': 'Title of the KPI card',
                        },
                        'model': {
                            'type': 'string',
                            'description': 'Odoo model to fetch data from (e.g., sale.order)',
                        },
                        'domain': {
                            'type': 'array',
                            'description': 'Domain filter for records',
                            'default': [],
                        },
                        'measure_field': {
                            'type': 'string',
                            'description': 'Field to aggregate (e.g., amount_total)',
                        },
                        'aggregation': {
                            'type': 'string',
                            'enum': ['sum', 'avg', 'min', 'max', 'count'],
                            'description': 'Aggregation function',
                            'default': 'sum',
                        },
                        'format': {
                            'type': 'string',
                            'enum': ['number', 'currency', 'percent'],
                            'description': 'Value format',
                            'default': 'number',
                        },
                        'position': {
                            'type': 'object',
                            'properties': {
                                'x': {'type': 'integer'},
                                'y': {'type': 'integer'},
                            },
                            'description': 'Grid position',
                        },
                    },
                    'required': ['dashboard_id', 'name', 'model', 'measure_field'],
                },
                'implementation_method': 'loomworks_dashboard.services.ai_dashboard_service.add_kpi_widget',
                'risk_level': 'moderate',
                'requires_confirmation': False,
                'returns_description': 'Widget ID and configuration',
            },
            {
                'name': 'Add Chart Widget',
                'technical_name': 'dashboard_add_chart',
                'category': 'action',
                'description': (
                    'Add a chart widget to a dashboard. Supports line, bar, area, '
                    'and pie charts with data from Odoo models.'
                ),
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'dashboard_id': {
                            'type': 'integer',
                            'description': 'ID of the dashboard to add widget to',
                        },
                        'name': {
                            'type': 'string',
                            'description': 'Title of the chart',
                        },
                        'chart_type': {
                            'type': 'string',
                            'enum': ['chart_line', 'chart_bar', 'chart_area', 'chart_pie'],
                            'description': 'Type of chart',
                        },
                        'model': {
                            'type': 'string',
                            'description': 'Odoo model to fetch data from',
                        },
                        'domain': {
                            'type': 'array',
                            'description': 'Domain filter',
                            'default': [],
                        },
                        'group_by': {
                            'type': 'string',
                            'description': 'Field to group by (e.g., date_order:month)',
                        },
                        'measure_field': {
                            'type': 'string',
                            'description': 'Field to aggregate',
                        },
                        'aggregation': {
                            'type': 'string',
                            'enum': ['sum', 'avg', 'min', 'max', 'count'],
                            'default': 'sum',
                        },
                        'stacked': {
                            'type': 'boolean',
                            'description': 'Stack bars/areas',
                            'default': False,
                        },
                        'position': {
                            'type': 'object',
                            'properties': {
                                'x': {'type': 'integer'},
                                'y': {'type': 'integer'},
                            },
                        },
                        'size': {
                            'type': 'object',
                            'properties': {
                                'w': {'type': 'integer'},
                                'h': {'type': 'integer'},
                            },
                        },
                    },
                    'required': ['dashboard_id', 'name', 'chart_type', 'model', 'group_by', 'measure_field'],
                },
                'implementation_method': 'loomworks_dashboard.services.ai_dashboard_service.add_chart_widget',
                'risk_level': 'moderate',
                'requires_confirmation': False,
                'returns_description': 'Widget ID and configuration',
            },
            {
                'name': 'Add Table Widget',
                'technical_name': 'dashboard_add_table',
                'category': 'action',
                'description': (
                    'Add a data table widget to a dashboard. Tables show detailed '
                    'records with sorting and pagination.'
                ),
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'dashboard_id': {
                            'type': 'integer',
                            'description': 'ID of the dashboard',
                        },
                        'name': {
                            'type': 'string',
                            'description': 'Title of the table',
                        },
                        'model': {
                            'type': 'string',
                            'description': 'Odoo model to fetch data from',
                        },
                        'domain': {
                            'type': 'array',
                            'description': 'Domain filter',
                            'default': [],
                        },
                        'fields': {
                            'type': 'array',
                            'items': {'type': 'string'},
                            'description': 'Fields to display as columns',
                        },
                        'page_size': {
                            'type': 'integer',
                            'description': 'Records per page',
                            'default': 10,
                        },
                        'position': {
                            'type': 'object',
                            'properties': {
                                'x': {'type': 'integer'},
                                'y': {'type': 'integer'},
                            },
                        },
                    },
                    'required': ['dashboard_id', 'name', 'model', 'fields'],
                },
                'implementation_method': 'loomworks_dashboard.services.ai_dashboard_service.add_table_widget',
                'risk_level': 'moderate',
                'requires_confirmation': False,
                'returns_description': 'Widget ID and configuration',
            },
            {
                'name': 'Generate Dashboard from Prompt',
                'technical_name': 'dashboard_generate',
                'category': 'action',
                'description': (
                    'Generate a complete dashboard from a natural language description. '
                    'AI analyzes the prompt and creates appropriate widgets. '
                    'Example: "Create a sales dashboard showing revenue trends, top customers, and order status"'
                ),
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'prompt': {
                            'type': 'string',
                            'description': 'Natural language description of the desired dashboard',
                        },
                        'name': {
                            'type': 'string',
                            'description': 'Name for the dashboard (optional, will be generated)',
                        },
                    },
                    'required': ['prompt'],
                },
                'implementation_method': 'loomworks_dashboard.services.ai_dashboard_service.generate_from_prompt',
                'risk_level': 'moderate',
                'requires_confirmation': True,
                'returns_description': 'Dashboard ID with all generated widgets',
            },
            {
                'name': 'Get Dashboard Data',
                'technical_name': 'dashboard_get_data',
                'category': 'data',
                'description': (
                    'Fetch current data for a dashboard widget. '
                    'Returns the aggregated/formatted data ready for visualization.'
                ),
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'widget_id': {
                            'type': 'integer',
                            'description': 'ID of the widget to fetch data for',
                        },
                        'filters': {
                            'type': 'object',
                            'description': 'Optional filters to apply',
                        },
                    },
                    'required': ['widget_id'],
                },
                'implementation_method': 'loomworks_dashboard.services.ai_dashboard_service.get_widget_data',
                'risk_level': 'safe',
                'requires_confirmation': False,
                'returns_description': 'Widget data for visualization',
            },
            {
                'name': 'List Dashboards',
                'technical_name': 'dashboard_list',
                'category': 'data',
                'description': (
                    'List all dashboards accessible to the current user. '
                    'Returns dashboard names, descriptions, and widget counts.'
                ),
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'include_templates': {
                            'type': 'boolean',
                            'description': 'Include template dashboards',
                            'default': False,
                        },
                    },
                },
                'implementation_method': 'loomworks_dashboard.services.ai_dashboard_service.list_dashboards',
                'risk_level': 'safe',
                'requires_confirmation': False,
                'returns_description': 'List of accessible dashboards',
            },
        ]


class AIDashboardService(models.AbstractModel):
    """
    Service methods for AI tool execution.

    These methods are called by the AI tool system when tools are invoked.
    """
    _name = 'dashboard.ai.service'
    _description = 'Dashboard AI Service'

    @api.model
    def create_dashboard(self, name, description=None, layout_columns=12, auto_refresh=0):
        """Create a new dashboard."""
        Dashboard = self.env['dashboard.board']

        dashboard = Dashboard.create({
            'name': name,
            'description': description,
            'layout_columns': layout_columns,
            'auto_refresh': auto_refresh,
        })

        return {
            'success': True,
            'dashboard_id': dashboard.id,
            'name': dashboard.name,
            'message': f"Created dashboard '{name}' with ID {dashboard.id}",
        }

    @api.model
    def add_kpi_widget(self, dashboard_id, name, model, measure_field,
                       domain=None, aggregation='sum', format='number',
                       position=None):
        """Add a KPI widget to a dashboard."""
        Widget = self.env['dashboard.widget']

        pos = position or {'x': 0, 'y': 0}

        widget = Widget.create({
            'dashboard_id': dashboard_id,
            'name': name,
            'widget_type': 'kpi',
            'grid_x': pos.get('x', 0),
            'grid_y': pos.get('y', 0),
            'grid_width': 3,
            'grid_height': 2,
            'inline_model': model,
            'inline_domain': json.dumps(domain or []),
            'inline_measure_field': measure_field,
            'inline_aggregation': aggregation,
            'kpi_format': format,
        })

        return {
            'success': True,
            'widget_id': widget.id,
            'message': f"Added KPI widget '{name}' to dashboard",
        }

    @api.model
    def add_chart_widget(self, dashboard_id, name, chart_type, model,
                         group_by, measure_field, domain=None,
                         aggregation='sum', stacked=False,
                         position=None, size=None):
        """Add a chart widget to a dashboard."""
        Widget = self.env['dashboard.widget']

        pos = position or {'x': 0, 'y': 0}
        sz = size or {'w': 6, 'h': 4}

        widget = Widget.create({
            'dashboard_id': dashboard_id,
            'name': name,
            'widget_type': chart_type,
            'grid_x': pos.get('x', 0),
            'grid_y': pos.get('y', 0),
            'grid_width': sz.get('w', 6),
            'grid_height': sz.get('h', 4),
            'inline_model': model,
            'inline_domain': json.dumps(domain or []),
            'inline_group_by': group_by,
            'inline_measure_field': measure_field,
            'inline_aggregation': aggregation,
            'chart_stacked': stacked,
        })

        return {
            'success': True,
            'widget_id': widget.id,
            'message': f"Added {chart_type} widget '{name}' to dashboard",
        }

    @api.model
    def add_table_widget(self, dashboard_id, name, model, fields,
                         domain=None, page_size=10, position=None):
        """Add a table widget to a dashboard."""
        Widget = self.env['dashboard.widget']

        pos = position or {'x': 0, 'y': 0}

        # Build column config
        columns = [{'field': f, 'label': f.replace('_', ' ').title()} for f in fields]

        widget = Widget.create({
            'dashboard_id': dashboard_id,
            'name': name,
            'widget_type': 'table',
            'grid_x': pos.get('x', 0),
            'grid_y': pos.get('y', 0),
            'grid_width': 6,
            'grid_height': 4,
            'inline_model': model,
            'inline_domain': json.dumps(domain or []),
            'table_page_size': page_size,
            'table_columns': json.dumps(columns),
        })

        return {
            'success': True,
            'widget_id': widget.id,
            'message': f"Added table widget '{name}' to dashboard",
        }

    @api.model
    def generate_from_prompt(self, prompt, name=None):
        """
        Generate a complete dashboard from natural language prompt.

        Uses template matching or AI generation based on availability.
        """
        AIService = self.env.get('dashboard.ai.generation.service')
        if AIService:
            result = AIService.generate_from_prompt(prompt)
            if result.get('success'):
                spec = result['specification']

                # Create dashboard
                dashboard_result = self.create_dashboard(
                    name=name or spec.get('name', 'Generated Dashboard'),
                    description=spec.get('description', f'Generated from: {prompt}'),
                )
                dashboard_id = dashboard_result['dashboard_id']

                # Add widgets
                for widget_spec in spec.get('widgets', []):
                    self._create_widget_from_spec(dashboard_id, widget_spec)

                return {
                    'success': True,
                    'dashboard_id': dashboard_id,
                    'widget_count': len(spec.get('widgets', [])),
                    'method': result.get('method', 'template'),
                    'message': f"Generated dashboard with {len(spec.get('widgets', []))} widgets",
                }

        # Fallback: Create empty dashboard
        return self.create_dashboard(
            name=name or 'New Dashboard',
            description=f'Created from prompt: {prompt}',
        )

    def _create_widget_from_spec(self, dashboard_id, widget_spec):
        """Create a widget from AI-generated specification."""
        widget_type = widget_spec.get('type', 'kpi')
        data_source = widget_spec.get('data_source', {})

        if widget_type == 'kpi':
            self.add_kpi_widget(
                dashboard_id=dashboard_id,
                name=widget_spec.get('name', 'KPI'),
                model=data_source.get('model', 'res.partner'),
                measure_field=data_source.get('measure_field', 'id'),
                domain=data_source.get('domain', []),
                aggregation=data_source.get('aggregation', 'count'),
                format=widget_spec.get('config', {}).get('format', 'number'),
                position=widget_spec.get('position'),
            )
        elif widget_type.startswith('chart_'):
            self.add_chart_widget(
                dashboard_id=dashboard_id,
                name=widget_spec.get('name', 'Chart'),
                chart_type=widget_type,
                model=data_source.get('model', 'res.partner'),
                group_by=data_source.get('group_by', 'create_date:month'),
                measure_field=data_source.get('measure_field', 'id'),
                domain=data_source.get('domain', []),
                aggregation=data_source.get('aggregation', 'count'),
                position=widget_spec.get('position'),
                size=widget_spec.get('size'),
            )
        elif widget_type == 'table':
            self.add_table_widget(
                dashboard_id=dashboard_id,
                name=widget_spec.get('name', 'Table'),
                model=data_source.get('model', 'res.partner'),
                fields=widget_spec.get('config', {}).get('columns', ['name']),
                domain=data_source.get('domain', []),
                position=widget_spec.get('position'),
            )

    @api.model
    def get_widget_data(self, widget_id, filters=None):
        """Fetch data for a specific widget."""
        Widget = self.env['dashboard.widget']
        widget = Widget.browse(widget_id)

        if not widget.exists():
            return {'success': False, 'error': f'Widget {widget_id} not found'}

        # Check access
        if not widget.dashboard_id._check_access('read'):
            return {'success': False, 'error': 'Access denied'}

        # Get data
        if widget.data_source_id:
            DataSource = self.env['dashboard.data.source']
            data = DataSource.fetch_data(widget.data_source_id.id, filters)
        elif widget.inline_model:
            data = self._fetch_inline_widget_data(widget, filters)
        else:
            data = {'type': 'empty', 'data': []}

        return {
            'success': True,
            'widget_id': widget_id,
            'data': data,
        }

    def _fetch_inline_widget_data(self, widget, filters=None):
        """Fetch data using widget's inline data source config."""
        if not widget.inline_model:
            return {'type': 'empty', 'data': []}

        Model = self.env[widget.inline_model]
        domain = json.loads(widget.inline_domain or '[]')

        # Apply filters
        if filters:
            for field, value in filters.items():
                if value is not None:
                    if isinstance(value, dict):
                        if value.get('from'):
                            domain.append((field, '>=', value['from']))
                        if value.get('to'):
                            domain.append((field, '<=', value['to']))
                    else:
                        domain.append((field, '=', value))

        if widget.inline_group_by:
            # Grouped/aggregated data
            measure = widget.inline_measure_field or '__count'
            agg = widget.inline_aggregation or 'sum'

            group_by = widget.inline_group_by
            if agg == 'count':
                aggregates = ['__count']
            else:
                aggregates = [f"{measure}:{agg}"]

            raw_data = Model.read_group(domain, aggregates, [group_by], limit=100)

            # Transform for charts
            result = []
            for row in raw_data:
                name = row.get(group_by)
                if isinstance(name, tuple):
                    name = name[1]
                value = row.get('__count', 0) if agg == 'count' else row.get(f"{measure}", 0)
                result.append({'name': str(name) if name else 'Undefined', 'value': value})

            return {'type': 'grouped', 'data': result}
        else:
            # Single aggregate for KPI
            measure = widget.inline_measure_field
            agg = widget.inline_aggregation or 'sum'

            if agg == 'count':
                value = Model.search_count(domain)
            else:
                aggregates = [f"{measure}:{agg}"]
                result = Model.read_group(domain, aggregates, [])
                if result:
                    value = result[0].get(f"{measure}", 0)
                else:
                    value = 0

            return {'type': 'single', 'value': value}

    @api.model
    def list_dashboards(self, include_templates=False):
        """List accessible dashboards."""
        Dashboard = self.env['dashboard.board']

        domain = [
            '|',
            ('user_id', '=', self.env.uid),
            ('is_public', '=', True),
        ]

        if not include_templates:
            domain.append(('is_template', '=', False))

        dashboards = Dashboard.search_read(
            domain,
            ['id', 'name', 'description', 'widget_count', 'is_template'],
            order='name',
        )

        return {
            'success': True,
            'dashboards': dashboards,
            'count': len(dashboards),
        }
