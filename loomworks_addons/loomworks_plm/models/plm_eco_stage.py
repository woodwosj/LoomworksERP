# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from loomworks import api, fields, models


class PlmEcoStage(models.Model):
    """ECO Workflow Stages

    Defines the stages through which an Engineering Change Order progresses.
    Stages are linked to states and can have approval requirements.
    """
    _name = 'plm.eco.stage'
    _description = 'ECO Stage'
    _order = 'sequence, name'

    name = fields.Char(
        string='Stage Name',
        required=True,
        translate=True
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Determines the order of stages'
    )
    fold = fields.Boolean(
        string='Folded in Kanban',
        help='Fold this stage in kanban view to reduce visual clutter'
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('approved', 'Approved'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='Related State', required=True, default='draft',
        help='Maps this stage to an ECO state for status tracking')

    # Stage Behavior
    is_blocking = fields.Boolean(
        string='Blocking Stage',
        default=False,
        help='ECO cannot proceed to next stage without explicit approval'
    )
    require_approval = fields.Boolean(
        string='Requires Approval',
        default=False,
        help='ECO must be approved by designated approvers at this stage'
    )
    mail_template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        domain=[('model', '=', 'plm.eco')],
        help='Email notification sent when ECO enters this stage'
    )

    # ECO statistics
    eco_count = fields.Integer(
        compute='_compute_eco_count',
        string='ECO Count'
    )

    def _compute_eco_count(self):
        """Count ECOs in each stage."""
        eco_data = self.env['plm.eco'].read_group(
            [('stage_id', 'in', self.ids)],
            ['stage_id'],
            ['stage_id']
        )
        result = {data['stage_id'][0]: data['stage_id_count'] for data in eco_data}
        for stage in self:
            stage.eco_count = result.get(stage.id, 0)
