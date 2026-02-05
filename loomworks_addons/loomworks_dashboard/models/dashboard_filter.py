# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Dashboard Filter Model - Global filters affecting multiple widgets.

Filters allow users to dynamically filter dashboard data without editing
widget configurations. A filter affects all connected widgets.
"""

from odoo import api, fields, models
import json
import logging

_logger = logging.getLogger(__name__)


class DashboardFilter(models.Model):
    """
    Global dashboard filter.

    Filters connect to multiple widgets and provide a unified way
    to filter data across the dashboard.
    """
    _name = 'dashboard.filter'
    _description = 'Dashboard Filter'
    _order = 'sequence, id'

    # Basic Information
    name = fields.Char(
        string='Filter Name',
        required=True,
    )
    dashboard_id = fields.Many2one(
        'dashboard.board',
        string='Dashboard',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )

    # Filter Configuration
    field_name = fields.Char(
        string='Field Name',
        required=True,
        help='Field this filter controls (e.g., date_order, state)',
    )
    filter_type = fields.Selection([
        ('select', 'Dropdown'),
        ('multiselect', 'Multi-Select'),
        ('date_range', 'Date Range'),
        ('number_range', 'Number Range'),
        ('search', 'Text Search'),
        ('boolean', 'Yes/No Toggle'),
    ], string='Filter Type', default='select', required=True)

    # Display Configuration
    label = fields.Char(
        string='Display Label',
        help='Label shown to users (defaults to field label)',
    )
    placeholder = fields.Char(
        string='Placeholder',
        help='Placeholder text for input',
    )
    icon = fields.Char(
        string='Icon',
        help='FontAwesome icon class',
    )

    # Options for Select/Multiselect
    options_source = fields.Selection([
        ('model', 'From Model'),
        ('selection', 'From Selection Field'),
        ('static', 'Static Options'),
    ], string='Options Source', default='model')
    options_model_id = fields.Many2one(
        'ir.model',
        string='Options Model',
        help='Model to fetch options from',
        ondelete='cascade',
    )
    options_domain = fields.Text(
        string='Options Domain',
        default='[]',
        help='Domain to filter options',
    )
    options_display_field = fields.Char(
        string='Display Field',
        default='name',
        help='Field to show as option label',
    )
    static_options = fields.Text(
        string='Static Options',
        default='[]',
        help='JSON array of {value, label} objects',
    )

    # Range Configuration
    range_min = fields.Float(
        string='Minimum',
        help='Minimum value for number range',
    )
    range_max = fields.Float(
        string='Maximum',
        help='Maximum value for number range',
    )
    range_step = fields.Float(
        string='Step',
        default=1,
        help='Step increment for number range',
    )

    # Date Range Presets
    date_presets = fields.Selection([
        ('none', 'No Presets'),
        ('standard', 'Standard (Today, Week, Month, Year)'),
        ('custom', 'Custom Presets'),
    ], string='Date Presets', default='standard')
    custom_date_presets = fields.Text(
        string='Custom Date Presets',
        default='[]',
        help='JSON array of {name, from, to} objects',
    )

    # Default Value
    default_value = fields.Text(
        string='Default Value',
        help='JSON encoded default value',
    )

    # Affected Widgets
    affected_widget_ids = fields.Many2many(
        'dashboard.widget',
        'dashboard_filter_widget_rel',
        'filter_id',
        'widget_id',
        string='Affected Widgets',
        help='Widgets that are filtered by this filter',
    )

    def _safe_json_loads(self, value, default=None):
        """Safely parse a JSON string, returning default on failure."""
        if not value:
            return default
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            _logger.warning(
                "Invalid JSON in field for filter %s: %.100s", self.id, value
            )
            return default

    def get_filter_data(self):
        """
        Get filter data for React canvas.

        Returns:
            dict: Filter configuration for React
        """
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'fieldName': self.field_name,
            'type': self.filter_type,
            'label': self.label or self.name,
            'placeholder': self.placeholder,
            'icon': self.icon,
            'options': self._get_filter_options(),
            'range': {
                'min': self.range_min,
                'max': self.range_max,
                'step': self.range_step,
            } if self.filter_type in ('number_range',) else None,
            'datePresets': self._get_date_presets(),
            'defaultValue': self._safe_json_loads(self.default_value) if self.default_value else None,
            'affectedWidgetIds': self.affected_widget_ids.ids,
        }

    def _get_filter_options(self):
        """Get options for select/multiselect filters."""
        if self.filter_type not in ('select', 'multiselect'):
            return []

        if self.options_source == 'static':
            return self._safe_json_loads(self.static_options, [])

        elif self.options_source == 'model':
            if not self.options_model_id:
                return []

            Model = self.env[self.options_model_id.model]
            domain = self._safe_json_loads(self.options_domain, [])
            display_field = self.options_display_field or 'name'

            records = Model.search_read(
                domain,
                ['id', display_field],
                limit=1000,
                order=display_field,
            )

            return [
                {'value': r['id'], 'label': r[display_field]}
                for r in records
            ]

        elif self.options_source == 'selection':
            # Get selection options from the field
            # This requires knowing the model context
            return []

        return []

    def _get_date_presets(self):
        """Get date range presets."""
        if self.filter_type != 'date_range':
            return None

        if self.date_presets == 'none':
            return []

        if self.date_presets == 'custom':
            return self._safe_json_loads(self.custom_date_presets, [])

        # Standard presets
        from datetime import date, timedelta

        today = date.today()
        presets = [
            {
                'name': 'Today',
                'from': today.isoformat(),
                'to': today.isoformat(),
            },
            {
                'name': 'Yesterday',
                'from': (today - timedelta(days=1)).isoformat(),
                'to': (today - timedelta(days=1)).isoformat(),
            },
            {
                'name': 'This Week',
                'from': (today - timedelta(days=today.weekday())).isoformat(),
                'to': today.isoformat(),
            },
            {
                'name': 'Last Week',
                'from': (today - timedelta(days=today.weekday() + 7)).isoformat(),
                'to': (today - timedelta(days=today.weekday() + 1)).isoformat(),
            },
            {
                'name': 'This Month',
                'from': today.replace(day=1).isoformat(),
                'to': today.isoformat(),
            },
            {
                'name': 'Last Month',
                'from': (today.replace(day=1) - timedelta(days=1)).replace(day=1).isoformat(),
                'to': (today.replace(day=1) - timedelta(days=1)).isoformat(),
            },
            {
                'name': 'This Year',
                'from': today.replace(month=1, day=1).isoformat(),
                'to': today.isoformat(),
            },
            {
                'name': 'Last 30 Days',
                'from': (today - timedelta(days=30)).isoformat(),
                'to': today.isoformat(),
            },
            {
                'name': 'Last 90 Days',
                'from': (today - timedelta(days=90)).isoformat(),
                'to': today.isoformat(),
            },
        ]

        return presets

    def update_from_canvas(self, filter_data):
        """
        Update filter from React canvas data.

        Args:
            filter_data: dict with filter configuration from React
        """
        self.ensure_one()
        vals = {}

        if 'name' in filter_data:
            vals['name'] = filter_data['name']
        if 'fieldName' in filter_data:
            vals['field_name'] = filter_data['fieldName']
        if 'type' in filter_data:
            vals['filter_type'] = filter_data['type']
        if 'label' in filter_data:
            vals['label'] = filter_data['label']
        if 'affectedWidgetIds' in filter_data:
            vals['affected_widget_ids'] = [(6, 0, filter_data['affectedWidgetIds'])]
        if 'defaultValue' in filter_data:
            vals['default_value'] = json.dumps(filter_data['defaultValue'])

        if vals:
            self.write(vals)

    @api.model
    def create_from_canvas(self, dashboard_id, filter_data):
        """
        Create a new filter from React canvas data.

        Args:
            dashboard_id: ID of parent dashboard
            filter_data: dict with filter configuration from React

        Returns:
            dashboard.filter record
        """
        vals = {
            'dashboard_id': dashboard_id,
            'name': filter_data.get('name', 'New Filter'),
            'field_name': filter_data.get('fieldName', ''),
            'filter_type': filter_data.get('type', 'select'),
            'label': filter_data.get('label'),
            'default_value': json.dumps(filter_data.get('defaultValue')) if filter_data.get('defaultValue') else None,
        }

        if 'affectedWidgetIds' in filter_data:
            vals['affected_widget_ids'] = [(6, 0, filter_data['affectedWidgetIds'])]

        return self.create(vals)
