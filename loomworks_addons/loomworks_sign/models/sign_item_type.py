# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SignItemType(models.Model):
    """Signature Field Type Configuration

    Defines the types of fields that can be placed on signature templates,
    such as signature, initials, text, date, checkbox, etc.
    """
    _name = 'sign.item.type'
    _description = 'Signature Field Type'
    _order = 'sequence'

    name = fields.Char(
        string='Name',
        required=True,
        translate=True
    )
    technical_name = fields.Char(
        string='Technical Name',
        required=True,
        help='Internal identifier for the field type'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )

    item_type = fields.Selection([
        ('signature', 'Signature'),
        ('initial', 'Initials'),
        ('text', 'Text Input'),
        ('textarea', 'Text Area'),
        ('checkbox', 'Checkbox'),
        ('selection', 'Selection'),
        ('date', 'Date'),
        ('name', 'Full Name'),
        ('email', 'Email'),
        ('company', 'Company'),
    ], string='Type', required=True,
        help='The type of data this field captures')

    # Display Configuration
    icon = fields.Char(
        string='Icon Class',
        default='fa-pencil',
        help='Font Awesome icon class for display'
    )
    color = fields.Integer(
        string='Color Index',
        default=0
    )

    # Default Dimensions (percentage of page)
    default_width = fields.Float(
        string='Default Width (%)',
        default=20.0,
        help='Default width as percentage of page width'
    )
    default_height = fields.Float(
        string='Default Height (%)',
        default=5.0,
        help='Default height as percentage of page height'
    )

    # Behavior
    auto_fill = fields.Boolean(
        string='Auto-fill from Signer',
        default=False,
        help='Automatically fill from signer partner data'
    )
    auto_fill_field = fields.Char(
        string='Auto-fill Field',
        help='Partner field name to use for auto-fill (e.g., name, email, company_id.name)'
    )

    def name_get(self):
        result = []
        for item_type in self:
            name = f"{item_type.name} ({item_type.item_type})"
            result.append((item_type.id, name))
        return result
