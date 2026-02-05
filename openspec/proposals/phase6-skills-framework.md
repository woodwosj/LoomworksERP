# Phase 6: Skills Framework Proposal

## Overview

The Skills Framework enables Loomworks ERP users to define, execute, and share reusable AI workflow templates triggered by natural language. Skills transform general-purpose AI agents into specialized ERP assistants that can reliably execute complex business operations through standardized, composable workflows.

### Key Objectives

1. **Natural Language Activation**: Users trigger skills through conversational phrases (e.g., "create a quote for Acme Corp")
2. **Reusable Workflows**: Define once, execute consistently across sessions and users
3. **Session-to-Skill Conversion**: Record user interactions and convert them to shareable skills
4. **Extensible Architecture**: Enable community-developed skills through a marketplace model
5. **Enterprise Control**: Role-based skill access and organization-wide management

---

## Technical Design

### 1. Skills Architecture

#### 1.1 Core Data Models

##### `loomworks.skill` Model

```python
class LoomworksSkill(models.Model):
    _name = "loomworks.skill"
    _description = "AI Skill Definition"

    # Identity
    name = fields.Char(required=True, string="Skill Name")
    technical_name = fields.Char(required=True, index=True)  # e.g., "create-purchase-order"
    version = fields.Char(default="1.0.0")

    # Metadata
    description = fields.Text(required=True)  # Determines when Claude invokes the skill
    category = fields.Selection([
        ('sales', 'Sales'),
        ('purchase', 'Purchasing'),
        ('inventory', 'Inventory'),
        ('accounting', 'Accounting'),
        ('hr', 'Human Resources'),
        ('manufacturing', 'Manufacturing'),
        ('custom', 'Custom'),
    ], default='custom')

    # Trigger Configuration
    trigger_phrases = fields.Text()  # JSON array of trigger phrases
    trigger_confidence_threshold = fields.Float(default=0.75)  # Minimum match score

    # Skill Content
    system_prompt = fields.Text()  # Instructions for Claude when executing
    skill_content = fields.Text()  # Full SKILL.md content (Markdown)

    # Tool Bindings
    tool_ids = fields.Many2many(
        "loomworks.ai.tool",
        string="Allowed Tools",
        help="MCP tools this skill can invoke"
    )

    # Steps (for multi-step workflows)
    step_ids = fields.One2many(
        "loomworks.skill.step",
        "skill_id",
        string="Workflow Steps"
    )

    # Context Variables
    context_variables = fields.Text()  # JSON schema for extractable parameters
    required_context = fields.Text()   # JSON array of required context keys

    # Access Control
    is_builtin = fields.Boolean(default=False)
    is_published = fields.Boolean(default=False)
    company_id = fields.Many2one("res.company")
    user_id = fields.Many2one("res.users", string="Created By")

    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('testing', 'Testing'),
        ('active', 'Active'),
        ('deprecated', 'Deprecated'),
    ], default='draft')

    # Statistics
    execution_count = fields.Integer(readonly=True)
    success_rate = fields.Float(readonly=True, compute="_compute_success_rate")
    avg_execution_time = fields.Float(readonly=True)
```

##### `loomworks.skill.step` Model

```python
class LoomworksSkillStep(models.Model):
    _name = "loomworks.skill.step"
    _description = "Skill Workflow Step"
    _order = "sequence, id"

    skill_id = fields.Many2one("loomworks.skill", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)

    # Step Type
    step_type = fields.Selection([
        ('tool_call', 'Tool Invocation'),
        ('user_input', 'Request User Input'),
        ('condition', 'Conditional Branch'),
        ('loop', 'Loop/Iteration'),
        ('subskill', 'Execute Sub-Skill'),
        ('validation', 'Validate Data'),
        ('confirmation', 'User Confirmation'),
    ], required=True)

    # Tool Call Configuration
    tool_id = fields.Many2one("loomworks.ai.tool")
    tool_parameters = fields.Text()  # JSON template with variable placeholders

    # Conditional Logic
    condition_expression = fields.Text()  # Python expression for branching
    on_success_step_id = fields.Many2one("loomworks.skill.step")
    on_failure_step_id = fields.Many2one("loomworks.skill.step")

    # Sub-skill Reference
    subskill_id = fields.Many2one("loomworks.skill")

    # Error Handling
    is_critical = fields.Boolean(default=True)  # If True, failure stops execution
    retry_count = fields.Integer(default=0)
    rollback_on_failure = fields.Boolean(default=True)

    # Output Mapping
    output_variable = fields.Char()  # Store result in this context variable
    output_transform = fields.Text()  # Python expression to transform output

    # Instructions
    instructions = fields.Text()  # Natural language instructions for this step
```

##### `loomworks.skill.execution` Model

```python
class LoomworksSkillExecution(models.Model):
    _name = "loomworks.skill.execution"
    _description = "Skill Execution Log"

    skill_id = fields.Many2one("loomworks.skill", required=True)
    session_id = fields.Many2one("loomworks.ai.session")
    user_id = fields.Many2one("res.users")

    # Timing
    started_at = fields.Datetime()
    completed_at = fields.Datetime()
    duration_ms = fields.Integer(compute="_compute_duration")

    # Input/Output
    trigger_text = fields.Text()  # Original user input
    extracted_parameters = fields.Text()  # JSON
    context_snapshot = fields.Text()  # JSON of context at start

    # Result
    state = fields.Selection([
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('rolled_back', 'Rolled Back'),
        ('cancelled', 'Cancelled'),
    ])
    result_summary = fields.Text()
    error_message = fields.Text()

    # Rollback Support
    snapshot_id = fields.Many2one("loomworks.snapshot")
    operations_log = fields.Text()  # JSON array of operations performed
```

#### 1.2 Trigger Phrase Matching Strategy

The Skills Framework uses a **hybrid intent matching** approach combining:

1. **Fuzzy String Matching** (Levenshtein/Damerau-Levenshtein)
   - Handles typos and minor variations
   - Normalized edit distance scoring
   - Threshold-based acceptance (default 0.75)

2. **Semantic Similarity** (Embedding-based)
   - Claude generates embeddings for trigger phrases
   - Cosine similarity for meaning-based matching
   - Handles paraphrases and natural variations

3. **Keyword Extraction**
   - Extract key entities (customer names, product codes, amounts)
   - Match against domain-specific vocabularies
   - Support for Odoo model field references

```python
class IntentMatcher:
    """Multi-strategy intent matching for skill activation."""

    def match_skill(self, user_input: str, available_skills: list) -> tuple[Skill, float, dict]:
        """
        Returns: (matched_skill, confidence_score, extracted_params)
        """
        candidates = []

        for skill in available_skills:
            # Stage 1: Fuzzy match against trigger phrases
            fuzzy_score = self._fuzzy_match(user_input, skill.trigger_phrases)

            # Stage 2: Semantic similarity (cached embeddings)
            semantic_score = self._semantic_match(user_input, skill.description)

            # Stage 3: Keyword/entity extraction
            extracted_params = self._extract_parameters(user_input, skill.context_variables)
            param_coverage = len(extracted_params) / max(len(skill.required_context), 1)

            # Weighted combination
            combined_score = (
                fuzzy_score * 0.3 +
                semantic_score * 0.5 +
                param_coverage * 0.2
            )

            if combined_score >= skill.trigger_confidence_threshold:
                candidates.append((skill, combined_score, extracted_params))

        # Return highest-scoring candidate
        return max(candidates, key=lambda x: x[1]) if candidates else (None, 0, {})
```

#### 1.3 Tool Binding Architecture

Skills bind to MCP tools defined in `loomworks.ai.tool`:

```python
class LoomworksAITool(models.Model):
    _name = "loomworks.ai.tool"
    _description = "MCP Tool Definition"

    name = fields.Char(required=True)  # e.g., "search_records"
    mcp_name = fields.Char()  # Full MCP identifier, e.g., "mcp__odoo__search_records"
    description = fields.Text()

    # Schema
    input_schema = fields.Text()  # JSON Schema for parameters
    output_schema = fields.Text()  # JSON Schema for return value

    # Security
    requires_models = fields.Char()  # Comma-separated model list
    permission_level = fields.Selection([
        ('read', 'Read Only'),
        ('write', 'Read/Write'),
        ('admin', 'Administrative'),
    ])

    # Categorization
    category = fields.Selection([
        ('crud', 'CRUD Operations'),
        ('workflow', 'Workflow Actions'),
        ('report', 'Reporting'),
        ('integration', 'External Integration'),
    ])
```

#### 1.4 Context Variables and Parameter Extraction

Skills define extractable parameters using JSON Schema with Odoo-specific extensions:

```json
{
  "type": "object",
  "properties": {
    "customer_name": {
      "type": "string",
      "description": "Customer or company name",
      "odoo_model": "res.partner",
      "odoo_field": "name",
      "extraction_hints": ["for", "to", "customer"]
    },
    "product_name": {
      "type": "string",
      "description": "Product being quoted",
      "odoo_model": "product.product",
      "odoo_field": "name",
      "extraction_hints": ["product", "item", "of"]
    },
    "quantity": {
      "type": "number",
      "description": "Quantity of items",
      "extraction_patterns": ["\\d+\\s*(units?|pcs?|pieces?)"]
    },
    "delivery_date": {
      "type": "string",
      "format": "date",
      "description": "Requested delivery date",
      "extraction_hints": ["by", "before", "deliver"]
    }
  },
  "required": ["customer_name"]
}
```

---

### 2. Skills Creation Agent

The Skills Creation Agent enables users to define new skills through natural language or by recording existing sessions.

#### 2.1 Natural Language Skill Definition

```python
class SkillCreationWizard(models.TransientModel):
    _name = "loomworks.skill.creation.wizard"

    # User Input
    skill_description = fields.Text(
        string="Describe your skill",
        help="Describe what this skill should do in natural language"
    )
    example_phrases = fields.Text(
        string="Example trigger phrases",
        help="Provide 3-5 examples of how users might ask for this skill"
    )

    # AI-Generated Output
    generated_skill_id = fields.Many2one("loomworks.skill")

    def action_generate_skill(self):
        """Use Claude to generate skill definition from description."""
        prompt = f"""
        Create a Loomworks ERP skill definition based on this description:

        Description: {self.skill_description}
        Example triggers: {self.example_phrases}

        Generate:
        1. A technical name (kebab-case)
        2. Expanded trigger phrases (10 variations)
        3. Required context variables with extraction hints
        4. Step-by-step workflow with tool calls
        5. System prompt for execution
        6. Error handling strategy

        Output as JSON matching the loomworks.skill schema.
        """
        # Call Claude Agent SDK to generate skill definition
        result = self._generate_with_claude(prompt)
        return self._create_skill_from_json(result)
```

#### 2.2 Session Recording to Skill Conversion

The framework captures user interactions during an AI session and converts successful workflows into reusable skills.

```python
class SessionRecorder:
    """Records AI session interactions for skill conversion."""

    def start_recording(self, session_id: int):
        """Begin capturing interactions."""
        self.recording = {
            "session_id": session_id,
            "started_at": datetime.now(),
            "frames": [],  # Each interaction frame
            "tool_calls": [],
            "user_confirmations": [],
        }

    def capture_frame(self, frame_type: str, data: dict):
        """Capture a single interaction frame."""
        self.recording["frames"].append({
            "timestamp": datetime.now(),
            "type": frame_type,  # 'user_input', 'tool_call', 'tool_result', 'confirmation'
            "data": data,
            "context_snapshot": self._capture_context(),
        })

    def convert_to_skill(self) -> dict:
        """Convert recorded session into skill definition."""
        # Analyze frames to identify:
        # 1. Initial trigger (first user input)
        # 2. Parameter extraction from inputs
        # 3. Tool call sequence
        # 4. Conditional branches taken
        # 5. Confirmation points

        return {
            "name": self._derive_skill_name(),
            "trigger_phrases": self._extract_trigger_variations(),
            "context_variables": self._infer_parameters(),
            "steps": self._build_workflow_steps(),
            "system_prompt": self._generate_system_prompt(),
        }
```

#### 2.3 Skill Testing and Validation

```python
class SkillValidator:
    """Validates skill definitions before activation."""

    def validate(self, skill: LoomworksSkill) -> ValidationResult:
        errors = []
        warnings = []

        # 1. Schema Validation
        if not self._validate_context_schema(skill.context_variables):
            errors.append("Invalid context variable schema")

        # 2. Tool Availability
        for tool in skill.tool_ids:
            if not self._tool_available(tool):
                errors.append(f"Tool {tool.name} not available")

        # 3. Step Connectivity
        if not self._validate_step_flow(skill.step_ids):
            errors.append("Unreachable steps in workflow")

        # 4. Trigger Phrase Quality
        phrase_quality = self._assess_trigger_quality(skill.trigger_phrases)
        if phrase_quality < 0.5:
            warnings.append("Trigger phrases may have low match accuracy")

        # 5. Test Execution (dry run)
        test_result = self._dry_run(skill, sample_inputs=3)
        if not test_result.success:
            errors.append(f"Dry run failed: {test_result.error}")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            coverage_score=test_result.coverage
        )
```

#### 2.4 Skill Export Format

Skills are exported as portable packages following the Anthropic Agent Skills standard:

```
skill-package/
├── SKILL.md           # Main skill definition (YAML frontmatter + Markdown)
├── manifest.json      # Package metadata and dependencies
├── scripts/           # Bundled helper scripts
│   ├── validate.py
│   └── helpers.py
├── templates/         # Output templates
│   └── quote_email.md
└── tests/             # Test cases
    └── test_cases.json
```

**SKILL.md Format:**

```markdown
---
name: create-sales-quote
version: 1.0.0
description: Creates a sales quotation for a customer with specified products and quantities
category: sales
author: Loomworks
license: LGPL-3.0
triggers:
  - "create a quote for"
  - "make a quotation"
  - "prepare a sales quote"
  - "quote for {customer}"
  - "new quote with {products}"
tools:
  - search_records
  - create_record
  - update_record
  - send_email
context:
  customer_name:
    type: string
    required: true
    odoo_model: res.partner
  products:
    type: array
    items:
      type: object
      properties:
        name: { type: string }
        quantity: { type: number }
  delivery_date:
    type: string
    format: date
---

# Create Sales Quote

This skill creates a sales quotation for a customer.

## Prerequisites
- Customer must exist in the system
- Products must be available for sale

## Workflow

### Step 1: Find Customer
Search for the customer by name. If multiple matches, ask user to clarify.

### Step 2: Validate Products
For each product:
1. Search product catalog
2. Check availability
3. Confirm pricing

### Step 3: Create Quotation
Create the sales order with:
- Customer as partner
- All product lines with quantities
- Requested delivery date (if provided)

### Step 4: Confirmation
Display summary and ask for confirmation before finalizing.

## Error Handling
- If customer not found: Ask to create or search again
- If product not available: Suggest alternatives
- On any failure: Rollback all changes
```

---

### 3. Built-in Skills Library

The following 10 core ERP skills ship with Loomworks:

#### 3.1 Create Quote

| Property | Value |
|----------|-------|
| Technical Name | `create-sales-quote` |
| Category | Sales |
| Trigger Phrases | "create a quote for", "make a quotation", "prepare quote", "new quote for {customer}" |
| Tools Used | `search_records`, `create_record`, `update_record` |
| Context Variables | `customer_name` (required), `products[]`, `delivery_date`, `discount_percent` |

**Steps:**
1. Search customer by name (`res.partner`)
2. Validate/search products (`product.product`)
3. Create sales order (`sale.order`)
4. Add order lines (`sale.order.line`)
5. Confirm with user
6. Return quote reference and summary

---

#### 3.2 Check Inventory

| Property | Value |
|----------|-------|
| Technical Name | `check-inventory-levels` |
| Category | Inventory |
| Trigger Phrases | "do we have", "check stock of", "inventory level for", "how many {product} in stock" |
| Tools Used | `search_records`, `execute_action` |
| Context Variables | `product_name` (required), `warehouse_name`, `include_reserved` |

**Steps:**
1. Search product by name/code (`product.product`)
2. Get stock quantities (`stock.quant`)
3. Calculate available vs reserved
4. Format inventory report
5. Return summary with reorder recommendations

---

#### 3.3 Generate Invoice

| Property | Value |
|----------|-------|
| Technical Name | `generate-customer-invoice` |
| Category | Accounting |
| Trigger Phrases | "bill the customer", "create invoice for", "generate invoice from SO", "invoice {customer}" |
| Tools Used | `search_records`, `create_record`, `execute_action` |
| Context Variables | `customer_name`, `order_reference`, `include_delivered_only` |

**Steps:**
1. Find sales order or customer orders
2. Validate deliveries completed
3. Create invoice (`account.move`)
4. Add invoice lines
5. Confirm invoice posting
6. Return invoice number and total

---

#### 3.4 Approve Purchase Order

| Property | Value |
|----------|-------|
| Technical Name | `approve-purchase-order` |
| Category | Purchasing |
| Trigger Phrases | "approve purchase", "confirm PO", "approve PO {reference}", "authorize purchase" |
| Tools Used | `search_records`, `execute_action`, `update_record` |
| Context Variables | `po_reference` (required), `approval_note` |

**Steps:**
1. Find purchase order by reference
2. Validate user has approval authority
3. Check budget availability
4. Execute approval workflow
5. Notify stakeholders
6. Return confirmation

---

#### 3.5 Create Customer

| Property | Value |
|----------|-------|
| Technical Name | `create-new-customer` |
| Category | Sales |
| Trigger Phrases | "add new customer", "create customer", "new client {name}", "register customer" |
| Tools Used | `search_records`, `create_record` |
| Context Variables | `customer_name` (required), `email`, `phone`, `address`, `is_company` |

**Steps:**
1. Check for existing customer (prevent duplicates)
2. Validate required fields
3. Create partner record (`res.partner`)
4. Set customer flag and defaults
5. Return customer ID and profile link

---

#### 3.6 Process Return

| Property | Value |
|----------|-------|
| Technical Name | `process-customer-return` |
| Category | Inventory |
| Trigger Phrases | "process return", "customer return for", "RMA for", "return {product}" |
| Tools Used | `search_records`, `create_record`, `execute_action` |
| Context Variables | `order_reference`, `return_reason`, `products_to_return[]` |

**Steps:**
1. Find original order/delivery
2. Create return picking (`stock.picking`)
3. Add return lines
4. Process return receipt
5. Create credit note if applicable
6. Return RMA number

---

#### 3.7 Generate Report

| Property | Value |
|----------|-------|
| Technical Name | `generate-business-report` |
| Category | Reporting |
| Trigger Phrases | "generate report", "show me sales report", "create {report_type} report", "report for {period}" |
| Tools Used | `search_records`, `generate_report`, `execute_action` |
| Context Variables | `report_type` (required), `date_from`, `date_to`, `filters` |

**Steps:**
1. Identify report type and parameters
2. Execute report query
3. Format results (table/chart data)
4. Generate PDF if requested
5. Return report data or download link

---

#### 3.8 Schedule Appointment

| Property | Value |
|----------|-------|
| Technical Name | `schedule-appointment` |
| Category | CRM |
| Trigger Phrases | "schedule meeting with", "book appointment", "set up call with {contact}", "meeting on {date}" |
| Tools Used | `search_records`, `create_record`, `execute_action` |
| Context Variables | `contact_name` (required), `datetime` (required), `duration_hours`, `subject`, `attendees[]` |

**Steps:**
1. Find contact/partner
2. Check calendar availability
3. Create calendar event (`calendar.event`)
4. Send invitations
5. Return meeting details and link

---

#### 3.9 Update Product Price

| Property | Value |
|----------|-------|
| Technical Name | `update-product-pricing` |
| Category | Inventory |
| Trigger Phrases | "update price of", "change price for", "set price of {product} to", "new price for" |
| Tools Used | `search_records`, `update_record` |
| Context Variables | `product_name` (required), `new_price` (required), `pricelist_name`, `effective_date` |

**Steps:**
1. Find product
2. Validate price (positive, reasonable change %)
3. Update price or pricelist item
4. Log price change history
5. Return confirmation with old/new prices

---

#### 3.10 Create Purchase Order

| Property | Value |
|----------|-------|
| Technical Name | `create-purchase-order` |
| Category | Purchasing |
| Trigger Phrases | "order from supplier", "create PO for", "purchase {products} from {vendor}", "reorder {product}" |
| Tools Used | `search_records`, `create_record`, `update_record` |
| Context Variables | `vendor_name` (required), `products[]` (required), `delivery_date` |

**Steps:**
1. Find or confirm vendor
2. Validate products and vendor relationship
3. Get vendor pricing
4. Create purchase order (`purchase.order`)
5. Add order lines
6. Return PO reference

---

### 4. Skills Execution Engine

The execution engine orchestrates skill workflows with comprehensive error handling and rollback support.

#### 4.1 Intent Matching Algorithm

```python
class SkillExecutionEngine:
    """Orchestrates skill discovery and execution."""

    def __init__(self, session: AISession):
        self.session = session
        self.intent_matcher = IntentMatcher()
        self.context = SkillContext()

    async def process_user_input(self, user_input: str) -> ExecutionResult:
        """Main entry point for skill-based processing."""

        # 1. Skill Discovery
        available_skills = self._get_available_skills()
        skill, confidence, extracted_params = self.intent_matcher.match_skill(
            user_input, available_skills
        )

        if skill is None:
            return ExecutionResult(
                matched=False,
                message="No matching skill found. Would you like me to help you differently?"
            )

        # 2. Parameter Completion
        if missing := self._check_missing_params(skill, extracted_params):
            return ExecutionResult(
                matched=True,
                skill=skill,
                needs_input=True,
                missing_params=missing,
                message=f"To {skill.name}, I need: {', '.join(missing)}"
            )

        # 3. Skill Execution
        return await self.execute_skill(skill, extracted_params)
```

#### 4.2 Parameter Extraction from User Input

```python
class ParameterExtractor:
    """Extracts skill parameters from natural language input."""

    def extract(self, user_input: str, schema: dict) -> dict:
        """
        Extract parameters based on context variable schema.
        Uses combination of:
        1. Pattern matching (regex)
        2. Entity recognition (Odoo model lookup)
        3. Claude-based extraction for complex cases
        """
        extracted = {}

        for param_name, param_def in schema.get("properties", {}).items():
            value = None

            # Try pattern extraction first
            if patterns := param_def.get("extraction_patterns"):
                value = self._match_patterns(user_input, patterns)

            # Try hint-based extraction
            if not value and (hints := param_def.get("extraction_hints")):
                value = self._extract_near_hints(user_input, hints)

            # Try Odoo model lookup
            if not value and (model := param_def.get("odoo_model")):
                value = self._lookup_odoo_entity(user_input, model, param_def.get("odoo_field"))

            # Fallback to Claude extraction
            if not value and param_def.get("required"):
                value = self._claude_extract(user_input, param_name, param_def)

            if value is not None:
                extracted[param_name] = self._cast_value(value, param_def.get("type"))

        return extracted
```

#### 4.3 Step Execution with Error Handling

```python
class StepExecutor:
    """Executes individual skill steps with error handling."""

    async def execute_step(self, step: SkillStep, context: SkillContext) -> StepResult:
        """Execute a single workflow step."""

        try:
            if step.step_type == 'tool_call':
                result = await self._execute_tool(step, context)
            elif step.step_type == 'user_input':
                result = await self._request_user_input(step, context)
            elif step.step_type == 'condition':
                result = self._evaluate_condition(step, context)
            elif step.step_type == 'subskill':
                result = await self._execute_subskill(step, context)
            elif step.step_type == 'validation':
                result = self._validate_data(step, context)
            elif step.step_type == 'confirmation':
                result = await self._get_confirmation(step, context)

            # Store output in context
            if step.output_variable and result.data:
                context.set(step.output_variable, result.data)

            return result

        except ToolExecutionError as e:
            return self._handle_step_error(step, e, context)

    async def _execute_tool(self, step: SkillStep, context: SkillContext) -> StepResult:
        """Execute an MCP tool call."""

        # Resolve parameter template with context values
        params = self._resolve_template(step.tool_parameters, context)

        # Call MCP tool
        tool_result = await self.mcp_client.call_tool(
            step.tool_id.mcp_name,
            params
        )

        # Apply output transformation if defined
        if step.output_transform:
            tool_result = eval(step.output_transform, {"result": tool_result, "context": context})

        return StepResult(success=True, data=tool_result)
```

#### 4.4 Rollback on Failure

```python
class RollbackManager:
    """Manages transaction rollback for failed skill executions."""

    def __init__(self, env):
        self.env = env
        self.savepoint_stack = []
        self.operation_log = []

    def create_savepoint(self, name: str):
        """Create a database savepoint."""
        savepoint_id = f"skill_{name}_{uuid4().hex[:8]}"
        self.env.cr.execute(f"SAVEPOINT {savepoint_id}")
        self.savepoint_stack.append(savepoint_id)
        return savepoint_id

    def log_operation(self, operation: dict):
        """Log an operation for potential rollback."""
        self.operation_log.append({
            **operation,
            "timestamp": datetime.now(),
            "savepoint": self.savepoint_stack[-1] if self.savepoint_stack else None
        })

    def rollback_to_savepoint(self, savepoint_id: str):
        """Rollback to a specific savepoint."""
        self.env.cr.execute(f"ROLLBACK TO SAVEPOINT {savepoint_id}")

        # Clear operations after this savepoint
        savepoint_idx = next(
            i for i, sp in enumerate(self.savepoint_stack) if sp == savepoint_id
        )
        self.savepoint_stack = self.savepoint_stack[:savepoint_idx]
        self.operation_log = [
            op for op in self.operation_log
            if op["savepoint"] in self.savepoint_stack
        ]

    def commit(self):
        """Release all savepoints on success."""
        for savepoint_id in reversed(self.savepoint_stack):
            self.env.cr.execute(f"RELEASE SAVEPOINT {savepoint_id}")
        self.savepoint_stack.clear()
```

---

### 5. Skill Definition Format Specification

#### 5.1 JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Loomworks Skill Definition",
  "type": "object",
  "required": ["name", "version", "description", "triggers", "workflow"],
  "properties": {
    "name": {
      "type": "string",
      "pattern": "^[a-z][a-z0-9-]*$",
      "description": "Technical name in kebab-case"
    },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$"
    },
    "display_name": {
      "type": "string"
    },
    "description": {
      "type": "string",
      "minLength": 20,
      "description": "Detailed description for intent matching"
    },
    "category": {
      "type": "string",
      "enum": ["sales", "purchase", "inventory", "accounting", "hr", "manufacturing", "custom"]
    },
    "triggers": {
      "type": "array",
      "items": { "type": "string" },
      "minItems": 3,
      "description": "Natural language trigger phrases with optional {placeholders}"
    },
    "tools": {
      "type": "array",
      "items": { "type": "string" },
      "description": "MCP tool names this skill can invoke"
    },
    "context": {
      "type": "object",
      "additionalProperties": {
        "$ref": "#/$defs/contextVariable"
      }
    },
    "workflow": {
      "type": "object",
      "required": ["steps"],
      "properties": {
        "steps": {
          "type": "array",
          "items": { "$ref": "#/$defs/workflowStep" }
        },
        "error_handling": {
          "$ref": "#/$defs/errorHandling"
        }
      }
    },
    "metadata": {
      "type": "object",
      "properties": {
        "author": { "type": "string" },
        "license": { "type": "string" },
        "tags": { "type": "array", "items": { "type": "string" } },
        "requires_modules": { "type": "array", "items": { "type": "string" } }
      }
    }
  },
  "$defs": {
    "contextVariable": {
      "type": "object",
      "required": ["type"],
      "properties": {
        "type": { "type": "string", "enum": ["string", "number", "boolean", "array", "object", "date"] },
        "required": { "type": "boolean", "default": false },
        "description": { "type": "string" },
        "odoo_model": { "type": "string" },
        "odoo_field": { "type": "string" },
        "extraction_hints": { "type": "array", "items": { "type": "string" } },
        "extraction_patterns": { "type": "array", "items": { "type": "string" } },
        "default": {},
        "enum": { "type": "array" }
      }
    },
    "workflowStep": {
      "type": "object",
      "required": ["id", "type", "name"],
      "properties": {
        "id": { "type": "string" },
        "type": { "type": "string", "enum": ["tool_call", "user_input", "condition", "loop", "subskill", "validation", "confirmation"] },
        "name": { "type": "string" },
        "tool": { "type": "string" },
        "parameters": { "type": "object" },
        "condition": { "type": "string" },
        "on_success": { "type": "string" },
        "on_failure": { "type": "string" },
        "output_var": { "type": "string" },
        "critical": { "type": "boolean", "default": true },
        "retry": { "type": "integer", "default": 0 }
      }
    },
    "errorHandling": {
      "type": "object",
      "properties": {
        "on_tool_failure": { "type": "string", "enum": ["retry", "skip", "abort", "ask_user"] },
        "rollback_on_failure": { "type": "boolean", "default": true },
        "max_retries": { "type": "integer", "default": 3 },
        "fallback_skill": { "type": "string" }
      }
    }
  }
}
```

#### 5.2 YAML Example

```yaml
name: create-sales-quote
version: 1.0.0
display_name: Create Sales Quote
description: |
  Creates a sales quotation for a customer with specified products.
  Handles customer lookup, product validation, and pricing calculation.
category: sales

triggers:
  - "create a quote for {customer}"
  - "make a quotation for {customer}"
  - "prepare quote with {products}"
  - "new sales quote"
  - "quote {quantity} {product} for {customer}"

tools:
  - search_records
  - create_record
  - update_record
  - get_product_price

context:
  customer_name:
    type: string
    required: true
    description: Customer or company name
    odoo_model: res.partner
    odoo_field: name
    extraction_hints: ["for", "to", "customer", "client"]

  products:
    type: array
    items:
      type: object
      properties:
        name: { type: string }
        quantity: { type: number, default: 1 }
    extraction_hints: ["product", "item", "of"]

  delivery_date:
    type: date
    description: Requested delivery date
    extraction_hints: ["by", "before", "deliver", "ship"]

  discount_percent:
    type: number
    default: 0
    extraction_hints: ["discount", "off", "reduction"]

workflow:
  steps:
    - id: find_customer
      type: tool_call
      name: Find Customer
      tool: search_records
      parameters:
        model: res.partner
        domain: "[['name', 'ilike', '{customer_name}']]"
        limit: 5
      output_var: customers
      critical: true

    - id: select_customer
      type: condition
      name: Select Customer
      condition: "len(customers) == 1"
      on_success: validate_products
      on_failure: clarify_customer

    - id: clarify_customer
      type: user_input
      name: Clarify Customer
      prompt: "Found multiple customers: {customers}. Which one?"
      output_var: selected_customer

    - id: validate_products
      type: loop
      name: Validate Products
      over: products
      steps:
        - id: find_product
          type: tool_call
          tool: search_records
          parameters:
            model: product.product
            domain: "[['name', 'ilike', '{item.name}']]"

    - id: create_order
      type: tool_call
      name: Create Sales Order
      tool: create_record
      parameters:
        model: sale.order
        values:
          partner_id: "{selected_customer.id}"
          date_order: "{now()}"
          commitment_date: "{delivery_date}"
      output_var: order

    - id: confirm
      type: confirmation
      name: Confirm Quote
      message: |
        Created quote {order.name} for {selected_customer.name}
        Total: {order.amount_total}

        Proceed?

  error_handling:
    on_tool_failure: ask_user
    rollback_on_failure: true
    max_retries: 2

metadata:
  author: Loomworks
  license: LGPL-3.0
  tags: [sales, quote, customer]
  requires_modules: [sale]
```

---

### 6. Skills Marketplace (Future Capability)

#### 6.1 Architecture Overview

```
loomworks.app/marketplace/
├── /skills                    # Browse skills
├── /skills/{id}               # Skill detail page
├── /skills/{id}/install       # Installation flow
├── /publishers/{id}           # Publisher profile
├── /my/skills                  # Manage installed skills
└── /my/published              # Manage published skills
```

#### 6.2 Skill Package Distribution

```python
class SkillPackage:
    """Manages skill packaging for marketplace distribution."""

    def export(self, skill: LoomworksSkill) -> bytes:
        """Export skill as distributable package."""
        package = {
            "manifest": {
                "name": skill.technical_name,
                "version": skill.version,
                "loomworks_version": ">=1.0.0",
                "checksum": None,  # Computed after packaging
            },
            "skill": skill.to_skill_md(),
            "scripts": self._collect_scripts(skill),
            "templates": self._collect_templates(skill),
            "tests": self._collect_tests(skill),
        }

        # Create signed archive
        archive = self._create_archive(package)
        package["manifest"]["checksum"] = hashlib.sha256(archive).hexdigest()

        return self._sign_package(archive)

    def install(self, package_data: bytes, validate: bool = True) -> LoomworksSkill:
        """Install skill from package."""
        # Verify signature
        if not self._verify_signature(package_data):
            raise SecurityError("Invalid package signature")

        # Extract and validate
        package = self._extract_archive(package_data)
        if validate:
            self._validate_package(package)

        # Create skill record
        return self._create_skill_from_package(package)
```

#### 6.3 Marketplace API

```python
class MarketplaceAPI:
    """API for skill marketplace operations."""

    def search_skills(self, query: str, filters: dict) -> list:
        """Search marketplace for skills."""
        pass

    def get_skill_details(self, skill_id: str) -> dict:
        """Get detailed skill information."""
        pass

    def install_skill(self, skill_id: str, company_id: int) -> LoomworksSkill:
        """Install skill from marketplace."""
        pass

    def publish_skill(self, skill: LoomworksSkill, pricing: dict) -> str:
        """Publish skill to marketplace."""
        pass

    def report_skill(self, skill_id: str, reason: str):
        """Report problematic skill."""
        pass
```

---

## Implementation Steps

### Phase 6.1: Core Engine (Weeks 47-48)

1. **Data Models** (Week 47)
   - [ ] Create `loomworks.skill` model
   - [ ] Create `loomworks.skill.step` model
   - [ ] Create `loomworks.skill.execution` model
   - [ ] Create `loomworks.ai.tool` model (if not exists)
   - [ ] Add security rules and access rights

2. **Intent Matching** (Week 47-48)
   - [ ] Implement `IntentMatcher` class
   - [ ] Add fuzzy string matching (Levenshtein)
   - [ ] Add semantic similarity scoring
   - [ ] Implement parameter extraction

3. **Execution Engine** (Week 48)
   - [ ] Implement `SkillExecutionEngine`
   - [ ] Implement `StepExecutor`
   - [ ] Implement `RollbackManager`
   - [ ] Add execution logging

### Phase 6.2: Built-in Skills (Weeks 49-50)

4. **Core Skills** (Week 49)
   - [ ] Create Quote skill
   - [ ] Check Inventory skill
   - [ ] Generate Invoice skill
   - [ ] Approve PO skill
   - [ ] Create Customer skill

5. **Additional Skills** (Week 50)
   - [ ] Process Return skill
   - [ ] Generate Report skill
   - [ ] Schedule Appointment skill
   - [ ] Update Product Price skill
   - [ ] Create Purchase Order skill

### Phase 6.3: Creation Agent (Weeks 51-52)

6. **Skill Creation Tools** (Week 51)
   - [ ] Natural language skill wizard
   - [ ] Session recording framework
   - [ ] Session-to-skill converter
   - [ ] Skill validation engine

7. **Management UI** (Week 52)
   - [ ] Skills list view
   - [ ] Skill editor (form view)
   - [ ] Step designer (visual workflow)
   - [ ] Testing interface
   - [ ] Export/import functionality

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
| Memory per active skill | <10MB |

### Test Cases

```python
class TestSkillFramework(TransactionCase):

    def test_intent_matching_exact(self):
        """Test exact trigger phrase matching."""
        skill = self._create_test_skill(triggers=["create a quote for"])
        result = self.matcher.match_skill("create a quote for Acme Corp", [skill])
        self.assertEqual(result[0], skill)
        self.assertGreater(result[1], 0.9)

    def test_intent_matching_fuzzy(self):
        """Test fuzzy matching with typos."""
        skill = self._create_test_skill(triggers=["create a quote for"])
        result = self.matcher.match_skill("creat a qoute for Acme", [skill])
        self.assertIsNotNone(result[0])
        self.assertGreater(result[1], 0.75)

    def test_parameter_extraction(self):
        """Test parameter extraction from natural language."""
        params = self.extractor.extract(
            "create a quote for Acme Corp for 10 widgets",
            self._get_quote_schema()
        )
        self.assertEqual(params["customer_name"], "Acme Corp")
        self.assertEqual(params["products"][0]["quantity"], 10)

    def test_workflow_execution(self):
        """Test complete workflow execution."""
        skill = self.env.ref("loomworks_skills.skill_create_quote")
        result = self.engine.execute_skill(skill, {
            "customer_name": "Test Customer",
            "products": [{"name": "Test Product", "quantity": 5}]
        })
        self.assertEqual(result.state, "completed")
        self.assertTrue(result.created_records)

    def test_rollback_on_failure(self):
        """Test rollback when step fails."""
        # Force failure in middle of workflow
        with self.assertRaises(SkillExecutionError):
            self.engine.execute_skill(self.failing_skill, {})

        # Verify no records created
        self.assertEqual(
            self.env["sale.order"].search_count([("origin", "=", "skill_test")]),
            0
        )
```

---

## Security Considerations

### Skill Execution Sandboxing

1. **Tool Restrictions**: Skills can only use explicitly bound tools
2. **Model Access**: Enforce user permissions for all operations
3. **Rate Limiting**: Limit skill executions per user/minute
4. **Audit Logging**: Log all skill executions and operations

### Marketplace Security

1. **Code Review**: All marketplace skills undergo security review
2. **Signature Verification**: Packages must be signed by verified publishers
3. **Permission Disclosure**: Skills must declare all required permissions
4. **Sandboxed Testing**: Test skills in isolated environment before installation

---

## Dependencies

### Python Packages

```
rapidfuzz>=3.0.0          # Fuzzy string matching
sentence-transformers     # Semantic similarity (optional, for embedding-based matching)
jsonschema>=4.0.0         # Schema validation
pyyaml>=6.0               # YAML parsing
```

### Odoo Modules

- `loomworks_ai` (required) - AI agent integration
- `loomworks_snapshot` (required) - Rollback support
- `sale` (optional) - For sales-related skills
- `purchase` (optional) - For purchasing skills
- `stock` (optional) - For inventory skills
- `account` (optional) - For accounting skills

---

## References

### Research Sources

- [Anthropic Engineering: Equipping Agents for the Real World with Agent Skills](https://claude.com/blog/equipping-agents-for-the-real-world-with-agent-skills)
- [Claude Agent SDK Documentation](https://platform.claude.com/docs/en/agent-sdk/skills)
- [Fuzzy String Matching Techniques](https://www.datacamp.com/tutorial/fuzzy-string-python)
- [Natural Language Understanding for Enterprise Workflows](https://skillup.ccccloud.com/2025/07/03/introduction-to-natural-language-understanding-nlu-for-enterprise-workflows/)
- [Session Recording and Replay for Workflow Capture](https://developer.chrome.com/docs/devtools/recorder)
- [ERP Workflow Automation Patterns 2025](https://erp.today/how-deloitte-and-servicenows-2025-workflow-automation-outlook-guides-erp-users/)

### Related Specifications

- Phase 2: AI Integration Layer (`loomworks_ai`)
- Phase 5: Hosting Infrastructure (`loomworks_snapshot`)
- Odoo 18 Developer Documentation
