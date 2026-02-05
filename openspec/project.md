# Project Context

## Purpose

**Loomworks ERP** is an AI-first open-source ERP system based on Odoo Community v18 (LGPL v3). The core differentiator is that users interact primarily with Claude AI agents rather than traditional forms and menus.

**Key Goals**:
- Eliminate the need for developer labor by having AI perform all ERP operations
- Provide free open-source software with revenue from hosted database services
- Include database snapshots for AI rollback (undo mistakes)
- Offer interactive React dashboards for business intelligence
- Implement a skills framework for workflow automation

**Market Positioning**: Free software + hosted databases + AI does all the work

## Tech Stack

### Backend
- **Odoo Community v18** - Core ERP framework (LGPL v3)
- **Python 3.10+** - Primary backend language
- **PostgreSQL 15+** - Database with WAL archiving for PITR snapshots
- **Redis** - Session caching and message queue

### AI Integration
- **Claude Agent SDK** - AI agent orchestration
- **MCP (Model Context Protocol)** - Tool interface for Odoo operations

### Frontend
- **Owl.js** - Odoo's reactive component framework (Odoo-native)
- **React 18+** - Dashboard canvas (via Owl bridge)
- **React Flow** - Node-based drag-drop dashboard builder
- **Tremor / Recharts** - Chart and KPI components
- **Gridstack.js** - Resizable widget layouts

### Infrastructure
- **Docker** - Containerized deployment
- **Kubernetes** - Production orchestration
- **Terraform** - Infrastructure as code

## Project Conventions

### Code Style

**Python (Odoo modules)**:
- Follow [Odoo Coding Guidelines](https://www.odoo.com/documentation/18.0/contributing/development/coding_guidelines.html)
- PEP 8 with 120 character line limit
- Use `_` prefix for private methods
- Model names: `loomworks.model.name` (lowercase, dot-separated)
- Technical names: `loomworks_module_name` (lowercase, underscore-separated)

**JavaScript (Owl/React)**:
- ES6+ syntax
- Owl components in `static/src/components/`
- React components in `static/src/dashboard/`
- Use JSX for React, XML templates for Owl

**XML (Views/Data)**:
- 4-space indentation
- View IDs: `loomworks_model_view_type` (e.g., `loomworks_ai_session_tree`)
- Action IDs: `action_loomworks_model`

### Architecture Patterns

**Module Structure**:
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

**AI Operation Pattern**:
1. Create savepoint/snapshot before operation
2. Execute AI operations with full logging
3. On error: auto-rollback to savepoint
4. On success: commit and record operation log

**Owl-React Bridge**:
- Owl component wraps React via `createRoot`
- Data flows: Odoo → Owl → React props
- Events flow: React callbacks → Owl → RPC to Python

### Testing Strategy

**Unit Tests**:
- Python: `tests/` directory in each module using Odoo's `TransactionCase`
- Run: `python -m pytest loomworks_addons/*/tests/`

**Integration Tests**:
- AI agent end-to-end workflow tests
- Snapshot/restore verification
- Multi-tenant isolation tests

**Performance Benchmarks**:
- AI response time < 3 seconds
- Snapshot creation < 30 seconds
- Dashboard render < 1 second

### Git Workflow

**Branching Strategy**:
- `main` - Stable release branch
- `develop` - Integration branch
- `feature/[name]` - New features
- `fix/[name]` - Bug fixes
- `module/[name]` - New Loomworks module development

**Commit Convention**:
```
[module] type: description

Types: feat, fix, refactor, docs, test, chore
Example: [loomworks_ai] feat: add MCP search_records tool
```

## Domain Context

**ERP Terminology**:
- **SO** - Sales Order
- **PO** - Purchase Order
- **BOM** - Bill of Materials
- **ECO** - Engineering Change Order (PLM)
- **PITR** - Point-in-Time Recovery (database snapshots)
- **MCP** - Model Context Protocol (AI tool interface)

**Odoo-Specific Concepts**:
- **Models** - Python classes that map to database tables
- **Views** - XML definitions for UI (form, tree, kanban, etc.)
- **Actions** - UI navigation and workflow triggers
- **Security Rules** - Record-level access control (`ir.rule`)
- **Access Rights** - Model-level permissions (`ir.model.access`)

**AI Agent Concepts**:
- **Skills** - Reusable workflow templates triggered by natural language
- **Tools** - Functions the AI can call (search, create, update, delete)
- **Sessions** - Conversation context with operation history
- **Sandbox** - Isolated execution environment with rollback capability

## Important Constraints

### Legal/Licensing
- **CRITICAL**: All code must be LGPL v3 compatible
- **NO CODE COPYING** from Odoo Enterprise modules
- Enterprise features must be independently developed (use as feature reference only)
- Enterprise source at `/home/loomworks/Desktop/OdooTestLauncher` is for reference only

### Security
- AI cannot access sensitive models: `res.users`, `ir.config_parameter`, `ir.rule`
- All AI operations must be logged to `ai.operation.log`
- Multi-tenant isolation required for hosted deployments
- User permissions must be enforced even for AI operations

### Technical
- Must maintain compatibility with Odoo Community v18 core
- React components must not break Odoo's asset bundling
- Database migrations must support PITR snapshots

## External Dependencies

### APIs/Services
- **Claude API** - AI agent (via Claude Agent SDK)
- **PostgreSQL** - Primary database with WAL archiving

### Runtime Environment Requirements

| Component | Version | Required For | Notes |
|-----------|---------|--------------|-------|
| **Python** | >= 3.10 | Odoo v18 | Core backend runtime |
| **PostgreSQL** | >= 15 | Database | WAL archiving for PITR snapshots |
| **Node.js** | >= 20.0.0 (LTS) | Frontend builds | Dashboard (React), Spreadsheet (Univer) |
| **npm** | >= 9.0.0 | Package management | Node.js package manager |
| **Redis** | >= 7.0 | Caching | Session cache and message queue |

**Node.js Version Policy:**
- **Minimum**: Node.js 20.0.0 LTS
- **Recommended**: Node.js 20 LTS (Active LTS until October 2024, Maintenance until April 2026)
- **Supported**: Node.js 22 LTS (Current LTS)
- **Rationale**:
  - Univer spreadsheet library requires >= 18.17.0
  - Node.js 18 LTS reached EOL on April 30, 2025
  - Node.js 20 LTS provides security updates through April 2026
  - Modern ES module support required for React 18+ and Odoo asset bundling

### Key Python Packages
```
odoo==18.0
claude-agent-sdk>=1.0.0
psycopg2-binary>=2.9
redis>=4.0
```

### Key Node.js Packages (Dashboard/Spreadsheet)
```
# Dashboard (Phase 4)
@xyflow/react
react@18
react-dom@18
recharts
@tremor/react
gridstack

# Spreadsheet (Phase 3.1)
@univerjs/core
@univerjs/sheets
@univerjs/sheets-ui
@univerjs/engine-render
```

### Reference Documentation
- [Odoo 18 Developer Docs](https://www.odoo.com/documentation/18.0/developer.html)
- [Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview)
- [PostgreSQL PITR](https://www.postgresql.org/docs/current/continuous-archiving.html)
- [React Flow](https://reactflow.dev)
- [Tremor](https://www.tremor.so/)
