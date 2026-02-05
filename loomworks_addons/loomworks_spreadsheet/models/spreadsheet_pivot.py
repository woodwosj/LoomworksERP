# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Spreadsheet Pivot Model - Pivot table configurations.

Defines pivot table structure with rows, columns, measures,
and filters for dynamic data analysis.
"""

import json
import logging

from odoo import api, models, fields, _
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class SpreadsheetPivot(models.Model):
    """
    Pivot table definition for spreadsheets.

    Stores the configuration for a pivot table that summarizes
    Odoo data with grouping and aggregation.
    """
    _name = 'spreadsheet.pivot'
    _description = 'Spreadsheet Pivot Table'
    _order = 'name'

    name = fields.Char(
        string='Name',
        required=True
    )
    document_id = fields.Many2one(
        'spreadsheet.document',
        string='Spreadsheet',
        required=True,
        ondelete='cascade'
    )
    active = fields.Boolean(default=True)

    # Data Source
    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        required=True,
        ondelete='cascade'
    )
    model_name = fields.Char(
        related='model_id.model',
        store=True
    )
    domain = fields.Char(
        string='Filter Domain',
        default='[]'
    )

    # Pivot Configuration
    row_field_ids = fields.Many2many(
        'ir.model.fields',
        'spreadsheet_pivot_row_field_rel',
        'pivot_id',
        'field_id',
        string='Row Fields',
        help="Fields to group by in rows"
    )
    column_field_ids = fields.Many2many(
        'ir.model.fields',
        'spreadsheet_pivot_col_field_rel',
        'pivot_id',
        'field_id',
        string='Column Fields',
        help="Fields to group by in columns"
    )
    measure_ids = fields.One2many(
        'spreadsheet.pivot.measure',
        'pivot_id',
        string='Measures'
    )

    # Display Options
    show_totals = fields.Boolean(
        string='Show Totals',
        default=True
    )
    show_empty = fields.Boolean(
        string='Show Empty Values',
        default=False
    )
    collapsed = fields.Boolean(
        string='Start Collapsed',
        default=False
    )

    # Target Location
    target_sheet = fields.Char(
        string='Target Sheet',
        default='sheet1'
    )
    target_cell = fields.Char(
        string='Target Cell',
        default='A1'
    )

    # Cached Data
    cached_data = fields.Text(
        string='Cached Data',
        help="JSON cache of pivot results"
    )
    last_computed = fields.Datetime(
        string='Last Computed'
    )

    def compute_pivot(self):
        """
        Compute the pivot table data.

        Returns:
            dict: Pivot data structure
        """
        self.ensure_one()

        if not self.model_name or self.model_name not in self.env:
            return {'error': f"Model '{self.model_name}' not found"}

        Model = self.env[self.model_name]

        # Parse domain
        domain = safe_eval(self.domain or '[]')

        # Get field names
        row_fields = self.row_field_ids.mapped('name')
        col_fields = self.column_field_ids.mapped('name')

        # Prepare measures
        measures = []
        for measure in self.measure_ids:
            measures.append({
                'field': measure.field_id.name,
                'aggregator': measure.aggregator,
                'label': measure.name or measure.field_id.field_description,
            })

        if not measures:
            # Default measure: count
            measures = [{'field': '__count', 'aggregator': 'count', 'label': 'Count'}]

        # Build groupby
        groupby = row_fields + col_fields

        # Prepare aggregation fields
        agg_fields = []
        for m in measures:
            if m['field'] != '__count':
                agg_fields.append(f"{m['field']}:{m['aggregator']}")

        # Execute read_group
        try:
            if groupby:
                results = Model.read_group(
                    domain,
                    agg_fields or ['id'],
                    groupby,
                    lazy=False
                )
            else:
                # No grouping - aggregate all
                results = [Model.read_group(domain, agg_fields or ['id'], [])[0]]
        except Exception as e:
            _logger.error("Pivot computation failed: %s", e)
            return {'error': str(e)}

        # Process results into pivot structure
        pivot_data = self._process_pivot_results(
            results,
            row_fields,
            col_fields,
            measures
        )

        # Cache results
        self.write({
            'cached_data': json.dumps(pivot_data),
            'last_computed': fields.Datetime.now(),
        })

        return pivot_data

    def _process_pivot_results(self, results, row_fields, col_fields, measures):
        """
        Process read_group results into pivot table structure.

        Args:
            results: read_group results
            row_fields: List of row field names
            col_fields: List of column field names
            measures: List of measure definitions

        Returns:
            dict: Pivot table data
        """
        # Build unique row and column values
        row_values = []
        col_values = []
        data_matrix = {}

        for record in results:
            # Extract row key
            row_key = tuple(
                self._get_group_value(record, f) for f in row_fields
            )
            if row_key not in row_values:
                row_values.append(row_key)

            # Extract column key
            col_key = tuple(
                self._get_group_value(record, f) for f in col_fields
            )
            if col_key not in col_values:
                col_values.append(col_key)

            # Store measure values
            cell_key = (row_key, col_key)
            data_matrix[cell_key] = {}
            for measure in measures:
                field = measure['field']
                if field == '__count':
                    data_matrix[cell_key][field] = record.get('__count', 0)
                else:
                    data_matrix[cell_key][field] = record.get(field, 0)

        # Build pivot structure
        return {
            'rows': {
                'fields': row_fields,
                'values': [list(v) for v in row_values],
            },
            'columns': {
                'fields': col_fields,
                'values': [list(v) for v in col_values],
            },
            'measures': measures,
            'data': {
                f"{i},{j}": data_matrix.get((row_values[i], col_values[j]), {})
                for i, _ in enumerate(row_values)
                for j, _ in enumerate(col_values)
                if (row_values[i], col_values[j]) in data_matrix
            } if row_values and col_values else {},
            'totals': self._compute_totals(data_matrix, row_values, col_values, measures)
            if self.show_totals else {},
        }

    def _get_group_value(self, record, field_name):
        """Extract group value from read_group record."""
        value = record.get(field_name)
        if isinstance(value, tuple):
            return value[1]  # Display name
        if value is False:
            return 'N/A'
        return value

    def _compute_totals(self, data_matrix, row_values, col_values, measures):
        """Compute row, column, and grand totals."""
        totals = {
            'row': {},
            'column': {},
            'grand': {},
        }

        # Initialize grand totals
        for measure in measures:
            field = measure['field']
            totals['grand'][field] = 0

        # Row totals
        for i, row_key in enumerate(row_values):
            totals['row'][i] = {}
            for measure in measures:
                field = measure['field']
                total = sum(
                    data_matrix.get((row_key, col_key), {}).get(field, 0)
                    for col_key in col_values
                )
                totals['row'][i][field] = total
                totals['grand'][field] += total

        # Column totals
        for j, col_key in enumerate(col_values):
            totals['column'][j] = {}
            for measure in measures:
                field = measure['field']
                totals['column'][j][field] = sum(
                    data_matrix.get((row_key, col_key), {}).get(field, 0)
                    for row_key in row_values
                )

        return totals

    def action_refresh(self):
        """Refresh the pivot table data."""
        self.ensure_one()
        data = self.compute_pivot()
        if 'error' in data:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Pivot Error'),
                    'message': data['error'],
                    'type': 'danger',
                }
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Pivot Refreshed'),
                'message': _('Data updated successfully'),
                'type': 'success',
            }
        }


class SpreadsheetPivotMeasure(models.Model):
    """Measure definition for pivot tables."""
    _name = 'spreadsheet.pivot.measure'
    _description = 'Pivot Table Measure'
    _order = 'sequence'

    pivot_id = fields.Many2one(
        'spreadsheet.pivot',
        string='Pivot',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(
        string='Label',
        help="Custom label for the measure"
    )

    field_id = fields.Many2one(
        'ir.model.fields',
        string='Field',
        required=True,
        domain="[('model_id', '=', parent.model_id), ('ttype', 'in', ['integer', 'float', 'monetary'])]",
        ondelete='cascade'
    )
    aggregator = fields.Selection([
        ('sum', 'Sum'),
        ('avg', 'Average'),
        ('min', 'Minimum'),
        ('max', 'Maximum'),
        ('count', 'Count'),
    ], string='Aggregation', default='sum', required=True)

    format_type = fields.Selection([
        ('number', 'Number'),
        ('currency', 'Currency'),
        ('percentage', 'Percentage'),
    ], string='Format', default='number')
    decimal_places = fields.Integer(
        string='Decimal Places',
        default=2
    )
