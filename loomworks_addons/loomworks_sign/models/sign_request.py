# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

import base64
import hashlib
import secrets
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SignRequest(models.Model):
    """Signature Request

    Main model for signature request workflows. Tracks the document
    being signed, signers, and completion status.
    """
    _name = 'sign.request'
    _description = 'Signature Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference',
        required=True,
        readonly=True,
        copy=False,
        default='New',
        tracking=True
    )

    # Document Source
    template_id = fields.Many2one(
        'sign.template',
        string='Template',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        tracking=True
    )

    # Working Documents
    attachment_id = fields.Many2one(
        'ir.attachment',
        string='Working Document',
        readonly=True,
        help='Current working copy of the document'
    )
    signed_attachment_id = fields.Many2one(
        'ir.attachment',
        string='Signed Document',
        readonly=True,
        help='Final signed document'
    )

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('signing', 'In Progress'),
        ('done', 'Completed'),
        ('canceled', 'Cancelled'),
        ('expired', 'Expired')
    ], default='draft', string='Status', tracking=True, index=True)

    # Signers
    signer_ids = fields.One2many(
        'sign.request.signer',
        'request_id',
        string='Signers',
        copy=True
    )
    signer_count = fields.Integer(
        compute='_compute_signer_stats',
        string='Signer Count'
    )
    completed_count = fields.Integer(
        compute='_compute_signer_stats',
        string='Completed Count'
    )
    progress_percentage = fields.Float(
        compute='_compute_signer_stats',
        string='Progress %'
    )

    # Request Details
    subject = fields.Char(
        string='Email Subject',
        default='Signature Request'
    )
    message = fields.Html(
        string='Message',
        help='Message to include in signature request email'
    )

    # Owner/Creator
    create_uid = fields.Many2one(
        'res.users',
        string='Created By',
        readonly=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )

    # Dates
    sent_date = fields.Datetime(
        string='Sent Date',
        readonly=True
    )
    expire_date = fields.Date(
        string='Expiration Date',
        help='Request expires after this date'
    )
    completion_date = fields.Datetime(
        string='Completion Date',
        readonly=True
    )

    # Security
    access_token = fields.Char(
        string='Access Token',
        copy=False,
        default=lambda self: secrets.token_urlsafe(32),
        index=True
    )

    # Audit
    audit_log_ids = fields.One2many(
        'sign.audit.log',
        'request_id',
        string='Audit Log'
    )
    audit_log_count = fields.Integer(
        compute='_compute_audit_log_count',
        string='Audit Log Count'
    )

    # Related Record (optional link to source)
    res_model = fields.Char(
        string='Related Model',
        help='Model of the record this request is linked to'
    )
    res_id = fields.Integer(
        string='Related Record ID'
    )

    # Display color for kanban
    color = fields.Integer(string='Color', default=0)

    # Signed field values
    item_value_ids = fields.One2many(
        'sign.request.item.value',
        'request_id',
        string='Field Values'
    )

    # Document integrity
    original_hash = fields.Char(
        string='Original Document Hash',
        readonly=True
    )
    final_hash = fields.Char(
        string='Final Document Hash',
        readonly=True
    )

    @api.depends('signer_ids', 'signer_ids.state')
    def _compute_signer_stats(self):
        for request in self:
            signers = request.signer_ids
            request.signer_count = len(signers)
            request.completed_count = len(signers.filtered(lambda s: s.state == 'done'))
            if request.signer_count:
                request.progress_percentage = (request.completed_count / request.signer_count) * 100
            else:
                request.progress_percentage = 0

    @api.depends('audit_log_ids')
    def _compute_audit_log_count(self):
        for request in self:
            request.audit_log_count = len(request.audit_log_ids)

    # ==================== CRUD ====================

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('sign.request') or 'New'

        records = super().create(vals_list)

        for record in records:
            # Prepare document from template
            if record.template_id and record.template_id.attachment_id:
                record._prepare_document()

            # Log creation
            record._log_audit('create', 'Signature request created')

        return records

    def _prepare_document(self):
        """Create working copy of template document with placeholders."""
        self.ensure_one()
        if not self.template_id or not self.template_id.attachment_id:
            return

        from loomworks_sign.services.pdf_service import PDFService
        pdf_service = PDFService(self.env)

        # Create copy with field placeholders
        prepared_pdf = pdf_service.prepare_document(self.template_id)

        self.attachment_id = self.env['ir.attachment'].create({
            'name': f'{self.name}.pdf',
            'datas': prepared_pdf,
            'mimetype': 'application/pdf',
            'res_model': 'sign.request',
            'res_id': self.id,
        })

        # Store original hash
        self.original_hash = pdf_service.get_document_hash(self.template_id.attachment_id.datas)

    # ==================== Workflow Actions ====================

    def action_send(self):
        """Send signature request to all signers."""
        self.ensure_one()
        if not self.signer_ids:
            raise UserError(_('Please add at least one signer before sending.'))

        for signer in self.signer_ids:
            self._send_signature_email(signer)
            signer.state = 'sent'

        self.write({
            'state': 'sent',
            'sent_date': fields.Datetime.now()
        })
        self._log_audit('send', 'Signature request sent to signers')

        return True

    def _send_signature_email(self, signer):
        """Send email with signing link to signer."""
        template = self.env.ref('loomworks_sign.mail_template_signature_request', raise_if_not_found=False)

        if template:
            signing_url = self._get_signing_url(signer)
            template.with_context(
                signing_url=signing_url,
                signer_name=signer.partner_id.name
            ).send_mail(self.id, email_values={
                'email_to': signer.email
            })

    def _get_signing_url(self, signer):
        """Generate unique signing URL for signer."""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f'{base_url}/sign/{self.access_token}/{signer.access_token}'

    def action_sign(self, signer, item_values):
        """Process signature submission from signer.

        Args:
            signer: sign.request.signer record
            item_values: dict mapping template_item_id to value dict
        """
        self.ensure_one()

        if signer.state == 'done':
            raise UserError(_('You have already signed this document.'))

        from loomworks_sign.services.pdf_service import PDFService
        pdf_service = PDFService(self.env)

        # Store item values and embed into PDF
        for item_id, value in item_values.items():
            template_item = self.env['sign.template.item'].browse(int(item_id))
            if not template_item.exists():
                continue

            # Create value record
            self.env['sign.request.item.value'].create({
                'signer_id': signer.id,
                'template_item_id': template_item.id,
                'value': value.get('text'),
                'signature_image': value.get('signature'),
            })

            # Embed into PDF
            if template_item.item_type in ('signature', 'initial'):
                signature_data = value.get('signature')
            else:
                signature_data = value.get('text')

            if signature_data:
                new_pdf = pdf_service.embed_field(
                    self.attachment_id.datas,
                    signature_data,
                    template_item
                )
                self.attachment_id.datas = new_pdf

        # Update signer status
        signer.write({
            'state': 'done',
            'signed_date': fields.Datetime.now(),
        })

        # Update request state
        if self.state == 'sent':
            self.state = 'signing'

        # Log signature
        self._log_audit(
            'sign',
            f'{signer.partner_id.name} signed the document',
            signer_id=signer.id
        )

        # Check if all signed
        if all(s.state == 'done' for s in self.signer_ids):
            self.action_complete()

        return True

    def action_complete(self):
        """Finalize the signed document."""
        self.ensure_one()

        from loomworks_sign.services.pdf_service import PDFService
        pdf_service = PDFService(self.env)

        # Finalize document (add completion metadata)
        final_pdf, doc_hash = pdf_service.finalize_document(self)

        self.signed_attachment_id = self.env['ir.attachment'].create({
            'name': f'{self.name}_signed.pdf',
            'datas': base64.b64encode(final_pdf) if isinstance(final_pdf, bytes) else final_pdf,
            'mimetype': 'application/pdf',
            'res_model': 'sign.request',
            'res_id': self.id,
        })

        self.write({
            'state': 'done',
            'completion_date': fields.Datetime.now(),
            'final_hash': doc_hash,
        })

        self._log_audit('complete', f'Document completed. Hash: {doc_hash}')

        # Send completion notification
        self._send_completion_notification()

        return True

    def _send_completion_notification(self):
        """Send completion email to all parties."""
        template = self.env.ref('loomworks_sign.mail_template_signature_complete', raise_if_not_found=False)
        if template:
            # Send to creator
            template.send_mail(self.id, email_values={
                'email_to': self.create_uid.email
            })
            # Send to all signers
            for signer in self.signer_ids:
                template.send_mail(self.id, email_values={
                    'email_to': signer.email
                })

    def action_cancel(self):
        """Cancel the signature request."""
        self.ensure_one()
        self.write({'state': 'canceled'})
        self._log_audit('cancel', 'Signature request cancelled')
        return True

    def action_resend(self, signer=None):
        """Resend signature request to pending signers."""
        self.ensure_one()
        signers = signer or self.signer_ids.filtered(lambda s: s.state in ('waiting', 'sent'))
        for s in signers:
            self._send_signature_email(s)
        return True

    def action_reset_to_draft(self):
        """Reset a cancelled request back to draft state."""
        self.ensure_one()
        self.write({'state': 'draft'})
        self._log_audit('reset', 'Signature request reset to draft')
        return True

    def action_download_document(self):
        """Download the completed signed document."""
        self.ensure_one()
        if self.signed_attachment_id:
            return {
                'type': 'ir.actions.act_url',
                'url': '/web/content/%d?download=true' % self.signed_attachment_id.id,
                'target': 'new',
            }
        return True

    # ==================== Audit Logging ====================

    def _log_audit(self, action, description, signer_id=None, ip=None, user_agent=None):
        """Create audit log entry with integrity hash."""
        self.ensure_one()

        # Get previous hash for chain integrity
        last_log = self.audit_log_ids.sorted('timestamp', reverse=True)[:1]
        previous_hash = last_log.hash_value if last_log else '0' * 64

        # Create log content for hashing
        log_content = f'{self.id}|{action}|{description}|{fields.Datetime.now()}|{previous_hash}'
        hash_value = hashlib.sha256(log_content.encode()).hexdigest()

        self.env['sign.audit.log'].create({
            'request_id': self.id,
            'signer_id': signer_id,
            'action': action,
            'description': description,
            'ip_address': ip,
            'user_agent': user_agent,
            'hash_value': hash_value,
            'previous_hash': previous_hash,
        })

    # ==================== Cron Jobs ====================

    @api.model
    def _cron_check_expiration(self):
        """Check and expire overdue requests."""
        expired = self.search([
            ('state', 'in', ['sent', 'signing']),
            ('expire_date', '<', fields.Date.today())
        ])
        for request in expired:
            request.write({'state': 'expired'})
            request._log_audit('expire', 'Request expired')

    # ==================== Action Views ====================

    def action_view_document(self):
        """View the working document."""
        self.ensure_one()
        attachment = self.signed_attachment_id or self.attachment_id
        if not attachment:
            raise UserError(_('No document available.'))

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    def action_view_audit_log(self):
        """View audit log."""
        self.ensure_one()
        return {
            'name': _('Audit Log'),
            'type': 'ir.actions.act_window',
            'res_model': 'sign.audit.log',
            'view_mode': 'tree,form',
            'domain': [('request_id', '=', self.id)],
        }
