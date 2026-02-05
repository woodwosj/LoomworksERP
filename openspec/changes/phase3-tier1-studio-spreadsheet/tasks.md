# Tasks: Phase 3 Tier 1 - Studio and Spreadsheet (Core Fork Edition)

This task list is organized by the two-layer architecture: **Core Modifications** (changes to forked Odoo) and **Addon Development** (loomworks_addons modules).

---

## Section A: Core Modifications (Odoo Fork)

These tasks modify the forked Odoo source code to enable deep Studio and Spreadsheet integration.

### A1. Core View System - Studio Edit Mode

- [ ] A1.1 Create `odoo/addons/web/static/src/studio/` directory structure
- [ ] A1.2 Implement `studio_service.js` - Core Studio service for view editing
- [ ] A1.3 Create `field_palette/field_palette.js` - Drag-drop field type palette component
- [ ] A1.4 Create `field_palette/field_palette.xml` - Owl template for field palette
- [ ] A1.5 Create `field_palette/field_palette.scss` - Styles for field palette
- [ ] A1.6 Create `form_overlay/studio_form_overlay.js` - Form view edit overlay
- [ ] A1.7 Create `list_editor/studio_column_editor.js` - List column customization
- [ ] A1.8 Create `drop_zone/studio_drop_zone.js` - Generic drop zone component
- [ ] A1.9 Add Studio service to web module asset bundle (`__manifest__.py`)

### A2. Core View Controllers - Studio Integration

- [ ] A2.1 Modify `odoo/addons/web/static/src/views/view.js` - Add Studio state and toggle
- [ ] A2.2 Modify `odoo/addons/web/static/src/views/form/form_controller.js` - Add Studio overlay
- [ ] A2.3 Modify `odoo/addons/web/static/src/views/form/form_controller.xml` - Add Studio toggle button
- [ ] A2.4 Modify `odoo/addons/web/static/src/views/list/list_controller.js` - Add column editor
- [ ] A2.5 Modify `odoo/addons/web/static/src/views/list/list_controller.xml` - Add Studio toggle
- [ ] A2.6 Modify `odoo/addons/web/static/src/views/kanban/kanban_controller.js` - Add Studio mode
- [ ] A2.7 Modify `odoo/addons/web/static/src/views/kanban/kanban_controller.xml` - Add Studio toggle
- [ ] A2.8 Create common Studio mixin for view controllers
- [ ] A2.9 Add CSS classes for Studio edit mode visual feedback

### A3. Core Python - ir.ui.view Extensions

- [ ] A3.1 Modify `odoo/odoo/addons/base/models/ir_ui_view.py` - Add `studio_customized` field
- [ ] A3.2 Add `studio_customization_id` Many2one field to ir.ui.view
- [ ] A3.3 Add `studio_arch_backup` field for original arch storage
- [ ] A3.4 Implement `_studio_backup_arch()` method
- [ ] A3.5 Implement `_studio_restore_arch()` method
- [ ] A3.6 Implement `_apply_studio_customizations()` hook in view processing
- [ ] A3.7 Add `spreadsheet` to view type Selection field
- [ ] A3.8 Implement `_get_view_info()` override for spreadsheet icon
- [ ] A3.9 Write unit tests for ir.ui.view Studio extensions

### A4. Core Python - ir.model Extensions

- [ ] A4.1 Modify `odoo/odoo/addons/base/models/ir_model.py` - Add `studio_app_id` field
- [ ] A4.2 Add `studio_origin` computed field (odoo/studio/customized)
- [ ] A4.3 Add `studio_icon`, `studio_color`, `studio_description` fields
- [ ] A4.4 Implement `_studio_create_model()` method with validation
- [ ] A4.5 Implement `_studio_create_field()` method with type handling
- [ ] A4.6 Implement `_studio_create_default_views()` method
- [ ] A4.7 Implement `_studio_generate_form_arch()` helper
- [ ] A4.8 Implement `_studio_generate_list_arch()` helper
- [ ] A4.9 Implement `_studio_generate_kanban_arch()` helper
- [ ] A4.10 Implement `_studio_generate_search_arch()` helper
- [ ] A4.11 Implement `_studio_create_menu()` method
- [ ] A4.12 Add ORM cache clearing after dynamic model creation
- [ ] A4.13 Write unit tests for ir.model Studio extensions

### A5. Core Spreadsheet View Type

- [ ] A5.1 Create `odoo/addons/web/static/src/views/spreadsheet/` directory
- [ ] A5.2 Implement `spreadsheet_view.js` - View registration
- [ ] A5.3 Implement `spreadsheet_controller.js` - View controller
- [ ] A5.4 Implement `spreadsheet_model.js` - Data model
- [ ] A5.5 Implement `spreadsheet_renderer.js` - Rendering logic
- [ ] A5.6 Implement `spreadsheet_arch_parser.js` - XML arch parser
- [ ] A5.7 Create `spreadsheet_view.xml` - Owl template
- [ ] A5.8 Create `spreadsheet_view.scss` - Styles
- [ ] A5.9 Add spreadsheet view to web module asset bundle
- [ ] A5.10 Modify `odoo/odoo/addons/base/models/ir_actions.py` - Support spreadsheet in view_mode

---

## Section B: loomworks_studio Addon

Business logic and UI components built on core modifications.

### B1. Module Scaffolding

- [ ] B1.1 Create `loomworks_studio/` module directory structure
- [ ] B1.2 Create `__manifest__.py` with dependencies on `base`, `web`, `mail`
- [ ] B1.3 Create `__init__.py` importing models, controllers
- [ ] B1.4 Create security groups: `group_studio_user`, `group_studio_admin`
- [ ] B1.5 Create `ir.model.access.csv` for all Studio models

### B2. Studio App Model

- [ ] B2.1 Implement `studio.app` model with name, technical_name, icon, color
- [ ] B2.2 Add state field (draft/published/archived) with transitions
- [ ] B2.3 Add computed fields: model_count, record_count
- [ ] B2.4 Implement `action_create_model()` delegating to core ir.model
- [ ] B2.5 Implement `action_publish()`, `action_archive()`, `action_unarchive()`
- [ ] B2.6 Add constraint validation for technical_name format
- [ ] B2.7 Create form view for studio.app
- [ ] B2.8 Create list/kanban views for studio.app
- [ ] B2.9 Write unit tests for studio.app

### B3. View Customization Model

- [ ] B3.1 Implement `studio.view.customization` model
- [ ] B3.2 Add model_name, view_type, base_view_id, generated_view_id fields
- [ ] B3.3 Implement `add_field_to_view()` API method
- [ ] B3.4 Implement `add_list_column()` API method
- [ ] B3.5 Implement `remove_list_column()` API method
- [ ] B3.6 Implement `reorder_list_columns()` API method
- [ ] B3.7 Implement `_generate_view()` to create/update ir.ui.view
- [ ] B3.8 Implement `_build_form_arch()` XML generator
- [ ] B3.9 Implement `_build_list_arch()` XML generator
- [ ] B3.10 Implement `_build_kanban_arch()` XML generator
- [ ] B3.11 Implement `_apply_to_arch()` for runtime customization
- [ ] B3.12 Write unit tests for view customization

### B4. View Field Model

- [ ] B4.1 Implement `studio.view.field` model
- [ ] B4.2 Add field_id, sequence, group_name, widget, readonly, required fields
- [ ] B4.3 Add invisible_domain, custom_label, placeholder fields
- [ ] B4.4 Add column field for form layout positioning
- [ ] B4.5 Write unit tests for field placement

### B5. Automation Engine

- [ ] B5.1 Implement `studio.automation` model with triggers
- [ ] B5.2 Add trigger_field_ids, filter_domain, filter_pre_domain fields
- [ ] B5.3 Implement `studio.automation.action` model
- [ ] B5.4 Implement `update_record` action type
- [ ] B5.5 Implement `create_record` action type
- [ ] B5.6 Implement `send_email` action type with mail.template
- [ ] B5.7 Implement `send_notification` action type
- [ ] B5.8 Implement `execute_code` action type with RestrictedPython sandbox
- [ ] B5.9 Implement `call_webhook` action type
- [ ] B5.10 Implement automation-to-base.automation conversion
- [ ] B5.11 Add loop detection and execution limits
- [ ] B5.12 Add audit logging for automation executions
- [ ] B5.13 Create form view for automation builder
- [ ] B5.14 Write unit tests for automation engine

### B6. Studio Frontend Components (Owl)

- [ ] B6.1 Create `app_wizard/` - New app creation wizard
- [ ] B6.2 Create `model_wizard/` - New model creation wizard
- [ ] B6.3 Create `field_config_dialog/` - Field property editor
- [ ] B6.4 Create `automation_builder/` - Visual automation rule builder
- [ ] B6.5 Create `view_switcher/` - Switch between view types in editor
- [ ] B6.6 Create Studio toolbar component with common actions
- [ ] B6.7 Add SCSS styles matching Loomworks theme
- [ ] B6.8 Add XML templates for all components
- [ ] B6.9 Register components in asset bundle

### B7. Studio Views and Menus

- [ ] B7.1 Create Studio main menu with icon
- [ ] B7.2 Create "My Apps" submenu showing studio.app records
- [ ] B7.3 Create "Customizations" submenu for view customizations
- [ ] B7.4 Create "Automations" submenu for automation rules
- [ ] B7.5 Create client action for Studio editor interface
- [ ] B7.6 Add "Open in Studio" action to all form/list/kanban views

### B8. Studio REST API

- [ ] B8.1 Create `controllers/studio_controller.py`
- [ ] B8.2 Implement `/studio/app/<id>/create_model` endpoint
- [ ] B8.3 Implement `/studio/model/<id>/add_field` endpoint
- [ ] B8.4 Implement `/studio/view/customize` endpoint
- [ ] B8.5 Implement `/studio/automation/test` endpoint
- [ ] B8.6 Add authentication and access control to endpoints

---

## Section C: loomworks_spreadsheet Addon

Spreadsheet document management and Univer integration.

### C1. Module Scaffolding

- [ ] C1.1 Create `loomworks_spreadsheet/` module directory structure
- [ ] C1.2 Create `__manifest__.py` with dependencies
- [ ] C1.3 Set up npm package.json for Univer dependencies
- [ ] C1.4 Configure asset bundling for Univer TypeScript/JavaScript
- [ ] C1.5 Create security groups and `ir.model.access.csv`

### C2. Spreadsheet Document Model

- [ ] C2.1 Implement `spreadsheet.document` model
- [ ] C2.2 Add name, description, data (JSON), thumbnail fields
- [ ] C2.3 Add owner_id, shared_user_ids, share_mode fields
- [ ] C2.4 Add folder_id, tag_ids for organization
- [ ] C2.5 Add version, last_modified for change tracking
- [ ] C2.6 Implement `_get_empty_spreadsheet()` default data
- [ ] C2.7 Inherit mail.thread for document chatter
- [ ] C2.8 Create form/list/kanban views for documents
- [ ] C2.9 Write unit tests for document CRUD

### C3. Data Source Model

- [ ] C3.1 Implement `spreadsheet.data.source` model
- [ ] C3.2 Add source_type (model/pivot/list/chart) field
- [ ] C3.3 Add model_id, domain, field_ids configuration
- [ ] C3.4 Add group_by_ids, measure_ids for aggregation
- [ ] C3.5 Add target_sheet, target_cell placement fields
- [ ] C3.6 Add auto_refresh, last_refresh tracking
- [ ] C3.7 Implement `fetch_data()` method
- [ ] C3.8 Implement `_fetch_model_data()` for raw queries
- [ ] C3.9 Implement `_fetch_pivot_data()` using read_group
- [ ] C3.10 Add pagination support for large datasets
- [ ] C3.11 Write unit tests for data fetching

### C4. Pivot Model

- [ ] C4.1 Implement `spreadsheet.pivot` model
- [ ] C4.2 Add model_id, domain configuration
- [ ] C4.3 Implement `spreadsheet.pivot.dimension` for row/col groups
- [ ] C4.4 Add date_granularity (day/week/month/quarter/year)
- [ ] C4.5 Implement `spreadsheet.pivot.measure` for aggregations
- [ ] C4.6 Add aggregation field (sum/avg/min/max/count/count_distinct)
- [ ] C4.7 Implement `compute_pivot()` method
- [ ] C4.8 Implement `_format_pivot_results()` helper
- [ ] C4.9 Add row/column totals computation
- [ ] C4.10 Write unit tests for pivot computation

### C5. Chart Model

- [ ] C5.1 Implement `spreadsheet.chart` model
- [ ] C5.2 Add chart_type (bar/line/pie/area/scatter/combo)
- [ ] C5.3 Add data_source_id or data_range configuration
- [ ] C5.4 Add title, stacked, show_legend, show_labels options
- [ ] C5.5 Add axes_config JSON field
- [ ] C5.6 Add position (sheet, x, y, width, height) fields
- [ ] C5.7 Write unit tests for chart configuration

### C6. Univer Integration

- [ ] C6.1 Create `static/src/univer/` directory
- [ ] C6.2 Implement `univer_wrapper.js` - Owl component wrapping Univer
- [ ] C6.3 Implement Univer initialization with core plugins
- [ ] C6.4 Implement document loading and serialization
- [ ] C6.5 Set up auto-save with debouncing
- [ ] C6.6 Configure Univer theme to match Loomworks branding
- [ ] C6.7 Implement `getSnapshot()` and `loadDocument()` methods
- [ ] C6.8 Create `univer_wrapper.xml` Owl template
- [ ] C6.9 Create `univer_wrapper.scss` styles

### C7. Odoo Data Plugin

- [ ] C7.1 Implement `odoo_data_plugin.js` extending Univer Plugin
- [ ] C7.2 Register `ODOO.DATA()` formula function
- [ ] C7.3 Register `ODOO.PIVOT()` formula function
- [ ] C7.4 Register `ODOO.PIVOT.HEADER()` formula function
- [ ] C7.5 Register `ODOO.FIELD()` formula function
- [ ] C7.6 Implement `insertDataSource()` method
- [ ] C7.7 Implement `insertTableData()` method
- [ ] C7.8 Implement `cellRefToCoords()` utility
- [ ] C7.9 Add data refresh functionality
- [ ] C7.10 Handle relational field formatting

### C8. Pivot Plugin

- [ ] C8.1 Implement `pivot_plugin.js` extending Univer Plugin
- [ ] C8.2 Implement pivot table rendering from Odoo data
- [ ] C8.3 Add row/column grouping support
- [ ] C8.4 Add measure aggregation (sum, avg, min, max, count)
- [ ] C8.5 Implement row and column totals
- [ ] C8.6 Add date granularity grouping

### C9. Chart Plugin

- [ ] C9.1 Implement `chart_plugin.js` extending Univer Plugin
- [ ] C9.2 Implement bar chart creation
- [ ] C9.3 Implement line chart creation
- [ ] C9.4 Implement pie chart creation
- [ ] C9.5 Implement area chart creation
- [ ] C9.6 Implement scatter plot creation
- [ ] C9.7 Implement combo chart creation
- [ ] C9.8 Add stacked chart option
- [ ] C9.9 Configure Loomworks color palette

### C10. Spreadsheet Frontend Components

- [ ] C10.1 Create `spreadsheet_action/` - Client action component
- [ ] C10.2 Create `data_source_dialog/` - Data source selector
- [ ] C10.3 Create `model_selector/` - Odoo model picker
- [ ] C10.4 Create `field_selector/` - Multi-field picker
- [ ] C10.5 Create `domain_builder/` - Domain filter builder
- [ ] C10.6 Create `pivot_config_dialog/` - Pivot configuration
- [ ] C10.7 Create `chart_config_dialog/` - Chart configuration
- [ ] C10.8 Add toolbar with "Insert Odoo Data", "Create Pivot", "Insert Chart"

### C11. Spreadsheet Views and Menus

- [ ] C11.1 Create Spreadsheet main menu
- [ ] C11.2 Create document list/kanban views
- [ ] C11.3 Create client action for spreadsheet editor
- [ ] C11.4 Add "New Spreadsheet" action
- [ ] C11.5 Add "Open as Spreadsheet" option to pivot/graph views

### C12. Spreadsheet REST API

- [ ] C12.1 Create `controllers/spreadsheet_controller.py`
- [ ] C12.2 Implement `/spreadsheet/document/<id>` CRUD endpoints
- [ ] C12.3 Implement `/spreadsheet/data/<source_id>` endpoint
- [ ] C12.4 Implement `/spreadsheet/pivot/<pivot_id>` endpoint
- [ ] C12.5 Implement `/spreadsheet/save` auto-save endpoint
- [ ] C12.6 Add authentication and access control

---

## Section D: AI Agent Integration (MCP Tools)

### D1. Studio MCP Tools

- [ ] D1.1 Create MCP tool `studio_create_app` - Create new Studio app
- [ ] D1.2 Create MCP tool `studio_add_model` - Add model to app
- [ ] D1.3 Create MCP tool `studio_add_field` - Add field to model
- [ ] D1.4 Create MCP tool `studio_customize_view` - Modify view layout
- [ ] D1.5 Create MCP tool `studio_add_automation` - Create automation rule
- [ ] D1.6 Create MCP tool `studio_list_apps` - List available apps
- [ ] D1.7 Create MCP tool `studio_get_model_fields` - Get model schema
- [ ] D1.8 Add tool documentation and examples

### D2. Spreadsheet MCP Tools

- [ ] D2.1 Create MCP tool `spreadsheet_create` - Create new spreadsheet
- [ ] D2.2 Create MCP tool `spreadsheet_add_data_source` - Connect Odoo data
- [ ] D2.3 Create MCP tool `spreadsheet_create_pivot` - Add pivot table
- [ ] D2.4 Create MCP tool `spreadsheet_create_chart` - Add chart
- [ ] D2.5 Create MCP tool `spreadsheet_get_data` - Read spreadsheet data
- [ ] D2.6 Create MCP tool `spreadsheet_update_cell` - Modify cell value
- [ ] D2.7 Create MCP tool `spreadsheet_export` - Export to XLSX/CSV
- [ ] D2.8 Add tool documentation and examples

---

## Section E: Testing

### E1. Core Modification Tests

- [ ] E1.1 Unit tests for Studio service JavaScript
- [ ] E1.2 Unit tests for field palette component
- [ ] E1.3 Unit tests for ir.ui.view Studio extensions
- [ ] E1.4 Unit tests for ir.model Studio extensions
- [ ] E1.5 Unit tests for spreadsheet view type
- [ ] E1.6 Integration tests for core view Studio toggle

### E2. Studio Addon Tests

- [ ] E2.1 Unit tests for studio.app model creation
- [ ] E2.2 Unit tests for dynamic model creation
- [ ] E2.3 Unit tests for dynamic field creation (all types)
- [ ] E2.4 Unit tests for view generation (form, list, kanban)
- [ ] E2.5 Unit tests for automation execution
- [ ] E2.6 Unit tests for automation loop detection
- [ ] E2.7 Integration tests for Studio end-to-end flow
- [ ] E2.8 JavaScript tests for Owl components

### E3. Spreadsheet Addon Tests

- [ ] E3.1 Unit tests for spreadsheet.document CRUD
- [ ] E3.2 Unit tests for data source fetching
- [ ] E3.3 Unit tests for pivot computation
- [ ] E3.4 Unit tests for chart configuration
- [ ] E3.5 Integration tests for Univer initialization
- [ ] E3.6 Integration tests for ODOO.DATA formula
- [ ] E3.7 Performance tests for large dataset handling (10k+ rows)
- [ ] E3.8 JavaScript tests for Univer plugins

### E4. MCP Tool Tests

- [ ] E4.1 Unit tests for Studio MCP tools
- [ ] E4.2 Unit tests for Spreadsheet MCP tools
- [ ] E4.3 Integration tests with AI agent

---

## Section F: Documentation

### F1. Developer Documentation

- [ ] F1.1 Document core modification architecture
- [ ] F1.2 Document Studio service API
- [ ] F1.3 Document view customization patterns
- [ ] F1.4 Document spreadsheet view integration
- [ ] F1.5 Document Univer plugin development

### F2. User Documentation

- [ ] F2.1 Write Studio user guide
- [ ] F2.2 Write Spreadsheet user guide
- [ ] F2.3 Document AI agent tools for customization
- [ ] F2.4 Create video tutorials for common workflows

### F3. Maintenance Documentation

- [ ] F3.1 Document all core file modifications with line references
- [ ] F3.2 Create upgrade guide for future Odoo versions
- [ ] F3.3 Document rollback procedures

---

## Task Dependencies

```
A1 (Core Studio) -> A2 (Controllers) -> B6 (Studio UI)
A3 (ir.ui.view) -> B3 (Customization) -> B6 (Studio UI)
A4 (ir.model) -> B2 (Studio App) -> D1 (MCP Tools)
A5 (Spreadsheet View) -> C6 (Univer) -> C7-C9 (Plugins)
B1 (Scaffolding) -> B2-B5 (Models) -> B6-B7 (UI)
C1 (Scaffolding) -> C2-C5 (Models) -> C6-C9 (Univer)
B (Studio Complete) + C (Spreadsheet Complete) -> D (MCP) -> E (Testing) -> F (Docs)
```

## Priority Order

1. **Week 1-2**: A1-A4 (Core modifications)
2. **Week 2-3**: A5, B1-B3 (Spreadsheet view, Studio scaffolding)
3. **Week 3-4**: B4-B5, C1-C3 (Studio models, Spreadsheet models)
4. **Week 4-5**: B6-B8, C4-C5 (Studio UI, Spreadsheet models)
5. **Week 5-6**: C6-C9 (Univer integration)
6. **Week 6-7**: C10-C12 (Spreadsheet UI)
7. **Week 7-8**: D1-D2 (MCP tools)
8. **Week 8-9**: E1-E4 (Testing)
9. **Week 9-10**: F1-F3 (Documentation)
