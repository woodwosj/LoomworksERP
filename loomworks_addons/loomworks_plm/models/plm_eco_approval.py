# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from loomworks import api, fields, models


class PlmEcoApproval(models.Model):
    """ECO Approval Record

    Tracks individual approval decisions from Change Control Board members.
    Each ECO may require multiple approvals before implementation.
    """
    _name = 'plm.eco.approval'
    _description = 'ECO Approval'
    _order = 'create_date desc'
    _rec_name = 'display_name'

    eco_id = fields.Many2one(
        'plm.eco',
        string='ECO',
        required=True,
        ondelete='cascade',
        index=True
    )
    user_id = fields.Many2one(
        'res.users',
        string='Approver',
        required=True,
        index=True
    )
    status = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], default='pending', string='Status', required=True, tracking=True)

    approval_date = fields.Datetime(
        string='Decision Date',
        help='Date and time when approval decision was made'
    )
    comments = fields.Text(
        string='Comments',
        help='Approval comments or rejection reason'
    )

    # Digital Signature (optional integration with loomworks_sign)
    signature = fields.Binary(
        string='Signature',
        help='Digital signature for regulatory compliance'
    )

    # Related fields for display
    eco_name = fields.Char(
        related='eco_id.name',
        string='ECO Number',
        store=True
    )
    eco_title = fields.Char(
        related='eco_id.title',
        string='ECO Title'
    )
    approver_name = fields.Char(
        related='user_id.name',
        string='Approver Name'
    )
    approver_email = fields.Char(
        related='user_id.email',
        string='Approver Email'
    )

    display_name = fields.Char(
        compute='_compute_display_name',
        store=True
    )

    @api.depends('eco_id.name', 'user_id.name', 'status')
    def _compute_display_name(self):
        for approval in self:
            approval.display_name = f"{approval.eco_id.name or 'ECO'} - {approval.user_id.name or 'User'} ({approval.status})"

    def action_approve(self):
        """Quick approve action."""
        self.ensure_one()
        self.write({
            'status': 'approved',
            'approval_date': fields.Datetime.now()
        })
        self.eco_id._check_full_approval()
        return True

    def action_reject(self):
        """Quick reject action - opens comment dialog."""
        self.ensure_one()
        return {
            'name': 'Reject ECO',
            'type': 'ir.actions.act_window',
            'res_model': 'plm.eco.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_eco_id': self.eco_id.id,
                'default_approval_id': self.id,
            },
        }

    def action_send_reminder(self):
        """Send reminder email to pending approver."""
        self.ensure_one()
        if self.status != 'pending':
            return False

        template = self.env.ref('loomworks_plm.mail_template_eco_approval_reminder', raise_if_not_found=False)
        if template:
            template.send_mail(self.id)
        return True
