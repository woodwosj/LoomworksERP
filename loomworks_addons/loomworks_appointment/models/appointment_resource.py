# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AppointmentResource(models.Model):
    """Appointment Resource - staff members or other bookable resources."""
    _name = 'appointment.resource'
    _description = 'Appointment Resource'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char(
        string='Resource Name',
        required=True,
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    # Resource type
    resource_type = fields.Selection([
        ('employee', 'Employee'),
        ('room', 'Room'),
        ('equipment', 'Equipment'),
        ('other', 'Other'),
    ], string='Type', default='employee', required=True)

    # Employee link
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
    )
    user_id = fields.Many2one(
        related='employee_id.user_id',
        string='User',
        store=True,
    )

    # Description
    description = fields.Text(string='Description')
    short_description = fields.Char(
        string='Short Description',
        help='Brief description shown in booking selection',
    )
    image = fields.Binary(
        string='Photo',
        compute='_compute_image',
        store=True,
        readonly=False,
    )

    # Availability
    resource_calendar_id = fields.Many2one(
        'resource.calendar',
        string='Working Hours',
        help='Default working hours for this resource',
    )

    # Appointment types this resource can handle
    appointment_type_ids = fields.Many2many(
        'appointment.type',
        string='Appointment Types',
        help='Types of appointments this resource can handle',
    )

    # Limits
    max_per_day = fields.Integer(
        string='Max Appointments per Day',
        default=0,
        help='Maximum appointments per day (0 = unlimited)',
    )
    max_per_week = fields.Integer(
        string='Max Appointments per Week',
        default=0,
        help='Maximum appointments per week (0 = unlimited)',
    )

    # Contact
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')

    # Statistics
    booking_count = fields.Integer(
        string='Total Bookings',
        compute='_compute_booking_stats',
    )
    upcoming_count = fields.Integer(
        string='Upcoming Bookings',
        compute='_compute_booking_stats',
    )

    # Location
    location = fields.Char(string='Location')
    capacity = fields.Integer(
        string='Capacity',
        default=1,
        help='For rooms - number of people',
    )

    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    # Color for calendar display
    color = fields.Integer(string='Color')

    @api.depends('employee_id', 'employee_id.image_128')
    def _compute_image(self):
        for rec in self:
            if rec.employee_id and rec.employee_id.image_128:
                rec.image = rec.employee_id.image_128
            elif not rec.image:
                rec.image = False

    def _compute_booking_stats(self):
        today = fields.Datetime.now()
        for rec in self:
            bookings = self.env['appointment.booking'].search([
                ('resource_id', '=', rec.id),
                ('state', 'not in', ['canceled', 'no_show']),
            ])
            rec.booking_count = len(bookings)
            rec.upcoming_count = len(bookings.filtered(lambda b: b.start_datetime >= today))

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            if not self.name:
                self.name = self.employee_id.name
            if not self.email:
                self.email = self.employee_id.work_email
            if not self.phone:
                self.phone = self.employee_id.work_phone
            if not self.resource_calendar_id:
                self.resource_calendar_id = self.employee_id.resource_calendar_id

    def action_view_bookings(self):
        """View bookings for this resource."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bookings'),
            'res_model': 'appointment.booking',
            'view_mode': 'tree,calendar,form',
            'domain': [('resource_id', '=', self.id)],
            'context': {'default_resource_id': self.id},
        }

    def get_availability(self, start_date, end_date, appointment_type=False):
        """Get resource availability for a date range.

        Args:
            start_date: Start datetime
            end_date: End datetime
            appointment_type: Optional specific appointment type

        Returns:
            List of available time slots
        """
        self.ensure_one()
        from ..services.availability_service import AvailabilityService
        service = AvailabilityService(self.env)
        return service.get_resource_availability(
            self, start_date, end_date, appointment_type
        )

    def is_available(self, start_datetime, end_datetime, exclude_booking_id=False):
        """Check if resource is available for a time slot.

        Args:
            start_datetime: Slot start
            end_datetime: Slot end
            exclude_booking_id: Booking to exclude (for reschedule)

        Returns:
            bool: True if available
        """
        self.ensure_one()

        # Check for conflicting bookings
        domain = [
            ('resource_id', '=', self.id),
            ('state', 'in', ['pending', 'confirmed']),
            '|',
            '&', ('start_datetime', '<', end_datetime), ('end_datetime', '>', start_datetime),
            '&', ('start_datetime', '>=', start_datetime), ('start_datetime', '<', end_datetime),
        ]
        if exclude_booking_id:
            domain.append(('id', '!=', exclude_booking_id))

        conflicting = self.env['appointment.booking'].search_count(domain)
        return conflicting == 0
