# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from loomworks import api, fields, models, _


class AppointmentSlot(models.Model):
    """Appointment Slot - pre-defined availability slots."""
    _name = 'appointment.slot'
    _description = 'Appointment Slot'
    _order = 'weekday, start_hour'

    appointment_type_id = fields.Many2one(
        'appointment.type',
        string='Appointment Type',
        required=True,
        ondelete='cascade',
    )

    # Day of week
    weekday = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday'),
    ], string='Day of Week', required=True)

    # Time range
    start_hour = fields.Float(
        string='Start Time',
        required=True,
        help='Start time in hours (e.g., 9.5 = 9:30 AM)',
    )
    end_hour = fields.Float(
        string='End Time',
        required=True,
        help='End time in hours (e.g., 17.0 = 5:00 PM)',
    )

    # Display
    start_time_display = fields.Char(
        string='Start',
        compute='_compute_time_display',
    )
    end_time_display = fields.Char(
        string='End',
        compute='_compute_time_display',
    )

    # Resource restrictions
    resource_ids = fields.Many2many(
        'appointment.resource',
        string='Specific Resources',
        help='Leave empty to apply to all resources',
    )

    @api.depends('start_hour', 'end_hour')
    def _compute_time_display(self):
        for rec in self:
            rec.start_time_display = self._float_to_time(rec.start_hour)
            rec.end_time_display = self._float_to_time(rec.end_hour)

    @staticmethod
    def _float_to_time(float_time):
        """Convert float time to HH:MM format."""
        hours = int(float_time)
        minutes = int((float_time - hours) * 60)
        return f"{hours:02d}:{minutes:02d}"

    @api.constrains('start_hour', 'end_hour')
    def _check_hours(self):
        for rec in self:
            if rec.start_hour < 0 or rec.start_hour >= 24:
                raise models.ValidationError(_('Start time must be between 0 and 24.'))
            if rec.end_hour < 0 or rec.end_hour > 24:
                raise models.ValidationError(_('End time must be between 0 and 24.'))
            if rec.end_hour <= rec.start_hour:
                raise models.ValidationError(_('End time must be after start time.'))


class AppointmentSlotException(models.Model):
    """Slot exceptions - days when normal availability doesn't apply."""
    _name = 'appointment.slot.exception'
    _description = 'Appointment Slot Exception'
    _order = 'date'

    appointment_type_id = fields.Many2one(
        'appointment.type',
        string='Appointment Type',
        required=True,
        ondelete='cascade',
    )

    date = fields.Date(
        string='Date',
        required=True,
    )

    exception_type = fields.Selection([
        ('unavailable', 'Not Available'),
        ('custom', 'Custom Hours'),
    ], string='Type', default='unavailable', required=True)

    reason = fields.Char(string='Reason')

    # Custom hours (only if type is 'custom')
    start_hour = fields.Float(string='Start Time')
    end_hour = fields.Float(string='End Time')

    # Resource restrictions
    resource_ids = fields.Many2many(
        'appointment.resource',
        string='Specific Resources',
        help='Leave empty to apply to all resources',
    )

    @api.constrains('exception_type', 'start_hour', 'end_hour')
    def _check_custom_hours(self):
        for rec in self:
            if rec.exception_type == 'custom':
                if not rec.start_hour or not rec.end_hour:
                    raise models.ValidationError(
                        _('Custom hours require start and end time.')
                    )
                if rec.end_hour <= rec.start_hour:
                    raise models.ValidationError(
                        _('End time must be after start time.')
                    )
