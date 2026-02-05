# Loomworks ERP - OpenSpec Compatibility Review (Revision 2)

**Review Date**: 2026-02-05
**Reviewer**: Automated Compatibility Analysis (Revision 2 - Full Fork Architecture)
**Scope**: All 8 Phases (Foundation through Skills Framework)
**Total Project Duration**: 52 Weeks
**Architecture**: FULL FORK of Odoo Community v18

---

## 1. Executive Summary

### Overall Assessment: APPROVED WITH RECOMMENDATIONS

The revised Loomworks ERP OpenSpec proposals demonstrate a **coherent, well-integrated system design** for a fully forked Odoo architecture. All proposals have been updated to reflect the FULL FORK strategy where core modifications are made directly in the forked Odoo codebase at `/odoo/`.

**Key Strengths:**
- **Consistent Fork Strategy**: All proposals correctly reference `/odoo/` as the forked core location
- **Clear Core vs Addon Separation**: Each proposal explicitly distinguishes between core modifications and addon code
- **Well-Defined Phase Dependencies**: Critical path dependencies are properly documented
- **LGPL v3 Compliance**: All modifications maintain proper attribution markers (`LOOMWORKS-*` comments)
- **Native View Types**: Spreadsheet, Gantt, and Dashboard are integrated as first-class view types
- **Unified Infrastructure**: React bridge, PWA, and AI hooks are shared across all phases

**Areas Requiring Attention:**
- Some overlapping modifications to `odoo/addons/web/static/src/views/` need coordination
- React bridge must be available before Spreadsheet (Phase 3.1) and Dashboard (Phase 4)
- Skills framework (Phase 6) depends on both AI hooks (Phase 2) and snapshots (Phase 5)

**Architecture Validation**: PASS

---

## 2. Core Modification Matrix

This matrix shows which files each phase modifies in the forked Odoo core.

### 2.1 Forked Core Files (`odoo/odoo/`)

| File Path | Phase 1 | Phase 2 | Phase 3.2 | Phase 3.3 | Phase 5 | Phase 6 |
|-----------|:-------:|:-------:|:---------:|:---------:|:-------:|:-------:|
| `odoo/release.py` | **M** | - | - | - | - | - |
| `odoo/http.py` | **M** | - | - | - | **M** | - |
| `odoo/models.py` | - | **M** | - | - | **M** | - |
| `odoo/api.py` | - | **M** | - | - | - | - |
| `odoo/fields.py` | - | - | **M** | - | - | - |
| `odoo/tools/pdf.py` | - | - | **A** | - | - | - |
| `odoo/service/server.py` | **M** | **M** | - | - | - | - |

**Legend**: **M** = Modified, **A** = Added, **-** = No change

### 2.2 Forked Core Addons (`odoo/addons/`)

| File Path | P1 | P2 | P3.1 | P3.2 | P3.3 | P4 | P5 | P6 |
|-----------|:--:|:--:|:----:|:----:|:----:|:--:|:--:|:--:|
| `base/models/ir_ui_view.py` | - | - | **M** | - | **M** | **M** | - | - |
| `base/models/ir_model.py` | - | - | **M** | - | - | - | - | - |
| `base/models/ir_actions.py` | - | - | - | - | - | - | - | **M** |
| `base/models/ir_actions_skill.py` | - | - | - | - | - | - | - | **A** |
| `web/static/src/webclient/` | **M** | **M** | - | - | - | - | - | - |
| `web/static/src/views/` | - | **M** | **M** | **M** | **M** | **M** | - | - |
| `web/static/src/core/ai/` | - | **A** | - | - | - | - | - | - |
| `web/static/src/core/react_bridge/` | - | - | - | - | - | **A** | - | - |
| `web/static/src/core/pwa/` | - | - | - | **A** | - | - | - | - |
| `web/static/src/studio/` | - | - | **A** | - | - | - | - | - |
| `web/static/lib/react/` | - | - | - | - | - | **A** | - | - |
| `web/__manifest__.py` | **M** | **M** | **M** | **M** | **M** | **M** | - | - |
| `web/views/webclient_templates.xml` | **M** | - | - | - | - | - | - | - |
| `mrp/models/mrp_bom.py` | - | - | - | **M** | - | - | - | - |
| `calendar/models/calendar_event.py` | - | - | - | **M** | - | - | - | - |
| `portal/controllers/portal.py` | - | - | - | **M** | - | - | - | - |
| `project/models/project_task.py` | - | - | - | - | **M** | - | - | - |
| `hr_contract/models/` | - | - | - | - | **M** | - | - | - |

### 2.3 Loomworks Addons (`loomworks_addons/`)

| Module | Phase | Dependencies |
|--------|-------|--------------|
| `loomworks_core` | 1 | `base`, `web`, `mail` |
| `loomworks_ai` | 2 | `loomworks_core`, `base`, `web` |
| `loomworks_studio` | 3.1 | `loomworks_core`, `base`, `web`, (opt: `loomworks_ai`) |
| `loomworks_spreadsheet` | 3.1 | `loomworks_core`, `base`, `web`, (opt: `loomworks_ai`, `documents`) |
| `loomworks_plm` | 3.2 | `loomworks_core`, `mrp`, (opt: `loomworks_sign`) |
| `loomworks_sign` | 3.2 | `loomworks_core`, `mail`, `portal` |
| `loomworks_appointment` | 3.2 | `loomworks_core`, `calendar`, `website` |
| `loomworks_payroll` | 3.3 | `loomworks_core`, `hr`, (opt: `hr_contract`) |
| `loomworks_fsm` | 3.3 | `loomworks_core`, `project`, `hr_timesheet` |
| `loomworks_planning` | 3.3 | `loomworks_core`, `hr`, (opt: `project`) |
| `loomworks_dashboard` | 4 | `loomworks_core`, `web`, (opt: `loomworks_ai`, `loomworks_spreadsheet`) |
| `loomworks_tenant` | 5 | `loomworks_core` |
| `loomworks_snapshot` | 5 | `loomworks_tenant`, **`loomworks_ai`** |
| `loomworks_skills` | 6 | **`loomworks_ai`**, **`loomworks_snapshot`** |

---

## 3. Conflict Analysis

### 3.1 Overlapping Modifications - RESOLVED

#### `odoo/addons/web/static/src/views/` Directory

Multiple phases add view types to this directory:

| Phase | View Type | Directory | Status |
|-------|-----------|-----------|--------|
| 3.1 | Spreadsheet | `views/spreadsheet/` | **No conflict** |
| 3.3 | Gantt | `views/gantt/` | **No conflict** |
| 4 | Dashboard | `views/dashboard/` | **No conflict** |
| 3.1 | Studio overlay | `views/form/`, `views/list/` | **Potential conflict** |

**Resolution**: Studio view enhancements (form_controller.js, list_controller.js) must use inheritance patterns that compose cleanly. Each enhancement adds mixins rather than replacing methods.

#### `odoo/addons/base/models/ir_ui_view.py`

Multiple phases extend the `ir.ui.view` model:

| Phase | Extension | Change |
|-------|-----------|--------|
| 3.1 | Studio customization | Adds `studio_customized`, `studio_customization_id`, `studio_arch_backup` fields |
| 3.1 | Spreadsheet view type | Adds `'spreadsheet'` to `type` selection |
| 3.3 | Gantt view type | Adds `'gantt'` to `type` selection |
| 4 | Dashboard view type | Adds `'dashboard'` to `type` selection |

**Resolution**: All `selection_add` modifications are additive and compatible. Fields from Studio customization do not conflict with view type additions. **No conflict**.

#### `odoo/odoo/models.py`

| Phase | Extension | Purpose |
|-------|-----------|---------|
| 2 | AI operation hooks | Adds `_ai_before_operation()` and `_ai_after_operation()` hooks |
| 5 | Tenant isolation | Adds `_check_tenant_isolation()` check |

**Resolution**: Both are independent hook additions to BaseModel. Phase 5 hooks run before Phase 2 hooks in the call chain. **No conflict**.

### 3.2 Asset Bundle Conflicts - MONITORED

The `web.assets_backend` bundle is extended by multiple phases:

```
Phase 1:  primary_variables.scss (prepend), loomworks_backend.scss
Phase 2:  core/ai/*.js, components/ai_chat/*.js
Phase 3.1: views/spreadsheet/*.js, studio/*.js, lib/univer/*.js
Phase 3.2: views/fields/signature/*.js
Phase 3.3: views/gantt/*.js, core/pwa/*.js
Phase 4:  lib/react/*.js, core/react_bridge/*.js, views/dashboard/*.js
Phase 6:  core/skill_recorder_service.js
```

**Load Order Requirement**:
1. Primary variables (Phase 1) - MUST be prepended
2. React libraries (Phase 4) - MUST load before react_bridge
3. React bridge (Phase 4) - MUST load before Spreadsheet (3.1) components that use it
4. All other JS - Order independent

**Recommendation**: Ensure Phase 4 React integration is completed before Phase 3.1 Spreadsheet components that optionally use React for chart rendering.

---

## 4. Dependency Graph

### 4.1 Critical Path

```
Phase 1: Fork + Rebrand
    │
    ├── Phase 2: AI Integration (Core)
    │       │
    │       ├── Phase 3.1: Studio/Spreadsheet
    │       │       │
    │       │       └── Phase 4: Dashboard (uses React bridge)
    │       │
    │       ├── Phase 3.2: PLM/Sign/Appointment
    │       │
    │       ├── Phase 3.3: Payroll/FSM/Planning
    │       │
    │       └── Phase 5: Infrastructure
    │               │
    │               └── Phase 6: Skills Framework
    │
    └── (All phases depend on Phase 1)
```

### 4.2 Detailed Dependencies

```
Phase 1 (Foundation)
  └── Required by: ALL OTHER PHASES
  └── Provides: Forked core, branding, loomworks_core module

Phase 2 (AI Integration)
  └── Requires: Phase 1
  └── Provides: loomworks.ai.* models, MCP server, AI hooks
  └── Required by: Phase 5 (snapshot extends ai.operation.log)
                   Phase 6 (skills use AI tools)

Phase 3.1 (Studio/Spreadsheet)
  └── Requires: Phase 1
  └── Optional: Phase 2 (AI tools for Studio)
              Phase 4 (React bridge for charts) *
  └── Provides: Studio view editing, spreadsheet view type

Phase 3.2 (PLM/Sign/Appointment)
  └── Requires: Phase 1
  └── Provides: Signature field type (core), PLM versioning, appointment booking

Phase 3.3 (Payroll/FSM/Planning)
  └── Requires: Phase 1
  └── Provides: Gantt view type (core), PWA infrastructure

Phase 4 (Dashboard)
  └── Requires: Phase 1
  └── Optional: Phase 2 (AI dashboard generation)
  └── Provides: React bridge (core), dashboard view type

Phase 5 (Infrastructure)
  └── Requires: Phase 1, Phase 2
  └── Provides: Multi-tenant routing, snapshot system, Docker/K8s infrastructure

Phase 6 (Skills Framework)
  └── Requires: Phase 2, Phase 5
  └── Provides: ir.actions.skill action type, session recording, intent matching
```

*Note: Phase 3.1 Spreadsheet can work without React, but advanced chart rendering benefits from React bridge. Implementation order flexibility exists.

---

## 5. New Core Components Alignment

### 5.1 Native View Types Registration

All new view types follow the consistent pattern in `odoo/addons/base/models/ir_ui_view.py`:

```python
type = fields.Selection(selection_add=[
    ('spreadsheet', 'Spreadsheet'),  # Phase 3.1
    ('gantt', 'Gantt'),              # Phase 3.3
    ('dashboard', 'Dashboard'),       # Phase 4
], ondelete={...})
```

**Status**: CONSISTENT across proposals

### 5.2 React Bridge Availability

| Component | Needs React Bridge | Phase Available |
|-----------|-------------------|-----------------|
| Spreadsheet charts (advanced) | Optional | 4 |
| Dashboard builder | Required | 4 |
| Graph view (Recharts) | Required | 4 |
| Pivot view (enhanced) | Required | 4 |

**Issue Identified**: Phase 3.1 Spreadsheet design includes Univer charts that may benefit from the React bridge, but Phase 4 introduces the React bridge.

**Resolution Options**:
1. **Recommended**: Spreadsheet uses Univer's native chart rendering (no React dependency)
2. Alternative: Move React bridge to Phase 3.1 (increases scope)

**Decision**: Spreadsheet (Phase 3.1) will use Univer's native capabilities. Enhanced React-based chart integration will be added as an optional enhancement after Phase 4 completes.

### 5.3 Signature Field Type

Phase 3.2 adds a native `Signature` field type to `odoo/odoo/fields.py`:

```python
class Signature(Field):
    type = 'signature'
    column_type = ('jsonb', 'jsonb')
```

**Verification Points**:
- [x] Registered in core fields.py
- [x] Widget registered in `web/static/src/views/fields/signature/`
- [x] Accessible to all modules after Phase 3.2

### 5.4 Skills Action Type

Phase 6 adds `ir.actions.skill` as a native action type:

```python
class IrActionsSkill(models.Model):
    _name = 'ir.actions.skill'
    _inherit = 'ir.actions.actions'
```

**Verification Points**:
- [x] Located in `odoo/odoo/addons/base/models/ir_actions_skill.py`
- [x] Inherits from `ir.actions.actions`
- [x] Registered in action manager
- [x] Requires Phase 2 AI tools for execution
- [x] Requires Phase 5 snapshots for rollback

### 5.5 PWA Infrastructure

Phase 3.3 adds PWA support in `odoo/addons/web/static/src/core/pwa/`:

**Verification Points**:
- [x] Service worker at `core/pwa/service_worker.js`
- [x] PWA service at `core/pwa/pwa_service.js`
- [x] Offline capabilities for FSM mobile views
- [x] Available to all modules after Phase 3.3

---

## 6. Distribution Compatibility

### 6.1 Docker Image Verification

Phase 5 defines Docker image structure that must include:

| Component | Source | Included |
|-----------|--------|----------|
| Forked Odoo core | `/odoo/` | YES |
| Loomworks addons | `/loomworks_addons/` | YES |
| React libraries | `web/static/lib/react/` | YES (after Phase 4) |
| Univer libraries | `spreadsheet/static/lib/univer/` | YES (after Phase 3.1) |
| Node.js runtime | System dependency | YES (>= 20.0.0 LTS) |
| Python dependencies | `requirements.txt` | YES |

**Addons path in container**: `/opt/loomworks/odoo/addons,/opt/loomworks/addons`

### 6.2 CI/CD Workflow Coverage

Phase 5 CI/CD workflows must test:

| Component | Test Type | Status |
|-----------|-----------|--------|
| Core modifications | Unit tests | Covered (`pytest odoo/`) |
| Loomworks addons | Unit tests | Covered (`pytest loomworks_addons/`) |
| View types (Spreadsheet, Gantt, Dashboard) | Frontend tests | QUnit in CI |
| React components | Jest tests | Covered in Phase 4 |
| Integration | Docker compose tests | Covered |

### 6.3 Rebrand Script Compatibility

Phase 1 rebrand script (`scripts/rebrand.py`) must handle:

| Pattern | Files Affected | Status |
|---------|---------------|--------|
| Logo replacements | `web/static/img/*` | Covered |
| Text replacements | All `.py`, `.js`, `.xml` | Covered |
| Manifest updates | `__manifest__.py` files | Covered |
| React components | `*.jsx` files | **ADD** to file handlers |
| SCSS variables | `primary_variables.scss` | Covered |

**Recommendation**: Ensure rebrand script handles `.jsx` files added in Phase 4.

---

## 7. LGPL v3 Compliance Check

### 7.1 Modification Markers

All core modifications must include the `LOOMWORKS-*` comment marker:

| Phase | Marker Pattern | Verified |
|-------|---------------|----------|
| 1 | `LOOMWORKS-CORE` | YES |
| 2 | `LOOMWORKS-AI` | YES |
| 3.1 | `LOOMWORKS-STUDIO`, `LOOMWORKS-SPREADSHEET` | YES |
| 3.2 | `LOOMWORKS-PLM`, `LOOMWORKS-SIGN` | YES |
| 3.3 | `LOOMWORKS-GANTT`, `LOOMWORKS-PWA`, `LOOMWORKS-PAYROLL` | YES |
| 4 | `LOOMWORKS-DASHBOARD`, `LOOMWORKS-REACT` | YES |
| 5 | `LOOMWORKS-TENANT`, `LOOMWORKS-SNAPSHOT` | YES |
| 6 | `LOOMWORKS-SKILLS` | YES |

### 7.2 Attribution Requirements

| Requirement | Status |
|-------------|--------|
| Original Odoo copyright in modified files | REQUIRED |
| Loomworks copyright addition | REQUIRED |
| LICENSE file at repository root | REQUIRED |
| About dialog attribution | REQUIRED |
| README attribution section | REQUIRED |

**Template for modified files**:
```python
# -*- coding: utf-8 -*-
# Loomworks ERP - An AI-first ERP system
# Copyright (C) 2024-2026 Loomworks
#
# Based on Odoo Community Edition
# Copyright (C) 2004-2024 Odoo S.A. <https://www.odoo.com>
#
# License: LGPL-3 (see LICENSE file)
#
# LOOMWORKS-[MARKER]: [Brief description of modification]
```

---

## 8. Issues Found

### 8.1 Critical Issues

**None identified.** All proposals are architecturally sound and compatible.

### 8.2 High Priority Issues

All HIGH priority issues from Revision 1 have been **RESOLVED**:

| Issue | Resolution | Status |
|-------|------------|--------|
| H1: ai.operation.log ownership | Phase 2 owns model, Phase 5 extends via `_inherit` | **RESOLVED** |
| H2: Node.js version unspecified | Node.js >= 20.0.0 LTS specified in project.md, Phase 3.1, Phase 4 | **RESOLVED** |

### 8.3 Medium Priority Issues

All MEDIUM priority issues have been **RESOLVED** in Revision 2.1:

#### Issue M1: React Bridge Timing (RESOLVED)

**Severity**: MEDIUM
**Location**: Phase 3.1, Phase 4
**Status**: **RESOLVED** (2026-02-05)

**Description**: The React bridge is defined in Phase 4, but Phase 3.1 Spreadsheet design mentions potential React usage for chart rendering.

**Research Finding**: Univer spreadsheet library **requires React** as a runtime dependency (React 18.3.1+, ReactDOM, RxJS).

**Resolution**:
- React libraries are now loaded in Phase 3.1 asset bundle as a Univer dependency
- Phase 4 Dashboard reuses the already-loaded React instance
- Phase 3.1 design.md updated with "React Dependency Clarification (M1 Resolution)" section
- Asset bundle order ensures React is available for all downstream consumers

**Files Modified**: `/openspec/changes/phase3-tier1-studio-spreadsheet/design.md`

#### Issue M2: PWA Service Worker Scope (RESOLVED)

**Severity**: MEDIUM
**Location**: Phase 3.3
**Status**: **RESOLVED** (2026-02-05)

**Description**: PWA service worker registers with scope `/`, which affects all Odoo URLs.

**Resolution**: Implemented FSM-specific route whitelist that restricts offline caching to FSM routes only:

```javascript
// M2 RESOLUTION: FSM-Specific Route Whitelist
const FSM_ROUTE_WHITELIST = [
    '/fsm/',                      // FSM main routes
    '/my/tasks/',                 // Portal task views
    '/my/fsm/',                   // Portal FSM views
    '/web/dataset/call_kw/project.task/action_fsm',
    '/web/dataset/call_kw/fsm.',  // All FSM model calls
    '/loomworks_fsm/',            // Module-specific routes
];

// Non-FSM routes pass through without PWA interference
if (!isFSMRoute(url) && !isFSMStaticAsset(url)) {
    return; // Pass through to network
}
```

**Files Modified**: `/openspec/proposals/phase3-tier3-payroll-fsm-planning.md`

#### Issue M3: Skills Execution Depends on Snapshot (RESOLVED)

**Severity**: MEDIUM
**Location**: Phase 6
**Status**: **RESOLVED** (2026-02-05)

**Description**: Skills framework uses snapshots for rollback, creating a hard dependency on Phase 5.

**Resolution**: Added explicit dependency documentation and graceful degradation:

- Phase 2 (AI Integration): **REQUIRED** dependency
- Phase 5 (Snapshots): **OPTIONAL** dependency with graceful degradation
- When Phase 5 is not installed, Skills Framework uses PostgreSQL SAVEPOINTs for transaction-level rollback
- When Phase 5 is installed, full PITR database-level rollback is available
- User notification when running in degraded mode

**Files Modified**: `/openspec/proposals/phase6-skills-framework.md`

#### Issue M4: AI Tool Registration Pattern (RESOLVED)

**Severity**: MEDIUM
**Location**: Phase 2, Phase 3 modules
**Status**: **RESOLVED** (2026-02-05)

**Description**: Phase 3 modules define AI tools (e.g., `studio_create_app`) but no standard registration pattern exists in Phase 2 design.

**Resolution**: Implemented `ToolProvider` mixin pattern following Odoo registry patterns:

```python
class AIToolProvider(models.AbstractModel):
    _name = 'loomworks.ai.tool.provider'

    @api.model
    def _get_tool_definitions(self):
        """Override to return list of tool definition dicts."""
        return []

    @api.model
    def _register_tools(self):
        """Auto-register tools on module installation."""
        # Creates/updates loomworks.ai.tool records

# Usage in Phase 3+ modules:
class StudioToolProvider(models.AbstractModel):
    _name = 'studio.tool.provider'
    _inherit = 'loomworks.ai.tool.provider'

    @api.model
    def _get_tool_definitions(self):
        return [
            {'technical_name': 'studio_create_app', ...},
            {'technical_name': 'studio_add_field', ...},
        ]
```

- JavaScript registry added for frontend-only tools
- Module hooks for auto-registration on install/uninstall
- Full examples provided for Studio and FSM modules

**Files Modified**: `/openspec/proposals/phase2-ai-integration.md`

### 8.4 Low Priority Issues

| Issue | Description | Status |
|-------|-------------|--------|
| L1: Skill SKILL.md format | Support both SKILL.md and XML export | DOCUMENTED |
| L2: Timezone handling | Store all timestamps in UTC | DOCUMENTED |
| L3: Performance benchmarks | Create PERFORMANCE_REQUIREMENTS.md | RECOMMENDED |

---

## 9. Integration Verification

### 9.1 Cross-Phase Model References

| Model | Defined In | Extended By | Referenced By | Status |
|-------|------------|-------------|---------------|--------|
| `loomworks.ai.session` | Phase 2 | - | Phase 5, Phase 6 | VERIFIED |
| `loomworks.ai.tool` | Phase 2 | - | Phase 3 (all), Phase 4, Phase 6 | VERIFIED |
| `loomworks.ai.operation.log` | Phase 2 | Phase 5 (adds `snapshot_id`) | Phase 6 | VERIFIED |
| `loomworks.snapshot` | Phase 5 | - | Phase 2 (rollback), Phase 6 | VERIFIED |
| `loomworks.tenant` | Phase 5 | - | All hosted modules | VERIFIED |
| `dashboard.data_source` | Phase 4 | - | Phase 3.1 (spreadsheet) | VERIFIED |
| `ir.actions.skill` | Phase 6 | - | Phase 2 (agent binding) | VERIFIED |

### 9.2 Core Service Dependencies

| Service | Defined In | Used By | Status |
|---------|------------|---------|--------|
| `studioService` | Phase 3.1 (core) | loomworks_studio addon | VERIFIED |
| `reactBridgeService` | Phase 4 (core) | loomworks_dashboard, enhanced graph/pivot | VERIFIED |
| `pwaService` | Phase 3.3 (core) | loomworks_fsm addon | VERIFIED |
| `aiService` | Phase 2 (core) | All AI-enabled modules | VERIFIED |
| `skillRecorderService` | Phase 6 (core) | Skills framework | VERIFIED |

### 9.3 View Type Registration

| View Type | Registered In | arch parser | Controller | Model | Renderer | Status |
|-----------|---------------|-------------|------------|-------|----------|--------|
| spreadsheet | Phase 3.1 | YES | YES | YES | YES | COMPLETE |
| gantt | Phase 3.3 | YES | YES | YES | YES | COMPLETE |
| dashboard | Phase 4 | YES | YES | YES | YES | COMPLETE |

---

## 10. Sign-off Status

### Phase Sign-off Checklist

| Phase | Title | Status | Blocking Issues | Ready |
|-------|-------|--------|-----------------|-------|
| 1 | Foundation & Branding | APPROVED | None | YES |
| 2 | AI Integration | APPROVED | None | YES |
| 3.1 | Studio & Spreadsheet | APPROVED | None (React optional) | YES |
| 3.2 | PLM, Sign, Appointment | APPROVED | None | YES |
| 3.3 | Payroll, FSM, Planning | APPROVED | M2 (minor) | YES |
| 4 | Dashboard System | APPROVED | None | YES |
| 5 | Infrastructure | APPROVED | None | YES |
| 6 | Skills Framework | APPROVED | None | YES |

### Pre-Implementation Checklist

- [x] All proposals reference consistent fork location (`/odoo/`)
- [x] Core modification paths documented in each proposal
- [x] Dependency chain validated (no circular dependencies)
- [x] `loomworks.ai.operation.log` ownership clarified (Phase 2 owns, Phase 5 extends)
- [x] Node.js version specified (>= 20.0.0 LTS)
- [x] View type registration consistent across proposals
- [x] LGPL attribution requirements documented
- [x] React dependency clarified for Phase 3.1 Spreadsheet (M1 RESOLVED)
- [x] PWA URL filtering strategy documented for Phase 3.3 (M2 RESOLVED)
- [x] Skills Framework dependency on Phase 5 documented with graceful degradation (M3 RESOLVED)
- [x] AI tool registration pattern added to Phase 2 (M4 RESOLVED)
- [ ] Create PERFORMANCE_REQUIREMENTS.md (RECOMMENDED)

---

## 11. Recommendations Summary

### Required Before Implementation

1. **None** - All blocking issues resolved

### Completed Improvements (M1-M4 Resolution)

| # | Recommendation | Phase | Status |
|---|---------------|-------|--------|
| R1 | Add `ToolProvider` mixin pattern documentation | Phase 2 | **COMPLETED** (M4) |
| R2 | Document PWA route filtering for FSM | Phase 3.3 | **COMPLETED** (M2) |

### Remaining Recommended Improvements

| # | Recommendation | Phase | Impact |
|---|---------------|-------|--------|
| R3 | Create consolidated PERFORMANCE_REQUIREMENTS.md | Project | Single source of truth for performance targets |
| R4 | Add `.jsx` handling to rebrand script | Phase 1 | Ensures React components are rebranded |
| R5 | Document Dashboard vs Spreadsheet use cases | Phase 3.1, 4 | User guidance |

### Future Considerations

| # | Consideration | Timeline |
|---|---------------|----------|
| F1 | PgBouncer connection pooling | Phase 6+ |
| F2 | Multi-region deployment | Phase 7+ |
| F3 | Mobile app builder for Studio | Future |
| F4 | Real-time collaboration for Spreadsheet | Future |

---

## Appendix A: Model Name Consistency Check

All models follow consistent naming conventions:

| Namespace | Pattern | Examples |
|-----------|---------|----------|
| AI | `loomworks.ai.*` | `loomworks.ai.agent`, `loomworks.ai.session` |
| Studio | `studio.*` | `studio.app`, `studio.view.customization` |
| Spreadsheet | `spreadsheet.*` | `spreadsheet.document`, `spreadsheet.data.source` |
| PLM | `plm.*` | `plm.eco`, `plm.eco.type` |
| Sign | `sign.*` | `sign.request`, `sign.item` |
| Appointment | `appointment.*` | `appointment.type`, `appointment.slot` |
| Payroll | `hr.payroll.*` | `hr.payroll.structure`, `hr.salary.rule` |
| Planning | `planning.*` | `planning.slot`, `planning.shift` |
| Dashboard | `dashboard.*` | `dashboard.board`, `dashboard.widget` |
| Tenant | `loomworks.tenant` | - |
| Snapshot | `loomworks.snapshot` | - |
| Skills | `loomworks.skill*` / `ir.actions.skill*` | `loomworks.skill`, `ir.actions.skill` |

---

## Appendix B: Forked Core File Summary

Total files modified in forked Odoo core:

| Category | Count | Notes |
|----------|-------|-------|
| Python core (`odoo/odoo/`) | 6 | release.py, http.py, models.py, api.py, fields.py, tools/pdf.py |
| Python addons (`odoo/addons/`) | ~15 | Across base, web, mrp, calendar, portal, project, hr_contract |
| JavaScript/Owl (`web/static/src/`) | ~30 | New view types, services, components |
| SCSS (`web/static/src/scss/`) | 5 | Branding, view styles |
| XML templates | ~20 | View definitions, component templates |

---

**Review Completed**: 2026-02-05
**Next Review**: After implementation of Phase 1 and Phase 2
**Document Version**: 2.0

---

## Changelog

### Version 2.1 (2026-02-05)
- **M1 RESOLVED**: React Bridge Timing - React loads in Phase 3.1 for Univer, reused by Phase 4
- **M2 RESOLVED**: PWA Service Worker Scope - Added FSM-specific route whitelist
- **M3 RESOLVED**: Skills Dependency - Added explicit dependency documentation and graceful degradation
- **M4 RESOLVED**: AI Tool Registration - Added ToolProvider mixin pattern to Phase 2
- Updated Pre-Implementation Checklist with resolved items
- Updated Recommendations Summary with completed items
- All medium-priority issues now RESOLVED

### Version 2.0 (2026-02-05)
- Complete review of revised proposals with FULL FORK architecture
- Added Core Modification Matrix (Section 2)
- Added Conflict Analysis (Section 3)
- Updated Dependency Graph with visual representation (Section 4)
- Added New Core Components Alignment (Section 5)
- Added Distribution Compatibility verification (Section 6)
- Updated LGPL Compliance check with modification markers (Section 7)
- Identified new medium-priority issues (M1, M2)
- Confirmed all HIGH priority issues from v1.0 are RESOLVED
- Added Integration Verification section (Section 9)
- Updated Sign-off Status for all phases (Section 10)

### Version 1.0 (2026-02-05)
- Initial compatibility review
- Identified H1 (ai.operation.log ownership) and H2 (Node.js version) issues
