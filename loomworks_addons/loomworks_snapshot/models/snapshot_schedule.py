# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Snapshot Schedule Model - Automated Snapshot Creation

Provides configurable scheduled snapshots with various interval options
and retention policy integration.
"""

from loomworks import models, fields, api
from loomworks.exceptions import ValidationError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class SnapshotSchedule(models.Model):
    """
    Automated snapshot schedule configuration.

    Defines when and how often to create automatic snapshots,
    with optional retention policy integration.
    """
    _name = 'loomworks.snapshot.schedule'
    _description = 'Snapshot Schedule'
    _order = 'sequence, name'

    name = fields.Char(
        string='Schedule Name',
        required=True,
        help='Descriptive name for this schedule'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Whether this schedule is active'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )

    # Tenant relationship (optional)
    tenant_id = fields.Many2one(
        'loomworks.tenant',
        string='Tenant',
        ondelete='cascade',
        help='Specific tenant for this schedule (leave empty for all)'
    )

    # Schedule configuration
    interval_type = fields.Selection([
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('custom', 'Custom Cron'),
    ], string='Interval Type', required=True, default='daily')

    interval_number = fields.Integer(
        string='Interval Number',
        default=1,
        help='Number of intervals between snapshots'
    )

    # For daily/weekly/monthly schedules
    execution_hour = fields.Integer(
        string='Execution Hour (UTC)',
        default=2,
        help='Hour of day to run (0-23, UTC)'
    )
    execution_minute = fields.Integer(
        string='Execution Minute',
        default=0,
        help='Minute of hour to run (0-59)'
    )
    execution_weekday = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday'),
    ], string='Execution Day of Week', default='0')

    execution_day = fields.Integer(
        string='Execution Day of Month',
        default=1,
        help='Day of month to run (1-28)'
    )

    # Custom cron expression
    cron_expression = fields.Char(
        string='Cron Expression',
        help='Custom cron expression (for advanced scheduling)'
    )

    # Retention policy
    retention_policy_id = fields.Many2one(
        'loomworks.snapshot.retention',
        string='Retention Policy',
        help='Policy for how long to keep snapshots from this schedule'
    )
    retention_days = fields.Integer(
        string='Retention Days',
        default=7,
        help='Number of days to keep snapshots (if no policy specified)'
    )
    max_snapshots = fields.Integer(
        string='Max Snapshots',
        default=168,
        help='Maximum number of snapshots to keep (0 for unlimited)'
    )

    # Status tracking
    last_run = fields.Datetime(
        string='Last Run',
        readonly=True
    )
    next_run = fields.Datetime(
        string='Next Run',
        compute='_compute_next_run',
        store=True
    )
    last_snapshot_id = fields.Many2one(
        'loomworks.snapshot',
        string='Last Snapshot',
        readonly=True
    )
    run_count = fields.Integer(
        string='Run Count',
        default=0,
        readonly=True
    )
    error_count = fields.Integer(
        string='Error Count',
        default=0,
        readonly=True
    )
    last_error = fields.Text(
        string='Last Error',
        readonly=True
    )

    # Related snapshots
    snapshot_ids = fields.One2many(
        'loomworks.snapshot',
        'schedule_id',
        string='Snapshots'
    )
    snapshot_count = fields.Integer(
        string='Snapshot Count',
        compute='_compute_snapshot_count'
    )

    @api.constrains('execution_hour')
    def _check_execution_hour(self):
        for schedule in self:
            if not 0 <= schedule.execution_hour <= 23:
                raise ValidationError("Execution hour must be between 0 and 23")

    @api.constrains('execution_minute')
    def _check_execution_minute(self):
        for schedule in self:
            if not 0 <= schedule.execution_minute <= 59:
                raise ValidationError("Execution minute must be between 0 and 59")

    @api.constrains('execution_day')
    def _check_execution_day(self):
        for schedule in self:
            if schedule.interval_type == 'monthly' and not 1 <= schedule.execution_day <= 28:
                raise ValidationError("Execution day must be between 1 and 28")

    @api.depends('interval_type', 'interval_number', 'last_run')
    def _compute_next_run(self):
        for schedule in self:
            if not schedule.last_run:
                schedule.next_run = fields.Datetime.now()
                continue

            interval_map = {
                'hourly': timedelta(hours=schedule.interval_number),
                'daily': timedelta(days=schedule.interval_number),
                'weekly': timedelta(weeks=schedule.interval_number),
                'monthly': timedelta(days=30 * schedule.interval_number),
            }

            if schedule.interval_type in interval_map:
                schedule.next_run = schedule.last_run + interval_map[schedule.interval_type]
            else:
                schedule.next_run = fields.Datetime.now()

    def _compute_snapshot_count(self):
        for schedule in self:
            schedule.snapshot_count = len(schedule.snapshot_ids)

    def action_run_now(self):
        """
        Manually trigger this schedule to run immediately.
        """
        self.ensure_one()
        return self._execute_schedule()

    def _execute_schedule(self):
        """
        Execute this schedule - create a snapshot.

        Returns:
            loomworks.snapshot: The created snapshot record
        """
        self.ensure_one()

        Snapshot = self.env['loomworks.snapshot']

        try:
            # Calculate expiration
            if self.retention_policy_id:
                expires_at = self.retention_policy_id.calculate_expiry()
            else:
                expires_at = fields.Datetime.now() + timedelta(days=self.retention_days)

            # Create snapshot
            snapshot = Snapshot.create({
                'name': f"{self.name} - {fields.Datetime.now().strftime('%Y-%m-%d %H:%M')}",
                'snapshot_type': 'auto',
                'schedule_id': self.id,
                'tenant_id': self.tenant_id.id if self.tenant_id else False,
                'expires_at': expires_at,
                'description': f"Automatic snapshot from schedule: {self.name}",
            })

            # Execute snapshot creation
            snapshot.action_create_snapshot()

            # Update schedule status
            self.write({
                'last_run': fields.Datetime.now(),
                'last_snapshot_id': snapshot.id,
                'run_count': self.run_count + 1,
                'last_error': False,
            })

            # Cleanup old snapshots if max_snapshots is set
            if self.max_snapshots > 0:
                self._cleanup_excess_snapshots()

            _logger.info(
                "Schedule '%s' executed successfully, created snapshot '%s'",
                self.name, snapshot.name
            )

            return snapshot

        except Exception as e:
            self.write({
                'last_run': fields.Datetime.now(),
                'error_count': self.error_count + 1,
                'last_error': str(e),
            })
            _logger.exception(
                "Schedule '%s' failed to create snapshot: %s",
                self.name, e
            )
            raise

    def _cleanup_excess_snapshots(self):
        """
        Remove excess snapshots beyond max_snapshots limit.
        """
        self.ensure_one()

        if self.max_snapshots <= 0:
            return

        # Get snapshots from this schedule, ordered by creation date
        snapshots = self.env['loomworks.snapshot'].search([
            ('schedule_id', '=', self.id),
            ('state', '=', 'ready'),
        ], order='create_date desc')

        # Keep only max_snapshots, expire the rest
        if len(snapshots) > self.max_snapshots:
            to_expire = snapshots[self.max_snapshots:]
            for snapshot in to_expire:
                snapshot.action_mark_expired()
                _logger.info(
                    "Expired excess snapshot '%s' from schedule '%s'",
                    snapshot.name, self.name
                )

    @api.model
    def run_due_schedules(self):
        """
        Run all schedules that are due to execute.

        Called by scheduled action to process all active schedules.
        """
        now = fields.Datetime.now()
        due_schedules = self.search([
            ('active', '=', True),
            ('next_run', '<=', now),
        ])

        results = {
            'success': [],
            'failed': [],
        }

        for schedule in due_schedules:
            try:
                snapshot = schedule._execute_schedule()
                results['success'].append({
                    'schedule': schedule.name,
                    'snapshot': snapshot.name,
                })
            except Exception as e:
                results['failed'].append({
                    'schedule': schedule.name,
                    'error': str(e),
                })

        _logger.info(
            "Processed %d due schedules: %d success, %d failed",
            len(due_schedules),
            len(results['success']),
            len(results['failed'])
        )

        return results
