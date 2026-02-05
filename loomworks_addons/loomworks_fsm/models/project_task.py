# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProjectTaskFSM(models.Model):
    """
    Extension of project.task for field service management.

    Adds FSM-specific fields and methods for mobile field service work
    including worksheets, materials tracking, GPS check-in/out, and
    timesheet integration.

    Note: Core FSM fields (is_fsm, timer_start, timer_pause, customer_signature, etc.)
    are defined in the forked project module (Part 0 modifications).
    """
    _inherit = 'project.task'

    # FSM flag - enables FSM features on this task
    is_fsm = fields.Boolean(
        string='Field Service Task',
        default=False,
        help="Enable field service features for this task (timer, signature, geolocation)")

    # Geolocation fields (for customer location)
    partner_latitude = fields.Float(
        related='partner_id.partner_latitude',
        string='Latitude',
        readonly=False,
        store=True)
    partner_longitude = fields.Float(
        related='partner_id.partner_longitude',
        string='Longitude',
        readonly=False,
        store=True)

    # Scheduling fields for FSM
    planned_date_start = fields.Datetime(
        string='Planned Start',
        help="Planned start date/time for field service work")
    planned_date_end = fields.Datetime(
        string='Planned End',
        help="Planned end date/time for field service work")

    # Timer infrastructure for time tracking
    timer_start = fields.Datetime(
        string='Timer Started',
        help="When the work timer was started")
    timer_pause = fields.Datetime(
        string='Timer Paused',
        help="When the work timer was paused")

    # Customer signature capture
    customer_signature = fields.Binary(
        string='Customer Signature',
        attachment=False,
        help="Customer signature confirming work completion")
    customer_signed_by = fields.Char(
        string='Signed By',
        help="Name of person who signed")
    customer_signed_on = fields.Datetime(
        string='Signed On',
        help="Date/time when signature was captured")

    # FSM User (technician assigned)
    fsm_user_id = fields.Many2one(
        'res.users',
        string='Field Technician',
        domain=[('share', '=', False)],
        tracking=True,
        help="Technician assigned to this field service task")

    # Worksheets
    worksheet_template_id = fields.Many2one(
        'fsm.worksheet.template',
        string='Worksheet Template',
        help="Template for the worksheet to complete on-site")
    worksheet_data = fields.Json(
        string='Worksheet Data',
        help="Completed worksheet data in JSON format")
    worksheet_completed = fields.Boolean(
        string='Worksheet Completed',
        compute='_compute_worksheet_completed',
        store=True)

    # Materials/Products used
    material_line_ids = fields.One2many(
        'fsm.material.line',
        'task_id',
        string='Materials Used')
    material_cost = fields.Monetary(
        string='Materials Cost',
        compute='_compute_material_cost',
        currency_field='currency_id')

    # GPS check-in/out
    checkin_latitude = fields.Float(string='Check-in Latitude')
    checkin_longitude = fields.Float(string='Check-in Longitude')
    checkin_time = fields.Datetime(string='Check-in Time')
    checkin_address = fields.Char(string='Check-in Address')

    checkout_latitude = fields.Float(string='Check-out Latitude')
    checkout_longitude = fields.Float(string='Check-out Longitude')
    checkout_time = fields.Datetime(string='Check-out Time')

    # Work status
    fsm_done = fields.Boolean(
        string='Task Done',
        default=False,
        tracking=True,
        help="Mark when field service work is completed")

    # Time tracking
    total_hours_spent = fields.Float(
        string='Total Hours',
        compute='_compute_total_hours',
        store=True,
        help="Total hours logged from timesheets")

    # Company and currency
    currency_id = fields.Many2one(
        related='company_id.currency_id')

    @api.depends('worksheet_data')
    def _compute_worksheet_completed(self):
        for task in self:
            task.worksheet_completed = bool(task.worksheet_data)

    @api.depends('material_line_ids.subtotal')
    def _compute_material_cost(self):
        for task in self:
            task.material_cost = sum(task.material_line_ids.mapped('subtotal'))

    @api.depends('timesheet_ids.unit_amount')
    def _compute_total_hours(self):
        for task in self:
            task.total_hours_spent = sum(task.timesheet_ids.mapped('unit_amount'))

    @api.onchange('project_id')
    def _onchange_project_fsm(self):
        """Set is_fsm based on project when task is created."""
        if self.project_id and self.project_id.is_fsm:
            self.is_fsm = True
            if self.project_id.default_worksheet_template_id:
                self.worksheet_template_id = self.project_id.default_worksheet_template_id

    def action_timer_start(self):
        """Start the work timer for FSM task."""
        self.ensure_one()
        if not self.timer_start:
            self.timer_start = fields.Datetime.now()
        return True

    def action_timer_pause(self):
        """Pause the work timer for FSM task."""
        self.ensure_one()
        if self.timer_start and not self.timer_pause:
            self.timer_pause = fields.Datetime.now()
        return True

    def action_timer_resume(self):
        """Resume the work timer for FSM task."""
        self.ensure_one()
        if self.timer_pause:
            # Adjust timer_start to account for paused time
            pause_duration = fields.Datetime.now() - self.timer_pause
            self.timer_start = self.timer_start + pause_duration
            self.timer_pause = False
        return True

    def action_timer_stop(self):
        """Stop the work timer and return hours elapsed."""
        self.ensure_one()
        if not self.timer_start:
            return 0.0

        end_time = fields.Datetime.now()
        if self.timer_pause:
            end_time = self.timer_pause

        hours = (end_time - self.timer_start).total_seconds() / 3600

        self.write({
            'timer_start': False,
            'timer_pause': False,
        })
        return hours

    def action_fsm_checkin(self, latitude=None, longitude=None, address=None):
        """
        Record GPS check-in and start timer.

        Called from mobile interface with device GPS coordinates.
        """
        self.ensure_one()
        now = fields.Datetime.now()

        vals = {
            'checkin_time': now,
        }
        if latitude:
            vals['checkin_latitude'] = latitude
        if longitude:
            vals['checkin_longitude'] = longitude
        if address:
            vals['checkin_address'] = address

        self.write(vals)

        # Start timer
        self.action_timer_start()

        return True

    def action_fsm_checkout(self, latitude=None, longitude=None):
        """
        Record GPS check-out and stop timer.

        Creates timesheet entry from timer duration.
        """
        self.ensure_one()
        now = fields.Datetime.now()

        vals = {
            'checkout_time': now,
        }
        if latitude:
            vals['checkout_latitude'] = latitude
        if longitude:
            vals['checkout_longitude'] = longitude

        self.write(vals)

        # Stop timer and get hours
        hours = self.action_timer_stop()

        # Create timesheet entry if hours > 0
        if hours and hours > 0:
            self._create_timesheet_entry(hours)

        return True

    def _create_timesheet_entry(self, hours):
        """Create timesheet entry from FSM work."""
        self.ensure_one()

        employee = self.env.user.employee_id
        if not employee:
            return False

        # Find or create analytic account
        analytic_account = self.project_id.account_id
        if not analytic_account:
            # Create one if doesn't exist
            analytic_account = self.env['account.analytic.account'].create({
                'name': self.project_id.name,
                'company_id': self.company_id.id,
            })
            self.project_id.account_id = analytic_account

        self.env['account.analytic.line'].create({
            'task_id': self.id,
            'project_id': self.project_id.id,
            'account_id': analytic_account.id,
            'employee_id': employee.id,
            'name': _('FSM: %s') % self.name,
            'unit_amount': hours,
            'date': fields.Date.today(),
        })

        return True

    def action_fsm_mark_done(self):
        """Mark FSM task as done."""
        self.ensure_one()

        # Check if signature is required
        if self.is_fsm and not self.customer_signature:
            raise UserError(_("Please capture customer signature before marking task as done."))

        self.write({
            'fsm_done': True,
        })

        return True

    def action_save_signature(self, signature_data, signed_by=None):
        """
        Save customer signature from mobile interface.

        Args:
            signature_data: Base64 encoded PNG image
            signed_by: Name of person who signed
        """
        self.ensure_one()
        self.write({
            'customer_signature': signature_data,
            'customer_signed_by': signed_by,
            'customer_signed_on': fields.Datetime.now(),
        })
        return True

    def action_save_worksheet(self, worksheet_data):
        """
        Save worksheet data from mobile interface.

        Args:
            worksheet_data: Dict containing worksheet field values
        """
        self.ensure_one()
        self.write({
            'worksheet_data': worksheet_data,
        })
        return True

    def action_view_worksheet(self):
        """Open worksheet in a form for viewing/editing."""
        self.ensure_one()
        return {
            'name': _('Worksheet'),
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': {
                'form_view_ref': 'loomworks_fsm.project_task_view_form_worksheet',
            },
        }

    def action_open_maps(self):
        """Override to use partner geolocation."""
        self.ensure_one()
        lat = self.partner_latitude or (self.partner_id.partner_latitude if self.partner_id else 0)
        lng = self.partner_longitude or (self.partner_id.partner_longitude if self.partner_id else 0)

        if lat and lng:
            return {
                'type': 'ir.actions.act_url',
                'url': f'https://www.google.com/maps?q={lat},{lng}',
                'target': 'new',
            }
        elif self.partner_id:
            # Try to open maps with address
            address = self.partner_id._display_address(without_company=True)
            if address:
                return {
                    'type': 'ir.actions.act_url',
                    'url': f'https://www.google.com/maps/search/{address}',
                    'target': 'new',
                }

        raise UserError(_("No location information available for this task."))
