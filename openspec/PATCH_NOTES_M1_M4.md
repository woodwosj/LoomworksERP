# Patch Notes: M1-M4 Medium Priority Issue Resolution

**Date**: 2026-02-05
**Reviewer**: Claude Opus 4.5 (Automated Compatibility Analysis)
**Scope**: Resolve 4 medium-priority issues identified in COMPATIBILITY_REVIEW.md v2.0

---

## Executive Summary

This patch resolves all four medium-priority compatibility issues (M1-M4) identified in the Loomworks ERP OpenSpec compatibility review. Each issue has been addressed with research-backed solutions that maintain architectural consistency across all 8 phases.

| Issue | Title | Resolution |
|-------|-------|------------|
| M1 | React Bridge Timing | React loads in Phase 3.1 for Univer; Phase 4 reuses |
| M2 | PWA Service Worker Scope | FSM-specific route whitelist implemented |
| M3 | Skills Depends on Snapshot | Explicit dependency + graceful degradation |
| M4 | AI Tool Registration Pattern | ToolProvider mixin pattern added to Phase 2 |

---

## M1: React Bridge Timing (Phase 3.1 / Phase 4)

### Problem Statement

The Spreadsheet module (Phase 3.1) uses Univer for spreadsheet functionality, which may require React. However, the React Bridge was scheduled for Phase 4 (Dashboard), creating a potential timing conflict.

### Research Conducted

**Source**: [Univer Official Documentation - CDN Installation](https://docs.univer.ai/guides/sheets/getting-started/installation/cdn)

**Finding**: Univer **requires React** as a runtime dependency. The CDN installation explicitly lists:
- `react@18.3.1` (UMD production build)
- `react-dom@18.3.1` (UMD production build)
- `rxjs` (RxJS library for reactive programming)
- `echarts@5.6.0` (for chart rendering)

The documentation shows React must be loaded before Univer can initialize.

### Resolution

1. **React libraries are now loaded in Phase 3.1** as a dependency of the Univer spreadsheet integration
2. **Phase 4 reuses the same React instance** rather than bundling it separately
3. **Asset bundle order** ensures React is available before any components that need it

### Changes Made

**File**: `/openspec/changes/phase3-tier1-studio-spreadsheet/design.md`

Added new section: "React Dependency Clarification (M1 Resolution)"

Key additions:
- Documentation of Univer's React requirement
- Asset bundle configuration showing React loading order
- Owl-to-React bridge pattern for Univer integration
- Clarification that Phase 4 extends this foundation

### Code Pattern

```xml
<!-- In web/__manifest__.py assets -->
'web.assets_backend': [
    # React libraries (Phase 3.1 - required for Univer)
    ('prepend', 'web/static/lib/react/react.production.min.js'),
    ('prepend', 'web/static/lib/react/react-dom.production.min.js'),
    ('prepend', 'web/static/lib/react/rxjs.umd.min.js'),
    # Univer libraries
    'web/static/lib/univer/*.js',
]
```

---

## M2: PWA Service Worker Scope (Phase 3.3)

### Problem Statement

The PWA service worker in Phase 3.3 registers with scope `/`, which could intercept and cache all Odoo URLs. This might cause unintended offline behavior for modules that don't need PWA support (e.g., accounting, sales).

### Research Conducted

**Sources**:
- [Service Worker Scope Best Practices - web.dev](https://web.dev/learn/pwa/service-workers)
- [Using Service Workers - MDN](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API/Using_Service_Workers)
- [PWA Best Practices - Microsoft](https://learn.microsoft.com/en-us/microsoft-edge/progressive-web-apps/how-to/best-practices)

**Key Findings**:
1. Service worker scope should be carefully controlled to prevent unintended caching
2. URL filtering in the fetch handler is the recommended approach for fine-grained control
3. Non-matching routes should pass through without any caching interference

### Resolution

Implemented a **FSM-specific route whitelist** that restricts offline caching and sync operations to FSM-related routes only. Non-FSM routes pass through to the network without any service worker interference.

### Changes Made

**File**: `/openspec/proposals/phase3-tier3-payroll-fsm-planning.md`

Added:
1. "PWA Service Worker URL Filtering Strategy (M2 Resolution)" section header
2. FSM_ROUTE_WHITELIST constant with specific FSM URLs
3. FSM_STATIC_WHITELIST for cacheable static assets
4. `isFSMRoute()` and `isFSMStaticAsset()` helper functions
5. Early return for non-FSM routes in fetch handler
6. Research source citations in references section

### Code Pattern

```javascript
const FSM_ROUTE_WHITELIST = [
    '/fsm/',                      // FSM main routes
    '/my/tasks/',                 // Portal task views
    '/my/fsm/',                   // Portal FSM views
    '/web/dataset/call_kw/project.task/action_fsm',
    '/web/dataset/call_kw/fsm.', // All FSM model calls
    '/loomworks_fsm/',            // Module-specific routes
];

// In fetch handler:
if (!isFSMRoute(url) && !isFSMStaticAsset(url)) {
    return; // Pass through to network without caching
}
```

---

## M3: Skills Depends on Snapshot (Phase 6 / Phase 5)

### Problem Statement

The Skills Framework (Phase 6) uses the Snapshot System (Phase 5) for rollback capabilities. This creates a dependency that was not explicitly documented, and the behavior when Phase 5 is not installed was undefined.

### Resolution

Added explicit dependency documentation and implemented graceful degradation:

1. **Phase 2 (AI Integration)**: Marked as **REQUIRED** dependency
2. **Phase 5 (Snapshots)**: Marked as **OPTIONAL** dependency with graceful degradation

### Changes Made

**File**: `/openspec/proposals/phase6-skills-framework.md`

Added new section: "Phase Dependencies and Graceful Degradation (M3 Resolution)"

Key additions:
- Dependency matrix table (Phase 2 required, Phase 5 optional)
- Detailed explanation of why Phase 2 is required
- Code examples for graceful degradation
- Feature matrix comparing capabilities with/without Phase 5
- User notification pattern for degraded mode

### Graceful Degradation Behavior

| Feature | With Phase 5 | Without Phase 5 |
|---------|--------------|-----------------|
| Pre-execution checkpoint | Full PITR snapshot | PostgreSQL SAVEPOINT |
| Rollback scope | Entire database | Current transaction only |
| Post-commit undo | Yes | No |
| Cross-transaction rollback | Yes | No |
| Snapshot retention | Configurable | Until transaction ends |

### Code Pattern

```python
class RollbackManager:
    def create_savepoint(self, name):
        if self.snapshot_service:
            # Phase 5 available: use full PITR snapshot
            return self.snapshot_service.create_snapshot(name=f"skill_{name}")
        else:
            # Phase 5 not available: use PostgreSQL savepoint
            savepoint_id = f"skill_{name}_{uuid4().hex[:8]}"
            self.env.cr.execute(f"SAVEPOINT {savepoint_id}")
            return savepoint_id
```

---

## M4: AI Tool Registration Pattern (Phase 2)

### Problem Statement

Phase 3+ modules (Studio, Spreadsheet, PLM, FSM, etc.) need to register AI tools (e.g., `studio_create_app`, `fsm_dispatch_technician`) but no standard registration pattern existed in Phase 2.

### Research Conducted

**Sources**:
- [Odoo 18 Registries Documentation](https://www.odoo.com/documentation/18.0/developer/reference/frontend/registries.html)
- [A Guide to Registries in Odoo 18](https://bassaminfotech.com/odoo18-registries/)
- [Dynamic Tool Updates in MCP - Spring AI](https://spring.io/blog/2025/05/04/spring-ai-dynamic-tool-updates-with-mcp/)

**Key Findings**:
1. Odoo uses registries as the main extension points for modules to contribute functionality
2. MCP protocol supports dynamic tool registration via notifications
3. Abstract models with `_inherit` provide clean patterns for module contributions

### Resolution

Implemented a **ToolProvider mixin pattern** that follows Odoo conventions:

1. `loomworks.ai.tool.provider` - Abstract model that modules inherit
2. `_get_tool_definitions()` - Method to override with tool definitions
3. `_register_tools()` / `_unregister_tools()` - Auto-registration lifecycle
4. Module hooks for installation/uninstallation
5. JavaScript registry for frontend-only tools

### Changes Made

**File**: `/openspec/proposals/phase2-ai-integration.md`

Added new section: "2.2.3.1 AI Tool Registration Pattern (M4 Resolution)"

Key additions:
- `AIToolProvider` abstract model with full documentation
- `AIToolRegistry` model for discovering all providers
- Example: `StudioToolProvider` for Phase 3.1
- Example: `FSMToolProvider` for Phase 3.3
- Module hook patterns for `__manifest__.py` and `__init__.py`
- JavaScript `ai_tool_registry` for frontend tools
- Research citations

### Code Pattern

```python
# In Phase 2: Define the mixin
class AIToolProvider(models.AbstractModel):
    _name = 'loomworks.ai.tool.provider'

    @api.model
    def _get_tool_definitions(self):
        return []  # Override in inheriting models

    @api.model
    def _register_tools(self):
        # Creates/updates loomworks.ai.tool records
        ...

# In Phase 3+ modules: Use the mixin
class StudioToolProvider(models.AbstractModel):
    _name = 'studio.tool.provider'
    _inherit = 'loomworks.ai.tool.provider'

    @api.model
    def _get_tool_definitions(self):
        return [
            {
                'technical_name': 'studio_create_app',
                'name': 'Create Studio App',
                'category': 'action',
                'description': '...',
                'parameters_schema': {...},
                'implementation_method': 'loomworks_studio.services.tools.create_app',
            },
        ]
```

---

## Files Modified

| File | Issue | Change Type |
|------|-------|-------------|
| `/openspec/changes/phase3-tier1-studio-spreadsheet/design.md` | M1 | Added React Dependency Clarification section |
| `/openspec/proposals/phase3-tier3-payroll-fsm-planning.md` | M2 | Added PWA URL Filtering Strategy |
| `/openspec/proposals/phase6-skills-framework.md` | M3 | Added Phase Dependencies and Graceful Degradation |
| `/openspec/proposals/phase2-ai-integration.md` | M4 | Added AI Tool Registration Pattern |
| `/openspec/COMPATIBILITY_REVIEW.md` | All | Updated issue statuses, checklist, recommendations |

---

## Verification Checklist

- [x] M1: Phase 3.1 design.md documents React as Univer dependency
- [x] M1: Asset bundle order specified for React loading
- [x] M2: FSM_ROUTE_WHITELIST defined in service worker
- [x] M2: Non-FSM routes explicitly pass through
- [x] M3: Phase 2 marked as REQUIRED dependency
- [x] M3: Phase 5 marked as OPTIONAL with degradation
- [x] M3: Feature matrix documents capabilities with/without Phase 5
- [x] M4: AIToolProvider abstract model defined
- [x] M4: Example providers for Studio and FSM included
- [x] M4: JavaScript registry for frontend tools added
- [x] COMPATIBILITY_REVIEW.md updated with RESOLVED status
- [x] All research sources cited in relevant documents

---

## Research Citations

### M1: React Bridge Timing
- Univer Official Documentation - CDN Installation: https://docs.univer.ai/guides/sheets/getting-started/installation/cdn
- Univer React Integration Guide: https://docs.univer.ai/guides/sheets/getting-started/integrations/react

### M2: PWA Service Worker Scope
- web.dev - Service Workers: https://web.dev/learn/pwa/service-workers
- MDN - Using Service Workers: https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API/Using_Service_Workers
- Microsoft - PWA Best Practices: https://learn.microsoft.com/en-us/microsoft-edge/progressive-web-apps/how-to/best-practices

### M4: AI Tool Registration Pattern
- Odoo 18 Registries Documentation: https://www.odoo.com/documentation/18.0/developer/reference/frontend/registries.html
- Bassam Infotech - Guide to Registries in Odoo 18: https://bassaminfotech.com/odoo18-registries/
- Spring AI - Dynamic Tool Updates with MCP: https://spring.io/blog/2025/05/04/spring-ai-dynamic-tool-updates-with-mcp/

---

## Impact Assessment

### No Breaking Changes

All resolutions are **backward compatible** and **additive**:
- M1: React loading is transparent to existing Owl components
- M2: Non-FSM modules unaffected by PWA changes
- M3: Skills work with or without Phase 5 (degraded mode)
- M4: Existing tool definitions remain valid; mixin is optional

### Implementation Order

The resolutions do not change the recommended phase implementation order:
1. Phase 1 (Foundation) - No changes
2. Phase 2 (AI Integration) - M4 adds ToolProvider mixin
3. Phase 3.1 (Studio/Spreadsheet) - M1 adds React loading
4. Phase 3.2 (PLM/Sign/Appointment) - No changes
5. Phase 3.3 (Payroll/FSM/Planning) - M2 adds PWA filtering
6. Phase 4 (Dashboard) - Reuses React from Phase 3.1
7. Phase 5 (Infrastructure) - No changes
8. Phase 6 (Skills Framework) - M3 adds dependency documentation

---

**Document Version**: 1.0
**Created By**: Claude Opus 4.5 (Automated Analysis)
**Review Status**: Complete
