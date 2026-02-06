# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from loomworks import http
from loomworks.http import request


class AppointmentController(http.Controller):
    """Main controller for appointment module."""

    @http.route('/appointment/calendar/<int:appointment_type_id>', type='http',
                auth='user', website=True)
    def appointment_calendar_embed(self, appointment_type_id, **kw):
        """Embeddable calendar widget for appointment booking."""
        apt_type = request.env['appointment.type'].browse(appointment_type_id)

        if not apt_type.exists() or not apt_type.is_published:
            return request.not_found()

        values = {
            'appointment_type': apt_type,
            'embed_mode': True,
        }

        return request.render(
            'loomworks_appointment.appointment_calendar_embed', values
        )

    @http.route('/appointment/ical/<string:access_token>', type='http',
                auth='public', website=False)
    def appointment_ical_download(self, access_token, **kw):
        """Download iCal file for booking."""
        booking = request.env['appointment.booking'].sudo().search([
            ('access_token', '=', access_token)
        ], limit=1)

        if not booking:
            return request.not_found()

        # Generate iCal content
        ical_content = self._generate_ical(booking)

        return request.make_response(
            ical_content,
            headers=[
                ('Content-Type', 'text/calendar'),
                ('Content-Disposition', f'attachment; filename=appointment_{booking.name}.ics'),
            ]
        )

    def _generate_ical(self, booking):
        """Generate iCal format for booking."""
        from datetime import datetime

        lines = [
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//Loomworks//Appointment//EN',
            'BEGIN:VEVENT',
            f'UID:{booking.access_token}@loomworks',
            f'DTSTART:{booking.start_datetime.strftime("%Y%m%dT%H%M%SZ")}',
            f'DTEND:{booking.end_datetime.strftime("%Y%m%dT%H%M%SZ")}',
            f'SUMMARY:{booking.appointment_type_id.name}',
            f'DESCRIPTION:{booking.customer_notes or ""}',
            f'LOCATION:{booking.location or booking.meeting_url or ""}',
            f'STATUS:{"CONFIRMED" if booking.state == "confirmed" else "TENTATIVE"}',
            'END:VEVENT',
            'END:VCALENDAR',
        ]

        return '\r\n'.join(lines)
