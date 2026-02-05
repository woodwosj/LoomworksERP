# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Spreadsheet Chart Model - Chart configurations.

Defines chart types and configurations for data visualization
within spreadsheets.
"""

import json
import logging

from odoo import api, models, fields, _
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class SpreadsheetChart(models.Model):
    """
    Chart definition for spreadsheets.

    Stores the configuration for visualizing data using
    various chart types (bar, line, pie, etc.).
    """
    _name = 'spreadsheet.chart'
    _description = 'Spreadsheet Chart'
    _order = 'name'

    name = fields.Char(
        string='Title',
        required=True
    )
    document_id = fields.Many2one(
        'spreadsheet.document',
        string='Spreadsheet',
        required=True,
        ondelete='cascade'
    )
    active = fields.Boolean(default=True)

    # Chart Type
    chart_type = fields.Selection([
        ('bar', 'Bar Chart'),
        ('line', 'Line Chart'),
        ('pie', 'Pie Chart'),
        ('doughnut', 'Doughnut Chart'),
        ('area', 'Area Chart'),
        ('scatter', 'Scatter Plot'),
        ('radar', 'Radar Chart'),
        ('combo', 'Combo Chart'),
    ], string='Chart Type', default='bar', required=True)

    # Data Source
    source_type = fields.Selection([
        ('range', 'Cell Range'),
        ('model', 'Odoo Model'),
        ('pivot', 'Pivot Table'),
    ], string='Data Source', default='range', required=True)

    # Cell Range Source
    data_range = fields.Char(
        string='Data Range',
        help="Cell range for chart data (e.g., 'A1:D10')"
    )
    label_range = fields.Char(
        string='Label Range',
        help="Cell range for labels (e.g., 'A1:A10')"
    )

    # Odoo Model Source
    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        ondelete='cascade'
    )
    model_name = fields.Char(
        related='model_id.model'
    )
    domain = fields.Char(
        string='Filter Domain',
        default='[]'
    )
    groupby_field_id = fields.Many2one(
        'ir.model.fields',
        string='Group By',
        ondelete='cascade'
    )
    measure_field_id = fields.Many2one(
        'ir.model.fields',
        string='Measure Field',
        ondelete='cascade'
    )
    measure_aggregator = fields.Selection([
        ('sum', 'Sum'),
        ('avg', 'Average'),
        ('count', 'Count'),
        ('min', 'Minimum'),
        ('max', 'Maximum'),
    ], string='Aggregation', default='sum')

    # Pivot Source
    pivot_id = fields.Many2one(
        'spreadsheet.pivot',
        string='Pivot Table'
    )

    # Display Settings
    width = fields.Integer(
        string='Width',
        default=600
    )
    height = fields.Integer(
        string='Height',
        default=400
    )
    position_x = fields.Integer(
        string='X Position',
        default=0
    )
    position_y = fields.Integer(
        string='Y Position',
        default=0
    )
    target_sheet = fields.Char(
        string='Target Sheet',
        default='sheet1'
    )

    # Styling
    show_legend = fields.Boolean(
        string='Show Legend',
        default=True
    )
    legend_position = fields.Selection([
        ('top', 'Top'),
        ('bottom', 'Bottom'),
        ('left', 'Left'),
        ('right', 'Right'),
    ], string='Legend Position', default='bottom')

    show_title = fields.Boolean(
        string='Show Title',
        default=True
    )
    show_data_labels = fields.Boolean(
        string='Show Data Labels',
        default=False
    )

    # Colors
    color_scheme = fields.Selection([
        ('default', 'Default'),
        ('vibrant', 'Vibrant'),
        ('pastel', 'Pastel'),
        ('monochrome', 'Monochrome'),
        ('custom', 'Custom'),
    ], string='Color Scheme', default='default')
    custom_colors = fields.Char(
        string='Custom Colors',
        help="Comma-separated hex colors (e.g., '#FF6384,#36A2EB,#FFCE56')"
    )

    # Chart Configuration (JSON)
    config_json = fields.Text(
        string='Chart Configuration',
        help="Full chart configuration in JSON format"
    )

    def get_chart_data(self):
        """
        Get the data for rendering the chart.

        Returns:
            dict: Chart data suitable for Univer/ECharts
        """
        self.ensure_one()

        if self.source_type == 'model':
            return self._get_model_chart_data()
        elif self.source_type == 'pivot':
            return self._get_pivot_chart_data()
        else:
            return self._get_range_chart_data()

    def _get_model_chart_data(self):
        """Get chart data from Odoo model."""
        if not self.model_name or self.model_name not in self.env:
            return {'error': 'Model not configured'}

        Model = self.env[self.model_name]
        domain = safe_eval(self.domain or '[]')

        # Get groupby and measure fields
        groupby = self.groupby_field_id.name if self.groupby_field_id else None
        measure = self.measure_field_id.name if self.measure_field_id else 'id'

        if not groupby:
            return {'error': 'Group by field not configured'}

        # Execute read_group
        agg_spec = f"{measure}:{self.measure_aggregator}" if measure != 'id' else 'id'
        results = Model.read_group(domain, [agg_spec], [groupby])

        # Process results
        labels = []
        values = []
        for result in results:
            label = result.get(groupby)
            if isinstance(label, tuple):
                label = label[1]
            labels.append(label or 'N/A')

            if measure == 'id':
                values.append(result.get('__count', 0))
            else:
                values.append(result.get(measure, 0))

        return {
            'labels': labels,
            'datasets': [{
                'label': self.measure_field_id.field_description if self.measure_field_id else 'Count',
                'data': values,
            }],
        }

    def _get_pivot_chart_data(self):
        """Get chart data from pivot table."""
        if not self.pivot_id:
            return {'error': 'Pivot table not configured'}

        # Get cached pivot data or compute
        if self.pivot_id.cached_data:
            pivot_data = json.loads(self.pivot_id.cached_data)
        else:
            pivot_data = self.pivot_id.compute_pivot()

        if 'error' in pivot_data:
            return pivot_data

        # Convert pivot to chart format
        row_values = pivot_data.get('rows', {}).get('values', [])
        measures = pivot_data.get('measures', [])
        data = pivot_data.get('data', {})

        labels = [str(v[0]) if v else 'Total' for v in row_values]
        datasets = []

        for measure in measures:
            field = measure['field']
            values = []
            for i, _ in enumerate(row_values):
                cell_data = data.get(f"{i},0", {})
                values.append(cell_data.get(field, 0))
            datasets.append({
                'label': measure['label'],
                'data': values,
            })

        return {
            'labels': labels,
            'datasets': datasets,
        }

    def _get_range_chart_data(self):
        """Get chart data from spreadsheet cell range."""
        # This would parse the data_range and extract values
        # For now, return empty
        return {
            'labels': [],
            'datasets': [],
            'source': 'range',
            'range': self.data_range,
        }

    def get_echarts_option(self):
        """
        Generate ECharts configuration option.

        Returns:
            dict: ECharts option configuration
        """
        self.ensure_one()

        data = self.get_chart_data()
        if 'error' in data:
            return data

        option = {
            'title': {
                'text': self.name if self.show_title else '',
                'left': 'center',
            },
            'tooltip': {
                'trigger': 'axis' if self.chart_type in ['bar', 'line', 'area'] else 'item',
            },
            'legend': {
                'show': self.show_legend,
                'orient': 'horizontal',
                'bottom': 0 if self.legend_position == 'bottom' else None,
                'top': 0 if self.legend_position == 'top' else None,
                'left': 0 if self.legend_position == 'left' else None,
                'right': 0 if self.legend_position == 'right' else None,
            },
        }

        # Get colors
        colors = self._get_colors()
        if colors:
            option['color'] = colors

        # Build series based on chart type
        if self.chart_type == 'pie':
            option['series'] = [{
                'type': 'pie',
                'radius': '50%',
                'data': [
                    {'value': v, 'name': n}
                    for n, v in zip(data['labels'], data['datasets'][0]['data'])
                ] if data['datasets'] else [],
                'label': {
                    'show': self.show_data_labels,
                },
            }]
        elif self.chart_type == 'doughnut':
            option['series'] = [{
                'type': 'pie',
                'radius': ['40%', '70%'],
                'data': [
                    {'value': v, 'name': n}
                    for n, v in zip(data['labels'], data['datasets'][0]['data'])
                ] if data['datasets'] else [],
            }]
        else:
            # Bar, line, area
            option['xAxis'] = {
                'type': 'category',
                'data': data['labels'],
            }
            option['yAxis'] = {
                'type': 'value',
            }
            option['series'] = [
                {
                    'name': ds['label'],
                    'type': self.chart_type if self.chart_type != 'area' else 'line',
                    'data': ds['data'],
                    'areaStyle': {} if self.chart_type == 'area' else None,
                    'label': {
                        'show': self.show_data_labels,
                    },
                }
                for ds in data.get('datasets', [])
            ]

        return option

    def _get_colors(self):
        """Get color palette for the chart."""
        if self.color_scheme == 'custom' and self.custom_colors:
            return [c.strip() for c in self.custom_colors.split(',')]

        schemes = {
            'default': ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de'],
            'vibrant': ['#ff6384', '#36a2eb', '#ffce56', '#4bc0c0', '#9966ff'],
            'pastel': ['#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5'],
            'monochrome': ['#1a1a1a', '#4d4d4d', '#808080', '#b3b3b3', '#e6e6e6'],
        }

        return schemes.get(self.color_scheme, schemes['default'])

    def action_preview(self):
        """Open chart preview."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'loomworks_spreadsheet_chart_preview',
            'params': {
                'chart_id': self.id,
                'chart_type': self.chart_type,
                'option': self.get_echarts_option(),
            },
        }
