# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SignTemplateItem(models.Model):
    """Signature Template Field

    Defines a field (signature, text, date, etc.) to be placed on a template
    at a specific position. Position is stored as percentages for responsive
    placement across different display sizes.
    """
    _name = 'sign.template.item'
    _description = 'Template Signature Field'
    _order = 'page, sequence'

    template_id = fields.Many2one(
        'sign.template',
        string='Template',
        required=True,
        ondelete='cascade',
        index=True
    )

    # Field Type
    type_id = fields.Many2one(
        'sign.item.type',
        string='Field Type',
        required=True,
        ondelete='restrict'
    )
    item_type = fields.Selection(
        related='type_id.item_type',
        store=True
    )

    # Position (percentage-based for responsiveness)
    page = fields.Integer(
        string='Page Number',
        default=1,
        required=True,
        help='Page where this field appears (1-indexed)'
    )
    pos_x = fields.Float(
        string='X Position (%)',
        required=True,
        default=10.0,
        help='Horizontal position as percentage of page width (0-100)'
    )
    pos_y = fields.Float(
        string='Y Position (%)',
        required=True,
        default=10.0,
        help='Vertical position as percentage of page height (0-100)'
    )
    width = fields.Float(
        string='Width (%)',
        default=20.0,
        help='Width as percentage of page width'
    )
    height = fields.Float(
        string='Height (%)',
        default=5.0,
        help='Height as percentage of page height'
    )

    # Assignment
    role_id = fields.Many2one(
        'sign.role',
        string='Assigned Role',
        required=True,
        help='Role of the signer who must complete this field'
    )

    # Configuration
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    required = fields.Boolean(
        string='Required',
        default=True,
        help='Signer must complete this field to sign'
    )
    placeholder = fields.Char(
        string='Placeholder Text',
        help='Hint text shown before field is filled'
    )
    name = fields.Char(
        string='Field Name',
        help='Internal name for this field'
    )

    # For selection/radio/checkbox fields
    option_ids = fields.One2many(
        'sign.template.item.option',
        'item_id',
        string='Options',
        help='Available options for selection/radio fields'
    )

    # Validation
    validation_pattern = fields.Char(
        string='Validation Pattern',
        help='Regex pattern for text field validation'
    )
    min_length = fields.Integer(
        string='Minimum Length'
    )
    max_length = fields.Integer(
        string='Maximum Length'
    )

    @api.onchange('type_id')
    def _onchange_type_id(self):
        """Set default dimensions from type."""
        if self.type_id:
            self.width = self.type_id.default_width
            self.height = self.type_id.default_height

    def name_get(self):
        result = []
        for item in self:
            name = f"Page {item.page}: {item.type_id.name or 'Field'}"
            if item.name:
                name = f"{name} ({item.name})"
            result.append((item.id, name))
        return result


class SignTemplateItemOption(models.Model):
    """Options for selection/radio/checkbox template fields."""
    _name = 'sign.template.item.option'
    _description = 'Template Field Option'
    _order = 'sequence'

    item_id = fields.Many2one(
        'sign.template.item',
        string='Template Field',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    value = fields.Char(
        string='Value',
        required=True
    )
    label = fields.Char(
        string='Display Label',
        help='Label shown to signer (defaults to value)'
    )

    def name_get(self):
        result = []
        for option in self:
            name = option.label or option.value
            result.append((option.id, name))
        return result
