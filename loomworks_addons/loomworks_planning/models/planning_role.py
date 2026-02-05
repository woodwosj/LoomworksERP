# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PlanningRole(models.Model):
    """Planning role for categorizing shifts and assignments."""
    _name = 'planning.role'
    _description = 'Planning Role'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(string='Code', help='Short identifier for the role')
    sequence = fields.Integer(default=10)
    color = fields.Integer(string='Color Index', default=0)

    # Role requirements
    description = fields.Text(string='Description', translate=True)
    skill_ids = fields.Many2many(
        'hr.skill',
        string='Required Skills',
        help='Skills employees should have for this role',
    )

    # Default hours
    default_hours = fields.Float(
        string='Default Hours',
        default=8.0,
        help='Default shift duration for this role',
    )

    # Hourly rate (for planning/costing)
    hourly_rate = fields.Monetary(
        string='Hourly Rate',
        currency_field='currency_id',
        help='Standard hourly rate for this role',
    )
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)

    # Statistics
    slot_count = fields.Integer(compute='_compute_slot_count')

    @api.depends()
    def _compute_slot_count(self):
        for role in self:
            role.slot_count = self.env['planning.slot'].search_count([
                ('role_id', '=', role.id),
            ])

    def action_view_slots(self):
        """Open planning slots for this role."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Slots - {self.name}',
            'res_model': 'planning.slot',
            'view_mode': 'gantt,list,form',
            'domain': [('role_id', '=', self.id)],
            'context': {'default_role_id': self.id},
        }
