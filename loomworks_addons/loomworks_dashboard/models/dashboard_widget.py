# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Dashboard Widget Model - Individual widgets placed on the dashboard canvas.

Widget types:
- KPI: Single metric display with trend indicator
- chart_line: Line chart for trends over time
- chart_bar: Bar chart for comparisons
- chart_area: Area chart for cumulative trends
- chart_pie: Pie chart for proportions
- table: Data table with sorting and pagination
- filter: Global filter control
- gauge: Progress toward target
"""

from loomworks import api, fields, models
from loomworks.exceptions import ValidationError
import json
import logging

_logger = logging.getLogger(__name__)

# Widget type configurations
WIDGET_TYPES = {
    'kpi': {
        'name': 'KPI Card',
        'description': 'Single metric with trend indicator',
        'default_width': 3,
        'default_height': 2,
        'min_width': 2,
        'min_height': 2,
    },
    'chart_line': {
        'name': 'Line Chart',
        'description': 'Trends over time',
        'default_width': 6,
        'default_height': 4,
        'min_width': 4,
        'min_height': 3,
    },
    'chart_bar': {
        'name': 'Bar Chart',
        'description': 'Comparisons across categories',
        'default_width': 6,
        'default_height': 4,
        'min_width': 4,
        'min_height': 3,
    },
    'chart_area': {
        'name': 'Area Chart',
        'description': 'Cumulative trends',
        'default_width': 6,
        'default_height': 4,
        'min_width': 4,
        'min_height': 3,
    },
    'chart_pie': {
        'name': 'Pie Chart',
        'description': 'Distribution and proportions',
        'default_width': 4,
        'default_height': 4,
        'min_width': 3,
        'min_height': 3,
    },
    'table': {
        'name': 'Data Table',
        'description': 'Detailed record list with sorting',
        'default_width': 6,
        'default_height': 4,
        'min_width': 4,
        'min_height': 3,
    },
    'filter': {
        'name': 'Filter Control',
        'description': 'Global filter for other widgets',
        'default_width': 3,
        'default_height': 2,
        'min_width': 2,
        'min_height': 1,
    },
    'gauge': {
        'name': 'Gauge',
        'description': 'Progress toward target',
        'default_width': 3,
        'default_height': 3,
        'min_width': 2,
        'min_height': 2,
    },
}


class DashboardWidget(models.Model):
    """
    Widget instance on a dashboard canvas.

    Each widget has:
    - Type (KPI, chart, table, filter, gauge)
    - Position and size on the grid
    - Data source connection
    - Visual configuration
    """
    _name = 'dashboard.widget'
    _description = 'Dashboard Widget'
    _order = 'sequence, id'

    # Basic Information
    name = fields.Char(
        string='Widget Title',
        required=True,
    )
    dashboard_id = fields.Many2one(
        'dashboard.board',
        string='Dashboard',
        required=True,
        ondelete='cascade',
    )
    tab_id = fields.Many2one(
        'dashboard.tab',
        string='Tab',
        help='Tab this widget belongs to (optional)',
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )

    # Widget Type
    widget_type = fields.Selection([
        ('kpi', 'KPI Card'),
        ('chart_line', 'Line Chart'),
        ('chart_bar', 'Bar Chart'),
        ('chart_area', 'Area Chart'),
        ('chart_pie', 'Pie Chart'),
        ('table', 'Data Table'),
        ('filter', 'Filter Control'),
        ('gauge', 'Gauge'),
    ], string='Widget Type', required=True, default='kpi')

    # Grid Position (Gridstack coordinates)
    grid_x = fields.Integer(
        string='Grid X',
        default=0,
        help='Horizontal position in grid units',
    )
    grid_y = fields.Integer(
        string='Grid Y',
        default=0,
        help='Vertical position in grid units',
    )
    grid_width = fields.Integer(
        string='Grid Width',
        default=4,
        help='Width in grid units',
    )
    grid_height = fields.Integer(
        string='Grid Height',
        default=3,
        help='Height in grid units',
    )
    min_width = fields.Integer(
        string='Min Width',
        compute='_compute_min_dimensions',
    )
    min_height = fields.Integer(
        string='Min Height',
        compute='_compute_min_dimensions',
    )

    # Data Source
    data_source_id = fields.Many2one(
        'dashboard.data.source',
        string='Data Source',
        help='Data source for this widget',
    )
    # Inline data source config (for widgets without separate data source)
    inline_model = fields.Char(
        string='Model',
        help='Loomworks model for inline data source',
    )
    inline_domain = fields.Text(
        string='Domain',
        default='[]',
        help='Domain filter for inline data source',
    )
    inline_group_by = fields.Char(
        string='Group By',
        help='Field to group by (e.g., date_order:month)',
    )
    inline_measure_field = fields.Char(
        string='Measure Field',
        help='Field to aggregate',
    )
    inline_aggregation = fields.Selection([
        ('sum', 'Sum'),
        ('avg', 'Average'),
        ('min', 'Minimum'),
        ('max', 'Maximum'),
        ('count', 'Count'),
    ], string='Aggregation', default='sum')

    # Visual Configuration (JSON)
    config = fields.Text(
        string='Configuration',
        default='{}',
        help='JSON configuration for widget appearance',
    )

    # KPI-Specific Fields
    kpi_format = fields.Selection([
        ('number', 'Number'),
        ('currency', 'Currency'),
        ('percent', 'Percentage'),
    ], string='KPI Format', default='number')
    kpi_prefix = fields.Char(
        string='Prefix',
        help='Text to show before value (e.g., $)',
    )
    kpi_suffix = fields.Char(
        string='Suffix',
        help='Text to show after value (e.g., %)',
    )
    kpi_trend_enabled = fields.Boolean(
        string='Show Trend',
        default=True,
    )
    kpi_target = fields.Float(
        string='Target Value',
        help='Target for gauge or trend comparison',
    )

    # Chart-Specific Fields
    chart_colors = fields.Char(
        string='Chart Colors',
        help='Comma-separated hex colors (e.g., #6366f1,#8b5cf6)',
    )
    chart_show_legend = fields.Boolean(
        string='Show Legend',
        default=True,
    )
    chart_show_grid = fields.Boolean(
        string='Show Grid',
        default=True,
    )
    chart_stacked = fields.Boolean(
        string='Stacked',
        default=False,
    )

    # Table-Specific Fields
    table_page_size = fields.Integer(
        string='Page Size',
        default=10,
    )
    table_columns = fields.Text(
        string='Table Columns',
        default='[]',
        help='JSON array of column configurations',
    )

    # Filter Widget Fields
    filter_field = fields.Char(
        string='Filter Field',
        help='Field this filter controls',
    )
    filter_type = fields.Selection([
        ('select', 'Dropdown'),
        ('multiselect', 'Multi-Select'),
        ('date_range', 'Date Range'),
        ('number_range', 'Number Range'),
        ('search', 'Text Search'),
    ], string='Filter Type', default='select')

    # Linked Widgets (for filters)
    linked_widget_ids = fields.Many2many(
        'dashboard.widget',
        'dashboard_widget_filter_rel',
        'filter_widget_id',
        'target_widget_id',
        string='Linked Widgets',
        help='Widgets affected by this filter',
    )

    @api.depends('widget_type')
    def _compute_min_dimensions(self):
        for widget in self:
            config = WIDGET_TYPES.get(widget.widget_type, {})
            widget.min_width = config.get('min_width', 2)
            widget.min_height = config.get('min_height', 2)

    @api.onchange('widget_type')
    def _onchange_widget_type(self):
        """Set default dimensions when widget type changes."""
        if self.widget_type:
            config = WIDGET_TYPES.get(self.widget_type, {})
            self.grid_width = config.get('default_width', 4)
            self.grid_height = config.get('default_height', 3)

    @api.constrains('grid_width', 'grid_height')
    def _check_dimensions(self):
        for widget in self:
            config = WIDGET_TYPES.get(widget.widget_type, {})
            min_w = config.get('min_width', 2)
            min_h = config.get('min_height', 2)
            if widget.grid_width < min_w:
                raise ValidationError(
                    f"Widget width must be at least {min_w} for {widget.widget_type}"
                )
            if widget.grid_height < min_h:
                raise ValidationError(
                    f"Widget height must be at least {min_h} for {widget.widget_type}"
                )

    def get_widget_data(self):
        """
        Get widget data for React canvas.

        Returns:
            dict: Widget configuration for React
        """
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'type': self.widget_type,
            'position': {
                'x': self.grid_x,
                'y': self.grid_y,
            },
            'size': {
                'w': self.grid_width,
                'h': self.grid_height,
            },
            'minSize': {
                'w': self.min_width,
                'h': self.min_height,
            },
            'tabId': self.tab_id.id if self.tab_id else None,
            'dataSourceId': self.data_source_id.id if self.data_source_id else None,
            'inlineDataSource': self._get_inline_data_source() if not self.data_source_id else None,
            'config': self._get_widget_config(),
        }

    def _get_inline_data_source(self):
        """Get inline data source configuration."""
        if not self.inline_model:
            return None
        try:
            domain = json.loads(self.inline_domain or '[]')
        except (json.JSONDecodeError, TypeError):
            _logger.warning("Invalid JSON in inline_domain for widget %s", self.id)
            domain = []
        return {
            'type': 'model',
            'model': self.inline_model,
            'domain': domain,
            'groupBy': self.inline_group_by,
            'measureField': self.inline_measure_field,
            'aggregation': self.inline_aggregation,
        }

    def _get_widget_config(self):
        """Get widget-specific configuration."""
        try:
            base_config = json.loads(self.config or '{}')
        except (json.JSONDecodeError, TypeError):
            _logger.warning("Invalid JSON in config for widget %s", self.id)
            base_config = {}

        if self.widget_type == 'kpi':
            base_config.update({
                'format': self.kpi_format,
                'prefix': self.kpi_prefix,
                'suffix': self.kpi_suffix,
                'showTrend': self.kpi_trend_enabled,
                'target': self.kpi_target,
            })
        elif self.widget_type.startswith('chart_'):
            base_config.update({
                'colors': self.chart_colors.split(',') if self.chart_colors else None,
                'showLegend': self.chart_show_legend,
                'showGrid': self.chart_show_grid,
                'stacked': self.chart_stacked,
            })
        elif self.widget_type == 'table':
            try:
                columns = json.loads(self.table_columns or '[]')
            except (json.JSONDecodeError, TypeError):
                _logger.warning("Invalid JSON in table_columns for widget %s", self.id)
                columns = []
            base_config.update({
                'pageSize': self.table_page_size,
                'columns': columns,
            })
        elif self.widget_type == 'filter':
            base_config.update({
                'field': self.filter_field,
                'filterType': self.filter_type,
                'linkedWidgetIds': self.linked_widget_ids.ids,
            })
        elif self.widget_type == 'gauge':
            base_config.update({
                'target': self.kpi_target,
                'format': self.kpi_format,
            })

        return base_config

    def update_from_canvas(self, widget_data):
        """
        Update widget from React canvas data.

        Args:
            widget_data: dict with position, size, config from React
        """
        self.ensure_one()
        vals = {}

        if 'name' in widget_data:
            vals['name'] = widget_data['name']

        if 'position' in widget_data:
            vals['grid_x'] = widget_data['position'].get('x', 0)
            vals['grid_y'] = widget_data['position'].get('y', 0)

        if 'size' in widget_data:
            vals['grid_width'] = widget_data['size'].get('w', 4)
            vals['grid_height'] = widget_data['size'].get('h', 3)

        if 'config' in widget_data:
            config = widget_data['config']
            vals['config'] = json.dumps(config)

            # Extract specific config fields
            if self.widget_type == 'kpi':
                if 'format' in config:
                    vals['kpi_format'] = config['format']
                if 'prefix' in config:
                    vals['kpi_prefix'] = config['prefix']
                if 'suffix' in config:
                    vals['kpi_suffix'] = config['suffix']
                if 'showTrend' in config:
                    vals['kpi_trend_enabled'] = config['showTrend']
                if 'target' in config:
                    vals['kpi_target'] = config['target']

            elif self.widget_type.startswith('chart_'):
                if 'colors' in config:
                    vals['chart_colors'] = ','.join(config['colors']) if config['colors'] else ''
                if 'showLegend' in config:
                    vals['chart_show_legend'] = config['showLegend']
                if 'showGrid' in config:
                    vals['chart_show_grid'] = config['showGrid']
                if 'stacked' in config:
                    vals['chart_stacked'] = config['stacked']

            elif self.widget_type == 'table':
                if 'pageSize' in config:
                    vals['table_page_size'] = config['pageSize']
                if 'columns' in config:
                    vals['table_columns'] = json.dumps(config['columns'])

        if vals:
            self.write(vals)

    @api.model
    def create_from_canvas(self, dashboard_id, widget_data):
        """
        Create a new widget from React canvas data.

        Args:
            dashboard_id: ID of parent dashboard
            widget_data: dict with widget configuration from React

        Returns:
            dashboard.widget record
        """
        widget_type = widget_data.get('type', 'kpi')
        type_config = WIDGET_TYPES.get(widget_type, {})

        vals = {
            'dashboard_id': dashboard_id,
            'name': widget_data.get('name', type_config.get('name', 'New Widget')),
            'widget_type': widget_type,
            'grid_x': widget_data.get('position', {}).get('x', 0),
            'grid_y': widget_data.get('position', {}).get('y', 0),
            'grid_width': widget_data.get('size', {}).get('w', type_config.get('default_width', 4)),
            'grid_height': widget_data.get('size', {}).get('h', type_config.get('default_height', 3)),
            'config': json.dumps(widget_data.get('config', {})),
        }

        # Handle inline data source
        data_source = widget_data.get('inlineDataSource')
        if data_source:
            vals.update({
                'inline_model': data_source.get('model'),
                'inline_domain': json.dumps(data_source.get('domain', [])),
                'inline_group_by': data_source.get('groupBy'),
                'inline_measure_field': data_source.get('measureField'),
                'inline_aggregation': data_source.get('aggregation', 'sum'),
            })

        return self.create(vals)


class DashboardWidgetType(models.Model):
    """
    Widget type registry for extensibility.

    Allows third-party modules to register new widget types.
    """
    _name = 'dashboard.widget.type'
    _description = 'Dashboard Widget Type'
    _order = 'sequence, name'

    name = fields.Char(
        string='Name',
        required=True,
    )
    technical_name = fields.Char(
        string='Technical Name',
        required=True,
        help='Unique identifier used in code (e.g., chart_radar)',
    )
    description = fields.Text(
        string='Description',
    )
    icon = fields.Char(
        string='Icon',
        help='FontAwesome icon class',
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    default_width = fields.Integer(
        string='Default Width',
        default=4,
    )
    default_height = fields.Integer(
        string='Default Height',
        default=3,
    )
    min_width = fields.Integer(
        string='Min Width',
        default=2,
    )
    min_height = fields.Integer(
        string='Min Height',
        default=2,
    )
    react_component = fields.Char(
        string='React Component',
        help='Name of the React component to render this widget',
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )

    _sql_constraints = [
        ('technical_name_uniq', 'unique(technical_name)',
         'Widget type technical name must be unique'),
    ]
