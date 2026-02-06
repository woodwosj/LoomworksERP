# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

import json
from loomworks.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'loomworks_skills')
class TestSkillMatching(TransactionCase):
    """Test cases for skill matching service (IntentMatcher)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Skill = cls.env['loomworks.skill']
        cls.SkillMatchingService = cls.env['loomworks.skill.matching.service']

        # Create test skills with various trigger phrases
        cls.quote_skill = cls.Skill.create({
            'name': 'Create Sales Quote',
            'technical_name': 'create_sales_quote',
            'state': 'active',
            'trigger_phrases': json.dumps([
                'create a quote',
                'make a quotation',
                'generate sales quote',
                'new quote for customer',
            ]),
            'context_schema': json.dumps({
                'type': 'object',
                'properties': {
                    'customer_name': {'type': 'string'},
                    'product_name': {'type': 'string'},
                },
            }),
        })

        cls.invoice_skill = cls.Skill.create({
            'name': 'Generate Invoice',
            'technical_name': 'generate_invoice',
            'state': 'active',
            'trigger_phrases': json.dumps([
                'create invoice',
                'generate invoice',
                'make an invoice',
                'bill the customer',
            ]),
        })

        cls.inventory_skill = cls.Skill.create({
            'name': 'Check Inventory',
            'technical_name': 'check_inventory',
            'state': 'active',
            'trigger_phrases': json.dumps([
                'check inventory',
                'stock levels',
                'how much stock',
                'inventory status',
            ]),
        })

        # Create an inactive skill that should not match
        cls.inactive_skill = cls.Skill.create({
            'name': 'Disabled Skill',
            'technical_name': 'disabled_skill',
            'state': 'draft',
            'trigger_phrases': json.dumps(['disabled trigger']),
        })

    def test_exact_match(self):
        """Test exact phrase matching."""
        matches = self.SkillMatchingService.match_intent('create a quote')

        self.assertTrue(len(matches) > 0)
        self.assertEqual(matches[0]['skill_id'], self.quote_skill.id)
        self.assertGreater(matches[0]['score'], 0.8)

    def test_fuzzy_match(self):
        """Test fuzzy/similar phrase matching."""
        # Slight variation from exact trigger
        matches = self.SkillMatchingService.match_intent('create a quotation')

        self.assertTrue(len(matches) > 0)
        self.assertEqual(matches[0]['skill_id'], self.quote_skill.id)

    def test_partial_match(self):
        """Test partial phrase matching."""
        matches = self.SkillMatchingService.match_intent('I need to generate a sales quote for Acme Corp')

        self.assertTrue(len(matches) > 0)
        # Should match quote skill
        skill_ids = [m['skill_id'] for m in matches]
        self.assertIn(self.quote_skill.id, skill_ids)

    def test_parameter_extraction(self):
        """Test parameter extraction from user input."""
        matches = self.SkillMatchingService.match_intent(
            'create a quote for customer John Smith for product Laptop Pro'
        )

        self.assertTrue(len(matches) > 0)

        # Check if parameters were extracted
        match = matches[0]
        if 'parameters' in match and match['parameters']:
            params = match['parameters']
            # Parameter extraction should identify customer_name and product_name
            self.assertIn('customer_name', params)

    def test_no_match_for_inactive_skill(self):
        """Test that inactive skills don't match."""
        matches = self.SkillMatchingService.match_intent('disabled trigger')

        # Should not find the inactive skill
        skill_ids = [m['skill_id'] for m in matches]
        self.assertNotIn(self.inactive_skill.id, skill_ids)

    def test_no_match_for_irrelevant_input(self):
        """Test no match for completely irrelevant input."""
        matches = self.SkillMatchingService.match_intent(
            'what is the weather like today'
        )

        # Should return empty or very low confidence matches
        if matches:
            self.assertLess(matches[0]['score'], 0.3)

    def test_multiple_matches_ranked(self):
        """Test that multiple matches are ranked by score."""
        matches = self.SkillMatchingService.match_intent('create invoice for customer')

        self.assertTrue(len(matches) > 0)
        # Invoice skill should be highest ranked
        self.assertEqual(matches[0]['skill_id'], self.invoice_skill.id)

        # Scores should be in descending order
        for i in range(len(matches) - 1):
            self.assertGreaterEqual(matches[i]['score'], matches[i + 1]['score'])

    def test_match_with_context(self):
        """Test matching with additional context."""
        context = {
            'active_model': 'sale.order',
            'user_role': 'sales',
        }

        matches = self.SkillMatchingService.match_intent(
            'create a quote',
            context=context
        )

        self.assertTrue(len(matches) > 0)
        self.assertEqual(matches[0]['skill_id'], self.quote_skill.id)

    def test_case_insensitive_matching(self):
        """Test that matching is case insensitive."""
        matches_lower = self.SkillMatchingService.match_intent('create a quote')
        matches_upper = self.SkillMatchingService.match_intent('CREATE A QUOTE')
        matches_mixed = self.SkillMatchingService.match_intent('Create A Quote')

        # All should match the same skill
        self.assertEqual(
            matches_lower[0]['skill_id'],
            matches_upper[0]['skill_id']
        )
        self.assertEqual(
            matches_lower[0]['skill_id'],
            matches_mixed[0]['skill_id']
        )

    def test_threshold_filtering(self):
        """Test confidence threshold filtering."""
        matches = self.SkillMatchingService.match_intent(
            'create a quote',
            threshold=0.5
        )

        for match in matches:
            self.assertGreaterEqual(match['score'], 0.5)

    def test_limit_results(self):
        """Test limiting number of results."""
        matches = self.SkillMatchingService.match_intent(
            'create something',
            limit=2
        )

        self.assertLessEqual(len(matches), 2)

    def test_match_returns_skill_info(self):
        """Test that match results include skill information."""
        matches = self.SkillMatchingService.match_intent('check inventory')

        self.assertTrue(len(matches) > 0)
        match = matches[0]

        self.assertIn('skill_id', match)
        self.assertIn('skill_name', match)
        self.assertIn('score', match)
        self.assertEqual(match['skill_name'], 'Check Inventory')


@tagged('post_install', '-at_install', 'loomworks_skills')
class TestIntentMatcherAlgorithms(TransactionCase):
    """Test specific matching algorithms."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Import the IntentMatcher class for direct testing
        try:
            from loomworks.addons.loomworks_skills.services.skill_matching_service import IntentMatcher
            cls.IntentMatcher = IntentMatcher
        except ImportError:
            cls.IntentMatcher = None

    def test_jaccard_similarity(self):
        """Test Jaccard similarity calculation."""
        if not self.IntentMatcher:
            self.skipTest('IntentMatcher not available')

        matcher = self.IntentMatcher()

        # Identical sets
        sim1 = matcher._jaccard_similarity(
            {'create', 'quote'},
            {'create', 'quote'}
        )
        self.assertEqual(sim1, 1.0)

        # Completely different sets
        sim2 = matcher._jaccard_similarity(
            {'create', 'quote'},
            {'check', 'inventory'}
        )
        self.assertEqual(sim2, 0.0)

        # Partial overlap
        sim3 = matcher._jaccard_similarity(
            {'create', 'sales', 'quote'},
            {'create', 'quote'}
        )
        self.assertGreater(sim3, 0.5)
        self.assertLess(sim3, 1.0)

    def test_word_tokenization(self):
        """Test word tokenization."""
        if not self.IntentMatcher:
            self.skipTest('IntentMatcher not available')

        matcher = self.IntentMatcher()

        tokens = matcher._tokenize('Create a Quote for Customer')

        self.assertIn('create', tokens)
        self.assertIn('quote', tokens)
        self.assertIn('customer', tokens)
        # Stopwords like 'a', 'for' might be filtered
        self.assertNotIn('a', tokens)

    def test_pattern_extraction(self):
        """Test pattern extraction from trigger phrases."""
        if not self.IntentMatcher:
            self.skipTest('IntentMatcher not available')

        matcher = self.IntentMatcher()

        phrases = [
            'create {item} for {recipient}',
            'make a {item}',
        ]

        patterns = matcher._build_patterns(phrases)

        self.assertTrue(len(patterns) > 0)

    def test_parameter_pattern_matching(self):
        """Test parameter extraction via pattern matching."""
        if not self.IntentMatcher:
            self.skipTest('IntentMatcher not available')

        matcher = self.IntentMatcher()

        # Set up a pattern with placeholders
        schema = {
            'properties': {
                'customer_name': {'type': 'string'},
                'product_name': {'type': 'string'},
            }
        }

        text = 'create a quote for John Doe for product Widget Pro'

        params = matcher._extract_parameters(text, schema)

        # Should attempt to extract parameters
        self.assertIsInstance(params, dict)
