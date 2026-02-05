# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import api, fields, models


class HrEmployeePlanning(models.Model):
    """Extend HR Employee with planning capabilities."""
    _inherit = 'hr.employee'

    planning_slot_ids = fields.One2many(
        'planning.slot',
        'employee_id',
        string='Planning Slots',
    )

    # Planning statistics
    planning_slot_count = fields.Integer(
        compute='_compute_planning_stats',
        string='Total Slots',
    )
    planning_hours_this_week = fields.Float(
        compute='_compute_planning_stats',
        string='Hours This Week',
    )
    planning_hours_next_week = fields.Float(
        compute='_compute_planning_stats',
        string='Hours Next Week',
    )

    # Default planning role
    default_planning_role_id = fields.Many2one(
        'planning.role',
        string='Default Planning Role',
        help='Default role when assigning this employee',
    )

    @api.depends('planning_slot_ids', 'planning_slot_ids.state', 'planning_slot_ids.allocated_hours')
    def _compute_planning_stats(self):
        today = fields.Date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        next_week_start = week_start + timedelta(weeks=1)
        next_week_end = next_week_start + timedelta(days=6)

        for employee in self:
            # Total slots
            employee.planning_slot_count = len(employee.planning_slot_ids.filtered(
                lambda s: s.state not in ['cancelled']
            ))

            # Hours this week
            this_week_slots = employee.planning_slot_ids.filtered(
                lambda s: s.state not in ['cancelled'] and
                          s.start_datetime and
                          s.start_datetime.date() >= week_start and
                          s.start_datetime.date() <= week_end
            )
            employee.planning_hours_this_week = sum(this_week_slots.mapped('allocated_hours'))

            # Hours next week
            next_week_slots = employee.planning_slot_ids.filtered(
                lambda s: s.state not in ['cancelled'] and
                          s.start_datetime and
                          s.start_datetime.date() >= next_week_start and
                          s.start_datetime.date() <= next_week_end
            )
            employee.planning_hours_next_week = sum(next_week_slots.mapped('allocated_hours'))

    def get_availability(self, date_from, date_to):
        """
        Returns available hours for planning in the given date range.
        Considers working schedule and approved time off.

        Args:
            date_from: datetime - Start of range
            date_to: datetime - End of range

        Returns:
            float: Available hours
        """
        self.ensure_one()

        # Convert dates to datetime if needed
        if isinstance(date_from, type(fields.Date.today())):
            date_from = datetime.combine(date_from, datetime.min.time())
        if isinstance(date_to, type(fields.Date.today())):
            date_to = datetime.combine(date_to, datetime.max.time())

        # Get working hours from resource calendar
        calendar = self.resource_calendar_id or self.company_id.resource_calendar_id
        if not calendar:
            # Default 8 hours per working day
            delta = date_to - date_from
            working_days = sum(
                1 for i in range(delta.days + 1)
                if (date_from + timedelta(days=i)).weekday() < 5
            )
            working_hours = working_days * 8
        else:
            # Calculate using resource calendar
            working_hours = calendar.get_work_hours_count(
                date_from,
                date_to,
                compute_leaves=True,
                resource=self.resource_id,
            )

        # Subtract already allocated hours
        allocated_slots = self.planning_slot_ids.filtered(
            lambda s: s.start_datetime and
                      s.end_datetime and
                      s.start_datetime >= date_from and
                      s.end_datetime <= date_to and
                      s.state not in ['cancelled']
        )
        allocated_hours = sum(allocated_slots.mapped('allocated_hours'))

        return max(0, working_hours - allocated_hours)

    def get_conflicts_in_range(self, date_from, date_to):
        """
        Find all scheduling conflicts for this employee in date range.

        Returns:
            recordset of planning.slot with conflicts
        """
        self.ensure_one()

        # Convert dates to datetime if needed
        if isinstance(date_from, type(fields.Date.today())):
            date_from = datetime.combine(date_from, datetime.min.time())
        if isinstance(date_to, type(fields.Date.today())):
            date_to = datetime.combine(date_to, datetime.max.time())

        return self.planning_slot_ids.filtered(
            lambda s: s.has_conflict and
                      s.start_datetime and
                      s.start_datetime >= date_from and
                      s.start_datetime <= date_to and
                      s.state not in ['cancelled']
        )

    def action_view_planning(self):
        """Open planning view for this employee."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Planning - {self.name}',
            'res_model': 'planning.slot',
            'view_mode': 'gantt,list,form,calendar',
            'domain': [('employee_id', '=', self.id)],
            'context': {
                'default_employee_id': self.id,
                'search_default_employee_id': self.id,
            },
        }

    def action_view_this_week(self):
        """Open this week's planning for employee."""
        self.ensure_one()
        today = fields.Date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        return {
            'type': 'ir.actions.act_window',
            'name': f'This Week - {self.name}',
            'res_model': 'planning.slot',
            'view_mode': 'gantt,list,form',
            'domain': [
                ('employee_id', '=', self.id),
                ('start_datetime', '>=', datetime.combine(week_start, datetime.min.time())),
                ('start_datetime', '<=', datetime.combine(week_end, datetime.max.time())),
            ],
            'context': {
                'default_employee_id': self.id,
            },
        }
