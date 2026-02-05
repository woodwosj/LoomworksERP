# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

import json
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError, UserError


@tagged('post_install', '-at_install', 'loomworks_skills')
class TestSkill(TransactionCase):
    """Test cases for loomworks.skill model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Skill = cls.env['loomworks.skill']
        cls.SkillStep = cls.env['loomworks.skill.step']

        # Create a test user
        cls.test_user = cls.env['res.users'].create({
            'name': 'Test Skills User',
            'login': 'test_skills_user',
            'email': 'test_skills@example.com',
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('loomworks_skills.group_skills_user').id,
            ])],
        })

    def test_skill_create_basic(self):
        """Test creating a basic skill."""
        skill = self.Skill.create({
            'name': 'Test Skill',
            'technical_name': 'test_skill',
            'description': 'A test skill for unit testing',
            'category': 'general',
        })

        self.assertEqual(skill.name, 'Test Skill')
        self.assertEqual(skill.technical_name, 'test_skill')
        self.assertEqual(skill.state, 'draft')
        self.assertFalse(skill.is_builtin)

    def test_skill_technical_name_generation(self):
        """Test automatic technical name generation."""
        skill = self.Skill.create({
            'name': 'My Amazing Skill With Spaces',
            'description': 'Test skill',
        })

        self.assertTrue(skill.technical_name)
        # Should not contain spaces
        self.assertNotIn(' ', skill.technical_name)

    def test_skill_trigger_phrases(self):
        """Test trigger phrases JSON field."""
        phrases = ['create a quote', 'make quotation', 'generate quote']
        skill = self.Skill.create({
            'name': 'Quote Skill',
            'technical_name': 'quote_skill',
            'trigger_phrases': json.dumps(phrases),
        })

        loaded_phrases = json.loads(skill.trigger_phrases)
        self.assertEqual(loaded_phrases, phrases)

    def test_skill_context_schema(self):
        """Test context schema validation."""
        schema = {
            'type': 'object',
            'properties': {
                'customer_name': {'type': 'string'},
                'amount': {'type': 'number'},
            },
            'required': ['customer_name'],
        }

        skill = self.Skill.create({
            'name': 'Schema Test Skill',
            'technical_name': 'schema_test',
            'context_schema': json.dumps(schema),
        })

        loaded_schema = json.loads(skill.context_schema)
        self.assertEqual(loaded_schema['type'], 'object')
        self.assertIn('customer_name', loaded_schema['properties'])

    def test_skill_state_transitions(self):
        """Test skill state transitions."""
        skill = self.Skill.create({
            'name': 'State Test Skill',
            'technical_name': 'state_test',
        })

        self.assertEqual(skill.state, 'draft')

        # Activate the skill
        skill.action_activate()
        self.assertEqual(skill.state, 'active')

        # Deactivate (deprecate) the skill
        skill.action_deactivate()
        self.assertEqual(skill.state, 'deprecated')

    def test_skill_with_steps(self):
        """Test skill with workflow steps."""
        skill = self.Skill.create({
            'name': 'Workflow Skill',
            'technical_name': 'workflow_skill',
        })

        # Add steps
        step1 = self.SkillStep.create({
            'skill_id': skill.id,
            'name': 'Step 1: Get Customer',
            'sequence': 10,
            'step_type': 'tool_call',
            'tool_name': 'search_records',
            'tool_parameters': json.dumps({
                'model': 'res.partner',
                'domain': [['name', 'ilike', '{customer_name}']],
            }),
            'output_variable': 'customer',
        })

        step2 = self.SkillStep.create({
            'skill_id': skill.id,
            'name': 'Step 2: Validate Customer',
            'sequence': 20,
            'step_type': 'validation',
            'condition_expression': 'len(customer) > 0',
        })

        self.assertEqual(len(skill.step_ids), 2)
        self.assertEqual(skill.step_ids[0].sequence, 10)
        self.assertEqual(skill.step_ids[1].sequence, 20)

    def test_skill_statistics(self):
        """Test skill statistics computation."""
        skill = self.Skill.create({
            'name': 'Stats Test Skill',
            'technical_name': 'stats_test',
        })

        self.assertEqual(skill.execution_count, 0)
        self.assertEqual(skill.success_count, 0)
        self.assertEqual(skill.success_rate, 0.0)

    def test_skill_duplicate(self):
        """Test skill duplication."""
        original = self.Skill.create({
            'name': 'Original Skill',
            'technical_name': 'original_skill',
            'description': 'Original description',
            'trigger_phrases': json.dumps(['original trigger']),
        })

        copy = original.copy()

        self.assertNotEqual(copy.id, original.id)
        self.assertIn('copy', copy.name.lower())
        self.assertNotEqual(copy.technical_name, original.technical_name)

    def test_skill_category_selection(self):
        """Test skill category field options."""
        valid_categories = ['general', 'sales', 'purchase', 'inventory',
                          'accounting', 'hr', 'project', 'crm', 'custom']

        for category in valid_categories:
            skill = self.Skill.create({
                'name': f'{category.title()} Category Skill',
                'technical_name': f'{category}_cat_skill',
                'category': category,
            })
            self.assertEqual(skill.category, category)

    def test_skill_owner_assignment(self):
        """Test skill owner assignment."""
        skill = self.Skill.with_user(self.test_user).create({
            'name': 'Owned Skill',
            'technical_name': 'owned_skill',
        })

        self.assertEqual(skill.owner_id.id, self.test_user.id)

    def test_skill_tools_configuration(self):
        """Test skill allowed tools configuration."""
        allowed = ['search_records', 'create_record', 'update_record']
        skill = self.Skill.create({
            'name': 'Tools Test Skill',
            'technical_name': 'tools_test',
            'allowed_tools': json.dumps(allowed),
        })

        loaded = json.loads(skill.allowed_tools)
        self.assertEqual(loaded, allowed)

    def test_skill_timeout_and_limits(self):
        """Test skill timeout and operation limits."""
        skill = self.Skill.create({
            'name': 'Limits Test Skill',
            'technical_name': 'limits_test',
            'timeout_seconds': 300,
            'max_operations': 50,
        })

        self.assertEqual(skill.timeout_seconds, 300)
        self.assertEqual(skill.max_operations, 50)

    def test_skill_confirmation_required(self):
        """Test skill requires confirmation flag."""
        skill = self.Skill.create({
            'name': 'Confirm Test Skill',
            'technical_name': 'confirm_test',
            'requires_confirmation': True,
        })

        self.assertTrue(skill.requires_confirmation)

    def test_skill_rollback_configuration(self):
        """Test skill rollback configuration."""
        skill = self.Skill.create({
            'name': 'Rollback Test Skill',
            'technical_name': 'rollback_test',
            'auto_snapshot': True,
            'rollback_on_failure': True,
        })

        self.assertTrue(skill.auto_snapshot)
        self.assertTrue(skill.rollback_on_failure)
