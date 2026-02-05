# Change: Phase 3 Tier 1 - Studio and Spreadsheet (Core Fork Edition)

## Why

Loomworks ERP requires no-code customization capabilities and business intelligence tools to fulfill its AI-first vision. Users must be able to create custom applications and analyze data without developer involvement. These are the **highest priority** Phase 3 modules because:

1. **loomworks_studio** enables users to customize and create apps without developers, directly supporting the core differentiator of eliminating developer labor
2. **loomworks_spreadsheet** provides universal BI capabilities that integrate with AI dashboards and support data-driven decision making

Both modules are essential for the "Free software + AI does all the work" market positioning.

**Key Change in Approach**: Since Loomworks ERP is a **fully forked** Odoo Community v18 codebase, we can now implement Studio and Spreadsheet with **deep core integration** rather than as addon-only solutions. This enables:

- Native Studio toggle in every view (form, list, kanban)
- Spreadsheet as a first-class view type alongside form/list/kanban
- Direct modifications to `ir.model` and `ir.ui.view` for seamless dynamic model/view creation
- Better performance through core-level optimizations

## What Changes

### Core Modifications (Odoo Fork)

These changes are made directly to the forked Odoo source code:

| Area | Files Modified | Purpose |
|------|----------------|---------|
| **View Edit Mode** | `odoo/addons/web/static/src/views/*.js` | Add Studio toggle to all view controllers |
| **Studio Service** | `odoo/addons/web/static/src/studio/` | New core service for view editing |
| **Field Palette** | `odoo/addons/web/static/src/studio/field_palette/` | Drag-drop field insertion framework |
| **Spreadsheet View** | `odoo/addons/web/static/src/views/spreadsheet/` | New core view type |
| **ir.ui.view** | `odoo/odoo/addons/base/models/ir_ui_view.py` | Studio customization fields, spreadsheet view type |
| **ir.model** | `odoo/odoo/addons/base/models/ir_model.py` | Enhanced `_studio_create_model()` and `_studio_create_field()` methods |

### New Module: loomworks_studio

Business logic addon building on core modifications:

- `studio.app` - Custom application registry with state management
- `studio.view.customization` - View modification storage and generation
- `studio.view.field` - Field placement in views
- `studio.automation` - Workflow rules with trigger/action pattern
- Owl components for wizards and configuration dialogs
- MCP tools for AI agent integration

### New Module: loomworks_spreadsheet

Excel-like interface with BI capabilities:

- `spreadsheet.document` - Document storage with JSON serialization
- `spreadsheet.data.source` - Odoo data connections with live refresh
- `spreadsheet.pivot` - Dynamic pivot table configurations
- `spreadsheet.chart` - Chart visualization settings
- Univer spreadsheet library integration via Owl wrapper
- Custom ODOO.DATA(), ODOO.PIVOT(), ODOO.FIELD() formula functions
- MCP tools for AI agent integration

### Key Technical Decisions

1. **Core vs Addon Split**: Core modifications enable deep integration; addons contain business logic
2. **Studio in Core**: Every view has built-in Studio toggle via core controller modifications
3. **Spreadsheet as View Type**: Registered in core view registry alongside form/list/kanban
4. **Univer Library**: Apache-2.0 licensed, successor to Luckysheet, TypeScript-native
5. **LGPL v3 Compliance**: All implementations from scratch, no Odoo Enterprise code copying

## Impact

- **Affected specs**: None (new capabilities)
- **Affected code**:
  - Core modifications in forked `odoo/` directory
  - New module `loomworks_addons/loomworks_studio/`
  - New module `loomworks_addons/loomworks_spreadsheet/`
- **Dependencies**:
  - Odoo Community v18 core (forked) - `base`, `web`, `mail`
  - Node.js >= 20.0.0 LTS for Univer
  - Univer packages: `@univerjs/core`, `@univerjs/sheets`, `@univerjs/sheets-ui`, `@univerjs/sheets-formula`
- **Database changes**:
  - New fields on `ir.ui.view`: `studio_customized`, `studio_customization_id`, `studio_arch_backup`
  - New fields on `ir.model`: `studio_app_id`, `studio_origin`, `studio_icon`, `studio_color`
  - New tables: `studio_app`, `studio_view_customization`, `studio_view_field`, `studio_automation`, `studio_automation_action`
  - New tables: `spreadsheet_document`, `spreadsheet_data_source`, `spreadsheet_pivot`, `spreadsheet_pivot_dimension`, `spreadsheet_pivot_measure`, `spreadsheet_chart`
- **Integration points**:
  - AI agent MCP tools for Studio operations
  - AI agent MCP tools for Spreadsheet operations
  - Dashboard system integration for BI

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Upstream merge conflicts | High | Medium | Isolate core changes; document all modifications |
| Breaking changes in Odoo 19 | Medium | High | Abstract dependencies; maintain compatibility layer |
| Univer library instability | Medium | Medium | Pin versions; maintain compatibility layer |
| Large dataset performance | High | Medium | Pagination; lazy loading; row limits |
| Increased maintenance burden | High | Medium | Comprehensive tests; clear documentation |

## Timeline

- **Week 1-2**: Core modifications (A1-A4)
- **Week 2-3**: Spreadsheet view type, Studio scaffolding (A5, B1-B3)
- **Week 3-4**: Studio models, Spreadsheet models (B4-B5, C1-C3)
- **Week 4-5**: Studio UI, Spreadsheet models (B6-B8, C4-C5)
- **Week 5-6**: Univer integration (C6-C9)
- **Week 6-7**: Spreadsheet UI (C10-C12)
- **Week 7-8**: MCP tools (D1-D2)
- **Week 8-9**: Testing (E1-E4)
- **Week 9-10**: Documentation (F1-F3)

Total: **10 weeks**
