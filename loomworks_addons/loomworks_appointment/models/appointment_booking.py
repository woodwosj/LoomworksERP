# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from loomworks import api, fields, models, _
from loomworks.exceptions import UserError, ValidationError
from datetime import timedelta
import secrets


class AppointmentBooking(models.Model):
    """Appointment Booking - individual appointment instances."""
    _name = 'appointment.booking'
    _description = 'Appointment Booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_datetime desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )

    # Appointment Type
    appointment_type_id = fields.Many2one(
        'appointment.type',
        string='Appointment Type',
        required=True,
        tracking=True,
    )

    # Scheduling
    start_datetime = fields.Datetime(
        string='Start Time',
        required=True,
        tracking=True,
    )
    end_datetime = fields.Datetime(
        string='End Time',
        required=True,
        tracking=True,
    )
    duration = fields.Float(
        string='Duration (hours)',
        compute='_compute_duration',
        store=True,
    )
    all_day = fields.Boolean(string='All Day', default=False)

    # Resource assignment
    resource_id = fields.Many2one(
        'appointment.resource',
        string='Resource',
        tracking=True,
    )
    employee_id = fields.Many2one(
        related='resource_id.employee_id',
        string='Employee',
        store=True,
    )

    # Customer information
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True,
    )
    customer_name = fields.Char(
        string='Customer Name',
        related='partner_id.name',
        store=True,
    )
    customer_email = fields.Char(
        string='Email',
        related='partner_id.email',
        store=True,
    )
    customer_phone = fields.Char(
        string='Phone',
        related='partner_id.phone',
        store=True,
    )

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Confirmation'),
        ('confirmed', 'Confirmed'),
        ('done', 'Completed'),
        ('canceled', 'Canceled'),
        ('no_show', 'No Show'),
    ], string='Status', default='draft', required=True, tracking=True)

    # Access
    access_token = fields.Char(
        string='Access Token',
        copy=False,
        readonly=True,
    )
    booking_url = fields.Char(
        string='Booking URL',
        compute='_compute_booking_url',
    )

    # Calendar integration
    calendar_event_id = fields.Many2one(
        'calendar.event',
        string='Calendar Event',
        copy=False,
    )

    # Location
    location_type = fields.Selection(
        related='appointment_type_id.location',
        store=True,
    )
    location = fields.Char(string='Location')
    meeting_url = fields.Char(string='Meeting URL')

    # Notes and answers
    notes = fields.Text(string='Internal Notes')
    customer_notes = fields.Text(string='Customer Notes')
    answer_ids = fields.One2many(
        'appointment.booking.answer',
        'booking_id',
        string='Answers',
    )

    # Cancellation
    canceled_date = fields.Datetime(string='Canceled Date')
    cancel_reason = fields.Text(string='Cancellation Reason')

    # Reminders
    reminder_sent = fields.Boolean(string='Reminder Sent', default=False)
    reminder_date = fields.Datetime(string='Reminder Date')

    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    # Display
    color = fields.Integer(related='appointment_type_id.color')

    @api.depends('start_datetime', 'end_datetime')
    def _compute_duration(self):
        for rec in self:
            if rec.start_datetime and rec.end_datetime:
                delta = rec.end_datetime - rec.start_datetime
                rec.duration = delta.total_seconds() / 3600
            else:
                rec.duration = 0

    @api.depends('access_token')
    def _compute_booking_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            if rec.access_token:
                rec.booking_url = f"{base_url}/my/appointment/{rec.access_token}"
            else:
                rec.booking_url = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('appointment.booking') or _('New')
            if not vals.get('access_token'):
                vals['access_token'] = secrets.token_urlsafe(24)
        records = super().create(vals_list)
        for record in records:
            if record.appointment_type_id.requires_confirmation:
                record.state = 'pending'
            else:
                record.action_confirm()
        return records

    @api.constrains('start_datetime', 'end_datetime')
    def _check_dates(self):
        for rec in self:
            if rec.start_datetime and rec.end_datetime:
                if rec.end_datetime <= rec.start_datetime:
                    raise ValidationError(_('End time must be after start time.'))

    def action_confirm(self):
        """Confirm the booking."""
        for rec in self:
            if rec.state in ('draft', 'pending'):
                rec.state = 'confirmed'
                rec._create_calendar_event()
                rec._send_confirmation_email()
                rec.message_post(body=_('Booking confirmed.'))

    def action_cancel(self):
        """Cancel the booking."""
        for rec in self:
            if rec.state in ('draft', 'pending', 'confirmed'):
                rec.write({
                    'state': 'canceled',
                    'canceled_date': fields.Datetime.now(),
                })
                if rec.calendar_event_id:
                    rec.calendar_event_id.unlink()
                rec._send_cancellation_email()
                rec.message_post(body=_('Booking canceled.'))

    def action_complete(self):
        """Mark booking as completed."""
        for rec in self:
            if rec.state == 'confirmed':
                rec.state = 'done'
                rec.message_post(body=_('Appointment completed.'))

    def action_no_show(self):
        """Mark as no-show."""
        for rec in self:
            if rec.state == 'confirmed':
                rec.state = 'no_show'
                rec.message_post(body=_('Customer did not show up.'))

    def action_reschedule(self):
        """Open reschedule wizard."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reschedule Appointment'),
            'res_model': 'appointment.reschedule.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_booking_id': self.id},
        }

    def _create_calendar_event(self):
        """Create a calendar event for the booking."""
        self.ensure_one()
        if self.calendar_event_id:
            return

        attendee_ids = []
        if self.partner_id:
            attendee_ids.append((0, 0, {'partner_id': self.partner_id.id}))
        if self.resource_id.employee_id:
            if self.resource_id.employee_id.user_id.partner_id:
                attendee_ids.append((0, 0, {
                    'partner_id': self.resource_id.employee_id.user_id.partner_id.id
                }))

        event_vals = {
            'name': f"{self.appointment_type_id.name} - {self.partner_id.name}",
            'start': self.start_datetime,
            'stop': self.end_datetime,
            'allday': self.all_day,
            'description': self._get_event_description(),
            'location': self.location or self.meeting_url or '',
            'attendee_ids': attendee_ids,
            'user_id': self.resource_id.employee_id.user_id.id if self.resource_id.employee_id.user_id else self.env.user.id,
        }

        event = self.env['calendar.event'].create(event_vals)
        self.calendar_event_id = event

    def _get_event_description(self):
        """Generate calendar event description."""
        self.ensure_one()
        lines = [
            f"Appointment Type: {self.appointment_type_id.name}",
            f"Customer: {self.partner_id.name}",
        ]
        if self.customer_email:
            lines.append(f"Email: {self.customer_email}")
        if self.customer_phone:
            lines.append(f"Phone: {self.customer_phone}")
        if self.resource_id:
            lines.append(f"Resource: {self.resource_id.name}")
        if self.meeting_url:
            lines.append(f"Meeting URL: {self.meeting_url}")
        if self.customer_notes:
            lines.append(f"\nCustomer Notes:\n{self.customer_notes}")
        return '\n'.join(lines)

    def _send_confirmation_email(self):
        """Send confirmation email to customer."""
        self.ensure_one()
        template = self.env.ref(
            'loomworks_appointment.mail_template_booking_confirmation',
            raise_if_not_found=False
        )
        if template:
            template.send_mail(self.id, force_send=True)

    def _send_cancellation_email(self):
        """Send cancellation email to customer."""
        self.ensure_one()
        template = self.env.ref(
            'loomworks_appointment.mail_template_booking_cancellation',
            raise_if_not_found=False
        )
        if template:
            template.send_mail(self.id, force_send=True)

    def _send_reminder_email(self):
        """Send reminder email to customer."""
        self.ensure_one()
        template = self.env.ref(
            'loomworks_appointment.mail_template_booking_reminder',
            raise_if_not_found=False
        )
        if template:
            template.send_mail(self.id, force_send=True)
            self.reminder_sent = True

    @api.model
    def _cron_send_reminders(self):
        """Cron job to send appointment reminders."""
        # Send reminders 24 hours before
        reminder_time = fields.Datetime.now() + timedelta(hours=24)
        bookings = self.search([
            ('state', '=', 'confirmed'),
            ('reminder_sent', '=', False),
            ('start_datetime', '<=', reminder_time),
            ('start_datetime', '>', fields.Datetime.now()),
        ])
        for booking in bookings:
            try:
                booking._send_reminder_email()
            except Exception:
                pass  # Log but don't fail

    @api.model
    def _cron_complete_past_bookings(self):
        """Cron job to auto-complete past bookings."""
        past_bookings = self.search([
            ('state', '=', 'confirmed'),
            ('end_datetime', '<', fields.Datetime.now() - timedelta(hours=1)),
        ])
        past_bookings.write({'state': 'done'})


class AppointmentBookingAnswer(models.Model):
    """Answers to appointment questions."""
    _name = 'appointment.booking.answer'
    _description = 'Appointment Booking Answer'

    booking_id = fields.Many2one(
        'appointment.booking',
        string='Booking',
        required=True,
        ondelete='cascade',
    )
    question_id = fields.Many2one(
        'appointment.question',
        string='Question',
        required=True,
    )
    value = fields.Text(string='Answer')
