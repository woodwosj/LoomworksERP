# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
IR Model Extensions for Studio integration.

Extends ir.model with Studio-specific fields and methods for
tracking custom models created via Studio.
"""

from odoo import api, models, fields


class IrModel(models.Model):
    """Extends ir.model with Studio integration."""
    _inherit = 'ir.model'

    # Studio Integration
    studio_app_id = fields.Many2one(
        'studio.app',
        string='Studio Application',
        ondelete='set null',
        help="The Studio app this model belongs to"
    )
    studio_origin = fields.Selection([
        ('odoo', 'Odoo Core'),
        ('studio', 'Studio Created'),
        ('customized', 'Studio Customized'),
    ], string='Origin', compute='_compute_studio_origin', store=True)

    # Display customization
    studio_icon = fields.Char(
        string='Icon',
        default='fa-cube',
        help="FontAwesome icon for this model"
    )
    studio_color = fields.Integer(
        string='Color',
        default=0,
        help="Color index for kanban cards"
    )
    studio_description = fields.Text(
        string='Model Description',
        help="Detailed description of what this model represents"
    )

    @api.depends('state', 'studio_app_id')
    def _compute_studio_origin(self):
        """Determine the origin of each model."""
        for model in self:
            if model.studio_app_id:
                model.studio_origin = 'studio'
            elif model.state == 'manual':
                model.studio_origin = 'customized'
            else:
                model.studio_origin = 'odoo'

    def _get_studio_field_count(self):
        """Get count of custom fields added via Studio."""
        self.ensure_one()
        return self.env['ir.model.fields'].search_count([
            ('model_id', '=', self.id),
            ('state', '=', 'manual'),
        ])

    def action_open_studio(self):
        """Open Studio for this model."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'loomworks_studio_model_editor',
            'params': {
                'model_id': self.id,
                'model_name': self.model,
            },
        }
