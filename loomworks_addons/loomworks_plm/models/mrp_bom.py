# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MrpBom(models.Model):
    """Extension of MRP BOM for PLM versioning support.

    Adds revision tracking, lifecycle management, and ECO integration
    to the standard Bill of Materials model.
    """
    _inherit = 'mrp.bom'

    # ==================== Revision Tracking ====================

    revision_code = fields.Char(
        string='Revision',
        default='A',
        tracking=True,
        index=True,
        help='BOM revision identifier (e.g., A, B, C or 1.0, 2.0)'
    )

    revision_ids = fields.One2many(
        'plm.bom.revision',
        'bom_id',
        string='Revision History'
    )
    revision_count = fields.Integer(
        compute='_compute_revision_count',
        string='Revision Count'
    )

    # ==================== ECO References ====================

    eco_ids = fields.One2many(
        'plm.eco',
        'bom_id',
        string='Engineering Change Orders'
    )
    pending_eco_count = fields.Integer(
        compute='_compute_pending_eco_count',
        string='Pending ECOs'
    )

    # ==================== Lifecycle Status ====================

    lifecycle_state = fields.Selection([
        ('draft', 'Draft'),
        ('review', 'Under Review'),
        ('released', 'Released'),
        ('obsolete', 'Obsolete')
    ], default='draft', string='Lifecycle State', tracking=True, index=True,
        help='Current lifecycle state of this BOM revision')

    # ==================== Version Chain ====================

    previous_bom_id = fields.Many2one(
        'mrp.bom',
        string='Previous Version',
        ondelete='set null',
        help='Link to the previous revision of this BOM'
    )
    is_current_revision = fields.Boolean(
        string='Current Revision',
        default=True,
        index=True,
        help='Indicates if this is the active revision for production'
    )
    next_bom_ids = fields.One2many(
        'mrp.bom',
        'previous_bom_id',
        string='Next Versions'
    )

    # ==================== Computed Fields ====================

    @api.depends('revision_ids')
    def _compute_revision_count(self):
        for bom in self:
            bom.revision_count = len(bom.revision_ids)

    @api.depends('eco_ids', 'eco_ids.state')
    def _compute_pending_eco_count(self):
        for bom in self:
            bom.pending_eco_count = len(bom.eco_ids.filtered(
                lambda e: e.state not in ('done', 'cancelled')
            ))

    # ==================== Revision Management ====================

    def action_create_revision(self):
        """Create a new revision of this BOM via ECO."""
        self.ensure_one()
        return {
            'name': _('Create ECO for New Revision'),
            'type': 'ir.actions.act_window',
            'res_model': 'plm.eco',
            'view_mode': 'form',
            'context': {
                'default_bom_id': self.id,
                'default_title': _('New revision for %s') % self.product_tmpl_id.name,
            },
        }

    def action_view_revisions(self):
        """View revision history."""
        self.ensure_one()
        return {
            'name': _('Revision History'),
            'type': 'ir.actions.act_window',
            'res_model': 'plm.bom.revision',
            'view_mode': 'tree,form',
            'domain': [('bom_id', '=', self.id)],
            'context': {'default_bom_id': self.id},
        }

    def action_view_ecos(self):
        """View related ECOs."""
        self.ensure_one()
        return {
            'name': _('Engineering Change Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'plm.eco',
            'view_mode': 'tree,kanban,form',
            'domain': [('bom_id', '=', self.id)],
            'context': {'default_bom_id': self.id},
        }

    def action_compare_revisions(self):
        """Open wizard to compare BOM versions."""
        self.ensure_one()

        # Find other versions to compare
        all_versions = self.search([
            ('product_tmpl_id', '=', self.product_tmpl_id.id)
        ])

        return {
            'name': _('Compare BOM Revisions'),
            'type': 'ir.actions.act_window',
            'res_model': 'plm.bom.compare.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_bom_id': self.id,
                'available_bom_ids': all_versions.ids,
            },
        }

    def action_set_released(self):
        """Mark BOM as released for production."""
        self.ensure_one()
        if self.lifecycle_state == 'obsolete':
            raise UserError(_('Cannot release an obsolete BOM. Create a new revision instead.'))

        # Mark other versions as not current
        sibling_boms = self.search([
            ('product_tmpl_id', '=', self.product_tmpl_id.id),
            ('id', '!=', self.id),
        ])
        sibling_boms.write({'is_current_revision': False})

        self.write({
            'lifecycle_state': 'released',
            'is_current_revision': True,
        })
        return True

    def action_set_obsolete(self):
        """Mark BOM as obsolete."""
        self.ensure_one()
        if self.pending_eco_count:
            raise UserError(_('Cannot obsolete a BOM with pending ECOs. Complete or cancel them first.'))

        self.write({
            'lifecycle_state': 'obsolete',
            'is_current_revision': False,
        })
        return True

    # ==================== Override Name Display ====================

    def name_get(self):
        """Include revision code in display name."""
        result = []
        for bom in self:
            name = bom.product_tmpl_id.name or 'BOM'
            if bom.code:
                name = f'[{bom.code}] {name}'
            if bom.revision_code:
                name = f'{name} (Rev {bom.revision_code})'
            if not bom.is_current_revision and bom.lifecycle_state != 'draft':
                name = f'{name} [OLD]'
            result.append((bom.id, name))
        return result

    # ==================== BOM Comparison Utilities ====================

    def get_bom_diff(self, other_bom):
        """Compare this BOM with another and return differences.

        Returns a dict with added, removed, and modified lines.
        """
        self.ensure_one()
        if not other_bom:
            return {'added': [], 'removed': [], 'modified': []}

        # Build component maps
        self_components = {
            line.product_id.id: {
                'line': line,
                'qty': line.product_qty,
                'name': line.product_id.name,
            }
            for line in self.bom_line_ids
        }
        other_components = {
            line.product_id.id: {
                'line': line,
                'qty': line.product_qty,
                'name': line.product_id.name,
            }
            for line in other_bom.bom_line_ids
        }

        diff = {
            'added': [],
            'removed': [],
            'modified': [],
        }

        # Find added and modified
        for product_id, data in self_components.items():
            if product_id not in other_components:
                diff['added'].append({
                    'product_id': product_id,
                    'product_name': data['name'],
                    'new_qty': data['qty'],
                })
            elif data['qty'] != other_components[product_id]['qty']:
                diff['modified'].append({
                    'product_id': product_id,
                    'product_name': data['name'],
                    'old_qty': other_components[product_id]['qty'],
                    'new_qty': data['qty'],
                })

        # Find removed
        for product_id, data in other_components.items():
            if product_id not in self_components:
                diff['removed'].append({
                    'product_id': product_id,
                    'product_name': data['name'],
                    'old_qty': data['qty'],
                })

        return diff
