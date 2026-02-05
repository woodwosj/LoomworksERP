# Change: Phase 3 Tier 1 - Studio and Spreadsheet Modules

## Why

Loomworks ERP requires no-code customization capabilities and business intelligence tools to fulfill its AI-first vision. Users must be able to create custom applications and analyze data without developer involvement. These are the **highest priority** Phase 3 modules because:

1. **loomworks_studio** enables users to customize and create apps without developers, directly supporting the core differentiator of eliminating developer labor
2. **loomworks_spreadsheet** provides universal BI capabilities that integrate with AI dashboards and support data-driven decision making

Both modules are essential for the "Free software + AI does all the work" market positioning.

## What Changes

### New Module: loomworks_studio

A no-code application builder enabling users to:
- Create custom applications with drag-and-drop interface
- Add fields to existing models dynamically via `ir.model.fields`
- Customize views (form, list, kanban, calendar, pivot, graph)
- Define automated actions and workflows
- Generate menus and navigation automatically
- Build reports without coding

### New Module: loomworks_spreadsheet

An Excel-like interface with BI capabilities:
- Full spreadsheet functionality with formulas
- Integration with Odoo data sources (live data)
- Dynamic pivot tables connected to any model
- Chart visualization (bar, line, pie, area, scatter)
- Document storage and sharing
- Real-time collaboration support

### Key Technical Decisions

1. **Studio**: Uses Odoo's native `ir.model` and `ir.model.fields` APIs for dynamic model/field creation with `state='manual'` and `x_` prefix convention
2. **Spreadsheet**: Recommends **Univer** as the spreadsheet library (successor to Luckysheet, Apache-2.0 license, TypeScript-based, actively maintained)
3. **CRITICAL**: All implementations are from scratch - no code copying from Odoo Enterprise

## Impact

- **Affected specs**: None (new capabilities)
- **Affected code**:
  - New module `loomworks_addons/loomworks_studio/`
  - New module `loomworks_addons/loomworks_spreadsheet/`
- **Dependencies**:
  - Odoo Community v18 core (`base`, `web`)
  - Univer spreadsheet library (`@univerjs/core`, `@univerjs/sheets`, `@univerjs/ui`)
- **Database changes**: New models for storing studio apps, view configurations, spreadsheet documents
- **Integration points**: AI agent tools for no-code operations, dashboard system for BI
