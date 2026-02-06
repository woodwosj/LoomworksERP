# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Studio App Model - Custom application registry.

Each Studio App groups related models, menus, and views into a logical
application that can be managed, exported, and imported as a unit.
"""

import re
import json
import logging
from datetime import datetime

from loomworks import api, models, fields, _
from loomworks.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class StudioApp(models.Model):
    """
    Custom application definition created via Studio.

    A Studio App serves as a container for:
    - Custom models (prefixed with x_[technical_name]_)
    - Menu items and actions
    - View customizations
    - Automations and workflows
    """
    _name = 'studio.app'
    _description = 'Studio Custom Application'
    _order = 'sequence, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Application Name',
        required=True,
        tracking=True,
        help="Display name shown in menus and navigation"
    )
    technical_name = fields.Char(
        string='Technical Name',
        required=True,
        help="Used as prefix for models: x_[technical_name]_modelname"
    )
    description = fields.Text(
        string='Description',
        help="Detailed description of what this application does"
    )
    icon = fields.Char(
        string='Icon',
        default='fa-cube',
        help="FontAwesome icon class (e.g., fa-cube, fa-users)"
    )
    color = fields.Integer(
        string='Color Index',
        default=0,
        help="Color used in kanban views (0-11)"
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Display order in menus"
    )

    # Related Components
    model_ids = fields.One2many(
        'ir.model',
        'studio_app_id',
        string='Models',
        help="Custom models belonging to this application"
    )
    menu_id = fields.Many2one(
        'ir.ui.menu',
        string='Root Menu',
        ondelete='set null',
        help="Main menu entry for this application"
    )
    action_id = fields.Many2one(
        'ir.actions.act_window',
        string='Default Action',
        ondelete='set null',
        help="Action opened when clicking the main menu"
    )
    automation_ids = fields.One2many(
        'studio.automation',
        'app_id',
        string='Automations',
        help="Workflow rules and automations"
    )
    view_customization_ids = fields.One2many(
        'studio.view.customization',
        'app_id',
        string='View Customizations'
    )

    # State Management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ], string='State', default='draft', tracking=True)
    active = fields.Boolean(default=True)

    # Audit Fields
    created_by_id = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
        readonly=True
    )
    published_date = fields.Datetime(
        string='Published Date',
        readonly=True
    )

    # Statistics (Computed)
    model_count = fields.Integer(
        string='Model Count',
        compute='_compute_model_count',
        store=True
    )
    record_count = fields.Integer(
        string='Total Records',
        compute='_compute_record_count'
    )
    automation_count = fields.Integer(
        string='Automation Count',
        compute='_compute_automation_count',
        store=True
    )

    # Export Data
    export_data = fields.Text(
        string='Export JSON',
        compute='_compute_export_data',
        help="JSON representation of the app for export"
    )

    # Constraints
    _sql_constraints = [
        ('technical_name_unique', 'UNIQUE(technical_name)',
         'Technical name must be unique!'),
    ]

    @api.constrains('technical_name')
    def _check_technical_name(self):
        """Validate technical name format."""
        for app in self:
            if not app.technical_name:
                continue
            if not re.match(r'^[a-z][a-z0-9_]*$', app.technical_name):
                raise ValidationError(_(
                    "Technical name '%(name)s' is invalid. It must contain only "
                    "lowercase letters, numbers, and underscores, and start with a letter.",
                    name=app.technical_name
                ))
            if len(app.technical_name) > 50:
                raise ValidationError(_(
                    "Technical name must be 50 characters or less."
                ))

    @api.depends('model_ids')
    def _compute_model_count(self):
        for app in self:
            app.model_count = len(app.model_ids)

    def _compute_record_count(self):
        """Count total records across all models in the app."""
        for app in self:
            count = 0
            for model in app.model_ids:
                try:
                    if model.model in self.env:
                        count += self.env[model.model].sudo().search_count([])
                except Exception as e:
                    _logger.warning(
                        "Could not count records for model %s: %s",
                        model.model, e
                    )
            app.record_count = count

    @api.depends('automation_ids')
    def _compute_automation_count(self):
        for app in self:
            app.automation_count = len(app.automation_ids)

    def _compute_export_data(self):
        """Generate JSON export of the app definition."""
        for app in self:
            app.export_data = json.dumps(app._get_export_dict(), indent=2)

    def _get_export_dict(self):
        """Generate export dictionary for this app."""
        self.ensure_one()
        return {
            'name': self.name,
            'technical_name': self.technical_name,
            'description': self.description,
            'icon': self.icon,
            'color': self.color,
            'models': [
                {
                    'name': m.name,
                    'model': m.model,
                    'fields': [
                        {
                            'name': f.name,
                            'field_description': f.field_description,
                            'ttype': f.ttype,
                            'required': f.required,
                            'relation': f.relation,
                        }
                        for f in m.field_id.filtered(lambda f: f.state == 'manual')
                    ]
                }
                for m in self.model_ids
            ],
            'automations': [
                {
                    'name': a.name,
                    'trigger_type': a.trigger_type,
                    'model_id': a.model_id.model if a.model_id else None,
                    'action_type': a.action_type,
                    'python_code': a.python_code,
                }
                for a in self.automation_ids
            ],
            'exported_at': datetime.now().isoformat(),
            'version': '1.0',
        }

    # ---------------------------------
    # Actions
    # ---------------------------------

    def action_create_model(self, vals):
        """
        Create a new model for this Studio app.

        Args:
            vals: Dictionary containing:
                - name: Human-readable model name
                - model: Technical model name (will be prefixed)
                - fields: List of field definitions
                - create_menu: Whether to create menu item
                - create_views: List of view types to generate

        Returns:
            Created ir.model record
        """
        self.ensure_one()

        # Ensure draft state
        if self.state == 'archived':
            raise UserError(_("Cannot modify archived applications."))

        # Prefix model name with app technical name
        model_name = vals.get('model', vals.get('name', '')).lower()
        model_name = re.sub(r'[^a-z0-9_]', '_', model_name)
        model_name = re.sub(r'_+', '_', model_name).strip('_')

        if not model_name:
            raise ValidationError(_("Model name is required."))

        technical_name = f"x_{self.technical_name}_{model_name}"

        # Check for existing model
        existing = self.env['ir.model'].search([
            ('model', '=', technical_name)
        ])
        if existing:
            raise ValidationError(_(
                "A model with technical name '%(name)s' already exists.",
                name=technical_name
            ))

        # Prepare model creation values
        model_vals = {
            'name': vals.get('name', model_name.replace('_', ' ').title()),
            'model': technical_name,
            'state': 'manual',
            'studio_app_id': self.id,
        }

        # Create the model
        new_model = self.env['ir.model'].sudo().create(model_vals)

        # Create default name field if not provided
        fields_data = vals.get('fields', [])
        has_name_field = any(
            f.get('name') in ('x_name', 'name') for f in fields_data
        )

        if not has_name_field:
            fields_data.insert(0, {
                'name': 'x_name',
                'label': 'Name',
                'type': 'char',
                'required': True,
            })

        # Create fields
        for field_def in fields_data:
            self._create_field_for_model(new_model, field_def)

        # Setup ORM for new model
        self._setup_new_model(new_model)

        # Create default views
        create_views = vals.get('create_views', ['form', 'list'])
        if create_views:
            self._create_default_views(new_model, create_views)

        # Create menu if requested
        if vals.get('create_menu', True):
            self._create_model_menu(new_model)

        _logger.info(
            "Created Studio model %s for app %s",
            technical_name, self.name
        )

        return new_model

    def _create_field_for_model(self, model, field_def):
        """Create a field on the given model."""
        field_name = field_def.get('name', '')
        if not field_name.startswith('x_'):
            field_name = f"x_{field_name}"

        # Normalize field name
        field_name = re.sub(r'[^a-z0-9_]', '_', field_name.lower())

        ttype = field_def.get('type', 'char')

        vals = {
            'model_id': model.id,
            'name': field_name,
            'field_description': field_def.get('label', field_name),
            'ttype': ttype,
            'state': 'manual',
            'required': field_def.get('required', False),
            'index': field_def.get('index', False),
            'copied': field_def.get('copied', True),
            'help': field_def.get('help', ''),
        }

        # Type-specific attributes
        if ttype == 'selection':
            selection = field_def.get('selection', [])
            if selection:
                vals['selection_ids'] = [
                    (0, 0, {'value': opt[0], 'name': opt[1], 'sequence': idx * 10})
                    for idx, opt in enumerate(selection)
                ]
        elif ttype in ('many2one', 'one2many', 'many2many'):
            relation = field_def.get('relation')
            if relation:
                vals['relation'] = relation
                if ttype == 'one2many':
                    vals['relation_field'] = field_def.get('relation_field')
        elif ttype in ('char', 'text'):
            if 'size' in field_def:
                vals['size'] = field_def['size']
        elif ttype == 'float':
            # Store digits as JSON string for precision
            digits = field_def.get('digits')
            if digits:
                vals['digits'] = str(digits)

        return self.env['ir.model.fields'].sudo().create(vals)

    def _setup_new_model(self, model):
        """Initialize the ORM for a newly created model."""
        try:
            # This forces Odoo to recognize the new model
            self.env.registry.init_models(
                self.env.cr,
                [model.model],
                {'module': 'loomworks_studio'}
            )
        except Exception as e:
            _logger.warning(
                "Could not fully initialize model %s: %s",
                model.model, e
            )

    def _create_default_views(self, model, view_types):
        """Generate default views for a model."""
        IrUIView = self.env['ir.ui.view'].sudo()

        for view_type in view_types:
            arch = self._generate_view_arch(model, view_type)
            if arch:
                IrUIView.create({
                    'name': f"studio.{model.model}.{view_type}",
                    'model': model.model,
                    'type': view_type,
                    'arch_db': arch,
                    'priority': 16,
                })

    def _generate_view_arch(self, model, view_type):
        """Generate XML architecture for a view type."""
        fields = model.field_id.filtered(lambda f: f.state == 'manual')

        if view_type == 'form':
            return self._generate_form_view(model, fields)
        elif view_type == 'list':
            return self._generate_list_view(model, fields)
        elif view_type == 'search':
            return self._generate_search_view(model, fields)
        elif view_type == 'kanban':
            return self._generate_kanban_view(model, fields)

        return None

    def _generate_form_view(self, model, fields):
        """Generate form view XML."""
        field_elements = []

        # Name field first if exists
        name_field = fields.filtered(lambda f: f.name in ('x_name', 'name'))
        if name_field:
            field_elements.append(f'<field name="{name_field[0].name}"/>')
            fields = fields - name_field

        # Other fields in two-column layout
        other_fields = '\n                        '.join(
            f'<field name="{f.name}"/>'
            for f in fields[:20]  # Limit to 20 fields
        )

        return f'''<?xml version="1.0"?>
<form string="{model.name}">
    <sheet>
        <div class="oe_title">
            <h1>
                {field_elements[0] if field_elements else '<field name="display_name"/>'}
            </h1>
        </div>
        <group>
            <group>
                {other_fields}
            </group>
        </group>
    </sheet>
    <div class="oe_chatter">
        <field name="message_follower_ids"/>
        <field name="message_ids"/>
    </div>
</form>'''

    def _generate_list_view(self, model, fields):
        """Generate list/tree view XML."""
        field_elements = '\n        '.join(
            f'<field name="{f.name}"/>'
            for f in fields[:10]  # Limit to 10 columns
        )

        return f'''<?xml version="1.0"?>
<list string="{model.name}">
    {field_elements}
</list>'''

    def _generate_search_view(self, model, fields):
        """Generate search view XML."""
        searchable = fields.filtered(
            lambda f: f.ttype in ('char', 'text', 'selection', 'many2one')
        )[:5]

        field_elements = '\n        '.join(
            f'<field name="{f.name}"/>'
            for f in searchable
        )

        return f'''<?xml version="1.0"?>
<search string="{model.name}">
    {field_elements}
</search>'''

    def _generate_kanban_view(self, model, fields):
        """Generate kanban view XML."""
        name_field = fields.filtered(
            lambda f: f.name in ('x_name', 'name')
        )
        name = name_field[0].name if name_field else 'display_name'

        return f'''<?xml version="1.0"?>
<kanban string="{model.name}">
    <templates>
        <t t-name="kanban-box">
            <div class="oe_kanban_card oe_kanban_global_click">
                <div class="oe_kanban_content">
                    <strong><field name="{name}"/></strong>
                </div>
            </div>
        </t>
    </templates>
</kanban>'''

    def _create_model_menu(self, model):
        """Create menu and action for a model."""
        # Create action
        action = self.env['ir.actions.act_window'].sudo().create({
            'name': model.name,
            'res_model': model.model,
            'view_mode': 'list,form,kanban',
            'target': 'current',
        })

        # Get or create app root menu
        if not self.menu_id:
            studio_root = self.env.ref(
                'loomworks_studio.menu_studio_apps',
                raise_if_not_found=False
            )
            parent_id = studio_root.id if studio_root else False

            app_menu = self.env['ir.ui.menu'].sudo().create({
                'name': self.name,
                'parent_id': parent_id,
                'sequence': self.sequence,
            })
            self.menu_id = app_menu
            self.action_id = action

        # Create model menu under app
        self.env['ir.ui.menu'].sudo().create({
            'name': model.name,
            'parent_id': self.menu_id.id,
            'action': f'ir.actions.act_window,{action.id}',
            'sequence': 10,
        })

    def action_publish(self):
        """Publish the application, making it available to users."""
        for app in self:
            if app.state != 'draft':
                raise UserError(_(
                    "Only draft applications can be published."
                ))
            app.write({
                'state': 'published',
                'published_date': fields.Datetime.now(),
            })
        return True

    def action_archive(self):
        """Archive the application."""
        self.write({'state': 'archived', 'active': False})
        return True

    def action_unarchive(self):
        """Restore an archived application."""
        self.write({'state': 'published', 'active': True})
        return True

    def action_export(self):
        """Export the application as JSON."""
        self.ensure_one()
        export_data = self._get_export_dict()

        # Create attachment
        attachment = self.env['ir.attachment'].sudo().create({
            'name': f"{self.technical_name}_export.json",
            'type': 'binary',
            'datas': json.dumps(export_data, indent=2).encode('utf-8'),
            'mimetype': 'application/json',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    @api.model
    def action_import(self, json_data):
        """Import an application from JSON data."""
        try:
            data = json.loads(json_data) if isinstance(json_data, str) else json_data
        except json.JSONDecodeError as e:
            raise ValidationError(_(
                "Invalid JSON data: %(error)s",
                error=str(e)
            ))

        # Validate required fields
        required = ['name', 'technical_name']
        for field in required:
            if not data.get(field):
                raise ValidationError(_(
                    "Missing required field: %(field)s",
                    field=field
                ))

        # Check for existing app
        existing = self.search([
            ('technical_name', '=', data['technical_name'])
        ])
        if existing:
            raise ValidationError(_(
                "An application with technical name '%(name)s' already exists.",
                name=data['technical_name']
            ))

        # Create app
        app = self.create({
            'name': data['name'],
            'technical_name': data['technical_name'],
            'description': data.get('description', ''),
            'icon': data.get('icon', 'fa-cube'),
            'color': data.get('color', 0),
        })

        # Create models
        for model_data in data.get('models', []):
            app.action_create_model({
                'name': model_data['name'],
                'model': model_data.get('model', '').replace(
                    f"x_{data['technical_name']}_", ''
                ),
                'fields': model_data.get('fields', []),
            })

        # Create automations
        for auto_data in data.get('automations', []):
            model = self.env['ir.model'].search([
                ('model', '=', auto_data.get('model_id'))
            ], limit=1)

            if model:
                self.env['studio.automation'].create({
                    'name': auto_data['name'],
                    'app_id': app.id,
                    'model_id': model.id,
                    'trigger_type': auto_data.get('trigger_type', 'on_create'),
                    'action_type': auto_data.get('action_type', 'python_code'),
                    'python_code': auto_data.get('python_code', ''),
                })

        _logger.info("Imported Studio app: %s", app.name)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'studio.app',
            'res_id': app.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_builder(self):
        """Open the Studio visual builder for this app."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'loomworks_studio_builder',
            'params': {
                'app_id': self.id,
                'app_name': self.name,
            },
        }
