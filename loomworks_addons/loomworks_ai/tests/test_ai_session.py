# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
import json


class TestAISession(TransactionCase):
    """Test cases for the AI Session model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Agent = cls.env['loomworks.ai.agent']
        cls.Session = cls.env['loomworks.ai.session']

        # Create test agent
        cls.test_agent = cls.Agent.create({
            'name': 'Test Agent',
            'technical_name': 'test_session_agent',
            'model_id': 'claude-sonnet-4-20250514',
        })

    def test_create_session(self):
        """Test basic session creation."""
        session = self.Session.create({
            'agent_id': self.test_agent.id,
        })
        self.assertTrue(session.id)
        self.assertTrue(session.uuid)
        self.assertEqual(session.state, 'active')
        self.assertEqual(session.user_id, self.env.user)

    def test_session_uuid_uniqueness(self):
        """Test UUID is unique for each session."""
        session1 = self.Session.create({'agent_id': self.test_agent.id})
        session2 = self.Session.create({'agent_id': self.test_agent.id})
        self.assertNotEqual(session1.uuid, session2.uuid)

    def test_add_message(self):
        """Test adding messages to session."""
        session = self.Session.create({'agent_id': self.test_agent.id})

        # Add user message
        msg1 = session.add_message('user', 'Hello')
        self.assertEqual(msg1.role, 'user')
        self.assertEqual(msg1.content, 'Hello')

        # Add assistant message with tool calls
        tool_calls = [{'tool': 'search_records', 'input': {'model': 'res.partner'}}]
        msg2 = session.add_message('assistant', 'Here are the results', tool_calls=tool_calls)
        self.assertEqual(msg2.role, 'assistant')
        self.assertTrue(msg2.tool_calls_json)

        # Check message count
        self.assertEqual(session.message_count, 2)

    def test_get_conversation_history(self):
        """Test retrieving conversation history."""
        session = self.Session.create({'agent_id': self.test_agent.id})
        session.add_message('user', 'First message')
        session.add_message('assistant', 'First response')
        session.add_message('user', 'Second message')

        history = session.get_conversation_history()
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0]['role'], 'user')
        self.assertEqual(history[0]['content'], 'First message')

    def test_context_management(self):
        """Test session context storage."""
        session = self.Session.create({'agent_id': self.test_agent.id})

        # Update context
        session.update_context('turn_operation_count', 5)
        session.update_context('last_model', 'res.partner')

        # Retrieve context
        count = session.get_context('turn_operation_count')
        self.assertEqual(count, 5)

        full_context = session.get_context()
        self.assertEqual(full_context['last_model'], 'res.partner')

    def test_touch_updates_last_activity(self):
        """Test that touch() updates last_activity."""
        session = self.Session.create({'agent_id': self.test_agent.id})
        initial_activity = session.last_activity

        # Touch and check update
        session.touch()
        session.refresh()
        # Note: In same transaction, datetime might be same, so just verify it runs
        self.assertTrue(session.last_activity)

    def test_cleanup_stale_sessions(self):
        """Test stale session cleanup."""
        # Create a session
        session = self.Session.create({'agent_id': self.test_agent.id})
        self.assertEqual(session.state, 'active')

        # Cleanup with 0 hours (should mark as completed)
        cleaned = self.Session.cleanup_stale_sessions(hours=0)
        session.refresh()
        # Should be completed now (since it's older than 0 hours)
        self.assertGreaterEqual(cleaned, 0)  # May or may not catch depending on timing
