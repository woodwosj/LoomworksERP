# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from loomworks import api, fields, models, _


class HrEmployee(models.Model):
    """Extend hr.employee for appointment resource linking."""
    _inherit = 'hr.employee'

    appointment_resource_ids = fields.One2many(
        'appointment.resource',
        'employee_id',
        string='Appointment Resources',
    )
    appointment_resource_count = fields.Integer(
        string='Appointment Resources',
        compute='_compute_appointment_resource_count',
    )
    is_appointment_resource = fields.Boolean(
        string='Is Appointment Resource',
        compute='_compute_is_appointment_resource',
        store=True,
    )
    upcoming_appointment_count = fields.Integer(
        string='Upcoming Appointments',
        compute='_compute_appointment_stats',
    )

    @api.depends('appointment_resource_ids')
    def _compute_appointment_resource_count(self):
        for employee in self:
            employee.appointment_resource_count = len(employee.appointment_resource_ids)

    @api.depends('appointment_resource_ids')
    def _compute_is_appointment_resource(self):
        for employee in self:
            employee.is_appointment_resource = bool(employee.appointment_resource_ids)

    def _compute_appointment_stats(self):
        today = fields.Datetime.now()
        for employee in self:
            bookings = self.env['appointment.booking'].search([
                ('resource_id.employee_id', '=', employee.id),
                ('state', 'in', ['pending', 'confirmed']),
                ('start_datetime', '>=', today),
            ])
            employee.upcoming_appointment_count = len(bookings)

    def action_create_appointment_resource(self):
        """Create appointment resource for this employee."""
        self.ensure_one()
        if self.appointment_resource_ids:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'appointment.resource',
                'res_id': self.appointment_resource_ids[0].id,
                'view_mode': 'form',
            }

        resource = self.env['appointment.resource'].create({
            'name': self.name,
            'resource_type': 'employee',
            'employee_id': self.id,
            'email': self.work_email,
            'phone': self.work_phone,
            'resource_calendar_id': self.resource_calendar_id.id,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'appointment.resource',
            'res_id': resource.id,
            'view_mode': 'form',
        }

    def action_view_appointments(self):
        """View employee's appointments."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Appointments'),
            'res_model': 'appointment.booking',
            'view_mode': 'tree,calendar,form',
            'domain': [('resource_id.employee_id', '=', self.id)],
        }
