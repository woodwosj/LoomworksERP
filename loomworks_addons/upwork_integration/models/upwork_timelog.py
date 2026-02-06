# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Upwork Time Log model - Represents tracked hours on an Upwork contract.
"""

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class UpworkTimelog(models.Model):
    """Upwork Time Log synced from the Upwork API."""
    _name = 'upwork.timelog'
    _description = 'Upwork Time Log'
    _order = 'date desc'

    upwork_timelog_id = fields.Char(
        string='Upwork Timelog ID',
        index=True,
    )
    date = fields.Date(
        string='Date',
        required=True,
        index=True,
    )
    memo = fields.Text(
        string='Memo',
    )
    tracked_hours = fields.Float(
        string='Tracked Hours',
    )
    manual_hours = fields.Float(
        string='Manual Hours',
    )
    total_hours = fields.Float(
        string='Total Hours',
    )
    contract_id = fields.Many2one(
        'upwork.contract',
        string='Contract',
        required=True,
        ondelete='cascade',
        index=True,
    )
    upwork_account_id = fields.Many2one(
        'upwork.account',
        string='Upwork Account',
        ondelete='set null',
    )
    timesheet_id = fields.Many2one(
        'account.analytic.line',
        string='Timesheet Entry',
        ondelete='set null',
        index=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        (
            'upwork_timelog_upwork_timelog_unique',
            'UNIQUE(upwork_timelog_id, contract_id)',
            'Timelog ID must be unique per contract.',
        ),
        (
            'upwork_timelog_unique_timelog_per_contract_date',
            'UNIQUE(contract_id, date)',
            'Only one time log per contract per date.',
        ),
        (
            'upwork_timelog_timesheet_unique',
            'UNIQUE(timesheet_id)',
            'A timesheet entry can only be linked to one time log.',
        ),
    ]

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_create_timesheet(self):
        """Create an Odoo timesheet entry (account.analytic.line) from this time log."""
        self.ensure_one()
        if self.timesheet_id:
            raise UserError(_("A timesheet entry already exists for this time log."))

        contract = self.contract_id
        project = contract.project_id
        if not project:
            raise UserError(_(
                "Please assign a project to contract '%s' before creating timesheets.",
                contract.name
            ))

        # Find a task or use project default
        task = self.env['project.task'].search([
            ('project_id', '=', project.id),
        ], limit=1)

        vals = {
            'name': self.memo or f'Upwork: {contract.name}',
            'date': self.date,
            'unit_amount': self.total_hours or 0.0,
            'project_id': project.id,
            'company_id': self.company_id.id,
        }
        if task:
            vals['task_id'] = task.id

        timesheet = self.env['account.analytic.line'].create(vals)
        self.write({'timesheet_id': timesheet.id})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Timesheet Created"),
                'message': _("Created timesheet entry for %.2f hours.", self.total_hours),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_create_timesheets(self):
        """Batch create timesheets for multiple time logs. Called by server action."""
        created_count = 0
        errors = []
        for record in self:
            if record.timesheet_id:
                continue
            try:
                record.action_create_timesheet()
                created_count += 1
            except UserError as e:
                errors.append(f"{record.contract_id.name} ({record.date}): {e}")

        if errors:
            _logger.warning("Timesheet creation errors: %s", errors)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Timesheets Created"),
                'message': _("Created %d timesheet entries.", created_count),
                'type': 'success' if not errors else 'warning',
                'sticky': bool(errors),
            }
        }
