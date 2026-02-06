# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from loomworks import api, fields, models, _


class CalendarEvent(models.Model):
    """Extend calendar.event for appointment integration."""
    _inherit = 'calendar.event'

    appointment_booking_id = fields.Many2one(
        'appointment.booking',
        string='Appointment Booking',
        compute='_compute_appointment_booking',
        store=True,
    )
    is_appointment = fields.Boolean(
        string='Is Appointment',
        compute='_compute_is_appointment',
        store=True,
    )

    @api.depends('res_id', 'res_model')
    def _compute_appointment_booking(self):
        for event in self:
            booking = self.env['appointment.booking'].search([
                ('calendar_event_id', '=', event.id)
            ], limit=1)
            event.appointment_booking_id = booking.id if booking else False

    @api.depends('appointment_booking_id')
    def _compute_is_appointment(self):
        for event in self:
            event.is_appointment = bool(event.appointment_booking_id)

    def write(self, vals):
        """Sync changes to appointment bookings."""
        result = super().write(vals)

        # If start/stop changed, update linked booking
        if 'start' in vals or 'stop' in vals:
            for event in self:
                if event.appointment_booking_id:
                    booking_vals = {}
                    if 'start' in vals:
                        booking_vals['start_datetime'] = event.start
                    if 'stop' in vals:
                        booking_vals['end_datetime'] = event.stop
                    if booking_vals:
                        event.appointment_booking_id.write(booking_vals)

        return result

    def unlink(self):
        """Handle deletion of appointment calendar events."""
        bookings = self.mapped('appointment_booking_id')
        result = super().unlink()

        # Clear calendar event reference from bookings
        for booking in bookings:
            booking.calendar_event_id = False

        return result
