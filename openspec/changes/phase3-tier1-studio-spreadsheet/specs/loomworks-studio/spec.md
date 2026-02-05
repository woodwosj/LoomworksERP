# Specification: loomworks_studio

No-code application builder enabling users to create and customize Odoo applications without developer involvement.

## ADDED Requirements

### Requirement: Custom Application Creation

The system SHALL allow users to create custom applications through a visual interface without writing code.

Each custom application MUST have:
- A unique technical name (prefixed with `x_`)
- A display name and optional description
- An icon and color for visual identification
- At least one custom model
- Auto-generated menu entries and actions

#### Scenario: User creates a new custom application

- **GIVEN** a user with Studio access permissions
- **WHEN** the user opens Studio and clicks "New App"
- **AND** enters app name "Equipment Tracker" and selects an icon
- **THEN** the system creates a `studio.app` record
- **AND** generates a root menu item for the application
- **AND** displays the app builder interface for model creation

#### Scenario: Custom app appears in main menu

- **GIVEN** a published custom application "Equipment Tracker"
- **WHEN** a user with access permissions logs into Odoo
- **THEN** the user sees "Equipment Tracker" in the main application menu
- **AND** clicking it opens the default view of the primary model

---

### Requirement: Dynamic Model Creation

The system SHALL allow users to create new database models (tables) at runtime through the UI.

Custom models MUST:
- Use the `x_` prefix convention (e.g., `x_equipment_tracker_asset`)
- Have `state='manual'` in `ir.model`
- Include standard fields (id, create_date, write_date, create_uid, write_uid)
- Support all standard Odoo field types

#### Scenario: User creates a model for tracking assets

- **GIVEN** a user editing the "Equipment Tracker" app in Studio
- **WHEN** the user clicks "Add Model" and enters name "Asset"
- **THEN** the system creates `ir.model` with model name `x_equipment_tracker_asset`
- **AND** the model is immediately available for field addition
- **AND** the ORM cache is cleared to recognize the new model

#### Scenario: Model name validation prevents invalid names

- **GIVEN** a user creating a new model in Studio
- **WHEN** the user enters a name containing special characters like "Asset@123"
- **THEN** the system displays a validation error
- **AND** prevents model creation until a valid name is provided

---

### Requirement: Dynamic Field Creation

The system SHALL allow users to add fields to any model (custom or standard) through a drag-and-drop interface.

Supported field types MUST include:
- Text (char) with optional email, URL, phone widgets
- Long Text (text) with optional HTML widget
- Number (integer, float) with optional monetary widget
- Date and DateTime
- Boolean (checkbox, toggle)
- Selection (dropdown, radio, badge)
- Many2one (link to another record)
- One2many (list of related records)
- Many2many (multiple links, tags)
- Binary (file upload, image)

#### Scenario: User adds a text field by drag-and-drop

- **GIVEN** a user editing a model in Studio
- **WHEN** the user drags "Text" from the field palette to the form
- **AND** enters field label "Serial Number" and marks it as required
- **THEN** the system creates `ir.model.fields` with `name='x_serial_number'` and `ttype='char'`
- **AND** the field appears immediately in the form view

#### Scenario: User adds a relation field linking to products

- **GIVEN** a user editing the Asset model in Studio
- **WHEN** the user drags "Link" field type and selects "Product" as target model
- **AND** enters label "Product"
- **THEN** the system creates a Many2one field `x_product_id` relating to `product.product`
- **AND** the field displays as a dropdown/autocomplete in forms

#### Scenario: User adds a selection field with custom options

- **GIVEN** a user editing the Asset model in Studio
- **WHEN** the user drags "Dropdown" and adds options "Active", "Maintenance", "Retired"
- **THEN** the system creates a selection field with the specified options
- **AND** the field renders as a dropdown in form view

---

### Requirement: View Customization

The system SHALL allow users to customize how data is displayed in various view types.

Supported view types MUST include:
- Form view (record detail with field groups)
- List view (table with sortable columns)
- Kanban view (card-based with grouping)
- Calendar view (date-based)
- Pivot view (aggregated data table)
- Graph view (charts and visualizations)
- Search view (filters and groupings)

#### Scenario: User rearranges form layout

- **GIVEN** a model with multiple fields in Studio
- **WHEN** the user opens form view customization
- **AND** drags fields to rearrange their order and grouping
- **THEN** the system updates `studio.view.customization` with new layout
- **AND** regenerates the `ir.ui.view` XML
- **AND** changes are visible immediately upon form reload

#### Scenario: User creates a kanban view grouped by status

- **GIVEN** a model with a selection field "Status"
- **WHEN** the user adds a kanban view and sets "Status" as the grouping field
- **AND** configures which fields appear on the kanban card
- **THEN** the system generates a kanban view with columns for each status value
- **AND** users can drag cards between columns to change status

#### Scenario: User makes a field conditionally visible

- **GIVEN** a form view with fields "Type" (selection) and "Warranty Expiry" (date)
- **WHEN** the user configures "Warranty Expiry" to be visible only when Type is "Equipment"
- **THEN** the system adds `invisible="type != 'equipment'"` to the field element
- **AND** the field shows/hides dynamically based on Type value

---

### Requirement: Automation Rules

The system SHALL allow users to create automated actions triggered by record events.

Supported triggers MUST include:
- On record creation
- On record update
- On record deletion
- On state/status change
- On time condition (scheduled)
- On user assignment
- On tag addition

Supported actions MUST include:
- Update the current record
- Create a new record in any model
- Send an email using a template
- Create an activity or notification
- Execute Python code (sandboxed)
- Call an external webhook

#### Scenario: Auto-assign owner when asset is created

- **GIVEN** an automation rule configured for the Asset model
- **WHEN** the rule trigger is set to "On Creation"
- **AND** the action is "Update Record" setting owner_id to current user
- **THEN** every new Asset record automatically has owner_id set to the creator

#### Scenario: Send notification when maintenance is due

- **GIVEN** an automation rule with time-based trigger
- **WHEN** configured to trigger when "Next Maintenance Date" equals today
- **AND** action is "Send Email" to the asset owner
- **THEN** owners receive daily notifications for assets due for maintenance

#### Scenario: Prevent infinite automation loops

- **GIVEN** an automation that updates a field which triggers another automation
- **WHEN** the second automation would update a field triggering the first
- **THEN** the system detects the potential loop
- **AND** stops execution after a configurable maximum depth (default: 5)
- **AND** logs a warning about the recursion

---

### Requirement: Menu and Navigation Generation

The system SHALL automatically generate menu entries and navigation actions for custom applications.

Menu structure MUST include:
- Root menu entry with app icon and name
- Submenu for each model in the application
- Actions linking menus to default views

#### Scenario: Publishing app creates complete navigation

- **GIVEN** a draft custom app with two models: Asset and Maintenance Log
- **WHEN** the user publishes the application
- **THEN** the system creates:
  - Root menu "Equipment Tracker" with configured icon
  - Submenu "Assets" opening Asset list view
  - Submenu "Maintenance Logs" opening Maintenance Log list view
  - Window actions for each model with form and list views

#### Scenario: Menu sequence follows model order

- **GIVEN** a custom app with models ordered: Asset (1), Category (2), Maintenance (3)
- **WHEN** the app is published
- **THEN** submenus appear in the same sequence order
- **AND** users can reorder via Studio interface

---

### Requirement: Access Control for Studio

The system SHALL enforce role-based access control for Studio features.

Access levels MUST include:
- **Studio User**: Can customize views and add fields to allowed models
- **Studio Manager**: Can create apps, models, and automation rules
- **Studio Admin**: Full access including security settings

#### Scenario: Regular user cannot create new models

- **GIVEN** a user with "Studio User" group only
- **WHEN** the user opens Studio
- **THEN** the "New App" and "Add Model" buttons are hidden or disabled
- **AND** the user can only modify views and fields on existing models they have access to

#### Scenario: Studio Manager can create but not delete published apps

- **GIVEN** a user with "Studio Manager" group
- **WHEN** the user attempts to delete a published application
- **THEN** the system requires confirmation and audit logging
- **OR** restricts deletion to "Studio Admin" only

---

### Requirement: Studio Change Audit Trail

The system SHALL log all Studio modifications for compliance and debugging.

Logged events MUST include:
- Model creation/modification/deletion
- Field creation/modification/deletion
- View customization changes
- Automation rule changes
- App publication/archival

#### Scenario: Field addition is logged

- **GIVEN** a user adds a new field to a model via Studio
- **WHEN** the operation completes
- **THEN** the system creates an audit log entry with:
  - User who made the change
  - Timestamp
  - Model affected
  - Field details (name, type)
  - Before/after state (for modifications)

#### Scenario: Audit logs are queryable

- **GIVEN** multiple Studio changes over time
- **WHEN** an administrator views the Studio audit log
- **THEN** they can filter by date range, user, model, and change type
- **AND** export the log to CSV for compliance reporting

---

### Requirement: Export and Import Studio Customizations

The system SHALL support exporting and importing Studio customizations for migration and backup.

Export format MUST include:
- Custom models and fields as XML data files
- View customizations as XML views
- Automation rules as XML records
- All in standard Odoo data file format

#### Scenario: Export customizations for backup

- **GIVEN** a custom application with models, views, and automations
- **WHEN** the user clicks "Export" in Studio
- **THEN** the system generates a ZIP file containing:
  - `models.xml` with ir.model and ir.model.fields records
  - `views.xml` with ir.ui.view records
  - `automations.xml` with base.automation and ir.actions.server records
  - `menus.xml` with ir.ui.menu and ir.actions.act_window records

#### Scenario: Import customizations to another database

- **GIVEN** an exported customization ZIP file
- **WHEN** an administrator imports it into a new database
- **THEN** the system creates all models, fields, views, and automations
- **AND** validates that target models for relations exist
- **AND** reports any import errors clearly
