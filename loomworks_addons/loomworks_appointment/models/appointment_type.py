# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import secrets


class AppointmentType(models.Model):
    """Appointment Type - defines a type of appointment that can be booked."""
    _name = 'appointment.type'
    _description = 'Appointment Type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char(
        string='Appointment Type',
        required=True,
        tracking=True,
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    # Description
    description = fields.Html(
        string='Description',
        help='Public description shown on the booking page',
    )
    internal_note = fields.Text(
        string='Internal Notes',
        help='Notes for internal use only',
    )

    # Duration and scheduling
    duration = fields.Float(
        string='Duration (hours)',
        default=1.0,
        required=True,
    )
    duration_minutes = fields.Integer(
        string='Duration (minutes)',
        compute='_compute_duration_minutes',
        store=True,
    )
    buffer_before = fields.Integer(
        string='Buffer Before (minutes)',
        default=0,
        help='Time to block before the appointment',
    )
    buffer_after = fields.Integer(
        string='Buffer After (minutes)',
        default=0,
        help='Time to block after the appointment',
    )

    # Availability
    min_schedule_hours = fields.Float(
        string='Minimum Scheduling Notice (hours)',
        default=1.0,
        help='Minimum time before an appointment can be booked',
    )
    max_schedule_days = fields.Integer(
        string='Maximum Scheduling Window (days)',
        default=60,
        help='How far in advance appointments can be booked',
    )
    slot_duration = fields.Float(
        string='Slot Duration (hours)',
        default=0.5,
        help='Time intervals for available slots (e.g., 0.5 = 30 min slots)',
    )

    # Capacity and limits
    max_per_day = fields.Integer(
        string='Max Appointments per Day',
        default=0,
        help='Maximum appointments of this type per day (0 = unlimited)',
    )
    max_per_week = fields.Integer(
        string='Max Appointments per Week',
        default=0,
        help='Maximum appointments of this type per week (0 = unlimited)',
    )
    concurrent_limit = fields.Integer(
        string='Concurrent Appointments',
        default=1,
        help='Number of appointments that can occur at the same time',
    )

    # Resources
    assign_method = fields.Selection([
        ('any_available', 'Any Available'),
        ('round_robin', 'Round Robin'),
        ('least_busy', 'Least Busy'),
        ('customer_choice', 'Customer Choice'),
    ], string='Assignment Method', default='any_available', required=True)
    resource_ids = fields.Many2many(
        'appointment.resource',
        string='Available Resources',
        help='Resources that can handle this appointment type',
    )
    resource_count = fields.Integer(
        string='Resource Count',
        compute='_compute_resource_count',
    )

    # Booking settings
    requires_confirmation = fields.Boolean(
        string='Requires Confirmation',
        default=False,
        help='Bookings need to be confirmed before being finalized',
    )
    allow_reschedule = fields.Boolean(
        string='Allow Reschedule',
        default=True,
    )
    allow_cancel = fields.Boolean(
        string='Allow Cancellation',
        default=True,
    )
    cancel_limit_hours = fields.Float(
        string='Cancellation Deadline (hours)',
        default=24.0,
        help='Hours before appointment when cancellation is no longer allowed',
    )

    # Questions/Intake
    question_ids = fields.One2many(
        'appointment.question',
        'appointment_type_id',
        string='Questions',
    )

    # Online booking
    is_published = fields.Boolean(
        string='Published',
        default=False,
        help='Make this appointment type available for online booking',
    )
    website_url = fields.Char(
        string='Booking URL',
        compute='_compute_website_url',
    )
    access_token = fields.Char(
        string='Access Token',
        copy=False,
    )

    # Location
    location = fields.Selection([
        ('in_person', 'In Person'),
        ('online', 'Online (Video Call)'),
        ('phone', 'Phone Call'),
        ('customer_location', 'At Customer Location'),
    ], string='Location Type', default='in_person', required=True)
    location_name = fields.Char(string='Location Name')
    location_address = fields.Text(string='Location Address')
    online_meeting_provider = fields.Selection([
        ('google_meet', 'Google Meet'),
        ('zoom', 'Zoom'),
        ('teams', 'Microsoft Teams'),
        ('custom', 'Custom Link'),
    ], string='Online Meeting Provider')
    custom_meeting_url = fields.Char(string='Custom Meeting URL')

    # Colors and visuals
    color = fields.Integer(string='Color')
    icon = fields.Char(string='Icon', default='fa-calendar')
    image = fields.Binary(string='Image')

    # Statistics
    booking_count = fields.Integer(
        string='Total Bookings',
        compute='_compute_booking_stats',
    )
    upcoming_count = fields.Integer(
        string='Upcoming Bookings',
        compute='_compute_booking_stats',
    )

    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    @api.depends('duration')
    def _compute_duration_minutes(self):
        for rec in self:
            rec.duration_minutes = int(rec.duration * 60)

    @api.depends('resource_ids')
    def _compute_resource_count(self):
        for rec in self:
            rec.resource_count = len(rec.resource_ids)

    @api.depends('access_token')
    def _compute_website_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            if rec.access_token:
                rec.website_url = f"{base_url}/appointment/{rec.access_token}"
            else:
                rec.website_url = False

    def _compute_booking_stats(self):
        today = fields.Datetime.now()
        for rec in self:
            bookings = self.env['appointment.booking'].search([
                ('appointment_type_id', '=', rec.id),
                ('state', '!=', 'canceled'),
            ])
            rec.booking_count = len(bookings)
            rec.upcoming_count = len(bookings.filtered(lambda b: b.start_datetime >= today))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('access_token'):
                vals['access_token'] = secrets.token_urlsafe(16)
        return super().create(vals_list)

    def action_publish(self):
        """Publish appointment type for online booking."""
        self.ensure_one()
        if not self.resource_ids:
            raise ValidationError(_('Please assign at least one resource before publishing.'))
        self.is_published = True

    def action_unpublish(self):
        """Unpublish appointment type."""
        self.ensure_one()
        self.is_published = False

    def action_regenerate_token(self):
        """Regenerate the access token."""
        self.ensure_one()
        self.access_token = secrets.token_urlsafe(16)

    def action_view_bookings(self):
        """Open bookings for this appointment type."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bookings'),
            'res_model': 'appointment.booking',
            'view_mode': 'tree,form,calendar',
            'domain': [('appointment_type_id', '=', self.id)],
            'context': {'default_appointment_type_id': self.id},
        }

    def get_available_slots(self, start_date, end_date, resource_id=False, timezone='UTC'):
        """Get available time slots for booking.

        Args:
            start_date: Start of date range
            end_date: End of date range
            resource_id: Optional specific resource
            timezone: Timezone for display

        Returns:
            List of available slots with datetime and resources
        """
        self.ensure_one()
        from ..services.availability_service import AvailabilityService
        service = AvailabilityService(self.env)
        return service.get_available_slots(
            self, start_date, end_date, resource_id, timezone
        )


class AppointmentQuestion(models.Model):
    """Questions/intake form for appointments."""
    _name = 'appointment.question'
    _description = 'Appointment Question'
    _order = 'sequence, id'

    appointment_type_id = fields.Many2one(
        'appointment.type',
        string='Appointment Type',
        required=True,
        ondelete='cascade',
    )
    name = fields.Char(
        string='Question',
        required=True,
    )
    sequence = fields.Integer(default=10)
    question_type = fields.Selection([
        ('text', 'Short Text'),
        ('textarea', 'Long Text'),
        ('select', 'Dropdown'),
        ('radio', 'Radio Buttons'),
        ('checkbox', 'Checkbox'),
        ('date', 'Date'),
        ('phone', 'Phone Number'),
        ('email', 'Email'),
    ], string='Type', default='text', required=True)
    required = fields.Boolean(string='Required', default=False)
    placeholder = fields.Char(string='Placeholder')
    option_ids = fields.One2many(
        'appointment.question.option',
        'question_id',
        string='Options',
    )


class AppointmentQuestionOption(models.Model):
    """Options for select/radio questions."""
    _name = 'appointment.question.option'
    _description = 'Appointment Question Option'
    _order = 'sequence, id'

    question_id = fields.Many2one(
        'appointment.question',
        string='Question',
        required=True,
        ondelete='cascade',
    )
    name = fields.Char(string='Option', required=True)
    sequence = fields.Integer(default=10)
