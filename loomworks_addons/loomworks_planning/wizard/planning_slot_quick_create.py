# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PlanningSlotQuickCreate(models.TransientModel):
    """Wizard for batch shift creation from templates."""
    _name = 'planning.slot.quick.create'
    _description = 'Quick Create Shifts'

    template_id = fields.Many2one(
        'planning.slot.template',
        string='Shift Template',
        required=True,
    )
    employee_ids = fields.Many2many(
        'hr.employee',
        string='Employees',
        required=True,
    )
    role_id = fields.Many2one(
        'planning.role',
        string='Role',
        help='Override template role',
    )

    date_from = fields.Date(
        string='From Date',
        required=True,
        default=fields.Date.today,
    )
    date_to = fields.Date(
        string='To Date',
        required=True,
    )

    # Recurrence options
    create_recurrence = fields.Boolean(
        string='Create Recurring Pattern',
        help='Generate shifts based on recurrence settings',
    )
    repeat_type = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
    ], default='weekly', string='Repeat')

    # Weekly options
    mon = fields.Boolean('Monday', default=True)
    tue = fields.Boolean('Tuesday', default=True)
    wed = fields.Boolean('Wednesday', default=True)
    thu = fields.Boolean('Thursday', default=True)
    fri = fields.Boolean('Friday', default=True)
    sat = fields.Boolean('Saturday')
    sun = fields.Boolean('Sunday')

    # Options
    publish_immediately = fields.Boolean(
        string='Publish Immediately',
        help='Publish slots after creation (skips conflicts)',
    )
    skip_conflicts = fields.Boolean(
        string='Skip Conflicting Slots',
        default=True,
        help='Skip creation if employee already has a slot at that time',
    )

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id and self.template_id.role_id:
            self.role_id = self.template_id.role_id

    @api.onchange('date_from')
    def _onchange_date_from(self):
        if self.date_from and not self.date_to:
            # Default to 1 week
            self.date_to = self.date_from + timedelta(days=6)

    def _get_weekdays(self):
        """Return list of weekday indices (0=Monday)."""
        days = []
        if self.mon:
            days.append(0)
        if self.tue:
            days.append(1)
        if self.wed:
            days.append(2)
        if self.thu:
            days.append(3)
        if self.fri:
            days.append(4)
        if self.sat:
            days.append(5)
        if self.sun:
            days.append(6)
        return days or [0, 1, 2, 3, 4]  # Default to weekdays

    def _generate_dates(self):
        """Generate list of dates based on settings."""
        dates = []
        current = self.date_from

        if self.create_recurrence:
            if self.repeat_type == 'daily':
                while current <= self.date_to:
                    dates.append(current)
                    current += timedelta(days=1)
            else:  # weekly
                weekdays = self._get_weekdays()
                while current <= self.date_to:
                    if current.weekday() in weekdays:
                        dates.append(current)
                    current += timedelta(days=1)
        else:
            # Single occurrence
            dates.append(self.date_from)

        return dates

    def _check_conflict(self, employee, start_dt, end_dt):
        """Check if employee has conflicting slot."""
        existing = self.env['planning.slot'].search([
            ('employee_id', '=', employee.id),
            ('state', 'not in', ['cancelled']),
            ('start_datetime', '<', end_dt),
            ('end_datetime', '>', start_dt),
        ], limit=1)
        return bool(existing)

    def action_create_slots(self):
        """Create planning slots based on wizard settings."""
        self.ensure_one()

        if not self.employee_ids:
            raise UserError(_('Please select at least one employee.'))

        if self.date_to < self.date_from:
            raise UserError(_('End date must be after start date.'))

        template = self.template_id
        role = self.role_id or template.role_id

        # Generate dates
        dates = self._generate_dates()

        if not dates:
            raise UserError(_('No valid dates found for the selected criteria.'))

        slots = self.env['planning.slot']
        skipped = 0

        for date in dates:
            # Calculate start/end datetime from template time
            start_hour = int(template.start_time)
            start_min = int((template.start_time % 1) * 60)
            start_dt = datetime.combine(date, datetime.min.time()) + timedelta(
                hours=start_hour, minutes=start_min
            )
            end_dt = start_dt + timedelta(hours=template.duration)

            for employee in self.employee_ids:
                # Check for conflicts
                if self.skip_conflicts and self._check_conflict(employee, start_dt, end_dt):
                    skipped += 1
                    continue

                # Create slot
                slot = self.env['planning.slot'].create({
                    'template_id': template.id,
                    'employee_id': employee.id,
                    'role_id': role.id,
                    'start_datetime': start_dt,
                    'end_datetime': end_dt,
                    'project_id': template.project_id.id if template.project_id else False,
                    'task_id': template.task_id.id if template.task_id else False,
                    'state': 'draft',
                })
                slots |= slot

        # Optionally publish
        if self.publish_immediately and slots:
            publishable = slots.filtered(lambda s: not s.has_conflict)
            if publishable:
                publishable.action_publish()

        # Return action to view created slots
        message = _('Created %d slots') % len(slots)
        if skipped:
            message += _(' (skipped %d conflicts)') % skipped

        return {
            'type': 'ir.actions.act_window',
            'name': message,
            'res_model': 'planning.slot',
            'domain': [('id', 'in', slots.ids)] if slots else [('id', '=', 0)],
            'view_mode': 'gantt,list,form',
            'context': {'create': False},
        }
