# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

import json
from datetime import datetime
from unittest.mock import patch, MagicMock
from loomworks.tests import TransactionCase, tagged
from loomworks.exceptions import UserError


@tagged('post_install', '-at_install', 'loomworks_skills')
class TestSkillExecution(TransactionCase):
    """Test cases for loomworks.skill.execution model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Skill = cls.env['loomworks.skill']
        cls.SkillStep = cls.env['loomworks.skill.step']
        cls.SkillExecution = cls.env['loomworks.skill.execution']

        # Create test user
        cls.test_user = cls.env['res.users'].create({
            'name': 'Execution Test User',
            'login': 'exec_test_user',
            'email': 'exec_test@example.com',
        })

        # Create a test skill
        cls.test_skill = cls.Skill.create({
            'name': 'Execution Test Skill',
            'technical_name': 'execution_test_skill',
            'state': 'active',
        })

        # Add a simple step
        cls.test_step = cls.SkillStep.create({
            'skill_id': cls.test_skill.id,
            'name': 'Test Step',
            'sequence': 10,
            'step_type': 'tool_call',
            'tool_name': 'search_records',
        })

    def test_execution_create(self):
        """Test creating an execution record."""
        execution = self.SkillExecution.create({
            'skill_id': self.test_skill.id,
            'user_id': self.test_user.id,
            'trigger_text': 'Test trigger',
            'input_data': json.dumps({'customer': 'Test'}),
        })

        self.assertEqual(execution.state, 'pending')
        self.assertEqual(execution.skill_id.id, self.test_skill.id)
        self.assertEqual(execution.user_id.id, self.test_user.id)

    def test_execution_skill_name_computed(self):
        """Test skill_name computed field."""
        execution = self.SkillExecution.create({
            'skill_id': self.test_skill.id,
            'user_id': self.test_user.id,
        })

        self.assertEqual(execution.skill_name, 'Execution Test Skill')

    def test_execution_state_transitions(self):
        """Test execution state transitions."""
        execution = self.SkillExecution.create({
            'skill_id': self.test_skill.id,
            'user_id': self.test_user.id,
        })

        self.assertEqual(execution.state, 'pending')

        # Start execution
        execution.state = 'running'
        execution.started_at = datetime.now()
        self.assertEqual(execution.state, 'running')

        # Complete execution
        execution.state = 'completed'
        execution.completed_at = datetime.now()
        self.assertEqual(execution.state, 'completed')

    def test_execution_duration_calculation(self):
        """Test duration_ms calculation."""
        execution = self.SkillExecution.create({
            'skill_id': self.test_skill.id,
            'user_id': self.test_user.id,
            'state': 'running',
            'started_at': datetime.now(),
        })

        # Simulate completion
        execution.completed_at = datetime.now()
        execution.state = 'completed'

        # Duration should be calculated
        self.assertIsNotNone(execution.duration_ms)

    def test_execution_steps_progress(self):
        """Test steps progress tracking."""
        execution = self.SkillExecution.create({
            'skill_id': self.test_skill.id,
            'user_id': self.test_user.id,
            'steps_total': 5,
            'steps_completed': 2,
        })

        self.assertEqual(execution.steps_total, 5)
        self.assertEqual(execution.steps_completed, 2)

    def test_execution_input_output_data(self):
        """Test input/output data JSON fields."""
        input_data = {'customer_name': 'Test Corp', 'amount': 1500}
        output_data = {'order_id': 123, 'success': True}

        execution = self.SkillExecution.create({
            'skill_id': self.test_skill.id,
            'user_id': self.test_user.id,
            'input_data': json.dumps(input_data),
            'output_data': json.dumps(output_data),
        })

        loaded_input = json.loads(execution.input_data)
        loaded_output = json.loads(execution.output_data)

        self.assertEqual(loaded_input['customer_name'], 'Test Corp')
        self.assertEqual(loaded_output['order_id'], 123)

    def test_execution_failed_state(self):
        """Test execution failure handling."""
        execution = self.SkillExecution.create({
            'skill_id': self.test_skill.id,
            'user_id': self.test_user.id,
            'state': 'failed',
            'error_message': 'Test error: Something went wrong',
            'error_step_id': self.test_step.id,
        })

        self.assertEqual(execution.state, 'failed')
        self.assertIn('Something went wrong', execution.error_message)
        self.assertEqual(execution.error_step_id.id, self.test_step.id)

    def test_execution_waiting_input_state(self):
        """Test waiting_input state and pending input fields."""
        execution = self.SkillExecution.create({
            'skill_id': self.test_skill.id,
            'user_id': self.test_user.id,
            'state': 'waiting_input',
            'pending_input_prompt': 'Please select a customer:',
            'pending_input_type': 'record',
            'pending_input_variable': 'selected_customer',
        })

        self.assertEqual(execution.state, 'waiting_input')
        self.assertEqual(execution.pending_input_prompt, 'Please select a customer:')
        self.assertEqual(execution.pending_input_type, 'record')

    def test_execution_cancel(self):
        """Test cancelling an execution."""
        execution = self.SkillExecution.create({
            'skill_id': self.test_skill.id,
            'user_id': self.test_user.id,
            'state': 'running',
        })

        execution.cancel_execution()
        self.assertEqual(execution.state, 'cancelled')

    def test_execution_rollback_configuration(self):
        """Test rollback configuration fields."""
        execution = self.SkillExecution.create({
            'skill_id': self.test_skill.id,
            'user_id': self.test_user.id,
            'can_rollback': True,
            'rollback_mode': 'savepoint',
            'savepoint_name': 'skill_test_abc123',
        })

        self.assertTrue(execution.can_rollback)
        self.assertEqual(execution.rollback_mode, 'savepoint')
        self.assertEqual(execution.savepoint_name, 'skill_test_abc123')

    def test_execution_with_snapshot(self):
        """Test execution with snapshot ID."""
        execution = self.SkillExecution.create({
            'skill_id': self.test_skill.id,
            'user_id': self.test_user.id,
            'can_rollback': True,
            'rollback_mode': 'snapshot',
            'snapshot_id': 'snap_12345',
        })

        self.assertEqual(execution.rollback_mode, 'snapshot')
        self.assertEqual(execution.snapshot_id, 'snap_12345')

    def test_execution_session_tracking(self):
        """Test session_id tracking."""
        execution = self.SkillExecution.create({
            'skill_id': self.test_skill.id,
            'user_id': self.test_user.id,
            'session_id': 'session_abc123',
        })

        self.assertEqual(execution.session_id, 'session_abc123')

    def test_execution_result_summary(self):
        """Test result_summary field."""
        execution = self.SkillExecution.create({
            'skill_id': self.test_skill.id,
            'user_id': self.test_user.id,
            'state': 'completed',
            'result_summary': 'Successfully created quotation SO/001 for customer Test Corp',
        })

        self.assertIn('quotation', execution.result_summary)
        self.assertIn('Test Corp', execution.result_summary)

    def test_execution_current_step_tracking(self):
        """Test current_step_id tracking."""
        execution = self.SkillExecution.create({
            'skill_id': self.test_skill.id,
            'user_id': self.test_user.id,
            'state': 'running',
            'current_step_id': self.test_step.id,
        })

        self.assertEqual(execution.current_step_id.id, self.test_step.id)

    def test_execution_operation_count_computed(self):
        """Test operation_count computed field."""
        execution = self.SkillExecution.create({
            'skill_id': self.test_skill.id,
            'user_id': self.test_user.id,
        })

        # Without operation logs, count should be 0
        self.assertEqual(execution.operation_count, 0)

    def test_execution_search_by_trigger_text(self):
        """Test searching executions by trigger text."""
        execution1 = self.SkillExecution.create({
            'skill_id': self.test_skill.id,
            'user_id': self.test_user.id,
            'trigger_text': 'create a quote for Acme Corp',
        })

        execution2 = self.SkillExecution.create({
            'skill_id': self.test_skill.id,
            'user_id': self.test_user.id,
            'trigger_text': 'generate invoice',
        })

        # Search for Acme
        found = self.SkillExecution.search([
            ('trigger_text', 'ilike', 'Acme'),
        ])
        self.assertIn(execution1.id, found.ids)
        self.assertNotIn(execution2.id, found.ids)

    def test_execution_group_by_state(self):
        """Test grouping executions by state."""
        # Create multiple executions with different states
        self.SkillExecution.create({
            'skill_id': self.test_skill.id,
            'user_id': self.test_user.id,
            'state': 'completed',
        })

        self.SkillExecution.create({
            'skill_id': self.test_skill.id,
            'user_id': self.test_user.id,
            'state': 'completed',
        })

        self.SkillExecution.create({
            'skill_id': self.test_skill.id,
            'user_id': self.test_user.id,
            'state': 'failed',
        })

        # Read group by state
        groups = self.SkillExecution.read_group(
            [('skill_id', '=', self.test_skill.id)],
            ['state'],
            ['state'],
        )

        state_counts = {g['state']: g['state_count'] for g in groups}
        self.assertGreaterEqual(state_counts.get('completed', 0), 2)
        self.assertGreaterEqual(state_counts.get('failed', 0), 1)
