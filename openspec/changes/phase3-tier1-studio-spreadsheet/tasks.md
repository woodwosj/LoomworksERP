# Tasks: Phase 3 Tier 1 - Studio and Spreadsheet Modules

## 1. Module Scaffolding

- [ ] 1.1 Create `loomworks_studio` module structure with `__manifest__.py`
- [ ] 1.2 Create `loomworks_spreadsheet` module structure with `__manifest__.py`
- [ ] 1.3 Set up npm package.json for Univer dependencies
- [ ] 1.4 Configure asset bundling for TypeScript/JavaScript
- [ ] 1.5 Create security groups and base access rights

## 2. Studio Data Models

- [ ] 2.1 Implement `studio.app` model for custom application registry
- [ ] 2.2 Extend `ir.model` with `studio_app_id` and `studio_origin` fields
- [ ] 2.3 Implement `studio.view.customization` model for view modifications
- [ ] 2.4 Implement `studio.view.field` model for field placement tracking
- [ ] 2.5 Implement `studio.automation` model for workflow rules
- [ ] 2.6 Implement `studio.automation.action` model for action steps
- [ ] 2.7 Create `ir.model.access.csv` for all Studio models

## 3. Studio Dynamic Model/Field Creation

- [ ] 3.1 Implement `action_create_model()` method on `studio.app`
- [ ] 3.2 Implement `_create_field()` helper for dynamic field creation
- [ ] 3.3 Add validation for model and field names (x_ prefix enforcement)
- [ ] 3.4 Implement ORM cache clearing after model creation
- [ ] 3.5 Add unit tests for dynamic model creation
- [ ] 3.6 Add unit tests for all field types creation

## 4. Studio View Generation

- [ ] 4.1 Implement `generate_view()` method on `studio.view.customization`
- [ ] 4.2 Implement `_build_form_arch()` for form view generation
- [ ] 4.3 Implement `_build_list_arch()` for list view generation
- [ ] 4.4 Implement `_build_kanban_arch()` for kanban view generation
- [ ] 4.5 Implement `_build_calendar_arch()` for calendar view generation
- [ ] 4.6 Implement `_build_pivot_arch()` for pivot view generation
- [ ] 4.7 Implement `_build_graph_arch()` for graph view generation
- [ ] 4.8 Implement `_build_search_arch()` for search view generation
- [ ] 4.9 Add menu and action auto-generation for custom apps

## 5. Studio Automation Engine

- [ ] 5.1 Implement automation rule to `base.automation` conversion
- [ ] 5.2 Implement `update_record` action type
- [ ] 5.3 Implement `create_record` action type
- [ ] 5.4 Implement `send_email` action type with mail.template
- [ ] 5.5 Implement `send_notification` action type
- [ ] 5.6 Implement `execute_code` action type with sandbox
- [ ] 5.7 Implement `call_webhook` action type
- [ ] 5.8 Add loop detection for automation rules
- [ ] 5.9 Add execution limits and audit logging

## 6. Studio Frontend (Owl Components)

- [ ] 6.1 Create `StudioSidebar` component with field type palette
- [ ] 6.2 Create `FieldPalette` component with drag-and-drop
- [ ] 6.3 Create `ViewEditor` canvas component
- [ ] 6.4 Create `FormEditor` specific component
- [ ] 6.5 Create `ListEditor` specific component
- [ ] 6.6 Create `FieldConfigDialog` for field properties
- [ ] 6.7 Create `AutomationBuilder` component
- [ ] 6.8 Create `NewAppWizard` component
- [ ] 6.9 Implement drop zones and visual feedback
- [ ] 6.10 Add SCSS styles matching Loomworks theme

## 7. Studio Views and Menus

- [ ] 7.1 Create form/tree views for `studio.app`
- [ ] 7.2 Create form view for `studio.view.customization`
- [ ] 7.3 Create form view for `studio.automation`
- [ ] 7.4 Create Studio main menu and submenu structure
- [ ] 7.5 Create client action for Studio editor interface

## 8. Spreadsheet Data Models

- [ ] 8.1 Implement `spreadsheet.document` model with JSON storage
- [ ] 8.2 Implement `spreadsheet.data.source` model for Odoo connections
- [ ] 8.3 Implement `spreadsheet.pivot` model for pivot configuration
- [ ] 8.4 Implement `spreadsheet.pivot.dimension` model
- [ ] 8.5 Implement `spreadsheet.pivot.measure` model
- [ ] 8.6 Implement `spreadsheet.chart` model for chart configuration
- [ ] 8.7 Create `ir.model.access.csv` for all Spreadsheet models

## 9. Spreadsheet Data Fetching

- [ ] 9.1 Implement `fetch_data()` method on `spreadsheet.data.source`
- [ ] 9.2 Implement `_fetch_model_data()` for raw data queries
- [ ] 9.3 Implement `_fetch_pivot_data()` using read_group
- [ ] 9.4 Implement `_fetch_list_data()` for list views
- [ ] 9.5 Implement `compute_pivot()` on `spreadsheet.pivot`
- [ ] 9.6 Add pagination support for large datasets
- [ ] 9.7 Add caching layer for frequently accessed data

## 10. Spreadsheet REST API

- [ ] 10.1 Create `spreadsheet_controller.py` with CRUD endpoints
- [ ] 10.2 Implement `/spreadsheet/data/<source_id>` endpoint
- [ ] 10.3 Implement `/spreadsheet/pivot/<pivot_id>` endpoint
- [ ] 10.4 Implement `/spreadsheet/save` endpoint with auto-save
- [ ] 10.5 Add authentication and access control to endpoints

## 11. Univer Integration

- [ ] 11.1 Set up Univer package imports and initialization
- [ ] 11.2 Create `SpreadsheetComponent` Owl wrapper
- [ ] 11.3 Implement Univer instance lifecycle management
- [ ] 11.4 Implement document loading and serialization
- [ ] 11.5 Set up auto-save with debouncing
- [ ] 11.6 Configure Univer theme to match Loomworks branding

## 12. Odoo Data Plugin

- [ ] 12.1 Create `OdooDataPlugin` for Univer
- [ ] 12.2 Register `ODOO.DATA()` formula function
- [ ] 12.3 Register `ODOO.PIVOT()` formula function
- [ ] 12.4 Register `ODOO.PIVOT.HEADER()` formula function
- [ ] 12.5 Implement `insertDataSource()` method
- [ ] 12.6 Implement `insertTableData()` method
- [ ] 12.7 Add data refresh functionality

## 13. Pivot Plugin

- [ ] 13.1 Create `LoomworksPivotPlugin` for Univer
- [ ] 13.2 Implement pivot table rendering from Odoo data
- [ ] 13.3 Add row/column grouping support
- [ ] 13.4 Add measure aggregation (sum, avg, min, max, count)
- [ ] 13.5 Implement row and column totals
- [ ] 13.6 Add date granularity grouping (day, week, month, quarter, year)

## 14. Chart Plugin

- [ ] 14.1 Create `LoomworksChartPlugin` for Univer
- [ ] 14.2 Implement bar chart creation
- [ ] 14.3 Implement line chart creation
- [ ] 14.4 Implement pie chart creation
- [ ] 14.5 Implement area chart creation
- [ ] 14.6 Implement scatter plot creation
- [ ] 14.7 Implement combo chart creation
- [ ] 14.8 Add stacked chart option
- [ ] 14.9 Configure Loomworks color palette

## 15. Spreadsheet Frontend Components

- [ ] 15.1 Create `DataSourceDialog` for data source selection
- [ ] 15.2 Create `ModelSelector` component
- [ ] 15.3 Create `FieldSelector` component
- [ ] 15.4 Create `DomainBuilder` component
- [ ] 15.5 Create `PivotConfigDialog` component
- [ ] 15.6 Create `ChartConfigDialog` component
- [ ] 15.7 Create spreadsheet document list/kanban views

## 16. Spreadsheet Views and Menus

- [ ] 16.1 Create form/tree views for `spreadsheet.document`
- [ ] 16.2 Create client action for spreadsheet editor
- [ ] 16.3 Create Spreadsheet main menu
- [ ] 16.4 Add "Insert Odoo Data" menu item to spreadsheet toolbar
- [ ] 16.5 Add "Create Pivot" menu item to spreadsheet toolbar
- [ ] 16.6 Add "Insert Chart" menu item to spreadsheet toolbar

## 17. AI Agent Integration

- [ ] 17.1 Create MCP tool `studio_create_app` for AI agent
- [ ] 17.2 Create MCP tool `studio_add_field` for AI agent
- [ ] 17.3 Create MCP tool `studio_customize_view` for AI agent
- [ ] 17.4 Create MCP tool `studio_create_automation` for AI agent
- [ ] 17.5 Create MCP tool `spreadsheet_create` for AI agent
- [ ] 17.6 Create MCP tool `spreadsheet_add_data_source` for AI agent
- [ ] 17.7 Create MCP tool `spreadsheet_create_pivot` for AI agent
- [ ] 17.8 Create MCP tool `spreadsheet_create_chart` for AI agent

## 18. Testing

- [ ] 18.1 Unit tests for Studio model creation
- [ ] 18.2 Unit tests for Studio field creation (all types)
- [ ] 18.3 Unit tests for Studio view generation
- [ ] 18.4 Unit tests for Studio automation execution
- [ ] 18.5 Unit tests for Spreadsheet document CRUD
- [ ] 18.6 Unit tests for Spreadsheet data source fetching
- [ ] 18.7 Unit tests for Spreadsheet pivot computation
- [ ] 18.8 Integration tests for Studio end-to-end flow
- [ ] 18.9 Integration tests for Spreadsheet end-to-end flow
- [ ] 18.10 Performance tests for large dataset handling

## 19. Documentation

- [ ] 19.1 Write Studio user documentation
- [ ] 19.2 Write Spreadsheet user documentation
- [ ] 19.3 Write developer API documentation for Studio
- [ ] 19.4 Write developer API documentation for Spreadsheet
- [ ] 19.5 Document AI agent tools and usage examples
- [ ] 19.6 Create video tutorials for common workflows
