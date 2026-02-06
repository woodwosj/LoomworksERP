# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

"""
Portal Controllers for Signature Workflows

Provides public routes for external signers to view and sign documents.
"""

import json
from loomworks import http
from loomworks.http import request


class SignPortal(http.Controller):
    """Portal controller for signature operations."""

    @http.route('/sign/<string:request_token>/<string:signer_token>',
                type='http', auth='public', website=True)
    def sign_document(self, request_token, signer_token, **kwargs):
        """Public signing page for external signers.

        Args:
            request_token: Token identifying the signature request
            signer_token: Token identifying the specific signer
        """
        sign_request = request.env['sign.request'].sudo().search([
            ('access_token', '=', request_token)
        ], limit=1)

        if not sign_request:
            return request.render('loomworks_sign.sign_invalid', {
                'error': 'Invalid or expired signature request.'
            })

        if sign_request.state in ('done', 'canceled', 'expired'):
            return request.render('loomworks_sign.sign_completed', {
                'sign_request': sign_request,
                'state': sign_request.state,
            })

        signer = sign_request.signer_ids.filtered(
            lambda s: s.access_token == signer_token
        )

        if not signer:
            return request.render('loomworks_sign.sign_invalid', {
                'error': 'Invalid signer link.'
            })

        # Mark document as viewed
        if signer.state in ('waiting', 'sent'):
            signer.mark_viewed(
                ip=request.httprequest.remote_addr,
                user_agent=request.httprequest.user_agent.string[:500] if request.httprequest.user_agent else None
            )

        # Check if already signed
        if signer.state == 'done':
            return request.render('loomworks_sign.sign_already_signed', {
                'sign_request': sign_request,
                'signer': signer,
            })

        # Get items for this signer's role
        items = sign_request.template_id.item_ids.filtered(
            lambda i: i.role_id == signer.role_id
        ).sorted('sequence')

        return request.render('loomworks_sign.sign_document', {
            'sign_request': sign_request,
            'signer': signer,
            'items': items,
            'request_token': request_token,
            'signer_token': signer_token,
        })

    @http.route('/sign/submit', type='json', auth='public')
    def submit_signature(self, request_token, signer_token, item_values):
        """Submit signature via AJAX.

        Args:
            request_token: Request access token
            signer_token: Signer access token
            item_values: Dict mapping item_id to value dict
        """
        sign_request = request.env['sign.request'].sudo().search([
            ('access_token', '=', request_token)
        ], limit=1)

        if not sign_request:
            return {'error': 'Invalid request'}

        signer = sign_request.signer_ids.filtered(
            lambda s: s.access_token == signer_token
        )

        if not signer:
            return {'error': 'Invalid signer'}

        if signer.state == 'done':
            return {'error': 'Already signed'}

        # Store IP and user agent
        signer.write({
            'signing_ip': request.httprequest.remote_addr,
            'signing_user_agent': request.httprequest.user_agent.string[:500] if request.httprequest.user_agent else None,
        })

        try:
            # Process signature
            sign_request.action_sign(signer, item_values)

            return {
                'success': True,
                'message': 'Thank you for signing!',
                'completed': sign_request.state == 'done',
            }
        except Exception as e:
            return {'error': str(e)}

    @http.route('/sign/preview/<string:request_token>/<string:signer_token>/<int:page>',
                type='http', auth='public')
    def get_page_preview(self, request_token, signer_token, page=0):
        """Get PDF page preview as image.

        Args:
            request_token: Request access token
            signer_token: Signer access token
            page: Page number (0-indexed)
        """
        sign_request = request.env['sign.request'].sudo().search([
            ('access_token', '=', request_token)
        ], limit=1)

        if not sign_request:
            return request.not_found()

        signer = sign_request.signer_ids.filtered(
            lambda s: s.access_token == signer_token
        )

        if not signer:
            return request.not_found()

        from loomworks_sign.services.pdf_service import PDFService
        pdf_service = PDFService(request.env)

        preview = pdf_service.generate_preview(
            sign_request.attachment_id.datas,
            page=page,
            dpi=150
        )

        if not preview:
            return request.not_found()

        import base64
        image_data = base64.b64decode(preview)

        return request.make_response(
            image_data,
            headers=[
                ('Content-Type', 'image/png'),
                ('Cache-Control', 'private, max-age=3600'),
            ]
        )

    @http.route('/sign/download/<string:request_token>/<string:signer_token>',
                type='http', auth='public')
    def download_signed_document(self, request_token, signer_token):
        """Download the signed document.

        Only available after completion.
        """
        sign_request = request.env['sign.request'].sudo().search([
            ('access_token', '=', request_token)
        ], limit=1)

        if not sign_request or sign_request.state != 'done':
            return request.redirect('/sign/error')

        signer = sign_request.signer_ids.filtered(
            lambda s: s.access_token == signer_token
        )

        if not signer:
            return request.not_found()

        # Log download
        sign_request._log_audit(
            'download',
            f'{signer.partner_id.name} downloaded the signed document',
            signer_id=signer.id,
            ip=request.httprequest.remote_addr
        )

        attachment = sign_request.signed_attachment_id or sign_request.attachment_id

        return request.make_response(
            attachment.raw,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', f'attachment; filename="{attachment.name}"'),
            ]
        )

    @http.route('/sign/refuse', type='json', auth='public')
    def refuse_signature(self, request_token, signer_token, reason=None):
        """Refuse to sign the document."""
        sign_request = request.env['sign.request'].sudo().search([
            ('access_token', '=', request_token)
        ], limit=1)

        if not sign_request:
            return {'error': 'Invalid request'}

        signer = sign_request.signer_ids.filtered(
            lambda s: s.access_token == signer_token
        )

        if not signer:
            return {'error': 'Invalid signer'}

        signer.action_refuse(reason)

        return {
            'success': True,
            'message': 'Your refusal has been recorded.'
        }
