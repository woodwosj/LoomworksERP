# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

import secrets
from loomworks import api, fields, models


class SignRequestSigner(models.Model):
    """Signature Request Signer

    Represents an individual who must sign a document. Tracks their
    signing status, access credentials, and completed fields.
    """
    _name = 'sign.request.signer'
    _description = 'Signature Request Signer'
    _order = 'sequence, id'

    request_id = fields.Many2one(
        'sign.request',
        string='Request',
        required=True,
        ondelete='cascade',
        index=True
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Signing order when sequential signing is required'
    )

    # Signer Identity
    partner_id = fields.Many2one(
        'res.partner',
        string='Signer',
        required=True,
        help='Contact who will sign'
    )
    email = fields.Char(
        string='Email',
        related='partner_id.email',
        store=True
    )
    phone = fields.Char(
        string='Phone',
        related='partner_id.phone'
    )

    # Role
    role_id = fields.Many2one(
        'sign.role',
        string='Role',
        required=True,
        default=lambda self: self.env['sign.role'].get_default_role()
    )

    # Status
    state = fields.Selection([
        ('waiting', 'Waiting'),
        ('sent', 'Email Sent'),
        ('viewed', 'Document Viewed'),
        ('signing', 'Signing'),
        ('done', 'Signed'),
        ('refused', 'Refused')
    ], default='waiting', string='Status', tracking=True)

    # Signing Data
    signed_date = fields.Datetime(
        string='Signed Date',
        readonly=True
    )
    signature_data = fields.Binary(
        string='Signature Image',
        help='Primary signature capture'
    )
    signature_type = fields.Selection([
        ('draw', 'Drawn'),
        ('type', 'Typed'),
        ('upload', 'Uploaded')
    ], string='Signature Type')

    # Security & Access
    access_token = fields.Char(
        string='Access Token',
        copy=False,
        default=lambda self: secrets.token_urlsafe(32),
        index=True
    )

    # Audit Metadata
    signing_ip = fields.Char(
        string='IP Address',
        readonly=True
    )
    signing_user_agent = fields.Char(
        string='User Agent',
        readonly=True
    )
    view_date = fields.Datetime(
        string='First Viewed',
        readonly=True
    )

    # Completed field values
    item_value_ids = fields.One2many(
        'sign.request.item.value',
        'signer_id',
        string='Field Values'
    )

    # Related fields for display
    request_name = fields.Char(
        related='request_id.name',
        string='Request Reference'
    )
    template_name = fields.Char(
        related='request_id.template_id.name',
        string='Template'
    )

    def action_resend_email(self):
        """Resend signature request email."""
        self.ensure_one()
        self.request_id._send_signature_email(self)
        self.state = 'sent'
        return True

    def action_refuse(self, reason=None):
        """Mark signer as refused."""
        self.ensure_one()
        self.state = 'refused'
        self.request_id._log_audit(
            'refuse',
            f'{self.partner_id.name} refused to sign. Reason: {reason or "Not specified"}',
            signer_id=self.id
        )
        return True

    def mark_viewed(self, ip=None, user_agent=None):
        """Mark document as viewed by signer."""
        self.ensure_one()
        if self.state == 'sent':
            self.write({
                'state': 'viewed',
                'view_date': fields.Datetime.now(),
                'signing_ip': ip,
                'signing_user_agent': user_agent,
            })
            self.request_id._log_audit(
                'view',
                f'{self.partner_id.name} viewed the document',
                signer_id=self.id,
                ip=ip,
                user_agent=user_agent
            )

    def name_get(self):
        result = []
        for signer in self:
            name = f"{signer.request_id.name or 'Request'} - {signer.partner_id.name or 'Signer'}"
            result.append((signer.id, name))
        return result
