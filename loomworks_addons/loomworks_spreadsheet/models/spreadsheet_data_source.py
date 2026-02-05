# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Spreadsheet Data Source Model - Odoo data connections.

Data sources define how to pull data from Odoo models into
spreadsheet cells, including field selection and filtering.
"""

import json
import logging

from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class SpreadsheetDataSource(models.Model):
    """
    Data source configuration for spreadsheets.

    Defines a connection to an Odoo model that populates
    spreadsheet cells with live data.
    """
    _name = 'spreadsheet.data.source'
    _description = 'Spreadsheet Data Source'
    _order = 'name'

    name = fields.Char(
        string='Name',
        required=True,
        help="Descriptive name for this data source"
    )
    document_id = fields.Many2one(
        'spreadsheet.document',
        string='Spreadsheet',
        required=True,
        ondelete='cascade'
    )
    active = fields.Boolean(default=True)

    # Data Source Configuration
    source_type = fields.Selection([
        ('model', 'Odoo Model'),
        ('sql', 'SQL Query'),
        ('external', 'External API'),
    ], string='Source Type', default='model', required=True)

    # Odoo Model Source
    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        help="Odoo model to fetch data from"
    )
    model_name = fields.Char(
        related='model_id.model',
        store=True
    )
    domain = fields.Char(
        string='Filter Domain',
        default='[]',
        help="Domain to filter records"
    )
    field_ids = fields.Many2many(
        'ir.model.fields',
        'spreadsheet_data_source_field_rel',
        'source_id',
        'field_id',
        string='Fields',
        help="Fields to include in the data source"
    )
    limit = fields.Integer(
        string='Record Limit',
        default=1000,
        help="Maximum number of records to fetch (0 = unlimited)"
    )
    order = fields.Char(
        string='Sort Order',
        help="Field to sort by (e.g., 'name desc')"
    )

    # Target Location
    target_sheet = fields.Char(
        string='Target Sheet',
        default='sheet1',
        help="Sheet ID where data will be inserted"
    )
    target_cell = fields.Char(
        string='Target Cell',
        default='A1',
        help="Starting cell for data insertion"
    )
    include_headers = fields.Boolean(
        string='Include Headers',
        default=True,
        help="Include column headers in first row"
    )

    # Refresh Settings
    auto_refresh = fields.Boolean(
        string='Auto Refresh',
        default=False
    )
    refresh_interval = fields.Integer(
        string='Refresh Interval (minutes)',
        default=60
    )
    last_refresh = fields.Datetime(
        string='Last Refresh',
        readonly=True
    )

    # Computed Data Preview
    preview_data = fields.Text(
        string='Data Preview',
        compute='_compute_preview_data'
    )
    record_count = fields.Integer(
        string='Record Count',
        compute='_compute_record_count'
    )

    @api.constrains('domain')
    def _check_domain(self):
        """Validate domain syntax."""
        for source in self:
            if source.domain:
                try:
                    domain = safe_eval(source.domain)
                    if not isinstance(domain, list):
                        raise UserError(_("Domain must be a list."))
                except Exception as e:
                    raise UserError(_("Invalid domain: %s", str(e)))

    def _compute_preview_data(self):
        """Generate a preview of the data source."""
        for source in self:
            if source.source_type == 'model' and source.model_name:
                try:
                    data = source.fetch_data(limit=5)
                    source.preview_data = json.dumps(data, indent=2, default=str)
                except Exception as e:
                    source.preview_data = f"Error: {e}"
            else:
                source.preview_data = "Configure model to see preview"

    def _compute_record_count(self):
        """Count total records matching the domain."""
        for source in self:
            if source.source_type == 'model' and source.model_name:
                try:
                    domain = safe_eval(source.domain or '[]')
                    source.record_count = self.env[source.model_name].search_count(domain)
                except Exception:
                    source.record_count = 0
            else:
                source.record_count = 0

    def fetch_data(self, limit=None):
        """
        Fetch data from the configured source.

        Args:
            limit: Override the configured limit

        Returns:
            dict: Data structure with headers and rows
        """
        self.ensure_one()

        if self.source_type != 'model':
            raise UserError(_("Only model sources are currently supported."))

        if not self.model_name:
            raise UserError(_("No model configured."))

        if self.model_name not in self.env:
            raise UserError(_("Model '%s' not found.", self.model_name))

        Model = self.env[self.model_name]

        # Parse domain
        domain = safe_eval(self.domain or '[]')

        # Get field names
        field_names = self.field_ids.mapped('name')
        if not field_names:
            # Default to name and id
            field_names = ['id', 'display_name']

        # Search records
        search_limit = limit or self.limit or None
        order = self.order or None

        records = Model.search_read(
            domain,
            field_names,
            limit=search_limit,
            order=order
        )

        # Build result
        headers = []
        for field_name in field_names:
            field = self.field_ids.filtered(lambda f: f.name == field_name)
            if field:
                headers.append(field.field_description)
            else:
                headers.append(field_name)

        rows = []
        for record in records:
            row = []
            for field_name in field_names:
                value = record.get(field_name)
                # Handle relational fields
                if isinstance(value, tuple) and len(value) == 2:
                    value = value[1]  # Use display name
                elif isinstance(value, list):
                    value = ', '.join(str(v[1]) if isinstance(v, tuple) else str(v) for v in value)
                row.append(value)
            rows.append(row)

        # Update last refresh
        self.write({'last_refresh': fields.Datetime.now()})

        return {
            'headers': headers,
            'rows': rows,
            'field_names': field_names,
            'record_count': len(rows),
        }

    def action_refresh(self):
        """Manually refresh the data source."""
        self.ensure_one()
        data = self.fetch_data()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Data Refreshed'),
                'message': _('%d records loaded', data['record_count']),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_configure_fields(self):
        """Open field selection wizard."""
        self.ensure_one()
        if not self.model_id:
            raise UserError(_("Please select a model first."))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Select Fields'),
            'res_model': 'ir.model.fields',
            'view_mode': 'list',
            'domain': [('model_id', '=', self.model_id.id)],
            'context': {
                'default_model_id': self.model_id.id,
            },
            'target': 'new',
        }

    def insert_into_spreadsheet(self):
        """
        Insert the data source data into the spreadsheet.

        Updates the spreadsheet document with data at the configured location.
        """
        self.ensure_one()

        data = self.fetch_data()

        # Get current spreadsheet data
        spreadsheet_data = self.document_id.get_data_for_univer()

        # Find or create target sheet
        target_sheet = None
        for sheet in spreadsheet_data.get('sheets', []):
            if sheet.get('id') == self.target_sheet:
                target_sheet = sheet
                break

        if not target_sheet:
            _logger.warning(
                "Target sheet %s not found in spreadsheet %s",
                self.target_sheet, self.document_id.id
            )
            return

        # Parse target cell
        col, row = self._parse_cell_ref(self.target_cell)

        # Get or create cellData
        cell_data = target_sheet.setdefault('cellData', {})

        # Insert headers
        current_row = row
        if self.include_headers:
            for col_idx, header in enumerate(data['headers']):
                cell_key = f"{current_row}:{col + col_idx}"
                cell_data[cell_key] = {
                    'v': header,
                    's': {'b': 1, 'bg': '#f0f0f0'},  # Bold, gray background
                }
            current_row += 1

        # Insert data rows
        for row_data in data['rows']:
            for col_idx, value in enumerate(row_data):
                cell_key = f"{current_row}:{col + col_idx}"
                cell_data[cell_key] = {'v': value if value is not None else ''}
            current_row += 1

        # Save updated spreadsheet
        self.document_id.save_from_univer(spreadsheet_data)

        _logger.info(
            "Inserted %d records into spreadsheet %s at %s",
            len(data['rows']), self.document_id.id, self.target_cell
        )

    def _parse_cell_ref(self, ref):
        """
        Parse a cell reference like 'A1' into (column, row) indices.

        Args:
            ref: Cell reference string (e.g., 'A1', 'B2', 'AA10')

        Returns:
            tuple: (column_index, row_index) both 0-based
        """
        import re
        match = re.match(r'^([A-Z]+)(\d+)$', ref.upper())
        if not match:
            return (0, 0)

        col_str = match.group(1)
        row_str = match.group(2)

        # Convert column letters to index
        col = 0
        for char in col_str:
            col = col * 26 + (ord(char) - ord('A') + 1)
        col -= 1  # 0-based

        row = int(row_str) - 1  # 0-based

        return (col, row)
