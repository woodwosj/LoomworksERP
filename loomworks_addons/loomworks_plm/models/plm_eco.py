# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

import json
from loomworks import api, fields, models, _
from loomworks.exceptions import UserError, ValidationError


class PlmEco(models.Model):
    """Engineering Change Order

    Primary model for managing engineering change requests. ECOs track
    proposed changes to BOMs, components, and manufacturing processes
    through a formal approval workflow.
    """
    _name = 'plm.eco'
    _description = 'Engineering Change Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'

    name = fields.Char(
        string='ECO Number',
        required=True,
        readonly=True,
        copy=False,
        default='New',
        tracking=True
    )
    title = fields.Char(
        string='Title',
        required=True,
        tracking=True,
        help='Brief descriptive title for the change'
    )
    description = fields.Html(
        string='Description',
        help='Detailed explanation of the proposed change'
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )
    color = fields.Integer(
        string='Color Index'
    )

    # Classification
    type_id = fields.Many2one(
        'plm.eco.type',
        string='ECO Type',
        required=True,
        tracking=True,
        help='Category of change (e.g., Design Change, Supplier Change)'
    )
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Critical')
    ], default='1', string='Priority', tracking=True,
        help='Urgency level of the change request')

    reason_code = fields.Selection([
        ('cost_reduction', 'Cost Reduction'),
        ('quality_improvement', 'Quality Improvement'),
        ('regulatory_compliance', 'Regulatory Compliance'),
        ('customer_request', 'Customer Request'),
        ('supplier_change', 'Supplier Change'),
        ('design_error', 'Design Error Correction'),
        ('obsolescence', 'Component Obsolescence'),
        ('performance', 'Performance Enhancement'),
        ('other', 'Other')
    ], string='Reason Code', required=True, tracking=True,
        help='Primary reason for the change request')

    # Workflow
    stage_id = fields.Many2one(
        'plm.eco.stage',
        string='Stage',
        group_expand='_read_group_stage_ids',
        default=lambda self: self._get_default_stage(),
        tracking=True,
        index=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('approved', 'Approved'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], default='draft', string='Status', tracking=True, index=True,
        compute='_compute_state', store=True, readonly=False)

    # Dates
    request_date = fields.Date(
        string='Request Date',
        default=fields.Date.today,
        tracking=True
    )
    target_date = fields.Date(
        string='Target Implementation Date',
        tracking=True,
        help='Desired date for change implementation'
    )
    effective_date = fields.Date(
        string='Effective Date',
        help='Date when the change becomes active in production'
    )
    completion_date = fields.Date(
        string='Completion Date',
        readonly=True,
        help='Actual date when ECO was implemented'
    )

    # Stakeholders
    requester_id = fields.Many2one(
        'res.users',
        string='Requester',
        default=lambda self: self.env.user,
        tracking=True,
        help='Person who initiated the change request'
    )
    responsible_id = fields.Many2one(
        'res.users',
        string='Responsible Engineer',
        tracking=True,
        help='Engineer responsible for implementing the change'
    )
    approver_ids = fields.Many2many(
        'res.users',
        'plm_eco_approver_rel',
        'eco_id', 'user_id',
        string='Approvers (CCB)',
        help='Change Control Board members who must approve this ECO'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )

    # Affected Items
    bom_id = fields.Many2one(
        'mrp.bom',
        string='Affected BOM',
        tracking=True,
        help='Bill of Materials being modified'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Affected Product',
        related='bom_id.product_id',
        store=True,
        help='Product affected by this change'
    )
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product Template',
        related='bom_id.product_tmpl_id',
        store=True
    )
    affected_bom_line_ids = fields.Many2many(
        'mrp.bom.line',
        'plm_eco_affected_bom_line_rel',
        'eco_id', 'bom_line_id',
        string='Affected BOM Lines',
        domain="[('bom_id', '=', bom_id)]"
    )

    # Change Details
    change_line_ids = fields.One2many(
        'plm.eco.change.line',
        'eco_id',
        string='Change Lines',
        help='Specific changes to be made'
    )
    change_count = fields.Integer(
        compute='_compute_change_count',
        string='Change Count'
    )

    # Versioning
    current_bom_revision = fields.Char(
        string='Current Revision',
        compute='_compute_bom_revision',
        help='Current revision code of affected BOM'
    )
    new_bom_revision = fields.Char(
        string='New Revision',
        help='Revision code after ECO implementation'
    )
    new_bom_id = fields.Many2one(
        'mrp.bom',
        string='New BOM Version',
        readonly=True,
        help='BOM created after ECO approval and implementation'
    )

    # Approval Tracking
    approval_ids = fields.One2many(
        'plm.eco.approval',
        'eco_id',
        string='Approvals'
    )
    approval_state = fields.Selection([
        ('pending', 'Pending'),
        ('partial', 'Partially Approved'),
        ('approved', 'Fully Approved'),
        ('rejected', 'Rejected')
    ], compute='_compute_approval_state', store=True, string='Approval Status')

    approval_count = fields.Integer(
        compute='_compute_approval_count',
        string='Approval Count'
    )
    approved_count = fields.Integer(
        compute='_compute_approval_count',
        string='Approved Count'
    )

    # Impact Analysis
    impact_production = fields.Boolean(
        string='Impacts Production',
        help='Will affect ongoing or planned manufacturing orders'
    )
    impact_inventory = fields.Boolean(
        string='Impacts Inventory',
        help='Requires inventory adjustments or material disposition'
    )
    impact_cost = fields.Float(
        string='Estimated Cost Impact',
        help='Expected change in per-unit cost (positive = increase)'
    )
    impact_notes = fields.Text(
        string='Impact Analysis Notes',
        help='Detailed analysis of change impact'
    )

    # Attachments and Documents
    document_ids = fields.Many2many(
        'ir.attachment',
        'plm_eco_attachment_rel',
        'eco_id', 'attachment_id',
        string='Supporting Documents',
        help='Engineering drawings, specifications, test results, etc.'
    )
    document_count = fields.Integer(
        compute='_compute_document_count',
        string='Document Count'
    )

    # ==================== Computed Fields ====================

    @api.depends('bom_id', 'bom_id.revision_code')
    def _compute_bom_revision(self):
        """Get current revision from affected BOM."""
        for eco in self:
            eco.current_bom_revision = eco.bom_id.revision_code if eco.bom_id else False

    @api.depends('change_line_ids')
    def _compute_change_count(self):
        for eco in self:
            eco.change_count = len(eco.change_line_ids)

    @api.depends('approval_ids', 'approval_ids.status')
    def _compute_approval_state(self):
        """Determine overall approval status based on individual approvals."""
        for eco in self:
            approvals = eco.approval_ids
            if not approvals:
                eco.approval_state = 'pending'
            elif any(a.status == 'rejected' for a in approvals):
                eco.approval_state = 'rejected'
            elif all(a.status == 'approved' for a in approvals):
                eco.approval_state = 'approved'
            elif any(a.status == 'approved' for a in approvals):
                eco.approval_state = 'partial'
            else:
                eco.approval_state = 'pending'

    @api.depends('approval_ids', 'approval_ids.status')
    def _compute_approval_count(self):
        for eco in self:
            eco.approval_count = len(eco.approval_ids)
            eco.approved_count = len(eco.approval_ids.filtered(
                lambda a: a.status == 'approved'
            ))

    @api.depends('document_ids')
    def _compute_document_count(self):
        for eco in self:
            eco.document_count = len(eco.document_ids)

    @api.depends('stage_id', 'stage_id.state')
    def _compute_state(self):
        """Sync state with stage."""
        for eco in self:
            if eco.stage_id:
                eco.state = eco.stage_id.state

    # ==================== Default Values ====================

    @api.model
    def _get_default_stage(self):
        """Get default stage based on context or first stage."""
        stage = self.env['plm.eco.stage'].search([
            ('state', '=', 'draft')
        ], limit=1)
        return stage

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        """Show all stages in kanban view."""
        return stages.search([], order='sequence')

    # ==================== CRUD Methods ====================

    @api.model_create_multi
    def create(self, vals_list):
        """Generate sequence number and set defaults on create."""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('plm.eco') or 'New'

            # Set defaults from type
            if vals.get('type_id'):
                eco_type = self.env['plm.eco.type'].browse(vals['type_id'])
                if eco_type.default_responsible_id and not vals.get('responsible_id'):
                    vals['responsible_id'] = eco_type.default_responsible_id.id
                if eco_type.default_approver_ids and not vals.get('approver_ids'):
                    vals['approver_ids'] = [(6, 0, eco_type.default_approver_ids.ids)]
                if eco_type.default_stage_id and not vals.get('stage_id'):
                    vals['stage_id'] = eco_type.default_stage_id.id

        return super().create(vals_list)

    def write(self, vals):
        """Handle stage changes and notifications."""
        res = super().write(vals)

        # Send notification on stage change
        if 'stage_id' in vals:
            for eco in self:
                if eco.stage_id.mail_template_id:
                    eco.stage_id.mail_template_id.send_mail(eco.id)

        return res

    # ==================== Workflow Actions ====================

    def action_confirm(self):
        """Move ECO from draft to confirmed, request approvals."""
        self.ensure_one()
        if not self.change_line_ids:
            raise UserError(_('Please add at least one change line before confirming.'))

        # Find confirmed stage
        stage = self._get_stage_by_state('confirmed')
        if not stage:
            raise UserError(_('No stage found for confirmed state.'))

        self.write({
            'stage_id': stage.id,
        })
        self._request_approvals()

        return True

    def action_start_review(self):
        """Begin the review/approval process."""
        self.ensure_one()
        stage = self._get_stage_by_state('in_progress')
        if stage:
            self.write({'stage_id': stage.id})
        return True

    def action_approve(self):
        """Record current user's approval."""
        self.ensure_one()
        approval = self.approval_ids.filtered(
            lambda a: a.user_id == self.env.user and a.status == 'pending'
        )
        if not approval:
            raise UserError(_('You are not an approver for this ECO or have already voted.'))

        approval.write({
            'status': 'approved',
            'approval_date': fields.Datetime.now()
        })

        self.message_post(
            body=_('%s approved this ECO.') % self.env.user.name,
            message_type='notification'
        )

        self._check_full_approval()
        return True

    def action_reject(self):
        """Open wizard to reject with reason."""
        self.ensure_one()
        return {
            'name': _('Reject ECO'),
            'type': 'ir.actions.act_window',
            'res_model': 'plm.eco.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_eco_id': self.id},
        }

    def action_do_reject(self, reason=None):
        """Reject the ECO with a reason."""
        self.ensure_one()
        approval = self.approval_ids.filtered(
            lambda a: a.user_id == self.env.user and a.status == 'pending'
        )
        if approval:
            approval.write({
                'status': 'rejected',
                'approval_date': fields.Datetime.now(),
                'comments': reason
            })

        stage = self._get_stage_by_state('cancelled')
        if stage:
            self.write({'stage_id': stage.id})

        self.message_post(
            body=_('%s rejected this ECO. Reason: %s') % (self.env.user.name, reason or 'Not specified'),
            message_type='notification'
        )
        return True

    def action_implement(self):
        """Implement the approved ECO - create new BOM revision."""
        self.ensure_one()
        if self.approval_state != 'approved':
            raise UserError(_('ECO must be fully approved before implementation.'))

        new_bom = self._create_new_bom_version()

        stage = self._get_stage_by_state('done')
        self.write({
            'stage_id': stage.id if stage else False,
            'new_bom_id': new_bom.id if new_bom else False,
            'completion_date': fields.Date.today(),
            'effective_date': self.effective_date or fields.Date.today()
        })

        self.message_post(
            body=_('ECO implemented. New BOM revision %s created.') % (new_bom.revision_code if new_bom else 'N/A'),
            message_type='notification'
        )

        return new_bom

    def action_cancel(self):
        """Cancel the ECO."""
        self.ensure_one()
        stage = self._get_stage_by_state('cancelled')
        if stage:
            self.write({'stage_id': stage.id})
        return True

    def action_reset_draft(self):
        """Reset ECO back to draft state."""
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_('Cannot reset a completed ECO.'))

        stage = self._get_stage_by_state('draft')
        if stage:
            self.write({'stage_id': stage.id})

        # Clear approvals
        self.approval_ids.unlink()
        return True

    # ==================== Helper Methods ====================

    def _get_stage_by_state(self, state):
        """Find stage matching given state."""
        return self.env['plm.eco.stage'].search([
            ('state', '=', state)
        ], limit=1)

    def _request_approvals(self):
        """Create approval records for all CCB members."""
        for user in self.approver_ids:
            existing = self.approval_ids.filtered(lambda a: a.user_id == user)
            if not existing:
                self.env['plm.eco.approval'].create({
                    'eco_id': self.id,
                    'user_id': user.id,
                    'status': 'pending'
                })

        # Create activities for approvers
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if activity_type:
            for user in self.approver_ids:
                self.activity_schedule(
                    activity_type_id=activity_type.id,
                    user_id=user.id,
                    summary=_('ECO Approval Required'),
                    note=_('Please review and approve/reject ECO %s: %s') % (self.name, self.title)
                )

        # Send notification emails
        template = self.env.ref('loomworks_plm.mail_template_eco_approval_request', raise_if_not_found=False)
        if template:
            for approval in self.approval_ids.filtered(lambda a: a.status == 'pending'):
                template.send_mail(approval.id)

    def _check_full_approval(self):
        """Check if all required approvals are received."""
        if self.approval_state == 'approved':
            stage = self._get_stage_by_state('approved')
            if stage:
                self.write({'stage_id': stage.id})

            # Mark activities as done
            self.activity_ids.filtered(
                lambda a: 'ECO Approval' in (a.summary or '')
            ).action_done()

    def _create_new_bom_version(self):
        """Create new BOM version based on ECO changes."""
        self.ensure_one()
        if not self.bom_id:
            return False

        old_bom = self.bom_id

        # Create snapshot of old BOM
        self.env['plm.bom.revision'].create({
            'bom_id': old_bom.id,
            'revision_code': old_bom.revision_code or 'A',
            'eco_id': self.id,
            'snapshot_data': self._serialize_bom(old_bom),
            'notes': _('Revision before ECO %s') % self.name
        })

        # Copy BOM and apply changes
        new_revision_code = self.new_bom_revision or self._get_next_revision(old_bom.revision_code or 'A')
        new_bom = old_bom.copy({
            'revision_code': new_revision_code,
            'previous_bom_id': old_bom.id,
            'lifecycle_state': 'released',
            'is_current_revision': True,
        })

        # Mark old BOM as not current
        old_bom.write({
            'lifecycle_state': 'obsolete',
            'is_current_revision': False,
        })

        # Apply change lines
        for change in self.change_line_ids:
            self._apply_change_to_bom(new_bom, change)

        return new_bom

    def _apply_change_to_bom(self, bom, change_line):
        """Apply a single change line to the BOM."""
        BomLine = self.env['mrp.bom.line']

        if change_line.change_type == 'add':
            BomLine.create({
                'bom_id': bom.id,
                'product_id': change_line.new_component_id.id,
                'product_qty': change_line.new_quantity or 1.0,
            })
        elif change_line.change_type == 'remove':
            lines = bom.bom_line_ids.filtered(
                lambda l: l.product_id == change_line.old_component_id
            )
            lines.unlink()
        elif change_line.change_type == 'replace':
            lines = bom.bom_line_ids.filtered(
                lambda l: l.product_id == change_line.old_component_id
            )
            lines.write({
                'product_id': change_line.new_component_id.id,
                'product_qty': change_line.new_quantity or lines[:1].product_qty
            })
        elif change_line.change_type == 'modify_qty':
            lines = bom.bom_line_ids.filtered(
                lambda l: l.product_id == change_line.old_component_id
            )
            lines.write({'product_qty': change_line.new_quantity})

    def _serialize_bom(self, bom):
        """Serialize BOM structure to JSON for snapshot."""
        data = {
            'id': bom.id,
            'code': bom.code,
            'product_tmpl_id': bom.product_tmpl_id.id,
            'product_id': bom.product_id.id if bom.product_id else False,
            'product_qty': bom.product_qty,
            'revision_code': bom.revision_code,
            'lines': []
        }
        for line in bom.bom_line_ids:
            data['lines'].append({
                'product_id': line.product_id.id,
                'product_name': line.product_id.name,
                'product_qty': line.product_qty,
                'product_uom_id': line.product_uom_id.id,
            })
        return json.dumps(data)

    def _get_next_revision(self, current):
        """Generate next revision code (A->B->C or 1.0->1.1->2.0)."""
        if not current:
            return 'A'
        if current.isalpha() and len(current) == 1:
            # Letter-based: A -> B -> ... -> Z -> AA
            if current == 'Z':
                return 'AA'
            return chr(ord(current) + 1)
        elif '.' in current:
            # Semantic versioning: 1.0 -> 1.1
            parts = current.split('.')
            parts[-1] = str(int(parts[-1]) + 1)
            return '.'.join(parts)
        return current + '.1'

    # ==================== Action Views ====================

    def action_view_approvals(self):
        """View approval records."""
        self.ensure_one()
        return {
            'name': _('Approvals'),
            'type': 'ir.actions.act_window',
            'res_model': 'plm.eco.approval',
            'view_mode': 'tree,form',
            'domain': [('eco_id', '=', self.id)],
            'context': {'default_eco_id': self.id},
        }

    def action_view_documents(self):
        """View attached documents."""
        self.ensure_one()
        return {
            'name': _('Documents'),
            'type': 'ir.actions.act_window',
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,tree,form',
            'domain': [('id', 'in', self.document_ids.ids)],
        }

    def action_view_new_bom(self):
        """View the new BOM created from this ECO."""
        self.ensure_one()
        if not self.new_bom_id:
            raise UserError(_('No new BOM has been created for this ECO yet.'))
        return {
            'name': _('New BOM'),
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.bom',
            'view_mode': 'form',
            'res_id': self.new_bom_id.id,
        }

    def action_compare_bom(self):
        """Compare current and new BOM versions."""
        self.ensure_one()
        if not self.bom_id:
            raise UserError(_('No BOM assigned to this ECO.'))
        return {
            'name': _('BOM Comparison'),
            'type': 'ir.actions.act_window',
            'res_model': 'plm.bom.compare.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_bom_id': self.bom_id.id,
                'default_compare_bom_id': self.new_bom_id.id if self.new_bom_id else False,
            },
        }
