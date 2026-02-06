# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

import json
from unittest.mock import patch, MagicMock, PropertyMock
from loomworks.tests import TransactionCase, tagged
from loomworks.exceptions import UserError


@tagged('post_install', '-at_install', 'loomworks_skills')
class TestRollbackManager(TransactionCase):
    """Test cases for RollbackManager with graceful degradation (M3)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Skill = cls.env['loomworks.skill']
        cls.SkillExecution = cls.env['loomworks.skill.execution']

        # Import RollbackManager
        try:
            from loomworks.addons.loomworks_skills.services.rollback_manager import RollbackManager
            cls.RollbackManager = RollbackManager
        except ImportError:
            cls.RollbackManager = None

        # Create test skill
        cls.test_skill = cls.Skill.create({
            'name': 'Rollback Test Skill',
            'technical_name': 'rollback_test_skill',
            'state': 'active',
            'auto_snapshot': True,
            'rollback_on_failure': True,
        })

    def test_rollback_manager_initialization(self):
        """Test RollbackManager initialization."""
        if not self.RollbackManager:
            self.skipTest('RollbackManager not available')

        manager = self.RollbackManager(self.env)

        self.assertIsNotNone(manager)

    def test_snapshot_availability_check(self):
        """Test snapshot availability detection."""
        if not self.RollbackManager:
            self.skipTest('RollbackManager not available')

        manager = self.RollbackManager(self.env)

        # snapshot_available should return boolean
        available = manager.snapshot_available

        self.assertIsInstance(available, bool)

    def test_savepoint_creation_without_snapshots(self):
        """Test savepoint creation when snapshots unavailable."""
        if not self.RollbackManager:
            self.skipTest('RollbackManager not available')

        # Mock snapshot unavailable
        with patch.object(self.RollbackManager, 'snapshot_available',
                         new_callable=PropertyMock, return_value=False):
            manager = self.RollbackManager(self.env)

            savepoint_id = manager.create_savepoint('test_operation')

            # Should return a savepoint name
            self.assertIsNotNone(savepoint_id)
            self.assertIn('skill_', savepoint_id)

    def test_savepoint_rollback_without_snapshots(self):
        """Test savepoint rollback when snapshots unavailable."""
        if not self.RollbackManager:
            self.skipTest('RollbackManager not available')

        with patch.object(self.RollbackManager, 'snapshot_available',
                         new_callable=PropertyMock, return_value=False):
            manager = self.RollbackManager(self.env)

            # Create savepoint
            savepoint_id = manager.create_savepoint('test_rollback')

            # Should be able to rollback
            result = manager.rollback(savepoint_id)

            self.assertTrue(result)

    def test_savepoint_release_without_snapshots(self):
        """Test savepoint release when snapshots unavailable."""
        if not self.RollbackManager:
            self.skipTest('RollbackManager not available')

        with patch.object(self.RollbackManager, 'snapshot_available',
                         new_callable=PropertyMock, return_value=False):
            manager = self.RollbackManager(self.env)

            # Create savepoint
            savepoint_id = manager.create_savepoint('test_release')

            # Should be able to release
            result = manager.release(savepoint_id)

            self.assertTrue(result)

    def test_snapshot_creation_when_available(self):
        """Test snapshot creation when Phase 5 snapshots available."""
        if not self.RollbackManager:
            self.skipTest('RollbackManager not available')

        # Mock snapshot service
        mock_snapshot_service = MagicMock()
        mock_snapshot_service.create_pre_ai_snapshot.return_value = 'snap_12345'

        with patch.object(self.RollbackManager, 'snapshot_available',
                         new_callable=PropertyMock, return_value=True):
            with patch.object(self.RollbackManager, 'snapshot_service',
                            new_callable=PropertyMock, return_value=mock_snapshot_service):
                manager = self.RollbackManager(self.env)

                result = manager.create_savepoint('test_snapshot')

                # Should call snapshot service
                mock_snapshot_service.create_pre_ai_snapshot.assert_called_once()
                self.assertEqual(result, 'snap_12345')

    def test_snapshot_rollback_when_available(self):
        """Test snapshot rollback when Phase 5 snapshots available."""
        if not self.RollbackManager:
            self.skipTest('RollbackManager not available')

        mock_snapshot_service = MagicMock()
        mock_snapshot_service.restore_snapshot.return_value = True

        with patch.object(self.RollbackManager, 'snapshot_available',
                         new_callable=PropertyMock, return_value=True):
            with patch.object(self.RollbackManager, 'snapshot_service',
                            new_callable=PropertyMock, return_value=mock_snapshot_service):
                manager = self.RollbackManager(self.env)

                result = manager.rollback('snap_12345', mode='snapshot')

                mock_snapshot_service.restore_snapshot.assert_called_once_with('snap_12345')
                self.assertTrue(result)

    def test_graceful_degradation_fallback(self):
        """Test graceful degradation - falls back to savepoint."""
        if not self.RollbackManager:
            self.skipTest('RollbackManager not available')

        manager = self.RollbackManager(self.env)

        # Regardless of snapshot availability, should work
        savepoint = manager.create_savepoint('degradation_test')
        self.assertIsNotNone(savepoint)

        # Should be able to rollback
        result = manager.rollback(savepoint)
        self.assertTrue(result)

    def test_rollback_mode_detection(self):
        """Test automatic rollback mode detection."""
        if not self.RollbackManager:
            self.skipTest('RollbackManager not available')

        manager = self.RollbackManager(self.env)

        # Savepoint IDs start with 'skill_'
        mode1 = manager.detect_mode('skill_test_abc123')
        self.assertEqual(mode1, 'savepoint')

        # Snapshot IDs start with 'snap_'
        mode2 = manager.detect_mode('snap_12345')
        self.assertEqual(mode2, 'snapshot')

    def test_multiple_savepoints(self):
        """Test multiple nested savepoints."""
        if not self.RollbackManager:
            self.skipTest('RollbackManager not available')

        with patch.object(self.RollbackManager, 'snapshot_available',
                         new_callable=PropertyMock, return_value=False):
            manager = self.RollbackManager(self.env)

            # Create multiple savepoints
            sp1 = manager.create_savepoint('step_1')
            sp2 = manager.create_savepoint('step_2')
            sp3 = manager.create_savepoint('step_3')

            # All should be unique
            self.assertNotEqual(sp1, sp2)
            self.assertNotEqual(sp2, sp3)
            self.assertNotEqual(sp1, sp3)

            # Should be able to rollback to middle savepoint
            result = manager.rollback(sp2)
            self.assertTrue(result)

    def test_execution_rollback_integration(self):
        """Test rollback integration with skill execution."""
        execution = self.SkillExecution.create({
            'skill_id': self.test_skill.id,
            'user_id': self.env.user.id,
            'can_rollback': True,
            'rollback_mode': 'savepoint',
            'savepoint_name': 'skill_test_integration',
        })

        # Verify execution has rollback capability
        self.assertTrue(execution.can_rollback)
        self.assertEqual(execution.rollback_mode, 'savepoint')

    def test_rollback_disabled_skill(self):
        """Test skill without rollback enabled."""
        skill_no_rollback = self.Skill.create({
            'name': 'No Rollback Skill',
            'technical_name': 'no_rollback_skill',
            'state': 'active',
            'auto_snapshot': False,
            'rollback_on_failure': False,
        })

        execution = self.SkillExecution.create({
            'skill_id': skill_no_rollback.id,
            'user_id': self.env.user.id,
            'can_rollback': False,
        })

        self.assertFalse(execution.can_rollback)


@tagged('post_install', '-at_install', 'loomworks_skills')
class TestRollbackManagerEdgeCases(TransactionCase):
    """Test edge cases for RollbackManager."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            from loomworks.addons.loomworks_skills.services.rollback_manager import RollbackManager
            cls.RollbackManager = RollbackManager
        except ImportError:
            cls.RollbackManager = None

    def test_rollback_invalid_savepoint(self):
        """Test rollback with invalid savepoint ID."""
        if not self.RollbackManager:
            self.skipTest('RollbackManager not available')

        manager = self.RollbackManager(self.env)

        # Rolling back invalid savepoint should handle gracefully
        result = manager.rollback('invalid_savepoint_name')

        # Should return False or handle error gracefully
        self.assertFalse(result)

    def test_release_invalid_savepoint(self):
        """Test release with invalid savepoint ID."""
        if not self.RollbackManager:
            self.skipTest('RollbackManager not available')

        manager = self.RollbackManager(self.env)

        # Releasing invalid savepoint should handle gracefully
        result = manager.release('invalid_savepoint_name')

        # Should return False or handle error gracefully
        self.assertFalse(result)

    def test_double_rollback(self):
        """Test attempting to rollback same savepoint twice."""
        if not self.RollbackManager:
            self.skipTest('RollbackManager not available')

        with patch.object(self.RollbackManager, 'snapshot_available',
                         new_callable=PropertyMock, return_value=False):
            manager = self.RollbackManager(self.env)

            savepoint = manager.create_savepoint('double_rollback')

            # First rollback should succeed
            result1 = manager.rollback(savepoint)
            self.assertTrue(result1)

            # Second rollback should fail or be a no-op
            result2 = manager.rollback(savepoint)
            self.assertFalse(result2)

    def test_concurrent_savepoints(self):
        """Test handling of concurrent savepoint operations."""
        if not self.RollbackManager:
            self.skipTest('RollbackManager not available')

        with patch.object(self.RollbackManager, 'snapshot_available',
                         new_callable=PropertyMock, return_value=False):
            manager1 = self.RollbackManager(self.env)
            manager2 = self.RollbackManager(self.env)

            # Create savepoints from different managers
            sp1 = manager1.create_savepoint('concurrent_1')
            sp2 = manager2.create_savepoint('concurrent_2')

            # Both should be unique
            self.assertNotEqual(sp1, sp2)

    def test_empty_operation_name(self):
        """Test savepoint creation with empty operation name."""
        if not self.RollbackManager:
            self.skipTest('RollbackManager not available')

        manager = self.RollbackManager(self.env)

        # Should handle empty name gracefully
        savepoint = manager.create_savepoint('')

        self.assertIsNotNone(savepoint)
        self.assertIn('skill_', savepoint)

    def test_special_characters_in_name(self):
        """Test savepoint with special characters in name."""
        if not self.RollbackManager:
            self.skipTest('RollbackManager not available')

        manager = self.RollbackManager(self.env)

        # Should sanitize special characters
        savepoint = manager.create_savepoint('test-operation.name!@#')

        self.assertIsNotNone(savepoint)
        # Should not contain invalid characters for SQL identifiers
        self.assertNotIn('!', savepoint)
        self.assertNotIn('@', savepoint)
        self.assertNotIn('#', savepoint)
