# Patch Notes: R1 and R2 Resolution

**Date**: 2026-02-05
**Author**: AI Assistant
**Scope**: HIGH-priority compatibility issues from COMPATIBILITY_REVIEW.md

---

## Executive Summary

This patch resolves the two HIGH-priority issues identified in the Loomworks ERP compatibility review:

| Issue | Description | Status |
|-------|-------------|--------|
| **R1** | `ai.operation.log` Model Ownership Conflict | **RESOLVED** |
| **R2** | Node.js Version Unspecified | **RESOLVED** |

---

## Issue R1: ai.operation.log Model Ownership Conflict

### Problem Statement

Phase 2 (AI Integration) and Phase 5 (Infrastructure) both defined models for AI operation logging:
- Phase 2 defined `loomworks.ai.operation.log` with full audit trail fields
- Phase 5 defined `ai.operation.log` with snapshot integration fields

This created:
1. Inconsistent model naming (`loomworks.ai.*` vs `ai.*`)
2. Unclear ownership and dependency chain
3. Potential circular dependency if Phase 2 needed Phase 5's model

### Research Conducted

**Odoo Module Dependency Best Practices** (Sources: [Odoo Forum](https://www.odoo.com/forum/help-1/when-is-it-required-to-add-a-module-as-a-dependency-to-another-module-125784), [4devnet](https://4devnet.com/best-practices-for-scalable-odoo-module-development/)):
- Dependencies should be explicit in manifest files
- Use `_inherit` to extend existing models rather than redefining
- The module that first defines the model owns it
- Extending modules should depend on the owner module

**AI Operation Logging Patterns** (Sources: [Yodaplus - ERP Audit Trails](https://yodaplus.com/blog/audit-trails-in-erp-how-to-design-them-right/), [Medium - AI Audit Logging](https://medium.com/@pranavprakash4777/audit-logging-for-ai-what-should-you-track-and-where-3de96bbf171b)):
- AI operations should be logged in a dedicated audit model
- The AI module should own the logging model for self-contained deployment
- Infrastructure modules should extend logging for disaster recovery integration
- Granularity: field-level tracking for high-risk operations

### Resolution Applied

**Decision**: Phase 2 (`loomworks_ai`) owns the canonical `loomworks.ai.operation.log` model. Phase 5 (`loomworks_snapshot`) extends it via Odoo's `_inherit` mechanism.

**Rationale**:
1. Phase 2 is the AI module - it should own AI-related models
2. This allows Phase 2 to be deployed independently for AI functionality
3. Phase 5's snapshot integration is an enhancement, not a requirement
4. Clear dependency chain: `loomworks_snapshot` depends on `loomworks_ai`

### Files Modified

#### 1. `/home/loomworks/Desktop/LoomworksERP/openspec/changes/phase5-infrastructure/design.md`

**Changes**:
- Added "Module Dependencies" section with explicit manifest declarations
- Changed `ai.operation.log` definition to inherit from `loomworks.ai.operation.log`
- Renamed class to `AIOperationLogSnapshotExtension` for clarity
- Added documentation explaining the ownership model
- Added `snapshot_id`, `undone`, `undone_at` as extension fields
- Updated `action_undo()` to use `model_name` field from base class
- Added `loomworks_ai` as explicit dependency in manifest

**Key Code Change**:
```python
# Before (Phase 5 defined its own model):
class AIOperationLog(models.Model):
    _name = "ai.operation.log"
    ...

# After (Phase 5 extends Phase 2's model):
class AIOperationLogSnapshotExtension(models.Model):
    _inherit = 'loomworks.ai.operation.log'

    # Extension fields for PITR integration
    snapshot_id = fields.Many2one('loomworks.snapshot', ...)
    undone = fields.Boolean(default=False)
    undone_at = fields.Datetime()
```

#### 2. `/home/loomworks/Desktop/LoomworksERP/openspec/COMPATIBILITY_REVIEW.md`

**Changes**:
- Updated Model Cross-References table to show Phase 2 owns, Phase 5 extends
- Updated Section 3.2 (Snapshot System integration) to reflect resolution
- Marked Issue H1 as RESOLVED with resolution details
- Updated Required Actions table with RESOLVED status
- Updated Pre-Implementation Requirements checklist

---

## Issue R2: Node.js Version Unspecified

### Problem Statement

Phase 3.1 (Studio/Spreadsheet) and Phase 4 (Dashboard) require Node.js for frontend builds but did not specify version requirements:
- No Node.js version in project.md
- No Node.js version in Phase 3.1 design.md
- No Node.js version in Phase 4 proposal

This could cause:
- Build failures in different environments
- Incompatibility with required libraries
- Security vulnerabilities from unsupported Node.js versions

### Research Conducted

**Univer Library Requirements** (Source: [Univer Docs](https://docs.univer.ai/en-US/guides/sheets/getting-started/node)):
- Univer spreadsheet library requires Node.js >= 18.17.0
- Supports both browser and Node.js environments

**Node.js LTS Schedule** (Sources: [Node.js EOL](https://nodejs.org/en/about/eol), [endoflife.date](https://endoflife.date/nodejs)):
- Node.js 18 LTS: EOL April 30, 2025 (already end-of-life)
- Node.js 20 LTS: EOL April 30, 2026 (recommended for production)
- Node.js 22 LTS: Current active LTS version

**React 18 Requirements** (Sources: [React Blog](https://react.dev/blog/2022/03/29/react-v18), [bobbyhadz](https://bobbyhadz.com/blog/create-react-app-requires-node-14-or-higher)):
- Create React App requires Node.js >= 14.0.0
- Modern React tooling benefits from Node.js 18+ features

### Resolution Applied

**Decision**: Require Node.js >= 20.0.0 LTS across all proposals.

**Rationale**:
1. Univer requires >= 18.17.0, so 18.x minimum is needed
2. Node.js 18 LTS reached EOL on April 30, 2025 - not suitable for production
3. Node.js 20 LTS has security support until April 2026
4. Node.js 22 LTS is the current active version
5. Consistent version across all modules simplifies deployment

### Files Modified

#### 1. `/home/loomworks/Desktop/LoomworksERP/openspec/project.md`

**Changes**:
- Added "Runtime Environment Requirements" table with all versions
- Added "Node.js Version Policy" section with rationale
- Added Univer packages to Key Node.js Packages section
- Specified React@18 explicitly

**Key Addition**:
```markdown
### Runtime Environment Requirements

| Component | Version | Required For | Notes |
|-----------|---------|--------------|-------|
| **Python** | >= 3.10 | Odoo v18 | Core backend runtime |
| **PostgreSQL** | >= 15 | Database | WAL archiving for PITR snapshots |
| **Node.js** | >= 20.0.0 (LTS) | Frontend builds | Dashboard (React), Spreadsheet (Univer) |
| **npm** | >= 9.0.0 | Package management | Node.js package manager |
| **Redis** | >= 7.0 | Caching | Session cache and message queue |
```

#### 2. `/home/loomworks/Desktop/LoomworksERP/openspec/changes/phase3-tier1-studio-spreadsheet/design.md`

**Changes**:
- Added "Runtime Requirements" section after Constraints
- Added table with Node.js >= 20.0.0, npm >= 9.0.0, Python >= 3.10, PostgreSQL >= 15
- Added rationale explaining version selection

#### 3. `/home/loomworks/Desktop/LoomworksERP/openspec/proposals/phase4-dashboard.md`

**Changes**:
- Added "Runtime Requirements" section in Impact area
- Added table with Node.js >= 20.0.0, npm >= 9.0.0, Python >= 3.10, PostgreSQL >= 15
- Added rationale noting consistency with Phase 3.1

#### 4. `/home/loomworks/Desktop/LoomworksERP/openspec/COMPATIBILITY_REVIEW.md`

**Changes**:
- Updated Python/JS Library Versions table to show Node.js 20.0.0+ LTS
- Marked Issue H2 as RESOLVED with resolution details
- Updated Required Actions table with RESOLVED status
- Updated Pre-Implementation Requirements checklist

---

## Verification Checklist

### R1 Verification

- [x] Phase 2 defines `loomworks.ai.operation.log` as canonical model
- [x] Phase 5 uses `_inherit = 'loomworks.ai.operation.log'` (not `_name`)
- [x] Phase 5 manifest declares dependency on `loomworks_ai`
- [x] No circular dependency exists (Phase 2 can deploy without Phase 5)
- [x] Model naming follows `loomworks.*` convention consistently
- [x] COMPATIBILITY_REVIEW.md updated with resolution

### R2 Verification

- [x] project.md specifies Node.js >= 20.0.0 LTS
- [x] Phase 3.1 design.md specifies Node.js >= 20.0.0 LTS
- [x] Phase 4 proposal specifies Node.js >= 20.0.0 LTS
- [x] Rationale documented citing Univer requirements and Node.js EOL dates
- [x] npm version specified (>= 9.0.0)
- [x] COMPATIBILITY_REVIEW.md updated with resolution

---

## Summary of All Modified Files

| File | Changes |
|------|---------|
| `/home/loomworks/Desktop/LoomworksERP/openspec/changes/phase5-infrastructure/design.md` | Added Module Dependencies section, changed ai.operation.log to extend Phase 2 model |
| `/home/loomworks/Desktop/LoomworksERP/openspec/changes/phase3-tier1-studio-spreadsheet/design.md` | Added Runtime Requirements section with Node.js >= 20.0.0 |
| `/home/loomworks/Desktop/LoomworksERP/openspec/proposals/phase4-dashboard.md` | Added Runtime Requirements section with Node.js >= 20.0.0 |
| `/home/loomworks/Desktop/LoomworksERP/openspec/project.md` | Added Runtime Environment Requirements table and Node.js Version Policy |
| `/home/loomworks/Desktop/LoomworksERP/openspec/COMPATIBILITY_REVIEW.md` | Updated multiple sections to mark R1 and R2 as RESOLVED |

---

## Research Sources

### R1 - Odoo Module Dependencies
- [Odoo Forum: When to add module dependency](https://www.odoo.com/forum/help-1/when-is-it-required-to-add-a-module-as-a-dependency-to-another-module-125784)
- [4devnet: Best Practices for Scalable Odoo Module Development](https://4devnet.com/best-practices-for-scalable-odoo-module-development/)
- [Odoo Documentation: Building a Module](https://www.odoo.com/documentation/18.0/developer/tutorials/backend.html)

### R1 - AI Audit Logging Patterns
- [Yodaplus: Audit Trails in ERP](https://yodaplus.com/blog/audit-trails-in-erp-how-to-design-them-right/)
- [Medium: Audit Logging for AI](https://medium.com/@pranavprakash4777/audit-logging-for-ai-what-should-you-track-and-where-3de96bbf171b)
- [Martin Fowler: Audit Log Pattern](https://martinfowler.com/eaaDev/AuditLog.html)

### R2 - Node.js Requirements
- [Univer Documentation: Node.js Getting Started](https://docs.univer.ai/en-US/guides/sheets/getting-started/node)
- [Node.js End-of-Life Schedule](https://nodejs.org/en/about/eol)
- [endoflife.date: Node.js](https://endoflife.date/nodejs)
- [Vercel: Node.js 18 Deprecation Notice](https://vercel.com/changelog/node-js-18-is-being-deprecated)

### R2 - React Requirements
- [React v18.0 Release Blog](https://react.dev/blog/2022/03/29/react-v18)
- [React 18 Upgrade Guide](https://legacy.reactjs.org/blog/2022/03/08/react-18-upgrade-guide.html)

---

**Document Version**: 1.0
**Last Updated**: 2026-02-05
