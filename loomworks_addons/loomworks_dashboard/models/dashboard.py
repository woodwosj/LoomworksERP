# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Dashboard Model - Main dashboard definition and configuration.

Each dashboard consists of:
- Basic metadata (name, description, owner)
- Tabs for organizing widgets
- Widgets placed on a canvas
- Global filters affecting all widgets
- Sharing/permissions settings
"""

from odoo import api, fields, models
from odoo.exceptions import UserError, AccessError
import json
import logging

_logger = logging.getLogger(__name__)


class Dashboard(models.Model):
    """
    Main dashboard definition model.

    A dashboard is a collection of widgets arranged on a canvas,
    optionally organized into tabs, with global filters.
    """
    _name = 'dashboard.board'
    _description = 'Dashboard'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    # Basic Information
    name = fields.Char(
        string='Name',
        required=True,
        tracking=True,
    )
    description = fields.Text(
        string='Description',
        help='Describe what this dashboard shows',
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )

    # Ownership and Access
    user_id = fields.Many2one(
        'res.users',
        string='Owner',
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )
    is_public = fields.Boolean(
        string='Public Dashboard',
        default=False,
        help='Allow all users to view this dashboard',
    )
    is_template = fields.Boolean(
        string='Is Template',
        default=False,
        help='This dashboard serves as a template for creating new dashboards',
    )

    # Layout Settings
    layout_columns = fields.Integer(
        string='Grid Columns',
        default=12,
        help='Number of columns in the dashboard grid',
    )
    auto_refresh = fields.Integer(
        string='Auto Refresh (seconds)',
        default=0,
        help='Refresh interval in seconds (0 = disabled)',
    )
    theme = fields.Selection([
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('auto', 'Auto (System)'),
    ], string='Theme', default='light')

    # Canvas Configuration (JSON)
    canvas_config = fields.Text(
        string='Canvas Configuration',
        default='{}',
        help='JSON configuration for the dashboard canvas (Gridstack settings)',
    )

    # Relations
    tab_ids = fields.One2many(
        'dashboard.tab',
        'dashboard_id',
        string='Tabs',
    )
    widget_ids = fields.One2many(
        'dashboard.widget',
        'dashboard_id',
        string='Widgets',
    )
    filter_ids = fields.One2many(
        'dashboard.filter',
        'dashboard_id',
        string='Filters',
    )
    share_ids = fields.One2many(
        'dashboard.share',
        'dashboard_id',
        string='Shares',
    )

    # Computed Fields
    widget_count = fields.Integer(
        string='Widget Count',
        compute='_compute_widget_count',
    )

    @api.depends('widget_ids')
    def _compute_widget_count(self):
        for dashboard in self:
            dashboard.widget_count = len(dashboard.widget_ids)

    # CRUD Operations
    @api.model_create_multi
    def create(self, vals_list):
        """Create dashboards with default tab if not provided."""
        dashboards = super().create(vals_list)
        for dashboard in dashboards:
            if not dashboard.tab_ids:
                self.env['dashboard.tab'].create({
                    'dashboard_id': dashboard.id,
                    'name': 'Main',
                    'sequence': 1,
                })
        return dashboards

    def copy(self, default=None):
        """Copy dashboard with all widgets and tabs."""
        self.ensure_one()
        default = dict(default or {})
        default['name'] = f"{self.name} (Copy)"
        default['user_id'] = self.env.user.id
        default['is_template'] = False
        return super().copy(default)

    # Access Control
    def _check_access(self, mode='read'):
        """Check if current user can access this dashboard."""
        self.ensure_one()
        user = self.env.user

        # Owner always has full access
        if self.user_id == user:
            return True

        # Admins have full access
        if user._is_admin():
            return True

        # Check public dashboards
        if mode == 'read' and self.is_public:
            return True

        # Check share permissions
        share = self.share_ids.filtered(
            lambda s: s.user_id == user or user.id in s.group_ids.users.ids
        )
        if share:
            if mode == 'read':
                return True
            if mode == 'write' and share.can_edit:
                return True

        return False

    # Dashboard Operations
    def action_open_dashboard(self):
        """Open the dashboard in the React canvas."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'loomworks_dashboard_action',
            'params': {
                'dashboard_id': self.id,
            },
            'name': self.name,
            'target': 'current',
        }

    def action_duplicate_as_template(self):
        """Create a template from this dashboard."""
        self.ensure_one()
        copy = self.copy({
            'is_template': True,
            'name': f"{self.name} Template",
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'dashboard.board',
            'res_id': copy.id,
            'view_mode': 'form',
        }

    def get_dashboard_data(self):
        """
        Get complete dashboard data for React canvas.

        Returns:
            dict: Dashboard configuration with widgets, tabs, filters
        """
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description or '',
            'layoutColumns': self.layout_columns,
            'autoRefresh': self.auto_refresh,
            'theme': self.theme,
            'canvasConfig': json.loads(self.canvas_config or '{}'),
            'tabs': [{
                'id': tab.id,
                'name': tab.name,
                'sequence': tab.sequence,
            } for tab in self.tab_ids.sorted('sequence')],
            'widgets': [widget.get_widget_data() for widget in self.widget_ids],
            'filters': [f.get_filter_data() for f in self.filter_ids],
            'editable': self._check_access('write'),
        }

    def save_from_canvas(self, canvas_data):
        """
        Save dashboard state from React canvas.

        Args:
            canvas_data: dict with widgets, layout, filters from React
        """
        self.ensure_one()
        if not self._check_access('write'):
            raise AccessError("You don't have permission to edit this dashboard")

        # Update canvas config
        if 'canvasConfig' in canvas_data:
            self.canvas_config = json.dumps(canvas_data['canvasConfig'])

        # Update widgets
        if 'widgets' in canvas_data:
            self._sync_widgets(canvas_data['widgets'])

        # Update filters
        if 'filters' in canvas_data:
            self._sync_filters(canvas_data['filters'])

        return True

    def _sync_widgets(self, widget_data_list):
        """Sync widgets from canvas data."""
        existing_ids = set(self.widget_ids.ids)
        updated_ids = set()

        for widget_data in widget_data_list:
            widget_id = widget_data.get('id')
            if widget_id and not str(widget_id).startswith('new_'):
                # Update existing widget
                widget = self.widget_ids.filtered(lambda w: w.id == int(widget_id))
                if widget:
                    widget.update_from_canvas(widget_data)
                    updated_ids.add(widget.id)
            else:
                # Create new widget
                new_widget = self.env['dashboard.widget'].create_from_canvas(
                    self.id, widget_data
                )
                updated_ids.add(new_widget.id)

        # Delete removed widgets
        removed_ids = existing_ids - updated_ids
        if removed_ids:
            self.env['dashboard.widget'].browse(list(removed_ids)).unlink()

    def _sync_filters(self, filter_data_list):
        """Sync filters from canvas data."""
        existing_ids = set(self.filter_ids.ids)
        updated_ids = set()

        for filter_data in filter_data_list:
            filter_id = filter_data.get('id')
            if filter_id and not str(filter_id).startswith('new_'):
                # Update existing filter
                dashboard_filter = self.filter_ids.filtered(
                    lambda f: f.id == int(filter_id)
                )
                if dashboard_filter:
                    dashboard_filter.update_from_canvas(filter_data)
                    updated_ids.add(dashboard_filter.id)
            else:
                # Create new filter
                new_filter = self.env['dashboard.filter'].create_from_canvas(
                    self.id, filter_data
                )
                updated_ids.add(new_filter.id)

        # Delete removed filters
        removed_ids = existing_ids - updated_ids
        if removed_ids:
            self.env['dashboard.filter'].browse(list(removed_ids)).unlink()


class DashboardTab(models.Model):
    """
    Dashboard tab for organizing widgets into sections.
    """
    _name = 'dashboard.tab'
    _description = 'Dashboard Tab'
    _order = 'sequence, id'

    name = fields.Char(
        string='Tab Name',
        required=True,
    )
    dashboard_id = fields.Many2one(
        'dashboard.board',
        string='Dashboard',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    icon = fields.Char(
        string='Icon',
        help='FontAwesome icon class (e.g., fa-chart-bar)',
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )
