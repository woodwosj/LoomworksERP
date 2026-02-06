# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from loomworks import api, fields, models


class PlmEcoChangeLine(models.Model):
    """ECO Change Line

    Detailed specification of individual changes within an ECO.
    Each line represents one change action (add, remove, replace, modify).
    """
    _name = 'plm.eco.change.line'
    _description = 'ECO Change Line'
    _order = 'sequence, id'

    eco_id = fields.Many2one(
        'plm.eco',
        string='ECO',
        required=True,
        ondelete='cascade',
        index=True
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )

    change_type = fields.Selection([
        ('add', 'Add Component'),
        ('remove', 'Remove Component'),
        ('replace', 'Replace Component'),
        ('modify_qty', 'Modify Quantity'),
        ('modify_operation', 'Modify Operation'),
        ('other', 'Other Change')
    ], string='Change Type', required=True,
        help='Type of change to be made')

    # Component References
    old_component_id = fields.Many2one(
        'product.product',
        string='Current Component',
        help='Existing component being changed (for replace/remove/modify)'
    )
    new_component_id = fields.Many2one(
        'product.product',
        string='New Component',
        help='New component to add or replacement component'
    )

    # Quantity Changes
    old_quantity = fields.Float(
        string='Current Quantity',
        digits='Product Unit of Measure',
        help='Current quantity in BOM'
    )
    new_quantity = fields.Float(
        string='New Quantity',
        digits='Product Unit of Measure',
        help='New quantity after change'
    )
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        compute='_compute_uom',
        store=True
    )

    # Operation Changes (if applicable)
    old_operation_id = fields.Many2one(
        'mrp.routing.workcenter',
        string='Current Operation',
        help='Current manufacturing operation'
    )
    new_operation_id = fields.Many2one(
        'mrp.routing.workcenter',
        string='New Operation',
        help='New or modified operation'
    )

    notes = fields.Text(
        string='Notes',
        help='Additional details about this change'
    )

    # Impact calculation
    cost_impact = fields.Float(
        string='Cost Impact',
        compute='_compute_cost_impact',
        store=True,
        help='Estimated impact on unit cost (positive = increase)'
    )

    # Related BOM line (for tracking)
    bom_line_id = fields.Many2one(
        'mrp.bom.line',
        string='BOM Line',
        help='Related BOM line if modifying existing'
    )

    @api.depends('old_component_id', 'new_component_id')
    def _compute_uom(self):
        """Get UoM from component."""
        for line in self:
            component = line.new_component_id or line.old_component_id
            line.product_uom_id = component.uom_id if component else False

    @api.depends('change_type', 'old_component_id', 'new_component_id',
                 'old_quantity', 'new_quantity')
    def _compute_cost_impact(self):
        """Calculate estimated cost impact of change."""
        for line in self:
            impact = 0.0
            if line.change_type == 'add' and line.new_component_id:
                impact = (line.new_component_id.standard_price or 0) * (line.new_quantity or 1)
            elif line.change_type == 'remove' and line.old_component_id:
                impact = -(line.old_component_id.standard_price or 0) * (line.old_quantity or 1)
            elif line.change_type == 'replace':
                old_cost = (line.old_component_id.standard_price or 0) * (line.old_quantity or 1)
                new_cost = (line.new_component_id.standard_price or 0) * (line.new_quantity or line.old_quantity or 1)
                impact = new_cost - old_cost
            elif line.change_type == 'modify_qty' and line.old_component_id:
                unit_cost = line.old_component_id.standard_price or 0
                qty_diff = (line.new_quantity or 0) - (line.old_quantity or 0)
                impact = unit_cost * qty_diff
            line.cost_impact = impact

    @api.onchange('old_component_id')
    def _onchange_old_component(self):
        """Auto-fill current quantity from BOM."""
        if self.old_component_id and self.eco_id.bom_id:
            bom_line = self.eco_id.bom_id.bom_line_ids.filtered(
                lambda l: l.product_id == self.old_component_id
            )[:1]
            if bom_line:
                self.old_quantity = bom_line.product_qty
                self.bom_line_id = bom_line.id

    @api.onchange('change_type')
    def _onchange_change_type(self):
        """Clear fields based on change type."""
        if self.change_type == 'add':
            self.old_component_id = False
            self.old_quantity = 0
        elif self.change_type == 'remove':
            self.new_component_id = False
            self.new_quantity = 0

    def name_get(self):
        """Display name for change line."""
        result = []
        for line in self:
            if line.change_type == 'add':
                name = f"Add: {line.new_component_id.name or 'Component'}"
            elif line.change_type == 'remove':
                name = f"Remove: {line.old_component_id.name or 'Component'}"
            elif line.change_type == 'replace':
                old_name = line.old_component_id.name or '?'
                new_name = line.new_component_id.name or '?'
                name = f"Replace: {old_name} -> {new_name}"
            elif line.change_type == 'modify_qty':
                name = f"Qty Change: {line.old_component_id.name or 'Component'}"
            else:
                name = f"Change: {line.notes or line.change_type}"
            result.append((line.id, name))
        return result
