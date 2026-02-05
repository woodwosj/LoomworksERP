# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Skill Matching Service - Natural Language Intent Matching

This service matches user natural language input against available skills
using multiple strategies:
1. Exact phrase matching with placeholders
2. Fuzzy string matching (token overlap)
3. Keyword extraction and parameter matching
4. Context schema-based parameter extraction

The matching algorithm combines these strategies with weighted scoring
to find the best matching skill.
"""

import json
import re
import logging
from difflib import SequenceMatcher

_logger = logging.getLogger(__name__)


class SkillMatchingService:
    """
    Multi-strategy intent matching for skill activation.

    Combines fuzzy string matching, pattern matching, and keyword extraction
    for robust natural language matching.
    """

    def __init__(self, env):
        """
        Initialize the matching service.

        :param env: Odoo environment
        """
        self.env = env

    def match_skill(self, user_input, domain=None):
        """
        Find the best matching skill for natural language input.

        :param user_input: Natural language text from user
        :param domain: Optional domain to filter available skills
        :return: Dict with skill_id, confidence, params, suggestions
        """
        # Get active skills
        skills = self.env['loomworks.skill'].search([
            ('state', '=', 'active'),
        ] + (domain or []))

        if not skills:
            return {
                'skill_id': None,
                'confidence': 0,
                'params': {},
                'suggestions': [],
                'message': 'No active skills available',
            }

        # Find best match
        best_skill, confidence, params = self._find_best_match(user_input, skills)

        # Generate suggestions for low confidence matches
        suggestions = []
        if not best_skill or confidence < 0.5:
            suggestions = self._get_suggestions(user_input, skills)

        return {
            'skill_id': best_skill.id if best_skill else None,
            'skill_name': best_skill.name if best_skill else None,
            'confidence': confidence,
            'params': params,
            'suggestions': suggestions,
        }

    def _find_best_match(self, user_input, skills):
        """
        Find the best matching skill from a set.

        :param user_input: User input text
        :param skills: Recordset of skills to match against
        :return: Tuple of (skill, confidence, extracted_params)
        """
        candidates = []
        user_input_lower = user_input.lower().strip()
        user_input_tokens = set(user_input_lower.split())

        for skill in skills:
            trigger_phrases = skill.get_trigger_phrases()
            if not trigger_phrases:
                continue

            # Stage 1: Pattern and fuzzy matching against triggers
            best_phrase_score = 0
            best_phrase_params = {}

            for phrase in trigger_phrases:
                phrase_lower = phrase.lower().strip()

                # Try exact pattern match (with placeholders)
                pattern_result = self._pattern_match(user_input_lower, phrase_lower)
                if pattern_result['match']:
                    best_phrase_score = max(best_phrase_score, pattern_result['score'])
                    if pattern_result['params']:
                        best_phrase_params.update(pattern_result['params'])
                    continue

                # Fuzzy matching
                fuzzy_score = self._fuzzy_match(user_input_lower, phrase_lower)
                best_phrase_score = max(best_phrase_score, fuzzy_score)

            if best_phrase_score < 0.1:
                # No meaningful match for this skill
                continue

            # Stage 2: Extract parameters from context schema
            extracted_params = self._extract_parameters(
                user_input, skill.get_context_schema()
            )
            extracted_params.update(best_phrase_params)

            # Stage 3: Calculate coverage score
            required = skill.get_required_context()
            if required:
                param_coverage = len(
                    set(extracted_params.keys()) & set(required)
                ) / len(required)
            else:
                param_coverage = 1.0

            # Weighted combination
            combined_score = (
                best_phrase_score * 0.6 +
                param_coverage * 0.3 +
                (0.1 if skill.is_builtin else 0)  # Slight boost for built-in skills
            )

            # Apply threshold
            if combined_score >= skill.trigger_confidence_threshold:
                candidates.append((skill, combined_score, extracted_params))

        if not candidates:
            return (None, 0, {})

        # Return best match
        best = max(candidates, key=lambda x: x[1])
        return best

    def _pattern_match(self, user_input, phrase_template):
        """
        Match user input against a phrase template with placeholders.

        Placeholders like {customer_name} are replaced with capture groups.

        :param user_input: Normalized user input
        :param phrase_template: Template with {placeholder} markers
        :return: Dict with match status, score, and extracted params
        """
        # Extract placeholder names
        placeholders = re.findall(r'\{(\w+)\}', phrase_template)

        if not placeholders:
            # No placeholders - check for substring match
            if phrase_template in user_input:
                return {'match': True, 'score': 1.0, 'params': {}}
            return {'match': False, 'score': 0, 'params': {}}

        # Build regex pattern
        pattern = re.escape(phrase_template)
        for ph in placeholders:
            pattern = pattern.replace(re.escape('{' + ph + '}'), r'(.+?)')

        try:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                params = {}
                for idx, ph in enumerate(placeholders):
                    params[ph] = match.group(idx + 1).strip()
                return {'match': True, 'score': 1.0, 'params': params}
        except re.error:
            pass

        return {'match': False, 'score': 0, 'params': {}}

    def _fuzzy_match(self, user_input, phrase):
        """
        Calculate fuzzy match score between user input and phrase.

        Uses a combination of:
        - Token overlap (Jaccard similarity)
        - Sequence matching (SequenceMatcher)

        :param user_input: Normalized user input
        :param phrase: Normalized phrase to match
        :return: Score between 0 and 1
        """
        # Remove placeholders for matching
        phrase_clean = re.sub(r'\{[^}]+\}', '', phrase).strip()
        phrase_tokens = set(phrase_clean.split())

        if not phrase_tokens:
            return 0

        user_tokens = set(user_input.split())

        # Token overlap (Jaccard)
        if user_tokens and phrase_tokens:
            intersection = user_tokens & phrase_tokens
            union = user_tokens | phrase_tokens
            jaccard = len(intersection) / len(union) if union else 0
        else:
            jaccard = 0

        # Sequence similarity
        sequence_score = SequenceMatcher(None, user_input, phrase_clean).ratio()

        # Weighted combination
        return jaccard * 0.5 + sequence_score * 0.5

    def _extract_parameters(self, user_input, schema):
        """
        Extract parameters from user input based on context schema.

        :param user_input: Original user input
        :param schema: JSON Schema defining parameters
        :return: Dict of extracted parameter values
        """
        if not schema:
            return {}

        extracted = {}
        properties = schema.get('properties', {})

        for param_name, param_def in properties.items():
            value = None

            # Try explicit extraction patterns
            patterns = param_def.get('extraction_patterns', [])
            for pattern in patterns:
                try:
                    match = re.search(pattern, user_input, re.IGNORECASE)
                    if match:
                        value = match.group(1) if match.groups() else match.group()
                        break
                except re.error:
                    continue

            # Try hint-based extraction
            if not value:
                hints = param_def.get('extraction_hints', [])
                for hint in hints:
                    # Pattern: hint word followed by a value
                    hint_pattern = rf'\b{re.escape(hint)}\s+["\']?([^"\',.!?\n]+)["\']?'
                    match = re.search(hint_pattern, user_input, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        break

            # Type-specific extraction
            if not value:
                param_type = param_def.get('type')

                if param_type == 'number':
                    # Extract numbers
                    numbers = re.findall(r'\b(\d+(?:\.\d+)?)\b', user_input)
                    if numbers:
                        value = float(numbers[0]) if '.' in numbers[0] else int(numbers[0])

                elif param_type == 'string' and param_def.get('format') == 'email':
                    # Extract email
                    emails = re.findall(
                        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                        user_input
                    )
                    if emails:
                        value = emails[0]

                elif param_type == 'string' and param_def.get('format') == 'date':
                    # Extract date patterns
                    date_patterns = [
                        r'\b(\d{4}-\d{2}-\d{2})\b',  # ISO format
                        r'\b(\d{1,2}/\d{1,2}/\d{4})\b',  # US format
                        r'\b(\d{1,2}\s+\w+\s+\d{4})\b',  # Natural format
                    ]
                    for dp in date_patterns:
                        dates = re.findall(dp, user_input)
                        if dates:
                            value = dates[0]
                            break

            if value is not None:
                extracted[param_name] = self._cast_value(value, param_def.get('type'))

        return extracted

    def _cast_value(self, value, type_hint):
        """
        Cast extracted value to appropriate type.

        :param value: Raw extracted value
        :param type_hint: JSON Schema type hint
        :return: Casted value
        """
        if type_hint == 'number':
            try:
                return float(value) if '.' in str(value) else int(value)
            except (ValueError, TypeError):
                return value
        elif type_hint == 'boolean':
            if isinstance(value, bool):
                return value
            return str(value).lower() in ('true', 'yes', '1', 'y')
        elif type_hint == 'array':
            if isinstance(value, list):
                return value
            return [value] if value else []
        return value

    def _get_suggestions(self, user_input, skills):
        """
        Get skill suggestions for low-confidence matches.

        :param user_input: User input
        :param skills: Available skills
        :return: List of suggested skill dicts
        """
        suggestions = []
        user_tokens = set(user_input.lower().split())

        for skill in skills[:10]:  # Limit to prevent performance issues
            phrases = skill.get_trigger_phrases()
            if not phrases:
                continue

            # Find any keyword overlap
            for phrase in phrases:
                phrase_tokens = set(phrase.lower().split())
                # Remove placeholders
                phrase_tokens = {t for t in phrase_tokens if not t.startswith('{')}

                overlap = user_tokens & phrase_tokens
                if overlap:
                    suggestions.append({
                        'skill_id': skill.id,
                        'skill_name': skill.name,
                        'category': skill.category,
                        'sample_trigger': phrases[0] if phrases else '',
                        'relevance': len(overlap) / max(len(phrase_tokens), 1),
                    })
                    break

        # Sort by relevance and limit
        suggestions.sort(key=lambda x: x['relevance'], reverse=True)
        return suggestions[:5]


class IntentMatcher(SkillMatchingService):
    """Alias for backward compatibility."""
    pass
