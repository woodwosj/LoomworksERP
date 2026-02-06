# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Studio View Customization Model - Stores view modifications made via Studio.

This model tracks changes to views (field additions, removals, reorderings)
and generates the appropriate ir.ui.view records.
"""

import json
import logging
from collections import defaultdict
from lxml import etree

from loomworks import api, models, fields, _
from loomworks.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class StudioViewCustomization(models.Model):
    """
    Stores Studio customizations for a specific view.

    Each customization record represents modifications to a base view,
    including field additions, removals, reorderings, and attribute changes.
    """
    _name = 'studio.view.customization'
    _description = 'Studio View Customization'
    _order = 'model_name, view_type'

    name = fields.Char(
        string='Name',
        required=True,
        help="Descriptive name for this customization"
    )
    model_name = fields.Char(
        string='Model',
        required=True,
        index=True,
        help="Technical name of the model (e.g., res.partner)"
    )
    model_id = fields.Many2one(
        'ir.model',
        string='Model Reference',
        compute='_compute_model_id',
        store=True,
        ondelete='cascade'
    )
    view_type = fields.Selection([
        ('form', 'Form'),
        ('list', 'List'),
        ('kanban', 'Kanban'),
        ('calendar', 'Calendar'),
        ('pivot', 'Pivot'),
        ('graph', 'Graph'),
        ('search', 'Search'),
    ], string='View Type', required=True)

    # Related app (optional - some customizations are standalone)
    app_id = fields.Many2one(
        'studio.app',
        string='Studio App',
        ondelete='cascade'
    )

    # Original view reference
    base_view_id = fields.Many2one(
        'ir.ui.view',
        string='Base View',
        help="Original view being customized"
    )

    # Generated view
    generated_view_id = fields.Many2one(
        'ir.ui.view',
        string='Generated View',
        readonly=True,
        help="Studio-generated view record"
    )

    # Field customizations
    field_ids = fields.One2many(
        'studio.view.field',
        'customization_id',
        string='Fields',
        help="Field configurations for this view"
    )

    # JSON storage for complex customizations
    arch_json = fields.Text(
        string='Customization Data',
        help="JSON representation of view customizations"
    )

    # State
    active = fields.Boolean(default=True)

    # Audit
    last_modified = fields.Datetime(
        string='Last Modified',
        default=fields.Datetime.now
    )
    modified_by_id = fields.Many2one(
        'res.users',
        string='Modified By',
        default=lambda self: self.env.user
    )

    @api.depends('model_name')
    def _compute_model_id(self):
        IrModel = self.env['ir.model']
        for cust in self:
            if cust.model_name:
                cust.model_id = IrModel.search([
                    ('model', '=', cust.model_name)
                ], limit=1)
            else:
                cust.model_id = False

    @api.model
    def _get_or_create_customization(self, model, view_type):
        """Get existing customization or create a new one."""
        customization = self.search([
            ('model_name', '=', model),
            ('view_type', '=', view_type),
            ('active', '=', True),
        ], limit=1)

        if not customization:
            # Find base view
            base_view = self.env['ir.ui.view'].search([
                ('model', '=', model),
                ('type', '=', view_type),
            ], order='priority', limit=1)

            customization = self.create({
                'name': f"Studio: {model} {view_type}",
                'model_name': model,
                'view_type': view_type,
                'base_view_id': base_view.id if base_view else False,
            })

        return customization

    # ---------------------------------
    # Field Management
    # ---------------------------------

    def add_field_to_view(self, field_id, position='inside', after_field=None):
        """
        Add a field to this view.

        Args:
            field_id: ID of ir.model.fields record
            position: Where to place ('inside', 'before', 'after')
            after_field: Field name to place after (if position='after')

        Returns:
            Created studio.view.field record
        """
        self.ensure_one()

        field = self.env['ir.model.fields'].browse(field_id)
        if not field.exists():
            raise ValidationError(_("Field not found."))

        # Compute sequence
        sequence = 10
        if after_field:
            after = self.field_ids.filtered(
                lambda f: f.field_id.name == after_field
            )
            if after:
                sequence = after.sequence + 5

        # Check if field already in view
        existing = self.field_ids.filtered(
            lambda f: f.field_id.id == field_id
        )
        if existing:
            # Update existing
            existing.write({'sequence': sequence, 'visible': True})
            view_field = existing
        else:
            # Create new
            view_field = self.env['studio.view.field'].create({
                'customization_id': self.id,
                'field_id': field_id,
                'sequence': sequence,
                'visible': True,
            })

        # Regenerate view
        self._generate_view()

        self.write({
            'last_modified': fields.Datetime.now(),
            'modified_by_id': self.env.user.id,
        })

        return view_field

    def remove_field_from_view(self, field_name):
        """Remove or hide a field from this view."""
        self.ensure_one()

        field = self.field_ids.filtered(
            lambda f: f.field_id.name == field_name
        )
        if field:
            field.write({'visible': False})
            self._generate_view()

            self.write({
                'last_modified': fields.Datetime.now(),
                'modified_by_id': self.env.user.id,
            })

    def reorder_fields(self, field_order):
        """
        Reorder fields in this view.

        Args:
            field_order: List of field names in desired order
        """
        self.ensure_one()

        for idx, field_name in enumerate(field_order):
            field = self.field_ids.filtered(
                lambda f: f.field_id.name == field_name
            )
            if field:
                field.write({'sequence': idx * 10})

        self._generate_view()

        self.write({
            'last_modified': fields.Datetime.now(),
            'modified_by_id': self.env.user.id,
        })

    def update_field_attributes(self, field_name, attributes):
        """
        Update attributes for a field.

        Args:
            field_name: Name of the field
            attributes: Dict of attributes to update
                - widget: Widget to use
                - readonly: Make field readonly
                - required: Make field required
                - invisible_domain: Domain for visibility
                - custom_label: Override label
                - group_name: Group for form views
        """
        self.ensure_one()

        field = self.field_ids.filtered(
            lambda f: f.field_id.name == field_name
        )
        if not field:
            raise ValidationError(_(
                "Field '%(name)s' not found in this view.",
                name=field_name
            ))

        field.write(attributes)
        self._generate_view()

        self.write({
            'last_modified': fields.Datetime.now(),
            'modified_by_id': self.env.user.id,
        })

    # ---------------------------------
    # List View Specific
    # ---------------------------------

    @api.model
    def add_list_column(self, model, field_name, position=-1):
        """Add a column to a list view."""
        customization = self._get_or_create_customization(model, 'list')

        field = self.env['ir.model.fields'].search([
            ('model', '=', model),
            ('name', '=', field_name),
        ], limit=1)

        if not field:
            raise ValidationError(_(
                "Field '%(name)s' not found on model '%(model)s'.",
                name=field_name, model=model
            ))

        return customization.add_field_to_view(field.id)

    @api.model
    def remove_list_column(self, model, field_name):
        """Remove a column from a list view."""
        customization = self._get_or_create_customization(model, 'list')
        customization.remove_field_from_view(field_name)

    @api.model
    def reorder_list_columns(self, model, from_index, to_index):
        """Reorder columns in a list view."""
        customization = self._get_or_create_customization(model, 'list')

        # Get current field order
        fields = customization.field_ids.sorted('sequence')
        field_names = [f.field_id.name for f in fields if f.visible]

        if 0 <= from_index < len(field_names) and 0 <= to_index < len(field_names):
            # Move field
            field_name = field_names.pop(from_index)
            field_names.insert(to_index, field_name)
            customization.reorder_fields(field_names)

    # ---------------------------------
    # View Generation
    # ---------------------------------

    def _generate_view(self):
        """Generate or update the ir.ui.view from this customization."""
        self.ensure_one()

        arch = self._build_arch()
        if not arch:
            return

        view_vals = {
            'name': f"studio.{self.model_name}.{self.view_type}",
            'model': self.model_name,
            'type': self.view_type,
            'arch_db': arch,
            'priority': 99,  # Low priority = loads after other views
        }

        # If we have a base view, create an inheriting view
        if self.base_view_id:
            view_vals['inherit_id'] = self.base_view_id.id
            # For inheritance, we need xpath-based arch
            arch = self._build_inherit_arch()
            if arch:
                view_vals['arch_db'] = arch

        if self.generated_view_id:
            self.generated_view_id.write(view_vals)
        else:
            view = self.env['ir.ui.view'].sudo().create(view_vals)
            self.generated_view_id = view

    def _build_arch(self):
        """Build complete XML architecture from customization."""
        builder = getattr(self, f'_build_{self.view_type}_arch', None)
        if builder:
            return builder()
        return None

    def _build_inherit_arch(self):
        """Build inheritance arch with xpaths."""
        # For now, return complete view
        # TODO: Generate proper xpath operations
        return self._build_arch()

    def _build_form_arch(self):
        """Build form view XML."""
        fields = self.field_ids.filtered('visible').sorted('sequence')
        if not fields:
            return None

        root = etree.Element('form')
        sheet = etree.SubElement(root, 'sheet')

        # Group fields by group_name
        grouped = defaultdict(list)
        for field_rec in fields:
            group_name = field_rec.group_name or 'main'
            grouped[group_name].append(field_rec)

        # Create groups
        main_group = etree.SubElement(sheet, 'group')

        for group_name, group_fields in grouped.items():
            if group_name == 'main':
                group = main_group
            else:
                group = etree.SubElement(main_group, 'group', string=group_name)

            for field_rec in group_fields:
                self._add_field_element(group, field_rec)

        return etree.tostring(root, encoding='unicode', pretty_print=True)

    def _build_list_arch(self):
        """Build list/tree view XML."""
        fields = self.field_ids.filtered('visible').sorted('sequence')
        if not fields:
            return None

        root = etree.Element('list')

        for field_rec in fields:
            self._add_field_element(root, field_rec)

        return etree.tostring(root, encoding='unicode', pretty_print=True)

    def _build_kanban_arch(self):
        """Build kanban view XML."""
        fields = self.field_ids.filtered('visible').sorted('sequence')
        if not fields:
            return None

        root = etree.Element('kanban')
        templates = etree.SubElement(root, 'templates')
        kanban_box = etree.SubElement(templates, 't')
        kanban_box.set('t-name', 'kanban-box')

        div = etree.SubElement(kanban_box, 'div')
        div.set('class', 'oe_kanban_card oe_kanban_global_click')

        content = etree.SubElement(div, 'div')
        content.set('class', 'oe_kanban_content')

        # Add first field as title
        if fields:
            strong = etree.SubElement(content, 'strong')
            field_el = etree.SubElement(strong, 'field')
            field_el.set('name', fields[0].field_id.name)

            # Add other fields
            for field_rec in fields[1:5]:  # Limit to 5 fields
                field_el = etree.SubElement(content, 'field')
                field_el.set('name', field_rec.field_id.name)

        return etree.tostring(root, encoding='unicode', pretty_print=True)

    def _build_search_arch(self):
        """Build search view XML."""
        fields = self.field_ids.filtered('visible').sorted('sequence')
        if not fields:
            return None

        root = etree.Element('search')

        for field_rec in fields[:10]:  # Limit search fields
            field_el = etree.SubElement(root, 'field')
            field_el.set('name', field_rec.field_id.name)

        return etree.tostring(root, encoding='unicode', pretty_print=True)

    def _add_field_element(self, parent, field_rec):
        """Add a field element to parent XML element."""
        field_el = etree.SubElement(parent, 'field')
        field_el.set('name', field_rec.field_id.name)

        if field_rec.widget:
            field_el.set('widget', field_rec.widget)
        if field_rec.readonly:
            field_el.set('readonly', '1')
        if field_rec.required:
            field_el.set('required', '1')
        if field_rec.invisible_domain:
            field_el.set('invisible', field_rec.invisible_domain)
        if field_rec.custom_label:
            field_el.set('string', field_rec.custom_label)
        if field_rec.column_width and self.view_type == 'list':
            field_el.set('width', field_rec.column_width)

        return field_el

    def action_reset(self):
        """Reset customization, reverting to base view."""
        self.ensure_one()

        if self.generated_view_id:
            self.generated_view_id.unlink()

        self.field_ids.unlink()
        self.write({
            'generated_view_id': False,
            'arch_json': False,
        })

        return True
