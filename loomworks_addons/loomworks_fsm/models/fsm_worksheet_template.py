# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class FSMWorksheetTemplate(models.Model):
    """
    Worksheet Template - Configurable form templates for different service types.

    Templates define the fields technicians need to fill out during service,
    such as inspection checklists, service reports, etc.
    """
    _name = 'fsm.worksheet.template'
    _description = 'FSM Worksheet Template'
    _order = 'sequence, name'

    name = fields.Char(
        string='Name',
        required=True,
        translate=True)
    code = fields.Char(
        string='Code',
        required=True,
        help="Unique code for this template")
    sequence = fields.Integer(
        string='Sequence',
        default=10)
    active = fields.Boolean(
        string='Active',
        default=True)

    # Template fields
    field_ids = fields.One2many(
        'fsm.worksheet.field',
        'template_id',
        string='Fields')

    # Usage configuration
    project_ids = fields.Many2many(
        'project.project',
        string='Projects',
        help="Projects that can use this worksheet template")

    # Description
    description = fields.Html(
        string='Description',
        translate=True,
        help="Instructions for filling out this worksheet")

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company)

    _sql_constraints = [
        ('code_company_uniq', 'unique(code, company_id)',
         'The code must be unique per company!'),
    ]

    def get_template_schema(self):
        """
        Get the template as a JSON schema for frontend rendering.

        Returns:
            dict: JSON schema describing the worksheet fields
        """
        self.ensure_one()
        fields_schema = []

        for field in self.field_ids.sorted('sequence'):
            field_schema = {
                'name': field.technical_name,
                'label': field.name,
                'type': field.field_type,
                'required': field.required,
                'placeholder': field.placeholder or '',
                'sequence': field.sequence,
            }

            if field.field_type == 'select' and field.selection_options:
                field_schema['options'] = [
                    opt.strip() for opt in field.selection_options.split('\n')
                    if opt.strip()
                ]

            fields_schema.append(field_schema)

        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'description': self.description or '',
            'fields': fields_schema,
        }


class FSMWorksheetField(models.Model):
    """
    Worksheet Field - Individual field within a worksheet template.

    Supports various field types including text, number, checkbox,
    selection, date, photo, and signature.
    """
    _name = 'fsm.worksheet.field'
    _description = 'FSM Worksheet Field'
    _order = 'sequence, id'

    template_id = fields.Many2one(
        'fsm.worksheet.template',
        string='Template',
        required=True,
        ondelete='cascade')
    sequence = fields.Integer(
        string='Sequence',
        default=10)

    name = fields.Char(
        string='Label',
        required=True,
        translate=True,
        help="Display label for this field")
    technical_name = fields.Char(
        string='Technical Name',
        required=True,
        help="Field name used in data storage (no spaces, lowercase)")
    field_type = fields.Selection([
        ('text', 'Text'),
        ('textarea', 'Multi-line Text'),
        ('number', 'Number'),
        ('checkbox', 'Checkbox'),
        ('select', 'Selection'),
        ('date', 'Date'),
        ('datetime', 'Date & Time'),
        ('photo', 'Photo'),
        ('signature', 'Signature'),
        ('section', 'Section Header'),
    ], string='Type', required=True, default='text')

    # For selection fields
    selection_options = fields.Text(
        string='Options',
        help="One option per line for selection fields")

    # Validation
    required = fields.Boolean(
        string='Required',
        default=False)
    placeholder = fields.Char(
        string='Placeholder',
        translate=True)
    help_text = fields.Char(
        string='Help Text',
        translate=True,
        help="Additional instructions for this field")

    # Default value
    default_value = fields.Char(
        string='Default Value')

    @api.onchange('name')
    def _onchange_name(self):
        """Auto-generate technical name from label."""
        if self.name and not self.technical_name:
            import re
            # Convert to lowercase, replace spaces with underscores
            tech_name = self.name.lower().strip()
            tech_name = re.sub(r'[^a-z0-9]+', '_', tech_name)
            tech_name = re.sub(r'_+', '_', tech_name).strip('_')
            self.technical_name = tech_name
