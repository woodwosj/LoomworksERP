# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
IR UI View Extensions for Studio integration.

Extends ir.ui.view with fields to track Studio customizations
and enable view backup/restore functionality.
"""

from loomworks import api, models, fields


class IrUIView(models.Model):
    """Extends ir.ui.view with Studio tracking."""
    _inherit = 'ir.ui.view'

    # Studio tracking
    studio_customized = fields.Boolean(
        string='Studio Customized',
        default=False,
        help="Indicates this view was modified via Studio"
    )
    studio_customization_id = fields.Many2one(
        'studio.view.customization',
        string='Studio Customization',
        ondelete='set null',
        help="Link to the Studio customization record"
    )
    studio_arch_backup = fields.Text(
        string='Original Architecture',
        help="Backup of the original arch before Studio modifications"
    )

    def _studio_backup_arch(self):
        """Backup the original arch before first Studio modification."""
        for view in self:
            if not view.studio_arch_backup and view.arch:
                view.write({
                    'studio_arch_backup': view.arch,
                    'studio_customized': True,
                })

    def _studio_restore_arch(self):
        """Restore the original arch, removing Studio customizations."""
        for view in self:
            if view.studio_arch_backup:
                view.write({
                    'arch_db': view.studio_arch_backup,
                    'studio_arch_backup': False,
                    'studio_customized': False,
                    'studio_customization_id': False,
                })

    def action_studio_restore(self):
        """Button action to restore original view."""
        self._studio_restore_arch()
        return True

    def action_open_studio(self):
        """Open Studio editor for this view."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'loomworks_studio_view_editor',
            'params': {
                'view_id': self.id,
                'model': self.model,
                'view_type': self.type,
            },
        }
