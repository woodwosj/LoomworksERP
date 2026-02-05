# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

import json
from odoo import api, fields, models


class PlmBomRevision(models.Model):
    """BOM Revision History

    Stores snapshots of BOM configurations at specific revisions.
    Enables comparison between versions and potential rollback.
    """
    _name = 'plm.bom.revision'
    _description = 'BOM Revision History'
    _order = 'revision_date desc'

    bom_id = fields.Many2one(
        'mrp.bom',
        string='BOM',
        required=True,
        ondelete='cascade',
        index=True
    )
    revision_code = fields.Char(
        string='Revision Code',
        required=True,
        help='e.g., A, B, C or 1.0, 1.1, 2.0'
    )
    revision_date = fields.Datetime(
        string='Revision Date',
        default=fields.Datetime.now,
        required=True
    )

    # Change Reference
    eco_id = fields.Many2one(
        'plm.eco',
        string='Source ECO',
        help='ECO that triggered this revision'
    )

    # Snapshot of BOM at this revision
    snapshot_data = fields.Text(
        string='BOM Snapshot (JSON)',
        help='Serialized BOM structure at this revision'
    )

    # Metadata
    created_by_id = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user
    )
    notes = fields.Text(
        string='Revision Notes',
        help='Description of changes in this revision'
    )

    # Status
    is_active = fields.Boolean(
        string='Active Revision',
        default=True,
        help='Indicates if this revision snapshot is still valid'
    )
    is_released = fields.Boolean(
        string='Released',
        help='Revision has been released to production'
    )

    # Related fields
    product_tmpl_id = fields.Many2one(
        'product.template',
        related='bom_id.product_tmpl_id',
        store=True,
        string='Product'
    )

    # Computed fields for display
    line_count = fields.Integer(
        compute='_compute_snapshot_info',
        string='Component Count'
    )
    snapshot_summary = fields.Text(
        compute='_compute_snapshot_info',
        string='Snapshot Summary'
    )

    @api.depends('snapshot_data')
    def _compute_snapshot_info(self):
        """Parse snapshot data for display."""
        for rev in self:
            if rev.snapshot_data:
                try:
                    data = json.loads(rev.snapshot_data)
                    lines = data.get('lines', [])
                    rev.line_count = len(lines)
                    # Build summary
                    summary_lines = []
                    for line in lines[:5]:
                        summary_lines.append(f"- {line.get('product_name', 'Unknown')}: {line.get('product_qty', 0)}")
                    if len(lines) > 5:
                        summary_lines.append(f"... and {len(lines) - 5} more components")
                    rev.snapshot_summary = '\n'.join(summary_lines)
                except (json.JSONDecodeError, TypeError):
                    rev.line_count = 0
                    rev.snapshot_summary = 'Invalid snapshot data'
            else:
                rev.line_count = 0
                rev.snapshot_summary = 'No snapshot data'

    def action_view_snapshot(self):
        """Open wizard to view detailed snapshot."""
        self.ensure_one()
        return {
            'name': f'BOM Snapshot - Rev {self.revision_code}',
            'type': 'ir.actions.act_window',
            'res_model': 'plm.bom.snapshot.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_revision_id': self.id},
        }

    def action_compare_with_current(self):
        """Compare this revision with current BOM."""
        self.ensure_one()
        return {
            'name': 'BOM Comparison',
            'type': 'ir.actions.act_window',
            'res_model': 'plm.bom.compare.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_bom_id': self.bom_id.id,
                'default_revision_id': self.id,
            },
        }

    def get_snapshot_lines(self):
        """Parse and return snapshot lines as list of dicts."""
        self.ensure_one()
        if not self.snapshot_data:
            return []
        try:
            data = json.loads(self.snapshot_data)
            return data.get('lines', [])
        except (json.JSONDecodeError, TypeError):
            return []

    def name_get(self):
        """Display name including product and revision."""
        result = []
        for rev in self:
            name = f"{rev.bom_id.product_tmpl_id.name or 'BOM'} - Rev {rev.revision_code}"
            result.append((rev.id, name))
        return result
