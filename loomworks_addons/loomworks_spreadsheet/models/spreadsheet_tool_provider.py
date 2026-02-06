# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Spreadsheet AI Tool Provider - Implements M4 pattern for AI tool registration.

This provider registers Spreadsheet-specific tools that allow AI agents to:
- Create and manage spreadsheets
- Insert Odoo data into spreadsheets
- Create pivot tables and charts
"""

import json
import logging

from loomworks import api, models

_logger = logging.getLogger(__name__)


class SpreadsheetToolProvider(models.AbstractModel):
    """
    AI Tool Provider for Loomworks Spreadsheet.

    Provides tools for AI-assisted data analysis:
    - spreadsheet_create: Create new spreadsheets
    - spreadsheet_insert_data: Add Odoo data to spreadsheet
    - spreadsheet_create_pivot: Build pivot tables
    - spreadsheet_create_chart: Generate visualizations
    - spreadsheet_list: List user's spreadsheets
    """
    _name = 'loomworks.spreadsheet.tool.provider'
    _inherit = 'loomworks.ai.tool.provider'
    _description = 'Spreadsheet AI Tool Provider'

    @api.model
    def _get_tool_definitions(self):
        """Return Spreadsheet tool definitions for AI registration."""
        return [
            # Document Management
            {
                'name': 'Create Spreadsheet',
                'technical_name': 'spreadsheet_create',
                'category': 'action',
                'description': (
                    'Create a new spreadsheet document. '
                    'Returns the document ID which can be used for further operations.'
                ),
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'name': {
                            'type': 'string',
                            'description': 'Name for the spreadsheet'
                        },
                        'description': {
                            'type': 'string',
                            'description': 'Optional description'
                        },
                    },
                    'required': ['name']
                },
                'implementation_method': 'loomworks_spreadsheet.tool_provider._execute_create',
                'risk_level': 'safe',
                'returns_description': 'Created spreadsheet ID and name',
            },
            {
                'name': 'List Spreadsheets',
                'technical_name': 'spreadsheet_list',
                'category': 'data',
                'description': 'List all spreadsheets accessible to the current user.',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'limit': {
                            'type': 'integer',
                            'default': 20
                        },
                        'search': {
                            'type': 'string',
                            'description': 'Search term for name'
                        },
                    },
                },
                'implementation_method': 'loomworks_spreadsheet.tool_provider._execute_list',
                'risk_level': 'safe',
                'returns_description': 'List of spreadsheets with basic info',
            },
            # Data Operations
            {
                'name': 'Insert Odoo Data',
                'technical_name': 'spreadsheet_insert_data',
                'category': 'action',
                'description': (
                    'Insert data from an Odoo model into a spreadsheet. '
                    'Creates a data source and populates cells with the fetched records.'
                ),
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'document_id': {
                            'type': 'integer',
                            'description': 'ID of the spreadsheet document'
                        },
                        'model': {
                            'type': 'string',
                            'description': 'Odoo model name (e.g., res.partner)'
                        },
                        'fields': {
                            'type': 'array',
                            'items': {'type': 'string'},
                            'description': 'List of field names to include'
                        },
                        'domain': {
                            'type': 'string',
                            'description': 'Domain filter (e.g., "[(\'active\', \'=\', True)]")',
                            'default': '[]'
                        },
                        'target_cell': {
                            'type': 'string',
                            'description': 'Starting cell (e.g., A1)',
                            'default': 'A1'
                        },
                        'limit': {
                            'type': 'integer',
                            'default': 1000
                        },
                    },
                    'required': ['document_id', 'model', 'fields']
                },
                'implementation_method': 'loomworks_spreadsheet.tool_provider._execute_insert_data',
                'risk_level': 'safe',
                'returns_description': 'Number of records inserted',
            },
            # Pivot Tables
            {
                'name': 'Create Pivot Table',
                'technical_name': 'spreadsheet_create_pivot',
                'category': 'action',
                'description': (
                    'Create a pivot table in a spreadsheet from Odoo data. '
                    'Supports grouping by rows and columns with various aggregations.'
                ),
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'document_id': {
                            'type': 'integer',
                            'description': 'Spreadsheet document ID'
                        },
                        'name': {
                            'type': 'string',
                            'description': 'Name for the pivot table'
                        },
                        'model': {
                            'type': 'string',
                            'description': 'Odoo model name'
                        },
                        'row_fields': {
                            'type': 'array',
                            'items': {'type': 'string'},
                            'description': 'Fields to group by in rows'
                        },
                        'column_fields': {
                            'type': 'array',
                            'items': {'type': 'string'},
                            'description': 'Fields to group by in columns (optional)'
                        },
                        'measures': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'field': {'type': 'string'},
                                    'aggregator': {
                                        'type': 'string',
                                        'enum': ['sum', 'avg', 'count', 'min', 'max']
                                    },
                                }
                            },
                            'description': 'Measure definitions'
                        },
                        'domain': {
                            'type': 'string',
                            'default': '[]'
                        },
                    },
                    'required': ['document_id', 'name', 'model', 'row_fields']
                },
                'implementation_method': 'loomworks_spreadsheet.tool_provider._execute_create_pivot',
                'risk_level': 'safe',
                'returns_description': 'Created pivot table ID',
            },
            # Charts
            {
                'name': 'Create Chart',
                'technical_name': 'spreadsheet_create_chart',
                'category': 'action',
                'description': (
                    'Create a chart in a spreadsheet from Odoo data. '
                    'Supports bar, line, pie, and other chart types.'
                ),
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'document_id': {
                            'type': 'integer',
                            'description': 'Spreadsheet document ID'
                        },
                        'name': {
                            'type': 'string',
                            'description': 'Chart title'
                        },
                        'chart_type': {
                            'type': 'string',
                            'enum': ['bar', 'line', 'pie', 'doughnut', 'area'],
                            'description': 'Type of chart'
                        },
                        'model': {
                            'type': 'string',
                            'description': 'Odoo model for data'
                        },
                        'groupby_field': {
                            'type': 'string',
                            'description': 'Field to group by (x-axis/labels)'
                        },
                        'measure_field': {
                            'type': 'string',
                            'description': 'Field to measure (y-axis/values)'
                        },
                        'aggregator': {
                            'type': 'string',
                            'enum': ['sum', 'avg', 'count'],
                            'default': 'sum'
                        },
                        'domain': {
                            'type': 'string',
                            'default': '[]'
                        },
                    },
                    'required': ['document_id', 'name', 'chart_type', 'model', 'groupby_field']
                },
                'implementation_method': 'loomworks_spreadsheet.tool_provider._execute_create_chart',
                'risk_level': 'safe',
                'returns_description': 'Created chart ID and preview data',
            },
        ]

    # ---------------------------------
    # Tool Implementation Methods
    # ---------------------------------

    @api.model
    def _execute_create(self, params):
        """Create a new spreadsheet document."""
        Document = self.env['spreadsheet.document']

        doc = Document.create({
            'name': params['name'],
            'description': params.get('description', ''),
        })

        return {
            'success': True,
            'document_id': doc.id,
            'name': doc.name,
            'message': f"Created spreadsheet '{doc.name}' (ID: {doc.id})"
        }

    @api.model
    def _execute_list(self, params):
        """List spreadsheets."""
        Document = self.env['spreadsheet.document']

        domain = []
        if params.get('search'):
            domain.append(('name', 'ilike', params['search']))

        limit = params.get('limit', 20)
        docs = Document.search(domain, limit=limit, order='write_date desc')

        result = []
        for doc in docs:
            result.append({
                'id': doc.id,
                'name': doc.name,
                'description': doc.description,
                'sheet_count': doc.sheet_count,
                'data_source_count': doc.data_source_count,
                'last_modified': doc.last_modified.isoformat() if doc.last_modified else None,
            })

        return {
            'success': True,
            'spreadsheets': result,
            'count': len(result),
        }

    @api.model
    def _execute_insert_data(self, params):
        """Insert Odoo data into a spreadsheet."""
        Document = self.env['spreadsheet.document']
        DataSource = self.env['spreadsheet.data.source']
        IrModel = self.env['ir.model']
        IrModelFields = self.env['ir.model.fields']

        # Get document
        doc = Document.browse(params['document_id'])
        if not doc.exists():
            return {'success': False, 'error': f"Document {params['document_id']} not found"}

        # Get model
        model_name = params['model']
        ir_model = IrModel.search([('model', '=', model_name)], limit=1)
        if not ir_model:
            return {'success': False, 'error': f"Model '{model_name}' not found"}

        # Get fields
        field_names = params['fields']
        field_ids = IrModelFields.search([
            ('model', '=', model_name),
            ('name', 'in', field_names)
        ])

        # Create data source
        data_source = DataSource.create({
            'name': f"AI Data: {model_name}",
            'document_id': doc.id,
            'source_type': 'model',
            'model_id': ir_model.id,
            'domain': params.get('domain', '[]'),
            'field_ids': [(6, 0, field_ids.ids)],
            'target_cell': params.get('target_cell', 'A1'),
            'limit': params.get('limit', 1000),
        })

        # Insert data into spreadsheet
        data_source.insert_into_spreadsheet()

        return {
            'success': True,
            'data_source_id': data_source.id,
            'record_count': data_source.record_count,
            'message': f"Inserted {data_source.record_count} records into spreadsheet"
        }

    @api.model
    def _execute_create_pivot(self, params):
        """Create a pivot table in a spreadsheet."""
        Document = self.env['spreadsheet.document']
        Pivot = self.env['spreadsheet.pivot']
        IrModel = self.env['ir.model']
        IrModelFields = self.env['ir.model.fields']

        # Get document
        doc = Document.browse(params['document_id'])
        if not doc.exists():
            return {'success': False, 'error': f"Document {params['document_id']} not found"}

        # Get model
        model_name = params['model']
        ir_model = IrModel.search([('model', '=', model_name)], limit=1)
        if not ir_model:
            return {'success': False, 'error': f"Model '{model_name}' not found"}

        # Get row fields
        row_field_ids = IrModelFields.search([
            ('model', '=', model_name),
            ('name', 'in', params['row_fields'])
        ])

        # Get column fields
        col_field_ids = IrModelFields.search([
            ('model', '=', model_name),
            ('name', 'in', params.get('column_fields', []))
        ])

        # Create pivot
        pivot = Pivot.create({
            'name': params['name'],
            'document_id': doc.id,
            'model_id': ir_model.id,
            'domain': params.get('domain', '[]'),
            'row_field_ids': [(6, 0, row_field_ids.ids)],
            'column_field_ids': [(6, 0, col_field_ids.ids)],
        })

        # Create measures
        PivotMeasure = self.env['spreadsheet.pivot.measure']
        for measure_def in params.get('measures', []):
            field = IrModelFields.search([
                ('model', '=', model_name),
                ('name', '=', measure_def['field'])
            ], limit=1)
            if field:
                PivotMeasure.create({
                    'pivot_id': pivot.id,
                    'field_id': field.id,
                    'aggregator': measure_def.get('aggregator', 'sum'),
                })

        # Compute pivot
        pivot_data = pivot.compute_pivot()

        return {
            'success': True,
            'pivot_id': pivot.id,
            'name': pivot.name,
            'row_count': len(pivot_data.get('rows', {}).get('values', [])),
            'message': f"Created pivot table '{pivot.name}'"
        }

    @api.model
    def _execute_create_chart(self, params):
        """Create a chart in a spreadsheet."""
        Document = self.env['spreadsheet.document']
        Chart = self.env['spreadsheet.chart']
        IrModel = self.env['ir.model']
        IrModelFields = self.env['ir.model.fields']

        # Get document
        doc = Document.browse(params['document_id'])
        if not doc.exists():
            return {'success': False, 'error': f"Document {params['document_id']} not found"}

        # Get model
        model_name = params['model']
        ir_model = IrModel.search([('model', '=', model_name)], limit=1)
        if not ir_model:
            return {'success': False, 'error': f"Model '{model_name}' not found"}

        # Get fields
        groupby_field = IrModelFields.search([
            ('model', '=', model_name),
            ('name', '=', params['groupby_field'])
        ], limit=1)

        measure_field = None
        if params.get('measure_field'):
            measure_field = IrModelFields.search([
                ('model', '=', model_name),
                ('name', '=', params['measure_field'])
            ], limit=1)

        # Create chart
        chart = Chart.create({
            'name': params['name'],
            'document_id': doc.id,
            'chart_type': params['chart_type'],
            'source_type': 'model',
            'model_id': ir_model.id,
            'domain': params.get('domain', '[]'),
            'groupby_field_id': groupby_field.id if groupby_field else None,
            'measure_field_id': measure_field.id if measure_field else None,
            'measure_aggregator': params.get('aggregator', 'sum'),
        })

        # Get chart data for preview
        chart_data = chart.get_chart_data()

        return {
            'success': True,
            'chart_id': chart.id,
            'name': chart.name,
            'chart_type': chart.chart_type,
            'preview': chart_data,
            'message': f"Created {params['chart_type']} chart '{chart.name}'"
        }
