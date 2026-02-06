# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

"""
Sign AI Tool Provider - Provides AI tools for electronic signature workflows.
"""

from loomworks import api, models, _
import logging

_logger = logging.getLogger(__name__)


class SignToolProvider(models.AbstractModel):
    """AI Tool Provider for Sign operations."""
    _name = 'sign.tool.provider'
    _inherit = 'loomworks.ai.tool.provider'
    _description = 'Sign AI Tool Provider'

    @api.model
    def _get_tool_definitions(self):
        """Return Sign tool definitions for AI."""
        return [
            {
                'name': 'Send Signature Request',
                'technical_name': 'sign_send_request',
                'category': 'action',
                'description': '''Send a document for electronic signature.

Use this tool when:
- User wants to send a document for signing
- User needs to collect signatures from customers or partners
- User wants to create a signature request from a template

Required information:
- Template name or reference
- Signer details (email, name)
- Optional custom message''',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'template_name': {
                            'type': 'string',
                            'description': 'Name of the signature template to use'
                        },
                        'signers': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'properties': {
                                    'email': {'type': 'string'},
                                    'name': {'type': 'string'},
                                    'role': {'type': 'string'}
                                },
                                'required': ['email', 'name']
                            },
                            'description': 'List of signers with email and name'
                        },
                        'subject': {
                            'type': 'string',
                            'description': 'Email subject line'
                        },
                        'message': {
                            'type': 'string',
                            'description': 'Custom message to include in email'
                        },
                        'expire_days': {
                            'type': 'integer',
                            'description': 'Number of days until request expires'
                        }
                    },
                    'required': ['template_name', 'signers']
                },
                'implementation_method': 'sign.tool.provider._execute_send_request',
                'risk_level': 'moderate',
                'requires_confirmation': True,
                'returns_description': 'Returns the created signature request details and signing links',
                'sequence': 10,
            },
            {
                'name': 'Get Signature Status',
                'technical_name': 'sign_get_status',
                'category': 'data',
                'description': '''Check the status of a signature request.

Use this tool when:
- User asks about signature request status
- User wants to know who has signed
- User needs signing progress update''',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'request_reference': {
                            'type': 'string',
                            'description': 'Signature request reference number or name'
                        }
                    },
                    'required': ['request_reference']
                },
                'implementation_method': 'sign.tool.provider._execute_get_status',
                'risk_level': 'safe',
                'requires_confirmation': False,
                'returns_description': 'Request status and signer details',
                'sequence': 20,
            },
            {
                'name': 'List Signature Templates',
                'technical_name': 'sign_list_templates',
                'category': 'data',
                'description': '''List available signature templates.

Use this tool when:
- User wants to see what templates are available
- User asks about document templates
- Before sending a request to help user choose template''',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'search': {
                            'type': 'string',
                            'description': 'Optional search term'
                        }
                    },
                    'required': []
                },
                'implementation_method': 'sign.tool.provider._execute_list_templates',
                'risk_level': 'safe',
                'requires_confirmation': False,
                'returns_description': 'List of available templates',
                'sequence': 30,
            },
            {
                'name': 'List Pending Signature Requests',
                'technical_name': 'sign_list_pending',
                'category': 'data',
                'description': '''List signature requests awaiting completion.

Use this tool when:
- User asks about pending signatures
- User wants to see outstanding requests
- User needs to follow up on signatures''',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'filter': {
                            'type': 'string',
                            'enum': ['all', 'my_requests', 'to_sign'],
                            'description': 'Filter pending requests'
                        }
                    },
                    'required': []
                },
                'implementation_method': 'sign.tool.provider._execute_list_pending',
                'risk_level': 'safe',
                'requires_confirmation': False,
                'returns_description': 'List of pending signature requests',
                'sequence': 40,
            },
            {
                'name': 'Resend Signature Request',
                'technical_name': 'sign_resend',
                'category': 'action',
                'description': '''Resend a signature request email to pending signers.

Use this tool when:
- User wants to remind signers
- Signer did not receive original email
- User asks to resend signature request''',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'request_reference': {
                            'type': 'string',
                            'description': 'Signature request reference'
                        },
                        'signer_email': {
                            'type': 'string',
                            'description': 'Optional specific signer email to resend to'
                        }
                    },
                    'required': ['request_reference']
                },
                'implementation_method': 'sign.tool.provider._execute_resend',
                'risk_level': 'safe',
                'requires_confirmation': True,
                'returns_description': 'Confirmation of resend',
                'sequence': 50,
            },
        ]

    # ==================== Tool Implementations ====================

    @api.model
    def _execute_send_request(self, params):
        """Create and send a signature request."""
        template_name = params.get('template_name')
        signers_data = params.get('signers', [])
        subject = params.get('subject', 'Signature Request')
        message = params.get('message', '')
        expire_days = params.get('expire_days', 30)

        # Find template
        Template = self.env['sign.template']
        template = Template.search([
            '|',
            ('name', 'ilike', template_name),
            ('id', '=', int(template_name) if template_name.isdigit() else 0)
        ], limit=1)

        if not template:
            return {
                'success': False,
                'error': f"Could not find signature template '{template_name}'"
            }

        # Find or create partners for signers
        Partner = self.env['res.partner']
        Role = self.env['sign.role']
        signer_vals = []

        for signer_data in signers_data:
            email = signer_data.get('email')
            name = signer_data.get('name', email)
            role_name = signer_data.get('role')

            # Find or create partner
            partner = Partner.search([('email', '=', email)], limit=1)
            if not partner:
                partner = Partner.create({
                    'name': name,
                    'email': email,
                })

            # Find role
            role = None
            if role_name:
                role = Role.search([('name', 'ilike', role_name)], limit=1)
            if not role:
                role = Role.get_default_role()

            signer_vals.append((0, 0, {
                'partner_id': partner.id,
                'role_id': role.id,
            }))

        # Create request
        from datetime import timedelta
        from loomworks import fields
        expire_date = fields.Date.today() + timedelta(days=expire_days) if expire_days else False

        request = self.env['sign.request'].create({
            'template_id': template.id,
            'subject': subject,
            'message': message,
            'expire_date': expire_date,
            'signer_ids': signer_vals,
        })

        # Send the request
        request.action_send()

        return {
            'success': True,
            'request_id': request.id,
            'request_reference': request.name,
            'template': template.name,
            'signers': [{'name': s.partner_id.name, 'email': s.email} for s in request.signer_ids],
            'message': f"Signature request {request.name} sent successfully to {len(request.signer_ids)} signer(s)"
        }

    @api.model
    def _execute_get_status(self, params):
        """Get signature request status."""
        ref = params.get('request_reference')

        Request = self.env['sign.request']
        request = Request.search([
            '|',
            ('name', 'ilike', ref),
            ('id', '=', int(ref) if ref.isdigit() else 0)
        ], limit=1)

        if not request:
            return {
                'success': False,
                'error': f"Could not find signature request '{ref}'"
            }

        signers = []
        for signer in request.signer_ids:
            signers.append({
                'name': signer.partner_id.name,
                'email': signer.email,
                'role': signer.role_id.name,
                'state': signer.state,
                'signed_date': str(signer.signed_date) if signer.signed_date else None,
            })

        return {
            'success': True,
            'request_reference': request.name,
            'template': request.template_id.name,
            'state': request.state,
            'progress': f"{request.completed_count}/{request.signer_count}",
            'progress_percentage': request.progress_percentage,
            'sent_date': str(request.sent_date) if request.sent_date else None,
            'completion_date': str(request.completion_date) if request.completion_date else None,
            'expire_date': str(request.expire_date) if request.expire_date else None,
            'signers': signers,
        }

    @api.model
    def _execute_list_templates(self, params):
        """List available templates."""
        search_term = params.get('search', '')

        domain = [('active', '=', True)]
        if search_term:
            domain.append(('name', 'ilike', search_term))

        templates = self.env['sign.template'].search(domain, limit=20)

        results = []
        for template in templates:
            results.append({
                'id': template.id,
                'name': template.name,
                'pages': template.page_count,
                'fields': template.item_count,
                'roles': template.role_ids.mapped('name'),
                'request_count': template.request_count,
            })

        return {
            'success': True,
            'count': len(results),
            'templates': results,
        }

    @api.model
    def _execute_list_pending(self, params):
        """List pending signature requests."""
        filter_type = params.get('filter', 'all')

        domain = [('state', 'in', ['sent', 'signing'])]

        if filter_type == 'my_requests':
            domain.append(('create_uid', '=', self.env.user.id))

        requests = self.env['sign.request'].search(domain, order='create_date desc', limit=20)

        results = []
        for request in requests:
            results.append({
                'reference': request.name,
                'template': request.template_id.name,
                'state': request.state,
                'progress': f"{request.completed_count}/{request.signer_count}",
                'sent_date': str(request.sent_date) if request.sent_date else None,
                'pending_signers': request.signer_ids.filtered(
                    lambda s: s.state not in ('done', 'refused')
                ).mapped('partner_id.name'),
            })

        return {
            'success': True,
            'count': len(results),
            'requests': results,
        }

    @api.model
    def _execute_resend(self, params):
        """Resend signature request."""
        ref = params.get('request_reference')
        signer_email = params.get('signer_email')

        Request = self.env['sign.request']
        request = Request.search([
            '|',
            ('name', 'ilike', ref),
            ('id', '=', int(ref) if ref.isdigit() else 0)
        ], limit=1)

        if not request:
            return {
                'success': False,
                'error': f"Could not find signature request '{ref}'"
            }

        if request.state not in ('sent', 'signing'):
            return {
                'success': False,
                'error': f"Cannot resend request in state '{request.state}'"
            }

        # Find specific signer or all pending
        if signer_email:
            signers = request.signer_ids.filtered(
                lambda s: s.email == signer_email and s.state in ('waiting', 'sent', 'viewed')
            )
        else:
            signers = request.signer_ids.filtered(
                lambda s: s.state in ('waiting', 'sent', 'viewed')
            )

        if not signers:
            return {
                'success': False,
                'error': "No pending signers to resend to"
            }

        request.action_resend(signers)

        return {
            'success': True,
            'message': f"Resent signature request to {len(signers)} signer(s)",
            'signers_notified': signers.mapped('partner_id.name'),
        }
