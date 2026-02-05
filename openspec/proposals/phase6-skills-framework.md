# Phase 6: Skills Framework Proposal

## Overview

The Skills Framework transforms AI workflow automation into a **first-class Odoo action type** within the Loomworks forked core. Rather than building skills as an addon layer, this proposal integrates skills directly into Odoo's action system, making them as fundamental as window actions, server actions, and client actions.

### Key Objectives

1. **Skills as Core Action Type**: Introduce `ir.actions.skill` as a native Odoo action alongside existing types
2. **Session Recording in Core**: Built-in workflow capture via RPC interception and action logging
3. **Natural Language Commands**: Intent matcher integrated with Odoo's command palette service
4. **Skill-Aware Views**: Native UI elements for skill recording, execution, and management
5. **Built-in Skills Library**: Pre-installed skills shipping with the forked Odoo core

### Why Core Integration?

| Aspect | Addon Approach | Core Integration |
|--------|----------------|------------------|
| Action execution | Custom engine bypassing Odoo | Native action manager handles skills |
| View integration | Injected buttons via JS patches | Built-in view components |
| Recording | External session tracking | RPC interceptor captures all operations |
| Command palette | Separate command provider | Skills in native command service |
| Performance | Additional abstraction layer | Direct integration, faster execution |
| Maintenance | Compatibility with each Odoo update | Part of forked core release cycle |

---

## Phase Dependencies and Graceful Degradation (M3 Resolution)

### Explicit Dependencies

The Skills Framework has the following phase dependencies:

| Dependency | Phase | Type | Required For |
|------------|-------|------|--------------|
| **AI Integration Layer** | Phase 2 | **REQUIRED** | MCP tools, AI sessions, agent execution |
| **Snapshot System** | Phase 5 | **OPTIONAL** | Database-level PITR rollback, undo operations |
| **Fork Foundation** | Phase 1 | **REQUIRED** | Core modifications to action system |

### Phase 2 Dependency (REQUIRED)

The Skills Framework **requires** the AI Integration Layer (Phase 2) because:

1. **MCP Tools**: Skills invoke `loomworks.ai.tool` records for operations
2. **AI Sessions**: Skill executions are logged to `loomworks.ai.session`
3. **Operation Logging**: All skill operations flow through `loomworks.ai.operation.log`
4. **Agent Binding**: `ir.actions.skill` references `loomworks.ai.agent` for execution context

**Installation Requirement**: `loomworks_ai` module must be installed before Skills Framework is active.

### Phase 5 Dependency (OPTIONAL - Graceful Degradation)

The Skills Framework **optionally** uses the Snapshot System (Phase 5) for enhanced rollback capabilities. When Phase 5 is not installed, the Skills Framework degrades gracefully:

#### With Phase 5 Snapshots (Full Capability)

```python
# Full PITR rollback via loomworks.snapshot
class SkillExecutionEngine:
    def execute_skill(self, skill, context, params=None):
        # Create database-level snapshot for full PITR rollback
        snapshot_service = self.env.get('loomworks.snapshot')
        if snapshot_service:
            snapshot = snapshot_service.create_snapshot(
                name=f"skill_{skill.technical_name}_{datetime.now().isoformat()}",
                description=f"Pre-execution snapshot for skill: {skill.name}",
                retention_hours=24,
            )

        try:
            result = self._execute_steps(skill, context)
            return result
        except Exception as e:
            if snapshot:
                snapshot.restore()  # Full database PITR restore
            raise
```

**Capabilities with Phase 5**:
- Full database-level Point-in-Time Recovery (PITR)
- Cross-table rollback (including records created in other models)
- Snapshot retention for audit and replay
- Undo operations even after commit

#### Without Phase 5 Snapshots (Degraded Mode)

```python
# Fallback to PostgreSQL savepoints only
class RollbackManager:
    def __init__(self, env):
        self.env = env
        self.savepoint_stack = []
        # Check if Phase 5 snapshot service is available
        self.snapshot_service = env.get('loomworks.snapshot') if 'loomworks.snapshot' in env.registry else None

    def create_savepoint(self, name):
        """Create rollback point - uses snapshot if available, else savepoint."""
        if self.snapshot_service:
            # Phase 5 available: use full PITR snapshot
            return self.snapshot_service.create_snapshot(name=f"skill_{name}")
        else:
            # Phase 5 not available: use PostgreSQL savepoint
            savepoint_id = f"skill_{name}_{uuid4().hex[:8]}"
            self.env.cr.execute(f"SAVEPOINT {savepoint_id}")
            self.savepoint_stack.append(savepoint_id)
            return savepoint_id

    def rollback(self, savepoint_ref):
        """Rollback to savepoint or snapshot."""
        if self.snapshot_service and hasattr(savepoint_ref, 'restore'):
            # Phase 5 snapshot object
            savepoint_ref.restore()
        elif isinstance(savepoint_ref, str):
            # PostgreSQL savepoint name
            self.env.cr.execute(f"ROLLBACK TO SAVEPOINT {savepoint_ref}")
```

**Capabilities without Phase 5 (Degraded Mode)**:
- Transaction-level rollback only (PostgreSQL SAVEPOINT)
- Rollback only within current transaction (before commit)
- No post-commit undo capability
- No snapshot retention for audit

### Degraded Mode Feature Matrix

| Feature | With Phase 5 | Without Phase 5 |
|---------|--------------|-----------------|
| Pre-execution checkpoint | Full PITR snapshot | PostgreSQL SAVEPOINT |
| Rollback scope | Entire database | Current transaction only |
| Post-commit undo | Yes | No |
| Cross-transaction rollback | Yes | No |
| Snapshot retention | Configurable (hours/days) | Until transaction ends |
| Audit trail | Full snapshot history | Operation log only |
| Performance impact | Higher (WAL archiving) | Lower |

### User Notification for Degraded Mode

When Phase 5 is not installed, the Skills Framework displays a warning:

```python
def _check_snapshot_capability(self):
    """Check and notify about snapshot capability."""
    if 'loomworks.snapshot' not in self.env.registry:
        _logger.warning(
            "Skills Framework running in degraded mode: "
            "Phase 5 Snapshot System not installed. "
            "Rollback limited to current transaction only."
        )
        return False
    return True
```

In the UI, skills with `rollback_on_failure=True` show an indicator:

```xml
<field name="rollback_on_failure" widget="boolean_toggle"/>
<span t-if="!snapshot_available" class="text-warning">
    <i class="fa fa-exclamation-triangle"/>
    Limited rollback (savepoint only)
</span>
```

---

## Technical Design

### 1. Core Action System: `ir.actions.skill`

#### 1.1 Action Model in Forked Core

**Location**: `odoo/odoo/addons/base/models/ir_actions_skill.py`

```python
# -*- coding: utf-8 -*-
"""
Skill Actions - Core action type for AI workflow automation.

This module extends Odoo's action system with skill-based actions that enable
natural language triggered, recordable, and replayable workflows.
"""
from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval


class IrActionsSkill(models.Model):
    """
    Skill action type for AI-driven workflow automation.

    Skills are first-class Odoo actions that:
    - Can be triggered by natural language intent matching
    - Execute multi-step workflows with rollback support
    - Can be recorded from user sessions and replayed
    - Integrate with Odoo's standard action manager
    """
    _name = 'ir.actions.skill'
    _description = 'Skill Action'
    _inherit = 'ir.actions.actions'
    _table = 'ir_act_skill'
    _order = 'name'

    # Action type identification
    type = fields.Char(default='ir.actions.skill', required=True)

    # Skill identity
    technical_name = fields.Char(
        required=True,
        index=True,
        help="Unique kebab-case identifier, e.g., 'create-sales-quote'"
    )
    version = fields.Char(default='1.0.0')

    # Classification
    category = fields.Selection([
        ('sales', 'Sales'),
        ('purchase', 'Purchasing'),
        ('inventory', 'Inventory'),
        ('accounting', 'Accounting'),
        ('hr', 'Human Resources'),
        ('manufacturing', 'Manufacturing'),
        ('crm', 'CRM'),
        ('project', 'Project'),
        ('custom', 'Custom'),
    ], default='custom', required=True)

    # Natural language triggers
    trigger_phrases = fields.Text(
        help="JSON array of natural language phrases that activate this skill"
    )
    trigger_confidence_threshold = fields.Float(
        default=0.75,
        help="Minimum confidence score (0-1) for intent matching"
    )

    # Skill content and execution
    skill_content = fields.Text(
        help="Full SKILL.md content defining the workflow"
    )
    system_prompt = fields.Text(
        help="Instructions for Claude when executing this skill"
    )

    # Context variables schema
    context_schema = fields.Text(
        help="JSON Schema defining extractable parameters"
    )
    required_context = fields.Text(
        help="JSON array of required context variable names"
    )

    # Workflow steps
    step_ids = fields.One2many(
        'ir.actions.skill.step',
        'skill_id',
        string='Workflow Steps'
    )

    # Tool bindings (MCP tools this skill can invoke)
    allowed_tools = fields.Text(
        help="JSON array of MCP tool names this skill may call"
    )

    # Target models (for binding and permissions)
    model_id = fields.Many2one(
        'ir.model',
        string='Primary Model',
        ondelete='cascade',
        help="Main model this skill operates on"
    )

    # Access control
    is_builtin = fields.Boolean(
        default=False,
        help="True for skills shipped with core"
    )
    is_published = fields.Boolean(
        default=False,
        help="True if available to other users"
    )

    # State management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('testing', 'Testing'),
        ('active', 'Active'),
        ('deprecated', 'Deprecated'),
    ], default='draft', required=True)

    # Statistics (computed)
    execution_count = fields.Integer(readonly=True, default=0)
    success_count = fields.Integer(readonly=True, default=0)
    success_rate = fields.Float(compute='_compute_success_rate', store=True)
    avg_duration_ms = fields.Integer(readonly=True, default=0)

    _sql_constraints = [
        ('technical_name_uniq', 'unique(technical_name)',
         'Technical name must be unique'),
    ]

    @api.depends('execution_count', 'success_count')
    def _compute_success_rate(self):
        for skill in self:
            if skill.execution_count > 0:
                skill.success_rate = skill.success_count / skill.execution_count
            else:
                skill.success_rate = 0.0

    @api.model
    def _get_readable_fields(self):
        """Fields exposed to the web client."""
        return super()._get_readable_fields() | {
            'technical_name', 'version', 'category', 'trigger_phrases',
            'trigger_confidence_threshold', 'system_prompt', 'context_schema',
            'required_context', 'allowed_tools', 'model_id', 'state',
            'is_builtin', 'success_rate',
        }

    def run(self, context=None, params=None):
        """
        Execute the skill workflow.

        This is the main entry point called by the action manager.

        :param context: Execution context with extracted parameters
        :param params: Additional runtime parameters
        :return: dict with execution result or follow-up action
        """
        self.ensure_one()

        # Import here to avoid circular dependency
        from odoo.addons.base.models.skill_execution_engine import SkillExecutionEngine

        engine = SkillExecutionEngine(self.env)
        return engine.execute_skill(self, context or {}, params or {})


class IrActionsSkillStep(models.Model):
    """Individual step in a skill workflow."""
    _name = 'ir.actions.skill.step'
    _description = 'Skill Workflow Step'
    _order = 'sequence, id'

    skill_id = fields.Many2one(
        'ir.actions.skill',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)

    # Step type
    step_type = fields.Selection([
        ('tool_call', 'Tool Invocation'),
        ('user_input', 'Request User Input'),
        ('condition', 'Conditional Branch'),
        ('loop', 'Loop/Iteration'),
        ('subskill', 'Execute Sub-Skill'),
        ('validation', 'Validate Data'),
        ('confirmation', 'User Confirmation'),
        ('action', 'Execute Odoo Action'),
    ], required=True)

    # Tool call configuration
    tool_name = fields.Char(help="MCP tool name for tool_call type")
    tool_parameters = fields.Text(help="JSON template with {variable} placeholders")

    # Conditional logic
    condition_expression = fields.Text(help="Python expression for branching")
    on_success_step_id = fields.Many2one('ir.actions.skill.step')
    on_failure_step_id = fields.Many2one('ir.actions.skill.step')

    # Sub-skill reference
    subskill_id = fields.Many2one('ir.actions.skill')

    # Odoo action reference (for action type steps)
    action_id = fields.Many2one('ir.actions.actions')

    # Error handling
    is_critical = fields.Boolean(default=True)
    retry_count = fields.Integer(default=0)
    rollback_on_failure = fields.Boolean(default=True)

    # Output mapping
    output_variable = fields.Char()
    output_transform = fields.Text(help="Python expression to transform output")

    # Instructions for AI
    instructions = fields.Text()
```

#### 1.2 Skill Execution Engine

**Location**: `odoo/odoo/addons/base/models/skill_execution_engine.py`

```python
# -*- coding: utf-8 -*-
"""
Skill Execution Engine - Core orchestrator for skill workflows.

Handles skill matching, parameter extraction, step execution,
rollback management, and integration with AI agents.
"""
import json
import logging
import re
from datetime import datetime
from uuid import uuid4

from odoo import api, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SkillExecutionEngine:
    """
    Orchestrates skill discovery, matching, and execution.

    This engine is the core runtime for ir.actions.skill, handling:
    - Natural language intent matching
    - Parameter extraction from user input
    - Step-by-step workflow execution
    - Transaction management and rollback
    - Integration with MCP tools and AI agents
    """

    def __init__(self, env):
        self.env = env
        self.intent_matcher = IntentMatcher(env)
        self.step_executor = StepExecutor(env)
        self.rollback_manager = RollbackManager(env)

    def match_skill(self, user_input, domain=None):
        """
        Find the best matching skill for natural language input.

        :param user_input: Natural language text from user
        :param domain: Optional domain to filter available skills
        :return: tuple(skill, confidence, extracted_params) or (None, 0, {})
        """
        skills = self.env['ir.actions.skill'].search([
            ('state', '=', 'active'),
        ] + (domain or []))

        return self.intent_matcher.match(user_input, skills)

    def execute_skill(self, skill, context, params=None):
        """
        Execute a skill workflow with full transaction support.

        :param skill: ir.actions.skill record
        :param context: dict of extracted parameters
        :param params: Additional runtime parameters
        :return: dict with result or follow-up action
        """
        execution = self._create_execution_log(skill, context)
        savepoint = self.rollback_manager.create_savepoint(skill.technical_name)

        try:
            # Validate required context
            missing = self._check_required_context(skill, context)
            if missing:
                return {
                    'type': 'ir.actions.skill.input_required',
                    'skill_id': skill.id,
                    'missing_params': missing,
                    'execution_id': execution.id,
                }

            # Execute workflow steps
            result = self._execute_steps(skill, context, execution)

            # Commit on success
            self.rollback_manager.commit()
            self._finalize_execution(execution, 'completed', result)

            # Update skill statistics
            skill.sudo().write({
                'execution_count': skill.execution_count + 1,
                'success_count': skill.success_count + 1,
            })

            return result

        except Exception as e:
            _logger.exception("Skill execution failed: %s", skill.technical_name)
            self.rollback_manager.rollback_to_savepoint(savepoint)
            self._finalize_execution(execution, 'failed', error=str(e))

            skill.sudo().write({
                'execution_count': skill.execution_count + 1,
            })

            raise UserError(f"Skill '{skill.name}' failed: {e}")

    def _create_execution_log(self, skill, context):
        """Create execution log record."""
        return self.env['ir.actions.skill.execution'].create({
            'skill_id': skill.id,
            'user_id': self.env.uid,
            'started_at': datetime.now(),
            'context_snapshot': json.dumps(context),
            'state': 'running',
        })

    def _check_required_context(self, skill, context):
        """Return list of missing required parameters."""
        if not skill.required_context:
            return []
        required = json.loads(skill.required_context)
        return [p for p in required if p not in context or context[p] is None]

    def _execute_steps(self, skill, context, execution):
        """Execute workflow steps in sequence."""
        steps = skill.step_ids.sorted('sequence')
        current_context = dict(context)
        result = None

        for step in steps:
            step_result = self.step_executor.execute(step, current_context)

            if step.output_variable and step_result.get('data'):
                current_context[step.output_variable] = step_result['data']

            if step_result.get('next_step_id'):
                # Handle conditional branching
                pass

            if step_result.get('requires_input'):
                return {
                    'type': 'ir.actions.skill.input_required',
                    'skill_id': skill.id,
                    'step_id': step.id,
                    'prompt': step_result.get('prompt'),
                    'execution_id': execution.id,
                }

            result = step_result

        return result or {'type': 'ir.actions.skill.completed', 'message': 'Skill completed'}

    def _finalize_execution(self, execution, state, result=None, error=None):
        """Update execution log with final state."""
        execution.write({
            'completed_at': datetime.now(),
            'state': state,
            'result_summary': json.dumps(result) if result else None,
            'error_message': error,
        })


class IntentMatcher:
    """
    Multi-strategy intent matching for skill activation.

    Combines fuzzy string matching, semantic similarity,
    and keyword extraction for robust natural language matching.
    """

    def __init__(self, env):
        self.env = env

    def match(self, user_input, skills):
        """
        Match user input against available skills.

        :param user_input: Natural language text
        :param skills: Recordset of ir.actions.skill
        :return: (best_skill, confidence, extracted_params)
        """
        candidates = []
        user_input_lower = user_input.lower().strip()

        for skill in skills:
            if not skill.trigger_phrases:
                continue

            phrases = json.loads(skill.trigger_phrases)

            # Stage 1: Fuzzy match against trigger phrases
            fuzzy_score = self._fuzzy_match(user_input_lower, phrases)

            # Stage 2: Keyword extraction and parameter matching
            extracted_params = self._extract_parameters(
                user_input,
                skill.context_schema
            )

            # Stage 3: Calculate coverage score
            required = json.loads(skill.required_context) if skill.required_context else []
            param_coverage = len(extracted_params) / max(len(required), 1) if required else 1.0

            # Weighted combination
            combined_score = (
                fuzzy_score * 0.6 +
                param_coverage * 0.4
            )

            if combined_score >= skill.trigger_confidence_threshold:
                candidates.append((skill, combined_score, extracted_params))

        if not candidates:
            return (None, 0, {})

        return max(candidates, key=lambda x: x[1])

    def _fuzzy_match(self, user_input, phrases):
        """Calculate best fuzzy match score against trigger phrases."""
        best_score = 0

        for phrase in phrases:
            phrase_lower = phrase.lower().strip()

            # Handle placeholder substitution
            pattern = re.sub(r'\{[^}]+\}', r'.*', re.escape(phrase_lower))
            if re.search(pattern, user_input):
                return 1.0  # Exact pattern match

            # Calculate Levenshtein-like similarity
            score = self._similarity_score(user_input, phrase_lower)
            best_score = max(best_score, score)

        return best_score

    def _similarity_score(self, s1, s2):
        """Calculate normalized similarity between two strings."""
        # Simple token overlap for now; can be enhanced with rapidfuzz
        tokens1 = set(s1.split())
        tokens2 = set(s2.split())
        if not tokens1 or not tokens2:
            return 0
        intersection = tokens1 & tokens2
        return len(intersection) / max(len(tokens1), len(tokens2))

    def _extract_parameters(self, user_input, schema_json):
        """Extract parameters based on context schema."""
        if not schema_json:
            return {}

        schema = json.loads(schema_json)
        extracted = {}

        for param_name, param_def in schema.get('properties', {}).items():
            value = None

            # Try pattern extraction
            patterns = param_def.get('extraction_patterns', [])
            for pattern in patterns:
                match = re.search(pattern, user_input, re.IGNORECASE)
                if match:
                    value = match.group(1) if match.groups() else match.group()
                    break

            # Try hint-based extraction
            if not value:
                hints = param_def.get('extraction_hints', [])
                for hint in hints:
                    hint_pattern = rf'{hint}\s+(["\']?)([^"\'\s,]+)\1'
                    match = re.search(hint_pattern, user_input, re.IGNORECASE)
                    if match:
                        value = match.group(2)
                        break

            if value:
                extracted[param_name] = self._cast_value(value, param_def.get('type'))

        return extracted

    def _cast_value(self, value, type_hint):
        """Cast extracted value to appropriate type."""
        if type_hint == 'number':
            try:
                return float(value) if '.' in str(value) else int(value)
            except (ValueError, TypeError):
                return value
        return value


class StepExecutor:
    """Executes individual skill workflow steps."""

    def __init__(self, env):
        self.env = env

    def execute(self, step, context):
        """Execute a single workflow step."""
        method = getattr(self, f'_execute_{step.step_type}', None)
        if not method:
            raise ValidationError(f"Unknown step type: {step.step_type}")
        return method(step, context)

    def _execute_tool_call(self, step, context):
        """Execute an MCP tool call."""
        # Resolve parameter template
        params = self._resolve_template(step.tool_parameters, context)

        # Tool execution delegated to AI layer
        return {
            'type': 'tool_call',
            'tool': step.tool_name,
            'params': params,
        }

    def _execute_user_input(self, step, context):
        """Request input from user."""
        prompt = self._resolve_template(step.instructions, context)
        return {
            'requires_input': True,
            'prompt': prompt,
            'variable': step.output_variable,
        }

    def _execute_condition(self, step, context):
        """Evaluate conditional and determine next step."""
        try:
            result = safe_eval(step.condition_expression, context)
        except Exception:
            result = False

        next_step = step.on_success_step_id if result else step.on_failure_step_id
        return {
            'condition_result': result,
            'next_step_id': next_step.id if next_step else None,
        }

    def _execute_validation(self, step, context):
        """Validate data against rules."""
        try:
            result = safe_eval(step.condition_expression, context)
            if not result:
                raise ValidationError(step.instructions or "Validation failed")
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Validation error: {e}")

        return {'validated': True}

    def _execute_confirmation(self, step, context):
        """Request user confirmation."""
        message = self._resolve_template(step.instructions, context)
        return {
            'requires_input': True,
            'prompt': message,
            'confirmation': True,
        }

    def _execute_action(self, step, context):
        """Execute a referenced Odoo action."""
        if not step.action_id:
            raise ValidationError("No action configured for step")

        return step.action_id.read()[0]

    def _execute_subskill(self, step, context):
        """Execute a sub-skill."""
        if not step.subskill_id:
            raise ValidationError("No subskill configured")

        return step.subskill_id.run(context=context)

    def _resolve_template(self, template, context):
        """Replace {variable} placeholders with context values."""
        if not template:
            return template

        def replace_var(match):
            var_name = match.group(1)
            return str(context.get(var_name, match.group(0)))

        return re.sub(r'\{(\w+)\}', replace_var, template)


class RollbackManager:
    """Manages transaction savepoints for skill execution."""

    def __init__(self, env):
        self.env = env
        self.savepoint_stack = []

    def create_savepoint(self, name):
        """Create a database savepoint."""
        savepoint_id = f"skill_{name}_{uuid4().hex[:8]}"
        self.env.cr.execute(f"SAVEPOINT {savepoint_id}")
        self.savepoint_stack.append(savepoint_id)
        return savepoint_id

    def rollback_to_savepoint(self, savepoint_id):
        """Rollback to a specific savepoint."""
        self.env.cr.execute(f"ROLLBACK TO SAVEPOINT {savepoint_id}")

        # Clear savepoints after this one
        if savepoint_id in self.savepoint_stack:
            idx = self.savepoint_stack.index(savepoint_id)
            self.savepoint_stack = self.savepoint_stack[:idx]

    def commit(self):
        """Release all savepoints on success."""
        for savepoint_id in reversed(self.savepoint_stack):
            self.env.cr.execute(f"RELEASE SAVEPOINT {savepoint_id}")
        self.savepoint_stack.clear()


class IrActionsSkillExecution(models.Model):
    """Execution log for skill runs."""
    _name = 'ir.actions.skill.execution'
    _description = 'Skill Execution Log'
    _order = 'started_at desc'

    skill_id = fields.Many2one('ir.actions.skill', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', required=True)
    session_id = fields.Many2one('loomworks.ai.session')

    started_at = fields.Datetime(required=True)
    completed_at = fields.Datetime()
    duration_ms = fields.Integer(compute='_compute_duration', store=True)

    trigger_text = fields.Text()
    context_snapshot = fields.Text()

    state = fields.Selection([
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('rolled_back', 'Rolled Back'),
        ('cancelled', 'Cancelled'),
    ], required=True)

    result_summary = fields.Text()
    error_message = fields.Text()
    operations_log = fields.Text()

    @api.depends('started_at', 'completed_at')
    def _compute_duration(self):
        for rec in self:
            if rec.started_at and rec.completed_at:
                delta = rec.completed_at - rec.started_at
                rec.duration_ms = int(delta.total_seconds() * 1000)
            else:
                rec.duration_ms = 0
```

#### 1.3 Action Manager Integration

**Location**: `odoo/odoo/addons/base/models/ir_actions.py` (patch to existing file)

```python
# Add to IrActions class

@api.model
def _get_action_definition(self, action_id):
    """Extended to handle skill actions."""
    action = super()._get_action_definition(action_id)
    if action and action.get('type') == 'ir.actions.skill':
        # Skill actions return their execution result
        skill = self.env['ir.actions.skill'].browse(action_id)
        return skill.run()
    return action
```

---

### 2. Session Recording Infrastructure

#### 2.1 RPC Interceptor Service

**Location**: `odoo/addons/web/static/src/core/skill_recorder_service.js`

```javascript
/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

/**
 * Skill Recorder Service
 *
 * Intercepts RPC calls and user actions to record workflows
 * that can be converted into reusable skills.
 *
 * Architecture:
 * - Patches rpc service to capture all server calls
 * - Hooks into action service to track navigation
 * - Records DOM interactions via event delegation
 * - Produces structured recording that maps to skill steps
 */
export const skillRecorderService = {
    dependencies: ["rpc", "action", "notification", "user"],

    start(env, { rpc, action, notification, user }) {
        let isRecording = false;
        let recording = null;
        let frameCounter = 0;

        const originalRpc = rpc;

        /**
         * Patched RPC function that captures calls during recording.
         */
        async function patchedRpc(route, params = {}, settings = {}) {
            const result = await originalRpc(route, params, settings);

            if (isRecording && !settings.skipRecording) {
                recording.frames.push({
                    id: ++frameCounter,
                    timestamp: Date.now(),
                    type: 'rpc',
                    route,
                    params: sanitizeParams(params),
                    model: params.model,
                    method: params.method,
                    result: summarizeResult(result),
                });
            }

            return result;
        }

        /**
         * Start recording a new skill session.
         */
        function startRecording(options = {}) {
            if (isRecording) {
                throw new Error("Recording already in progress");
            }

            isRecording = true;
            frameCounter = 0;
            recording = {
                id: generateRecordingId(),
                startedAt: Date.now(),
                userId: user.userId,
                options,
                frames: [],
                userInputs: [],
                confirmations: [],
            };

            // Hook into action manager
            const originalDoAction = action.doAction.bind(action);
            action.doAction = async (actionRequest, options = {}) => {
                if (isRecording) {
                    recording.frames.push({
                        id: ++frameCounter,
                        timestamp: Date.now(),
                        type: 'action',
                        action: summarizeAction(actionRequest),
                    });
                }
                return originalDoAction(actionRequest, options);
            };

            notification.add("Skill recording started", { type: "info" });

            return recording.id;
        }

        /**
         * Stop recording and return the captured workflow.
         */
        function stopRecording() {
            if (!isRecording) {
                throw new Error("No recording in progress");
            }

            isRecording = false;
            recording.stoppedAt = Date.now();
            recording.duration = recording.stoppedAt - recording.startedAt;

            const result = { ...recording };
            recording = null;

            notification.add("Skill recording stopped", { type: "success" });

            return result;
        }

        /**
         * Record a user input during skill execution.
         */
        function captureUserInput(prompt, value) {
            if (isRecording) {
                recording.userInputs.push({
                    timestamp: Date.now(),
                    prompt,
                    value,
                    frameId: frameCounter,
                });
            }
        }

        /**
         * Check if recording is active.
         */
        function isRecordingActive() {
            return isRecording;
        }

        /**
         * Get current recording state.
         */
        function getRecordingState() {
            if (!isRecording) return null;
            return {
                id: recording.id,
                frameCount: recording.frames.length,
                duration: Date.now() - recording.startedAt,
            };
        }

        // Helper functions
        function generateRecordingId() {
            return `rec_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        }

        function sanitizeParams(params) {
            // Remove sensitive data from recorded params
            const sanitized = { ...params };
            delete sanitized.password;
            delete sanitized.token;
            delete sanitized.api_key;
            return sanitized;
        }

        function summarizeResult(result) {
            // Summarize large results for storage efficiency
            if (Array.isArray(result)) {
                return { type: 'array', length: result.length };
            }
            if (result && typeof result === 'object') {
                return { type: 'object', keys: Object.keys(result) };
            }
            return result;
        }

        function summarizeAction(action) {
            if (typeof action === 'string') {
                return { xmlId: action };
            }
            return {
                type: action.type,
                resModel: action.res_model,
                resId: action.res_id,
                viewMode: action.view_mode,
            };
        }

        // Replace RPC in environment
        env.services.rpc = patchedRpc;

        return {
            startRecording,
            stopRecording,
            captureUserInput,
            isRecordingActive,
            getRecordingState,
        };
    },
};

registry.category("services").add("skillRecorder", skillRecorderService);
```

#### 2.2 Action Logger Component

**Location**: `odoo/addons/web/static/src/core/skill_recording_indicator.js`

```javascript
/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

/**
 * Recording indicator displayed in systray during skill recording.
 */
export class SkillRecordingIndicator extends Component {
    static template = "web.SkillRecordingIndicator";
    static props = {};

    setup() {
        this.skillRecorder = useService("skillRecorder");
        this.state = useState({
            recording: false,
            frameCount: 0,
            duration: 0,
        });

        // Poll recording state
        this.interval = setInterval(() => this.updateState(), 500);
    }

    updateState() {
        const recordingState = this.skillRecorder.getRecordingState();
        if (recordingState) {
            this.state.recording = true;
            this.state.frameCount = recordingState.frameCount;
            this.state.duration = Math.floor(recordingState.duration / 1000);
        } else {
            this.state.recording = false;
        }
    }

    onStopClick() {
        const recording = this.skillRecorder.stopRecording();
        // Navigate to skill creation wizard with recording data
        this.env.services.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'ir.actions.skill.creation.wizard',
            views: [[false, 'form']],
            target: 'new',
            context: {
                default_recording_data: JSON.stringify(recording),
            },
        });
    }

    willUnmount() {
        clearInterval(this.interval);
    }
}

SkillRecordingIndicator.template = owl.xml`
    <div t-if="state.recording" class="o_skill_recording_indicator d-flex align-items-center text-danger">
        <span class="o_recording_dot me-2"></span>
        <span class="me-2">Recording: <t t-esc="state.frameCount"/> actions (<t t-esc="state.duration"/>s)</span>
        <button class="btn btn-sm btn-danger" t-on-click="onStopClick">
            <i class="fa fa-stop me-1"/>Stop
        </button>
    </div>
`;

registry.category("systray").add("skillRecordingIndicator", {
    Component: SkillRecordingIndicator,
    sequence: 1,
});
```

#### 2.3 Recording to Skill Converter

**Location**: `odoo/odoo/addons/base/wizard/skill_creation_wizard.py`

```python
# -*- coding: utf-8 -*-
"""Wizard for creating skills from recordings or natural language."""

import json
from odoo import api, fields, models


class SkillCreationWizard(models.TransientModel):
    _name = 'ir.actions.skill.creation.wizard'
    _description = 'Skill Creation Wizard'

    # Creation method
    creation_method = fields.Selection([
        ('recording', 'From Recording'),
        ('natural_language', 'From Description'),
        ('manual', 'Manual Definition'),
    ], default='recording', required=True)

    # Recording data (from recorder service)
    recording_data = fields.Text()

    # Natural language input
    skill_description = fields.Text(
        string="Describe your skill",
        help="Describe what this skill should do in natural language"
    )
    example_phrases = fields.Text(
        string="Example trigger phrases",
        help="Provide 3-5 examples of how users might ask for this skill"
    )

    # Generated/configured skill details
    name = fields.Char()
    technical_name = fields.Char()
    category = fields.Selection([
        ('sales', 'Sales'),
        ('purchase', 'Purchasing'),
        ('inventory', 'Inventory'),
        ('accounting', 'Accounting'),
        ('hr', 'Human Resources'),
        ('manufacturing', 'Manufacturing'),
        ('crm', 'CRM'),
        ('project', 'Project'),
        ('custom', 'Custom'),
    ], default='custom')

    # Preview
    preview_steps = fields.Text(readonly=True)
    preview_triggers = fields.Text(readonly=True)

    @api.onchange('recording_data')
    def _onchange_recording_data(self):
        """Parse recording and generate skill preview."""
        if not self.recording_data:
            return

        recording = json.loads(self.recording_data)
        steps = self._convert_frames_to_steps(recording.get('frames', []))

        self.preview_steps = json.dumps(steps, indent=2)
        self.name = self._derive_skill_name(steps)
        self.technical_name = self._to_technical_name(self.name)

    @api.onchange('skill_description')
    def _onchange_skill_description(self):
        """Generate skill preview from description using AI."""
        if not self.skill_description or len(self.skill_description) < 20:
            return

        # Placeholder: AI generation would happen here
        # In production, this calls Claude to generate skill definition
        self.name = self._extract_skill_name(self.skill_description)
        self.technical_name = self._to_technical_name(self.name)

    def action_create_skill(self):
        """Create the skill from wizard data."""
        self.ensure_one()

        if self.creation_method == 'recording':
            return self._create_from_recording()
        elif self.creation_method == 'natural_language':
            return self._create_from_description()
        else:
            return self._create_manual()

    def _create_from_recording(self):
        """Create skill from recorded workflow."""
        recording = json.loads(self.recording_data)
        steps = self._convert_frames_to_steps(recording.get('frames', []))

        # Infer trigger phrases from user inputs
        triggers = self._infer_triggers(recording)

        # Create skill record
        skill = self.env['ir.actions.skill'].create({
            'name': self.name,
            'technical_name': self.technical_name,
            'category': self.category,
            'trigger_phrases': json.dumps(triggers),
            'state': 'draft',
        })

        # Create step records
        for seq, step_data in enumerate(steps):
            self.env['ir.actions.skill.step'].create({
                'skill_id': skill.id,
                'sequence': (seq + 1) * 10,
                **step_data,
            })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ir.actions.skill',
            'res_id': skill.id,
            'views': [[False, 'form']],
            'target': 'current',
        }

    def _create_from_description(self):
        """Create skill from natural language description using AI."""
        # Placeholder: In production, calls Claude to generate full skill
        skill = self.env['ir.actions.skill'].create({
            'name': self.name,
            'technical_name': self.technical_name,
            'category': self.category,
            'trigger_phrases': json.dumps(
                self.example_phrases.split('\n') if self.example_phrases else []
            ),
            'system_prompt': self.skill_description,
            'state': 'draft',
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ir.actions.skill',
            'res_id': skill.id,
            'views': [[False, 'form']],
            'target': 'current',
        }

    def _create_manual(self):
        """Create empty skill for manual configuration."""
        skill = self.env['ir.actions.skill'].create({
            'name': self.name or 'New Skill',
            'technical_name': self.technical_name or 'new-skill',
            'category': self.category,
            'state': 'draft',
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ir.actions.skill',
            'res_id': skill.id,
            'views': [[False, 'form']],
            'target': 'current',
        }

    def _convert_frames_to_steps(self, frames):
        """Convert recording frames to skill step definitions."""
        steps = []

        for frame in frames:
            if frame['type'] == 'rpc':
                if frame.get('method') == 'create':
                    steps.append({
                        'name': f"Create {frame.get('model', 'record')}",
                        'step_type': 'tool_call',
                        'tool_name': 'create_record',
                        'tool_parameters': json.dumps({
                            'model': frame.get('model'),
                            'values': frame.get('params', {}).get('values', {}),
                        }),
                    })
                elif frame.get('method') == 'write':
                    steps.append({
                        'name': f"Update {frame.get('model', 'record')}",
                        'step_type': 'tool_call',
                        'tool_name': 'update_record',
                        'tool_parameters': json.dumps({
                            'model': frame.get('model'),
                        }),
                    })
                elif frame.get('method') == 'search_read':
                    steps.append({
                        'name': f"Search {frame.get('model', 'records')}",
                        'step_type': 'tool_call',
                        'tool_name': 'search_records',
                        'tool_parameters': json.dumps({
                            'model': frame.get('model'),
                            'domain': frame.get('params', {}).get('domain', []),
                        }),
                    })
            elif frame['type'] == 'action':
                action = frame.get('action', {})
                if action.get('type') == 'ir.actions.act_window':
                    steps.append({
                        'name': f"Open {action.get('resModel', 'view')}",
                        'step_type': 'action',
                        'instructions': f"Navigate to {action.get('resModel')}",
                    })

        return steps

    def _derive_skill_name(self, steps):
        """Derive a skill name from the steps."""
        if not steps:
            return "New Skill"

        # Use first create/update step's model
        for step in steps:
            if step.get('step_type') == 'tool_call':
                params = json.loads(step.get('tool_parameters', '{}'))
                model = params.get('model', '')
                if model:
                    model_name = model.replace('.', ' ').title()
                    tool = step.get('tool_name', '')
                    if 'create' in tool:
                        return f"Create {model_name}"
                    elif 'update' in tool:
                        return f"Update {model_name}"

        return "Recorded Workflow"

    def _to_technical_name(self, name):
        """Convert display name to technical name."""
        if not name:
            return 'new-skill'
        return name.lower().replace(' ', '-').replace('_', '-')

    def _infer_triggers(self, recording):
        """Infer trigger phrases from recording context."""
        triggers = []

        # Use user inputs as trigger templates
        for user_input in recording.get('userInputs', []):
            value = user_input.get('value', '')
            if value and len(value) > 5:
                triggers.append(value)

        # Generate variations based on skill name
        name = self.name or ''
        if name:
            triggers.extend([
                name.lower(),
                f"please {name.lower()}",
                f"I want to {name.lower()}",
            ])

        return triggers[:10]  # Limit to 10 triggers

    def _extract_skill_name(self, description):
        """Extract a skill name from the description."""
        # Simple extraction: use first sentence or first N words
        first_sentence = description.split('.')[0].strip()
        words = first_sentence.split()[:5]
        return ' '.join(words).title()
```

---

### 3. Natural Language in Core

#### 3.1 Skill Command Provider

**Location**: `odoo/addons/web/static/src/core/skill_command_provider.js`

```javascript
/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

/**
 * Command provider for skill-related actions in the command palette.
 *
 * Integrates skills into Odoo's command palette (Ctrl+K),
 * allowing users to:
 * - Execute skills by name
 * - Start skill recording
 * - Search skills by trigger phrase
 */
export const skillCommandProvider = {
    async provide(env, options) {
        const commands = [];
        const searchValue = options.searchValue?.toLowerCase() || "";

        // Add recording commands
        const recorder = env.services.skillRecorder;

        if (!recorder.isRecordingActive()) {
            commands.push({
                name: _t("Start Skill Recording"),
                description: _t("Record your actions to create a new skill"),
                category: "skills",
                action: () => {
                    recorder.startRecording();
                },
            });
        } else {
            commands.push({
                name: _t("Stop Skill Recording"),
                description: _t("Stop recording and create skill"),
                category: "skills",
                action: () => {
                    recorder.stopRecording();
                },
            });
        }

        // Add skill creation command
        commands.push({
            name: _t("Create New Skill"),
            description: _t("Create a skill from description"),
            category: "skills",
            action: async () => {
                await env.services.action.doAction({
                    type: 'ir.actions.act_window',
                    res_model: 'ir.actions.skill.creation.wizard',
                    views: [[false, 'form']],
                    target: 'new',
                    context: {
                        default_creation_method: 'natural_language',
                    },
                });
            },
        });

        // Fetch and add available skills
        if (searchValue.length >= 2) {
            try {
                const skills = await env.services.orm.searchRead(
                    'ir.actions.skill',
                    [
                        ['state', '=', 'active'],
                        '|',
                        ['name', 'ilike', searchValue],
                        ['trigger_phrases', 'ilike', searchValue],
                    ],
                    ['name', 'category', 'technical_name'],
                    { limit: 10 }
                );

                for (const skill of skills) {
                    commands.push({
                        name: skill.name,
                        description: _t("Run skill: %s", skill.technical_name),
                        category: "skills",
                        action: async () => {
                            await env.services.action.doAction({
                                type: 'ir.actions.skill',
                                id: skill.id,
                            });
                        },
                    });
                }
            } catch (e) {
                console.error("Failed to fetch skills for command palette:", e);
            }
        }

        return commands;
    },
};

registry.category("command_provider").add("skills", skillCommandProvider, { sequence: 50 });
```

#### 3.2 Intent Matcher Core Service

**Location**: `odoo/addons/web/static/src/core/skill_intent_service.js`

```javascript
/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Skill Intent Service
 *
 * Provides natural language intent matching in the web client,
 * enabling AI chat interfaces and voice commands to trigger skills.
 */
export const skillIntentService = {
    dependencies: ["orm", "action"],

    start(env, { orm, action }) {

        /**
         * Match user input against available skills.
         * Returns the best matching skill or null.
         */
        async function matchIntent(userInput) {
            const result = await orm.call(
                'ir.actions.skill',
                'match_intent',
                [userInput]
            );
            return result;
        }

        /**
         * Execute a skill with extracted parameters.
         */
        async function executeSkill(skillId, context = {}) {
            return action.doAction({
                type: 'ir.actions.skill',
                id: skillId,
                context,
            });
        }

        /**
         * Combined: match and execute if found.
         */
        async function processNaturalLanguage(userInput) {
            const match = await matchIntent(userInput);

            if (match && match.skill_id && match.confidence >= 0.75) {
                return executeSkill(match.skill_id, match.params);
            }

            return {
                matched: false,
                suggestions: match?.suggestions || [],
            };
        }

        return {
            matchIntent,
            executeSkill,
            processNaturalLanguage,
        };
    },
};

registry.category("services").add("skillIntent", skillIntentService);
```

---

### 4. Skill-Aware Views

#### 4.1 Record as Skill Button

**Location**: `odoo/addons/web/static/src/views/form/skill_form_controller_patch.js`

```javascript
/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

/**
 * Patch FormController to add "Record as Skill" functionality.
 */
patch(FormController.prototype, {
    setup() {
        super.setup();
        this.skillRecorder = useService("skillRecorder");
    },

    /**
     * Check if skill recording is available for this form.
     */
    get canRecordSkill() {
        // Available for all models except system models
        const systemModels = ['ir.', 'base.', 'res.users', 'res.config'];
        const model = this.model.root.resModel;
        return !systemModels.some(prefix => model.startsWith(prefix));
    },

    /**
     * Start recording actions on this form as a skill.
     */
    async onRecordAsSkill() {
        if (this.skillRecorder.isRecordingActive()) {
            this.notification.add("Recording already in progress", { type: "warning" });
            return;
        }

        this.skillRecorder.startRecording({
            startModel: this.model.root.resModel,
            startResId: this.model.root.resId,
        });
    },
});
```

#### 4.2 Skill Status Bar Widget

**Location**: `odoo/addons/web/static/src/views/form/skill_statusbar_widget.js`

```javascript
/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * Statusbar widget extension showing available skills for current record.
 */
export class SkillStatusbarWidget extends Component {
    static template = "web.SkillStatusbarWidget";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            skills: [],
            loading: true,
        });

        this.loadSkills();
    }

    async loadSkills() {
        const model = this.props.record.resModel;

        try {
            const skills = await this.orm.searchRead(
                'ir.actions.skill',
                [
                    ['state', '=', 'active'],
                    ['model_id.model', '=', model],
                ],
                ['name', 'technical_name', 'category'],
                { limit: 5 }
            );

            this.state.skills = skills;
        } catch (e) {
            console.error("Failed to load skills:", e);
        } finally {
            this.state.loading = false;
        }
    }

    async executeSkill(skill) {
        await this.action.doAction({
            type: 'ir.actions.skill',
            id: skill.id,
            context: {
                active_id: this.props.record.resId,
                active_model: this.props.record.resModel,
            },
        });
    }
}

SkillStatusbarWidget.template = owl.xml`
    <div class="o_skill_statusbar d-flex align-items-center">
        <t t-if="state.loading">
            <span class="text-muted">Loading skills...</span>
        </t>
        <t t-elif="state.skills.length">
            <div class="dropdown">
                <button class="btn btn-sm btn-outline-primary dropdown-toggle"
                        data-bs-toggle="dropdown">
                    <i class="fa fa-magic me-1"/>Skills
                </button>
                <ul class="dropdown-menu">
                    <t t-foreach="state.skills" t-as="skill" t-key="skill.id">
                        <li>
                            <a class="dropdown-item" href="#"
                               t-on-click.prevent="() => this.executeSkill(skill)">
                                <t t-esc="skill.name"/>
                            </a>
                        </li>
                    </t>
                </ul>
            </div>
        </t>
    </div>
`;

registry.category("fields").add("skill_statusbar", {
    component: SkillStatusbarWidget,
});
```

---

### 5. Built-in Skills in Core

The forked Odoo core ships with these pre-installed skills in `odoo/odoo/addons/base/data/skills.xml`:

#### 5.1 Core Skills Data

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="1">

        <!-- Create Sales Quote Skill -->
        <record id="skill_create_sales_quote" model="ir.actions.skill">
            <field name="name">Create Sales Quote</field>
            <field name="technical_name">create-sales-quote</field>
            <field name="category">sales</field>
            <field name="is_builtin">True</field>
            <field name="state">active</field>
            <field name="trigger_phrases">[
                "create a quote for",
                "make a quotation for",
                "prepare quote",
                "new quote for {customer}",
                "quote {quantity} {product} for {customer}"
            ]</field>
            <field name="context_schema">{
                "type": "object",
                "properties": {
                    "customer_name": {
                        "type": "string",
                        "description": "Customer or company name",
                        "extraction_hints": ["for", "to", "customer", "client"]
                    },
                    "products": {
                        "type": "array",
                        "description": "Products to quote"
                    },
                    "delivery_date": {
                        "type": "string",
                        "format": "date",
                        "extraction_hints": ["by", "before", "deliver"]
                    }
                },
                "required": ["customer_name"]
            }</field>
            <field name="required_context">["customer_name"]</field>
            <field name="system_prompt">You are creating a sales quotation.
Find the customer by name, then create a sales order with the requested products.
If products are not specified, ask for them.
Always confirm the final quote before completing.</field>
            <field name="allowed_tools">["search_records", "create_record", "update_record"]</field>
        </record>

        <!-- Check Inventory Skill -->
        <record id="skill_check_inventory" model="ir.actions.skill">
            <field name="name">Check Inventory Levels</field>
            <field name="technical_name">check-inventory-levels</field>
            <field name="category">inventory</field>
            <field name="is_builtin">True</field>
            <field name="state">active</field>
            <field name="trigger_phrases">[
                "do we have",
                "check stock of",
                "inventory level for",
                "how many {product} in stock",
                "what's the inventory of"
            ]</field>
            <field name="context_schema">{
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "extraction_hints": ["of", "for", "product"]
                    },
                    "warehouse_name": {
                        "type": "string",
                        "extraction_hints": ["in", "at", "warehouse"]
                    }
                },
                "required": ["product_name"]
            }</field>
            <field name="required_context">["product_name"]</field>
            <field name="system_prompt">Check inventory levels for the specified product.
Return available quantity, reserved quantity, and total on hand.
Include warehouse breakdown if multiple locations exist.</field>
            <field name="allowed_tools">["search_records"]</field>
        </record>

        <!-- Create Customer Skill -->
        <record id="skill_create_customer" model="ir.actions.skill">
            <field name="name">Create New Customer</field>
            <field name="technical_name">create-new-customer</field>
            <field name="category">sales</field>
            <field name="is_builtin">True</field>
            <field name="state">active</field>
            <field name="trigger_phrases">[
                "add new customer",
                "create customer",
                "new client {name}",
                "register customer",
                "add customer {name}"
            ]</field>
            <field name="context_schema">{
                "type": "object",
                "properties": {
                    "customer_name": {
                        "type": "string",
                        "extraction_hints": ["named", "called", "customer"]
                    },
                    "email": {
                        "type": "string",
                        "format": "email",
                        "extraction_hints": ["email", "contact"]
                    },
                    "phone": {
                        "type": "string",
                        "extraction_hints": ["phone", "tel", "call"]
                    },
                    "is_company": {
                        "type": "boolean",
                        "default": false
                    }
                },
                "required": ["customer_name"]
            }</field>
            <field name="required_context">["customer_name"]</field>
            <field name="system_prompt">Create a new customer (res.partner) record.
First check if a customer with similar name exists to prevent duplicates.
Set customer flag to true and fill in any provided contact details.</field>
            <field name="allowed_tools">["search_records", "create_record"]</field>
        </record>

        <!-- Generate Invoice Skill -->
        <record id="skill_generate_invoice" model="ir.actions.skill">
            <field name="name">Generate Customer Invoice</field>
            <field name="technical_name">generate-customer-invoice</field>
            <field name="category">accounting</field>
            <field name="is_builtin">True</field>
            <field name="state">active</field>
            <field name="trigger_phrases">[
                "bill the customer",
                "create invoice for",
                "generate invoice from SO",
                "invoice {customer}",
                "make invoice for order"
            ]</field>
            <field name="context_schema">{
                "type": "object",
                "properties": {
                    "customer_name": {
                        "type": "string",
                        "extraction_hints": ["for", "customer", "client"]
                    },
                    "order_reference": {
                        "type": "string",
                        "extraction_hints": ["SO", "order", "from"]
                    }
                }
            }</field>
            <field name="system_prompt">Generate an invoice for a customer or sales order.
If order reference provided, create invoice from that order.
Otherwise, find recent uninvoiced orders for the customer.
Confirm before posting the invoice.</field>
            <field name="allowed_tools">["search_records", "create_record", "execute_action"]</field>
        </record>

        <!-- Create Purchase Order Skill -->
        <record id="skill_create_purchase_order" model="ir.actions.skill">
            <field name="name">Create Purchase Order</field>
            <field name="technical_name">create-purchase-order</field>
            <field name="category">purchase</field>
            <field name="is_builtin">True</field>
            <field name="state">active</field>
            <field name="trigger_phrases">[
                "order from supplier",
                "create PO for",
                "purchase {products} from {vendor}",
                "reorder {product}",
                "new purchase order"
            ]</field>
            <field name="context_schema">{
                "type": "object",
                "properties": {
                    "vendor_name": {
                        "type": "string",
                        "extraction_hints": ["from", "supplier", "vendor"]
                    },
                    "products": {
                        "type": "array",
                        "extraction_hints": ["order", "purchase", "buy"]
                    },
                    "delivery_date": {
                        "type": "string",
                        "format": "date"
                    }
                },
                "required": ["vendor_name"]
            }</field>
            <field name="required_context">["vendor_name"]</field>
            <field name="system_prompt">Create a purchase order from a vendor.
Find the vendor by name, then create PO with requested products.
Use vendor's default pricelist for pricing.
Confirm quantities with user before finalizing.</field>
            <field name="allowed_tools">["search_records", "create_record", "update_record"]</field>
        </record>

        <!-- More built-in skills... -->

        <!-- Approve Purchase Order -->
        <record id="skill_approve_po" model="ir.actions.skill">
            <field name="name">Approve Purchase Order</field>
            <field name="technical_name">approve-purchase-order</field>
            <field name="category">purchase</field>
            <field name="is_builtin">True</field>
            <field name="state">active</field>
            <field name="trigger_phrases">[
                "approve purchase",
                "confirm PO",
                "approve PO {reference}",
                "authorize purchase"
            ]</field>
            <field name="context_schema">{
                "type": "object",
                "properties": {
                    "po_reference": {
                        "type": "string",
                        "extraction_hints": ["PO", "purchase", "order"]
                    },
                    "approval_note": {
                        "type": "string"
                    }
                },
                "required": ["po_reference"]
            }</field>
            <field name="required_context">["po_reference"]</field>
            <field name="system_prompt">Approve a purchase order by reference.
Verify the user has approval authority.
Show order summary and ask for confirmation before approving.</field>
            <field name="allowed_tools">["search_records", "execute_action", "update_record"]</field>
        </record>

        <!-- Process Return -->
        <record id="skill_process_return" model="ir.actions.skill">
            <field name="name">Process Customer Return</field>
            <field name="technical_name">process-customer-return</field>
            <field name="category">inventory</field>
            <field name="is_builtin">True</field>
            <field name="state">active</field>
            <field name="trigger_phrases">[
                "process return",
                "customer return for",
                "RMA for",
                "return {product}"
            ]</field>
            <field name="context_schema">{
                "type": "object",
                "properties": {
                    "order_reference": {
                        "type": "string"
                    },
                    "return_reason": {
                        "type": "string"
                    },
                    "products_to_return": {
                        "type": "array"
                    }
                }
            }</field>
            <field name="system_prompt">Process a customer return/RMA.
Find the original order or delivery.
Create return picking and process receipt.
Optionally create credit note if refund needed.</field>
            <field name="allowed_tools">["search_records", "create_record", "execute_action"]</field>
        </record>

        <!-- Generate Report -->
        <record id="skill_generate_report" model="ir.actions.skill">
            <field name="name">Generate Business Report</field>
            <field name="technical_name">generate-business-report</field>
            <field name="category">custom</field>
            <field name="is_builtin">True</field>
            <field name="state">active</field>
            <field name="trigger_phrases">[
                "generate report",
                "show me sales report",
                "create {report_type} report",
                "report for {period}"
            ]</field>
            <field name="context_schema">{
                "type": "object",
                "properties": {
                    "report_type": {
                        "type": "string",
                        "enum": ["sales", "purchase", "inventory", "accounting"]
                    },
                    "date_from": {
                        "type": "string",
                        "format": "date"
                    },
                    "date_to": {
                        "type": "string",
                        "format": "date"
                    }
                },
                "required": ["report_type"]
            }</field>
            <field name="required_context">["report_type"]</field>
            <field name="system_prompt">Generate a business report.
Determine report type and date range.
Execute appropriate report action and return results.</field>
            <field name="allowed_tools">["search_records", "generate_report", "execute_action"]</field>
        </record>

        <!-- Schedule Appointment -->
        <record id="skill_schedule_appointment" model="ir.actions.skill">
            <field name="name">Schedule Appointment</field>
            <field name="technical_name">schedule-appointment</field>
            <field name="category">crm</field>
            <field name="is_builtin">True</field>
            <field name="state">active</field>
            <field name="trigger_phrases">[
                "schedule meeting with",
                "book appointment",
                "set up call with {contact}",
                "meeting on {date}"
            ]</field>
            <field name="context_schema">{
                "type": "object",
                "properties": {
                    "contact_name": {
                        "type": "string"
                    },
                    "datetime": {
                        "type": "string",
                        "format": "date-time"
                    },
                    "duration_hours": {
                        "type": "number",
                        "default": 1
                    },
                    "subject": {
                        "type": "string"
                    }
                },
                "required": ["contact_name", "datetime"]
            }</field>
            <field name="required_context">["contact_name"]</field>
            <field name="system_prompt">Schedule a calendar event/meeting.
Find the contact by name.
Check calendar availability.
Create event and send invitation if requested.</field>
            <field name="allowed_tools">["search_records", "create_record", "execute_action"]</field>
        </record>

        <!-- Update Product Price -->
        <record id="skill_update_price" model="ir.actions.skill">
            <field name="name">Update Product Price</field>
            <field name="technical_name">update-product-pricing</field>
            <field name="category">inventory</field>
            <field name="is_builtin">True</field>
            <field name="state">active</field>
            <field name="trigger_phrases">[
                "update price of",
                "change price for",
                "set price of {product} to",
                "new price for"
            ]</field>
            <field name="context_schema">{
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string"
                    },
                    "new_price": {
                        "type": "number"
                    },
                    "pricelist_name": {
                        "type": "string"
                    }
                },
                "required": ["product_name", "new_price"]
            }</field>
            <field name="required_context">["product_name", "new_price"]</field>
            <field name="system_prompt">Update a product's price.
Find product by name.
Validate price is reasonable (warn if >50% change).
Update and confirm with old/new price comparison.</field>
            <field name="allowed_tools">["search_records", "update_record"]</field>
        </record>

    </data>
</odoo>
```

---

### 6. AI Integration (Phase 2 Connection)

#### 6.1 Skill Execution via MCP

The Skills Framework integrates with the AI layer (Phase 2) through MCP tool definitions:

**MCP Tool: `execute_skill`**

```python
# In loomworks_ai/mcp_tools/skill_tools.py

@mcp_tool(
    name="execute_skill",
    description="Execute a registered skill by name or trigger phrase"
)
def execute_skill(
    env,
    skill_identifier: str,
    context: dict = None,
) -> dict:
    """
    Execute a skill from the AI layer.

    :param skill_identifier: Technical name or trigger phrase
    :param context: Parameters for skill execution
    :return: Skill execution result
    """
    Skill = env['ir.actions.skill']

    # Try exact technical name match first
    skill = Skill.search([
        ('technical_name', '=', skill_identifier),
        ('state', '=', 'active'),
    ], limit=1)

    if not skill:
        # Try intent matching
        engine = SkillExecutionEngine(env)
        skill, confidence, extracted = engine.match_skill(skill_identifier)

        if skill and extracted:
            context = {**(context or {}), **extracted}

    if not skill:
        return {'error': f'No skill found matching: {skill_identifier}'}

    return skill.run(context=context)


@mcp_tool(
    name="list_skills",
    description="List available skills, optionally filtered by category"
)
def list_skills(
    env,
    category: str = None,
    search: str = None,
) -> list:
    """
    List available skills for AI to choose from.

    :param category: Filter by skill category
    :param search: Search in name/description
    :return: List of skill summaries
    """
    domain = [('state', '=', 'active')]

    if category:
        domain.append(('category', '=', category))

    if search:
        domain.extend([
            '|',
            ('name', 'ilike', search),
            ('trigger_phrases', 'ilike', search),
        ])

    skills = env['ir.actions.skill'].search(domain)

    return [{
        'id': s.id,
        'name': s.name,
        'technical_name': s.technical_name,
        'category': s.category,
        'description': s.system_prompt[:200] if s.system_prompt else '',
        'required_params': json.loads(s.required_context) if s.required_context else [],
    } for s in skills]


@mcp_tool(
    name="suggest_skill",
    description="Get skill suggestions for a user request"
)
def suggest_skill(
    env,
    user_input: str,
    limit: int = 3,
) -> list:
    """
    Suggest skills that might match user intent.

    :param user_input: Natural language user request
    :param limit: Maximum suggestions to return
    :return: List of skill suggestions with confidence
    """
    engine = SkillExecutionEngine(env)

    # Get all active skills
    skills = env['ir.actions.skill'].search([('state', '=', 'active')])

    # Score all skills
    scored = []
    for skill in skills:
        _, confidence, params = engine.intent_matcher.match(user_input, skill)
        if confidence > 0.3:  # Lower threshold for suggestions
            scored.append({
                'skill_id': skill.id,
                'name': skill.name,
                'technical_name': skill.technical_name,
                'confidence': confidence,
                'extracted_params': params,
            })

    # Sort by confidence and limit
    scored.sort(key=lambda x: x['confidence'], reverse=True)
    return scored[:limit]
```

#### 6.2 AI Agent Skill Integration

The AI agent (from Phase 2) uses skills as high-level capabilities:

```python
# In loomworks_ai/agent.py

class LoomworksAgent:
    """AI Agent with skill awareness."""

    async def process_message(self, user_message: str, session: AISession):
        """Process user message, attempting skill match first."""

        # Try skill matching before general AI processing
        skill_match = await self._try_skill_match(user_message)

        if skill_match and skill_match['confidence'] > 0.8:
            # High confidence: execute skill directly
            return await self._execute_skill_action(
                skill_match['skill_id'],
                skill_match['params'],
                session
            )
        elif skill_match and skill_match['confidence'] > 0.5:
            # Medium confidence: suggest skill but let AI decide
            return await self._process_with_skill_context(
                user_message,
                skill_match,
                session
            )
        else:
            # No skill match: standard AI processing
            return await self._process_general_request(user_message, session)

    async def _try_skill_match(self, user_input: str):
        """Attempt to match user input to a skill."""
        return self.env['ir.actions.skill'].match_intent(user_input)

    async def _execute_skill_action(self, skill_id, params, session):
        """Execute a skill and return result."""
        skill = self.env['ir.actions.skill'].browse(skill_id)

        # Create snapshot for rollback
        snapshot = await session.create_snapshot(f"skill_{skill.technical_name}")

        try:
            result = skill.run(context=params)
            return self._format_skill_result(result)
        except Exception as e:
            await session.rollback_to_snapshot(snapshot)
            return self._format_skill_error(skill, e)
```

---

## Implementation Steps

### Phase 6.1: Core Action Type (Weeks 47-48)

1. **Core Models** (Week 47)
   - [ ] Create `ir.actions.skill` model in `odoo/odoo/addons/base/models/`
   - [ ] Create `ir.actions.skill.step` model
   - [ ] Create `ir.actions.skill.execution` model
   - [ ] Add skill action to `ir.actions` inheritance chain
   - [ ] Create database migration for new tables

2. **Execution Engine** (Week 47-48)
   - [ ] Implement `SkillExecutionEngine` class
   - [ ] Implement `IntentMatcher` with fuzzy matching
   - [ ] Implement `StepExecutor` for workflow steps
   - [ ] Implement `RollbackManager` for transaction support
   - [ ] Add execution logging

3. **Action Manager Integration** (Week 48)
   - [ ] Patch action manager to handle `ir.actions.skill`
   - [ ] Register skill action type in action registry
   - [ ] Add skill action to client action handlers

### Phase 6.2: Recording Infrastructure (Weeks 49-50)

4. **RPC Interceptor** (Week 49)
   - [ ] Create `skill_recorder_service.js`
   - [ ] Implement RPC patching for call capture
   - [ ] Implement action manager hooks
   - [ ] Create recording data structure

5. **Recording UI** (Week 49-50)
   - [ ] Create recording indicator systray component
   - [ ] Add start/stop recording buttons
   - [ ] Create skill creation wizard
   - [ ] Implement recording-to-skill converter

### Phase 6.3: Natural Language & Commands (Weeks 51-52)

6. **Command Palette Integration** (Week 51)
   - [ ] Create `skill_command_provider.js`
   - [ ] Register skills in command palette
   - [ ] Add skill search functionality
   - [ ] Create skill execution commands

7. **Intent Service** (Week 51-52)
   - [ ] Create `skill_intent_service.js`
   - [ ] Add natural language matching API
   - [ ] Create AI chat integration points

### Phase 6.4: Built-in Skills & Views (Weeks 53-54)

8. **Built-in Skills** (Week 53)
   - [ ] Create `skills.xml` data file
   - [ ] Define 10 core ERP skills
   - [ ] Add skill steps for each built-in
   - [ ] Write skill documentation

9. **Skill-Aware Views** (Week 53-54)
   - [ ] Patch FormController for skill recording
   - [ ] Create skill statusbar widget
   - [ ] Add skill shortcuts to forms
   - [ ] Create skill management views

10. **AI Integration** (Week 54)
    - [ ] Create MCP skill tools
    - [ ] Integrate with Phase 2 AI agent
    - [ ] Add skill suggestions to chat
    - [ ] Test end-to-end skill execution

---

## Testing Criteria

### Intent Matching Accuracy

| Metric | Target | Measurement |
|--------|--------|-------------|
| Exact phrase match | 100% | Test with defined trigger phrases |
| Fuzzy match (typos) | >95% | Test with 1-2 character errors |
| Paraphrase match | >85% | Test with semantic variations |
| Parameter extraction | >90% | Test with varied input formats |
| False positive rate | <5% | Test with unrelated inputs |

### Workflow Completion

| Metric | Target | Measurement |
|--------|--------|-------------|
| Happy path completion | 100% | All steps execute successfully |
| Error recovery | >90% | Graceful handling of tool failures |
| Rollback success | 100% | No orphaned data on failure |
| User confirmation flow | 100% | Confirmation steps work correctly |

### Performance Benchmarks

| Metric | Target |
|--------|--------|
| Intent matching latency | <100ms |
| Skill execution start | <500ms |
| Average step execution | <2s |
| Full skill completion | <30s (typical) |
| Recording overhead | <5% RPC latency |
| Memory per active skill | <10MB |

### Test Cases

```python
class TestSkillFramework(TransactionCase):

    def test_skill_action_type_registered(self):
        """Test ir.actions.skill is a valid action type."""
        action = self.env['ir.actions.skill'].create({
            'name': 'Test Skill',
            'technical_name': 'test-skill',
        })
        self.assertEqual(action.type, 'ir.actions.skill')

    def test_intent_matching_exact(self):
        """Test exact trigger phrase matching."""
        skill = self._create_test_skill(triggers=["create a quote for"])
        engine = SkillExecutionEngine(self.env)
        result = engine.match_skill("create a quote for Acme Corp")
        self.assertEqual(result[0], skill)
        self.assertGreater(result[1], 0.9)

    def test_intent_matching_fuzzy(self):
        """Test fuzzy matching with typos."""
        skill = self._create_test_skill(triggers=["create a quote for"])
        engine = SkillExecutionEngine(self.env)
        result = engine.match_skill("creat a qoute for Acme")
        self.assertIsNotNone(result[0])
        self.assertGreater(result[1], 0.75)

    def test_parameter_extraction(self):
        """Test parameter extraction from natural language."""
        skill = self._create_test_skill(
            context_schema={
                "properties": {
                    "customer_name": {
                        "type": "string",
                        "extraction_hints": ["for", "customer"]
                    }
                }
            }
        )
        engine = SkillExecutionEngine(self.env)
        _, _, params = engine.match_skill("create a quote for Acme Corp")
        self.assertEqual(params.get("customer_name"), "Acme Corp")

    def test_skill_execution_with_rollback(self):
        """Test rollback when step fails."""
        skill = self._create_failing_skill()
        engine = SkillExecutionEngine(self.env)

        initial_count = self.env['sale.order'].search_count([])

        with self.assertRaises(UserError):
            engine.execute_skill(skill, {})

        # Verify no records created due to rollback
        final_count = self.env['sale.order'].search_count([])
        self.assertEqual(initial_count, final_count)

    def test_recording_captures_rpc(self):
        """Test that recording captures RPC calls."""
        # This would be tested via JavaScript tests
        pass
```

---

## Security Considerations

### Skill Execution Sandboxing

1. **Tool Restrictions**: Skills can only use explicitly bound tools in `allowed_tools`
2. **Model Access**: Enforce user permissions for all operations via `env.user`
3. **Rate Limiting**: Limit skill executions per user/minute
4. **Audit Logging**: Log all skill executions to `ir.actions.skill.execution`
5. **Sensitive Models**: Block skills from accessing `res.users`, `ir.rule`, `ir.config_parameter`

### Recording Security

1. **Sensitive Data Filtering**: Remove passwords, tokens from recorded RPC params
2. **Recording Permissions**: Only users with skill creation rights can record
3. **Playback Isolation**: Recorded skills execute with current user permissions
4. **Data Retention**: Auto-expire recordings after configurable period

---

## Dependencies

### Python Packages (Core)

```
# Added to odoo/requirements.txt
rapidfuzz>=3.0.0          # Fuzzy string matching for intent
```

### JavaScript Dependencies

```javascript
// Using existing Odoo dependencies
// No additional npm packages required
```

### Odoo Module Dependencies

Built into forked core, no external module dependencies.

Optional integrations with standard Odoo modules:
- `sale` - For sales skills
- `purchase` - For purchasing skills
- `stock` - For inventory skills
- `account` - For accounting skills

---

## References

### Research Sources

- [Odoo 18 Actions Documentation](https://www.odoo.com/documentation/18.0/developer/reference/backend/actions.html)
- [Odoo 18 Client Actions](https://www.odoo.com/documentation/18.0/developer/howtos/javascript_client_action.html)
- [OWL Framework Documentation](https://odoo.github.io/owl/)
- [Odoo Service Registry](https://www.odoo.com/documentation/18.0/developer/reference/frontend/registries)
- [RRWeb Session Recording](https://www.rrweb.io/)
- [Odoo Keyboard Shortcuts](https://www.odoo.com/documentation/18.0/applications/essentials/keyboard_shortcuts.html)

### Related Specifications

- Phase 2: AI Integration Layer (`loomworks_ai`)
- Phase 5: Hosting Infrastructure (`loomworks_snapshot`)
- Odoo 18 Developer Documentation

### Odoo Core Files (Reference)

- `odoo/odoo/addons/base/models/ir_actions.py` - Base action architecture
- `odoo/addons/web/static/src/core/` - Frontend services
- `odoo/addons/web/static/src/views/` - View components
