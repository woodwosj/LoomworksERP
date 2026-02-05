# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta, time
from odoo import fields
import pytz


class AvailabilityService:
    """Service for calculating appointment availability."""

    def __init__(self, env):
        self.env = env

    def get_available_slots(self, appointment_type, start_date, end_date,
                            resource_id=False, timezone='UTC'):
        """Get available time slots for an appointment type.

        Args:
            appointment_type: appointment.type record
            start_date: Start datetime
            end_date: End datetime
            resource_id: Optional specific resource ID
            timezone: Timezone for slot display

        Returns:
            List of dicts with slot information
        """
        slots = []
        tz = pytz.timezone(timezone)

        # Get resources to check
        if resource_id:
            resources = appointment_type.resource_ids.filtered(
                lambda r: r.id == resource_id
            )
        else:
            resources = appointment_type.resource_ids

        if not resources:
            return slots

        # Generate dates
        current_date = start_date.date() if isinstance(start_date, datetime) else start_date
        end = end_date.date() if isinstance(end_date, datetime) else end_date

        while current_date <= end:
            day_slots = self._get_day_slots(
                appointment_type, current_date, resources, tz
            )
            slots.extend(day_slots)
            current_date += timedelta(days=1)

        return slots

    def _get_day_slots(self, appointment_type, date, resources, tz):
        """Get available slots for a specific day.

        Args:
            appointment_type: appointment.type record
            date: Date to check
            resources: Resources to check
            tz: Timezone

        Returns:
            List of available slot dicts
        """
        slots = []
        weekday = str(date.weekday())

        # Check daily/weekly limits
        if appointment_type.max_per_day:
            day_start = datetime.combine(date, time.min)
            day_end = datetime.combine(date, time.max)
            day_count = self.env['appointment.booking'].search_count([
                ('appointment_type_id', '=', appointment_type.id),
                ('start_datetime', '>=', day_start),
                ('start_datetime', '<', day_end),
                ('state', 'in', ['pending', 'confirmed']),
            ])
            if day_count >= appointment_type.max_per_day:
                return slots

        # Get appointment slots for this day
        apt_slots = self.env['appointment.slot'].search([
            ('appointment_type_id', '=', appointment_type.id),
            ('weekday', '=', weekday),
        ])

        # Check for exceptions
        exceptions = self.env['appointment.slot.exception'].search([
            ('appointment_type_id', '=', appointment_type.id),
            ('date', '=', date),
        ])

        # If day is marked unavailable
        if any(e.exception_type == 'unavailable' for e in exceptions):
            return slots

        # Use custom hours if specified
        custom_hours = exceptions.filtered(lambda e: e.exception_type == 'custom')
        if custom_hours:
            apt_slots = custom_hours

        # Generate slots based on slot_duration
        slot_duration_hours = appointment_type.slot_duration or 0.5
        appointment_duration = appointment_type.duration

        for apt_slot in apt_slots:
            current_hour = apt_slot.start_hour

            while current_hour + appointment_duration <= apt_slot.end_hour:
                slot_start = datetime.combine(
                    date,
                    time(int(current_hour), int((current_hour % 1) * 60))
                )
                slot_end = slot_start + timedelta(hours=appointment_duration)

                # Check minimum scheduling notice
                min_notice = timedelta(hours=appointment_type.min_schedule_hours)
                if slot_start < datetime.now() + min_notice:
                    current_hour += slot_duration_hours
                    continue

                # Find available resources for this slot
                available_resources = []
                for resource in resources:
                    if self._is_resource_available(
                        resource, slot_start, slot_end, appointment_type
                    ):
                        available_resources.append({
                            'id': resource.id,
                            'name': resource.name,
                        })

                # Check concurrent limit
                if len(available_resources) >= 1:
                    # Add slot
                    slots.append({
                        'datetime': slot_start.strftime('%Y-%m-%d %H:%M:%S'),
                        'date': date.strftime('%Y-%m-%d'),
                        'time': slot_start.strftime('%H:%M'),
                        'end_time': slot_end.strftime('%H:%M'),
                        'available_resources': available_resources,
                        'resource_count': len(available_resources),
                    })

                current_hour += slot_duration_hours

        return slots

    def _is_resource_available(self, resource, start_dt, end_dt, appointment_type):
        """Check if a resource is available for a time slot.

        Args:
            resource: appointment.resource record
            start_dt: Slot start datetime
            end_dt: Slot end datetime
            appointment_type: appointment.type record

        Returns:
            bool: True if available
        """
        # Check resource calendar (working hours)
        if resource.resource_calendar_id:
            # TODO: Check against resource calendar
            pass

        # Check for conflicting bookings (including buffer time)
        buffer_before = timedelta(minutes=appointment_type.buffer_before)
        buffer_after = timedelta(minutes=appointment_type.buffer_after)

        check_start = start_dt - buffer_before
        check_end = end_dt + buffer_after

        conflicts = self.env['appointment.booking'].search_count([
            ('resource_id', '=', resource.id),
            ('state', 'in', ['pending', 'confirmed']),
            '|',
            '&', ('start_datetime', '<', check_end), ('end_datetime', '>', check_start),
            '&', ('start_datetime', '>=', check_start), ('start_datetime', '<', check_end),
        ])

        if conflicts > 0:
            return False

        # Check resource daily/weekly limits
        if resource.max_per_day:
            day_start = datetime.combine(start_dt.date(), time.min)
            day_end = datetime.combine(start_dt.date(), time.max)
            day_count = self.env['appointment.booking'].search_count([
                ('resource_id', '=', resource.id),
                ('start_datetime', '>=', day_start),
                ('start_datetime', '<', day_end),
                ('state', 'in', ['pending', 'confirmed']),
            ])
            if day_count >= resource.max_per_day:
                return False

        return True

    def get_resource_availability(self, resource, start_date, end_date, appointment_type=False):
        """Get availability for a specific resource.

        Args:
            resource: appointment.resource record
            start_date: Start datetime
            end_date: End datetime
            appointment_type: Optional appointment type filter

        Returns:
            List of available time periods
        """
        availability = []

        # Get appointment types for this resource
        if appointment_type:
            apt_types = appointment_type
        else:
            apt_types = resource.appointment_type_ids

        if not apt_types:
            return availability

        for apt_type in apt_types:
            slots = self.get_available_slots(
                apt_type, start_date, end_date, resource.id
            )
            for slot in slots:
                slot['appointment_type'] = {
                    'id': apt_type.id,
                    'name': apt_type.name,
                }
                availability.append(slot)

        # Sort by datetime
        availability.sort(key=lambda x: x['datetime'])

        return availability
