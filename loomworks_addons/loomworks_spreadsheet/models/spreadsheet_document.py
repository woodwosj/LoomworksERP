# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Spreadsheet Document Model - Main spreadsheet storage.

Each document stores the complete spreadsheet data as JSON,
including cells, formulas, formatting, and metadata.
"""

import json
import logging
from datetime import datetime

from loomworks import api, models, fields, _
from loomworks.exceptions import UserError

_logger = logging.getLogger(__name__)


class SpreadsheetDocument(models.Model):
    """
    Spreadsheet document storage.

    Stores the complete spreadsheet as JSON data compatible with
    the Univer library format.
    """
    _name = 'spreadsheet.document'
    _description = 'Spreadsheet Document'
    _order = 'write_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Name',
        required=True,
        tracking=True,
        default=lambda self: _('New Spreadsheet')
    )
    description = fields.Text(
        string='Description',
        help="Brief description of the spreadsheet contents"
    )
    active = fields.Boolean(
        default=True
    )

    # Spreadsheet Data (Univer JSON format)
    raw_data = fields.Text(
        string='Spreadsheet Data',
        help="JSON data in Univer format"
    )
    # Alias for compatibility
    data = fields.Text(
        string='Data',
        compute='_compute_data',
        inverse='_inverse_data',
        store=False,
    )
    thumbnail = fields.Binary(
        string='Thumbnail',
        help="Preview image of the spreadsheet"
    )

    # Template and Publishing
    is_template = fields.Boolean(
        string='Is Template',
        default=False,
        help="Mark this document as a template"
    )
    is_published = fields.Boolean(
        string='Published',
        default=False,
        help="Make this document accessible to others"
    )

    # Related Components
    data_source_ids = fields.One2many(
        'spreadsheet.data.source',
        'document_id',
        string='Data Sources'
    )
    pivot_ids = fields.One2many(
        'spreadsheet.pivot',
        'document_id',
        string='Pivot Tables'
    )
    chart_ids = fields.One2many(
        'spreadsheet.chart',
        'document_id',
        string='Charts'
    )

    # Sharing and Collaboration
    shared = fields.Boolean(
        string='Shared',
        default=False,
        help="Allow other users to access this spreadsheet"
    )
    share_link = fields.Char(
        string='Share Link',
        compute='_compute_share_link'
    )
    collaborator_ids = fields.Many2many(
        'res.users',
        'spreadsheet_document_collaborator_rel',
        'document_id',
        'user_id',
        string='Collaborators'
    )
    permission = fields.Selection([
        ('view', 'View Only'),
        ('edit', 'Can Edit'),
    ], string='Default Permission', default='view')

    # Audit and Versioning
    version = fields.Integer(
        string='Version',
        default=1,
        readonly=True
    )
    last_modified = fields.Datetime(
        string='Last Modified',
        default=fields.Datetime.now
    )
    last_modified_by_id = fields.Many2one(
        'res.users',
        string='Last Modified By',
        default=lambda self: self.env.user
    )

    # Statistics
    cell_count = fields.Integer(
        string='Cell Count',
        compute='_compute_statistics'
    )
    sheet_count = fields.Integer(
        string='Sheet Count',
        compute='_compute_statistics'
    )
    data_source_count = fields.Integer(
        string='Data Source Count',
        compute='_compute_data_source_count',
        store=True
    )
    pivot_count = fields.Integer(
        string='Pivot Count',
        compute='_compute_pivot_count'
    )
    chart_count = fields.Integer(
        string='Chart Count',
        compute='_compute_chart_count'
    )

    # Tags
    tag_ids = fields.Many2many(
        'spreadsheet.document.tag',
        string='Tags'
    )

    # Folder organization (optional)
    folder_id = fields.Many2one(
        'spreadsheet.folder',
        string='Folder'
    )

    def _compute_data(self):
        """Compute alias for raw_data."""
        for doc in self:
            doc.data = doc.raw_data

    def _inverse_data(self):
        """Set raw_data from data."""
        for doc in self:
            doc.raw_data = doc.data

    @api.depends('data_source_ids')
    def _compute_data_source_count(self):
        for doc in self:
            doc.data_source_count = len(doc.data_source_ids)

    def _compute_pivot_count(self):
        for doc in self:
            doc.pivot_count = len(doc.pivot_ids)

    def _compute_chart_count(self):
        for doc in self:
            doc.chart_count = len(doc.chart_ids)

    def _compute_share_link(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for doc in self:
            if doc.shared:
                doc.share_link = f"{base_url}/spreadsheet/view/{doc.id}"
            else:
                doc.share_link = False

    def _compute_statistics(self):
        for doc in self:
            cell_count = 0
            sheet_count = 0

            if doc.raw_data:
                try:
                    data = json.loads(doc.raw_data)
                    sheets = data.get('sheets', [])
                    sheet_count = len(sheets)
                    for sheet in sheets:
                        cell_data = sheet.get('cellData', {})
                        cell_count += len(cell_data)
                except json.JSONDecodeError:
                    pass

            doc.cell_count = cell_count
            doc.sheet_count = sheet_count or 1  # At least 1 sheet

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('raw_data') and not vals.get('data'):
                vals['raw_data'] = self._get_empty_spreadsheet()
            elif vals.get('data') and not vals.get('raw_data'):
                vals['raw_data'] = vals.pop('data')
        return super().create(vals_list)

    def write(self, vals):
        # Handle data/raw_data aliasing
        if 'data' in vals and 'raw_data' not in vals:
            vals['raw_data'] = vals.pop('data')

        if 'raw_data' in vals:
            vals['version'] = (self.version or 0) + 1
            vals['last_modified'] = fields.Datetime.now()
            vals['last_modified_by_id'] = self.env.user.id
        return super().write(vals)

    def _get_empty_spreadsheet(self):
        """Return default empty spreadsheet data."""
        return json.dumps({
            'id': f'spreadsheet_{self.id or "new"}',
            'name': self.name or 'New Spreadsheet',
            'sheets': [{
                'id': 'sheet1',
                'name': 'Sheet 1',
                'rowCount': 100,
                'columnCount': 26,
                'cellData': {},
            }],
            'namedRanges': [],
            'styles': {},
        })

    def action_open_spreadsheet(self):
        """Open the spreadsheet editor."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'loomworks_spreadsheet_editor',
            'params': {
                'document_id': self.id,
                'document_name': self.name,
            },
        }

    # Alias for compatibility
    action_open = action_open_spreadsheet

    def action_duplicate(self):
        """Create a copy of the spreadsheet."""
        self.ensure_one()
        new_doc = self.copy({
            'name': f"{self.name} (Copy)",
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'spreadsheet.document',
            'res_id': new_doc.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_share(self):
        """Toggle sharing and return share link."""
        self.ensure_one()
        self.shared = not self.shared
        if self.shared:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Spreadsheet Shared'),
                    'message': _('Share link: %s', self.share_link),
                    'type': 'success',
                    'sticky': True,
                }
            }

    def action_export_xlsx(self):
        """Export spreadsheet as Excel file."""
        self.ensure_one()
        # In a full implementation, this would use a library like openpyxl
        # to convert the JSON data to XLSX format
        raise UserError(_("Excel export will be implemented with openpyxl library."))

    def action_export_pdf(self):
        """Export spreadsheet as PDF."""
        self.ensure_one()
        raise UserError(_("PDF export will be implemented with wkhtmltopdf."))

    @api.model
    def action_import_xlsx(self):
        """Import spreadsheet from Excel file."""
        # Returns a wizard for file upload
        return {
            'type': 'ir.actions.act_window',
            'name': _('Import Excel'),
            'res_model': 'spreadsheet.import.wizard',
            'view_mode': 'form',
            'target': 'new',
        }

    def get_data_for_univer(self):
        """
        Get spreadsheet data formatted for Univer.

        Returns:
            dict: Univer-compatible data structure
        """
        self.ensure_one()

        if self.raw_data:
            try:
                return json.loads(self.raw_data)
            except json.JSONDecodeError:
                _logger.warning("Invalid JSON in spreadsheet %s", self.id)

        return json.loads(self._get_empty_spreadsheet())

    def save_from_univer(self, univer_data):
        """
        Save data from Univer back to the document.

        Args:
            univer_data: dict or JSON string from Univer
        """
        self.ensure_one()

        if isinstance(univer_data, str):
            # Validate JSON
            try:
                json.loads(univer_data)
                data = univer_data
            except json.JSONDecodeError as e:
                raise UserError(_("Invalid spreadsheet data: %s", str(e)))
        else:
            data = json.dumps(univer_data)

        self.write({'raw_data': data})

    def _export_xlsx(self):
        """
        Export spreadsheet as Excel file.

        Returns:
            tuple: (content_bytes, mime_type)
        """
        self.ensure_one()
        # Placeholder - would use openpyxl in production
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        data = self.get_data_for_univer()
        sheets = data.get('sheets', [])

        if sheets:
            sheet = sheets[0]
            cell_data = sheet.get('cellData', {})

            # Convert cell data to rows
            rows = {}
            for key, cell in cell_data.items():
                parts = key.split(':')
                if len(parts) == 2:
                    row, col = int(parts[0]), int(parts[1])
                    if row not in rows:
                        rows[row] = {}
                    rows[row][col] = cell.get('v', '')

            # Write rows
            for row_idx in sorted(rows.keys()):
                row_data = rows[row_idx]
                max_col = max(row_data.keys()) if row_data else 0
                row = [row_data.get(col, '') for col in range(max_col + 1)]
                writer.writerow(row)

        content = output.getvalue().encode('utf-8')
        return content, 'text/csv'

    def _export_csv(self):
        """
        Export spreadsheet as CSV file.

        Returns:
            tuple: (content_bytes, mime_type)
        """
        return self._export_xlsx()  # Same implementation for now


class SpreadsheetDocumentTag(models.Model):
    """Tags for organizing spreadsheets."""
    _name = 'spreadsheet.document.tag'
    _description = 'Spreadsheet Tag'

    name = fields.Char(required=True)
    color = fields.Integer(default=0)


class SpreadsheetFolder(models.Model):
    """Folder organization for spreadsheets."""
    _name = 'spreadsheet.folder'
    _description = 'Spreadsheet Folder'
    _parent_name = 'parent_id'
    _parent_store = True
    _order = 'name'

    name = fields.Char(required=True)
    parent_id = fields.Many2one('spreadsheet.folder', ondelete='cascade')
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many('spreadsheet.folder', 'parent_id')
    document_ids = fields.One2many('spreadsheet.document', 'folder_id')
    document_count = fields.Integer(compute='_compute_document_count')

    @api.depends('document_ids')
    def _compute_document_count(self):
        for folder in self:
            folder.document_count = len(folder.document_ids)
