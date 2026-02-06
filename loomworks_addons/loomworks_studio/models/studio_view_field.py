# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Studio View Field Model - Field configuration within a view customization.

This model stores per-field settings like visibility, widget, labels,
and positioning within a Studio-customized view.
"""

from loomworks import api, models, fields


class StudioViewField(models.Model):
    """
    Field configuration within a Studio view customization.

    Stores how a specific field should appear in a view, including
    widget, visibility rules, label overrides, and positioning.
    """
    _name = 'studio.view.field'
    _description = 'Studio View Field Configuration'
    _order = 'sequence, id'

    # Parent customization
    customization_id = fields.Many2one(
        'studio.view.customization',
        string='View Customization',
        required=True,
        ondelete='cascade'
    )

    # Field reference
    field_id = fields.Many2one(
        'ir.model.fields',
        string='Field',
        required=True,
        ondelete='cascade'
    )
    field_name = fields.Char(
        related='field_id.name',
        string='Field Name',
        store=True
    )
    field_type = fields.Selection(
        related='field_id.ttype',
        string='Field Type',
        store=True
    )

    # Display settings
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Order of the field in the view"
    )
    visible = fields.Boolean(
        string='Visible',
        default=True,
        help="Whether the field is shown in the view"
    )
    custom_label = fields.Char(
        string='Custom Label',
        help="Override the default field label"
    )

    # Widget and formatting
    widget = fields.Char(
        string='Widget',
        help="Widget to use (e.g., selection, handle, many2many_tags)"
    )
    placeholder = fields.Char(
        string='Placeholder',
        help="Placeholder text for input fields"
    )

    # Behavior
    readonly = fields.Boolean(
        string='Readonly',
        default=False,
        help="Make field readonly in this view"
    )
    required = fields.Boolean(
        string='Required',
        default=False,
        help="Make field required in this view"
    )
    invisible_domain = fields.Char(
        string='Invisible Condition',
        help="Domain expression for when field should be hidden"
    )
    readonly_domain = fields.Char(
        string='Readonly Condition',
        help="Domain expression for when field should be readonly"
    )

    # Form view specific
    group_name = fields.Char(
        string='Group',
        help="Group name for form view organization"
    )
    colspan = fields.Integer(
        string='Column Span',
        default=1,
        help="Number of columns to span in form view"
    )

    # List view specific
    column_width = fields.Char(
        string='Column Width',
        help="Width for list view column (e.g., '100px', '10%')"
    )
    sortable = fields.Boolean(
        string='Sortable',
        default=True,
        help="Allow sorting by this column"
    )
    sum_enabled = fields.Boolean(
        string='Show Sum',
        default=False,
        help="Show sum total for numeric columns"
    )
    avg_enabled = fields.Boolean(
        string='Show Average',
        default=False,
        help="Show average for numeric columns"
    )

    # Styling
    css_class = fields.Char(
        string='CSS Class',
        help="Additional CSS class for styling"
    )
    decoration = fields.Char(
        string='Decoration',
        help="Conditional decoration (e.g., decoration-danger)"
    )
    decoration_domain = fields.Char(
        string='Decoration Domain',
        help="Domain for when to apply decoration"
    )

    # Extra options stored as JSON
    options = fields.Text(
        string='Widget Options',
        help="JSON-encoded widget options"
    )

    @api.onchange('field_id')
    def _onchange_field_id(self):
        """Set default widget based on field type."""
        if self.field_id:
            # Set default widgets for common field types
            type_widgets = {
                'boolean': '',
                'selection': '',
                'many2one': '',
                'many2many': 'many2many_tags',
                'one2many': '',
                'html': 'html',
                'text': '',
                'date': '',
                'datetime': '',
                'binary': 'image',
            }
            default_widget = type_widgets.get(self.field_id.ttype, '')
            if default_widget and not self.widget:
                self.widget = default_widget

    def get_field_attributes(self):
        """
        Get dictionary of XML attributes for this field.

        Returns:
            dict: Attributes to set on the field element
        """
        self.ensure_one()

        attrs = {
            'name': self.field_id.name,
        }

        if self.widget:
            attrs['widget'] = self.widget
        if self.custom_label:
            attrs['string'] = self.custom_label
        if self.placeholder:
            attrs['placeholder'] = self.placeholder
        if self.readonly:
            attrs['readonly'] = '1'
        if self.required:
            attrs['required'] = '1'
        if self.invisible_domain:
            attrs['invisible'] = self.invisible_domain
        if self.css_class:
            attrs['class'] = self.css_class
        if self.column_width:
            attrs['width'] = self.column_width
        if self.colspan and self.colspan > 1:
            attrs['colspan'] = str(self.colspan)

        # Handle options
        if self.options:
            attrs['options'] = self.options

        # Handle sum/avg for list views
        if self.sum_enabled:
            attrs['sum'] = self.custom_label or self.field_id.field_description
        if self.avg_enabled:
            attrs['avg'] = self.custom_label or self.field_id.field_description

        # Handle decoration
        if self.decoration and self.decoration_domain:
            attrs[f'decoration-{self.decoration}'] = self.decoration_domain

        return attrs
