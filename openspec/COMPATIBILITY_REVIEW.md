# Loomworks ERP - OpenSpec Compatibility Review

**Review Date**: 2026-02-05
**Reviewer**: Automated Compatibility Analysis
**Scope**: All 8 Phases (Foundation through Skills Framework)
**Total Project Duration**: 52 Weeks

---

## 1. Executive Summary

### Overall Assessment: APPROVED WITH RECOMMENDATIONS

The Loomworks ERP OpenSpec proposals demonstrate a **well-architected, coherent system design** with proper phase dependencies and consistent technical patterns. The proposals collectively define a comprehensive AI-first ERP system built on Odoo Community v18.

**Strengths:**
- Clear phase dependencies with logical progression
- Consistent model naming conventions (`loomworks.*` namespace)
- Unified security model across all modules
- Proper LGPL v3 compliance strategy throughout
- Well-defined integration points between AI layer and business modules
- Comprehensive audit logging patterns

**Areas Requiring Attention:**
- Several cross-phase model references need explicit dependency declarations
- AI integration tools need to be extended for Phase 3 enterprise modules
- Snapshot system integration with AI rollback needs more explicit connection
- Dashboard data sources should explicitly support Phase 3 modules

**Critical Path Dependencies:**
```
Phase 1 (Foundation) --> Phase 2 (AI Integration) --> Phase 3 (Enterprise Modules)
                                |                           |
                                v                           v
                    Phase 4 (Dashboard) <------------- Phase 5 (Infrastructure)
                                |
                                v
                        Phase 6 (Skills Framework)
```

---

## 2. Dependency Matrix

### 2.1 Phase Dependencies

| Phase | Depends On | Blocks |
|-------|------------|--------|
| **Phase 1: Foundation** | Odoo v18 only | Phase 2, 3, 4, 5, 6 |
| **Phase 2: AI Integration** | Phase 1 | Phase 3 (AI tools), Phase 4 (AI generation), Phase 5 (operation logging), Phase 6 |
| **Phase 3.1: Studio/Spreadsheet** | Phase 1 | Phase 4 (data sources) |
| **Phase 3.2: PLM/Sign/Appointment** | Phase 1 | None (parallel with 3.1, 3.3) |
| **Phase 3.3: Payroll/FSM/Planning** | Phase 1 | None (parallel with 3.1, 3.2) |
| **Phase 4: Dashboard** | Phase 1, Phase 2 (optional), Phase 3 (data sources) | None |
| **Phase 5: Infrastructure** | Phase 1, Phase 2 (operation logging) | Phase 6 (execution rollback) |
| **Phase 6: Skills Framework** | Phase 2 (tools), Phase 5 (snapshots) | None |

### 2.2 Module Dependencies

| Module | Required Dependencies | Optional Dependencies |
|--------|----------------------|----------------------|
| `loomworks_core` | `base`, `web`, `mail` | - |
| `loomworks_ai` | `loomworks_core`, `base`, `web` | - |
| `loomworks_studio` | `loomworks_core`, `base`, `web` | `loomworks_ai` |
| `loomworks_spreadsheet` | `loomworks_core`, `base`, `web` | `loomworks_ai`, `documents` |
| `loomworks_plm` | `loomworks_core`, `mrp` | `loomworks_sign` |
| `loomworks_sign` | `loomworks_core`, `mail`, `portal` | - |
| `loomworks_appointment` | `loomworks_core`, `calendar`, `website` | - |
| `loomworks_payroll` | `loomworks_core`, `hr` | `hr_contract` |
| `loomworks_fsm` | `loomworks_core`, `project`, `hr_timesheet` | - |
| `loomworks_planning` | `loomworks_core`, `hr` | `project` |
| `loomworks_dashboard` | `loomworks_core`, `web` | `loomworks_ai`, `loomworks_spreadsheet` |
| `loomworks_tenant` | `loomworks_core` | - |
| `loomworks_snapshot` | `loomworks_tenant`, `loomworks_ai` | - |
| `loomworks_skills` | `loomworks_ai`, `loomworks_snapshot` | All Phase 3 modules |

### 2.3 Model Cross-References

The following models are referenced across multiple proposals:

| Model | Defined In | Extended By | Referenced By |
|-------|------------|-------------|---------------|
| `loomworks.ai.session` | Phase 2 | - | Phase 5 (snapshot), Phase 6 (skills) |
| `loomworks.ai.tool` | Phase 2 | - | Phase 3 (all), Phase 4, Phase 6 |
| `loomworks.ai.operation.log` | **Phase 2** | **Phase 5** (adds snapshot_id) | Phase 6 |
| `loomworks.snapshot` | Phase 5 | - | Phase 2 (rollback), Phase 6 (execution) |
| `loomworks.tenant` | Phase 5 | - | All hosted modules |
| `dashboard.data_source` | Phase 4 | - | Phase 3 (spreadsheet pivot) |
| `loomworks.skill` | Phase 6 | - | Phase 2 (agent binding) |

---

## 3. Integration Points Analysis

### 3.1 AI Integration (Phase 2) with Enterprise Modules (Phase 3)

**Status**: PARTIALLY DEFINED - Needs Extension

The Phase 2 proposal defines base MCP tools:
- `search_records` - Query any model
- `create_record` - Create records
- `update_record` - Modify records
- `delete_record` - Remove records
- `execute_action` - Run workflows/actions
- `generate_report` - Create reports
- `get_dashboard` - Fetch dashboard data

**Gap Identified**: Phase 3 modules define AI agent integration tasks (e.g., `studio_create_app`, `spreadsheet_create_pivot`) but the Phase 2 proposal does not explicitly define extension patterns for module-specific tools.

**Recommendation**: Add an explicit MCP tool extension pattern in Phase 2 design.md that Phase 3 modules must follow:

```python
# Proposed pattern for Phase 3 modules to add AI tools
class Module_AIToolProvider:
    """Mixin for modules providing AI tools."""

    @api.model
    def _register_ai_tools(self):
        """Called during module installation to register tools."""
        pass
```

### 3.2 Snapshot System (Phase 5) with AI Rollback (Phase 2)

**Status**: WELL INTEGRATED (R1 RESOLVED)

The integration is properly designed with clear model ownership:

1. **Phase 2** defines `loomworks.ai.operation.log` as the canonical model for AI audit trail
2. **Phase 2** defines `AIOperationSandbox` with savepoint-based rollback
3. **Phase 5** EXTENDS `loomworks.ai.operation.log` to add `snapshot_id` for PITR integration
4. **Phase 5** depends on `loomworks_ai` module (explicit dependency)
5. **Phase 5** design mentions "Pre-AI Operation Snapshots"

**Connection Points Verified**:
- `loomworks.ai.operation.log.session_id` -> `loomworks.ai.session` (Phase 2)
- `loomworks.ai.operation.log.snapshot_id` -> `loomworks.snapshot` (Phase 5 extension)
- Pre-AI snapshot triggers integrated with session workflow

**RESOLVED**: Phase 2 now owns the `loomworks.ai.operation.log` model. Phase 5's `loomworks_snapshot` module extends it via `_inherit` to add the `snapshot_id` field for PITR integration. The dependency chain is: `loomworks_snapshot` depends on `loomworks_ai`.

### 3.3 Dashboard System (Phase 4) with AI Integration (Phase 2)

**Status**: WELL INTEGRATED

Integration points:
- AI dashboard generation via Claude (defined in Phase 4)
- `dashboard.board.ai_generated` and `dashboard.board.ai_prompt` fields
- AI tools for dashboard operations (implicit)

**Verified**: Phase 4 states optional dependency on `loomworks_ai` with graceful degradation.

### 3.4 Dashboard System (Phase 4) with Spreadsheet (Phase 3.1)

**Status**: COMPLEMENTARY - Minor overlap to address

Both modules provide BI capabilities:
- **Spreadsheet**: Excel-like interface with pivot tables and charts
- **Dashboard**: Drag-drop canvas with KPI cards and real-time updates

**Potential Overlap**: Both can display charts and aggregated data.

**Recommendation**: Clearly differentiate use cases in documentation:
- Spreadsheet = Ad-hoc analysis, data manipulation, Excel replacement
- Dashboard = Real-time monitoring, KPI display, executive views

### 3.5 Studio (Phase 3.1) with Custom Models

**Status**: WELL DESIGNED

Studio's dynamic model creation properly uses Odoo's `ir.model` and `ir.model.fields` APIs with `state='manual'` and `x_` prefix convention. This ensures:
- Studio-created models work with all other modules
- AI tools can operate on Studio-created models
- Dashboard can use Studio models as data sources
- Spreadsheet can query Studio models

### 3.6 Skills Framework (Phase 6) with All Modules

**Status**: PROPERLY ARCHITECTED

Phase 6 correctly depends on:
- Phase 2 for `loomworks.ai.tool` bindings
- Phase 5 for execution snapshots and rollback
- Implicitly works with all Phase 3 modules via generic MCP tools

**Integration Verified**:
- `loomworks.skill.tool_ids` -> `loomworks.ai.tool` (Many2many)
- `loomworks.skill.execution.snapshot_id` -> `loomworks.snapshot`
- `loomworks.skill.execution.session_id` -> `loomworks.ai.session`

---

## 4. Technical Consistency Analysis

### 4.1 Odoo Version Compatibility

**Status**: CONSISTENT

All proposals assume Odoo Community v18:
- Phase 1: Explicitly forks v18
- All modules: Use `version: '18.0.x.x.x'` format
- Views use `<list>` (v18) not `<tree>` (deprecated)
- Asset bundles follow v18 patterns

### 4.2 Python/JS Library Versions

**Status**: CONSISTENT with one clarification needed

| Library | Specified Version | Notes |
|---------|------------------|-------|
| Python | 3.10+ | Consistent across all |
| PostgreSQL | 15+ | Required for WAL features |
| Node.js | **20.0.0+ LTS** | **RESOLVED**: Required for dashboard/spreadsheet builds |
| React | 18+ | Phase 4 dashboard |
| Univer | Latest | Phase 3.1 spreadsheet (Apache-2.0), requires Node.js >= 18.17.0 |

**Status**: Node.js version requirement now specified in project.md, Phase 3.1, and Phase 4.

### 4.3 Security Model Consistency

**Status**: CONSISTENT

All modules follow the same security patterns:

1. **Access Control Groups**:
   - `group_*_user` - Basic access
   - `group_*_manager` - Full CRUD
   - `group_*_admin` - System configuration

2. **Sensitive Model Protection**:
   - AI cannot access: `res.users`, `ir.config_parameter`, `ir.rule`, `ir.model.access`
   - Consistent across Phase 2 (AI) and Phase 6 (Skills)

3. **Multi-tenant Isolation**:
   - Database-per-tenant (Phase 5)
   - Subdomain routing via `dbfilter`
   - Record rules for tenant filtering

4. **Audit Logging**:
   - All AI operations logged to `ai.operation.log`
   - Studio changes logged
   - Tenant operations audited

### 4.4 Logging and Audit Patterns

**Status**: CONSISTENT

All proposals reference a common audit pattern:
- Odoo's `mail.thread` for record chatter
- `mail.activity.mixin` for activities
- Custom audit models where needed (`ai.operation.log`, Studio audit)
- `tracking=True` on sensitive fields

---

## 5. Issues Found

### 5.1 Critical Issues

**None identified.** The proposals are architecturally sound.

### 5.2 High Priority Issues

#### Issue H1: Missing Explicit ai.operation.log Definition Location

**Severity**: HIGH (RESOLVED)
**Location**: Phase 2 vs Phase 5

**Description**: Phase 2 (AI Integration) references operation logging but the `ai.operation.log` model was defined in Phase 5 (Infrastructure). This created a circular dependency concern.

**Impact**: If Phase 2 is deployed before Phase 5, operation logging will not work.

**Resolution Applied** (2026-02-05):
- **Phase 2 owns `loomworks.ai.operation.log`**: The canonical model is defined in Phase 2 with full audit trail fields (session_id, operation_type, values_before/after, state, etc.)
- **Phase 5 extends via `_inherit`**: The `loomworks_snapshot` module now uses `_inherit = 'loomworks.ai.operation.log'` to add `snapshot_id` and `undone`/`undone_at` fields
- **Explicit dependency declared**: `loomworks_snapshot` manifest now lists `loomworks_ai` as a required dependency
- **Consistent model naming**: Changed from `ai.operation.log` to `loomworks.ai.operation.log` for namespace consistency

**Status**: RESOLVED - No circular dependency. Clear ownership chain established.

#### Issue H2: Node.js Version Unspecified

**Severity**: HIGH (RESOLVED)
**Location**: Phase 3.1, Phase 4

**Description**: Frontend builds require Node.js but version is not specified.

**Impact**: Build failures or inconsistencies across environments.

**Resolution Applied** (2026-02-05):
- **project.md**: Added comprehensive Runtime Environment Requirements table with Node.js >= 20.0.0 LTS
- **Phase 3.1 design.md**: Added Runtime Requirements section with Node.js >= 20.0.0 and rationale
- **Phase 4 proposal**: Added Runtime Requirements section with Node.js >= 20.0.0 and rationale
- **Version Policy**: Node.js 20 LTS recommended (security support until April 2026), Node.js 22 LTS also supported
- **Rationale documented**: Univer requires >= 18.17.0, Node.js 18 EOL was April 2025

**Status**: RESOLVED - Consistent Node.js >= 20.0.0 requirement across all proposals.

### 5.3 Medium Priority Issues

#### Issue M1: AI Tool Registration Pattern Undefined

**Severity**: MEDIUM
**Location**: Phase 2, Phase 3 modules

**Description**: Phase 3 modules define AI tools (e.g., `studio_create_app`) but no standard registration pattern exists.

**Impact**: Inconsistent tool implementation across modules.

**Recommendation**: Add to Phase 2 design.md a `ToolProvider` mixin pattern that Phase 3 modules inherit.

#### Issue M2: Dashboard Data Source Support for Phase 3 Modules

**Severity**: MEDIUM
**Location**: Phase 4

**Description**: Dashboard data sources should explicitly list support for Phase 3 module models.

**Impact**: Users may not realize Phase 3 data is queryable from dashboards.

**Recommendation**: Add to Phase 4 spec.md:
```markdown
### Supported Models
The Dashboard system SHALL support data sources from:
- All Odoo Community models (sales, inventory, etc.)
- All Loomworks Phase 3 modules (PLM ECOs, Payslips, FSM Tasks, etc.)
- Studio-created custom models (x_* prefix)
```

#### Issue M3: Spreadsheet/Dashboard Overlap Not Addressed

**Severity**: MEDIUM
**Location**: Phase 3.1, Phase 4

**Description**: Both provide charting and data visualization. No guidance on when to use which.

**Impact**: User confusion, potential duplicate implementations.

**Recommendation**: Add a "When to Use" section to both specs:
- Spreadsheet: Ad-hoc analysis, data manipulation, formulas, Excel replacement
- Dashboard: Real-time monitoring, executive KPIs, interactive filtering

#### Issue M4: PLM-Sign Integration Incomplete

**Severity**: MEDIUM
**Location**: Phase 3.2

**Description**: PLM proposal mentions optional `loomworks_sign` integration for ECO approvals (`plm.eco.approval.signature` field) but integration details are minimal.

**Impact**: Digital signature workflow may not be fully implemented.

**Recommendation**: Add explicit integration requirements to PLM spec:
```markdown
### Requirement: Digital Signature Integration
When `loomworks_sign` is installed, ECO approvals SHALL support:
- Digital signature capture via Sign module
- Signature verification display
- Audit trail linking to Sign request
```

### 5.4 Low Priority Issues

#### Issue L1: Skill SKILL.md Format vs Odoo XML Data

**Severity**: LOW
**Location**: Phase 6

**Description**: Skills export as SKILL.md files but Odoo typically uses XML for data. Import/export may need dual format support.

**Impact**: Minor friction for Odoo administrators expecting XML.

**Recommendation**: Support both formats - SKILL.md for human editing and XML export for Odoo standard tools.

#### Issue L2: Timezone Handling Across Sessions

**Severity**: LOW
**Location**: Phase 2, Phase 5

**Description**: AI sessions capture user timezone but snapshot restore might cross timezone boundaries.

**Impact**: Minor display issues in restored data timestamps.

**Recommendation**: Store all timestamps in UTC; convert only for display.

#### Issue L3: Performance Benchmarks Need Consolidation

**Severity**: LOW
**Location**: All phases

**Description**: Performance targets are scattered across proposals.

**Impact**: No single source of truth for performance requirements.

**Recommendation**: Add a `PERFORMANCE_REQUIREMENTS.md` document consolidating all targets:
- AI response: < 3 seconds
- Snapshot creation: < 30 seconds
- PITR restore: < 15 minutes
- Dashboard render: < 1 second
- Page load: < 1 second additional from branding

---

## 6. Recommendations

### 6.1 Required Actions (Block deployment if not addressed)

| # | Action | Phase | Owner | Priority | Status |
|---|--------|-------|-------|----------|--------|
| R1 | Define `ai.operation.log` model location explicitly | Phase 2/5 | Architect | HIGH | **RESOLVED** |
| R2 | Specify Node.js version requirements | Phase 3.1, 4 | DevOps | HIGH | **RESOLVED** |

### 6.2 Recommended Improvements

| # | Action | Phase | Impact |
|---|--------|-------|--------|
| R3 | Add AI tool registration pattern documentation | Phase 2 | Enables consistent Phase 3 tool implementation |
| R4 | Document Dashboard vs Spreadsheet use cases | Phase 3.1, 4 | Reduces user confusion |
| R5 | Complete PLM-Sign integration specification | Phase 3.2 | Ensures feature completeness |
| R6 | Create consolidated PERFORMANCE_REQUIREMENTS.md | Project | Single source of truth |
| R7 | Add explicit Dashboard support for Phase 3 models | Phase 4 | User guidance |

### 6.3 Future Considerations

| # | Consideration | Timeline |
|---|---------------|----------|
| F1 | PgBouncer connection pooling (mentioned as Phase 6+) | Post-launch |
| F2 | Multi-region active-active replication | Phase 7+ |
| F3 | Real-time streaming replication standby | Phase 7+ |
| F4 | Mobile app builder for Studio | Future enhancement |

---

## 7. LGPL v3 Compliance Check

### Status: COMPLIANT

All proposals maintain consistent LGPL v3 compliance:

| Checkpoint | Status | Notes |
|------------|--------|-------|
| No Enterprise code copying | PASS | Explicitly stated in all Phase 3 modules |
| LGPL-3 license declaration | PASS | All manifests declare `'license': 'LGPL-3'` |
| Attribution to Odoo | PASS | Phase 1 includes proper attribution |
| Source availability | PASS | Open-source model confirmed |
| Third-party library licenses | PASS | Univer (Apache-2.0), React (MIT), Frappe Gantt (MIT) |

---

## 8. Sign-off Checklist

### Ready for Implementation

- [x] Phase 1: Foundation & Branding - **READY**
- [x] Phase 2: AI Integration - **READY** (with R1 addressed)
- [x] Phase 3.1: Studio & Spreadsheet - **READY** (with R2 addressed)
- [x] Phase 3.2: PLM, Sign, Appointment - **READY** (R5 recommended)
- [x] Phase 3.3: Payroll, FSM, Planning - **READY**
- [x] Phase 4: Dashboard System - **READY** (with R2 addressed)
- [x] Phase 5: Infrastructure & Snapshots - **READY** (with R1 addressed)
- [x] Phase 6: Skills Framework - **READY**

### Pre-Implementation Requirements

Before beginning implementation:

1. [x] **R1**: Clarify `ai.operation.log` model ownership (Phase 2 or Phase 5) - **RESOLVED 2026-02-05**: Phase 2 owns, Phase 5 extends
2. [x] **R2**: Add Node.js 20+ requirement to project.md - **RESOLVED 2026-02-05**: Node.js >= 20.0.0 LTS added to project.md, Phase 3.1, and Phase 4
3. [ ] Create PERFORMANCE_REQUIREMENTS.md consolidating all targets

### Post-Review Actions

1. Update Phase 2 proposal with operation log model decision
2. Update Phase 3.1 and Phase 4 with Node.js requirements
3. Add AI tool registration pattern to Phase 2 design.md
4. Enhance Phase 3.2 PLM-Sign integration specification

---

## Appendix A: Model Name Consistency Check

All models follow the `loomworks.*` or domain-specific naming convention:

| Module | Model Names | Status |
|--------|-------------|--------|
| loomworks_ai | `loomworks.ai.agent`, `loomworks.ai.session`, `loomworks.ai.tool`, `loomworks.ai.message` | CONSISTENT |
| loomworks_studio | `studio.app`, `studio.view.customization`, `studio.automation` | CONSISTENT |
| loomworks_spreadsheet | `spreadsheet.document`, `spreadsheet.data.source`, `spreadsheet.pivot`, `spreadsheet.chart` | CONSISTENT |
| loomworks_plm | `plm.eco`, `plm.eco.type`, `plm.eco.stage`, `plm.bom.revision` | CONSISTENT |
| loomworks_sign | `sign.request`, `sign.item`, `sign.template` | CONSISTENT |
| loomworks_appointment | `appointment.type`, `appointment.slot` | CONSISTENT |
| loomworks_payroll | `hr.payroll.structure`, `hr.salary.rule`, `hr.payslip` | CONSISTENT (follows hr.* pattern) |
| loomworks_fsm | `fsm.worksheet.template`, `fsm.material.line` (extends `project.task`) | CONSISTENT |
| loomworks_planning | `planning.slot`, `planning.shift` | CONSISTENT |
| loomworks_dashboard | `dashboard.board`, `dashboard.widget`, `dashboard.data_source` | CONSISTENT |
| loomworks_tenant | `loomworks.tenant` | CONSISTENT |
| loomworks_snapshot | `loomworks.snapshot`, extends `loomworks.ai.operation.log` | CONSISTENT |
| loomworks_skills | `loomworks.skill`, `loomworks.skill.step`, `loomworks.skill.execution` | CONSISTENT |

---

## Appendix B: Security Group Consistency

| Module | User Group | Manager Group | Admin Group |
|--------|------------|---------------|-------------|
| AI | `group_ai_user` | `group_ai_manager` | - |
| Studio | `group_studio_user` | `group_studio_manager` | `group_studio_admin` |
| Spreadsheet | `group_spreadsheet_user` | - | - |
| PLM | `group_plm_user` | `group_plm_manager` | - |
| Sign | `group_sign_user` | `group_sign_manager` | - |
| Payroll | `group_payroll_user` | `group_payroll_manager` | `group_payroll_admin` |
| FSM | `group_fsm_user` | `group_fsm_manager` | - |
| Dashboard | `group_dashboard_user` | - | - |
| Tenant | `group_tenant_user` | `group_tenant_admin` | - |

---

**Review Completed**: 2026-02-05
**Next Review**: After implementation of Phase 1 and Phase 2
**Document Version**: 1.0
