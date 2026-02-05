# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PlanningSlotTemplate(models.Model):
    """Shift template for quick slot creation."""
    _name = 'planning.slot.template'
    _description = 'Shift Template'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)

    # Role association
    role_id = fields.Many2one(
        'planning.role',
        string='Role',
        required=True,
        ondelete='restrict',
    )

    # Time pattern
    start_time = fields.Float(
        string='Start Time',
        required=True,
        default=9.0,
        help='Hour of day (0-24), e.g., 9.5 = 9:30 AM',
    )
    duration = fields.Float(
        string='Duration (hours)',
        required=True,
        default=8.0,
    )

    # Computed end time for display
    end_time = fields.Float(
        compute='_compute_end_time',
        string='End Time',
    )

    # Default assignment
    employee_id = fields.Many2one(
        'hr.employee',
        string='Default Employee',
        help='Pre-assign this employee when using template',
    )

    # Default project/task
    project_id = fields.Many2one('project.project', string='Project')
    task_id = fields.Many2one(
        'project.task',
        string='Task',
        domain="[('project_id', '=', project_id)]",
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)

    color = fields.Integer(related='role_id.color')

    @api.depends('start_time', 'duration')
    def _compute_end_time(self):
        for template in self:
            template.end_time = template.start_time + template.duration

    def name_get(self):
        result = []
        for template in self:
            start_hour = int(template.start_time)
            start_min = int((template.start_time % 1) * 60)
            end_time = template.start_time + template.duration
            end_hour = int(end_time)
            end_min = int((end_time % 1) * 60)

            time_str = f'{start_hour:02d}:{start_min:02d} - {end_hour:02d}:{end_min:02d}'
            name = f'{template.name} ({time_str})'
            result.append((template.id, name))
        return result

    @api.onchange('role_id')
    def _onchange_role_id(self):
        if self.role_id and self.role_id.default_hours:
            self.duration = self.role_id.default_hours
