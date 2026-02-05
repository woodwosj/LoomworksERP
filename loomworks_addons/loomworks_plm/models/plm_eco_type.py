# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PlmEcoType(models.Model):
    """ECO Type Configuration

    Defines categories of Engineering Change Orders with their approval
    requirements and workflow configurations.
    """
    _name = 'plm.eco.type'
    _description = 'ECO Type'
    _order = 'sequence, name'

    name = fields.Char(
        string='Name',
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
    description = fields.Text(
        string='Description',
        translate=True,
        help='Detailed description of when to use this ECO type'
    )
    color = fields.Integer(
        string='Color Index',
        default=0
    )

    # Workflow Configuration
    stage_ids = fields.Many2many(
        'plm.eco.stage',
        'plm_eco_type_stage_rel',
        'type_id', 'stage_id',
        string='Available Stages',
        help='Stages available for ECOs of this type'
    )
    default_stage_id = fields.Many2one(
        'plm.eco.stage',
        string='Default Stage',
        domain="[('id', 'in', stage_ids)]",
        help='Initial stage for new ECOs of this type'
    )

    # Approval Configuration
    require_approval = fields.Boolean(
        string='Requires Approval',
        default=True,
        help='ECOs of this type require approval before implementation'
    )
    min_approvers = fields.Integer(
        string='Minimum Approvers',
        default=1,
        help='Minimum number of approvals needed before ECO can proceed'
    )
    auto_approve_user_ids = fields.Many2many(
        'res.users',
        'plm_eco_type_auto_approver_rel',
        'type_id', 'user_id',
        string='Auto-Approvers',
        help='Users who can single-handedly approve ECOs of this type'
    )

    # Default Settings
    default_responsible_id = fields.Many2one(
        'res.users',
        string='Default Responsible',
        help='Default responsible engineer for ECOs of this type'
    )
    default_approver_ids = fields.Many2many(
        'res.users',
        'plm_eco_type_default_approver_rel',
        'type_id', 'user_id',
        string='Default Approvers',
        help='Default CCB members for ECOs of this type'
    )

    # Statistics
    eco_count = fields.Integer(
        compute='_compute_eco_count',
        string='ECO Count'
    )

    def _compute_eco_count(self):
        """Count ECOs by type."""
        eco_data = self.env['plm.eco'].read_group(
            [('type_id', 'in', self.ids)],
            ['type_id'],
            ['type_id']
        )
        result = {data['type_id'][0]: data['type_id_count'] for data in eco_data}
        for eco_type in self:
            eco_type.eco_count = result.get(eco_type.id, 0)
