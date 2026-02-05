# Loomworks ERP - Implementation Plan

## Executive Summary

Build an AI-first open-source ERP based on Odoo Community v18 (LGPL v3). Users interact primarily with Claude AI agents rather than traditional forms. The system includes database snapshots for AI rollback, interactive React dashboards, and a skills framework for workflow automation.

**Market Differentiator**: Free software + hosted databases + AI does all the work (eliminates developer labor cost).

---

## Licensing Strategy

| Component | License | What's Allowed |
|-----------|---------|----------------|
| Odoo Community v18 | LGPL v3 | Fork and modify, must stay LGPL |
| Odoo Enterprise | Proprietary | **Cannot copy code**, but can recreate features from scratch |
| Loomworks Modules | LGPL v3 | Our open-source additions |

**Critical**: All enterprise-equivalent features must be independently developed - no code copying from `/home/loomworks/Desktop/OdooTestLauncher` enterprise modules. Use them only as **feature reference**.

Sources:
- [Odoo Licenses Documentation](https://www.odoo.com/documentation/18.0/legal/licenses.html)
- [LGPL Forum Discussion](https://www.odoo.com/forum/help-1/can-i-use-odoo-enterprise-modules-licensed-under-lgplv3-in-odoo-community-185628)

---

## Business Model: Open-Core

| Tier | Features | Price |
|------|----------|-------|
| **Community (Self-Hosted)** | Core ERP + AI integration + Studio + Spreadsheets | Free (LGPL) |
| **Hosted Basic** | Managed database + automatic backups + basic support | $49/mo |
| **Hosted Pro** | + AI snapshots/rollback + priority support + advanced skills | $149/mo |
| **Enterprise** | + SLA + custom integrations + dedicated resources | Custom |

**Revenue Strategy**:
- Core software is 100% open source (LGPL)
- Revenue from hosted database services + premium support
- AI compute costs covered by subscription tiers
- Advanced AI features (complex skills, higher usage) in paid tiers

---

## Phase 1: Foundation (Weeks 1-4)

### 1.1 Fork Odoo Community v18

```bash
# Clone official community repo
git clone --branch 18.0 --depth 1 https://github.com/odoo/odoo.git /home/loomworks/Desktop/LoomworksERP/odoo

# Initialize project structure
mkdir -p /home/loomworks/Desktop/LoomworksERP/{loomworks_addons,infrastructure,docs}
```

### 1.2 Directory Structure

```
/home/loomworks/Desktop/LoomworksERP/
├── odoo/                          # Forked Odoo core (LGPL v3)
│   ├── odoo/                      # Core framework
│   └── addons/                    # Community addons
├── loomworks_addons/              # Custom modules (LGPL v3)
│   ├── loomworks_core/            # Branding, base config
│   ├── loomworks_ai/              # Claude integration
│   ├── loomworks_studio/          # No-code builder
│   ├── loomworks_payroll/         # Payroll system
│   ├── loomworks_plm/             # Product lifecycle
│   ├── loomworks_sign/            # E-signatures
│   ├── loomworks_spreadsheet/     # BI dashboards
│   ├── loomworks_appointment/     # Booking system
│   ├── loomworks_fsm/             # Field service
│   ├── loomworks_dashboard/       # React canvas
│   └── loomworks_snapshot/        # PITR rollback
├── infrastructure/
│   ├── docker/
│   └── kubernetes/
└── openspec/                       # Spec-driven development
```

### 1.3 Branding Module (`loomworks_core`)

**Files to create**:
- `loomworks_addons/loomworks_core/__manifest__.py`
- `loomworks_addons/loomworks_core/static/src/scss/loomworks_theme.scss`
- `loomworks_addons/loomworks_core/views/webclient_templates.xml`

**Key changes**:
- Replace Odoo logos in `web/static/src/`
- Update `base` module company defaults
- Custom color scheme and branding

---

## Phase 2: AI Integration Layer (Weeks 5-10)

### 2.1 Claude Agent SDK Integration

**Module**: `loomworks_addons/loomworks_ai/`

**Core Components**:

| File | Purpose |
|------|---------|
| `models/ai_agent.py` | Agent configuration model |
| `models/ai_session.py` | Chat session tracking |
| `models/ai_tool.py` | Tool definitions |
| `services/odoo_mcp_server.py` | MCP server for Odoo operations |
| `controllers/ai_controller.py` | HTTP endpoints for chat |
| `static/src/components/ai_chat/` | Owl chat interface |

**MCP Tools to Implement**:
```python
# Tools the AI can use to interact with Odoo
@tool("search_records")    # Query any model
@tool("create_record")     # Create records
@tool("update_record")     # Modify records
@tool("delete_record")     # Remove records
@tool("execute_action")    # Run workflows/actions
@tool("generate_report")   # Create reports
@tool("get_dashboard")     # Fetch dashboard data
```

**Reference**: [Claude Agent SDK Documentation](https://platform.claude.com/docs/en/agent-sdk/overview)

### 2.2 Security Sandbox

```python
# Restricted models AI cannot access
SENSITIVE_MODELS = ['res.users', 'ir.config_parameter', 'ir.rule']

# Savepoint-based rollback for each AI operation
with AIOperationSandbox(tenant_id, user_id) as sandbox:
    # Execute AI operations
    # Auto-rollback on error
```

---

## Phase 3: Enterprise Module Alternatives (Weeks 11-30)

### Priority Tier 1 - CRITICAL (Weeks 11-20)

These are the **highest priority** modules that enable the AI-first, no-developer vision:

| Module | Enterprise Equivalent | Key Features | Why Priority |
|--------|----------------------|---------------|--------------|
| `loomworks_studio` | `web_studio` | Visual app builder, field creation, view customization | **Enables users to customize without developers** |
| `loomworks_spreadsheet` | `spreadsheet` + dashboards | Excel-like interface, pivot tables, charts | **Universal BI need, works with AI dashboards** |

### Priority Tier 2 (Weeks 21-26)

| Module | Enterprise Equivalent | Key Features |
|--------|----------------------|---------------|
| `loomworks_plm` | `mrp_plm` | Engineering Change Orders, BOM versioning |
| `loomworks_sign` | `sign` | E-signature requests, document signing |
| `loomworks_appointment` | `appointment` | Online booking, calendar sync |

### Priority Tier 3 (Weeks 27-30)

| Module | Enterprise Equivalent | Key Features |
|--------|----------------------|---------------|
| `loomworks_payroll` | `hr_payroll` | Salary rules, payslips (start with 1 locale) |
| `loomworks_fsm` | `industry_fsm` | Field service tasks, mobile worksheets |
| `loomworks_planning` | `planning` | Workforce scheduling, Gantt views |

### Module Development Pattern

Each module follows this structure (based on existing `loomworks_operator_light`):

```
loomworks_[module]/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── [model].py
├── views/
│   └── [model]_views.xml
├── security/
│   ├── ir.model.access.csv
│   └── security.xml
├── data/
│   └── [data].xml
├── static/src/
│   ├── js/
│   ├── scss/
│   └── xml/
└── tests/
```

---

## Phase 4: Dashboard System (Weeks 31-38)

### 4.1 Technology Stack

| Library | Purpose | Source |
|---------|---------|--------|
| [React Flow](https://reactflow.dev) | Node-based canvas, drag-drop | Interactive dashboard builder |
| [Gridstack.js](https://gridstackjs.com/) | Resizable grid layouts | Dashboard widget positioning |
| [Tremor](https://www.tremor.so/) | Chart components | KPIs, graphs, tables |
| [Recharts](https://recharts.org/) | Data visualization | Line/bar/pie charts |

### 4.2 Architecture

```
Owl Component (LoomworksDashboard)
    └── React Bridge (createRoot)
        └── ReactFlowProvider
            └── DashboardCanvas
                ├── ChartNode (Tremor/Recharts)
                ├── KPINode
                ├── TableNode
                └── FilterNode
```

### 4.3 Key Files

- `loomworks_dashboard/static/src/dashboard/DashboardCanvas.jsx` - Main React canvas
- `loomworks_dashboard/static/src/dashboard/nodes/` - Custom node components
- `loomworks_dashboard/static/src/components/react_dashboard.js` - Owl-React bridge
- `loomworks_dashboard/models/dashboard.py` - Dashboard storage model

### 4.4 Features

- Drag-drop widget placement
- Real-time data connections to Odoo models
- AI-generated dashboards from natural language
- Tabbed dashboard organization
- Export/share capabilities

---

## Phase 5: Hosting Infrastructure (Weeks 39-46)

### 5.1 Multi-Tenant Architecture

```python
class LoomworksTenant(models.Model):
    _name = "loomworks.tenant"

    name = fields.Char()
    database_name = fields.Char()
    subdomain = fields.Char()  # tenant.loomworks.app

    # Resource limits
    max_users = fields.Integer(default=10)
    max_storage_gb = fields.Float(default=5.0)

    # Snapshot management
    snapshot_ids = fields.One2many("loomworks.snapshot", "tenant_id")
```

### 5.2 PostgreSQL PITR Snapshots

**Strategy**: Use WAL archiving for point-in-time recovery

```yaml
# docker-compose.yml - PostgreSQL config
db:
  image: postgres:15
  command: >
    postgres
    -c wal_level=replica
    -c archive_mode=on
    -c archive_command='cp %p /wal_archive/%f'
```

**Snapshot Model**:
```python
class LoomworksSnapshot(models.Model):
    _name = "loomworks.snapshot"

    tenant_id = fields.Many2one("loomworks.tenant")
    created_at = fields.Datetime()
    wal_position = fields.Char()  # LSN for PITR
    snapshot_type = fields.Selection([
        ('auto', 'Automatic'),
        ('manual', 'Manual'),
        ('pre_ai', 'Pre-AI Operation'),  # Created before AI makes changes
    ])
```

**Source**: [PostgreSQL PITR Documentation](https://www.postgresql.org/docs/current/continuous-archiving.html)

### 5.3 AI Rollback Mechanism

1. Before AI operation → Create snapshot (or savepoint for smaller ops)
2. AI executes operations → Log all changes to `ai.operation.log`
3. On error/user request → Restore to snapshot OR undo specific operations

```python
class AIOperationLog(models.Model):
    _name = "ai.operation.log"

    session_id = fields.Many2one("loomworks.ai.session")
    operation_type = fields.Selection([('create','Create'),('write','Update'),('unlink','Delete')])
    model = fields.Char()
    record_ids = fields.Char()  # JSON
    values_before = fields.Text()  # JSON - for undo
    values_after = fields.Text()   # JSON
    snapshot_id = fields.Many2one("loomworks.snapshot")
```

### 5.4 Docker/Kubernetes Setup

```
infrastructure/
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .env.example
├── kubernetes/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   └── pvc.yaml
└── terraform/
    └── main.tf
```

---

## Phase 6: Skills Framework (Weeks 47-52)

### 6.1 Skills Architecture

Based on [Claude Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills):

```python
class LoomworksSkill(models.Model):
    _name = "loomworks.skill"

    name = fields.Char()
    technical_name = fields.Char()  # e.g., "create-purchase-order"
    description = fields.Text()
    trigger_phrases = fields.Text()  # JSON list

    # Skill definition
    system_prompt = fields.Text()
    tool_ids = fields.Many2many("loomworks.ai.tool")
    step_ids = fields.One2many("loomworks.skill.step", "skill_id")
```

### 6.2 Skills Creation Agent

Allow users to:
1. Describe a workflow in natural language
2. AI analyzes and creates skill structure
3. Record user sessions → Convert to reusable skills
4. Export skills as shareable packages

### 6.3 Built-in Skills Examples

| Skill | Trigger | Actions |
|-------|---------|---------|
| Create Quote | "make a quote for..." | Search customer → Create SO → Add lines |
| Check Inventory | "do we have..." | Search products → Check stock → Report |
| Generate Invoice | "bill the customer..." | Find SO → Create invoice → Confirm |
| Approve PO | "approve purchase..." | Find PO → Validate → Confirm |

---

## Verification Plan

### Unit Tests
- Each module has `tests/` directory
- Run: `python -m pytest loomworks_addons/*/tests/`

### Integration Tests
- AI agent can complete end-to-end workflows
- Snapshot/restore works correctly
- Multi-tenant isolation verified

### Manual Testing
1. Start fresh Odoo instance with Loomworks modules
2. Create tenant, configure AI agent
3. Chat with AI to perform business operations
4. Trigger snapshot, make changes, restore
5. Build dashboard with React canvas
6. Create custom skill from workflow

### Performance Benchmarks
- AI response time < 3 seconds
- Snapshot creation < 30 seconds
- Dashboard render < 1 second

---

## Critical Files to Create

| Priority | File | Purpose |
|----------|------|---------|
| 1 | `loomworks_ai/models/ai_agent.py` | Core AI agent configuration |
| 1 | `loomworks_ai/services/odoo_mcp_server.py` | MCP tools for Odoo |
| 1 | `loomworks_core/__manifest__.py` | Branding module |
| 1 | `loomworks_studio/models/studio_app.py` | **No-code app builder (TOP PRIORITY)** |
| 1 | `loomworks_spreadsheet/models/spreadsheet.py` | **BI dashboards (TOP PRIORITY)** |
| 2 | `loomworks_snapshot/models/snapshot.py` | PITR snapshot management |
| 2 | `loomworks_dashboard/static/src/dashboard/` | React canvas |
| 3 | `loomworks_plm/models/plm_eco.py` | Engineering Change Orders |
| 3 | `loomworks_sign/models/sign_request.py` | E-signature workflows |

---

## Dependencies

```
# Python (requirements.txt)
odoo==18.0
claude-agent-sdk>=1.0.0
psycopg2-binary>=2.9
redis>=4.0

# Node.js (package.json for dashboard)
@xyflow/react
react
react-dom
recharts
@tremor/react
gridstack
```

---

## Timeline Summary

| Phase | Weeks | Deliverables |
|-------|-------|--------------|
| 1. Foundation | 1-4 | Forked codebase, branding, project structure |
| 2. AI Integration | 5-10 | Claude SDK, MCP server, chat interface |
| 3. Enterprise Modules | 11-30 | PLM, Studio, Payroll, Sign, Spreadsheet, FSM |
| 4. Dashboard | 31-38 | React canvas, drag-drop builder, charts |
| 5. Infrastructure | 39-46 | Multi-tenant, snapshots, Docker/K8s |
| 6. Skills | 47-52 | Skills framework, creation agent |

**Total: ~52 weeks (1 year) for full implementation**

---

## Next Steps

1. Initialize Git repository with proper `.gitignore`
2. Fork Odoo Community v18
3. Create `loomworks_core` branding module
4. Set up development Docker environment
5. Begin `loomworks_ai` module with basic MCP server
