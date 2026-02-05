# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PlanningSlot(models.Model):
    """Planning slot representing a scheduled shift or assignment."""
    _name = 'planning.slot'
    _description = 'Planning Slot'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_datetime'

    name = fields.Char(compute='_compute_name', store=True)

    # Resource assignment
    resource_id = fields.Many2one(
        'resource.resource',
        string='Resource',
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        compute='_compute_employee',
        store=True,
        readonly=False,
        tracking=True,
    )
    user_id = fields.Many2one(
        'res.users',
        related='employee_id.user_id',
        string='User',
        store=True,
    )

    # Timing
    start_datetime = fields.Datetime(
        string='Start',
        required=True,
        tracking=True,
        default=fields.Datetime.now,
    )
    end_datetime = fields.Datetime(
        string='End',
        required=True,
        tracking=True,
    )
    allocated_hours = fields.Float(
        compute='_compute_allocated_hours',
        store=True,
        string='Allocated Hours',
    )

    # Allocation percentage (for partial assignments)
    allocated_percentage = fields.Float(
        string='Allocation %',
        default=100.0,
        help='Percentage of time allocated for this slot',
    )

    # Role/Position
    role_id = fields.Many2one(
        'planning.role',
        string='Role',
        tracking=True,
    )

    # Project/Task link
    project_id = fields.Many2one('project.project', string='Project')
    task_id = fields.Many2one(
        'project.task',
        string='Task',
        domain="[('project_id', '=', project_id)]",
    )

    # Recurrence
    recurrence_id = fields.Many2one(
        'planning.recurrence',
        string='Recurrence',
        ondelete='set null',
    )
    is_recurring = fields.Boolean(
        compute='_compute_is_recurring',
        store=True,
    )
    recurrency_update = fields.Selection([
        ('this', 'This Shift Only'),
        ('subsequent', 'This and Following'),
        ('all', 'All Occurrences'),
    ], default='this', string='Update')

    # Template
    template_id = fields.Many2one(
        'planning.slot.template',
        string='Template',
    )

    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True, string='Status')

    # Publication
    is_published = fields.Boolean(default=False)
    publication_warning = fields.Boolean(
        compute='_compute_publication_warning',
        string='Has Warnings',
    )

    # Conflict detection
    has_conflict = fields.Boolean(
        compute='_compute_conflicts',
        store=True,
        string='Has Conflict',
    )
    conflict_description = fields.Char(
        compute='_compute_conflicts',
        store=True,
        string='Conflict Details',
    )

    # Progress (for Gantt view)
    progress = fields.Float(
        compute='_compute_progress',
        store=True,
    )

    # Notes
    note = fields.Text(string='Notes')

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    color = fields.Integer(
        related='role_id.color',
        string='Color Index',
    )

    # Display fields
    display_name_short = fields.Char(
        compute='_compute_display_name_short',
        string='Short Name',
    )

    @api.depends('employee_id', 'role_id', 'start_datetime')
    def _compute_name(self):
        for slot in self:
            parts = []
            if slot.employee_id:
                parts.append(slot.employee_id.name)
            if slot.role_id:
                parts.append(slot.role_id.name)
            if slot.start_datetime:
                parts.append(slot.start_datetime.strftime('%Y-%m-%d'))
            slot.name = ' - '.join(parts) if parts else _('New Slot')

    @api.depends('resource_id', 'resource_id.employee_id')
    def _compute_employee(self):
        for slot in self:
            if slot.resource_id and slot.resource_id.employee_id:
                slot.employee_id = slot.resource_id.employee_id
            elif not slot.employee_id:
                slot.employee_id = False

    @api.depends('start_datetime', 'end_datetime')
    def _compute_allocated_hours(self):
        for slot in self:
            if slot.start_datetime and slot.end_datetime:
                delta = slot.end_datetime - slot.start_datetime
                slot.allocated_hours = delta.total_seconds() / 3600
            else:
                slot.allocated_hours = 0

    @api.depends('recurrence_id')
    def _compute_is_recurring(self):
        for slot in self:
            slot.is_recurring = bool(slot.recurrence_id)

    @api.depends('state')
    def _compute_progress(self):
        for slot in self:
            if slot.state == 'done':
                slot.progress = 100
            elif slot.state == 'published':
                slot.progress = 50
            else:
                slot.progress = 0

    @api.depends('has_conflict', 'employee_id')
    def _compute_publication_warning(self):
        for slot in self:
            slot.publication_warning = slot.has_conflict or not slot.employee_id

    @api.depends('employee_id', 'start_datetime', 'end_datetime')
    def _compute_conflicts(self):
        for slot in self:
            slot.has_conflict = False
            slot.conflict_description = False

            if not slot.employee_id or not slot.start_datetime or not slot.end_datetime:
                continue

            # Check overlapping slots
            overlapping = self.search([
                ('id', '!=', slot.id),
                ('employee_id', '=', slot.employee_id.id),
                ('state', 'not in', ['cancelled']),
                ('start_datetime', '<', slot.end_datetime),
                ('end_datetime', '>', slot.start_datetime),
            ])

            if overlapping:
                slot.has_conflict = True
                conflict_times = []
                for other in overlapping:
                    conflict_times.append(
                        f"{other.start_datetime.strftime('%H:%M')}-{other.end_datetime.strftime('%H:%M')}"
                    )
                slot.conflict_description = _(
                    'Overlaps with: %s'
                ) % ', '.join(conflict_times)
                continue

            # Check time off
            if slot.employee_id.user_id:
                time_off = self.env['hr.leave'].search([
                    ('employee_id', '=', slot.employee_id.id),
                    ('state', '=', 'validate'),
                    ('date_from', '<=', slot.end_datetime),
                    ('date_to', '>=', slot.start_datetime),
                ], limit=1)

                if time_off:
                    slot.has_conflict = True
                    slot.conflict_description = _(
                        'Employee on time off: %s'
                    ) % time_off.holiday_status_id.name

    @api.depends('employee_id', 'role_id')
    def _compute_display_name_short(self):
        for slot in self:
            if slot.employee_id and slot.role_id:
                slot.display_name_short = f"{slot.employee_id.name[:10]} - {slot.role_id.name}"
            elif slot.employee_id:
                slot.display_name_short = slot.employee_id.name
            elif slot.role_id:
                slot.display_name_short = slot.role_id.name
            else:
                slot.display_name_short = _('Unassigned')

    @api.constrains('employee_id', 'start_datetime', 'end_datetime', 'state')
    def _check_overlap_published(self):
        """Prevent publishing slots with conflicts."""
        for slot in self:
            if slot.has_conflict and slot.state == 'published':
                raise ValidationError(_(
                    "Cannot publish slot with conflicts: %s"
                ) % slot.conflict_description)

    @api.constrains('start_datetime', 'end_datetime')
    def _check_dates(self):
        for slot in self:
            if slot.start_datetime and slot.end_datetime:
                if slot.end_datetime <= slot.start_datetime:
                    raise ValidationError(_(
                        'End datetime must be after start datetime.'
                    ))

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id and self.employee_id.resource_id:
            self.resource_id = self.employee_id.resource_id

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            template = self.template_id
            self.role_id = template.role_id
            self.project_id = template.project_id
            self.task_id = template.task_id

            if template.employee_id:
                self.employee_id = template.employee_id

            # Set times based on template
            if self.start_datetime:
                date = self.start_datetime.date()
                start_hour = int(template.start_time)
                start_min = int((template.start_time % 1) * 60)
                self.start_datetime = datetime.combine(
                    date,
                    datetime.min.time()
                ) + timedelta(hours=start_hour, minutes=start_min)
                self.end_datetime = self.start_datetime + timedelta(hours=template.duration)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Set end_datetime if not provided but duration is known
            if 'end_datetime' not in vals and vals.get('start_datetime') and vals.get('template_id'):
                template = self.env['planning.slot.template'].browse(vals['template_id'])
                start_dt = fields.Datetime.from_string(vals['start_datetime'])
                vals['end_datetime'] = start_dt + timedelta(hours=template.duration)

        return super().create(vals_list)

    def action_publish(self):
        """Publish slots to make them visible to employees."""
        for slot in self:
            if slot.has_conflict:
                raise ValidationError(_(
                    "Cannot publish slot '%s' with conflicts: %s"
                ) % (slot.name, slot.conflict_description))

        self.write({
            'state': 'published',
            'is_published': True,
        })

        # Send notification to employees
        for slot in self:
            if slot.employee_id and slot.employee_id.user_id:
                slot.message_post(
                    body=_('You have been assigned to: %s') % slot.name,
                    partner_ids=[slot.employee_id.user_id.partner_id.id],
                    message_type='notification',
                )

    def action_unpublish(self):
        """Unpublish slots (return to draft)."""
        self.write({
            'state': 'draft',
            'is_published': False,
        })

    def action_mark_done(self):
        """Mark slot as completed."""
        self.write({'state': 'done'})

    def action_cancel(self):
        """Cancel the slot."""
        self.write({'state': 'cancelled'})

    def action_draft(self):
        """Reset to draft state."""
        self.write({
            'state': 'draft',
            'is_published': False,
        })

    def action_copy_to_next_week(self):
        """Copy selected slots to next week."""
        new_slots = self.env['planning.slot']
        for slot in self:
            new_start = slot.start_datetime + timedelta(weeks=1)
            new_end = slot.end_datetime + timedelta(weeks=1)
            new_slots |= slot.copy({
                'start_datetime': new_start,
                'end_datetime': new_end,
                'state': 'draft',
                'is_published': False,
            })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Copied Slots'),
            'res_model': 'planning.slot',
            'view_mode': 'calendar,list,form',
            'domain': [('id', 'in', new_slots.ids)],
        }
