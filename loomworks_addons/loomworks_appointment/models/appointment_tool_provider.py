# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from loomworks import api, fields, models, _
from datetime import datetime, timedelta
import json


class AppointmentToolProvider(models.AbstractModel):
    """AI Tool Provider for Appointment operations."""
    _name = 'appointment.tool.provider'
    _inherit = 'loomworks.ai.tool.provider'
    _description = 'Appointment AI Tool Provider'

    @api.model
    def _get_tool_definitions(self):
        """Return appointment-related tool definitions for AI."""
        return [
            {
                'name': 'appointment_list_types',
                'description': 'List available appointment types that customers can book',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'published_only': {
                            'type': 'boolean',
                            'description': 'Only show published (publicly bookable) types',
                            'default': True,
                        },
                    },
                },
            },
            {
                'name': 'appointment_get_availability',
                'description': 'Get available time slots for booking an appointment',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'appointment_type_id': {
                            'type': 'integer',
                            'description': 'ID of the appointment type',
                        },
                        'date': {
                            'type': 'string',
                            'description': 'Date to check (YYYY-MM-DD format)',
                        },
                        'days': {
                            'type': 'integer',
                            'description': 'Number of days to check from the date',
                            'default': 7,
                        },
                        'resource_id': {
                            'type': 'integer',
                            'description': 'Specific resource ID (optional)',
                        },
                    },
                    'required': ['appointment_type_id', 'date'],
                },
            },
            {
                'name': 'appointment_book',
                'description': 'Book an appointment for a customer',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'appointment_type_id': {
                            'type': 'integer',
                            'description': 'ID of the appointment type',
                        },
                        'start_datetime': {
                            'type': 'string',
                            'description': 'Appointment start time (YYYY-MM-DD HH:MM:SS format)',
                        },
                        'partner_id': {
                            'type': 'integer',
                            'description': 'Customer partner ID (optional if creating new)',
                        },
                        'customer_name': {
                            'type': 'string',
                            'description': 'Customer name (required if no partner_id)',
                        },
                        'customer_email': {
                            'type': 'string',
                            'description': 'Customer email (required if no partner_id)',
                        },
                        'customer_phone': {
                            'type': 'string',
                            'description': 'Customer phone (optional)',
                        },
                        'resource_id': {
                            'type': 'integer',
                            'description': 'Specific resource to book (optional)',
                        },
                        'notes': {
                            'type': 'string',
                            'description': 'Customer notes or comments',
                        },
                    },
                    'required': ['appointment_type_id', 'start_datetime'],
                },
            },
            {
                'name': 'appointment_reschedule',
                'description': 'Reschedule an existing appointment',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'booking_id': {
                            'type': 'integer',
                            'description': 'ID of the booking to reschedule',
                        },
                        'new_datetime': {
                            'type': 'string',
                            'description': 'New appointment time (YYYY-MM-DD HH:MM:SS format)',
                        },
                    },
                    'required': ['booking_id', 'new_datetime'],
                },
            },
            {
                'name': 'appointment_cancel',
                'description': 'Cancel an appointment',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'booking_id': {
                            'type': 'integer',
                            'description': 'ID of the booking to cancel',
                        },
                        'reason': {
                            'type': 'string',
                            'description': 'Cancellation reason',
                        },
                    },
                    'required': ['booking_id'],
                },
            },
            {
                'name': 'appointment_get_booking',
                'description': 'Get details of a specific appointment booking',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'booking_id': {
                            'type': 'integer',
                            'description': 'ID of the booking',
                        },
                    },
                    'required': ['booking_id'],
                },
            },
            {
                'name': 'appointment_list_upcoming',
                'description': 'List upcoming appointments',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'partner_id': {
                            'type': 'integer',
                            'description': 'Filter by customer partner ID',
                        },
                        'resource_id': {
                            'type': 'integer',
                            'description': 'Filter by resource ID',
                        },
                        'days': {
                            'type': 'integer',
                            'description': 'Number of days to look ahead',
                            'default': 30,
                        },
                        'limit': {
                            'type': 'integer',
                            'description': 'Maximum number of results',
                            'default': 20,
                        },
                    },
                },
            },
            {
                'name': 'appointment_list_resources',
                'description': 'List available resources (staff, rooms, etc.)',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'appointment_type_id': {
                            'type': 'integer',
                            'description': 'Filter by appointment type',
                        },
                        'resource_type': {
                            'type': 'string',
                            'description': 'Filter by type (employee, room, equipment, other)',
                        },
                    },
                },
            },
        ]

    @api.model
    def _execute_tool(self, tool_name, parameters):
        """Execute an appointment tool."""
        method_name = f'_tool_{tool_name}'
        if hasattr(self, method_name):
            return getattr(self, method_name)(parameters)
        return {'error': f'Unknown tool: {tool_name}'}

    def _tool_appointment_list_types(self, params):
        """List available appointment types."""
        domain = [('active', '=', True)]
        if params.get('published_only', True):
            domain.append(('is_published', '=', True))

        types = self.env['appointment.type'].search(domain)
        return {
            'appointment_types': [{
                'id': t.id,
                'name': t.name,
                'duration_minutes': t.duration_minutes,
                'location': t.location,
                'is_published': t.is_published,
                'description': t.description or '',
                'resource_count': t.resource_count,
            } for t in types],
            'count': len(types),
        }

    def _tool_appointment_get_availability(self, params):
        """Get available slots for an appointment type."""
        apt_type = self.env['appointment.type'].browse(params['appointment_type_id'])
        if not apt_type.exists():
            return {'error': 'Appointment type not found'}

        start_date = datetime.strptime(params['date'], '%Y-%m-%d')
        days = params.get('days', 7)
        end_date = start_date + timedelta(days=days)
        resource_id = params.get('resource_id')

        slots = apt_type.get_available_slots(
            start_date, end_date, resource_id
        )

        return {
            'appointment_type': apt_type.name,
            'date_range': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d'),
            },
            'available_slots': slots,
            'slot_count': len(slots),
        }

    def _tool_appointment_book(self, params):
        """Book an appointment."""
        apt_type = self.env['appointment.type'].browse(params['appointment_type_id'])
        if not apt_type.exists():
            return {'error': 'Appointment type not found'}

        # Get or create partner
        partner_id = params.get('partner_id')
        if not partner_id:
            if not params.get('customer_email'):
                return {'error': 'Customer email is required'}

            # Check for existing partner
            partner = self.env['res.partner'].search([
                ('email', '=', params['customer_email'])
            ], limit=1)

            if not partner:
                partner = self.env['res.partner'].create({
                    'name': params.get('customer_name', params['customer_email']),
                    'email': params['customer_email'],
                    'phone': params.get('customer_phone'),
                })
            partner_id = partner.id

        # Parse datetime
        start_dt = datetime.strptime(params['start_datetime'], '%Y-%m-%d %H:%M:%S')
        end_dt = start_dt + timedelta(hours=apt_type.duration)

        # Get or assign resource
        resource_id = params.get('resource_id')
        if not resource_id and apt_type.resource_ids:
            # Auto-assign based on method
            for resource in apt_type.resource_ids:
                if resource.is_available(start_dt, end_dt):
                    resource_id = resource.id
                    break

        if not resource_id and apt_type.resource_ids:
            return {'error': 'No available resources for this time slot'}

        # Create booking
        booking = self.env['appointment.booking'].create({
            'appointment_type_id': apt_type.id,
            'partner_id': partner_id,
            'start_datetime': start_dt,
            'end_datetime': end_dt,
            'resource_id': resource_id,
            'customer_notes': params.get('notes'),
        })

        return {
            'success': True,
            'booking_id': booking.id,
            'reference': booking.name,
            'state': booking.state,
            'start_datetime': booking.start_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            'end_datetime': booking.end_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            'resource': booking.resource_id.name if booking.resource_id else None,
            'booking_url': booking.booking_url,
        }

    def _tool_appointment_reschedule(self, params):
        """Reschedule an appointment."""
        booking = self.env['appointment.booking'].browse(params['booking_id'])
        if not booking.exists():
            return {'error': 'Booking not found'}

        if booking.state not in ('pending', 'confirmed'):
            return {'error': f'Cannot reschedule booking in {booking.state} state'}

        if not booking.appointment_type_id.allow_reschedule:
            return {'error': 'Rescheduling is not allowed for this appointment type'}

        new_start = datetime.strptime(params['new_datetime'], '%Y-%m-%d %H:%M:%S')
        new_end = new_start + timedelta(hours=booking.duration)

        # Check availability
        if booking.resource_id:
            if not booking.resource_id.is_available(
                new_start, new_end, exclude_booking_id=booking.id
            ):
                return {'error': 'Resource is not available at this time'}

        # Update booking
        old_datetime = booking.start_datetime
        booking.write({
            'start_datetime': new_start,
            'end_datetime': new_end,
        })

        # Update calendar event
        if booking.calendar_event_id:
            booking.calendar_event_id.write({
                'start': new_start,
                'stop': new_end,
            })

        booking.message_post(
            body=_('Rescheduled from %s to %s') % (
                old_datetime.strftime('%Y-%m-%d %H:%M'),
                new_start.strftime('%Y-%m-%d %H:%M')
            )
        )

        return {
            'success': True,
            'booking_id': booking.id,
            'new_start': new_start.strftime('%Y-%m-%d %H:%M:%S'),
            'new_end': new_end.strftime('%Y-%m-%d %H:%M:%S'),
        }

    def _tool_appointment_cancel(self, params):
        """Cancel an appointment."""
        booking = self.env['appointment.booking'].browse(params['booking_id'])
        if not booking.exists():
            return {'error': 'Booking not found'}

        if booking.state in ('done', 'canceled'):
            return {'error': f'Cannot cancel booking in {booking.state} state'}

        if not booking.appointment_type_id.allow_cancel:
            return {'error': 'Cancellation is not allowed for this appointment type'}

        booking.cancel_reason = params.get('reason')
        booking.action_cancel()

        return {
            'success': True,
            'booking_id': booking.id,
            'state': 'canceled',
        }

    def _tool_appointment_get_booking(self, params):
        """Get booking details."""
        booking = self.env['appointment.booking'].browse(params['booking_id'])
        if not booking.exists():
            return {'error': 'Booking not found'}

        return {
            'id': booking.id,
            'reference': booking.name,
            'state': booking.state,
            'appointment_type': booking.appointment_type_id.name,
            'customer': {
                'id': booking.partner_id.id,
                'name': booking.customer_name,
                'email': booking.customer_email,
                'phone': booking.customer_phone,
            },
            'schedule': {
                'start': booking.start_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'end': booking.end_datetime.strftime('%Y-%m-%d %H:%M:%S'),
                'duration_hours': booking.duration,
            },
            'resource': booking.resource_id.name if booking.resource_id else None,
            'location': booking.location or booking.meeting_url,
            'notes': booking.customer_notes,
            'booking_url': booking.booking_url,
        }

    def _tool_appointment_list_upcoming(self, params):
        """List upcoming appointments."""
        domain = [
            ('state', 'in', ['pending', 'confirmed']),
            ('start_datetime', '>=', fields.Datetime.now()),
        ]

        if params.get('partner_id'):
            domain.append(('partner_id', '=', params['partner_id']))
        if params.get('resource_id'):
            domain.append(('resource_id', '=', params['resource_id']))

        days = params.get('days', 30)
        end_date = fields.Datetime.now() + timedelta(days=days)
        domain.append(('start_datetime', '<=', end_date))

        limit = params.get('limit', 20)
        bookings = self.env['appointment.booking'].search(
            domain, limit=limit, order='start_datetime'
        )

        return {
            'bookings': [{
                'id': b.id,
                'reference': b.name,
                'appointment_type': b.appointment_type_id.name,
                'customer': b.customer_name,
                'start': b.start_datetime.strftime('%Y-%m-%d %H:%M'),
                'state': b.state,
                'resource': b.resource_id.name if b.resource_id else None,
            } for b in bookings],
            'count': len(bookings),
        }

    def _tool_appointment_list_resources(self, params):
        """List available resources."""
        domain = [('active', '=', True)]

        if params.get('appointment_type_id'):
            domain.append(('appointment_type_ids', 'in', [params['appointment_type_id']]))
        if params.get('resource_type'):
            domain.append(('resource_type', '=', params['resource_type']))

        resources = self.env['appointment.resource'].search(domain)

        return {
            'resources': [{
                'id': r.id,
                'name': r.name,
                'type': r.resource_type,
                'description': r.short_description or '',
                'email': r.email,
                'upcoming_count': r.upcoming_count,
            } for r in resources],
            'count': len(resources),
        }
