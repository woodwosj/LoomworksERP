# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from loomworks import api, fields, models


class SignRole(models.Model):
    """Signer Roles

    Defines roles that can be assigned to signers (e.g., Customer, Vendor,
    Witness). Each role can have specific authentication requirements.
    """
    _name = 'sign.role'
    _description = 'Signer Role'
    _order = 'sequence'

    name = fields.Char(
        string='Role Name',
        required=True,
        translate=True
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )
    color = fields.Integer(
        string='Color Index',
        default=0
    )

    # Behavior
    can_reassign = fields.Boolean(
        string='Can Reassign',
        default=False,
        help='Signer can delegate signing to someone else'
    )

    # Authentication Method
    auth_method = fields.Selection([
        ('email', 'Email Link Only'),
        ('sms', 'SMS Code'),
        ('email_sms', 'Email + SMS'),
    ], default='email', string='Authentication Method',
        help='How signers in this role verify their identity')

    # Default settings
    is_default = fields.Boolean(
        string='Default Role',
        default=False,
        help='Automatically suggested when adding signers'
    )

    @api.model
    def get_default_role(self):
        """Return the default role or first available role."""
        role = self.search([('is_default', '=', True)], limit=1)
        if not role:
            role = self.search([], limit=1)
        return role
