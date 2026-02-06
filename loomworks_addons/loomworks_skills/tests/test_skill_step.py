# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

import json
from loomworks.tests import TransactionCase, tagged
from loomworks.exceptions import ValidationError


@tagged('post_install', '-at_install', 'loomworks_skills')
class TestSkillStep(TransactionCase):
    """Test cases for loomworks.skill.step model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Skill = cls.env['loomworks.skill']
        cls.SkillStep = cls.env['loomworks.skill.step']

        # Create a test skill
        cls.test_skill = cls.Skill.create({
            'name': 'Test Skill for Steps',
            'technical_name': 'test_skill_steps',
        })

    def test_step_create_tool_call(self):
        """Test creating a tool_call type step."""
        step = self.SkillStep.create({
            'skill_id': self.test_skill.id,
            'name': 'Search Customer',
            'sequence': 10,
            'step_type': 'tool_call',
            'tool_name': 'search_records',
            'tool_parameters': json.dumps({
                'model': 'res.partner',
                'domain': [['customer_rank', '>', 0]],
            }),
            'output_variable': 'customers',
        })

        self.assertEqual(step.step_type, 'tool_call')
        self.assertEqual(step.tool_name, 'search_records')
        self.assertEqual(step.output_variable, 'customers')

    def test_step_create_user_input(self):
        """Test creating a user_input type step."""
        step = self.SkillStep.create({
            'skill_id': self.test_skill.id,
            'name': 'Get Customer Name',
            'sequence': 10,
            'step_type': 'user_input',
            'input_prompt': 'Please enter the customer name:',
            'input_type': 'text',
            'input_required': True,
            'output_variable': 'customer_name',
        })

        self.assertEqual(step.step_type, 'user_input')
        self.assertEqual(step.input_type, 'text')
        self.assertTrue(step.input_required)

    def test_step_create_condition(self):
        """Test creating a condition type step."""
        # Create target steps first
        success_step = self.SkillStep.create({
            'skill_id': self.test_skill.id,
            'name': 'Success Branch',
            'sequence': 30,
            'step_type': 'tool_call',
            'tool_name': 'create_record',
        })

        failure_step = self.SkillStep.create({
            'skill_id': self.test_skill.id,
            'name': 'Failure Branch',
            'sequence': 40,
            'step_type': 'tool_call',
            'tool_name': 'send_notification',
        })

        condition_step = self.SkillStep.create({
            'skill_id': self.test_skill.id,
            'name': 'Check Amount',
            'sequence': 20,
            'step_type': 'condition',
            'condition_expression': 'amount > 1000',
            'on_success_step_id': success_step.id,
            'on_failure_step_id': failure_step.id,
        })

        self.assertEqual(condition_step.step_type, 'condition')
        self.assertEqual(condition_step.on_success_step_id.id, success_step.id)
        self.assertEqual(condition_step.on_failure_step_id.id, failure_step.id)

    def test_step_create_loop(self):
        """Test creating a loop type step."""
        step = self.SkillStep.create({
            'skill_id': self.test_skill.id,
            'name': 'Process Each Product',
            'sequence': 10,
            'step_type': 'loop',
            'loop_collection_expr': 'products',
            'loop_variable_name': 'product',
        })

        self.assertEqual(step.step_type, 'loop')
        self.assertEqual(step.loop_collection_expr, 'products')
        self.assertEqual(step.loop_variable_name, 'product')

    def test_step_create_validation(self):
        """Test creating a validation type step."""
        rules = {
            'customer_name': {'required': True, 'min_length': 2},
            'quantity': {'required': True, 'min': 1},
        }

        step = self.SkillStep.create({
            'skill_id': self.test_skill.id,
            'name': 'Validate Input',
            'sequence': 10,
            'step_type': 'validation',
            'condition_expression': 'customer_name and quantity > 0',
            'validation_rules': json.dumps(rules),
        })

        self.assertEqual(step.step_type, 'validation')
        loaded_rules = json.loads(step.validation_rules)
        self.assertIn('customer_name', loaded_rules)

    def test_step_create_confirmation(self):
        """Test creating a confirmation type step."""
        step = self.SkillStep.create({
            'skill_id': self.test_skill.id,
            'name': 'Confirm Creation',
            'sequence': 10,
            'step_type': 'confirmation',
            'input_prompt': 'Do you want to proceed with creating the order?',
        })

        self.assertEqual(step.step_type, 'confirmation')
        self.assertIn('proceed', step.input_prompt)

    def test_step_create_subskill(self):
        """Test creating a subskill type step."""
        # Create a subskill
        subskill = self.Skill.create({
            'name': 'Sub Skill',
            'technical_name': 'sub_skill',
        })

        step = self.SkillStep.create({
            'skill_id': self.test_skill.id,
            'name': 'Execute Sub Skill',
            'sequence': 10,
            'step_type': 'subskill',
            'subskill_id': subskill.id,
            'subskill_context_mapping': json.dumps({
                'customer': 'current_customer',
            }),
        })

        self.assertEqual(step.step_type, 'subskill')
        self.assertEqual(step.subskill_id.id, subskill.id)

    def test_step_create_action(self):
        """Test creating an action type step."""
        step = self.SkillStep.create({
            'skill_id': self.test_skill.id,
            'name': 'Open Form',
            'sequence': 10,
            'step_type': 'action',
            'action_context': json.dumps({'active_model': 'res.partner'}),
        })

        self.assertEqual(step.step_type, 'action')

    def test_step_create_ai_decision(self):
        """Test creating an ai_decision type step."""
        step = self.SkillStep.create({
            'skill_id': self.test_skill.id,
            'name': 'AI Decides Next Action',
            'sequence': 10,
            'step_type': 'ai_decision',
            'instructions': 'Analyze the customer data and decide whether to offer a discount.',
        })

        self.assertEqual(step.step_type, 'ai_decision')
        self.assertIn('discount', step.instructions)

    def test_step_sequence_ordering(self):
        """Test step sequence ordering."""
        step3 = self.SkillStep.create({
            'skill_id': self.test_skill.id,
            'name': 'Step 3',
            'sequence': 30,
            'step_type': 'tool_call',
        })

        step1 = self.SkillStep.create({
            'skill_id': self.test_skill.id,
            'name': 'Step 1',
            'sequence': 10,
            'step_type': 'tool_call',
        })

        step2 = self.SkillStep.create({
            'skill_id': self.test_skill.id,
            'name': 'Step 2',
            'sequence': 20,
            'step_type': 'tool_call',
        })

        # Refresh skill to get ordered steps
        self.test_skill.invalidate_recordset()
        steps = self.test_skill.step_ids
        self.assertEqual(steps[0].name, 'Step 1')
        self.assertEqual(steps[1].name, 'Step 2')
        self.assertEqual(steps[2].name, 'Step 3')

    def test_step_critical_flag(self):
        """Test step is_critical flag."""
        step = self.SkillStep.create({
            'skill_id': self.test_skill.id,
            'name': 'Critical Step',
            'sequence': 10,
            'step_type': 'tool_call',
            'is_critical': True,
        })

        self.assertTrue(step.is_critical)

    def test_step_retry_configuration(self):
        """Test step retry configuration."""
        step = self.SkillStep.create({
            'skill_id': self.test_skill.id,
            'name': 'Retry Step',
            'sequence': 10,
            'step_type': 'tool_call',
            'retry_count': 3,
            'retry_delay_seconds': 5,
        })

        self.assertEqual(step.retry_count, 3)
        self.assertEqual(step.retry_delay_seconds, 5)

    def test_step_rollback_on_failure(self):
        """Test step rollback_on_failure flag."""
        step = self.SkillStep.create({
            'skill_id': self.test_skill.id,
            'name': 'Rollback Step',
            'sequence': 10,
            'step_type': 'tool_call',
            'rollback_on_failure': True,
        })

        self.assertTrue(step.rollback_on_failure)

    def test_step_output_transform(self):
        """Test step output transformation."""
        step = self.SkillStep.create({
            'skill_id': self.test_skill.id,
            'name': 'Transform Step',
            'sequence': 10,
            'step_type': 'tool_call',
            'tool_name': 'search_records',
            'output_variable': 'customer_id',
            'output_transform': 'output[0].id if output else None',
        })

        self.assertEqual(step.output_transform, 'output[0].id if output else None')

    def test_step_error_message_template(self):
        """Test step error message template."""
        step = self.SkillStep.create({
            'skill_id': self.test_skill.id,
            'name': 'Error Step',
            'sequence': 10,
            'step_type': 'tool_call',
            'error_message_template': 'Failed to find customer: {error}',
        })

        self.assertIn('{error}', step.error_message_template)

    def test_step_input_selection_options(self):
        """Test step input selection options."""
        options = ['Option A', 'Option B', 'Option C']
        step = self.SkillStep.create({
            'skill_id': self.test_skill.id,
            'name': 'Select Option',
            'sequence': 10,
            'step_type': 'user_input',
            'input_type': 'selection',
            'input_options': json.dumps(options),
        })

        loaded = json.loads(step.input_options)
        self.assertEqual(loaded, options)

    def test_step_input_record_type(self):
        """Test step input record type configuration."""
        partner_model = self.env['ir.model'].search([('model', '=', 'res.partner')], limit=1)

        step = self.SkillStep.create({
            'skill_id': self.test_skill.id,
            'name': 'Select Partner',
            'sequence': 10,
            'step_type': 'user_input',
            'input_type': 'record',
            'input_model_id': partner_model.id,
            'input_domain': "[('customer_rank', '>', 0)]",
        })

        self.assertEqual(step.input_type, 'record')
        self.assertEqual(step.input_model_id.model, 'res.partner')

    def test_step_active_flag(self):
        """Test step active flag for disabling steps."""
        step = self.SkillStep.create({
            'skill_id': self.test_skill.id,
            'name': 'Disabled Step',
            'sequence': 10,
            'step_type': 'tool_call',
            'active': False,
        })

        self.assertFalse(step.active)

        # Verify disabled steps are excluded by default
        active_steps = self.SkillStep.search([
            ('skill_id', '=', self.test_skill.id),
        ])
        self.assertNotIn(step.id, active_steps.ids)
