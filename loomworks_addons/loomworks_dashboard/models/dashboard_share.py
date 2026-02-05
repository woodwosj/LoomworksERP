# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Dashboard Share Model - Sharing and permission management for dashboards.

Allows dashboard owners to share their dashboards with:
- Individual users
- User groups
- Public links (view-only)
"""

from odoo import api, fields, models
from odoo.exceptions import UserError
import uuid
import logging

_logger = logging.getLogger(__name__)


class DashboardShare(models.Model):
    """
    Dashboard sharing configuration.

    Each share record defines access for a user/group to a dashboard.
    """
    _name = 'dashboard.share'
    _description = 'Dashboard Share'
    _order = 'create_date desc'

    # Relations
    dashboard_id = fields.Many2one(
        'dashboard.board',
        string='Dashboard',
        required=True,
        ondelete='cascade',
    )

    # Share Target
    share_type = fields.Selection([
        ('user', 'User'),
        ('group', 'Group'),
        ('link', 'Public Link'),
    ], string='Share Type', default='user', required=True)

    user_id = fields.Many2one(
        'res.users',
        string='User',
        help='User to share with',
    )
    group_ids = fields.Many2many(
        'res.groups',
        'dashboard_share_group_rel',
        'share_id',
        'group_id',
        string='Groups',
        help='Groups to share with',
    )

    # Permissions
    can_edit = fields.Boolean(
        string='Can Edit',
        default=False,
        help='Allow editing the dashboard',
    )
    can_share = fields.Boolean(
        string='Can Share',
        default=False,
        help='Allow sharing with others',
    )

    # Public Link Settings
    public_token = fields.Char(
        string='Public Token',
        help='Token for public link access',
    )
    link_expires = fields.Datetime(
        string='Link Expires',
        help='When the public link expires',
    )
    link_password = fields.Char(
        string='Link Password',
        help='Password protection for public link',
    )
    link_views = fields.Integer(
        string='Link Views',
        default=0,
        readonly=True,
    )

    # Status
    active = fields.Boolean(
        string='Active',
        default=True,
    )
    shared_by = fields.Many2one(
        'res.users',
        string='Shared By',
        default=lambda self: self.env.user,
        readonly=True,
    )

    # Computed
    share_url = fields.Char(
        string='Share URL',
        compute='_compute_share_url',
    )

    @api.depends('public_token', 'share_type')
    def _compute_share_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for share in self:
            if share.share_type == 'link' and share.public_token:
                share.share_url = f"{base_url}/dashboard/public/{share.public_token}"
            else:
                share.share_url = False

    @api.model_create_multi
    def create(self, vals_list):
        """Create share records with tokens for public links."""
        for vals in vals_list:
            if vals.get('share_type') == 'link' and not vals.get('public_token'):
                vals['public_token'] = str(uuid.uuid4())
        return super().create(vals_list)

    @api.constrains('share_type', 'user_id', 'group_ids')
    def _check_share_target(self):
        for share in self:
            if share.share_type == 'user' and not share.user_id:
                raise UserError("Please select a user to share with")
            if share.share_type == 'group' and not share.group_ids:
                raise UserError("Please select at least one group to share with")

    def action_regenerate_token(self):
        """Regenerate public link token."""
        self.ensure_one()
        if self.share_type != 'link':
            raise UserError("Can only regenerate token for public links")
        self.public_token = str(uuid.uuid4())
        self.link_views = 0
        return True

    def action_copy_link(self):
        """Copy share link to clipboard (client-side)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Share Link',
                'message': f'Link: {self.share_url}',
                'type': 'info',
                'sticky': True,
                'buttons': [
                    {
                        'text': 'Copy',
                        'action': 'copy_to_clipboard',
                        'data': {'text': self.share_url},
                    }
                ],
            }
        }

    def record_view(self):
        """Record a view of the public link."""
        if self.share_type == 'link':
            self.sudo().write({'link_views': self.link_views + 1})

    def check_access(self, password=None):
        """
        Check if access is allowed for this share.

        Args:
            password: Password for password-protected links

        Returns:
            bool: True if access is allowed
        """
        self.ensure_one()

        # Check if active
        if not self.active:
            return False

        # Check expiration for links
        if self.share_type == 'link':
            if self.link_expires and fields.Datetime.now() > self.link_expires:
                return False

            # Check password
            if self.link_password and self.link_password != password:
                return False

        return True
