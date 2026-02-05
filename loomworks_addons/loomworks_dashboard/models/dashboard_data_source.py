# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Dashboard Data Source Model - Connections to Odoo models for widget data.

Data sources provide a reusable way to connect widgets to Odoo data.
They handle:
- Model selection and field mapping
- Domain filtering
- Grouping and aggregation
- Data transformation for charts/tables
"""

from odoo import api, fields, models
from odoo.exceptions import UserError, AccessError
from odoo.osv import expression
import json
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class DashboardDataSource(models.Model):
    """
    Data source definition for dashboard widgets.

    A data source defines how to fetch and transform data from an Odoo model
    for use in dashboard widgets.
    """
    _name = 'dashboard.data.source'
    _description = 'Dashboard Data Source'
    _order = 'name'

    # Basic Information
    name = fields.Char(
        string='Name',
        required=True,
    )
    description = fields.Text(
        string='Description',
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )

    # Source Type
    source_type = fields.Selection([
        ('model', 'Odoo Model'),
        ('sql', 'SQL Query'),
        ('api', 'External API'),
        ('static', 'Static Data'),
    ], string='Source Type', default='model', required=True)

    # Model-based Source
    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        help='Odoo model to fetch data from',
        domain=[('transient', '=', False)],
    )
    model_name = fields.Char(
        string='Model Name',
        related='model_id.model',
        store=True,
    )
    domain = fields.Text(
        string='Domain',
        default='[]',
        help='Domain filter for records',
    )
    field_ids = fields.Many2many(
        'ir.model.fields',
        'dashboard_data_source_field_rel',
        'source_id',
        'field_id',
        string='Fields',
        help='Fields to include in data',
    )

    # Grouping and Aggregation
    group_by_field_id = fields.Many2one(
        'ir.model.fields',
        string='Group By Field',
        help='Field to group records by',
    )
    group_by_granularity = fields.Selection([
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month'),
        ('quarter', 'Quarter'),
        ('year', 'Year'),
    ], string='Date Granularity', default='month',
        help='Granularity for date grouping')
    secondary_group_by_field_id = fields.Many2one(
        'ir.model.fields',
        string='Secondary Group By',
        help='Secondary field for multi-dimensional grouping',
    )
    measure_field_id = fields.Many2one(
        'ir.model.fields',
        string='Measure Field',
        help='Field to aggregate',
    )
    aggregation = fields.Selection([
        ('sum', 'Sum'),
        ('avg', 'Average'),
        ('min', 'Minimum'),
        ('max', 'Maximum'),
        ('count', 'Count'),
        ('count_distinct', 'Count Distinct'),
    ], string='Aggregation', default='sum')

    # Sorting and Limiting
    sort_field = fields.Char(
        string='Sort Field',
        help='Field to sort by',
    )
    sort_direction = fields.Selection([
        ('asc', 'Ascending'),
        ('desc', 'Descending'),
    ], string='Sort Direction', default='desc')
    limit = fields.Integer(
        string='Limit',
        default=0,
        help='Maximum number of records (0 = unlimited)',
    )

    # SQL Query Source
    sql_query = fields.Text(
        string='SQL Query',
        help='Custom SQL query (use with caution)',
    )

    # API Source
    api_endpoint = fields.Char(
        string='API Endpoint',
    )
    api_method = fields.Selection([
        ('GET', 'GET'),
        ('POST', 'POST'),
    ], string='HTTP Method', default='GET')
    api_headers = fields.Text(
        string='API Headers',
        default='{}',
    )
    api_body = fields.Text(
        string='API Body',
    )

    # Static Data Source
    static_data = fields.Text(
        string='Static Data',
        default='[]',
        help='JSON array of data objects',
    )

    # Caching
    cache_duration = fields.Integer(
        string='Cache Duration (seconds)',
        default=300,
        help='How long to cache results (0 = no cache)',
    )
    last_fetch = fields.Datetime(
        string='Last Fetch',
        readonly=True,
    )
    cached_data = fields.Text(
        string='Cached Data',
        readonly=True,
    )

    # Linked Widgets
    widget_ids = fields.One2many(
        'dashboard.widget',
        'data_source_id',
        string='Linked Widgets',
    )

    @api.model
    def fetch_data(self, source_id, filters=None):
        """
        Fetch data from a data source.

        Args:
            source_id: ID of the data source
            filters: dict of filter values from global filters

        Returns:
            dict: Fetched and transformed data
        """
        source = self.browse(source_id)
        if not source.exists():
            raise UserError(f"Data source {source_id} not found")

        # Check cache
        if source.cache_duration > 0 and source.last_fetch and source.cached_data:
            cache_age = (datetime.now() - source.last_fetch).total_seconds()
            if cache_age < source.cache_duration:
                try:
                    return json.loads(source.cached_data)
                except (json.JSONDecodeError, TypeError):
                    _logger.warning("Invalid cached data for source %s, re-fetching", source.id)

        # Fetch based on source type
        if source.source_type == 'model':
            data = source._fetch_model_data(filters)
        elif source.source_type == 'sql':
            data = source._fetch_sql_data(filters)
        elif source.source_type == 'api':
            data = source._fetch_api_data(filters)
        elif source.source_type == 'static':
            data = source._fetch_static_data()
        else:
            raise UserError(f"Unknown source type: {source.source_type}")

        # Update cache
        if source.cache_duration > 0:
            source.sudo().write({
                'last_fetch': datetime.now(),
                'cached_data': json.dumps(data),
            })

        return data

    def _fetch_model_data(self, filters=None):
        """Fetch data from an Odoo model."""
        self.ensure_one()
        if not self.model_id:
            raise UserError("No model configured for data source")

        # Check access rights
        Model = self.env[self.model_name]
        if not Model.check_access_rights('read', raise_exception=False):
            raise AccessError(f"No read access to model {self.model_name}")

        # Build domain
        try:
            domain = json.loads(self.domain or '[]')
        except (json.JSONDecodeError, TypeError):
            _logger.warning("Invalid JSON domain for data source %s", self.id)
            domain = []

        # Apply global filters
        if filters:
            filter_domain = self._build_filter_domain(filters)
            domain = expression.AND([domain, filter_domain])

        # Determine if we need grouping
        if self.group_by_field_id:
            return self._fetch_grouped_data(Model, domain)
        else:
            return self._fetch_flat_data(Model, domain)

    def _fetch_flat_data(self, Model, domain):
        """Fetch flat records without grouping."""
        # Build field list
        field_names = ['id', 'display_name']
        if self.field_ids:
            field_names = [f.name for f in self.field_ids]

        # Build order
        order = None
        if self.sort_field:
            order = f"{self.sort_field} {self.sort_direction}"

        # Fetch records
        records = Model.search_read(
            domain,
            field_names,
            limit=self.limit if self.limit > 0 else None,
            order=order,
        )

        return {
            'type': 'records',
            'data': records,
            'total': Model.search_count(domain),
            'fields': field_names,
        }

    def _fetch_grouped_data(self, Model, domain):
        """Fetch grouped and aggregated data."""
        group_by_field = self.group_by_field_id.name
        field_info = Model.fields_get([group_by_field])

        # Add granularity for date fields
        if field_info.get(group_by_field, {}).get('type') in ('date', 'datetime'):
            group_by = f"{group_by_field}:{self.group_by_granularity}"
        else:
            group_by = group_by_field

        # Build groupby list
        groupby = [group_by]
        if self.secondary_group_by_field_id:
            secondary_field = self.secondary_group_by_field_id.name
            secondary_info = Model.fields_get([secondary_field])
            if secondary_info.get(secondary_field, {}).get('type') in ('date', 'datetime'):
                groupby.append(f"{secondary_field}:{self.group_by_granularity}")
            else:
                groupby.append(secondary_field)

        # Build aggregates
        aggregates = []
        if self.measure_field_id:
            measure_field = self.measure_field_id.name
            agg = self.aggregation or 'sum'
            if agg == 'count_distinct':
                aggregates.append(f"{measure_field}:count_distinct")
            else:
                aggregates.append(f"{measure_field}:{agg}")
        else:
            # Default to count
            aggregates.append("__count")

        # Fetch grouped data
        raw_data = Model.read_group(
            domain,
            aggregates,
            groupby,
            limit=self.limit if self.limit > 0 else None,
            orderby=f"{group_by} {self.sort_direction}" if self.sort_direction else None,
        )

        # Transform for charts
        transformed = self._transform_grouped_data(raw_data, group_by, aggregates)

        return {
            'type': 'grouped',
            'data': transformed,
            'groupBy': group_by,
            'measure': aggregates[0] if aggregates else '__count',
        }

    def _transform_grouped_data(self, raw_data, group_by, aggregates):
        """Transform read_group output for Recharts."""
        result = []
        group_key = group_by.split(':')[0]

        for row in raw_data:
            item = {}

            # Extract group value
            group_value = row.get(group_by)
            if isinstance(group_value, tuple):
                # Many2one field
                item['name'] = group_value[1] if group_value else 'Unknown'
            elif group_value:
                item['name'] = str(group_value)
            else:
                item['name'] = 'Undefined'

            # Extract aggregate values
            for agg in aggregates:
                agg_key = agg.replace(':', '_')
                if agg == '__count':
                    item['value'] = row.get('__count', 0)
                else:
                    item['value'] = row.get(agg_key, 0)

            result.append(item)

        return result

    def _build_filter_domain(self, filters):
        """Build domain from global filter values."""
        filter_domain = []

        for field_name, filter_value in filters.items():
            if filter_value is None:
                continue

            if isinstance(filter_value, dict):
                # Range filter
                if 'from' in filter_value and filter_value['from']:
                    filter_domain.append((field_name, '>=', filter_value['from']))
                if 'to' in filter_value and filter_value['to']:
                    filter_domain.append((field_name, '<=', filter_value['to']))
            elif isinstance(filter_value, list):
                # Multi-select filter
                if filter_value:
                    filter_domain.append((field_name, 'in', filter_value))
            else:
                # Single value filter
                filter_domain.append((field_name, '=', filter_value))

        return filter_domain

    def _fetch_sql_data(self, filters=None):
        """Fetch data from SQL query."""
        self.ensure_one()
        if not self.sql_query:
            raise UserError("No SQL query configured")

        # Security: Only allow SELECT queries
        query_lower = self.sql_query.strip().lower()
        if not query_lower.startswith('select'):
            raise UserError("Only SELECT queries are allowed")

        # Execute query
        self.env.cr.execute(self.sql_query)
        columns = [desc[0] for desc in self.env.cr.description]
        rows = self.env.cr.fetchall()

        # Transform to dicts
        data = [dict(zip(columns, row)) for row in rows]

        return {
            'type': 'sql',
            'data': data,
            'columns': columns,
        }

    def _fetch_api_data(self, filters=None):
        """Fetch data from external API."""
        self.ensure_one()
        if not self.api_endpoint:
            raise UserError("No API endpoint configured")

        import requests

        try:
            headers = json.loads(self.api_headers or '{}')
        except (json.JSONDecodeError, TypeError):
            _logger.warning("Invalid JSON in api_headers for source %s", self.id)
            headers = {}

        try:
            if self.api_method == 'GET':
                response = requests.get(self.api_endpoint, headers=headers, timeout=30)
            else:
                try:
                    body = json.loads(self.api_body or '{}')
                except (json.JSONDecodeError, TypeError):
                    _logger.warning("Invalid JSON in api_body for source %s", self.id)
                    body = {}
                response = requests.post(
                    self.api_endpoint, headers=headers, json=body, timeout=30
                )

            response.raise_for_status()
            data = response.json()

            return {
                'type': 'api',
                'data': data,
            }
        except Exception as e:
            _logger.error("API fetch failed for source %s: %s", self.id, e)
            raise UserError(f"Failed to fetch API data: {e}")

    def _fetch_static_data(self):
        """Return static data."""
        self.ensure_one()
        try:
            static = json.loads(self.static_data or '[]')
        except (json.JSONDecodeError, TypeError):
            _logger.warning("Invalid JSON in static_data for source %s", self.id)
            static = []
        return {
            'type': 'static',
            'data': static,
        }

    def clear_cache(self):
        """Clear cached data."""
        self.write({
            'last_fetch': False,
            'cached_data': False,
        })

    def action_test_fetch(self):
        """Test data fetch and show results."""
        self.ensure_one()
        try:
            data = self.fetch_data(self.id)
            message = f"Success! Fetched {len(data.get('data', []))} items."
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Data Source Test',
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Data Source Test Failed',
                    'message': str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }
