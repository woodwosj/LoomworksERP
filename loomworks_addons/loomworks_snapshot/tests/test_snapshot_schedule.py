# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Tests for Loomworks Snapshot Schedule functionality.
"""

from loomworks.tests import TransactionCase, tagged
from loomworks.exceptions import ValidationError
from datetime import timedelta


@tagged('post_install', '-at_install', 'loomworks', 'snapshot')
class TestSnapshotSchedule(TransactionCase):
    """Test cases for loomworks.snapshot.schedule model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Schedule = cls.env['loomworks.snapshot.schedule']
        cls.Snapshot = cls.env['loomworks.snapshot']

    def test_create_daily_schedule(self):
        """Test creating a daily snapshot schedule."""
        schedule = self.Schedule.create({
            'name': 'Daily Test Schedule',
            'interval_type': 'daily',
            'interval_number': 1,
            'execution_hour': 2,
            'execution_minute': 0,
            'retention_days': 7,
        })

        self.assertEqual(schedule.interval_type, 'daily')
        self.assertEqual(schedule.interval_number, 1)
        self.assertTrue(schedule.active)

    def test_schedule_run_creates_snapshot(self):
        """Test that running a schedule creates a snapshot."""
        schedule = self.Schedule.create({
            'name': 'Run Test Schedule',
            'interval_type': 'daily',
            'interval_number': 1,
            'retention_days': 7,
        })

        # Run the schedule
        snapshot = schedule._execute_schedule()

        self.assertTrue(snapshot)
        self.assertEqual(snapshot.snapshot_type, 'auto')
        self.assertEqual(snapshot.schedule_id, schedule)
        self.assertEqual(snapshot.state, 'ready')

        # Verify schedule was updated
        self.assertTrue(schedule.last_run)
        self.assertEqual(schedule.last_snapshot_id, snapshot)
        self.assertEqual(schedule.run_count, 1)

    def test_execution_hour_validation(self):
        """Test that invalid execution hour raises validation error."""
        with self.assertRaises(ValidationError):
            self.Schedule.create({
                'name': 'Invalid Hour',
                'interval_type': 'daily',
                'execution_hour': 25,  # Invalid
            })

    def test_execution_day_validation(self):
        """Test that invalid execution day raises validation error."""
        with self.assertRaises(ValidationError):
            self.Schedule.create({
                'name': 'Invalid Day',
                'interval_type': 'monthly',
                'execution_day': 32,  # Invalid
            })

    def test_max_snapshots_cleanup(self):
        """Test that excess snapshots are cleaned up."""
        schedule = self.Schedule.create({
            'name': 'Cleanup Test',
            'interval_type': 'hourly',
            'max_snapshots': 3,
            'retention_days': 30,
        })

        # Create more snapshots than max
        for i in range(5):
            schedule._execute_schedule()

        # Check that only max_snapshots are kept
        ready_snapshots = self.Snapshot.search([
            ('schedule_id', '=', schedule.id),
            ('state', '=', 'ready'),
        ])
        self.assertLessEqual(len(ready_snapshots), 3)


@tagged('post_install', '-at_install', 'loomworks', 'snapshot')
class TestSnapshotRetention(TransactionCase):
    """Test cases for loomworks.snapshot.retention model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Retention = cls.env['loomworks.snapshot.retention']
        cls.Snapshot = cls.env['loomworks.snapshot']

    def test_create_simple_retention(self):
        """Test creating a simple retention policy."""
        policy = self.Retention.create({
            'name': 'Simple Test Policy',
            'retention_type': 'simple',
            'retention_days': 14,
        })

        self.assertEqual(policy.retention_type, 'simple')
        self.assertEqual(policy.retention_days, 14)

    def test_create_tiered_retention(self):
        """Test creating a tiered (GFS) retention policy."""
        policy = self.Retention.create({
            'name': 'Tiered Test Policy',
            'retention_type': 'tiered',
            'hourly_retention_hours': 24,
            'daily_retention_days': 7,
            'weekly_retention_weeks': 4,
            'monthly_retention_months': 12,
        })

        self.assertEqual(policy.retention_type, 'tiered')
        self.assertEqual(policy.hourly_retention_hours, 24)

    def test_calculate_expiry_simple(self):
        """Test expiry calculation for simple retention."""
        policy = self.Retention.create({
            'name': 'Expiry Test',
            'retention_type': 'simple',
            'retention_days': 7,
            'apply_to_auto': True,
        })

        from loomworks import fields
        now = fields.Datetime.now()
        expiry = policy.calculate_expiry(snapshot_type='auto')

        # Should be approximately 7 days from now
        delta = expiry - now
        self.assertAlmostEqual(delta.days, 7, delta=1)

    def test_retention_type_filter(self):
        """Test that retention only applies to selected snapshot types."""
        policy = self.Retention.create({
            'name': 'Type Filter Test',
            'retention_type': 'simple',
            'retention_days': 7,
            'apply_to_auto': True,
            'apply_to_manual': False,
            'apply_to_pre_ai': False,
        })

        # Should return False for types not enabled
        self.assertFalse(policy.calculate_expiry(snapshot_type='manual'))
        self.assertFalse(policy.calculate_expiry(snapshot_type='pre_ai'))
        # Should return datetime for enabled type
        self.assertTrue(policy.calculate_expiry(snapshot_type='auto'))
