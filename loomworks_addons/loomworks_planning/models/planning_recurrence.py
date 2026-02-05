# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PlanningRecurrence(models.Model):
    """Recurring shift pattern for generating multiple slots."""
    _name = 'planning.recurrence'
    _description = 'Planning Recurrence'

    name = fields.Char(compute='_compute_name', store=True)

    slot_ids = fields.One2many(
        'planning.slot',
        'recurrence_id',
        string='Generated Slots',
    )

    # Recurrence pattern
    repeat_type = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ], default='weekly', required=True, string='Repeat')

    repeat_interval = fields.Integer(
        default=1,
        string='Repeat Every',
        help='Number of days/weeks/months between occurrences',
    )

    # For weekly: which days
    mon = fields.Boolean('Monday', default=True)
    tue = fields.Boolean('Tuesday', default=True)
    wed = fields.Boolean('Wednesday', default=True)
    thu = fields.Boolean('Thursday', default=True)
    fri = fields.Boolean('Friday', default=True)
    sat = fields.Boolean('Saturday')
    sun = fields.Boolean('Sunday')

    # End condition
    repeat_until = fields.Date(string='Repeat Until')
    repeat_count = fields.Integer(
        string='Number of Occurrences',
        help='Generate this many occurrences (0 = until date)',
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    @api.depends('repeat_type', 'repeat_interval')
    def _compute_name(self):
        for rec in self:
            if rec.repeat_type == 'daily':
                if rec.repeat_interval == 1:
                    rec.name = _('Every day')
                else:
                    rec.name = _('Every %d days') % rec.repeat_interval
            elif rec.repeat_type == 'weekly':
                days = []
                if rec.mon:
                    days.append(_('Mon'))
                if rec.tue:
                    days.append(_('Tue'))
                if rec.wed:
                    days.append(_('Wed'))
                if rec.thu:
                    days.append(_('Thu'))
                if rec.fri:
                    days.append(_('Fri'))
                if rec.sat:
                    days.append(_('Sat'))
                if rec.sun:
                    days.append(_('Sun'))
                days_str = ', '.join(days) if days else _('No days')
                if rec.repeat_interval == 1:
                    rec.name = _('Weekly on %s') % days_str
                else:
                    rec.name = _('Every %d weeks on %s') % (rec.repeat_interval, days_str)
            elif rec.repeat_type == 'monthly':
                if rec.repeat_interval == 1:
                    rec.name = _('Every month')
                else:
                    rec.name = _('Every %d months') % rec.repeat_interval
            else:
                rec.name = _('Recurrence')

    @api.constrains('repeat_until', 'repeat_count')
    def _check_end_condition(self):
        for rec in self:
            if not rec.repeat_until and not rec.repeat_count:
                raise ValidationError(_(
                    'You must specify either a repeat until date or number of occurrences.'
                ))

    def get_weekdays(self):
        """Return list of weekday indices (0=Monday) for weekly recurrence."""
        self.ensure_one()
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
        return days

    def generate_dates(self, start_date, end_date=None):
        """
        Generate occurrence dates based on recurrence pattern.

        Args:
            start_date: Starting date for generation
            end_date: Optional end date (defaults to repeat_until)

        Returns:
            List of dates
        """
        self.ensure_one()

        if not end_date:
            if self.repeat_until:
                end_date = self.repeat_until
            elif self.repeat_count:
                # Will limit by count instead
                end_date = start_date + timedelta(days=365)  # Max 1 year
            else:
                end_date = start_date + timedelta(days=30)  # Default 30 days

        dates = []
        current = start_date
        count = 0
        max_count = self.repeat_count or 999

        if self.repeat_type == 'daily':
            while current <= end_date and count < max_count:
                dates.append(current)
                count += 1
                current += timedelta(days=self.repeat_interval)

        elif self.repeat_type == 'weekly':
            weekdays = self.get_weekdays()
            if not weekdays:
                weekdays = [0, 1, 2, 3, 4]  # Default weekdays

            week_start = current - timedelta(days=current.weekday())
            week_num = 0

            while week_start <= end_date and count < max_count:
                for day_idx in weekdays:
                    day_date = week_start + timedelta(days=day_idx)
                    if day_date >= start_date and day_date <= end_date and count < max_count:
                        dates.append(day_date)
                        count += 1

                week_num += 1
                if week_num >= self.repeat_interval:
                    week_start += timedelta(weeks=self.repeat_interval)
                    week_num = 0
                else:
                    week_start += timedelta(weeks=1)

        elif self.repeat_type == 'monthly':
            while current <= end_date and count < max_count:
                dates.append(current)
                count += 1
                current += relativedelta(months=self.repeat_interval)
                # Keep same day of month
                if current.day != start_date.day:
                    try:
                        current = current.replace(day=start_date.day)
                    except ValueError:
                        # Day doesn't exist in month, use last day
                        pass

        return dates
