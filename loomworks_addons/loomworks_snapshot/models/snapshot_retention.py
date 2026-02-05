# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Snapshot Retention Policy Model

Provides configurable retention policies for snapshot lifecycle management,
including tiered retention (e.g., hourly for 24h, daily for 7d, weekly for 4w).
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class SnapshotRetention(models.Model):
    """
    Retention policy for snapshot lifecycle management.

    Policies define how long to keep snapshots based on their age,
    supporting tiered retention strategies.
    """
    _name = 'loomworks.snapshot.retention'
    _description = 'Snapshot Retention Policy'
    _order = 'sequence, name'

    name = fields.Char(
        string='Policy Name',
        required=True,
        help='Descriptive name for this retention policy'
    )
    active = fields.Boolean(
        string='Active',
        default=True
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
        help='Specific tenant for this policy (leave empty for global)'
    )

    # Basic retention settings
    retention_type = fields.Selection([
        ('simple', 'Simple (Days)'),
        ('tiered', 'Tiered Retention'),
        ('count', 'Count-Based'),
    ], string='Retention Type', required=True, default='simple')

    # Simple retention
    retention_days = fields.Integer(
        string='Retention Days',
        default=7,
        help='Number of days to keep snapshots'
    )

    # Count-based retention
    keep_last_n = fields.Integer(
        string='Keep Last N Snapshots',
        default=10,
        help='Number of most recent snapshots to keep'
    )

    # Tiered retention (e.g., Grandfather-Father-Son)
    hourly_retention_hours = fields.Integer(
        string='Hourly Retention (hours)',
        default=24,
        help='Keep hourly snapshots for this many hours'
    )
    daily_retention_days = fields.Integer(
        string='Daily Retention (days)',
        default=7,
        help='Keep daily snapshots for this many days'
    )
    weekly_retention_weeks = fields.Integer(
        string='Weekly Retention (weeks)',
        default=4,
        help='Keep weekly snapshots for this many weeks'
    )
    monthly_retention_months = fields.Integer(
        string='Monthly Retention (months)',
        default=12,
        help='Keep monthly snapshots for this many months'
    )

    # Snapshot type filtering
    apply_to_auto = fields.Boolean(
        string='Apply to Automatic',
        default=True,
        help='Apply this policy to automatic snapshots'
    )
    apply_to_manual = fields.Boolean(
        string='Apply to Manual',
        default=False,
        help='Apply this policy to manual snapshots'
    )
    apply_to_pre_ai = fields.Boolean(
        string='Apply to Pre-AI',
        default=True,
        help='Apply this policy to pre-AI operation snapshots'
    )

    # Storage limits
    max_storage_gb = fields.Float(
        string='Max Storage (GB)',
        default=0.0,
        help='Maximum storage to use for snapshots (0 for unlimited)'
    )

    # Cleanup configuration
    cleanup_batch_size = fields.Integer(
        string='Cleanup Batch Size',
        default=100,
        help='Number of snapshots to process per cleanup run'
    )

    # Statistics
    schedule_ids = fields.One2many(
        'loomworks.snapshot.schedule',
        'retention_policy_id',
        string='Schedules Using This Policy'
    )
    schedule_count = fields.Integer(
        string='Schedule Count',
        compute='_compute_schedule_count'
    )

    description = fields.Text(
        string='Description',
        help='Description of this retention policy'
    )

    @api.constrains('retention_days')
    def _check_retention_days(self):
        for policy in self:
            if policy.retention_type == 'simple' and policy.retention_days < 1:
                raise ValidationError("Retention days must be at least 1")

    @api.constrains('keep_last_n')
    def _check_keep_last_n(self):
        for policy in self:
            if policy.retention_type == 'count' and policy.keep_last_n < 1:
                raise ValidationError("Keep last N must be at least 1")

    def _compute_schedule_count(self):
        for policy in self:
            policy.schedule_count = len(policy.schedule_ids)

    def calculate_expiry(self, snapshot_type='auto'):
        """
        Calculate expiration date based on this policy.

        Args:
            snapshot_type: Type of snapshot ('auto', 'manual', 'pre_ai')

        Returns:
            datetime: Expiration datetime, or False for no expiration
        """
        self.ensure_one()

        # Check if policy applies to this snapshot type
        type_applies = {
            'auto': self.apply_to_auto,
            'manual': self.apply_to_manual,
            'pre_ai': self.apply_to_pre_ai,
        }
        if not type_applies.get(snapshot_type, False):
            return False  # No expiration for this type

        now = fields.Datetime.now()

        if self.retention_type == 'simple':
            return now + timedelta(days=self.retention_days)

        elif self.retention_type == 'tiered':
            # For tiered, use the longest applicable retention
            # The actual tiered cleanup happens in apply_retention()
            max_days = max(
                self.hourly_retention_hours / 24,
                self.daily_retention_days,
                self.weekly_retention_weeks * 7,
                self.monthly_retention_months * 30,
            )
            return now + timedelta(days=max_days)

        elif self.retention_type == 'count':
            # Count-based doesn't use expiry dates
            return False

        return False

    def apply_retention(self):
        """
        Apply this retention policy to all applicable snapshots.

        For tiered retention, this implements Grandfather-Father-Son (GFS)
        backup rotation.

        Returns:
            dict: Summary of actions taken
        """
        self.ensure_one()

        Snapshot = self.env['loomworks.snapshot']
        results = {
            'expired': 0,
            'kept': 0,
            'errors': [],
        }

        # Build domain for applicable snapshots
        domain = [('state', '=', 'ready')]

        if self.tenant_id:
            domain.append(('tenant_id', '=', self.tenant_id.id))

        # Filter by snapshot types
        type_filter = []
        if self.apply_to_auto:
            type_filter.append('auto')
        if self.apply_to_manual:
            type_filter.append('manual')
        if self.apply_to_pre_ai:
            type_filter.append('pre_ai')

        if type_filter:
            domain.append(('snapshot_type', 'in', type_filter))
        else:
            # No types selected, nothing to do
            return results

        snapshots = Snapshot.search(
            domain,
            order='create_date desc',
            limit=self.cleanup_batch_size
        )

        if self.retention_type == 'simple':
            results = self._apply_simple_retention(snapshots)
        elif self.retention_type == 'tiered':
            results = self._apply_tiered_retention(snapshots)
        elif self.retention_type == 'count':
            results = self._apply_count_retention(snapshots, domain)

        _logger.info(
            "Applied retention policy '%s': %d expired, %d kept",
            self.name, results['expired'], results['kept']
        )

        return results

    def _apply_simple_retention(self, snapshots):
        """Apply simple date-based retention."""
        results = {'expired': 0, 'kept': 0, 'errors': []}
        now = fields.Datetime.now()
        cutoff = now - timedelta(days=self.retention_days)

        for snapshot in snapshots:
            if snapshot.created_at < cutoff:
                try:
                    snapshot.action_mark_expired()
                    results['expired'] += 1
                except Exception as e:
                    results['errors'].append(str(e))
            else:
                results['kept'] += 1

        return results

    def _apply_tiered_retention(self, snapshots):
        """
        Apply tiered (GFS) retention.

        Keeps:
        - All snapshots within hourly_retention_hours
        - One per day within daily_retention_days
        - One per week within weekly_retention_weeks
        - One per month within monthly_retention_months
        """
        results = {'expired': 0, 'kept': 0, 'errors': []}
        now = fields.Datetime.now()

        # Define retention tiers
        tiers = {
            'hourly': now - timedelta(hours=self.hourly_retention_hours),
            'daily': now - timedelta(days=self.daily_retention_days),
            'weekly': now - timedelta(weeks=self.weekly_retention_weeks),
            'monthly': now - timedelta(days=self.monthly_retention_months * 30),
        }

        # Track which periods we've kept snapshots for
        kept_periods = {
            'daily': set(),
            'weekly': set(),
            'monthly': set(),
        }

        for snapshot in snapshots:
            keep = False
            created = snapshot.created_at

            # Within hourly retention - keep all
            if created >= tiers['hourly']:
                keep = True

            # Within daily retention - keep one per day
            elif created >= tiers['daily']:
                day_key = created.strftime('%Y-%m-%d')
                if day_key not in kept_periods['daily']:
                    kept_periods['daily'].add(day_key)
                    keep = True

            # Within weekly retention - keep one per week
            elif created >= tiers['weekly']:
                week_key = created.strftime('%Y-W%W')
                if week_key not in kept_periods['weekly']:
                    kept_periods['weekly'].add(week_key)
                    keep = True

            # Within monthly retention - keep one per month
            elif created >= tiers['monthly']:
                month_key = created.strftime('%Y-%m')
                if month_key not in kept_periods['monthly']:
                    kept_periods['monthly'].add(month_key)
                    keep = True

            if keep:
                results['kept'] += 1
            else:
                try:
                    snapshot.action_mark_expired()
                    results['expired'] += 1
                except Exception as e:
                    results['errors'].append(str(e))

        return results

    def _apply_count_retention(self, snapshots, domain):
        """Apply count-based retention (keep last N)."""
        results = {'expired': 0, 'kept': 0, 'errors': []}

        # Get all matching snapshots (not just batch)
        all_snapshots = self.env['loomworks.snapshot'].search(
            domain, order='create_date desc'
        )

        for i, snapshot in enumerate(all_snapshots):
            if i < self.keep_last_n:
                results['kept'] += 1
            else:
                try:
                    snapshot.action_mark_expired()
                    results['expired'] += 1
                except Exception as e:
                    results['errors'].append(str(e))

        return results

    @api.model
    def run_all_retention_policies(self):
        """
        Run all active retention policies.

        Called by scheduled action.
        """
        policies = self.search([('active', '=', True)])
        total_expired = 0
        total_kept = 0

        for policy in policies:
            try:
                result = policy.apply_retention()
                total_expired += result['expired']
                total_kept += result['kept']
            except Exception as e:
                _logger.exception(
                    "Failed to apply retention policy '%s': %s",
                    policy.name, e
                )

        _logger.info(
            "Retention cleanup complete: %d expired, %d kept",
            total_expired, total_kept
        )

        return {
            'total_expired': total_expired,
            'total_kept': total_kept,
        }
