# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Claude API client wrapper for Odoo integration.

Provides a clean interface between Odoo and the Anthropic Claude API,
handling session management, tool execution, and response streaming.

Based on: https://docs.anthropic.com/en/api/messages
"""

import json
import logging
from typing import Generator, Optional, Dict, Any, List

_logger = logging.getLogger(__name__)

# Try to import anthropic - handle gracefully if not installed
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    _logger.warning("Anthropic SDK not installed. AI features will be limited.")


class LoomworksClaudeClient:
    """
    Wrapper around Claude API for Loomworks ERP.
    Handles conversation management and tool execution.
    """

    def __init__(self, env, session, agent):
        """
        Initialize Claude client for a session.

        Args:
            env: Odoo environment
            session: loomworks.ai.session record
            agent: loomworks.ai.agent record
        """
        self.env = env
        self.session = session
        self.agent = agent
        self._client = None
        self._connected = False

        # Import tool implementations
        from .odoo_mcp_tools import OdooMCPTools, get_tool_schemas
        self.mcp_tools = OdooMCPTools(env, session, agent)
        self.tool_schemas = get_tool_schemas()

    def _get_api_key(self):
        """Get API key from system parameters."""
        return self.env['ir.config_parameter'].sudo().get_param(
            'loomworks_ai.anthropic_api_key', ''
        )

    def connect(self):
        """Establish connection to Claude API."""
        if not ANTHROPIC_AVAILABLE:
            _logger.warning("Anthropic SDK not available")
            return False

        try:
            api_key = self._get_api_key()
            if not api_key:
                _logger.warning("Anthropic API key not configured")
                return False

            self._client = anthropic.Anthropic(api_key=api_key)
            self._connected = True
            _logger.info(f"Claude client connected for session {self.session.uuid}")
            return True

        except Exception as e:
            _logger.error(f"Failed to connect Claude client: {e}")
            return False

    def disconnect(self):
        """Close connection to Claude API."""
        self._client = None
        self._connected = False
        _logger.info(f"Claude client disconnected for session {self.session.uuid}")

    def send_message(self, message: str) -> Generator[Dict[str, Any], None, None]:
        """
        Send a message to Claude and yield response chunks.

        Args:
            message: User message text

        Yields:
            Response chunks with type and content
        """
        # Store user message
        self.session.add_message(role='user', content=message)
        self.session.touch()

        # Reset turn operation counter
        self.session.update_context('turn_operation_count', 0)

        if not self._connected:
            if not self.connect():
                yield {
                    'type': 'error',
                    'content': 'Failed to connect to Claude API. Please check API key configuration.'
                }
                return

        try:
            # Build conversation context
            system_prompt = self.agent.get_effective_system_prompt()
            history = self._build_messages(message)

            # Make API call with streaming
            with self._client.messages.stream(
                model=self.agent.model_id,
                max_tokens=self.agent.max_tokens,
                system=system_prompt,
                messages=history,
                tools=self.tool_schemas,
                temperature=self.agent.temperature,
            ) as stream:
                collected_text = []
                tool_use_blocks = []

                for event in stream:
                    if event.type == 'text':
                        collected_text.append(event.text)
                        yield {
                            'type': 'text',
                            'content': event.text
                        }
                    elif event.type == 'content_block_start':
                        if hasattr(event, 'content_block') and event.content_block.type == 'tool_use':
                            tool_use_blocks.append({
                                'id': event.content_block.id,
                                'name': event.content_block.name,
                                'input': {}
                            })
                    elif event.type == 'content_block_stop':
                        pass

                # Get final message for tool use handling
                final_message = stream.get_final_message()

                # Process tool calls if any
                for block in final_message.content:
                    if block.type == 'tool_use':
                        yield {
                            'type': 'tool_call',
                            'tool': block.name,
                            'input': block.input,
                            'id': block.id
                        }

                        # Execute tool
                        tool_result = self._execute_tool(block.name, block.input)

                        yield {
                            'type': 'tool_result',
                            'tool': block.name,
                            'result': tool_result
                        }

                        # Continue conversation with tool result
                        for chunk in self._continue_with_tool_result(
                            final_message, block.id, tool_result
                        ):
                            yield chunk

            # Completion
            yield {
                'type': 'done',
                'usage': {
                    'input_tokens': final_message.usage.input_tokens,
                    'output_tokens': final_message.usage.output_tokens
                } if hasattr(final_message, 'usage') else {}
            }

        except anthropic.APIConnectionError as e:
            _logger.error(f"Claude API connection error: {e}")
            yield {'type': 'error', 'content': 'Connection error with Claude API'}
        except anthropic.RateLimitError as e:
            _logger.error(f"Claude API rate limit: {e}")
            yield {'type': 'error', 'content': 'Rate limit exceeded. Please try again later.'}
        except anthropic.APIStatusError as e:
            _logger.error(f"Claude API status error: {e}")
            yield {'type': 'error', 'content': f'API error: {e.message}'}
        except Exception as e:
            _logger.error(f"Error processing message: {e}")
            yield {'type': 'error', 'content': str(e)}

    def send_message_sync(self, message: str) -> Dict[str, Any]:
        """
        Send a message and return complete response (non-streaming).

        Args:
            message: User message text

        Returns:
            Complete response dictionary
        """
        response_parts = []
        tool_calls = []
        operations = []

        for chunk in self.send_message(message):
            if chunk['type'] == 'text':
                response_parts.append(chunk['content'])
            elif chunk['type'] == 'tool_call':
                tool_calls.append(chunk)
            elif chunk['type'] == 'error':
                return {'error': chunk['content']}

        full_response = ''.join(response_parts)

        # Store assistant response
        self.session.add_message(
            role='assistant',
            content=full_response,
            tool_calls=tool_calls if tool_calls else None
        )

        return {
            'response': full_response,
            'tool_calls': tool_calls,
        }

    def _build_messages(self, current_message: str) -> List[Dict]:
        """Build messages array for Claude API from session history."""
        messages = []

        # Get conversation history (excluding the current message we just added)
        history = self.session.get_conversation_history(limit=20)

        for msg in history:
            role = msg['role']
            # Claude API only accepts 'user' and 'assistant' roles
            if role == 'system':
                continue  # System messages go in system parameter
            if role == 'tool':
                role = 'user'  # Tool results are user messages

            messages.append({
                'role': role,
                'content': msg['content']
            })

        return messages

    def _execute_tool(self, tool_name: str, tool_input: dict) -> dict:
        """
        Execute a tool call from Claude.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool

        Returns:
            Tool execution result
        """
        tools = {
            'search_records': self.mcp_tools.search_records,
            'create_record': self.mcp_tools.create_record,
            'update_record': self.mcp_tools.update_record,
            'delete_record': self.mcp_tools.delete_record,
            'execute_action': self.mcp_tools.execute_action,
            'generate_report': self.mcp_tools.generate_report,
            'get_field_info': self.mcp_tools.get_field_info,
            'get_dashboard_data': self.mcp_tools.get_dashboard_data,
        }

        if tool_name not in tools:
            return {'error': f'Unknown tool: {tool_name}'}

        try:
            # Record tool usage
            tool_record = self.env['loomworks.ai.tool'].search([
                ('technical_name', '=', tool_name)
            ], limit=1)
            if tool_record:
                tool_record.record_usage()

            result = tools[tool_name](**tool_input)
            return result
        except Exception as e:
            _logger.error(f"Tool execution error ({tool_name}): {e}")
            return {'error': str(e)}

    def _continue_with_tool_result(
        self,
        assistant_message,
        tool_use_id: str,
        tool_result: dict
    ) -> Generator[Dict[str, Any], None, None]:
        """Continue conversation after tool execution."""
        try:
            # Build message with tool result
            messages = self._build_messages('')

            # Add assistant's message with tool use
            messages.append({
                'role': 'assistant',
                'content': assistant_message.content
            })

            # Add tool result
            messages.append({
                'role': 'user',
                'content': [{
                    'type': 'tool_result',
                    'tool_use_id': tool_use_id,
                    'content': json.dumps(tool_result)
                }]
            })

            # Continue conversation
            with self._client.messages.stream(
                model=self.agent.model_id,
                max_tokens=self.agent.max_tokens,
                messages=messages,
                tools=self.tool_schemas,
            ) as stream:
                for event in stream:
                    if event.type == 'text':
                        yield {
                            'type': 'text',
                            'content': event.text
                        }

        except Exception as e:
            _logger.error(f"Error continuing with tool result: {e}")
            yield {'type': 'error', 'content': str(e)}


class MockClaudeClient(LoomworksClaudeClient):
    """
    Mock Claude client for development/testing without API key.
    Returns placeholder responses.
    """

    def connect(self):
        """Mock connection always succeeds."""
        self._connected = True
        _logger.info(f"Mock Claude client connected for session {self.session.uuid}")
        return True

    def send_message(self, message: str) -> Generator[Dict[str, Any], None, None]:
        """Return mock response."""
        self.session.add_message(role='user', content=message)
        self.session.touch()
        self.session.update_context('turn_operation_count', 0)

        # Simple mock response
        mock_response = f"[Development Mode] I received your message: '{message}'. " \
                       f"To enable real AI responses, configure your Anthropic API key " \
                       f"in Settings > System Parameters > loomworks_ai.anthropic_api_key"

        yield {'type': 'text', 'content': mock_response}
        yield {'type': 'done', 'usage': {'input_tokens': 100, 'output_tokens': 50}}

        # Store response
        self.session.add_message(role='assistant', content=mock_response)


def create_claude_client(env, session, agent) -> LoomworksClaudeClient:
    """
    Factory function to create appropriate Claude client instance.

    Returns MockClaudeClient if API key not configured, otherwise real client.
    """
    api_key = env['ir.config_parameter'].sudo().get_param(
        'loomworks_ai.anthropic_api_key', ''
    )

    if not api_key or not ANTHROPIC_AVAILABLE:
        _logger.info("Using mock Claude client (no API key or SDK)")
        return MockClaudeClient(env, session, agent)

    return LoomworksClaudeClient(env, session, agent)
