# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from odoo import http, fields, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from datetime import datetime, timedelta
import json


class AppointmentPortal(CustomerPortal):
    """Portal controller for appointment booking."""

    def _prepare_home_portal_values(self, counters):
        """Add appointment count to portal home."""
        values = super()._prepare_home_portal_values(counters)
        if 'appointment_count' in counters:
            partner = request.env.user.partner_id
            values['appointment_count'] = request.env['appointment.booking'].search_count([
                ('partner_id', '=', partner.id),
            ])
        return values

    @http.route(['/my/appointments', '/my/appointments/page/<int:page>'],
                type='http', auth='user', website=True)
    def portal_my_appointments(self, page=1, date_begin=None, date_end=None,
                               sortby=None, filterby=None, **kw):
        """Display customer's appointment bookings."""
        values = self._prepare_portal_layout_values()
        Booking = request.env['appointment.booking']
        partner = request.env.user.partner_id

        domain = [('partner_id', '=', partner.id)]

        # Sorting
        searchbar_sortings = {
            'date': {'label': _('Date'), 'order': 'start_datetime desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'state': {'label': _('Status'), 'order': 'state'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        # Filtering
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'upcoming': {'label': _('Upcoming'), 'domain': [
                ('state', 'in', ['pending', 'confirmed']),
                ('start_datetime', '>=', fields.Datetime.now()),
            ]},
            'past': {'label': _('Past'), 'domain': [
                ('start_datetime', '<', fields.Datetime.now()),
            ]},
            'canceled': {'label': _('Canceled'), 'domain': [('state', '=', 'canceled')]},
        }
        if not filterby:
            filterby = 'upcoming'
        domain += searchbar_filters[filterby]['domain']

        # Date filter
        if date_begin and date_end:
            domain += [
                ('start_datetime', '>=', date_begin),
                ('start_datetime', '<=', date_end),
            ]

        # Count
        booking_count = Booking.search_count(domain)

        # Pager
        pager = portal_pager(
            url='/my/appointments',
            url_args={'date_begin': date_begin, 'date_end': date_end,
                      'sortby': sortby, 'filterby': filterby},
            total=booking_count,
            page=page,
            step=self._items_per_page,
        )

        # Bookings
        bookings = Booking.search(domain, order=order, limit=self._items_per_page,
                                   offset=pager['offset'])

        values.update({
            'bookings': bookings,
            'page_name': 'appointment',
            'default_url': '/my/appointments',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
        })

        return request.render('loomworks_appointment.portal_my_appointments', values)

    @http.route('/my/appointment/<string:access_token>', type='http', auth='public', website=True)
    def portal_appointment_detail(self, access_token, **kw):
        """View appointment booking details."""
        booking = request.env['appointment.booking'].sudo().search([
            ('access_token', '=', access_token)
        ], limit=1)

        if not booking:
            return request.redirect('/my/appointments')

        values = {
            'booking': booking,
            'page_name': 'appointment_detail',
        }

        return request.render('loomworks_appointment.portal_appointment_detail', values)

    @http.route('/my/appointment/<string:access_token>/cancel', type='http',
                auth='public', website=True, methods=['POST'])
    def portal_appointment_cancel(self, access_token, **kw):
        """Cancel appointment from portal."""
        booking = request.env['appointment.booking'].sudo().search([
            ('access_token', '=', access_token)
        ], limit=1)

        if not booking:
            return request.redirect('/my/appointments')

        if booking.state in ('pending', 'confirmed'):
            # Check cancellation deadline
            if booking.appointment_type_id.allow_cancel:
                deadline = booking.start_datetime - timedelta(
                    hours=booking.appointment_type_id.cancel_limit_hours
                )
                if datetime.now() <= deadline:
                    booking.cancel_reason = kw.get('reason', _('Canceled by customer'))
                    booking.action_cancel()

        return request.redirect(f'/my/appointment/{access_token}')

    @http.route('/my/appointment/<string:access_token>/reschedule', type='http',
                auth='public', website=True)
    def portal_appointment_reschedule(self, access_token, **kw):
        """Reschedule appointment page."""
        booking = request.env['appointment.booking'].sudo().search([
            ('access_token', '=', access_token)
        ], limit=1)

        if not booking or booking.state not in ('pending', 'confirmed'):
            return request.redirect('/my/appointments')

        if not booking.appointment_type_id.allow_reschedule:
            return request.redirect(f'/my/appointment/{access_token}')

        # Get available slots
        apt_type = booking.appointment_type_id
        start_date = datetime.now()
        end_date = start_date + timedelta(days=apt_type.max_schedule_days)
        slots = apt_type.get_available_slots(start_date, end_date, booking.resource_id.id)

        values = {
            'booking': booking,
            'appointment_type': apt_type,
            'available_slots': slots,
            'page_name': 'appointment_reschedule',
        }

        return request.render('loomworks_appointment.portal_appointment_reschedule', values)


class AppointmentBooking(http.Controller):
    """Public controller for appointment booking."""

    @http.route('/appointment', type='http', auth='public', website=True)
    def appointment_index(self, **kw):
        """List all published appointment types."""
        apt_types = request.env['appointment.type'].sudo().search([
            ('is_published', '=', True),
            ('active', '=', True),
        ])

        values = {
            'appointment_types': apt_types,
            'page_name': 'appointment_index',
        }

        return request.render('loomworks_appointment.portal_appointment_index', values)

    @http.route('/appointment/<string:access_token>', type='http', auth='public', website=True)
    def appointment_type_page(self, access_token, **kw):
        """Appointment type booking page."""
        apt_type = request.env['appointment.type'].sudo().search([
            ('access_token', '=', access_token),
            ('is_published', '=', True),
        ], limit=1)

        if not apt_type:
            return request.redirect('/appointment')

        values = {
            'appointment_type': apt_type,
            'page_name': 'appointment_book',
        }

        return request.render('loomworks_appointment.portal_appointment_book', values)

    @http.route('/appointment/<string:access_token>/slots', type='json', auth='public')
    def appointment_get_slots(self, access_token, date=None, resource_id=None, **kw):
        """Get available slots for a date (JSON endpoint)."""
        apt_type = request.env['appointment.type'].sudo().search([
            ('access_token', '=', access_token),
            ('is_published', '=', True),
        ], limit=1)

        if not apt_type:
            return {'error': 'Appointment type not found'}

        if not date:
            date = datetime.now().strftime('%Y-%m-%d')

        start_date = datetime.strptime(date, '%Y-%m-%d')
        end_date = start_date + timedelta(days=1)

        slots = apt_type.get_available_slots(
            start_date, end_date, resource_id,
            timezone=kw.get('timezone', 'UTC')
        )

        return {
            'slots': slots,
            'date': date,
        }

    @http.route('/appointment/<string:access_token>/book', type='json', auth='public')
    def appointment_book_slot(self, access_token, datetime_str=None, resource_id=None,
                               name=None, email=None, phone=None, notes=None,
                               answers=None, **kw):
        """Book an appointment slot (JSON endpoint)."""
        apt_type = request.env['appointment.type'].sudo().search([
            ('access_token', '=', access_token),
            ('is_published', '=', True),
        ], limit=1)

        if not apt_type:
            return {'error': 'Appointment type not found'}

        if not datetime_str or not email or not name:
            return {'error': 'Missing required fields'}

        # Parse datetime
        try:
            start_dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return {'error': 'Invalid datetime format'}

        end_dt = start_dt + timedelta(hours=apt_type.duration)

        # Get or create partner
        Partner = request.env['res.partner'].sudo()
        partner = Partner.search([('email', '=', email)], limit=1)
        if not partner:
            partner = Partner.create({
                'name': name,
                'email': email,
                'phone': phone,
            })

        # Check resource availability
        if resource_id:
            resource = request.env['appointment.resource'].sudo().browse(resource_id)
            if not resource.is_available(start_dt, end_dt):
                return {'error': 'Selected resource is no longer available'}
        else:
            # Auto-assign resource
            resource = None
            for r in apt_type.resource_ids:
                if r.is_available(start_dt, end_dt):
                    resource = r
                    break
            if apt_type.resource_ids and not resource:
                return {'error': 'No available resources for this time'}
            resource_id = resource.id if resource else False

        # Create booking
        booking = request.env['appointment.booking'].sudo().create({
            'appointment_type_id': apt_type.id,
            'partner_id': partner.id,
            'start_datetime': start_dt,
            'end_datetime': end_dt,
            'resource_id': resource_id,
            'customer_notes': notes,
        })

        # Save answers
        if answers:
            for question_id, answer_value in answers.items():
                request.env['appointment.booking.answer'].sudo().create({
                    'booking_id': booking.id,
                    'question_id': int(question_id),
                    'value': answer_value,
                })

        return {
            'success': True,
            'booking_id': booking.id,
            'reference': booking.name,
            'access_token': booking.access_token,
            'redirect_url': f'/my/appointment/{booking.access_token}',
        }

    @http.route('/appointment/confirm/<string:access_token>', type='http',
                auth='public', website=True)
    def appointment_confirm(self, access_token, **kw):
        """Booking confirmation page."""
        booking = request.env['appointment.booking'].sudo().search([
            ('access_token', '=', access_token)
        ], limit=1)

        if not booking:
            return request.redirect('/appointment')

        values = {
            'booking': booking,
            'page_name': 'appointment_confirm',
        }

        return request.render('loomworks_appointment.portal_appointment_confirm', values)
