# Phase 2: AI Integration Layer

## Change ID: `add-ai-integration-layer`

---

## Overview

### Vision: AI-First ERP Architecture

Loomworks ERP reimagines enterprise resource planning by making Claude AI the primary interface for all business operations. Instead of navigating complex menus and forms, users interact with a conversational AI agent that can:

- Search and retrieve any business data
- Create, update, and delete records across all modules
- Execute complex workflows and business actions
- Generate reports and dashboards on demand
- Learn from user interactions to suggest optimizations

### User Interaction Model

```
User: "Create a purchase order for 100 units of steel from our best supplier"

Claude: I'll help you create that purchase order. Let me:
1. Search for steel products in inventory
2. Find your preferred supplier based on past orders
3. Create the PO with current pricing

[Executes: search_records, analyze data, create_record]

Done! I've created PO-2026-0142 for 100 units of Steel Grade A from
Acme Metals at $45.50/unit. The total is $4,550.00.

Would you like me to:
- Send this for approval?
- Add additional line items?
- Check current inventory levels?
```

### Architecture Principles

1. **Conversation as Interface**: Every ERP operation can be performed through natural language
2. **Sandboxed Execution**: All AI operations run within a security sandbox with rollback capability
3. **Full Auditability**: Every AI action is logged with before/after states for compliance
4. **Permission Inheritance**: AI respects the user's Odoo access rights and record rules
5. **Graceful Degradation**: Traditional UI remains available; AI enhances but doesn't replace

---

## Why

The traditional ERP paradigm requires users to learn complex navigation, memorize field locations, and understand data relationships. This creates:

- High training costs for new employees
- Slow adoption of advanced features
- Dependency on technical consultants for customization
- User frustration leading to workarounds and data quality issues

By making Claude AI the primary interface, we:

- Reduce onboarding time from weeks to hours
- Enable natural language queries for complex reports
- Allow non-technical users to perform advanced operations
- Provide intelligent suggestions based on business context
- Create a competitive moat that differentiates Loomworks from traditional ERPs

---

## What Changes

### Approach: AI as Core Feature (Forked Odoo)

Since Loomworks ERP is a **fully forked** version of Odoo Community v18 (not just addons), AI is implemented as a **native core feature** rather than a bolt-on module. This enables:

- AI button directly in the navbar (not just systray)
- Command palette (Ctrl+K) with native AI commands
- AI hooks in the ORM layer (`models.py`, `api.py`)
- MCP server starting alongside Odoo HTTP server
- Every view has native "Ask AI" capability

### New Module: `loomworks_ai`

Business logic and data models in a dedicated module:

- **BREAKING**: Introduces new security model for AI operations
- Adds conversation tracking and history
- Implements MCP (Model Context Protocol) server for tool access
- Creates Owl-based chat interface components
- Establishes operation sandbox with rollback

### Core Modifications (Forked Files)

Direct modifications to Odoo core for native AI integration:

- `odoo/odoo/models.py` - AI operation hooks in BaseModel
- `odoo/odoo/api.py` - AI context manager and decorators
- `odoo/odoo/service/server.py` - MCP server startup
- `odoo/addons/web/static/src/webclient/` - AI-enhanced web client
- `odoo/addons/web/static/src/core/ai/` - AI service and commands
- `odoo/addons/web/static/src/views/` - AI actions in form/list controllers

### Affected Systems

- `web` (frontend) - Native AI integration in webclient, navbar, command palette
- `base` (ORM) - AI hooks and context managers
- `server` - MCP server as core service
- Database - New tables for sessions, tools, operations

---

## Impact

- **Affected specs**: None (new capability)
- **Affected code**:
  - **Core modifications**: `odoo/odoo/models.py`, `odoo/odoo/api.py`, `odoo/odoo/service/server.py`
  - **Web client modifications**: `odoo/addons/web/static/src/webclient/`, `odoo/addons/web/static/src/views/`
  - **New AI module**: `loomworks_addons/loomworks_ai/`
  - **New AI core service**: `odoo/addons/web/static/src/core/ai/`
  - Database schema additions
- **Migration**: Fresh install only for Phase 2; no migration from previous versions
- **Fork maintenance**: All core modifications are marked with `LOOMWORKS-AI` comments for tracking

---

## Technical Design

### 2.1 Module Structure

```
loomworks_addons/loomworks_ai/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── ai_agent.py           # Agent configuration
│   ├── ai_session.py         # Conversation tracking
│   ├── ai_tool.py            # Tool definitions
│   ├── ai_operation_log.py   # Audit trail
│   └── ai_sandbox.py         # Security sandbox
├── services/
│   ├── __init__.py
│   ├── odoo_mcp_server.py    # MCP server implementation
│   ├── claude_client.py      # Claude Agent SDK wrapper
│   └── sandbox_executor.py   # Sandboxed operation runner
├── controllers/
│   ├── __init__.py
│   └── ai_controller.py      # HTTP/WebSocket endpoints
├── views/
│   ├── ai_agent_views.xml
│   ├── ai_session_views.xml
│   └── ai_menus.xml
├── security/
│   ├── ir.model.access.csv
│   ├── security.xml
│   └── ai_security_rules.xml
├── data/
│   ├── ai_tool_data.xml      # Default tool definitions
│   └── ai_system_prompts.xml # Default prompts
├── static/src/
│   ├── components/
│   │   ├── ai_chat/
│   │   │   ├── ai_chat.js
│   │   │   ├── ai_chat.xml
│   │   │   └── ai_chat.scss
│   │   ├── ai_message/
│   │   │   ├── ai_message.js
│   │   │   └── ai_message.xml
│   │   └── ai_sidebar/
│   │       ├── ai_sidebar.js
│   │       └── ai_sidebar.xml
│   └── xml/
│       └── assets.xml
└── tests/
    ├── __init__.py
    ├── test_ai_agent.py
    ├── test_ai_session.py
    ├── test_mcp_tools.py
    ├── test_sandbox.py
    └── test_security.py
```

---

### 2.2 Model Schemas

#### 2.2.1 `ai_agent.py` - Agent Configuration

```python
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, AccessError
import json

class AIAgent(models.Model):
    """
    Configuration for Claude AI agents.
    Each company can have multiple agents with different capabilities.
    """
    _name = 'loomworks.ai.agent'
    _description = 'AI Agent Configuration'
    _order = 'sequence, id'

    name = fields.Char(
        string='Agent Name',
        required=True,
        help='Display name for this AI agent'
    )
    technical_name = fields.Char(
        string='Technical Name',
        required=True,
        copy=False,
        help='Unique identifier used in API calls'
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    # Claude Configuration
    model_id = fields.Selection([
        ('claude-sonnet-4-20250514', 'Claude Sonnet 4'),
        ('claude-opus-4-5-20251101', 'Claude Opus 4.5'),
    ], string='Claude Model', default='claude-sonnet-4-20250514', required=True)

    system_prompt = fields.Text(
        string='System Prompt',
        help='Base instructions for the AI agent behavior'
    )
    max_tokens = fields.Integer(
        string='Max Response Tokens',
        default=4096,
        help='Maximum tokens in AI response'
    )
    temperature = fields.Float(
        string='Temperature',
        default=0.7,
        help='Creativity level (0.0 = deterministic, 1.0 = creative)'
    )

    # Tool Access Control
    tool_ids = fields.Many2many(
        'loomworks.ai.tool',
        string='Allowed Tools',
        help='MCP tools this agent can use'
    )
    allowed_model_ids = fields.Many2many(
        'ir.model',
        'ai_agent_allowed_models_rel',
        'agent_id',
        'model_id',
        string='Allowed Models',
        help='Odoo models this agent can access. Empty = all accessible models.'
    )
    blocked_model_ids = fields.Many2many(
        'ir.model',
        'ai_agent_blocked_models_rel',
        'agent_id',
        'model_id',
        string='Blocked Models',
        help='Odoo models this agent cannot access (overrides allowed)'
    )

    # Permission Settings
    permission_mode = fields.Selection([
        ('default', 'Default - Prompt for all operations'),
        ('accept_reads', 'Auto-approve read operations'),
        ('accept_edits', 'Auto-approve read and edit operations'),
        ('supervised', 'Require approval for every action'),
    ], string='Permission Mode', default='accept_reads', required=True)

    can_create = fields.Boolean(
        string='Can Create Records',
        default=True
    )
    can_write = fields.Boolean(
        string='Can Update Records',
        default=True
    )
    can_unlink = fields.Boolean(
        string='Can Delete Records',
        default=False,
        help='Dangerous: allows permanent deletion'
    )
    can_execute_actions = fields.Boolean(
        string='Can Execute Actions',
        default=True,
        help='Allow running server actions and workflows'
    )

    # Sandbox Settings
    use_savepoints = fields.Boolean(
        string='Use Database Savepoints',
        default=True,
        help='Create savepoint before each operation for rollback'
    )
    auto_rollback_on_error = fields.Boolean(
        string='Auto-Rollback on Error',
        default=True
    )
    max_operations_per_turn = fields.Integer(
        string='Max Operations per Turn',
        default=10,
        help='Limit operations in single conversation turn'
    )

    # Statistics
    session_count = fields.Integer(
        string='Total Sessions',
        compute='_compute_statistics'
    )
    operation_count = fields.Integer(
        string='Total Operations',
        compute='_compute_statistics'
    )

    _sql_constraints = [
        ('technical_name_company_uniq',
         'UNIQUE(technical_name, company_id)',
         'Technical name must be unique per company'),
    ]

    @api.depends('technical_name')
    def _compute_statistics(self):
        for agent in self:
            agent.session_count = self.env['loomworks.ai.session'].search_count([
                ('agent_id', '=', agent.id)
            ])
            agent.operation_count = self.env['loomworks.ai.operation.log'].search_count([
                ('agent_id', '=', agent.id)
            ])

    @api.constrains('temperature')
    def _check_temperature(self):
        for agent in self:
            if not 0.0 <= agent.temperature <= 1.0:
                raise UserError('Temperature must be between 0.0 and 1.0')

    def get_effective_system_prompt(self):
        """Build complete system prompt with Odoo context."""
        self.ensure_one()
        base_prompt = self.system_prompt or self._get_default_system_prompt()

        # Add Odoo-specific context
        odoo_context = self._build_odoo_context()

        return f"""{base_prompt}

## Odoo ERP Context

You are operating within Loomworks ERP (based on Odoo). Here is your current context:

{odoo_context}

## Tool Usage Guidelines

- Always use search_records before create/update to verify data exists
- Use transactions: operations within a turn are atomic
- Log your reasoning for audit compliance
- Respect user permissions - you inherit the user's access rights
"""

    def _get_default_system_prompt(self):
        return """You are Loomworks AI, an intelligent assistant for enterprise resource planning.

Your role is to help users manage their business operations through natural conversation.
You can search data, create records, update information, and execute business workflows.

Guidelines:
1. Always confirm understanding before making changes
2. Explain what you're doing in simple terms
3. Offer alternatives when requests are ambiguous
4. Warn about potential impacts of destructive operations
5. Suggest related actions that might be helpful
"""

    def _build_odoo_context(self):
        """Build contextual information about the current Odoo environment."""
        user = self.env.user
        company = self.env.company

        return f"""- Current User: {user.name} ({user.login})
- Company: {company.name}
- Timezone: {user.tz or 'UTC'}
- Language: {user.lang or 'en_US'}
- Date: {fields.Date.today()}
"""

    def check_model_access(self, model_name, operation='read'):
        """
        Verify if this agent can access a specific model.
        Returns True if access is allowed, False otherwise.
        """
        self.ensure_one()

        # Always block sensitive models
        SENSITIVE_MODELS = [
            'res.users',
            'res.users.log',
            'ir.config_parameter',
            'ir.rule',
            'ir.model.access',
            'ir.ui.view',
            'ir.attachment',  # Could contain sensitive files
            'mail.mail',      # Email content
        ]

        if model_name in SENSITIVE_MODELS:
            return False

        # Check explicit blocks
        if self.blocked_model_ids:
            blocked_names = self.blocked_model_ids.mapped('model')
            if model_name in blocked_names:
                return False

        # Check explicit allows (if defined)
        if self.allowed_model_ids:
            allowed_names = self.allowed_model_ids.mapped('model')
            if model_name not in allowed_names:
                return False

        # Check operation permissions
        if operation == 'create' and not self.can_create:
            return False
        if operation == 'write' and not self.can_write:
            return False
        if operation == 'unlink' and not self.can_unlink:
            return False

        return True
```

#### 2.2.2 `ai_session.py` - Conversation Tracking

```python
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import json
import uuid
from datetime import timedelta

class AISession(models.Model):
    """
    Tracks conversation sessions between users and AI agents.
    Each session maintains context across multiple message exchanges.
    """
    _name = 'loomworks.ai.session'
    _description = 'AI Conversation Session'
    _order = 'create_date desc'

    name = fields.Char(
        string='Session Name',
        compute='_compute_name',
        store=True
    )
    uuid = fields.Char(
        string='Session UUID',
        required=True,
        readonly=True,
        default=lambda self: str(uuid.uuid4()),
        copy=False
    )
    agent_id = fields.Many2one(
        'loomworks.ai.agent',
        string='AI Agent',
        required=True,
        ondelete='cascade'
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        default=lambda self: self.env.user,
        ondelete='cascade'
    )
    company_id = fields.Many2one(
        'res.company',
        related='agent_id.company_id',
        store=True
    )

    # Session State
    state = fields.Selection([
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('error', 'Error'),
        ('rolled_back', 'Rolled Back'),
    ], string='State', default='active', required=True)

    # Message History
    message_ids = fields.One2many(
        'loomworks.ai.message',
        'session_id',
        string='Messages'
    )
    message_count = fields.Integer(
        compute='_compute_message_count'
    )

    # Operation Tracking
    operation_ids = fields.One2many(
        'loomworks.ai.operation.log',
        'session_id',
        string='Operations'
    )
    operation_count = fields.Integer(
        compute='_compute_operation_count'
    )

    # Context Storage
    context_data = fields.Text(
        string='Session Context (JSON)',
        default='{}',
        help='Stores conversation context for continuity'
    )
    last_model_context = fields.Char(
        string='Last Active Model',
        help='The Odoo model user was working with'
    )
    last_record_ids = fields.Char(
        string='Last Record IDs (JSON)',
        help='Record IDs from last operation'
    )

    # Timestamps
    last_activity = fields.Datetime(
        string='Last Activity',
        default=fields.Datetime.now
    )
    duration_minutes = fields.Float(
        compute='_compute_duration'
    )

    # Rollback Support
    has_uncommitted_changes = fields.Boolean(
        string='Has Uncommitted Changes',
        default=False
    )
    savepoint_name = fields.Char(
        string='Current Savepoint'
    )

    _sql_constraints = [
        ('uuid_uniq', 'UNIQUE(uuid)', 'Session UUID must be unique'),
    ]

    @api.depends('create_date', 'user_id')
    def _compute_name(self):
        for session in self:
            date_str = session.create_date.strftime('%Y-%m-%d %H:%M') if session.create_date else ''
            session.name = f"{session.user_id.name} - {date_str}"

    def _compute_message_count(self):
        for session in self:
            session.message_count = len(session.message_ids)

    def _compute_operation_count(self):
        for session in self:
            session.operation_count = len(session.operation_ids)

    @api.depends('create_date', 'last_activity')
    def _compute_duration(self):
        for session in self:
            if session.create_date and session.last_activity:
                delta = session.last_activity - session.create_date
                session.duration_minutes = delta.total_seconds() / 60
            else:
                session.duration_minutes = 0

    def add_message(self, role, content, tool_calls=None, tool_results=None):
        """Add a message to the session history."""
        self.ensure_one()
        return self.env['loomworks.ai.message'].create({
            'session_id': self.id,
            'role': role,
            'content': content,
            'tool_calls_json': json.dumps(tool_calls) if tool_calls else False,
            'tool_results_json': json.dumps(tool_results) if tool_results else False,
        })

    def get_conversation_history(self, limit=50):
        """
        Retrieve conversation history formatted for Claude API.
        Returns list of message dicts with role and content.
        """
        self.ensure_one()
        messages = self.message_ids.sorted('create_date')[-limit:]

        history = []
        for msg in messages:
            history.append({
                'role': msg.role,
                'content': msg.content,
            })
            # Include tool calls/results if present
            if msg.tool_calls_json:
                history[-1]['tool_calls'] = json.loads(msg.tool_calls_json)
            if msg.tool_results_json:
                history[-1]['tool_results'] = json.loads(msg.tool_results_json)

        return history

    def update_context(self, key, value):
        """Update session context data."""
        self.ensure_one()
        context = json.loads(self.context_data or '{}')
        context[key] = value
        self.context_data = json.dumps(context)

    def get_context(self, key=None):
        """Retrieve session context data."""
        self.ensure_one()
        context = json.loads(self.context_data or '{}')
        if key:
            return context.get(key)
        return context

    def create_savepoint(self):
        """Create a database savepoint for rollback capability."""
        self.ensure_one()
        savepoint_name = f"ai_session_{self.uuid.replace('-', '_')}_{fields.Datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.env.cr.execute(f'SAVEPOINT {savepoint_name}')
        self.write({
            'savepoint_name': savepoint_name,
            'has_uncommitted_changes': True
        })
        return savepoint_name

    def rollback_to_savepoint(self):
        """Rollback all changes since last savepoint."""
        self.ensure_one()
        if not self.savepoint_name:
            raise UserError('No savepoint available for rollback')

        self.env.cr.execute(f'ROLLBACK TO SAVEPOINT {self.savepoint_name}')
        self.write({
            'state': 'rolled_back',
            'has_uncommitted_changes': False
        })

        # Log the rollback
        self.add_message(
            role='system',
            content=f'Session rolled back to savepoint {self.savepoint_name}'
        )

    def release_savepoint(self):
        """Release savepoint and commit changes."""
        self.ensure_one()
        if self.savepoint_name:
            self.env.cr.execute(f'RELEASE SAVEPOINT {self.savepoint_name}')
            self.write({
                'savepoint_name': False,
                'has_uncommitted_changes': False
            })

    def touch(self):
        """Update last activity timestamp."""
        self.write({'last_activity': fields.Datetime.now()})

    @api.model
    def cleanup_stale_sessions(self, hours=24):
        """Archive sessions inactive for specified hours."""
        cutoff = fields.Datetime.now() - timedelta(hours=hours)
        stale_sessions = self.search([
            ('state', '=', 'active'),
            ('last_activity', '<', cutoff)
        ])
        stale_sessions.write({'state': 'completed'})
        return len(stale_sessions)


class AIMessage(models.Model):
    """Individual messages within an AI session."""
    _name = 'loomworks.ai.message'
    _description = 'AI Chat Message'
    _order = 'create_date asc'

    session_id = fields.Many2one(
        'loomworks.ai.session',
        string='Session',
        required=True,
        ondelete='cascade'
    )
    role = fields.Selection([
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
        ('tool', 'Tool Result'),
    ], string='Role', required=True)

    content = fields.Text(
        string='Content',
        required=True
    )

    # Tool interaction data
    tool_calls_json = fields.Text(
        string='Tool Calls (JSON)',
        help='JSON array of tool calls made by assistant'
    )
    tool_results_json = fields.Text(
        string='Tool Results (JSON)',
        help='JSON array of tool execution results'
    )

    # Metadata
    token_count = fields.Integer(
        string='Token Count'
    )
    processing_time_ms = fields.Integer(
        string='Processing Time (ms)'
    )
```

#### 2.2.3 `ai_tool.py` - Tool Definitions

```python
# -*- coding: utf-8 -*-
from odoo import models, fields, api
import json

class AITool(models.Model):
    """
    Defines MCP tools available to AI agents.
    Each tool represents a capability the AI can invoke.
    """
    _name = 'loomworks.ai.tool'
    _description = 'AI Tool Definition'
    _order = 'category, sequence, name'

    name = fields.Char(
        string='Tool Name',
        required=True,
        help='Display name for the tool'
    )
    technical_name = fields.Char(
        string='Technical Name',
        required=True,
        help='Name used in MCP protocol (snake_case)'
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    category = fields.Selection([
        ('data', 'Data Operations'),
        ('action', 'Actions & Workflows'),
        ('report', 'Reports & Analytics'),
        ('system', 'System Operations'),
    ], string='Category', required=True, default='data')

    description = fields.Text(
        string='Description',
        required=True,
        help='Detailed description shown to AI for tool selection'
    )

    # JSON Schema for parameters
    parameters_schema = fields.Text(
        string='Parameters Schema (JSON)',
        required=True,
        default='{"type": "object", "properties": {}, "required": []}',
        help='JSON Schema defining tool parameters'
    )

    # Return type documentation
    returns_description = fields.Text(
        string='Returns Description',
        help='Description of what the tool returns'
    )

    # Implementation reference
    implementation_method = fields.Char(
        string='Implementation Method',
        required=True,
        help='Python method path: module.class.method'
    )

    # Risk assessment
    risk_level = fields.Selection([
        ('safe', 'Safe - Read only'),
        ('moderate', 'Moderate - Creates/modifies data'),
        ('high', 'High - Deletes data or runs workflows'),
        ('critical', 'Critical - System-level operations'),
    ], string='Risk Level', required=True, default='safe')

    requires_confirmation = fields.Boolean(
        string='Requires User Confirmation',
        default=False,
        help='Prompt user before executing'
    )

    # Usage statistics
    usage_count = fields.Integer(
        string='Usage Count',
        default=0
    )
    last_used = fields.Datetime(
        string='Last Used'
    )

    _sql_constraints = [
        ('technical_name_uniq', 'UNIQUE(technical_name)',
         'Technical name must be unique'),
    ]

    def get_mcp_schema(self):
        """Return tool definition in MCP format."""
        self.ensure_one()
        return {
            'name': self.technical_name,
            'description': self.description,
            'inputSchema': json.loads(self.parameters_schema),
        }

    def record_usage(self):
        """Record that this tool was used."""
        self.write({
            'usage_count': self.usage_count + 1,
            'last_used': fields.Datetime.now()
        })

    @api.model
    def get_tools_for_agent(self, agent):
        """Get all tools available to a specific agent."""
        if agent.tool_ids:
            return agent.tool_ids.filtered('active')
        # Default: return all safe tools
        return self.search([
            ('active', '=', True),
            ('risk_level', 'in', ['safe', 'moderate'])
        ])
```

### 2.2.3.1 AI Tool Registration Pattern (M4 Resolution)

To enable modules across all phases to register AI tools dynamically, Phase 2 provides a **ToolProvider mixin pattern**. This follows Odoo's registry pattern and allows any module to contribute tools without modifying the core `loomworks_ai` module.

#### Design Rationale

**Problem**: Phase 3+ modules (Studio, Spreadsheet, PLM, FSM, etc.) need to register AI tools (e.g., `studio_create_app`, `spreadsheet_create_pivot`) but there's no standard pattern for doing so.

**Solution**: Implement a `ToolProvider` abstract model that modules inherit. On module installation, tools are automatically registered via Odoo's model inheritance mechanism.

**Research Sources**:
- [Odoo 18 Registries Documentation](https://www.odoo.com/documentation/18.0/developer/reference/frontend/registries.html)
- [A Guide to Registries in Odoo 18](https://bassaminfotech.com/odoo18-registries/)
- [Dynamic Tool Updates in MCP](https://spring.io/blog/2025/05/04/spring-ai-dynamic-tool-updates-with-mcp/)

#### ToolProvider Abstract Model

**File**: `loomworks_ai/models/ai_tool_provider.py`

```python
# -*- coding: utf-8 -*-
"""
AI Tool Provider Mixin - Enables any module to register AI tools dynamically.

Modules inherit from this mixin and implement _register_ai_tools() to define
their tools. Tools are automatically discovered and registered on module load.
"""
from odoo import api, models, fields
import logging

_logger = logging.getLogger(__name__)


class AIToolProvider(models.AbstractModel):
    """
    Abstract mixin for modules that provide AI tools.

    To register AI tools from your module:

    1. Create a model that inherits from 'loomworks.ai.tool.provider'
    2. Implement _get_tool_definitions() returning a list of tool dicts
    3. Tools are auto-registered on module installation

    Example:
        class StudioToolProvider(models.AbstractModel):
            _name = 'studio.tool.provider'
            _inherit = 'loomworks.ai.tool.provider'

            @api.model
            def _get_tool_definitions(self):
                return [
                    {
                        'name': 'Create Studio App',
                        'technical_name': 'studio_create_app',
                        'category': 'action',
                        'description': 'Create a new custom application via Studio',
                        'parameters_schema': {...},
                        'implementation_method': 'loomworks_studio.tools.create_app',
                        'risk_level': 'moderate',
                    },
                ]
    """
    _name = 'loomworks.ai.tool.provider'
    _description = 'AI Tool Provider Mixin'

    @api.model
    def _get_tool_definitions(self):
        """
        Override in inheriting models to return tool definitions.

        Returns:
            list: List of dicts, each defining an AI tool with keys:
                - name (str): Display name
                - technical_name (str): Unique snake_case identifier
                - category (str): 'data', 'action', 'report', or 'system'
                - description (str): Detailed description for AI
                - parameters_schema (dict): JSON Schema for parameters
                - implementation_method (str): Python method path
                - risk_level (str): 'safe', 'moderate', 'high', or 'critical'
                - requires_confirmation (bool, optional): Default False
        """
        return []

    @api.model
    def _register_tools(self):
        """
        Register all tools from this provider.
        Called automatically on module installation.
        """
        AITool = self.env['loomworks.ai.tool']
        definitions = self._get_tool_definitions()

        for tool_def in definitions:
            technical_name = tool_def.get('technical_name')
            if not technical_name:
                _logger.warning("Tool definition missing technical_name: %s", tool_def)
                continue

            # Check if tool already exists
            existing = AITool.search([
                ('technical_name', '=', technical_name)
            ], limit=1)

            tool_vals = {
                'name': tool_def.get('name', technical_name),
                'technical_name': technical_name,
                'category': tool_def.get('category', 'data'),
                'description': tool_def.get('description', ''),
                'parameters_schema': json.dumps(tool_def.get('parameters_schema', {
                    'type': 'object',
                    'properties': {},
                    'required': []
                })),
                'implementation_method': tool_def.get('implementation_method', ''),
                'risk_level': tool_def.get('risk_level', 'safe'),
                'requires_confirmation': tool_def.get('requires_confirmation', False),
                'active': True,
            }

            if existing:
                existing.write(tool_vals)
                _logger.info("Updated AI tool: %s", technical_name)
            else:
                AITool.create(tool_vals)
                _logger.info("Registered AI tool: %s", technical_name)

    @api.model
    def _unregister_tools(self):
        """
        Unregister all tools from this provider.
        Called on module uninstallation.
        """
        AITool = self.env['loomworks.ai.tool']
        definitions = self._get_tool_definitions()

        for tool_def in definitions:
            technical_name = tool_def.get('technical_name')
            if technical_name:
                AITool.search([
                    ('technical_name', '=', technical_name)
                ]).unlink()
                _logger.info("Unregistered AI tool: %s", technical_name)


class AIToolRegistry(models.Model):
    """
    Registry for discovering all tool providers across installed modules.

    This model maintains a central registry of all ToolProvider implementations
    and orchestrates tool registration/unregistration.
    """
    _name = 'loomworks.ai.tool.registry'
    _description = 'AI Tool Registry'

    @api.model
    def discover_and_register_all_tools(self):
        """
        Discover all ToolProvider implementations and register their tools.
        Called on loomworks_ai module post_init_hook.
        """
        # Find all models that inherit from loomworks.ai.tool.provider
        provider_models = []
        for model_name, model_class in self.env.registry.items():
            if model_name == 'loomworks.ai.tool.provider':
                continue
            parents = getattr(model_class, '_inherit', [])
            if isinstance(parents, str):
                parents = [parents]
            if 'loomworks.ai.tool.provider' in parents:
                provider_models.append(model_name)

        _logger.info("Discovered %d AI tool providers: %s", len(provider_models), provider_models)

        for model_name in provider_models:
            try:
                provider = self.env[model_name]
                provider._register_tools()
            except Exception as e:
                _logger.exception("Failed to register tools from %s: %s", model_name, e)

    @api.model
    def refresh_tools(self):
        """
        Refresh all tool registrations. Useful after module updates.
        """
        self.discover_and_register_all_tools()
```

#### Example: Studio Tool Provider (Phase 3.1)

```python
# loomworks_studio/models/studio_tool_provider.py
from odoo import api, models

class StudioToolProvider(models.AbstractModel):
    _name = 'studio.tool.provider'
    _inherit = 'loomworks.ai.tool.provider'

    @api.model
    def _get_tool_definitions(self):
        return [
            {
                'name': 'Create Studio App',
                'technical_name': 'studio_create_app',
                'category': 'action',
                'description': '''Create a new custom application using Studio.
                    Parameters:
                    - app_name: Name for the new application
                    - app_description: Optional description
                    - icon: Font Awesome icon class (e.g., "fa-building")
                    - color: Color index (0-11)

                    This creates a new Studio app with a root menu and initial model.
                ''',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'app_name': {'type': 'string', 'description': 'Application name'},
                        'app_description': {'type': 'string', 'description': 'Description'},
                        'icon': {'type': 'string', 'default': 'fa-cube'},
                        'color': {'type': 'integer', 'minimum': 0, 'maximum': 11}
                    },
                    'required': ['app_name']
                },
                'implementation_method': 'loomworks_studio.services.tools.create_studio_app',
                'risk_level': 'moderate',
                'requires_confirmation': True,
            },
            {
                'name': 'Add Field to Model',
                'technical_name': 'studio_add_field',
                'category': 'action',
                'description': '''Add a new field to an existing model via Studio.
                    Supports all standard field types: char, text, integer, float,
                    boolean, date, datetime, selection, many2one, one2many, many2many.
                ''',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'model_name': {'type': 'string', 'description': 'Target model technical name'},
                        'field_name': {'type': 'string', 'description': 'Field technical name'},
                        'field_label': {'type': 'string', 'description': 'Field display label'},
                        'field_type': {
                            'type': 'string',
                            'enum': ['char', 'text', 'integer', 'float', 'boolean',
                                    'date', 'datetime', 'selection', 'many2one',
                                    'one2many', 'many2many', 'binary', 'html']
                        },
                        'required': {'type': 'boolean', 'default': False},
                    },
                    'required': ['model_name', 'field_name', 'field_type']
                },
                'implementation_method': 'loomworks_studio.services.tools.add_field_to_model',
                'risk_level': 'moderate',
            },
            {
                'name': 'Customize View',
                'technical_name': 'studio_customize_view',
                'category': 'action',
                'description': 'Modify a view using Studio customization capabilities.',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'model_name': {'type': 'string'},
                        'view_type': {'type': 'string', 'enum': ['form', 'list', 'kanban']},
                        'changes': {'type': 'array', 'items': {'type': 'object'}}
                    },
                    'required': ['model_name', 'view_type', 'changes']
                },
                'implementation_method': 'loomworks_studio.services.tools.customize_view',
                'risk_level': 'moderate',
            },
        ]
```

#### Example: FSM Tool Provider (Phase 3.3)

```python
# loomworks_fsm/models/fsm_tool_provider.py
from odoo import api, models

class FSMToolProvider(models.AbstractModel):
    _name = 'fsm.tool.provider'
    _inherit = 'loomworks.ai.tool.provider'

    @api.model
    def _get_tool_definitions(self):
        return [
            {
                'name': 'Dispatch Technician',
                'technical_name': 'fsm_dispatch_technician',
                'category': 'action',
                'description': '''Assign a field service task to a technician.
                    Considers technician availability, location, and skills.
                ''',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'task_id': {'type': 'integer', 'description': 'FSM task ID'},
                        'technician_id': {'type': 'integer', 'description': 'Employee ID'},
                        'scheduled_date': {'type': 'string', 'format': 'date'},
                    },
                    'required': ['task_id']
                },
                'implementation_method': 'loomworks_fsm.services.tools.dispatch_technician',
                'risk_level': 'moderate',
            },
            {
                'name': 'Complete FSM Task',
                'technical_name': 'fsm_complete_task',
                'category': 'action',
                'description': 'Mark a field service task as completed with signature.',
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'task_id': {'type': 'integer'},
                        'completion_notes': {'type': 'string'},
                        'materials_used': {'type': 'array', 'items': {'type': 'object'}},
                    },
                    'required': ['task_id']
                },
                'implementation_method': 'loomworks_fsm.services.tools.complete_task',
                'risk_level': 'moderate',
            },
        ]
```

#### Module Hook for Auto-Registration

Each module using the ToolProvider pattern adds a post_init_hook:

```python
# loomworks_studio/__manifest__.py
{
    'name': 'Loomworks Studio',
    ...
    'depends': ['loomworks_ai', ...],
    'post_init_hook': '_register_studio_tools',
    'uninstall_hook': '_unregister_studio_tools',
}

# loomworks_studio/__init__.py
def _register_studio_tools(env):
    env['studio.tool.provider']._register_tools()

def _unregister_studio_tools(env):
    env['studio.tool.provider']._unregister_tools()
```

#### JavaScript Registry for Frontend Tools

For frontend-only tools (e.g., UI actions), a JavaScript registry complements the Python pattern:

```javascript
// odoo/addons/web/static/src/core/ai/ai_tool_registry.js
/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * AI Tool Registry for frontend-defined tools.
 *
 * Modules can register frontend tools that the AI can invoke:
 *
 * registry.category("ai_tools").add("open_studio_editor", {
 *     name: "Open Studio Editor",
 *     description: "Opens the Studio view editor for the current view",
 *     execute: async (env, params) => {
 *         await env.services.studio.enterEditMode();
 *     },
 * });
 */
export const aiToolRegistry = registry.category("ai_tools");

// Core tools registered by default
aiToolRegistry.add("navigate_to_view", {
    name: "Navigate to View",
    description: "Navigate to a specific view or action",
    execute: async (env, { actionId, viewType }) => {
        await env.services.action.doAction(actionId, { viewType });
    },
});

aiToolRegistry.add("open_record", {
    name: "Open Record",
    description: "Open a specific record in form view",
    execute: async (env, { model, resId }) => {
        await env.services.action.doAction({
            type: 'ir.actions.act_window',
            res_model: model,
            res_id: resId,
            views: [[false, 'form']],
        });
    },
});
```

#### 2.2.4 `ai_operation_log.py` - Audit Trail

```python
# -*- coding: utf-8 -*-
from odoo import models, fields, api
import json

class AIOperationLog(models.Model):
    """
    Comprehensive audit log of all AI operations.
    Stores before/after state for rollback and compliance.
    """
    _name = 'loomworks.ai.operation.log'
    _description = 'AI Operation Log'
    _order = 'create_date desc'

    session_id = fields.Many2one(
        'loomworks.ai.session',
        string='Session',
        required=True,
        ondelete='cascade'
    )
    agent_id = fields.Many2one(
        'loomworks.ai.agent',
        related='session_id.agent_id',
        store=True
    )
    user_id = fields.Many2one(
        'res.users',
        related='session_id.user_id',
        store=True
    )

    # Operation details
    tool_name = fields.Char(
        string='Tool Name',
        required=True
    )
    operation_type = fields.Selection([
        ('search', 'Search'),
        ('read', 'Read'),
        ('create', 'Create'),
        ('write', 'Update'),
        ('unlink', 'Delete'),
        ('action', 'Execute Action'),
        ('report', 'Generate Report'),
        ('other', 'Other'),
    ], string='Operation Type', required=True)

    # Target model and records
    model_name = fields.Char(
        string='Model Name'
    )
    record_ids = fields.Char(
        string='Record IDs (JSON)',
        help='JSON array of affected record IDs'
    )
    record_count = fields.Integer(
        string='Record Count',
        compute='_compute_record_count'
    )

    # Input/Output data
    input_data = fields.Text(
        string='Input Parameters (JSON)'
    )
    output_data = fields.Text(
        string='Output Data (JSON)'
    )

    # Before/After state for rollback
    values_before = fields.Text(
        string='Values Before (JSON)',
        help='Record state before modification'
    )
    values_after = fields.Text(
        string='Values After (JSON)',
        help='Record state after modification'
    )

    # Execution status
    state = fields.Selection([
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('error', 'Error'),
        ('rolled_back', 'Rolled Back'),
        ('skipped', 'Skipped'),
    ], string='State', default='pending', required=True)

    error_message = fields.Text(
        string='Error Message'
    )

    # Performance metrics
    execution_time_ms = fields.Integer(
        string='Execution Time (ms)'
    )

    # AI reasoning
    ai_reasoning = fields.Text(
        string='AI Reasoning',
        help='Why the AI chose this operation'
    )

    @api.depends('record_ids')
    def _compute_record_count(self):
        for log in self:
            if log.record_ids:
                try:
                    ids = json.loads(log.record_ids)
                    log.record_count = len(ids) if isinstance(ids, list) else 1
                except json.JSONDecodeError:
                    log.record_count = 0
            else:
                log.record_count = 0

    def get_undo_operations(self):
        """
        Generate operations to undo this change.
        Returns dict with model, operation, and values.
        """
        self.ensure_one()
        if self.operation_type == 'create':
            # Undo create = delete
            return {
                'type': 'unlink',
                'model': self.model_name,
                'ids': json.loads(self.record_ids) if self.record_ids else []
            }
        elif self.operation_type == 'write':
            # Undo write = restore previous values
            return {
                'type': 'write',
                'model': self.model_name,
                'ids': json.loads(self.record_ids) if self.record_ids else [],
                'values': json.loads(self.values_before) if self.values_before else {}
            }
        elif self.operation_type == 'unlink':
            # Undo delete = recreate (if we have the data)
            if self.values_before:
                return {
                    'type': 'create',
                    'model': self.model_name,
                    'values': json.loads(self.values_before)
                }
        return None

    @api.model
    def create_log(self, session_id, tool_name, operation_type, **kwargs):
        """Convenience method to create operation logs."""
        return self.create({
            'session_id': session_id,
            'tool_name': tool_name,
            'operation_type': operation_type,
            'model_name': kwargs.get('model_name'),
            'record_ids': json.dumps(kwargs.get('record_ids', [])),
            'input_data': json.dumps(kwargs.get('input_data', {})),
            'output_data': json.dumps(kwargs.get('output_data', {})),
            'values_before': json.dumps(kwargs.get('values_before', {})),
            'values_after': json.dumps(kwargs.get('values_after', {})),
            'state': kwargs.get('state', 'success'),
            'error_message': kwargs.get('error_message'),
            'execution_time_ms': kwargs.get('execution_time_ms'),
            'ai_reasoning': kwargs.get('ai_reasoning'),
        })
```

#### 2.2.5 `ai_sandbox.py` - Security Sandbox

```python
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import AccessError, UserError
import json
import time
from contextlib import contextmanager

class AISandbox(models.AbstractModel):
    """
    Security sandbox for AI operations.
    Provides isolated execution with rollback capability.
    """
    _name = 'loomworks.ai.sandbox'
    _description = 'AI Operation Sandbox'

    # Models that AI cannot access under any circumstances
    FORBIDDEN_MODELS = [
        'res.users',
        'res.users.log',
        'ir.config_parameter',
        'ir.rule',
        'ir.model.access',
        'ir.module.module',
        'ir.cron',
        'ir.mail_server',
        'base.automation',
    ]

    # Fields that should never be exposed to AI
    FORBIDDEN_FIELDS = [
        'password',
        'password_crypt',
        'api_key',
        'secret',
        'token',
        'oauth_access_token',
    ]

    @api.model
    def validate_model_access(self, model_name, operation, agent):
        """
        Validate if the agent can access the specified model.
        Raises AccessError if access is denied.
        """
        # Check forbidden models
        if model_name in self.FORBIDDEN_MODELS:
            raise AccessError(
                f"Access to model '{model_name}' is not permitted for AI agents."
            )

        # Check agent-specific restrictions
        if not agent.check_model_access(model_name, operation):
            raise AccessError(
                f"Agent '{agent.name}' is not permitted to {operation} on '{model_name}'."
            )

        # Verify user has access (AI inherits user permissions)
        try:
            self.env[model_name].check_access_rights(operation)
        except AccessError as e:
            raise AccessError(
                f"User does not have {operation} access to '{model_name}': {str(e)}"
            )

        return True

    @api.model
    def sanitize_values(self, model_name, values, operation='write'):
        """
        Remove forbidden fields from values dict.
        Returns sanitized values.
        """
        if not values:
            return values

        sanitized = dict(values)
        model = self.env[model_name]

        # Remove forbidden fields
        for field_name in list(sanitized.keys()):
            if field_name in self.FORBIDDEN_FIELDS:
                del sanitized[field_name]
                continue

            # Check if field exists
            if field_name not in model._fields:
                del sanitized[field_name]
                continue

            field = model._fields[field_name]

            # Don't allow modifying computed fields
            if field.compute and not field.store:
                del sanitized[field_name]
                continue

            # Don't allow modifying readonly fields (except on create)
            if field.readonly and operation != 'create':
                del sanitized[field_name]

        return sanitized

    @api.model
    def sanitize_domain(self, model_name, domain):
        """
        Validate and sanitize search domain.
        Prevents injection attacks and forbidden field access.
        """
        if not domain:
            return []

        sanitized = []
        model = self.env[model_name]

        for element in domain:
            if isinstance(element, str):
                # Operators like '&', '|', '!'
                if element in ('&', '|', '!'):
                    sanitized.append(element)
            elif isinstance(element, (list, tuple)) and len(element) == 3:
                field_name, operator, value = element

                # Check field is not forbidden
                if field_name.split('.')[0] in self.FORBIDDEN_FIELDS:
                    continue

                # Validate operator
                valid_operators = [
                    '=', '!=', '>', '>=', '<', '<=',
                    'in', 'not in', 'like', 'ilike',
                    '=like', '=ilike', 'child_of', 'parent_of'
                ]
                if operator not in valid_operators:
                    continue

                sanitized.append((field_name, operator, value))

        return sanitized

    @api.model
    def capture_record_state(self, model_name, record_ids, fields_to_capture=None):
        """
        Capture current state of records for potential rollback.
        Returns dict mapping record IDs to their field values.
        """
        if not record_ids:
            return {}

        model = self.env[model_name]
        records = model.browse(record_ids).exists()

        if not records:
            return {}

        # Determine which fields to capture
        if fields_to_capture:
            field_names = [f for f in fields_to_capture if f in model._fields]
        else:
            # Capture all stored, non-computed fields
            field_names = [
                name for name, field in model._fields.items()
                if field.store and not (field.compute and not field.store)
                and name not in self.FORBIDDEN_FIELDS
                and name not in ['create_uid', 'create_date', 'write_uid', 'write_date']
            ]

        state = {}
        for record in records:
            record_data = {}
            for field_name in field_names:
                try:
                    value = record[field_name]
                    # Convert to serializable format
                    if hasattr(value, 'ids'):
                        record_data[field_name] = value.ids
                    elif isinstance(value, (int, float, str, bool, type(None))):
                        record_data[field_name] = value
                    else:
                        record_data[field_name] = str(value)
                except Exception:
                    pass
            state[record.id] = record_data

        return state

    @api.model
    @contextmanager
    def sandboxed_execution(self, session, agent, operation_desc=''):
        """
        Context manager for sandboxed AI operation execution.
        Handles savepoints, logging, and error recovery.

        Usage:
            with sandbox.sandboxed_execution(session, agent, 'create sale order') as ctx:
                # Perform operations
                ctx['records_created'] = new_records.ids
        """
        start_time = time.time()
        context = {
            'savepoint': None,
            'records_created': [],
            'records_modified': [],
            'records_deleted': [],
            'error': None,
        }

        # Create savepoint if enabled
        if agent.use_savepoints:
            savepoint_name = session.create_savepoint()
            context['savepoint'] = savepoint_name

        try:
            yield context

            # Success - release savepoint
            if context['savepoint']:
                session.release_savepoint()

        except Exception as e:
            context['error'] = str(e)

            # Rollback on error if enabled
            if agent.auto_rollback_on_error and context['savepoint']:
                try:
                    session.rollback_to_savepoint()
                except Exception:
                    pass  # Savepoint may already be released

            raise

        finally:
            # Log execution time
            execution_time = int((time.time() - start_time) * 1000)
            context['execution_time_ms'] = execution_time

    @api.model
    def execute_with_limits(self, session, agent, func, *args, **kwargs):
        """
        Execute a function with operation limits.
        Tracks operation count and enforces limits.
        """
        # Get current turn's operation count
        turn_ops = session.get_context('turn_operation_count') or 0

        if turn_ops >= agent.max_operations_per_turn:
            raise UserError(
                f"Maximum operations per turn ({agent.max_operations_per_turn}) exceeded. "
                "Please start a new conversation turn."
            )

        # Execute the function
        result = func(*args, **kwargs)

        # Increment counter
        session.update_context('turn_operation_count', turn_ops + 1)

        return result
```

---

### 2.3 MCP Server Implementation

#### `services/odoo_mcp_server.py`

```python
# -*- coding: utf-8 -*-
"""
MCP (Model Context Protocol) Server for Odoo Operations.

This module implements an MCP server that exposes Odoo functionality
to Claude AI agents. It provides tools for CRUD operations, action
execution, and report generation.

Based on MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
"""

from mcp.server.fastmcp import FastMCP
from typing import Any, Optional
import json
import logging

_logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP(
    "Loomworks Odoo MCP Server",
    json_response=True
)


class OdooMCPContext:
    """
    Holds the Odoo environment context for MCP tool execution.
    Must be initialized before tool calls.
    """
    env = None
    session = None
    agent = None
    sandbox = None

    @classmethod
    def initialize(cls, env, session, agent):
        """Initialize context with Odoo environment."""
        cls.env = env
        cls.session = session
        cls.agent = agent
        cls.sandbox = env['loomworks.ai.sandbox']


# =============================================================================
# MCP TOOLS
# =============================================================================

@mcp.tool()
def search_records(
    model: str,
    domain: list = None,
    fields: list = None,
    limit: int = 80,
    offset: int = 0,
    order: str = None
) -> dict:
    """
    Search for records in any Odoo model.

    Use this tool to find existing records before creating new ones,
    to check if data exists, or to retrieve information for reports.

    Args:
        model: The Odoo model name (e.g., 'sale.order', 'res.partner')
        domain: Search filter as list of tuples. Example: [('state', '=', 'draft')]
        fields: List of field names to return. If empty, returns all fields.
        limit: Maximum number of records to return (default: 80, max: 500)
        offset: Number of records to skip for pagination
        order: Sort order (e.g., 'create_date desc, name')

    Returns:
        Dictionary with 'count' (total matching), 'records' (list of dicts),
        and 'model' name for reference.

    Examples:
        - Find all draft sales orders: search_records('sale.order', [('state', '=', 'draft')])
        - Get customer list: search_records('res.partner', [('customer_rank', '>', 0)], ['name', 'email'])
    """
    ctx = OdooMCPContext

    # Validate access
    ctx.sandbox.validate_model_access(model, 'read', ctx.agent)

    # Sanitize domain
    safe_domain = ctx.sandbox.sanitize_domain(model, domain or [])

    # Enforce limits
    limit = min(limit, 500)

    # Execute search
    Model = ctx.env[model]
    total_count = Model.search_count(safe_domain)
    records = Model.search(safe_domain, limit=limit, offset=offset, order=order)

    # Read specified fields or get default display fields
    if fields:
        safe_fields = [f for f in fields if f not in ctx.sandbox.FORBIDDEN_FIELDS]
    else:
        # Return commonly useful fields
        safe_fields = ['id', 'display_name', 'create_date', 'write_date']
        if 'state' in Model._fields:
            safe_fields.append('state')
        if 'active' in Model._fields:
            safe_fields.append('active')

    records_data = records.read(safe_fields)

    # Log the operation
    ctx.env['loomworks.ai.operation.log'].create_log(
        session_id=ctx.session.id,
        tool_name='search_records',
        operation_type='search',
        model_name=model,
        record_ids=records.ids,
        input_data={'domain': safe_domain, 'fields': safe_fields, 'limit': limit},
        output_data={'count': total_count, 'returned': len(records_data)},
    )

    return {
        'model': model,
        'count': total_count,
        'records': records_data,
        'has_more': total_count > offset + len(records_data)
    }


@mcp.tool()
def create_record(
    model: str,
    values: dict,
    context: dict = None
) -> dict:
    """
    Create a new record in an Odoo model.

    Use this tool to create new business data like sales orders,
    invoices, products, contacts, etc.

    Args:
        model: The Odoo model name (e.g., 'sale.order', 'res.partner')
        values: Dictionary of field values for the new record
        context: Optional Odoo context overrides

    Returns:
        Dictionary with 'id' of created record, 'display_name', and key fields.

    Examples:
        - Create contact: create_record('res.partner', {'name': 'John Doe', 'email': 'john@example.com'})
        - Create product: create_record('product.product', {'name': 'Widget', 'list_price': 99.99})
    """
    ctx = OdooMCPContext

    # Validate access
    ctx.sandbox.validate_model_access(model, 'create', ctx.agent)

    # Sanitize values
    safe_values = ctx.sandbox.sanitize_values(model, values, 'create')

    # Execute with sandbox
    with ctx.sandbox.sandboxed_execution(ctx.session, ctx.agent, f'create {model}') as sandbox_ctx:
        Model = ctx.env[model]
        if context:
            Model = Model.with_context(**context)

        record = Model.create(safe_values)
        sandbox_ctx['records_created'] = record.ids

        # Capture created state
        created_state = ctx.sandbox.capture_record_state(model, record.ids)

        # Log operation
        ctx.env['loomworks.ai.operation.log'].create_log(
            session_id=ctx.session.id,
            tool_name='create_record',
            operation_type='create',
            model_name=model,
            record_ids=record.ids,
            input_data=safe_values,
            values_after=created_state,
            execution_time_ms=sandbox_ctx.get('execution_time_ms'),
        )

    return {
        'id': record.id,
        'display_name': record.display_name,
        'model': model,
        'created': True
    }


@mcp.tool()
def update_record(
    model: str,
    record_id: int,
    values: dict,
    context: dict = None
) -> dict:
    """
    Update an existing record in an Odoo model.

    Use this tool to modify existing data. Always search for records
    first to confirm they exist before updating.

    Args:
        model: The Odoo model name
        record_id: ID of the record to update
        values: Dictionary of field values to change
        context: Optional Odoo context overrides

    Returns:
        Dictionary with 'id', 'display_name', and 'updated' status.

    Examples:
        - Update contact email: update_record('res.partner', 42, {'email': 'new@example.com'})
        - Mark order as sent: update_record('sale.order', 15, {'state': 'sent'})
    """
    ctx = OdooMCPContext

    # Validate access
    ctx.sandbox.validate_model_access(model, 'write', ctx.agent)

    # Sanitize values
    safe_values = ctx.sandbox.sanitize_values(model, values, 'write')

    with ctx.sandbox.sandboxed_execution(ctx.session, ctx.agent, f'update {model}') as sandbox_ctx:
        Model = ctx.env[model]
        record = Model.browse(record_id)

        if not record.exists():
            return {'error': f'Record {model}({record_id}) not found', 'updated': False}

        # Capture state before
        state_before = ctx.sandbox.capture_record_state(model, [record_id])

        # Apply context if provided
        if context:
            record = record.with_context(**context)

        # Perform update
        record.write(safe_values)
        sandbox_ctx['records_modified'] = [record_id]

        # Capture state after
        state_after = ctx.sandbox.capture_record_state(model, [record_id])

        # Log operation
        ctx.env['loomworks.ai.operation.log'].create_log(
            session_id=ctx.session.id,
            tool_name='update_record',
            operation_type='write',
            model_name=model,
            record_ids=[record_id],
            input_data=safe_values,
            values_before=state_before,
            values_after=state_after,
            execution_time_ms=sandbox_ctx.get('execution_time_ms'),
        )

    return {
        'id': record.id,
        'display_name': record.display_name,
        'model': model,
        'updated': True
    }


@mcp.tool()
def delete_record(
    model: str,
    record_id: int,
    confirm: bool = False
) -> dict:
    """
    Delete a record from an Odoo model.

    WARNING: This is a destructive operation. The record will be
    permanently removed. Use with caution.

    Args:
        model: The Odoo model name
        record_id: ID of the record to delete
        confirm: Must be True to actually delete (safety check)

    Returns:
        Dictionary with 'deleted' status and record info.

    Examples:
        - Delete draft order: delete_record('sale.order', 99, confirm=True)
    """
    ctx = OdooMCPContext

    if not confirm:
        return {
            'error': 'Deletion requires confirm=True for safety',
            'deleted': False,
            'hint': 'Set confirm=True to proceed with deletion'
        }

    # Validate access
    ctx.sandbox.validate_model_access(model, 'unlink', ctx.agent)

    with ctx.sandbox.sandboxed_execution(ctx.session, ctx.agent, f'delete {model}') as sandbox_ctx:
        Model = ctx.env[model]
        record = Model.browse(record_id)

        if not record.exists():
            return {'error': f'Record {model}({record_id}) not found', 'deleted': False}

        # Capture state before deletion for potential undo
        state_before = ctx.sandbox.capture_record_state(model, [record_id])
        display_name = record.display_name

        # Perform deletion
        record.unlink()
        sandbox_ctx['records_deleted'] = [record_id]

        # Log operation
        ctx.env['loomworks.ai.operation.log'].create_log(
            session_id=ctx.session.id,
            tool_name='delete_record',
            operation_type='unlink',
            model_name=model,
            record_ids=[record_id],
            values_before=state_before,
            execution_time_ms=sandbox_ctx.get('execution_time_ms'),
        )

    return {
        'id': record_id,
        'display_name': display_name,
        'model': model,
        'deleted': True
    }


@mcp.tool()
def execute_action(
    model: str,
    record_ids: list,
    action: str,
    parameters: dict = None
) -> dict:
    """
    Execute a business action or workflow on records.

    Use this tool to trigger state transitions, confirmations,
    validations, and other business logic.

    Args:
        model: The Odoo model name
        record_ids: List of record IDs to act on
        action: Method name to call (e.g., 'action_confirm', 'action_done')
        parameters: Optional parameters to pass to the action

    Returns:
        Dictionary with 'success' status and any action results.

    Common actions:
        - sale.order: action_confirm, action_cancel, action_draft
        - purchase.order: button_confirm, button_cancel
        - account.move: action_post, button_draft
        - stock.picking: action_confirm, button_validate

    Examples:
        - Confirm sale: execute_action('sale.order', [15], 'action_confirm')
        - Post invoice: execute_action('account.move', [42], 'action_post')
    """
    ctx = OdooMCPContext

    # Validate access
    ctx.sandbox.validate_model_access(model, 'write', ctx.agent)

    # Security: only allow known safe actions
    SAFE_ACTIONS = {
        'sale.order': ['action_confirm', 'action_cancel', 'action_draft', 'action_quotation_send'],
        'purchase.order': ['button_confirm', 'button_cancel', 'button_draft'],
        'account.move': ['action_post', 'button_draft', 'button_cancel'],
        'stock.picking': ['action_confirm', 'action_assign', 'button_validate'],
        'mrp.production': ['action_confirm', 'action_assign', 'button_mark_done'],
        'project.task': ['action_assign_to_me', 'action_open_task_form'],
        # Add more as needed
    }

    allowed_actions = SAFE_ACTIONS.get(model, [])
    if action not in allowed_actions and not action.startswith('action_'):
        return {
            'error': f"Action '{action}' is not in the allowed list for {model}",
            'allowed_actions': allowed_actions,
            'success': False
        }

    with ctx.sandbox.sandboxed_execution(ctx.session, ctx.agent, f'{action} on {model}') as sandbox_ctx:
        Model = ctx.env[model]
        records = Model.browse(record_ids)

        if not records.exists():
            return {'error': 'No valid records found', 'success': False}

        # Capture state before
        state_before = ctx.sandbox.capture_record_state(model, record_ids)

        # Execute the action
        method = getattr(records, action, None)
        if not method or not callable(method):
            return {'error': f"Method '{action}' not found on {model}", 'success': False}

        if parameters:
            result = method(**parameters)
        else:
            result = method()

        # Capture state after
        state_after = ctx.sandbox.capture_record_state(model, record_ids)

        # Log operation
        ctx.env['loomworks.ai.operation.log'].create_log(
            session_id=ctx.session.id,
            tool_name='execute_action',
            operation_type='action',
            model_name=model,
            record_ids=record_ids,
            input_data={'action': action, 'parameters': parameters},
            values_before=state_before,
            values_after=state_after,
            execution_time_ms=sandbox_ctx.get('execution_time_ms'),
        )

    return {
        'model': model,
        'record_ids': record_ids,
        'action': action,
        'success': True,
        'result': str(result) if result else None
    }


@mcp.tool()
def generate_report(
    report_type: str,
    model: str = None,
    domain: list = None,
    date_from: str = None,
    date_to: str = None,
    group_by: list = None,
    measures: list = None
) -> dict:
    """
    Generate business reports and analytics.

    Use this tool to create summaries, aggregations, and insights
    from business data.

    Args:
        report_type: Type of report ('summary', 'trend', 'breakdown', 'comparison')
        model: Odoo model to analyze
        domain: Filter criteria
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        group_by: Fields to group results by
        measures: Numeric fields to aggregate (sum, avg, count)

    Returns:
        Dictionary with report data including aggregations and breakdowns.

    Examples:
        - Sales by month: generate_report('trend', 'sale.order', group_by=['create_date:month'], measures=['amount_total'])
        - Revenue by customer: generate_report('breakdown', 'account.move.line', group_by=['partner_id'], measures=['balance'])
    """
    ctx = OdooMCPContext

    if not model:
        return {'error': 'Model is required for reports', 'success': False}

    # Validate access
    ctx.sandbox.validate_model_access(model, 'read', ctx.agent)

    # Build domain with date filters
    safe_domain = ctx.sandbox.sanitize_domain(model, domain or [])

    if date_from:
        safe_domain.append(('create_date', '>=', date_from))
    if date_to:
        safe_domain.append(('create_date', '<=', date_to))

    Model = ctx.env[model]

    # Execute read_group for aggregations
    if group_by and measures:
        # Validate fields exist
        valid_measures = [m for m in measures if m in Model._fields]
        valid_groups = []
        for g in group_by:
            field_name = g.split(':')[0]
            if field_name in Model._fields:
                valid_groups.append(g)

        if valid_measures and valid_groups:
            report_data = Model.read_group(
                safe_domain,
                fields=valid_measures,
                groupby=valid_groups,
                lazy=False
            )
        else:
            report_data = []
    else:
        # Simple count and totals
        report_data = {
            'total_count': Model.search_count(safe_domain),
        }

        # Add sums for numeric fields if measures specified
        if measures:
            records = Model.search(safe_domain, limit=10000)
            for measure in measures:
                if measure in Model._fields:
                    field = Model._fields[measure]
                    if field.type in ('integer', 'float', 'monetary'):
                        report_data[f'{measure}_sum'] = sum(records.mapped(measure))

    # Log operation
    ctx.env['loomworks.ai.operation.log'].create_log(
        session_id=ctx.session.id,
        tool_name='generate_report',
        operation_type='report',
        model_name=model,
        input_data={
            'report_type': report_type,
            'domain': safe_domain,
            'group_by': group_by,
            'measures': measures
        },
        output_data={'record_count': len(report_data) if isinstance(report_data, list) else 1},
    )

    return {
        'report_type': report_type,
        'model': model,
        'data': report_data,
        'success': True
    }


# =============================================================================
# MCP SERVER RUNNER
# =============================================================================

def create_mcp_server_for_session(env, session, agent):
    """
    Factory function to create an MCP server instance for a session.
    Initializes context and returns the server.
    """
    OdooMCPContext.initialize(env, session, agent)
    return mcp


def get_tool_schemas():
    """Return all tool schemas for Claude API registration."""
    return [
        {
            'name': 'search_records',
            'description': search_records.__doc__,
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'model': {'type': 'string', 'description': 'Odoo model name'},
                    'domain': {'type': 'array', 'description': 'Search domain'},
                    'fields': {'type': 'array', 'items': {'type': 'string'}},
                    'limit': {'type': 'integer', 'default': 80},
                    'offset': {'type': 'integer', 'default': 0},
                    'order': {'type': 'string'}
                },
                'required': ['model']
            }
        },
        {
            'name': 'create_record',
            'description': create_record.__doc__,
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'model': {'type': 'string'},
                    'values': {'type': 'object'},
                    'context': {'type': 'object'}
                },
                'required': ['model', 'values']
            }
        },
        {
            'name': 'update_record',
            'description': update_record.__doc__,
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'model': {'type': 'string'},
                    'record_id': {'type': 'integer'},
                    'values': {'type': 'object'},
                    'context': {'type': 'object'}
                },
                'required': ['model', 'record_id', 'values']
            }
        },
        {
            'name': 'delete_record',
            'description': delete_record.__doc__,
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'model': {'type': 'string'},
                    'record_id': {'type': 'integer'},
                    'confirm': {'type': 'boolean', 'default': False}
                },
                'required': ['model', 'record_id']
            }
        },
        {
            'name': 'execute_action',
            'description': execute_action.__doc__,
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'model': {'type': 'string'},
                    'record_ids': {'type': 'array', 'items': {'type': 'integer'}},
                    'action': {'type': 'string'},
                    'parameters': {'type': 'object'}
                },
                'required': ['model', 'record_ids', 'action']
            }
        },
        {
            'name': 'generate_report',
            'description': generate_report.__doc__,
            'inputSchema': {
                'type': 'object',
                'properties': {
                    'report_type': {'type': 'string', 'enum': ['summary', 'trend', 'breakdown', 'comparison']},
                    'model': {'type': 'string'},
                    'domain': {'type': 'array'},
                    'date_from': {'type': 'string', 'format': 'date'},
                    'date_to': {'type': 'string', 'format': 'date'},
                    'group_by': {'type': 'array', 'items': {'type': 'string'}},
                    'measures': {'type': 'array', 'items': {'type': 'string'}}
                },
                'required': ['report_type']
            }
        }
    ]
```

---

### 2.4 Claude Client Service

#### `services/claude_client.py`

```python
# -*- coding: utf-8 -*-
"""
Claude Agent SDK client wrapper for Odoo integration.

Provides a clean interface between Odoo and the Claude Agent SDK,
handling session management, tool execution, and response streaming.

Based on: https://platform.claude.com/docs/en/agent-sdk/python
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Optional, Callable

_logger = logging.getLogger(__name__)

# Note: In production, these would come from claude_agent_sdk package
# For now, we define the expected interfaces


class LoomworksClaudeClient:
    """
    Wrapper around Claude Agent SDK for Loomworks ERP.
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

        # Import tool schemas
        from .odoo_mcp_server import get_tool_schemas, OdooMCPContext
        self.tool_schemas = get_tool_schemas()
        OdooMCPContext.initialize(env, session, agent)

    async def connect(self):
        """Establish connection to Claude API."""
        try:
            # In production, this would use actual Claude SDK
            # from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
            #
            # options = ClaudeAgentOptions(
            #     allowed_tools=self.tool_schemas,
            #     permission_mode=self._get_permission_mode(),
            #     can_use_tool=self._permission_handler
            # )
            # self._client = ClaudeSDKClient(options)
            # await self._client.connect()

            self._connected = True
            _logger.info(f"Claude client connected for session {self.session.uuid}")

        except Exception as e:
            _logger.error(f"Failed to connect Claude client: {e}")
            raise

    async def disconnect(self):
        """Close connection to Claude API."""
        if self._client:
            # await self._client.disconnect()
            pass
        self._connected = False
        _logger.info(f"Claude client disconnected for session {self.session.uuid}")

    async def send_message(self, message: str) -> AsyncGenerator[dict, None]:
        """
        Send a message to Claude and yield response chunks.

        Args:
            message: User message text

        Yields:
            Response chunks with type and content
        """
        if not self._connected:
            await self.connect()

        # Store user message
        self.session.add_message(role='user', content=message)
        self.session.touch()

        # Reset turn operation counter
        self.session.update_context('turn_operation_count', 0)

        try:
            # Build conversation context
            system_prompt = self.agent.get_effective_system_prompt()
            history = self.session.get_conversation_history()

            # In production, use actual Claude SDK:
            # await self._client.query(message)
            # async for response in self._client.receive_response():
            #     if isinstance(response, AssistantMessage):
            #         yield {'type': 'text', 'content': response.content}
            #     elif isinstance(response, ToolUseBlock):
            #         yield {'type': 'tool_call', 'tool': response.name, 'input': response.input}

            # Placeholder response for development
            yield {
                'type': 'text',
                'content': f"[Development Mode] Received: {message}"
            }
            yield {
                'type': 'done',
                'usage': {'input_tokens': 100, 'output_tokens': 50}
            }

        except Exception as e:
            _logger.error(f"Error processing message: {e}")
            yield {
                'type': 'error',
                'content': str(e)
            }

    async def execute_tool(self, tool_name: str, tool_input: dict) -> dict:
        """
        Execute a tool call from Claude.

        Args:
            tool_name: Name of the tool to execute
            tool_input: Input parameters for the tool

        Returns:
            Tool execution result
        """
        from .odoo_mcp_server import (
            search_records, create_record, update_record,
            delete_record, execute_action, generate_report
        )

        tools = {
            'search_records': search_records,
            'create_record': create_record,
            'update_record': update_record,
            'delete_record': delete_record,
            'execute_action': execute_action,
            'generate_report': generate_report,
        }

        if tool_name not in tools:
            return {'error': f'Unknown tool: {tool_name}'}

        try:
            result = tools[tool_name](**tool_input)
            return result
        except Exception as e:
            _logger.error(f"Tool execution error ({tool_name}): {e}")
            return {'error': str(e)}

    def _get_permission_mode(self) -> str:
        """Map agent permission mode to Claude SDK mode."""
        mode_map = {
            'default': 'default',
            'accept_reads': 'default',
            'accept_edits': 'acceptEdits',
            'supervised': 'default',
        }
        return mode_map.get(self.agent.permission_mode, 'default')

    async def _permission_handler(
        self,
        tool_name: str,
        input_data: dict,
        context: dict
    ):
        """
        Custom permission handler for tool execution.
        Implements Loomworks security policies.
        """
        # Check if tool requires confirmation
        tool = self.env['loomworks.ai.tool'].search([
            ('technical_name', '=', tool_name)
        ], limit=1)

        if tool and tool.requires_confirmation:
            # Would trigger user confirmation in UI
            pass

        # Auto-approve read operations in accept_reads mode
        if self.agent.permission_mode == 'accept_reads':
            if tool_name in ['search_records', 'generate_report']:
                return {'decision': 'allow', 'updated_input': input_data}

        # Auto-approve edits in accept_edits mode
        if self.agent.permission_mode == 'accept_edits':
            return {'decision': 'allow', 'updated_input': input_data}

        # Default: allow (actual permission check happens in sandbox)
        return {'decision': 'allow', 'updated_input': input_data}


def create_claude_client(env, session, agent) -> LoomworksClaudeClient:
    """Factory function to create Claude client instance."""
    return LoomworksClaudeClient(env, session, agent)
```

---

### 2.5 Controller Endpoints

#### `controllers/ai_controller.py`

```python
# -*- coding: utf-8 -*-
"""
HTTP/JSON-RPC controllers for AI chat functionality.

Provides REST and JSON-RPC endpoints for:
- Session management
- Message sending/receiving
- Operation history
- Rollback operations

Based on Odoo 18 controller patterns:
https://www.odoo.com/documentation/18.0/developer/reference/backend/http.html
"""

from odoo import http
from odoo.http import request, Response
import json
import logging
import asyncio

_logger = logging.getLogger(__name__)


class AIController(http.Controller):
    """
    Main controller for AI chat API endpoints.
    All endpoints require user authentication.
    """

    # =========================================================================
    # SESSION MANAGEMENT
    # =========================================================================

    @http.route('/loomworks/ai/session/create', type='json', auth='user', methods=['POST'])
    def create_session(self, agent_id=None, **kwargs):
        """
        Create a new AI chat session.

        Request:
            {
                "agent_id": 1  // Optional, uses default if not provided
            }

        Response:
            {
                "session_id": 1,
                "uuid": "abc-123-...",
                "agent_name": "Loomworks Assistant"
            }
        """
        Agent = request.env['loomworks.ai.agent']
        Session = request.env['loomworks.ai.session']

        # Get or find default agent
        if agent_id:
            agent = Agent.browse(agent_id)
            if not agent.exists():
                return {'error': 'Agent not found'}
        else:
            agent = Agent.search([
                ('company_id', '=', request.env.company.id),
                ('active', '=', True)
            ], limit=1)
            if not agent:
                return {'error': 'No active AI agent configured'}

        # Create session
        session = Session.create({
            'agent_id': agent.id,
            'user_id': request.env.user.id,
        })

        return {
            'session_id': session.id,
            'uuid': session.uuid,
            'agent_name': agent.name,
            'agent_id': agent.id,
        }

    @http.route('/loomworks/ai/session/<string:uuid>', type='json', auth='user', methods=['GET'])
    def get_session(self, uuid, **kwargs):
        """
        Get session details and recent messages.

        Response:
            {
                "session_id": 1,
                "state": "active",
                "messages": [...],
                "operations": [...]
            }
        """
        session = request.env['loomworks.ai.session'].search([
            ('uuid', '=', uuid),
            ('user_id', '=', request.env.user.id)
        ], limit=1)

        if not session:
            return {'error': 'Session not found'}

        return {
            'session_id': session.id,
            'uuid': session.uuid,
            'state': session.state,
            'agent_name': session.agent_id.name,
            'message_count': session.message_count,
            'operation_count': session.operation_count,
            'messages': self._format_messages(session.message_ids[-50:]),
            'has_uncommitted_changes': session.has_uncommitted_changes,
        }

    @http.route('/loomworks/ai/session/<string:uuid>/close', type='json', auth='user', methods=['POST'])
    def close_session(self, uuid, **kwargs):
        """
        Close an active session.
        """
        session = request.env['loomworks.ai.session'].search([
            ('uuid', '=', uuid),
            ('user_id', '=', request.env.user.id)
        ], limit=1)

        if not session:
            return {'error': 'Session not found'}

        # Release any savepoints
        if session.has_uncommitted_changes:
            session.release_savepoint()

        session.write({'state': 'completed'})

        return {'success': True, 'session_id': session.id}

    # =========================================================================
    # CHAT MESSAGING
    # =========================================================================

    @http.route('/loomworks/ai/chat', type='json', auth='user', methods=['POST'])
    def send_message(self, session_uuid, message, **kwargs):
        """
        Send a message to the AI and get response.

        Request:
            {
                "session_uuid": "abc-123-...",
                "message": "Create a new customer named John Doe"
            }

        Response:
            {
                "response": "I'll create that customer for you...",
                "tool_calls": [...],
                "operations": [...]
            }
        """
        session = request.env['loomworks.ai.session'].search([
            ('uuid', '=', session_uuid),
            ('user_id', '=', request.env.user.id),
            ('state', '=', 'active')
        ], limit=1)

        if not session:
            return {'error': 'Active session not found'}

        agent = session.agent_id

        # Create Claude client
        from ..services.claude_client import create_claude_client
        client = create_claude_client(request.env, session, agent)

        # Process message (synchronous wrapper for async)
        try:
            response_parts = []
            tool_calls = []

            async def process():
                async for chunk in client.send_message(message):
                    if chunk['type'] == 'text':
                        response_parts.append(chunk['content'])
                    elif chunk['type'] == 'tool_call':
                        tool_calls.append(chunk)

            # Run async code
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(process())
            finally:
                loop.close()

            # Store assistant response
            full_response = ''.join(response_parts)
            session.add_message(
                role='assistant',
                content=full_response,
                tool_calls=tool_calls if tool_calls else None
            )

            # Get operations performed in this turn
            recent_ops = request.env['loomworks.ai.operation.log'].search([
                ('session_id', '=', session.id)
            ], order='create_date desc', limit=10)

            return {
                'response': full_response,
                'tool_calls': tool_calls,
                'operations': self._format_operations(recent_ops),
                'session_state': session.state,
            }

        except Exception as e:
            _logger.error(f"Chat error: {e}")
            return {'error': str(e)}

    @http.route('/loomworks/ai/chat/stream', type='http', auth='user', methods=['POST'])
    def send_message_stream(self, **kwargs):
        """
        Send a message and receive streaming response via Server-Sent Events.

        Request body (JSON):
            {
                "session_uuid": "abc-123-...",
                "message": "..."
            }

        Response: SSE stream with events:
            - data: {"type": "text", "content": "..."}
            - data: {"type": "tool_call", "tool": "...", "input": {...}}
            - data: {"type": "done"}
        """
        try:
            data = json.loads(request.httprequest.data)
            session_uuid = data.get('session_uuid')
            message = data.get('message')
        except json.JSONDecodeError:
            return Response(
                json.dumps({'error': 'Invalid JSON'}),
                content_type='application/json',
                status=400
            )

        session = request.env['loomworks.ai.session'].search([
            ('uuid', '=', session_uuid),
            ('user_id', '=', request.env.user.id),
            ('state', '=', 'active')
        ], limit=1)

        if not session:
            return Response(
                json.dumps({'error': 'Session not found'}),
                content_type='application/json',
                status=404
            )

        def generate():
            """Generator for SSE stream."""
            from ..services.claude_client import create_claude_client
            client = create_claude_client(request.env, session, session.agent_id)

            async def stream_response():
                async for chunk in client.send_message(message):
                    yield f"data: {json.dumps(chunk)}\n\n"

            # Run async generator
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                async_gen = stream_response()
                while True:
                    try:
                        chunk = loop.run_until_complete(async_gen.__anext__())
                        yield chunk
                    except StopAsyncIteration:
                        break
            finally:
                loop.close()

        return Response(
            generate(),
            content_type='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
            }
        )

    # =========================================================================
    # ROLLBACK OPERATIONS
    # =========================================================================

    @http.route('/loomworks/ai/session/<string:uuid>/rollback', type='json', auth='user', methods=['POST'])
    def rollback_session(self, uuid, **kwargs):
        """
        Rollback all uncommitted changes in the session.
        """
        session = request.env['loomworks.ai.session'].search([
            ('uuid', '=', uuid),
            ('user_id', '=', request.env.user.id)
        ], limit=1)

        if not session:
            return {'error': 'Session not found'}

        if not session.has_uncommitted_changes:
            return {'error': 'No uncommitted changes to rollback'}

        try:
            session.rollback_to_savepoint()
            return {
                'success': True,
                'message': 'Changes rolled back successfully'
            }
        except Exception as e:
            return {'error': str(e)}

    @http.route('/loomworks/ai/operation/<int:operation_id>/undo', type='json', auth='user', methods=['POST'])
    def undo_operation(self, operation_id, **kwargs):
        """
        Undo a specific operation from the log.
        """
        operation = request.env['loomworks.ai.operation.log'].browse(operation_id)

        if not operation.exists():
            return {'error': 'Operation not found'}

        # Verify user owns this operation
        if operation.user_id.id != request.env.user.id:
            return {'error': 'Access denied'}

        undo_ops = operation.get_undo_operations()
        if not undo_ops:
            return {'error': 'This operation cannot be undone'}

        try:
            # Execute undo
            Model = request.env[undo_ops['model']]
            if undo_ops['type'] == 'unlink':
                Model.browse(undo_ops['ids']).unlink()
            elif undo_ops['type'] == 'write':
                for rec_id, values in undo_ops['values'].items():
                    Model.browse(int(rec_id)).write(values)
            elif undo_ops['type'] == 'create':
                Model.create(undo_ops['values'])

            operation.write({'state': 'rolled_back'})

            return {'success': True, 'operation_id': operation_id}

        except Exception as e:
            return {'error': str(e)}

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _format_messages(self, messages):
        """Format message records for JSON response."""
        return [{
            'id': msg.id,
            'role': msg.role,
            'content': msg.content,
            'timestamp': msg.create_date.isoformat() if msg.create_date else None,
            'has_tool_calls': bool(msg.tool_calls_json),
        } for msg in messages]

    def _format_operations(self, operations):
        """Format operation records for JSON response."""
        return [{
            'id': op.id,
            'tool': op.tool_name,
            'type': op.operation_type,
            'model': op.model_name,
            'record_count': op.record_count,
            'state': op.state,
            'timestamp': op.create_date.isoformat() if op.create_date else None,
        } for op in operations]
```

---

### 2.6 Owl Chat Component Architecture

#### `static/src/components/ai_chat/ai_chat.js`

```javascript
/** @odoo-module **/

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { AIMessage } from "../ai_message/ai_message";

/**
 * Main AI Chat component providing conversational interface.
 *
 * Features:
 * - Message history display
 * - Streaming response rendering
 * - Tool call visualization
 * - Session management
 * - Keyboard shortcuts
 *
 * Based on Owl.js patterns:
 * https://www.odoo.com/documentation/18.0/developer/reference/frontend/owl_components.html
 */
export class AIChat extends Component {
    static template = "loomworks_ai.AIChat";
    static components = { AIMessage };
    static props = {
        sessionUuid: { type: String, optional: true },
        agentId: { type: Number, optional: true },
        onClose: { type: Function, optional: true },
    };

    setup() {
        // Services
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.user = useService("user");

        // State
        this.state = useState({
            messages: [],
            inputText: "",
            isLoading: false,
            isConnected: false,
            sessionUuid: this.props.sessionUuid || null,
            agentName: "",
            error: null,
            streamingContent: "",
            operations: [],
            hasUncommittedChanges: false,
        });

        // Refs
        this.messagesRef = useRef("messages");
        this.inputRef = useRef("input");

        // Event source for streaming
        this.eventSource = null;

        // Lifecycle
        onMounted(() => this.onMounted());
        onWillUnmount(() => this.onWillUnmount());
    }

    async onMounted() {
        // Initialize or resume session
        if (this.state.sessionUuid) {
            await this.loadSession();
        } else {
            await this.createSession();
        }

        // Focus input
        this.inputRef.el?.focus();

        // Keyboard shortcut handler
        this.keyHandler = (e) => this.handleKeyboard(e);
        document.addEventListener("keydown", this.keyHandler);
    }

    onWillUnmount() {
        // Cleanup
        if (this.eventSource) {
            this.eventSource.close();
        }
        document.removeEventListener("keydown", this.keyHandler);
    }

    // =========================================================================
    // SESSION MANAGEMENT
    // =========================================================================

    async createSession() {
        try {
            const result = await this.rpc("/loomworks/ai/session/create", {
                agent_id: this.props.agentId,
            });

            if (result.error) {
                this.state.error = result.error;
                return;
            }

            this.state.sessionUuid = result.uuid;
            this.state.agentName = result.agent_name;
            this.state.isConnected = true;

            // Add welcome message
            this.addSystemMessage(
                `Connected to ${result.agent_name}. How can I help you today?`
            );

        } catch (error) {
            this.state.error = "Failed to create session";
            console.error("Session creation error:", error);
        }
    }

    async loadSession() {
        try {
            const result = await this.rpc(
                `/loomworks/ai/session/${this.state.sessionUuid}`,
                {}
            );

            if (result.error) {
                this.state.error = result.error;
                return;
            }

            this.state.agentName = result.agent_name;
            this.state.messages = result.messages.map(m => ({
                id: m.id,
                role: m.role,
                content: m.content,
                timestamp: new Date(m.timestamp),
                hasToolCalls: m.has_tool_calls,
            }));
            this.state.hasUncommittedChanges = result.has_uncommitted_changes;
            this.state.isConnected = true;

            this.scrollToBottom();

        } catch (error) {
            this.state.error = "Failed to load session";
            console.error("Session load error:", error);
        }
    }

    async closeSession() {
        if (!this.state.sessionUuid) return;

        try {
            await this.rpc(
                `/loomworks/ai/session/${this.state.sessionUuid}/close`,
                {}
            );

            if (this.props.onClose) {
                this.props.onClose();
            }

        } catch (error) {
            console.error("Session close error:", error);
        }
    }

    // =========================================================================
    // MESSAGE HANDLING
    // =========================================================================

    async sendMessage() {
        const text = this.state.inputText.trim();
        if (!text || this.state.isLoading) return;

        // Add user message
        this.addMessage("user", text);
        this.state.inputText = "";
        this.state.isLoading = true;
        this.state.error = null;

        try {
            // Use streaming endpoint
            await this.sendMessageStreaming(text);
        } catch (error) {
            this.state.error = "Failed to send message";
            console.error("Send message error:", error);
        } finally {
            this.state.isLoading = false;
        }
    }

    async sendMessageStreaming(text) {
        return new Promise((resolve, reject) => {
            // Start with empty streaming content
            this.state.streamingContent = "";

            // Create fetch request for SSE
            fetch("/loomworks/ai/chat/stream", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    session_uuid: this.state.sessionUuid,
                    message: text,
                }),
                credentials: "same-origin",
            })
            .then(response => {
                const reader = response.body.getReader();
                const decoder = new TextDecoder();

                const processStream = async () => {
                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;

                        const chunk = decoder.decode(value);
                        const lines = chunk.split("\n");

                        for (const line of lines) {
                            if (line.startsWith("data: ")) {
                                const data = JSON.parse(line.slice(6));
                                this.handleStreamChunk(data);
                            }
                        }
                    }
                };

                return processStream();
            })
            .then(() => {
                // Finalize message
                if (this.state.streamingContent) {
                    this.addMessage("assistant", this.state.streamingContent);
                    this.state.streamingContent = "";
                }
                resolve();
            })
            .catch(error => {
                reject(error);
            });
        });
    }

    handleStreamChunk(data) {
        switch (data.type) {
            case "text":
                this.state.streamingContent += data.content;
                this.scrollToBottom();
                break;

            case "tool_call":
                // Show tool call indicator
                this.addSystemMessage(
                    `Executing: ${data.tool}`,
                    { isToolCall: true, toolInput: data.input }
                );
                break;

            case "error":
                this.state.error = data.content;
                break;

            case "done":
                // Handle completion
                if (data.operations) {
                    this.state.operations = data.operations;
                }
                break;
        }
    }

    addMessage(role, content, metadata = {}) {
        this.state.messages.push({
            id: Date.now(),
            role,
            content,
            timestamp: new Date(),
            ...metadata,
        });
        this.scrollToBottom();
    }

    addSystemMessage(content, metadata = {}) {
        this.addMessage("system", content, metadata);
    }

    // =========================================================================
    // ROLLBACK
    // =========================================================================

    async rollback() {
        if (!this.state.hasUncommittedChanges) {
            this.notification.add("No changes to rollback", { type: "warning" });
            return;
        }

        try {
            const result = await this.rpc(
                `/loomworks/ai/session/${this.state.sessionUuid}/rollback`,
                {}
            );

            if (result.success) {
                this.notification.add("Changes rolled back successfully", { type: "success" });
                this.state.hasUncommittedChanges = false;
                this.addSystemMessage("All recent changes have been rolled back.");
            } else {
                this.notification.add(result.error, { type: "danger" });
            }

        } catch (error) {
            this.notification.add("Rollback failed", { type: "danger" });
        }
    }

    // =========================================================================
    // UI HELPERS
    // =========================================================================

    scrollToBottom() {
        requestAnimationFrame(() => {
            if (this.messagesRef.el) {
                this.messagesRef.el.scrollTop = this.messagesRef.el.scrollHeight;
            }
        });
    }

    handleKeyboard(e) {
        // Ctrl+Enter to send
        if (e.ctrlKey && e.key === "Enter") {
            this.sendMessage();
        }

        // Escape to close
        if (e.key === "Escape" && this.props.onClose) {
            this.closeSession();
        }

        // Ctrl+Z for rollback
        if (e.ctrlKey && e.key === "z" && this.state.hasUncommittedChanges) {
            e.preventDefault();
            this.rollback();
        }
    }

    onInputKeydown(e) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            this.sendMessage();
        }
    }

    get formattedOperations() {
        return this.state.operations.map(op => ({
            ...op,
            icon: this.getOperationIcon(op.type),
            label: `${op.type} ${op.record_count} ${op.model}`,
        }));
    }

    getOperationIcon(type) {
        const icons = {
            search: "fa-search",
            create: "fa-plus",
            write: "fa-edit",
            unlink: "fa-trash",
            action: "fa-play",
            report: "fa-chart-bar",
        };
        return icons[type] || "fa-cog";
    }
}
```

#### `static/src/components/ai_chat/ai_chat.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<templates xml:space="preserve">

    <t t-name="loomworks_ai.AIChat">
        <div class="loomworks-ai-chat d-flex flex-column h-100">
            <!-- Header -->
            <div class="ai-chat-header d-flex align-items-center justify-content-between p-3 border-bottom">
                <div class="d-flex align-items-center">
                    <i class="fa fa-robot me-2 text-primary"/>
                    <span class="fw-bold" t-esc="state.agentName or 'AI Assistant'"/>
                    <span t-if="state.isConnected" class="ms-2 badge bg-success">Connected</span>
                    <span t-else="" class="ms-2 badge bg-secondary">Disconnected</span>
                </div>
                <div class="d-flex gap-2">
                    <button t-if="state.hasUncommittedChanges"
                            class="btn btn-sm btn-outline-warning"
                            t-on-click="rollback"
                            title="Rollback changes (Ctrl+Z)">
                        <i class="fa fa-undo"/> Rollback
                    </button>
                    <button class="btn btn-sm btn-outline-secondary"
                            t-on-click="closeSession"
                            title="Close session (Esc)">
                        <i class="fa fa-times"/>
                    </button>
                </div>
            </div>

            <!-- Error Banner -->
            <div t-if="state.error" class="alert alert-danger m-2 mb-0">
                <i class="fa fa-exclamation-triangle me-2"/>
                <t t-esc="state.error"/>
                <button type="button" class="btn-close" t-on-click="() => this.state.error = null"/>
            </div>

            <!-- Messages -->
            <div class="ai-chat-messages flex-grow-1 overflow-auto p-3" t-ref="messages">
                <t t-foreach="state.messages" t-as="message" t-key="message.id">
                    <AIMessage
                        role="message.role"
                        content="message.content"
                        timestamp="message.timestamp"
                        isToolCall="message.isToolCall"
                    />
                </t>

                <!-- Streaming content -->
                <t t-if="state.streamingContent">
                    <AIMessage
                        role="'assistant'"
                        content="state.streamingContent"
                        isStreaming="true"
                    />
                </t>

                <!-- Loading indicator -->
                <div t-if="state.isLoading and !state.streamingContent"
                     class="ai-message ai-message-assistant">
                    <div class="message-content">
                        <div class="typing-indicator">
                            <span></span>
                            <span></span>
                            <span></span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Operations Panel (collapsible) -->
            <div t-if="state.operations.length" class="ai-operations-panel border-top">
                <details>
                    <summary class="p-2 cursor-pointer">
                        <i class="fa fa-history me-2"/>
                        Recent Operations (<t t-esc="state.operations.length"/>)
                    </summary>
                    <div class="operations-list p-2">
                        <t t-foreach="formattedOperations" t-as="op" t-key="op.id">
                            <div class="operation-item d-flex align-items-center gap-2 py-1">
                                <i t-attf-class="fa {{op.icon}} text-muted"/>
                                <span t-esc="op.label"/>
                                <span t-attf-class="badge bg-{{op.state === 'success' ? 'success' : 'danger'}} ms-auto">
                                    <t t-esc="op.state"/>
                                </span>
                            </div>
                        </t>
                    </div>
                </details>
            </div>

            <!-- Input Area -->
            <div class="ai-chat-input p-3 border-top">
                <div class="input-group">
                    <textarea
                        t-ref="input"
                        class="form-control"
                        placeholder="Type a message... (Enter to send, Shift+Enter for new line)"
                        t-model="state.inputText"
                        t-on-keydown="onInputKeydown"
                        rows="1"
                        t-att-disabled="state.isLoading or !state.isConnected"
                    />
                    <button
                        class="btn btn-primary"
                        t-on-click="sendMessage"
                        t-att-disabled="state.isLoading or !state.inputText.trim() or !state.isConnected">
                        <i t-attf-class="fa {{state.isLoading ? 'fa-spinner fa-spin' : 'fa-paper-plane'}}"/>
                    </button>
                </div>
                <small class="text-muted mt-1 d-block">
                    Ctrl+Enter to send | Ctrl+Z to rollback | Esc to close
                </small>
            </div>
        </div>
    </t>

</templates>
```

#### `static/src/components/ai_chat/ai_chat.scss`

```scss
.loomworks-ai-chat {
    background: var(--o-view-background-color, #fff);
    min-height: 400px;
    max-height: 80vh;

    .ai-chat-header {
        background: var(--o-webclient-color-scheme, #f8f9fa);
    }

    .ai-chat-messages {
        background: var(--o-form-lightsecondary, #f8f9fa);
    }

    .ai-chat-input {
        background: var(--o-view-background-color, #fff);

        textarea {
            resize: none;
            max-height: 150px;

            &:focus {
                border-color: var(--o-brand-primary, #714b67);
                box-shadow: 0 0 0 0.2rem rgba(113, 75, 103, 0.25);
            }
        }
    }

    .typing-indicator {
        display: flex;
        gap: 4px;
        padding: 8px;

        span {
            width: 8px;
            height: 8px;
            background: var(--o-brand-primary, #714b67);
            border-radius: 50%;
            animation: typing 1.4s infinite;

            &:nth-child(2) { animation-delay: 0.2s; }
            &:nth-child(3) { animation-delay: 0.4s; }
        }
    }

    @keyframes typing {
        0%, 100% { opacity: 0.3; transform: scale(0.8); }
        50% { opacity: 1; transform: scale(1); }
    }

    .ai-operations-panel {
        background: var(--o-webclient-color-scheme, #f8f9fa);
        max-height: 150px;
        overflow-y: auto;

        summary {
            user-select: none;

            &:hover {
                background: rgba(0, 0, 0, 0.05);
            }
        }

        .operation-item {
            font-size: 0.875rem;
        }
    }
}

// Message component styles
.ai-message {
    margin-bottom: 1rem;
    max-width: 85%;

    &.ai-message-user {
        margin-left: auto;

        .message-content {
            background: var(--o-brand-primary, #714b67);
            color: white;
            border-radius: 1rem 1rem 0.25rem 1rem;
        }
    }

    &.ai-message-assistant {
        margin-right: auto;

        .message-content {
            background: white;
            border: 1px solid var(--o-gray-300, #dee2e6);
            border-radius: 1rem 1rem 1rem 0.25rem;
        }
    }

    &.ai-message-system {
        margin: 0 auto;
        max-width: 70%;
        text-align: center;

        .message-content {
            background: var(--o-gray-200, #e9ecef);
            color: var(--o-gray-700, #495057);
            border-radius: 0.5rem;
            font-size: 0.875rem;
        }
    }

    .message-content {
        padding: 0.75rem 1rem;
        word-wrap: break-word;
        white-space: pre-wrap;
    }

    .message-timestamp {
        font-size: 0.75rem;
        color: var(--o-gray-500, #6c757d);
        margin-top: 0.25rem;
    }

    &.streaming .message-content::after {
        content: '|';
        animation: blink 1s infinite;
    }

    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0; }
    }
}
```

---

### 2.7 Security Model

#### Access Control Layers

```
Layer 1: Odoo User Permissions
├── AI inherits authenticated user's access rights
├── ir.model.access rules enforced
└── ir.rule record-level security applied

Layer 2: Agent Configuration
├── Allowed/Blocked model lists
├── CRUD operation permissions (can_create, can_write, can_unlink)
└── Action execution permissions

Layer 3: Sandbox Enforcement
├── FORBIDDEN_MODELS hardcoded blocklist
├── FORBIDDEN_FIELDS stripped from all operations
└── Domain/value sanitization
└── Operation limits per turn

Layer 4: Audit & Rollback
├── All operations logged to ai.operation.log
├── Before/after state captured
└── Savepoint-based transaction rollback
```

#### Sensitive Models Blocklist

```python
FORBIDDEN_MODELS = [
    # Authentication & Security
    'res.users',           # User accounts
    'res.users.log',       # Login history
    'ir.config_parameter', # System parameters (may contain secrets)

    # Access Control
    'ir.rule',             # Record rules
    'ir.model.access',     # Model access rights

    # System Configuration
    'ir.module.module',    # Module management
    'ir.cron',             # Scheduled actions
    'ir.mail_server',      # Email servers
    'base.automation',     # Automated actions

    # Potentially Sensitive
    'mail.mail',           # Outgoing emails
    'ir.attachment',       # File attachments
]
```

#### Security XML Rules

```xml
<!-- security/ai_security_rules.xml -->
<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <!-- AI Agent Access: Managers only -->
    <record id="ai_agent_rule_company" model="ir.rule">
        <field name="name">AI Agent: Company Isolation</field>
        <field name="model_id" ref="model_loomworks_ai_agent"/>
        <field name="domain_force">[('company_id', 'in', company_ids)]</field>
    </record>

    <!-- Sessions: Users see only their own -->
    <record id="ai_session_rule_own" model="ir.rule">
        <field name="name">AI Session: Own Sessions Only</field>
        <field name="model_id" ref="model_loomworks_ai_session"/>
        <field name="domain_force">[('user_id', '=', user.id)]</field>
        <field name="groups" eval="[(4, ref('base.group_user'))]"/>
    </record>

    <!-- Operation Logs: Users see only their own -->
    <record id="ai_operation_log_rule_own" model="ir.rule">
        <field name="name">AI Operation Log: Own Only</field>
        <field name="model_id" ref="model_loomworks_ai_operation_log"/>
        <field name="domain_force">[('user_id', '=', user.id)]</field>
        <field name="groups" eval="[(4, ref('base.group_user'))]"/>
    </record>

    <!-- Managers can see all sessions in their company -->
    <record id="ai_session_rule_manager" model="ir.rule">
        <field name="name">AI Session: Manager Access</field>
        <field name="model_id" ref="model_loomworks_ai_session"/>
        <field name="domain_force">[('company_id', 'in', company_ids)]</field>
        <field name="groups" eval="[(4, ref('loomworks_ai.group_ai_manager'))]"/>
    </record>

</odoo>
```

---

## Implementation Steps

### Phase 2.1: Core Models (Week 5-6)

- [ ] 2.1.1 Create module scaffold (`__init__.py`, `__manifest__.py`)
- [ ] 2.1.2 Implement `ai_agent.py` model with all fields and methods
- [ ] 2.1.3 Implement `ai_session.py` model with message handling
- [ ] 2.1.4 Implement `ai_tool.py` model with schema support
- [ ] 2.1.5 Implement `ai_operation_log.py` with undo support
- [ ] 2.1.6 Implement `ai_sandbox.py` abstract model
- [ ] 2.1.7 Create security CSV and XML files
- [ ] 2.1.8 Create default tool data XML
- [ ] 2.1.9 Write unit tests for models

**Dependencies**: None (foundation work)

### Phase 2.2: MCP Server (Week 6-7)

- [ ] 2.2.1 Implement `odoo_mcp_server.py` with FastMCP
- [ ] 2.2.2 Implement `search_records` tool with sanitization
- [ ] 2.2.3 Implement `create_record` tool with logging
- [ ] 2.2.4 Implement `update_record` tool with before/after capture
- [ ] 2.2.5 Implement `delete_record` tool with confirmation
- [ ] 2.2.6 Implement `execute_action` tool with safe action list
- [ ] 2.2.7 Implement `generate_report` tool with aggregations
- [ ] 2.2.8 Write integration tests for all tools

**Dependencies**: 2.1 (requires models)

### Phase 2.3: Claude Client (Week 7-8)

- [ ] 2.3.1 Implement `claude_client.py` wrapper
- [ ] 2.3.2 Implement session connection management
- [ ] 2.3.3 Implement streaming message handling
- [ ] 2.3.4 Implement tool execution routing
- [ ] 2.3.5 Implement permission handler
- [ ] 2.3.6 Add error handling and retry logic
- [ ] 2.3.7 Write integration tests with mock Claude API

**Dependencies**: 2.1, 2.2 (requires models and MCP tools)

### Phase 2.4: HTTP Controllers (Week 8-9)

- [ ] 2.4.1 Implement session create/get/close endpoints
- [ ] 2.4.2 Implement synchronous chat endpoint
- [ ] 2.4.3 Implement SSE streaming endpoint
- [ ] 2.4.4 Implement rollback endpoints
- [ ] 2.4.5 Implement operation undo endpoint
- [ ] 2.4.6 Add rate limiting and error handling
- [ ] 2.4.7 Write API integration tests

**Dependencies**: 2.3 (requires Claude client)

### Phase 2.5: Owl Components (Week 9-10)

- [ ] 2.5.1 Implement `AIChat` main component
- [ ] 2.5.2 Implement `AIMessage` component
- [ ] 2.5.3 Implement `AISidebar` component for global access
- [ ] 2.5.4 Create SCSS styles
- [ ] 2.5.5 Register assets in `assets.xml`
- [ ] 2.5.6 Add keyboard shortcuts
- [ ] 2.5.7 Implement streaming response rendering
- [ ] 2.5.8 Write JavaScript unit tests

**Dependencies**: 2.4 (requires API endpoints)

### Phase 2.6: Integration & Testing (Week 10)

- [ ] 2.6.1 End-to-end workflow testing
- [ ] 2.6.2 Performance benchmarking (< 3s response time)
- [ ] 2.6.3 Security penetration testing
- [ ] 2.6.4 Multi-user concurrent testing
- [ ] 2.6.5 Documentation and examples
- [ ] 2.6.6 Demo data creation

**Dependencies**: All previous phases

### Phase 2.7: Contextual AI Navbar (Week 11-12)

> **Full Specification**: See `/openspec/FEATURE_CONTEXTUAL_AI_NAVBAR.md`

The Contextual AI Navbar transforms the basic AI button into an intelligent, context-aware assistant dropdown that proactively offers relevant suggestions based on user activity.

#### Key Design Principle: Event-Driven Architecture

The AI only "thinks" about context when triggered by user actions - **no constant polling or monitoring**.

```javascript
// Triggers that invoke context analysis
const CONTEXT_TRIGGERS = [
    'view_loaded',        // User opens a form/list/kanban
    'record_created',     // User clicks "Create" button
    'record_selected',    // User clicks into a record
    'action_executed',    // User runs a workflow action
    'error_occurred',     // Something failed
    'idle_threshold',     // User paused for 10+ seconds
    'search_performed',   // User searched for something
    'tab_switched',       // User switched browser tab back
];

// NOT constantly monitoring:
// - No polling intervals
// - No continuous screenshot capture
// - No always-on pattern analysis
```

#### Key Components

| Component | Description |
|-----------|-------------|
| `ai_context_service.js` | Event-driven context detection (triggers on user actions) |
| `ai_suggestion_service.js` | Generates proactive suggestions with debouncing |
| `AINavbarDropdown` | Owl component with suggestions, quick actions, chat |
| `loomworks.ai.user.settings` | Simplified user preferences (3 fields) |

#### Implementation Tasks

- [ ] 2.7.1 Create `ai_context_service.js` (event-driven triggers)
- [ ] 2.7.2 Create `ai_suggestion_service.js` with debounced analysis
- [ ] 2.7.3 Create `AINavbarDropdown` Owl component
- [ ] 2.7.4 Create `AIContextIndicator` sub-component
- [ ] 2.7.5 Create `AISuggestionList` sub-component
- [ ] 2.7.6 Create `loomworks.ai.user.settings` model (simplified)
- [ ] 2.7.7 Create AI settings modal component (simplified)
- [ ] 2.7.8 Integrate with existing `AIChat` component
- [ ] 2.7.9 Implement backend suggestion triggers
- [ ] 2.7.10 Hook context triggers into view controllers
- [ ] 2.7.11 Add idle detection (10s threshold)
- [ ] 2.7.12 Write tests (unit + integration)
- [ ] 2.7.13 Documentation and UX testing

**Dependencies**: 2.5 (requires base AI components), 2.6 (integration tested)

#### Event Flow

```
User Action (trigger)
       │
       ▼
   Debounce (2-3 seconds)
       │
       ▼
   Capture Context
   - Current view state
   - Screenshot (if helpful)
   - Recent actions buffer
       │
       ▼
   AI Analysis (single call)
       │
       ▼
   Show suggestion (if any) or stay quiet
```

#### Suggestion Triggers

| Trigger Event | Context | Suggestion |
|---------------|---------|------------|
| `view_loaded` (sales order form) | model: sale.order | Check customer credit status |
| `record_created` (new quote) | state: draft | "Customer has overdue invoices" |
| `error_occurred` | lastError: validation | "I can help fix that" |
| `search_performed` (no results) | results: 0 | "Try broader search?" |
| `idle_threshold` (10s on empty form) | hasUnsavedChanges: false | "Need help getting started?" |

#### User Settings (Simplified)

```python
class AIUserSettings(models.Model):
    _name = 'loomworks.ai.user.settings'

    user_id = fields.Many2one('res.users', required=True)

    # Proactive suggestions on/off
    enable_suggestions = fields.Boolean(default=True)

    # How often to suggest
    suggestion_frequency = fields.Selection([
        ('minimal', 'Minimal - Only critical issues'),
        ('normal', 'Normal - Helpful suggestions'),
        ('frequent', 'Frequent - More proactive'),
    ], default='normal')

    # Notification style
    notification_style = fields.Selection([
        ('badge', 'Badge only'),
        ('popup', 'Popup notification'),
    ], default='popup')
```

#### Privacy & Data Handling

- **Anthropic Privacy**: Data processed by Claude AI with strict privacy policies - not used for training
- **Event-Driven**: Analysis only on user actions, no constant monitoring
- **Metadata Only**: Field names sent, not actual field values
- **EULA Coverage**: Vision/screenshot analysis consent covered at signup
- **Simple Controls**: Users can disable suggestions or adjust frequency

---

## API Specifications

### Session Create

```
POST /loomworks/ai/session/create
Content-Type: application/json

Request:
{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "agent_id": 1  // optional
    }
}

Response:
{
    "jsonrpc": "2.0",
    "result": {
        "session_id": 42,
        "uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "agent_name": "Loomworks Assistant",
        "agent_id": 1
    }
}

Errors:
- "No active AI agent configured" - No agent found for company
- "Agent not found" - Invalid agent_id
```

### Send Message

```
POST /loomworks/ai/chat
Content-Type: application/json

Request:
{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "session_uuid": "a1b2c3d4-...",
        "message": "Find all draft sales orders"
    }
}

Response:
{
    "jsonrpc": "2.0",
    "result": {
        "response": "I found 5 draft sales orders...",
        "tool_calls": [
            {
                "tool": "search_records",
                "input": {"model": "sale.order", "domain": [["state", "=", "draft"]]}
            }
        ],
        "operations": [
            {
                "id": 100,
                "tool": "search_records",
                "type": "search",
                "model": "sale.order",
                "record_count": 5,
                "state": "success"
            }
        ],
        "session_state": "active"
    }
}
```

### Stream Message (SSE)

```
POST /loomworks/ai/chat/stream
Content-Type: application/json

Request Body:
{
    "session_uuid": "a1b2c3d4-...",
    "message": "Create a customer named Acme Corp"
}

Response: text/event-stream
data: {"type": "text", "content": "I'll create "}
data: {"type": "text", "content": "that customer "}
data: {"type": "tool_call", "tool": "create_record", "input": {...}}
data: {"type": "text", "content": "Done! Created customer Acme Corp with ID 42."}
data: {"type": "done", "operations": [...]}
```

### Rollback Session

```
POST /loomworks/ai/session/{uuid}/rollback
Content-Type: application/json

Request:
{
    "jsonrpc": "2.0",
    "method": "call",
    "params": {}
}

Response:
{
    "jsonrpc": "2.0",
    "result": {
        "success": true,
        "message": "Changes rolled back successfully"
    }
}

Errors:
- "No uncommitted changes to rollback"
- "Session not found"
```

---

## Testing Criteria

### Unit Tests

| Test | Description | Pass Criteria |
|------|-------------|---------------|
| `test_agent_model_access` | Verify forbidden models blocked | Raises AccessError for res.users |
| `test_agent_permission_modes` | Test all permission mode behaviors | Each mode correctly restricts operations |
| `test_session_savepoint` | Verify savepoint create/rollback | Database state correctly restored |
| `test_tool_search` | Test search_records tool | Returns correct results with sanitized domain |
| `test_tool_create` | Test create_record tool | Creates record with logged state |
| `test_tool_delete_confirm` | Test deletion requires confirm | Fails without confirm=True |
| `test_sandbox_forbidden_fields` | Verify password fields stripped | Sensitive fields removed from values |
| `test_operation_log_undo` | Test undo operation generation | Correct undo operations returned |

### Integration Tests

| Test | Description | Pass Criteria |
|------|-------------|---------------|
| `test_end_to_end_search` | Full search flow via API | Returns results within 3s |
| `test_end_to_end_create` | Full create flow with logging | Record created, logged, rollback works |
| `test_multi_user_isolation` | Two users can't see each other's sessions | Session queries filtered by user |
| `test_company_isolation` | Agents isolated by company | Agent only accessible to own company |
| `test_streaming_response` | SSE streaming works | Events received in correct order |
| `test_rollback_after_error` | Auto-rollback on operation error | Database unchanged after error |

### Performance Benchmarks

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| AI response time | < 3 seconds | Time from message send to first response chunk |
| Search 1000 records | < 500ms | search_records tool execution time |
| Create single record | < 200ms | create_record tool execution time |
| Rollback operation | < 100ms | Time to execute rollback_to_savepoint |
| Session load time | < 300ms | Time to load session with 50 messages |

### Security Tests

| Test | Description | Expected Result |
|------|-------------|-----------------|
| `test_sql_injection_domain` | Malicious domain input | Sanitized, no SQL error |
| `test_xss_message_content` | Script tags in messages | Escaped in UI |
| `test_unauthorized_model_access` | Access res.users via tool | AccessError raised |
| `test_session_hijacking` | Access another user's session | 404 or access denied |
| `test_rate_limiting` | Rapid-fire requests | Throttled after limit |

---

## Dependencies

### Python Packages

```
# requirements.txt additions
anthropic>=0.39.0          # Claude API client (until agent-sdk available)
mcp>=1.0.0                 # Model Context Protocol SDK
aiohttp>=3.9.0             # Async HTTP for streaming
```

### Claude Agent SDK (when available)

```
# Future requirement
claude-agent-sdk>=1.0.0    # Official Agent SDK
```

### Module Dependencies

```python
# __manifest__.py
{
    'name': 'Loomworks AI',
    'depends': [
        'base',
        'web',
        'mail',  # For activity tracking
    ],
}
```

---

## Core Modifications (Forked Odoo Architecture)

Since Loomworks ERP is a fully forked version of Odoo Community v18, we have the unique opportunity to embed AI as a first-class citizen directly in the core codebase rather than bolting it on as an addon. This section documents the specific core files to modify and the architectural approach for native AI integration.

### Architecture Philosophy: AI as Core vs Addon

```
Traditional Addon Approach (NOT our approach):
┌─────────────────────────────────────────────────┐
│                 Odoo Core                        │
│  ┌─────────────────────────────────────────┐    │
│  │            Web Client                    │    │
│  │  NavBar → ActionContainer → Views        │    │
│  └─────────────────────────────────────────┘    │
│                      │                           │
│           (addon hooks via registry)             │
│                      ▼                           │
│  ┌─────────────────────────────────────────┐    │
│  │          loomworks_ai addon              │    │
│  │  (systray item, sidebar, patched comps) │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘

Native Forked Approach (OUR approach):
┌─────────────────────────────────────────────────┐
│              Loomworks ERP Core                  │
│  ┌─────────────────────────────────────────┐    │
│  │       AI-Enhanced Web Client             │    │
│  │  NavBar + AIButton → ActionContainer     │    │
│  │        → Views + AIContextPanel          │    │
│  │                                          │    │
│  │  CommandPalette (Ctrl+K) → AI Commands   │    │
│  │  AIStatusIndicator → System Tray         │    │
│  └─────────────────────────────────────────┘    │
│                      │                           │
│  ┌─────────────────────────────────────────┐    │
│  │       AI-Enhanced ORM Layer              │    │
│  │  models.py → ai_operation_hooks          │    │
│  │  api.py → ai_context_manager             │    │
│  └─────────────────────────────────────────┘    │
│                      │                           │
│  ┌─────────────────────────────────────────┐    │
│  │       MCP Server (Core Service)          │    │
│  │  Started alongside Odoo HTTP server      │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

### 3.1 Core Web Client Modifications

#### 3.1.1 Files to Modify in `odoo/addons/web/`

| File | Modification Type | Purpose |
|------|------------------|---------|
| `static/src/webclient/webclient.js` | Extend | Add AI service initialization, AI status indicator |
| `static/src/webclient/webclient.xml` | Extend | Add AIAssistant component to WebClient template |
| `static/src/webclient/navbar/navbar.js` | Extend | Add AI button to navbar |
| `static/src/webclient/navbar/navbar.xml` | Extend | AI button markup in navbar template |
| `static/src/core/commands/command_service.js` | Extend | Add AI commands to command palette |
| `static/src/core/commands/command_palette.js` | Extend | AI-specific command palette behaviors |
| `views/webclient_templates.xml` | Extend | Add AI assets to web client bundle |

#### 3.1.2 WebClient AI Integration

**File: `odoo/addons/web/static/src/webclient/webclient.js`**

```javascript
/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

// Import core webclient
import { WebClient as OriginalWebClient } from "./webclient_original";

// Import AI components
import { AIAssistant } from "@web/ai/ai_assistant/ai_assistant";
import { AIStatusIndicator } from "@web/ai/ai_status/ai_status_indicator";

/**
 * AI-Enhanced WebClient
 *
 * Extends the standard Odoo WebClient with native AI capabilities:
 * - AI Assistant sidebar (toggleable)
 * - AI status indicator in system tray
 * - AI context awareness for current view
 * - Global AI keyboard shortcuts
 */
export class WebClient extends OriginalWebClient {
    static template = "web.WebClient";
    static components = {
        ...OriginalWebClient.components,
        AIAssistant,
        AIStatusIndicator,
    };

    setup() {
        super.setup();

        // AI-specific state
        this.aiState = useState({
            isAssistantOpen: false,
            currentContext: null,
            sessionUuid: null,
            isConnected: false,
        });

        // AI Service
        this.aiService = useService("ai");
        this.hotkeyService = useService("hotkey");

        onMounted(() => {
            this.setupAIHotkeys();
            this.initializeAIContext();
        });
    }

    setupAIHotkeys() {
        // Ctrl+Shift+A: Toggle AI Assistant
        this.hotkeyService.add("control+shift+a", () => {
            this.toggleAIAssistant();
        }, { global: true });

        // Alt+A: Quick AI query (opens assistant with focus on input)
        this.hotkeyService.add("alt+a", () => {
            this.openAIAssistant({ focusInput: true });
        }, { global: true });
    }

    initializeAIContext() {
        // Subscribe to route changes to update AI context
        this.env.bus.addEventListener("ACTION_MANAGER:UI-UPDATED", ({ detail }) => {
            this.updateAIContext(detail);
        });
    }

    updateAIContext(actionInfo) {
        // Provide AI with context about current view
        const context = {
            actionId: actionInfo.actionId,
            model: actionInfo.resModel,
            viewType: actionInfo.viewType,
            activeIds: actionInfo.resIds || [],
            breadcrumbs: this.actionService.currentController?.props?.breadcrumbs || [],
        };
        this.aiState.currentContext = context;

        if (this.aiService) {
            this.aiService.updateContext(context);
        }
    }

    toggleAIAssistant() {
        this.aiState.isAssistantOpen = !this.aiState.isAssistantOpen;
    }

    openAIAssistant(options = {}) {
        this.aiState.isAssistantOpen = true;
        if (options.focusInput) {
            // Will be handled by AIAssistant component
            this.env.bus.trigger("AI:FOCUS_INPUT");
        }
    }

    closeAIAssistant() {
        this.aiState.isAssistantOpen = false;
    }

    async onAIAction(action) {
        // Handle AI-initiated actions
        if (action.type === "navigate") {
            await this.actionService.doAction(action.payload);
        } else if (action.type === "refresh") {
            this.env.bus.trigger("CLEAR-CACHES");
        }
    }
}

// Re-export for registry
registry.category("actions").add("web_client", WebClient, { force: true });
```

**File: `odoo/addons/web/static/src/webclient/webclient.xml`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<templates xml:space="preserve">

    <!-- AI-Enhanced WebClient Template -->
    <t t-name="web.WebClient">
        <body class="o_web_client" t-att-class="{ 'o_ai_assistant_open': aiState.isAssistantOpen }">
            <NavBar/>
            <ActionContainer/>
            <MainComponentsContainer/>

            <!-- AI Status Indicator (always visible in system tray area) -->
            <AIStatusIndicator
                isConnected="aiState.isConnected"
                onToggle="() => this.toggleAIAssistant()"
            />

            <!-- AI Assistant Sidebar -->
            <t t-if="aiState.isAssistantOpen">
                <AIAssistant
                    context="aiState.currentContext"
                    sessionUuid="aiState.sessionUuid"
                    onClose="() => this.closeAIAssistant()"
                    onAction="(action) => this.onAIAction(action)"
                />
            </t>
        </body>
    </t>

</templates>
```

#### 3.1.3 Navbar AI Button

**File: `odoo/addons/web/static/src/webclient/navbar/navbar.xml`** (modification)

```xml
<!-- Add AI button to navbar systray area -->
<t t-inherit="web.NavBar" t-inherit-mode="extension">
    <xpath expr="//div[hasclass('o_menu_systray')]" position="inside">
        <div class="o_nav_entry o_ai_nav_button" t-on-click="onAIButtonClick">
            <button class="btn btn-link" title="AI Assistant (Ctrl+Shift+A)">
                <i class="fa fa-robot"/>
                <span class="d-none d-md-inline ms-1">AI</span>
                <t t-if="aiState.hasUnreadSuggestions">
                    <span class="badge bg-primary rounded-pill ms-1">
                        <t t-esc="aiState.unreadCount"/>
                    </span>
                </t>
            </button>
        </div>
    </xpath>
</t>
```

#### 3.1.4 Command Palette AI Integration

**File: `odoo/addons/web/static/src/core/ai/ai_command_provider.js`** (new file)

```javascript
/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

/**
 * AI Command Provider for Command Palette
 *
 * Provides AI-specific commands when user opens command palette (Ctrl+K).
 * Commands are context-aware based on current view and model.
 */
export const aiCommandProvider = {
    name: "ai",
    provide: (env, options) => {
        const aiService = env.services.ai;
        if (!aiService) return [];

        const commands = [];
        const currentContext = aiService.getCurrentContext();

        // Always available AI commands
        commands.push({
            name: _t("Ask AI..."),
            category: "ai",
            description: _t("Open AI assistant and ask a question"),
            shortcut: "Alt+A",
            action: () => {
                env.bus.trigger("AI:OPEN", { focusInput: true });
            },
        });

        commands.push({
            name: _t("AI: Explain this page"),
            category: "ai",
            description: _t("Get AI explanation of current view"),
            action: async () => {
                await aiService.explainCurrentView();
            },
        });

        // Context-specific commands
        if (currentContext?.model) {
            commands.push({
                name: _t("AI: Search %s", currentContext.model),
                category: "ai",
                description: _t("Use AI to search records"),
                action: async () => {
                    env.bus.trigger("AI:OPEN", {
                        focusInput: true,
                        prefill: `Search for ${currentContext.model} where `,
                    });
                },
            });

            commands.push({
                name: _t("AI: Create %s", currentContext.model),
                category: "ai",
                description: _t("Use AI to create a new record"),
                action: async () => {
                    env.bus.trigger("AI:OPEN", {
                        focusInput: true,
                        prefill: `Create a new ${currentContext.model} with `,
                    });
                },
            });
        }

        // Commands for form views with active record
        if (currentContext?.viewType === "form" && currentContext?.activeIds?.length) {
            commands.push({
                name: _t("AI: Analyze this record"),
                category: "ai",
                description: _t("Get AI analysis of current record"),
                action: async () => {
                    await aiService.analyzeRecord(
                        currentContext.model,
                        currentContext.activeIds[0]
                    );
                },
            });

            commands.push({
                name: _t("AI: Suggest improvements"),
                category: "ai",
                description: _t("Get AI suggestions for this record"),
                action: async () => {
                    await aiService.suggestImprovements(
                        currentContext.model,
                        currentContext.activeIds[0]
                    );
                },
            });
        }

        // Commands for list views
        if (currentContext?.viewType === "list") {
            commands.push({
                name: _t("AI: Summarize selected"),
                category: "ai",
                description: _t("Get AI summary of selected records"),
                action: async () => {
                    await aiService.summarizeRecords(
                        currentContext.model,
                        currentContext.selectedIds
                    );
                },
            });
        }

        return commands;
    },
};

// Register the AI command category
registry.category("command_categories").add("ai", {
    name: _t("AI Assistant"),
    order: 5, // Appear early in the command palette
});

// Register the AI command provider
registry.category("command_provider").add("ai", aiCommandProvider);
```

### 3.2 Deep ORM Integration

#### 3.2.1 Files to Modify in `odoo/odoo/`

| File | Modification Type | Purpose |
|------|------------------|---------|
| `models.py` | Extend | Add AI operation hooks to BaseModel |
| `api.py` | Extend | Add AI context manager decorator |
| `service/server.py` | Extend | Start MCP server alongside HTTP server |

#### 3.2.2 AI Operation Hooks in ORM

**File: `odoo/odoo/models.py`** (modifications to BaseModel)

```python
# Add to BaseModel class

class BaseModel(metaclass=MetaModel):
    # ... existing code ...

    # =========================================================================
    # AI OPERATION HOOKS
    # =========================================================================

    _ai_observable = True  # Set to False to exclude from AI operations
    _ai_description = None  # Human-readable description for AI context

    @api.model
    def _ai_get_model_info(self):
        """
        Return model information for AI context.
        Called by MCP server to understand model capabilities.
        """
        return {
            'model': self._name,
            'description': self._ai_description or self._description,
            'fields': self._ai_get_field_info(),
            'actions': self._ai_get_available_actions(),
            'observable': self._ai_observable,
        }

    @api.model
    def _ai_get_field_info(self):
        """
        Return field information suitable for AI consumption.
        Filters sensitive fields and includes help text.
        """
        AI_HIDDEN_FIELDS = {'password', 'password_crypt', 'api_key', 'token', 'secret'}

        field_info = {}
        for name, field in self._fields.items():
            if name in AI_HIDDEN_FIELDS:
                continue
            if name.startswith('_'):
                continue

            field_info[name] = {
                'type': field.type,
                'string': field.string,
                'help': field.help or '',
                'required': field.required,
                'readonly': field.readonly,
                'stored': field.store,
            }

            # Include selection options for selection fields
            if field.type == 'selection':
                selection = field.selection
                if callable(selection):
                    try:
                        selection = selection(self)
                    except Exception:
                        selection = []
                field_info[name]['selection'] = selection

            # Include relation info for relational fields
            if field.type in ('many2one', 'one2many', 'many2many'):
                field_info[name]['relation'] = field.comodel_name

        return field_info

    @api.model
    def _ai_get_available_actions(self):
        """
        Return list of actions AI can execute on this model.
        """
        actions = []

        # Find methods that start with 'action_' or 'button_'
        for attr_name in dir(self):
            if attr_name.startswith(('action_', 'button_')):
                method = getattr(self, attr_name, None)
                if callable(method):
                    actions.append({
                        'name': attr_name,
                        'doc': method.__doc__ or '',
                    })

        return actions

    def _ai_pre_write_hook(self, vals):
        """
        Hook called before AI-initiated write operations.
        Override to add custom validation or transformation.

        Returns:
            dict: Modified vals (or original if no changes needed)
        """
        return vals

    def _ai_post_write_hook(self, vals):
        """
        Hook called after AI-initiated write operations.
        Override to add custom post-processing.
        """
        pass

    @api.model
    def _ai_pre_create_hook(self, vals_list):
        """
        Hook called before AI-initiated create operations.

        Returns:
            list: Modified vals_list
        """
        return vals_list

    @api.model
    def _ai_post_create_hook(self, records):
        """
        Hook called after AI-initiated create operations.
        """
        pass

    def _ai_pre_unlink_hook(self):
        """
        Hook called before AI-initiated unlink operations.
        Can raise exception to prevent deletion.
        """
        pass

    def _ai_search_context(self):
        """
        Return additional context hints for AI search operations.
        Override to provide model-specific search guidance.
        """
        return {
            'suggested_filters': [],
            'common_searches': [],
            'search_tips': [],
        }
```

#### 3.2.3 AI Context Manager

**File: `odoo/odoo/api.py`** (additions)

```python
# Add to api.py

import functools
import logging
from contextlib import contextmanager

_ai_logger = logging.getLogger('odoo.ai')


def ai_operation(operation_type='other', require_confirmation=False):
    """
    Decorator for methods that can be invoked by AI.

    Provides:
    - Automatic logging of AI operations
    - Permission checking
    - Savepoint management
    - Before/after state capture

    Args:
        operation_type: Type of operation (read, write, create, unlink, action)
        require_confirmation: If True, AI must get user confirmation first

    Usage:
        @api.ai_operation('write')
        def action_confirm(self):
            ...
    """
    def decorator(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            env = self.env
            ai_context = env.context.get('ai_context', {})

            if not ai_context:
                # Not an AI-initiated call, execute normally
                return method(self, *args, **kwargs)

            session_id = ai_context.get('session_id')
            agent_id = ai_context.get('agent_id')

            # Log operation start
            _ai_logger.info(
                f"AI Operation: {operation_type} on {self._name} "
                f"(session={session_id}, agent={agent_id})"
            )

            # Check confirmation requirement
            if require_confirmation and not ai_context.get('user_confirmed'):
                raise UserError(
                    f"This operation requires user confirmation. "
                    f"Please confirm before proceeding."
                )

            # Capture state before (for write/unlink)
            state_before = None
            if operation_type in ('write', 'unlink') and self.ids:
                state_before = self._ai_capture_state()

            try:
                result = method(self, *args, **kwargs)

                # Log success
                if session_id:
                    env['loomworks.ai.operation.log'].sudo().create({
                        'session_id': session_id,
                        'tool_name': method.__name__,
                        'operation_type': operation_type,
                        'model_name': self._name,
                        'record_ids': str(self.ids),
                        'state': 'success',
                    })

                return result

            except Exception as e:
                _ai_logger.error(f"AI Operation failed: {e}")
                if session_id:
                    env['loomworks.ai.operation.log'].sudo().create({
                        'session_id': session_id,
                        'tool_name': method.__name__,
                        'operation_type': operation_type,
                        'model_name': self._name,
                        'record_ids': str(self.ids),
                        'state': 'error',
                        'error_message': str(e),
                    })
                raise

        wrapper._ai_operation = True
        wrapper._ai_operation_type = operation_type
        wrapper._ai_require_confirmation = require_confirmation
        return wrapper

    return decorator


@contextmanager
def ai_context(env, session, agent):
    """
    Context manager for AI-initiated operations.

    Provides:
    - Automatic context injection
    - Transaction savepoint management
    - Operation counting and limits

    Usage:
        with api.ai_context(env, session, agent) as ctx:
            records = env['sale.order'].search([...])
            records.action_confirm()
    """
    ctx = {
        'ai_context': {
            'session_id': session.id,
            'agent_id': agent.id,
            'operation_count': 0,
            'max_operations': agent.max_operations_per_turn,
        }
    }

    # Create savepoint if agent settings require it
    savepoint_name = None
    if agent.use_savepoints:
        savepoint_name = f"ai_ctx_{session.uuid.replace('-', '_')}"
        env.cr.execute(f'SAVEPOINT {savepoint_name}')

    try:
        # Yield environment with AI context
        yield env.with_context(**ctx)

        # Success - release savepoint
        if savepoint_name:
            env.cr.execute(f'RELEASE SAVEPOINT {savepoint_name}')

    except Exception as e:
        # Error - rollback to savepoint
        if savepoint_name:
            env.cr.execute(f'ROLLBACK TO SAVEPOINT {savepoint_name}')
        raise
```

### 3.3 MCP Server as Core Service

#### 3.3.1 Service Architecture

The MCP server should start alongside the Odoo HTTP server as a core service, not as a separate daemon.

**File: `odoo/odoo/service/server.py`** (modifications)

```python
# Add to server.py

import threading
from odoo.addons.loomworks_ai.services.odoo_mcp_server import start_mcp_server

class ThreadedServer:
    # ... existing code ...

    def __init__(self, app):
        # ... existing init ...
        self.mcp_server = None
        self.mcp_thread = None

    def start(self, stop=False, log_level=None):
        # ... existing start code ...

        # Start MCP server if AI is enabled
        if config.get('ai_enabled', True):
            self._start_mcp_server()

    def _start_mcp_server(self):
        """Start MCP server in a separate thread."""
        try:
            mcp_port = config.get('mcp_port', 3100)

            def run_mcp():
                start_mcp_server(
                    host='127.0.0.1',
                    port=mcp_port,
                    db_name=config.get('db_name'),
                )

            self.mcp_thread = threading.Thread(
                target=run_mcp,
                name='odoo.mcp.server',
                daemon=True
            )
            self.mcp_thread.start()
            _logger.info(f"MCP server started on port {mcp_port}")

        except Exception as e:
            _logger.warning(f"Failed to start MCP server: {e}")

    def stop(self):
        # ... existing stop code ...

        # Stop MCP server
        if self.mcp_server:
            self.mcp_server.shutdown()
            self.mcp_thread.join(timeout=5)
```

#### 3.3.2 Configuration Options

**File: `odoo/odoo/tools/config.py`** (additions)

```python
# Add to config options

# AI Configuration
'ai_enabled': True,
'ai_api_key': '',  # Claude API key (or from environment)
'mcp_port': 3100,
'ai_default_model': 'claude-sonnet-4-20250514',
'ai_max_operations_per_turn': 10,
'ai_auto_rollback': True,
```

### 3.4 AI as First-Class Citizen: View Integration

#### 3.4.1 Form View AI Integration

Every form view should have an "Ask AI" option. This is achieved by modifying the form controller.

**File: `odoo/addons/web/static/src/views/form/form_controller.js`** (modifications)

```javascript
/** @odoo-module **/

import { FormController as OriginalFormController } from "./form_controller_original";
import { useService } from "@web/core/utils/hooks";

export class FormController extends OriginalFormController {
    setup() {
        super.setup();
        this.aiService = useService("ai");
    }

    /**
     * Get AI-specific actions for the control panel
     */
    getAIActions() {
        return [
            {
                type: "button",
                icon: "fa-robot",
                title: this.env._t("Ask AI about this record"),
                onClick: () => this.askAIAboutRecord(),
            },
            {
                type: "button",
                icon: "fa-magic",
                title: this.env._t("AI Suggestions"),
                onClick: () => this.getAISuggestions(),
            },
        ];
    }

    async askAIAboutRecord() {
        const record = this.model.root;
        await this.aiService.openWithContext({
            model: this.props.resModel,
            recordId: record.resId,
            recordData: record.data,
            prefill: `Tell me about this ${this.props.resModel} record: `,
        });
    }

    async getAISuggestions() {
        const record = this.model.root;
        await this.aiService.suggestImprovements(
            this.props.resModel,
            record.resId
        );
    }
}
```

#### 3.4.2 List View AI Integration

**File: `odoo/addons/web/static/src/views/list/list_controller.js`** (modifications)

```javascript
// Add AI bulk actions to list views

getAIActions() {
    const selectedRecords = this.model.root.selection;

    if (selectedRecords.length === 0) {
        return [{
            type: "button",
            icon: "fa-robot",
            title: this.env._t("Ask AI"),
            onClick: () => this.openAIForModel(),
        }];
    }

    return [
        {
            type: "button",
            icon: "fa-robot",
            title: this.env._t(`Ask AI about ${selectedRecords.length} records`),
            onClick: () => this.askAIAboutSelection(),
        },
        {
            type: "button",
            icon: "fa-list-check",
            title: this.env._t("AI: Bulk action"),
            onClick: () => this.aiBulkAction(),
        },
    ];
}

async askAIAboutSelection() {
    const selectedIds = this.model.root.selection.map(r => r.resId);
    await this.aiService.openWithContext({
        model: this.props.resModel,
        recordIds: selectedIds,
        prefill: `Analyze these ${selectedIds.length} ${this.props.resModel} records: `,
    });
}

async aiBulkAction() {
    const selectedIds = this.model.root.selection.map(r => r.resId);
    await this.aiService.openWithContext({
        model: this.props.resModel,
        recordIds: selectedIds,
        prefill: `For these ${selectedIds.length} records, I want to: `,
        suggestedActions: ['update', 'export', 'analyze', 'delete'],
    });
}
```

### 3.5 Implementation Phases for Core Modifications

#### Phase 2.0: Core Infrastructure (Week 4-5)

- [ ] 2.0.1 Fork Odoo Community v18 to Loomworks repository
- [ ] 2.0.2 Set up development environment with forked core
- [ ] 2.0.3 Create AI service in `odoo/addons/web/static/src/core/ai/`
- [ ] 2.0.4 Modify `config.py` for AI configuration options
- [ ] 2.0.5 Add AI hooks to `models.py` (BaseModel extensions)
- [ ] 2.0.6 Add `ai_context` and `ai_operation` decorators to `api.py`

#### Phase 2.1: Core Models (Week 5-6)

(Existing tasks - unchanged)

#### Phase 2.2: MCP Server Integration (Week 6-7)

- [ ] 2.2.0 Modify `server.py` to start MCP server alongside HTTP
- [ ] 2.2.1 Implement `odoo_mcp_server.py` with FastMCP
- [ ] ... (remaining existing tasks)

#### Phase 2.3-2.4: (Unchanged)

#### Phase 2.5: Core Web Client (Week 9-10)

- [ ] 2.5.0 Modify `webclient.js` for AI integration
- [ ] 2.5.1 Modify `webclient.xml` to include AI components
- [ ] 2.5.2 Add AI button to `navbar.xml`
- [ ] 2.5.3 Create AI command provider for command palette
- [ ] 2.5.4 Modify `form_controller.js` for AI actions
- [ ] 2.5.5 Modify `list_controller.js` for AI bulk actions
- [ ] 2.5.6 Implement AIAssistant sidebar component
- [ ] 2.5.7 Implement AIStatusIndicator component
- [ ] 2.5.8 Create AI-specific SCSS styles

### 3.6 File Summary: Core Modifications

| Category | File Path | Action | Purpose |
|----------|-----------|--------|---------|
| **Config** | `odoo/odoo/tools/config.py` | Modify | Add AI config options |
| **ORM** | `odoo/odoo/models.py` | Modify | Add AI hooks to BaseModel |
| **API** | `odoo/odoo/api.py` | Modify | Add ai_context, ai_operation |
| **Server** | `odoo/odoo/service/server.py` | Modify | Start MCP server |
| **WebClient** | `odoo/addons/web/static/src/webclient/webclient.js` | Modify | AI integration |
| **WebClient** | `odoo/addons/web/static/src/webclient/webclient.xml` | Modify | AI components |
| **Navbar** | `odoo/addons/web/static/src/webclient/navbar/navbar.xml` | Modify | AI button |
| **Commands** | `odoo/addons/web/static/src/core/ai/ai_command_provider.js` | Create | Command palette |
| **Form** | `odoo/addons/web/static/src/views/form/form_controller.js` | Modify | AI actions |
| **List** | `odoo/addons/web/static/src/views/list/list_controller.js` | Modify | AI bulk actions |
| **AI Core** | `odoo/addons/web/static/src/core/ai/` | Create | AI service directory |
| **Assets** | `odoo/addons/web/views/webclient_templates.xml` | Modify | AI asset bundles |
| **Context Service** | `odoo/addons/web/static/src/core/ai/ai_context_service.js` | Create | Event-driven context detection |
| **Suggestion Service** | `odoo/addons/web/static/src/core/ai/ai_suggestion_service.js` | Create | Debounced suggestion generation |
| **Idle Detector** | `odoo/addons/web/static/src/core/ai/ai_idle_detector.js` | Create | Simple idle detection (10s) |
| **AI Dropdown** | `odoo/addons/web/static/src/core/ai/ai_navbar_dropdown/` | Create | Navbar dropdown component |
| **User Settings** | `loomworks_ai/models/ai_user_settings.py` | Create | Simplified AI preferences (3 fields) |

#### Phase 2.7: Contextual AI Navbar (Week 11-12)

- [ ] 2.7.1 Create `ai_context_service.js` (event-driven)
- [ ] 2.7.2 Create `ai_suggestion_service.js`
- [ ] 2.7.3 Create `AINavbarDropdown` Owl component
- [ ] 2.7.4 Create `loomworks.ai.user.settings` model (simplified)
- [ ] 2.7.5 Create settings modal component (simplified)
- [ ] 2.7.6 Integrate with existing `AIChat` component
- [ ] 2.7.7 Add backend suggestion triggers
- [ ] 2.7.8 Hook context triggers into view controllers
- [ ] 2.7.9 Add idle detection (10s threshold)
- [ ] 2.7.10 Write tests (unit + integration)

### 3.7 Maintaining Upgrade Compatibility

Even though we own the fork, we should maintain a clean separation to facilitate merging upstream Odoo updates:

1. **Modification Comments**: All core modifications should include a comment block:
   ```python
   # LOOMWORKS-AI: Begin modification
   # ... modified code ...
   # LOOMWORKS-AI: End modification
   ```

2. **Minimal Core Changes**: Where possible, use Odoo's extension mechanisms (registries, inheritance) instead of direct modification.

3. **Feature Flags**: All AI features should be toggleable via config:
   ```python
   if config.get('ai_enabled', True):
       # AI-specific code
   ```

4. **Upstream Tracking**: Maintain a branch tracking upstream Odoo 18 for periodic rebasing.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Claude API rate limits | Medium | High | Implement queuing, caching, graceful degradation |
| AI makes destructive changes | Medium | Critical | Savepoints, confirmation dialogs, audit logs |
| User data exposure | Low | Critical | Strict model blocklist, permission inheritance |
| Performance bottlenecks | Medium | Medium | Async processing, response streaming |
| Claude Agent SDK API changes | Medium | Medium | Abstraction layer, version pinning |
| Fork maintenance burden | High | Medium | Upstream tracking branch, marked modifications, feature flags |
| Core modification conflicts | Medium | High | Minimal invasive changes, use registries where possible |
| Proactive AI feels intrusive | Medium | Medium | Conservative defaults, frequency control, easy disable |
| Privacy concerns | Low | Medium | Event-driven (not constant), Anthropic privacy policies, EULA coverage |
| Context detection errors | Medium | Low | Graceful fallbacks, user feedback mechanism |

---

## References

### Claude and MCP
- [Claude Agent SDK Documentation](https://platform.claude.com/docs/en/agent-sdk/overview)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)

### Odoo Core Documentation
- [Odoo 18 Web Controllers](https://www.odoo.com/documentation/18.0/developer/reference/backend/http.html)
- [Odoo 18 ORM API](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html)
- [Odoo Owl Components](https://www.odoo.com/documentation/18.0/developer/reference/frontend/owl_components.html)
- [Odoo 18 Registries](https://www.odoo.com/documentation/18.0/developer/reference/frontend/registries.html)
- [Odoo 18 Patching Code](https://www.odoo.com/documentation/18.0/developer/reference/frontend/patching_code.html)
- [Odoo 18 JavaScript Reference](https://www.odoo.com/documentation/18.0/developer/reference/frontend/javascript_reference.html)
- [Odoo 18 Framework Overview](https://www.odoo.com/documentation/18.0/developer/reference/frontend/framework_overview.html)
- [Odoo 18 Services](https://www.odoo.com/documentation/19.0/developer/reference/frontend/services.html)
- [Customizing the Web Client](https://www.odoo.com/documentation/18.0/developer/tutorials/web.html)

### Core Architecture
- [Odoo 18 Architecture Overview](https://www.odoo.com/documentation/18.0/developer/tutorials/server_framework_101/01_architecture.html)
- [Odoo webclient_templates.xml (GitHub)](https://github.com/odoo/odoo/blob/master/addons/web/views/webclient_templates.xml)
- [Odoo 18 Keyboard Shortcuts](https://www.odoo.com/documentation/18.0/applications/essentials/keyboard_shortcuts.html)

### Database and Transactions
- [PostgreSQL Savepoints](https://www.postgresql.org/docs/current/sql-savepoint.html)
- [AI Rollback Best Practices](https://www.sandgarden.com/learn/rollback)
