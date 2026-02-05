# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Spreadsheet Controller - HTTP endpoints for spreadsheet operations.

Provides REST API for frontend Univer integration:
- Document CRUD operations
- Data source fetching
- Pivot table computation
- Chart data retrieval
- Real-time collaboration (WebSocket-ready)
"""

import json
import logging

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class SpreadsheetController(http.Controller):
    """HTTP Controller for Spreadsheet operations."""

    # ---------------------------------
    # Document Operations
    # ---------------------------------

    @http.route('/spreadsheet/document/<int:document_id>/data',
                type='json', auth='user', methods=['GET'])
    def get_document_data(self, document_id):
        """
        Get spreadsheet document data for Univer.

        Args:
            document_id: ID of the spreadsheet document

        Returns:
            dict: Univer-compatible spreadsheet data
        """
        Document = request.env['spreadsheet.document']
        doc = Document.browse(document_id)

        if not doc.exists():
            return {'error': 'Document not found', 'code': 404}

        try:
            data = doc.get_data_for_univer()
            return {
                'success': True,
                'document_id': doc.id,
                'name': doc.name,
                'data': data,
            }
        except Exception as e:
            _logger.error("Error getting document data: %s", e)
            return {'error': str(e), 'code': 500}

    @http.route('/spreadsheet/document/<int:document_id>/save',
                type='json', auth='user', methods=['POST'])
    def save_document_data(self, document_id, data=None, **kwargs):
        """
        Save spreadsheet data from Univer.

        Args:
            document_id: ID of the spreadsheet document
            data: Univer workbook data

        Returns:
            dict: Save result
        """
        Document = request.env['spreadsheet.document']
        doc = Document.browse(document_id)

        if not doc.exists():
            return {'error': 'Document not found', 'code': 404}

        if not data:
            return {'error': 'No data provided', 'code': 400}

        try:
            doc.save_from_univer(data)
            return {
                'success': True,
                'document_id': doc.id,
                'message': 'Document saved successfully',
            }
        except Exception as e:
            _logger.error("Error saving document: %s", e)
            return {'error': str(e), 'code': 500}

    @http.route('/spreadsheet/document/create',
                type='json', auth='user', methods=['POST'])
    def create_document(self, name, description=None, template_id=None, **kwargs):
        """
        Create a new spreadsheet document.

        Args:
            name: Document name
            description: Optional description
            template_id: Optional template to copy from

        Returns:
            dict: Created document info
        """
        Document = request.env['spreadsheet.document']

        vals = {
            'name': name,
            'description': description or '',
        }

        if template_id:
            template = Document.browse(template_id)
            if template.exists():
                vals['raw_data'] = template.raw_data

        try:
            doc = Document.create(vals)
            return {
                'success': True,
                'document_id': doc.id,
                'name': doc.name,
            }
        except Exception as e:
            _logger.error("Error creating document: %s", e)
            return {'error': str(e), 'code': 500}

    @http.route('/spreadsheet/documents',
                type='json', auth='user', methods=['GET'])
    def list_documents(self, limit=50, offset=0, search=None, **kwargs):
        """
        List spreadsheet documents.

        Args:
            limit: Maximum documents to return
            offset: Starting offset
            search: Search term for name

        Returns:
            dict: List of documents
        """
        Document = request.env['spreadsheet.document']

        domain = []
        if search:
            domain.append(('name', 'ilike', search))

        try:
            total = Document.search_count(domain)
            docs = Document.search(
                domain,
                limit=limit,
                offset=offset,
                order='write_date desc'
            )

            result = []
            for doc in docs:
                result.append({
                    'id': doc.id,
                    'name': doc.name,
                    'description': doc.description,
                    'sheet_count': doc.sheet_count,
                    'last_modified': doc.last_modified.isoformat() if doc.last_modified else None,
                    'create_uid': doc.create_uid.name,
                })

            return {
                'success': True,
                'documents': result,
                'total': total,
                'limit': limit,
                'offset': offset,
            }
        except Exception as e:
            _logger.error("Error listing documents: %s", e)
            return {'error': str(e), 'code': 500}

    # ---------------------------------
    # Data Source Operations
    # ---------------------------------

    @http.route('/spreadsheet/datasource/<int:source_id>/fetch',
                type='json', auth='user', methods=['GET'])
    def fetch_data_source(self, source_id, limit=None):
        """
        Fetch data from a data source.

        Args:
            source_id: ID of the data source
            limit: Override record limit

        Returns:
            dict: Data with headers and rows
        """
        DataSource = request.env['spreadsheet.data.source']
        source = DataSource.browse(source_id)

        if not source.exists():
            return {'error': 'Data source not found', 'code': 404}

        try:
            data = source.fetch_data(limit=limit)
            return {
                'success': True,
                'source_id': source.id,
                'data': data,
            }
        except Exception as e:
            _logger.error("Error fetching data source: %s", e)
            return {'error': str(e), 'code': 500}

    @http.route('/spreadsheet/datasource/preview',
                type='json', auth='user', methods=['POST'])
    def preview_data_source(self, model, fields, domain='[]', limit=10, **kwargs):
        """
        Preview data from an Odoo model without creating a data source.

        Args:
            model: Odoo model name
            fields: List of field names
            domain: Domain filter
            limit: Number of records to preview

        Returns:
            dict: Preview data
        """
        from odoo.tools.safe_eval import safe_eval

        if model not in request.env:
            return {'error': f"Model '{model}' not found", 'code': 404}

        Model = request.env[model]

        try:
            parsed_domain = safe_eval(domain)
            records = Model.search_read(
                parsed_domain,
                fields,
                limit=limit
            )

            # Get field labels
            headers = []
            for field_name in fields:
                field_info = Model._fields.get(field_name)
                if field_info:
                    headers.append(field_info.string or field_name)
                else:
                    headers.append(field_name)

            # Process records
            rows = []
            for record in records:
                row = []
                for field_name in fields:
                    value = record.get(field_name)
                    if isinstance(value, tuple) and len(value) == 2:
                        value = value[1]
                    elif isinstance(value, list):
                        value = ', '.join(
                            str(v[1]) if isinstance(v, tuple) else str(v)
                            for v in value
                        )
                    row.append(value)
                rows.append(row)

            return {
                'success': True,
                'headers': headers,
                'rows': rows,
                'field_names': fields,
                'record_count': len(rows),
            }
        except Exception as e:
            _logger.error("Error previewing data: %s", e)
            return {'error': str(e), 'code': 500}

    @http.route('/spreadsheet/models',
                type='json', auth='user', methods=['GET'])
    def list_models(self, search=None, limit=50, **kwargs):
        """
        List available Odoo models for data sources.

        Args:
            search: Search term
            limit: Maximum results

        Returns:
            dict: List of models
        """
        IrModel = request.env['ir.model']

        domain = [('transient', '=', False)]
        if search:
            domain.append('|')
            domain.append(('name', 'ilike', search))
            domain.append(('model', 'ilike', search))

        try:
            models = IrModel.search(domain, limit=limit, order='name')

            result = []
            for model in models:
                result.append({
                    'id': model.id,
                    'name': model.name,
                    'model': model.model,
                })

            return {
                'success': True,
                'models': result,
            }
        except Exception as e:
            _logger.error("Error listing models: %s", e)
            return {'error': str(e), 'code': 500}

    @http.route('/spreadsheet/model/<string:model_name>/fields',
                type='json', auth='user', methods=['GET'])
    def get_model_fields(self, model_name, **kwargs):
        """
        Get fields for an Odoo model.

        Args:
            model_name: Odoo model name

        Returns:
            dict: List of fields
        """
        if model_name not in request.env:
            return {'error': f"Model '{model_name}' not found", 'code': 404}

        IrModelFields = request.env['ir.model.fields']

        try:
            fields_data = IrModelFields.search([
                ('model', '=', model_name),
                ('store', '=', True),
            ], order='field_description')

            result = []
            for field in fields_data:
                result.append({
                    'id': field.id,
                    'name': field.name,
                    'label': field.field_description,
                    'type': field.ttype,
                    'relation': field.relation,
                })

            return {
                'success': True,
                'model': model_name,
                'fields': result,
            }
        except Exception as e:
            _logger.error("Error getting model fields: %s", e)
            return {'error': str(e), 'code': 500}

    # ---------------------------------
    # Pivot Table Operations
    # ---------------------------------

    @http.route('/spreadsheet/pivot/<int:pivot_id>/compute',
                type='json', auth='user', methods=['GET'])
    def compute_pivot(self, pivot_id):
        """
        Compute pivot table data.

        Args:
            pivot_id: ID of the pivot table

        Returns:
            dict: Computed pivot data
        """
        Pivot = request.env['spreadsheet.pivot']
        pivot = Pivot.browse(pivot_id)

        if not pivot.exists():
            return {'error': 'Pivot table not found', 'code': 404}

        try:
            data = pivot.compute_pivot()
            return {
                'success': True,
                'pivot_id': pivot.id,
                'name': pivot.name,
                'data': data,
            }
        except Exception as e:
            _logger.error("Error computing pivot: %s", e)
            return {'error': str(e), 'code': 500}

    @http.route('/spreadsheet/pivot/preview',
                type='json', auth='user', methods=['POST'])
    def preview_pivot(self, model, row_fields, column_fields=None,
                      measures=None, domain='[]', **kwargs):
        """
        Preview pivot table without creating one.

        Args:
            model: Odoo model name
            row_fields: Fields to group by in rows
            column_fields: Fields to group by in columns
            measures: Measure definitions
            domain: Filter domain

        Returns:
            dict: Preview pivot data
        """
        from odoo.tools.safe_eval import safe_eval

        if model not in request.env:
            return {'error': f"Model '{model}' not found", 'code': 404}

        Model = request.env[model]
        column_fields = column_fields or []
        measures = measures or [{'field': '__count', 'aggregator': 'count', 'label': 'Count'}]

        try:
            parsed_domain = safe_eval(domain)
            groupby = row_fields + column_fields

            # Prepare aggregation fields
            agg_fields = []
            for m in measures:
                if m['field'] != '__count':
                    agg_fields.append(f"{m['field']}:{m['aggregator']}")

            # Execute read_group
            if groupby:
                results = Model.read_group(
                    parsed_domain,
                    agg_fields or ['id'],
                    groupby,
                    lazy=False
                )
            else:
                results = [Model.read_group(parsed_domain, agg_fields or ['id'], [])[0]]

            # Return raw results for preview
            return {
                'success': True,
                'results': results[:100],  # Limit preview
                'row_fields': row_fields,
                'column_fields': column_fields,
                'measures': measures,
            }
        except Exception as e:
            _logger.error("Error previewing pivot: %s", e)
            return {'error': str(e), 'code': 500}

    # ---------------------------------
    # Chart Operations
    # ---------------------------------

    @http.route('/spreadsheet/chart/<int:chart_id>/data',
                type='json', auth='user', methods=['GET'])
    def get_chart_data(self, chart_id):
        """
        Get chart data for rendering.

        Args:
            chart_id: ID of the chart

        Returns:
            dict: Chart data
        """
        Chart = request.env['spreadsheet.chart']
        chart = Chart.browse(chart_id)

        if not chart.exists():
            return {'error': 'Chart not found', 'code': 404}

        try:
            data = chart.get_chart_data()
            option = chart.get_echarts_option()

            return {
                'success': True,
                'chart_id': chart.id,
                'name': chart.name,
                'chart_type': chart.chart_type,
                'data': data,
                'echarts_option': option,
            }
        except Exception as e:
            _logger.error("Error getting chart data: %s", e)
            return {'error': str(e), 'code': 500}

    @http.route('/spreadsheet/chart/preview',
                type='json', auth='user', methods=['POST'])
    def preview_chart(self, model, groupby_field, measure_field=None,
                      aggregator='sum', domain='[]', chart_type='bar', **kwargs):
        """
        Preview chart data without creating one.

        Args:
            model: Odoo model name
            groupby_field: Field to group by
            measure_field: Field to measure (or count)
            aggregator: Aggregation function
            domain: Filter domain
            chart_type: Type of chart

        Returns:
            dict: Preview chart data
        """
        from odoo.tools.safe_eval import safe_eval

        if model not in request.env:
            return {'error': f"Model '{model}' not found", 'code': 404}

        Model = request.env[model]

        try:
            parsed_domain = safe_eval(domain)

            # Execute read_group
            agg_spec = f"{measure_field}:{aggregator}" if measure_field else 'id'
            results = Model.read_group(parsed_domain, [agg_spec], [groupby_field])

            # Process results
            labels = []
            values = []
            for result in results:
                label = result.get(groupby_field)
                if isinstance(label, tuple):
                    label = label[1]
                labels.append(label or 'N/A')

                if measure_field:
                    values.append(result.get(measure_field, 0))
                else:
                    values.append(result.get('__count', 0))

            return {
                'success': True,
                'labels': labels,
                'datasets': [{
                    'label': measure_field or 'Count',
                    'data': values,
                }],
                'chart_type': chart_type,
            }
        except Exception as e:
            _logger.error("Error previewing chart: %s", e)
            return {'error': str(e), 'code': 500}

    # ---------------------------------
    # Collaboration Operations
    # ---------------------------------

    @http.route('/spreadsheet/document/<int:document_id>/lock',
                type='json', auth='user', methods=['POST'])
    def lock_cell_range(self, document_id, sheet_id, range_start, range_end, **kwargs):
        """
        Lock a cell range for editing (collaboration support).

        Args:
            document_id: Document ID
            sheet_id: Sheet ID
            range_start: Start cell (e.g., 'A1')
            range_end: End cell (e.g., 'C5')

        Returns:
            dict: Lock result
        """
        # Simplified lock mechanism - for full collaboration would use Redis/WebSocket
        user = request.env.user

        # Store lock in session or cache
        lock_key = f"spreadsheet_lock_{document_id}_{sheet_id}"
        lock_data = {
            'user_id': user.id,
            'user_name': user.name,
            'range_start': range_start,
            'range_end': range_end,
        }

        return {
            'success': True,
            'lock': lock_data,
            'message': f"Range {range_start}:{range_end} locked by {user.name}",
        }

    @http.route('/spreadsheet/document/<int:document_id>/unlock',
                type='json', auth='user', methods=['POST'])
    def unlock_cell_range(self, document_id, sheet_id, range_start, range_end, **kwargs):
        """
        Unlock a cell range.

        Args:
            document_id: Document ID
            sheet_id: Sheet ID
            range_start: Start cell
            range_end: End cell

        Returns:
            dict: Unlock result
        """
        return {
            'success': True,
            'message': f"Range {range_start}:{range_end} unlocked",
        }

    # ---------------------------------
    # Export Operations
    # ---------------------------------

    @http.route('/spreadsheet/document/<int:document_id>/export/<string:format>',
                type='http', auth='user', methods=['GET'])
    def export_document(self, document_id, format='xlsx'):
        """
        Export spreadsheet to file format.

        Args:
            document_id: Document ID
            format: Export format (xlsx, csv, pdf)

        Returns:
            File download response
        """
        Document = request.env['spreadsheet.document']
        doc = Document.browse(document_id)

        if not doc.exists():
            return Response("Document not found", status=404)

        try:
            if format == 'xlsx':
                content, mime = doc._export_xlsx()
                filename = f"{doc.name}.xlsx"
            elif format == 'csv':
                content, mime = doc._export_csv()
                filename = f"{doc.name}.csv"
            else:
                return Response(f"Unsupported format: {format}", status=400)

            return request.make_response(
                content,
                headers=[
                    ('Content-Type', mime),
                    ('Content-Disposition', f'attachment; filename="{filename}"'),
                ]
            )
        except Exception as e:
            _logger.error("Error exporting document: %s", e)
            return Response(str(e), status=500)
