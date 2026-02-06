# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from loomworks.tests import TransactionCase, tagged
from loomworks.exceptions import UserError


@tagged('post_install', '-at_install', 'loomworks_skills')
class TestSkillRecording(TransactionCase):
    """Test cases for loomworks.skill.recording model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.SkillRecording = cls.env['loomworks.skill.recording']
        cls.RecordingAction = cls.env['loomworks.skill.recording.action']
        cls.Skill = cls.env['loomworks.skill']

        # Create test user
        cls.test_user = cls.env['res.users'].create({
            'name': 'Recording Test User',
            'login': 'rec_test_user',
            'email': 'rec_test@example.com',
        })

    def test_recording_create(self):
        """Test creating a recording."""
        recording = self.SkillRecording.create({
            'name': 'Test Recording',
            'user_id': self.test_user.id,
        })

        self.assertEqual(recording.state, 'recording')
        self.assertEqual(recording.user_id.id, self.test_user.id)
        self.assertIsNotNone(recording.started_at)

    def test_recording_stop(self):
        """Test stopping a recording."""
        recording = self.SkillRecording.create({
            'name': 'Stop Test Recording',
            'user_id': self.test_user.id,
        })

        recording.stop_recording()

        self.assertEqual(recording.state, 'stopped')
        self.assertIsNotNone(recording.stopped_at)

    def test_recording_duration_calculation(self):
        """Test duration calculation."""
        recording = self.SkillRecording.create({
            'name': 'Duration Test Recording',
            'user_id': self.test_user.id,
            'started_at': datetime.now() - timedelta(seconds=120),
        })

        recording.stop_recording()

        # Duration should be approximately 120 seconds
        self.assertGreaterEqual(recording.duration_seconds, 100)

    def test_recording_action_count(self):
        """Test action_count computed field."""
        recording = self.SkillRecording.create({
            'name': 'Action Count Test Recording',
            'user_id': self.test_user.id,
        })

        # Add actions
        self.RecordingAction.create({
            'recording_id': recording.id,
            'action_type': 'search',
            'model_name': 'res.partner',
            'method_name': 'search_read',
        })

        self.RecordingAction.create({
            'recording_id': recording.id,
            'action_type': 'create',
            'model_name': 'sale.order',
            'method_name': 'create',
        })

        recording.invalidate_recordset()
        self.assertEqual(recording.action_count, 2)

    def test_recording_capture_settings(self):
        """Test capture settings."""
        recording = self.SkillRecording.create({
            'name': 'Capture Settings Test',
            'user_id': self.test_user.id,
            'capture_field_changes': True,
            'capture_searches': True,
        })

        self.assertTrue(recording.capture_field_changes)
        self.assertTrue(recording.capture_searches)

    def test_recording_start_model(self):
        """Test start_model field."""
        recording = self.SkillRecording.create({
            'name': 'Start Model Test',
            'user_id': self.test_user.id,
            'start_model': 'sale.order',
        })

        self.assertEqual(recording.start_model, 'sale.order')

    def test_recording_user_inputs(self):
        """Test user_inputs JSON field."""
        inputs = {
            'customer_name': 'Test Corp',
            'product_selection': [1, 2, 3],
        }

        recording = self.SkillRecording.create({
            'name': 'User Inputs Test',
            'user_id': self.test_user.id,
            'user_inputs': json.dumps(inputs),
        })

        loaded = json.loads(recording.user_inputs)
        self.assertEqual(loaded['customer_name'], 'Test Corp')

    def test_recording_convert_to_skill(self):
        """Test converting recording to skill."""
        recording = self.SkillRecording.create({
            'name': 'Convert Test Recording',
            'user_id': self.test_user.id,
        })

        # Add some actions
        self.RecordingAction.create({
            'recording_id': recording.id,
            'action_type': 'search',
            'model_name': 'res.partner',
            'method_name': 'search_read',
            'parameters': json.dumps({
                'domain': [['customer_rank', '>', 0]],
            }),
        })

        self.RecordingAction.create({
            'recording_id': recording.id,
            'action_type': 'create',
            'model_name': 'sale.order',
            'method_name': 'create',
            'parameters': json.dumps({
                'partner_id': 1,
            }),
        })

        recording.stop_recording()

        # Convert to skill
        skill = recording.convert_to_skill()

        self.assertIsNotNone(skill)
        self.assertEqual(recording.state, 'converted')
        self.assertEqual(recording.generated_skill_id.id, skill.id)

    def test_recording_action_view_skill(self):
        """Test action_view_skill method."""
        recording = self.SkillRecording.create({
            'name': 'View Skill Test',
            'user_id': self.test_user.id,
        })

        recording.stop_recording()
        skill = recording.convert_to_skill()

        action = recording.action_view_skill()

        self.assertEqual(action['res_model'], 'loomworks.skill')
        self.assertEqual(action['res_id'], skill.id)

    def test_recording_failed_state(self):
        """Test recording failure handling."""
        recording = self.SkillRecording.create({
            'name': 'Failed Recording',
            'user_id': self.test_user.id,
            'state': 'failed',
            'error_message': 'Recording failed due to system error',
        })

        self.assertEqual(recording.state, 'failed')
        self.assertIn('system error', recording.error_message)


@tagged('post_install', '-at_install', 'loomworks_skills')
class TestSkillRecordingAction(TransactionCase):
    """Test cases for loomworks.skill.recording.action model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.SkillRecording = cls.env['loomworks.skill.recording']
        cls.RecordingAction = cls.env['loomworks.skill.recording.action']

        # Create test user
        cls.test_user = cls.env['res.users'].create({
            'name': 'Action Test User',
            'login': 'action_test_user',
            'email': 'action_test@example.com',
        })

        # Create test recording
        cls.test_recording = cls.SkillRecording.create({
            'name': 'Action Test Recording',
            'user_id': cls.test_user.id,
        })

    def test_action_create_search(self):
        """Test creating a search action."""
        action = self.RecordingAction.create({
            'recording_id': self.test_recording.id,
            'action_type': 'search',
            'model_name': 'res.partner',
            'method_name': 'search_read',
            'parameters': json.dumps({
                'domain': [['is_company', '=', True]],
                'fields': ['name', 'email'],
            }),
        })

        self.assertEqual(action.action_type, 'search')
        self.assertEqual(action.model_name, 'res.partner')
        self.assertIsNotNone(action.timestamp)

    def test_action_create_create(self):
        """Test creating a create action."""
        action = self.RecordingAction.create({
            'recording_id': self.test_recording.id,
            'action_type': 'create',
            'model_name': 'sale.order',
            'method_name': 'create',
            'parameters': json.dumps({
                'partner_id': 1,
                'date_order': '2024-01-15',
            }),
            'result': json.dumps({'id': 123}),
        })

        self.assertEqual(action.action_type, 'create')
        result = json.loads(action.result)
        self.assertEqual(result['id'], 123)

    def test_action_create_update(self):
        """Test creating an update action."""
        action = self.RecordingAction.create({
            'recording_id': self.test_recording.id,
            'action_type': 'update',
            'model_name': 'sale.order',
            'method_name': 'write',
            'record_ids': json.dumps([123]),
            'parameters': json.dumps({
                'state': 'sale',
            }),
        })

        self.assertEqual(action.action_type, 'update')
        record_ids = json.loads(action.record_ids)
        self.assertEqual(record_ids, [123])

    def test_action_create_delete(self):
        """Test creating a delete action."""
        action = self.RecordingAction.create({
            'recording_id': self.test_recording.id,
            'action_type': 'delete',
            'model_name': 'sale.order.line',
            'method_name': 'unlink',
            'record_ids': json.dumps([456, 789]),
        })

        self.assertEqual(action.action_type, 'delete')

    def test_action_create_workflow(self):
        """Test creating a workflow action."""
        action = self.RecordingAction.create({
            'recording_id': self.test_recording.id,
            'action_type': 'workflow',
            'model_name': 'sale.order',
            'method_name': 'action_confirm',
            'record_ids': json.dumps([123]),
        })

        self.assertEqual(action.action_type, 'workflow')
        self.assertEqual(action.method_name, 'action_confirm')

    def test_action_create_button(self):
        """Test creating a button action."""
        action = self.RecordingAction.create({
            'recording_id': self.test_recording.id,
            'action_type': 'button',
            'model_name': 'account.move',
            'method_name': 'action_post',
            'record_ids': json.dumps([100]),
        })

        self.assertEqual(action.action_type, 'button')

    def test_action_sequence(self):
        """Test action sequence ordering."""
        action1 = self.RecordingAction.create({
            'recording_id': self.test_recording.id,
            'action_type': 'search',
            'model_name': 'res.partner',
            'method_name': 'search',
            'sequence': 10,
        })

        action2 = self.RecordingAction.create({
            'recording_id': self.test_recording.id,
            'action_type': 'create',
            'model_name': 'sale.order',
            'method_name': 'create',
            'sequence': 20,
        })

        self.assertEqual(action1.sequence, 10)
        self.assertEqual(action2.sequence, 20)

    def test_action_duration_tracking(self):
        """Test action duration tracking."""
        action = self.RecordingAction.create({
            'recording_id': self.test_recording.id,
            'action_type': 'search',
            'model_name': 'res.partner',
            'method_name': 'search',
            'duration_ms': 150,
        })

        self.assertEqual(action.duration_ms, 150)

    def test_action_context_storage(self):
        """Test action context storage."""
        context = {
            'active_model': 'sale.order',
            'active_id': 123,
            'default_partner_id': 1,
        }

        action = self.RecordingAction.create({
            'recording_id': self.test_recording.id,
            'action_type': 'create',
            'model_name': 'sale.order.line',
            'method_name': 'create',
            'context': json.dumps(context),
        })

        loaded = json.loads(action.context)
        self.assertEqual(loaded['active_model'], 'sale.order')

    def test_action_field_changes(self):
        """Test field changes storage."""
        changes = {
            'name': {'old': 'Draft', 'new': 'Confirmed'},
            'state': {'old': 'draft', 'new': 'sale'},
        }

        action = self.RecordingAction.create({
            'recording_id': self.test_recording.id,
            'action_type': 'update',
            'model_name': 'sale.order',
            'method_name': 'write',
            'field_changes': json.dumps(changes),
        })

        loaded = json.loads(action.field_changes)
        self.assertEqual(loaded['state']['new'], 'sale')
