# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

"""
PLM AI Tool Provider - Provides AI tools for Engineering Change Order management.

This implements the M4 resolution pattern, allowing AI agents to interact with
PLM functionality through natural language.
"""

from loomworks import api, models, _
import logging

_logger = logging.getLogger(__name__)


class PlmToolProvider(models.AbstractModel):
    """AI Tool Provider for PLM operations.

    Provides tools for:
    - Creating Engineering Change Orders
    - Approving/rejecting ECOs
    - Comparing BOM revisions
    - Checking ECO status
    """
    _name = 'plm.tool.provider'
    _inherit = 'loomworks.ai.tool.provider'
    _description = 'PLM AI Tool Provider'

    @api.model
    def _get_tool_definitions(self):
        """Return PLM tool definitions for AI."""
        return [
            {
                'name': 'Create Engineering Change Order',
                'technical_name': 'plm_create_eco',
                'category': 'action',
                'description': '''Create a new Engineering Change Order (ECO) to request changes to a Bill of Materials.

Use this tool when:
- User wants to propose changes to a product's BOM
- User needs to add, remove, or replace components
- User wants to modify component quantities
- User needs to initiate a formal change request process

Required information:
- Title of the change
- BOM to modify (product name or BOM reference)
- Reason for change
- Description of changes

The tool will create the ECO in draft state, ready for the user to add change lines and submit for approval.''',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'title': {
                            'type': 'string',
                            'description': 'Brief title describing the change'
                        },
                        'bom_reference': {
                            'type': 'string',
                            'description': 'Product name or BOM reference to modify'
                        },
                        'reason_code': {
                            'type': 'string',
                            'enum': ['cost_reduction', 'quality_improvement', 'regulatory_compliance',
                                    'customer_request', 'supplier_change', 'design_error',
                                    'obsolescence', 'performance', 'other'],
                            'description': 'Primary reason for the change'
                        },
                        'description': {
                            'type': 'string',
                            'description': 'Detailed description of proposed changes'
                        },
                        'priority': {
                            'type': 'string',
                            'enum': ['0', '1', '2', '3'],
                            'description': 'Priority: 0=Low, 1=Normal, 2=High, 3=Critical',
                            'default': '1'
                        },
                        'eco_type': {
                            'type': 'string',
                            'description': 'Type of ECO (e.g., Design Change, Supplier Change)'
                        }
                    },
                    'required': ['title', 'bom_reference', 'reason_code']
                },
                'implementation_method': 'plm.tool.provider._execute_create_eco',
                'risk_level': 'moderate',
                'requires_confirmation': True,
                'returns_description': 'Returns the created ECO details including reference number and link',
                'sequence': 10,
            },
            {
                'name': 'Approve ECO',
                'technical_name': 'plm_approve_eco',
                'category': 'action',
                'description': '''Approve an Engineering Change Order on behalf of the current user.

Use this tool when:
- User wants to approve a pending ECO
- User confirms they agree with proposed changes

The user must be an assigned approver for the ECO.''',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'eco_reference': {
                            'type': 'string',
                            'description': 'ECO reference number (e.g., ECO/2024/0001) or title'
                        },
                        'comments': {
                            'type': 'string',
                            'description': 'Optional approval comments'
                        }
                    },
                    'required': ['eco_reference']
                },
                'implementation_method': 'plm.tool.provider._execute_approve_eco',
                'risk_level': 'moderate',
                'requires_confirmation': True,
                'returns_description': 'Confirmation of approval and current ECO status',
                'sequence': 20,
            },
            {
                'name': 'Reject ECO',
                'technical_name': 'plm_reject_eco',
                'category': 'action',
                'description': '''Reject an Engineering Change Order on behalf of the current user.

Use this tool when:
- User wants to reject a pending ECO
- User has concerns with proposed changes

A reason for rejection should be provided.''',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'eco_reference': {
                            'type': 'string',
                            'description': 'ECO reference number or title'
                        },
                        'reason': {
                            'type': 'string',
                            'description': 'Reason for rejection'
                        }
                    },
                    'required': ['eco_reference', 'reason']
                },
                'implementation_method': 'plm.tool.provider._execute_reject_eco',
                'risk_level': 'moderate',
                'requires_confirmation': True,
                'returns_description': 'Confirmation of rejection',
                'sequence': 25,
            },
            {
                'name': 'Compare BOM Revisions',
                'technical_name': 'plm_compare_bom',
                'category': 'data',
                'description': '''Compare two BOM revisions and show differences.

Use this tool when:
- User wants to see what changed between BOM versions
- User wants to review impact of an ECO
- User needs to understand component differences

Returns added, removed, and modified components.''',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'product_reference': {
                            'type': 'string',
                            'description': 'Product name or reference'
                        },
                        'revision_1': {
                            'type': 'string',
                            'description': 'First revision code (e.g., A, B, 1.0)'
                        },
                        'revision_2': {
                            'type': 'string',
                            'description': 'Second revision code to compare against'
                        }
                    },
                    'required': ['product_reference']
                },
                'implementation_method': 'plm.tool.provider._execute_compare_bom',
                'risk_level': 'safe',
                'requires_confirmation': False,
                'returns_description': 'List of differences between BOM revisions',
                'sequence': 30,
            },
            {
                'name': 'Get ECO Status',
                'technical_name': 'plm_get_eco_status',
                'category': 'data',
                'description': '''Get the current status of an Engineering Change Order.

Use this tool when:
- User wants to check approval progress
- User asks about ECO status
- User wants to see pending actions

Returns ECO details including approval status.''',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'eco_reference': {
                            'type': 'string',
                            'description': 'ECO reference number or title'
                        }
                    },
                    'required': ['eco_reference']
                },
                'implementation_method': 'plm.tool.provider._execute_get_eco_status',
                'risk_level': 'safe',
                'requires_confirmation': False,
                'returns_description': 'ECO details and approval status',
                'sequence': 40,
            },
            {
                'name': 'List Pending ECOs',
                'technical_name': 'plm_list_pending_ecos',
                'category': 'data',
                'description': '''List ECOs awaiting action from the current user.

Use this tool when:
- User asks what ECOs need their attention
- User wants to see pending approvals
- User asks about their ECO workload''',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'status_filter': {
                            'type': 'string',
                            'enum': ['all', 'pending_approval', 'my_requests'],
                            'description': 'Filter ECOs by status',
                            'default': 'all'
                        }
                    },
                    'required': []
                },
                'implementation_method': 'plm.tool.provider._execute_list_pending_ecos',
                'risk_level': 'safe',
                'requires_confirmation': False,
                'returns_description': 'List of ECOs requiring attention',
                'sequence': 50,
            },
        ]

    # ==================== Tool Implementations ====================

    @api.model
    def _execute_create_eco(self, params):
        """Create a new ECO."""
        title = params.get('title')
        bom_reference = params.get('bom_reference')
        reason_code = params.get('reason_code', 'other')
        description = params.get('description', '')
        priority = params.get('priority', '1')
        eco_type_name = params.get('eco_type')

        # Find BOM
        Bom = self.env['mrp.bom']
        bom = Bom.search([
            '|',
            ('code', 'ilike', bom_reference),
            ('product_tmpl_id.name', 'ilike', bom_reference)
        ], limit=1)

        if not bom:
            return {
                'success': False,
                'error': f"Could not find BOM matching '{bom_reference}'. Please verify the product name or BOM reference."
            }

        # Find ECO type
        EcoType = self.env['plm.eco.type']
        eco_type = None
        if eco_type_name:
            eco_type = EcoType.search([('name', 'ilike', eco_type_name)], limit=1)
        if not eco_type:
            eco_type = EcoType.search([], limit=1)

        if not eco_type:
            return {
                'success': False,
                'error': "No ECO types configured. Please contact administrator."
            }

        # Create ECO
        eco = self.env['plm.eco'].create({
            'title': title,
            'bom_id': bom.id,
            'type_id': eco_type.id,
            'reason_code': reason_code,
            'description': description,
            'priority': priority,
        })

        return {
            'success': True,
            'eco_id': eco.id,
            'eco_reference': eco.name,
            'eco_title': eco.title,
            'bom_name': bom.product_tmpl_id.name,
            'current_revision': bom.revision_code,
            'message': f"Created ECO {eco.name}: {eco.title} for {bom.product_tmpl_id.name}. Add change lines and submit for approval."
        }

    @api.model
    def _execute_approve_eco(self, params):
        """Approve an ECO."""
        eco_ref = params.get('eco_reference')
        comments = params.get('comments', '')

        # Find ECO
        Eco = self.env['plm.eco']
        eco = Eco.search([
            '|',
            ('name', 'ilike', eco_ref),
            ('title', 'ilike', eco_ref)
        ], limit=1)

        if not eco:
            return {
                'success': False,
                'error': f"Could not find ECO matching '{eco_ref}'."
            }

        # Check if user can approve
        approval = eco.approval_ids.filtered(
            lambda a: a.user_id == self.env.user and a.status == 'pending'
        )

        if not approval:
            return {
                'success': False,
                'error': f"You are not a pending approver for ECO {eco.name}."
            }

        # Approve
        approval.write({
            'status': 'approved',
            'approval_date': self.env.cr.now(),
            'comments': comments,
        })
        eco._check_full_approval()

        return {
            'success': True,
            'eco_reference': eco.name,
            'eco_title': eco.title,
            'approval_state': eco.approval_state,
            'approved_count': eco.approved_count,
            'total_approvers': eco.approval_count,
            'message': f"Approved ECO {eco.name}. Status: {eco.approval_state} ({eco.approved_count}/{eco.approval_count} approvals)"
        }

    @api.model
    def _execute_reject_eco(self, params):
        """Reject an ECO."""
        eco_ref = params.get('eco_reference')
        reason = params.get('reason', 'No reason provided')

        # Find ECO
        Eco = self.env['plm.eco']
        eco = Eco.search([
            '|',
            ('name', 'ilike', eco_ref),
            ('title', 'ilike', eco_ref)
        ], limit=1)

        if not eco:
            return {
                'success': False,
                'error': f"Could not find ECO matching '{eco_ref}'."
            }

        eco.action_do_reject(reason)

        return {
            'success': True,
            'eco_reference': eco.name,
            'message': f"Rejected ECO {eco.name}. Reason: {reason}"
        }

    @api.model
    def _execute_compare_bom(self, params):
        """Compare BOM revisions."""
        product_ref = params.get('product_reference')
        rev1 = params.get('revision_1')
        rev2 = params.get('revision_2')

        # Find BOMs
        Bom = self.env['mrp.bom']
        base_domain = [
            '|',
            ('code', 'ilike', product_ref),
            ('product_tmpl_id.name', 'ilike', product_ref)
        ]

        if rev1 and rev2:
            bom1 = Bom.search(base_domain + [('revision_code', '=', rev1)], limit=1)
            bom2 = Bom.search(base_domain + [('revision_code', '=', rev2)], limit=1)
        else:
            # Compare current vs previous
            bom1 = Bom.search(base_domain + [('is_current_revision', '=', True)], limit=1)
            bom2 = bom1.previous_bom_id if bom1 else False

        if not bom1:
            return {
                'success': False,
                'error': f"Could not find BOM for '{product_ref}'"
            }

        if not bom2:
            return {
                'success': True,
                'message': f"Only one revision exists for {bom1.product_tmpl_id.name}",
                'current_revision': bom1.revision_code,
                'components': [
                    {'name': line.product_id.name, 'qty': line.product_qty}
                    for line in bom1.bom_line_ids
                ]
            }

        diff = bom1.get_bom_diff(bom2)

        return {
            'success': True,
            'product': bom1.product_tmpl_id.name,
            'revision_1': bom1.revision_code,
            'revision_2': bom2.revision_code,
            'added': diff['added'],
            'removed': diff['removed'],
            'modified': diff['modified'],
            'summary': f"Comparing {bom1.revision_code} vs {bom2.revision_code}: {len(diff['added'])} added, {len(diff['removed'])} removed, {len(diff['modified'])} modified"
        }

    @api.model
    def _execute_get_eco_status(self, params):
        """Get ECO status."""
        eco_ref = params.get('eco_reference')

        Eco = self.env['plm.eco']
        eco = Eco.search([
            '|',
            ('name', 'ilike', eco_ref),
            ('title', 'ilike', eco_ref)
        ], limit=1)

        if not eco:
            return {
                'success': False,
                'error': f"Could not find ECO matching '{eco_ref}'."
            }

        approvals = []
        for approval in eco.approval_ids:
            approvals.append({
                'approver': approval.user_id.name,
                'status': approval.status,
                'date': str(approval.approval_date) if approval.approval_date else None,
                'comments': approval.comments,
            })

        return {
            'success': True,
            'eco_reference': eco.name,
            'title': eco.title,
            'state': eco.state,
            'stage': eco.stage_id.name,
            'approval_state': eco.approval_state,
            'requester': eco.requester_id.name,
            'responsible': eco.responsible_id.name if eco.responsible_id else None,
            'bom': eco.bom_id.product_tmpl_id.name if eco.bom_id else None,
            'current_revision': eco.current_bom_revision,
            'new_revision': eco.new_bom_revision,
            'approvals': approvals,
            'change_count': eco.change_count,
        }

    @api.model
    def _execute_list_pending_ecos(self, params):
        """List pending ECOs for current user."""
        status_filter = params.get('status_filter', 'all')

        domain = [('state', 'not in', ['done', 'cancelled'])]

        if status_filter == 'pending_approval':
            # ECOs where user has pending approval
            pending_approvals = self.env['plm.eco.approval'].search([
                ('user_id', '=', self.env.user.id),
                ('status', '=', 'pending')
            ])
            domain.append(('id', 'in', pending_approvals.mapped('eco_id').ids))
        elif status_filter == 'my_requests':
            domain.append(('requester_id', '=', self.env.user.id))

        ecos = self.env['plm.eco'].search(domain, order='create_date desc', limit=20)

        results = []
        for eco in ecos:
            results.append({
                'reference': eco.name,
                'title': eco.title,
                'state': eco.state,
                'approval_state': eco.approval_state,
                'bom': eco.bom_id.product_tmpl_id.name if eco.bom_id else None,
                'requester': eco.requester_id.name,
                'priority': dict(eco._fields['priority'].selection).get(eco.priority),
            })

        return {
            'success': True,
            'count': len(results),
            'ecos': results,
        }
