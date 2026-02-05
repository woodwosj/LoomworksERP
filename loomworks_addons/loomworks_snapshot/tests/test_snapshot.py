# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Tests for Loomworks Snapshot functionality.
"""

from odoo.tests import TransactionCase, tagged
from odoo.exceptions import UserError
from datetime import timedelta


@tagged('post_install', '-at_install', 'loomworks', 'snapshot')
class TestSnapshot(TransactionCase):
    """Test cases for loomworks.snapshot model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Snapshot = cls.env['loomworks.snapshot']
        cls.SnapshotService = cls.env['loomworks.snapshot.service']

    def test_create_manual_snapshot(self):
        """Test creating a manual snapshot."""
        snapshot = self.Snapshot.create({
            'name': 'Test Manual Snapshot',
            'snapshot_type': 'manual',
            'description': 'Test description',
        })

        self.assertEqual(snapshot.name, 'Test Manual Snapshot')
        self.assertEqual(snapshot.snapshot_type, 'manual')
        self.assertEqual(snapshot.state, 'creating')
        self.assertEqual(snapshot.database_name, self.env.cr.dbname)

    def test_create_snapshot_captures_wal_position(self):
        """Test that creating snapshot captures WAL position."""
        snapshot = self.Snapshot.create({
            'name': 'WAL Test Snapshot',
            'snapshot_type': 'manual',
        })

        # Execute snapshot creation
        snapshot.action_create_snapshot()

        # Verify WAL position captured
        self.assertTrue(snapshot.wal_position)
        self.assertTrue(snapshot.wal_file)
        self.assertEqual(snapshot.state, 'ready')
        self.assertTrue(snapshot.database_size_bytes > 0)

    def test_snapshot_display_name(self):
        """Test snapshot display name computation."""
        snapshot = self.Snapshot.create({
            'name': 'Display Name Test',
            'snapshot_type': 'pre_ai',
        })

        self.assertIn('[Pre-AI Operation]', snapshot.display_name)
        self.assertIn('Display Name Test', snapshot.display_name)

    def test_cannot_restore_creating_snapshot(self):
        """Test that restoring a snapshot in 'creating' state raises error."""
        snapshot = self.Snapshot.create({
            'name': 'Incomplete Snapshot',
            'snapshot_type': 'manual',
        })

        with self.assertRaises(UserError):
            snapshot.action_restore()

    def test_create_pre_ai_snapshot(self):
        """Test creating pre-AI operation snapshot via helper method."""
        snapshot = self.Snapshot.create_pre_ai_snapshot(
            operation_name='Test Operation'
        )

        self.assertIn('Pre-AI', snapshot.name)
        self.assertIn('Test Operation', snapshot.name)
        self.assertEqual(snapshot.snapshot_type, 'pre_ai')
        self.assertEqual(snapshot.state, 'ready')

    def test_mark_snapshot_expired(self):
        """Test marking snapshot as expired."""
        snapshot = self.Snapshot.create({
            'name': 'Expire Test',
            'snapshot_type': 'manual',
        })
        snapshot.action_create_snapshot()

        snapshot.action_mark_expired()
        self.assertEqual(snapshot.state, 'expired')

    def test_cannot_delete_restoring_snapshot(self):
        """Test that deleting a restoring snapshot raises error."""
        snapshot = self.Snapshot.create({
            'name': 'Delete Test',
            'snapshot_type': 'manual',
        })
        snapshot.action_create_snapshot()
        snapshot.write({'state': 'restoring'})

        with self.assertRaises(UserError):
            snapshot.unlink()


@tagged('post_install', '-at_install', 'loomworks', 'snapshot')
class TestSnapshotService(TransactionCase):
    """Test cases for snapshot service."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.service = cls.env['loomworks.snapshot.service']

    def test_service_create_snapshot(self):
        """Test snapshot creation via service."""
        result = self.service.create_snapshot(
            name='Service Test',
            snapshot_type='manual'
        )

        self.assertTrue(result['success'])
        self.assertIn('snapshot', result)
        self.assertEqual(result['snapshot']['type'], 'manual')
        self.assertEqual(result['snapshot']['state'], 'ready')

    def test_service_list_snapshots(self):
        """Test listing snapshots via service."""
        # Create some test snapshots
        self.service.create_snapshot(name='List Test 1', snapshot_type='manual')
        self.service.create_snapshot(name='List Test 2', snapshot_type='auto')

        result = self.service.list_snapshots(state='ready')

        self.assertTrue(result['success'])
        self.assertGreaterEqual(result['count'], 2)
        self.assertTrue(all(s['state'] == 'ready' for s in result['snapshots']))

    def test_service_get_snapshot_status(self):
        """Test getting snapshot status via service."""
        create_result = self.service.create_snapshot(
            name='Status Test',
            snapshot_type='manual'
        )
        snapshot_id = create_result['snapshot']['id']

        result = self.service.get_snapshot_status(snapshot_id)

        self.assertTrue(result['success'])
        self.assertEqual(result['snapshot']['id'], snapshot_id)
        self.assertTrue(result['snapshot']['wal_position'])

    def test_service_pitr_status(self):
        """Test checking PITR configuration status."""
        result = self.service.get_pitr_status()

        self.assertIn('wal_level', result)
        self.assertIn('archive_mode', result)
        self.assertIn('current_wal_lsn', result)
        self.assertIn('warnings', result)
