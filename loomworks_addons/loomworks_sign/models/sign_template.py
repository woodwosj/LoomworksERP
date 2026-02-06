# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

import base64
import logging
from loomworks import api, fields, models, _
from loomworks.exceptions import UserError

_logger = logging.getLogger(__name__)


class SignTemplate(models.Model):
    """Signature Template

    Reusable document templates with predefined signature field positions.
    Templates store the source PDF and field configurations for creating
    signature requests.
    """
    _name = 'sign.template'
    _description = 'Signature Template'
    _order = 'name'

    name = fields.Char(
        string='Template Name',
        required=True
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )

    # Source Document
    attachment_id = fields.Many2one(
        'ir.attachment',
        string='PDF Document',
        required=True,
        help='The PDF document to use as template'
    )
    attachment_name = fields.Char(
        related='attachment_id.name',
        string='Document Name'
    )

    # Document metadata
    page_count = fields.Integer(
        string='Page Count',
        compute='_compute_page_count',
        store=True
    )

    # Template Items (signature fields)
    item_ids = fields.One2many(
        'sign.template.item',
        'template_id',
        string='Signature Fields',
        copy=True
    )
    item_count = fields.Integer(
        compute='_compute_item_count',
        string='Field Count'
    )

    # Roles used in this template
    role_ids = fields.Many2many(
        'sign.role',
        string='Roles',
        compute='_compute_role_ids',
        store=True
    )

    # Tags for organization
    tag_ids = fields.Many2many(
        'sign.template.tag',
        string='Tags'
    )

    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    # Default role
    default_role_id = fields.Many2one(
        'sign.role',
        string='Default Role',
        help='Default signer role for this template'
    )

    # Statistics
    request_count = fields.Integer(
        compute='_compute_request_count',
        string='Request Count'
    )

    # Preview
    preview_image = fields.Binary(
        string='Preview',
        compute='_compute_preview',
        attachment=False
    )

    # Document hash for integrity
    document_hash = fields.Char(
        string='Document Hash',
        compute='_compute_document_hash',
        store=True,
        help='SHA-256 hash of the source document'
    )

    @api.depends('attachment_id', 'attachment_id.datas')
    def _compute_page_count(self):
        """Count pages in the PDF document."""
        for template in self:
            if template.attachment_id and template.attachment_id.datas:
                try:
                    from loomworks_sign.services.pdf_service import PDFService
                    pdf_service = PDFService(self.env)
                    template.page_count = pdf_service.get_page_count(template.attachment_id.datas)
                except Exception as e:
                    _logger.warning("Could not count PDF pages: %s", e)
                    template.page_count = 0
            else:
                template.page_count = 0

    @api.depends('item_ids')
    def _compute_item_count(self):
        for template in self:
            template.item_count = len(template.item_ids)

    @api.depends('item_ids.role_id')
    def _compute_role_ids(self):
        for template in self:
            template.role_ids = template.item_ids.mapped('role_id')

    def _compute_request_count(self):
        """Count signature requests using this template."""
        request_data = self.env['sign.request'].read_group(
            [('template_id', 'in', self.ids)],
            ['template_id'],
            ['template_id']
        )
        result = {data['template_id'][0]: data['template_id_count'] for data in request_data}
        for template in self:
            template.request_count = result.get(template.id, 0)

    @api.depends('attachment_id', 'attachment_id.datas')
    def _compute_preview(self):
        """Generate preview image of first page."""
        for template in self:
            if template.attachment_id and template.attachment_id.datas:
                try:
                    from loomworks_sign.services.pdf_service import PDFService
                    pdf_service = PDFService(self.env)
                    template.preview_image = pdf_service.generate_preview(
                        template.attachment_id.datas, page=0, dpi=72
                    )
                except Exception as e:
                    _logger.warning("Could not generate preview: %s", e)
                    template.preview_image = False
            else:
                template.preview_image = False

    @api.depends('attachment_id', 'attachment_id.datas')
    def _compute_document_hash(self):
        """Compute SHA-256 hash of document."""
        for template in self:
            if template.attachment_id and template.attachment_id.datas:
                try:
                    from loomworks_sign.services.pdf_service import PDFService
                    pdf_service = PDFService(self.env)
                    template.document_hash = pdf_service.get_document_hash(template.attachment_id.datas)
                except Exception as e:
                    _logger.warning("Could not compute hash: %s", e)
                    template.document_hash = False
            else:
                template.document_hash = False

    def action_preview(self):
        """Preview the template document."""
        self.ensure_one()
        return {
            'name': _('Preview: %s', self.name),
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=false' % self.attachment_id.id if self.attachment_id else '#',
            'target': 'new',
        }

    def action_view_requests(self):
        """View signature requests using this template."""
        self.ensure_one()
        return {
            'name': _('Signature Requests'),
            'type': 'ir.actions.act_window',
            'res_model': 'sign.request',
            'view_mode': 'tree,form',
            'domain': [('template_id', '=', self.id)],
            'context': {'default_template_id': self.id},
        }

    def action_create_request(self):
        """Create a new signature request from this template."""
        self.ensure_one()
        return {
            'name': _('New Signature Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'sign.request',
            'view_mode': 'form',
            'context': {
                'default_template_id': self.id,
                'default_name': f"{self.name} - {fields.Date.today()}",
            },
        }

    def action_edit_template(self):
        """Open template editor to position fields."""
        self.ensure_one()
        # This would open a visual editor component
        return {
            'name': _('Edit Template'),
            'type': 'ir.actions.act_window',
            'res_model': 'sign.template',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }


class SignTemplateTag(models.Model):
    """Tags for organizing signature templates."""
    _name = 'sign.template.tag'
    _description = 'Signature Template Tag'
    _order = 'name'

    name = fields.Char(
        string='Tag Name',
        required=True
    )
    color = fields.Integer(
        string='Color Index',
        default=0
    )
