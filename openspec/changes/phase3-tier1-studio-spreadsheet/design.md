# Design: Phase 3 Tier 1 - Studio and Spreadsheet Modules

## Context

Loomworks ERP aims to eliminate developer labor by enabling AI-driven customization. Phase 3 Tier 1 delivers two critical modules:

1. **loomworks_studio**: No-code application builder for creating and customizing apps
2. **loomworks_spreadsheet**: Excel-like BI interface with Odoo data integration

Both modules must be developed independently (LGPL v3 compatible) without copying Odoo Enterprise code. Odoo Enterprise features serve only as a reference for functionality.

### Stakeholders

- End users (business users who customize without coding)
- AI agents (programmatic customization via MCP tools)
- System administrators (managing custom apps and permissions)

### Constraints

- **Legal**: LGPL v3 only, no Enterprise code copying
- **Technical**: Must work with Odoo Community v18 APIs
- **Performance**: View rendering < 1 second, field creation < 3 seconds
- **Security**: Respect Odoo's access control, sandbox custom code execution

### Runtime Requirements

| Component | Version | Notes |
|-----------|---------|-------|
| **Node.js** | >= 20.0.0 (LTS) | Required for Univer spreadsheet library (requires >= 18.17.0) and frontend asset bundling. Node.js 20 LTS recommended for production (EOL: April 2026). Node.js 22 LTS also supported. |
| **npm** | >= 9.0.0 | Package management |
| **Python** | >= 3.10 | Odoo v18 requirement |
| **PostgreSQL** | >= 15 | Required for WAL features |

**Rationale for Node.js 20+:**
- Univer spreadsheet library requires Node.js >= 18.17.0
- Node.js 18 LTS reached end-of-life on April 30, 2025
- Node.js 20 LTS provides security updates until April 2026
- Node.js 22 LTS is the current active LTS version

---

## Goals / Non-Goals

### Goals

- Enable creation of custom models with `x_` prefix via UI
- Provide drag-and-drop field addition to any model
- Support all standard Odoo view types in the builder
- Integrate spreadsheets with live Odoo data sources
- Deliver pivot tables that query any model dynamically
- Support chart creation from spreadsheet data and pivots

### Non-Goals

- Full code editor (Python/JavaScript) in browser
- Mobile app builder (native iOS/Android)
- Complex workflow designer (use `loomworks_ai` skills instead)
- Excel macro/VBA compatibility
- Offline spreadsheet editing (online-first approach)

---

## Part 1: loomworks_studio - Technical Design

### 1.1 Architecture Overview

```
loomworks_studio/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── studio_app.py           # Custom app definitions
│   ├── studio_field.py         # Field configuration
│   ├── studio_view.py          # View customizations
│   ├── studio_automation.py    # Workflow rules
│   └── studio_report.py        # Report templates
├── views/
│   ├── studio_app_views.xml
│   ├── studio_menus.xml
│   └── studio_templates.xml
├── security/
│   ├── ir.model.access.csv
│   └── security.xml
├── static/src/
│   ├── components/
│   │   ├── studio_sidebar/     # Left panel with tools
│   │   ├── field_palette/      # Draggable field types
│   │   ├── view_editor/        # View customization canvas
│   │   └── automation_builder/ # Workflow configuration
│   ├── scss/
│   │   └── studio.scss
│   └── xml/
│       └── studio_templates.xml
├── data/
│   └── studio_data.xml
└── tests/
    └── test_studio.py
```

### 1.2 Data Models

#### studio.app - Custom Application Registry

```python
class StudioApp(models.Model):
    _name = 'studio.app'
    _description = 'Studio Custom Application'

    name = fields.Char(required=True)
    technical_name = fields.Char(
        required=True,
        help="Technical name used for model prefix (x_[name]_)"
    )
    icon = fields.Char(default='fa-cube')
    color = fields.Integer(default=0)
    description = fields.Text()

    # Related components
    model_ids = fields.One2many('ir.model', 'studio_app_id')
    menu_id = fields.Many2one('ir.ui.menu')
    action_id = fields.Many2one('ir.actions.act_window')

    # State management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived')
    ], default='draft')

    # Audit
    created_by_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    published_date = fields.Datetime()
```

#### Extension to ir.model

```python
class IrModel(models.Model):
    _inherit = 'ir.model'

    studio_app_id = fields.Many2one('studio.app', string='Studio App')
    studio_origin = fields.Selection([
        ('odoo', 'Odoo Core'),
        ('studio', 'Studio Created'),
        ('customized', 'Studio Customized')
    ], default='odoo', compute='_compute_studio_origin', store=True)

    @api.depends('state', 'studio_app_id')
    def _compute_studio_origin(self):
        for model in self:
            if model.studio_app_id:
                model.studio_origin = 'studio'
            elif model.state == 'manual':
                model.studio_origin = 'customized'
            else:
                model.studio_origin = 'odoo'
```

#### studio.view.customization - View Modifications

```python
class StudioViewCustomization(models.Model):
    _name = 'studio.view.customization'
    _description = 'Studio View Customization'

    name = fields.Char(required=True)
    model_id = fields.Many2one('ir.model', required=True, ondelete='cascade')
    view_type = fields.Selection([
        ('form', 'Form'),
        ('list', 'List'),
        ('kanban', 'Kanban'),
        ('calendar', 'Calendar'),
        ('pivot', 'Pivot'),
        ('graph', 'Graph'),
        ('search', 'Search')
    ], required=True)

    # Original view reference (if customizing existing)
    base_view_id = fields.Many2one('ir.ui.view')

    # Generated view
    generated_view_id = fields.Many2one('ir.ui.view', readonly=True)

    # Customization storage (JSON structure)
    arch_json = fields.Text(
        help="JSON representation of view architecture for UI editing"
    )

    # Field layout for form/list views
    field_ids = fields.One2many(
        'studio.view.field', 'customization_id',
        string='Fields'
    )

    active = fields.Boolean(default=True)
```

#### studio.view.field - Field Placement in Views

```python
class StudioViewField(models.Model):
    _name = 'studio.view.field'
    _description = 'Field in Studio View'
    _order = 'sequence'

    customization_id = fields.Many2one(
        'studio.view.customization',
        required=True,
        ondelete='cascade'
    )
    field_id = fields.Many2one('ir.model.fields', required=True)
    sequence = fields.Integer(default=10)

    # Positioning
    group_name = fields.Char(help="Group/notebook page name")
    column = fields.Integer(default=0, help="Column in form layout (0 or 1)")

    # Display options
    widget = fields.Char()
    readonly = fields.Boolean()
    required = fields.Boolean()
    invisible_domain = fields.Char(help="Domain for conditional visibility")

    # Label customization
    custom_label = fields.Char()
    placeholder = fields.Char()
```

#### studio.automation - Workflow Rules

```python
class StudioAutomation(models.Model):
    _name = 'studio.automation'
    _description = 'Studio Automation Rule'

    name = fields.Char(required=True)
    model_id = fields.Many2one('ir.model', required=True, ondelete='cascade')
    active = fields.Boolean(default=True)

    # Trigger configuration
    trigger = fields.Selection([
        ('on_create', 'On Creation'),
        ('on_write', 'On Update'),
        ('on_create_or_write', 'On Creation & Update'),
        ('on_unlink', 'On Deletion'),
        ('on_state_set', 'On State Change'),
        ('on_time', 'Based on Time Condition'),
        ('on_tag_set', 'On Tag Addition'),
        ('on_user_set', 'On User Assignment')
    ], required=True)

    trigger_field_ids = fields.Many2many(
        'ir.model.fields',
        string='Trigger Fields',
        help="Fields that trigger the automation when changed"
    )

    # Filter condition
    filter_domain = fields.Char(default='[]')
    filter_pre_domain = fields.Char(
        default='[]',
        help="Domain to check before the change"
    )

    # Actions to execute
    action_ids = fields.One2many('studio.automation.action', 'automation_id')

    # Generated base.automation record
    base_automation_id = fields.Many2one('base.automation', readonly=True)
```

#### studio.automation.action - Action Steps

```python
class StudioAutomationAction(models.Model):
    _name = 'studio.automation.action'
    _description = 'Automation Action Step'
    _order = 'sequence'

    automation_id = fields.Many2one(
        'studio.automation',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(default=10)

    action_type = fields.Selection([
        ('update_record', 'Update Record'),
        ('create_record', 'Create New Record'),
        ('send_email', 'Send Email'),
        ('send_notification', 'Add Activity/Notification'),
        ('execute_code', 'Execute Python Code'),
        ('call_webhook', 'Call Webhook')
    ], required=True)

    # For update_record
    field_updates = fields.Text(help="JSON: {field_name: value_expression}")

    # For create_record
    target_model_id = fields.Many2one('ir.model')
    record_values = fields.Text(help="JSON: {field_name: value_expression}")

    # For send_email
    email_template_id = fields.Many2one('mail.template')

    # For execute_code (sandboxed)
    code = fields.Text()

    # For call_webhook
    webhook_url = fields.Char()
    webhook_method = fields.Selection([
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT')
    ], default='POST')
```

### 1.3 Dynamic Model/Field Creation

Using Odoo's built-in `ir.model` and `ir.model.fields` APIs:

```python
class StudioApp(models.Model):
    _inherit = 'studio.app'

    def action_create_model(self, model_name, model_label, fields_config):
        """Create a new custom model for this studio app.

        Args:
            model_name: Technical name (will be prefixed with x_)
            model_label: Human-readable name
            fields_config: List of field definitions

        Returns:
            Created ir.model record
        """
        self.ensure_one()

        # Validate model name
        technical_name = f"x_{self.technical_name}_{model_name}"
        if not technical_name.replace('_', '').replace('.', '').isalnum():
            raise ValidationError(_("Invalid model name"))

        # Create the model
        IrModel = self.env['ir.model'].sudo()
        model = IrModel.create({
            'name': model_label,
            'model': technical_name,
            'state': 'manual',
            'studio_app_id': self.id,
        })

        # Create fields
        for field_def in fields_config:
            self._create_field(model, field_def)

        return model

    def _create_field(self, model, field_def):
        """Create a field on a model.

        Args:
            model: ir.model record
            field_def: Dict with name, type, label, etc.
        """
        IrModelFields = self.env['ir.model.fields'].sudo()

        field_name = f"x_{field_def['name']}"
        ttype = field_def.get('type', 'char')

        vals = {
            'model_id': model.id,
            'name': field_name,
            'field_description': field_def.get('label', field_def['name']),
            'ttype': ttype,
            'state': 'manual',
            'required': field_def.get('required', False),
            'index': field_def.get('index', False),
        }

        # Type-specific attributes
        if ttype == 'selection':
            vals['selection'] = str(field_def.get('selection', []))
        elif ttype in ('many2one', 'one2many', 'many2many'):
            vals['relation'] = field_def.get('relation')
            if ttype == 'one2many':
                vals['relation_field'] = field_def.get('relation_field')
        elif ttype in ('char', 'text'):
            vals['size'] = field_def.get('size', 0)

        return IrModelFields.create(vals)
```

### 1.4 View Generation

Dynamic view generation from customization records:

```python
class StudioViewCustomization(models.Model):
    _inherit = 'studio.view.customization'

    def generate_view(self):
        """Generate ir.ui.view from customization settings."""
        self.ensure_one()

        # Build view architecture
        arch = self._build_arch()

        view_vals = {
            'name': f"studio.{self.model_id.model}.{self.view_type}",
            'model': self.model_id.model,
            'type': self.view_type,
            'arch': arch,
            'priority': 99,  # Lower priority to override defaults
        }

        if self.base_view_id:
            # Create as inherited view
            view_vals['inherit_id'] = self.base_view_id.id

        if self.generated_view_id:
            self.generated_view_id.write(view_vals)
        else:
            view = self.env['ir.ui.view'].sudo().create(view_vals)
            self.generated_view_id = view

        return self.generated_view_id

    def _build_arch(self):
        """Build XML architecture based on view type."""
        if self.view_type == 'form':
            return self._build_form_arch()
        elif self.view_type == 'list':
            return self._build_list_arch()
        elif self.view_type == 'kanban':
            return self._build_kanban_arch()
        # ... other view types

    def _build_form_arch(self):
        """Generate form view XML."""
        root = etree.Element('form')
        sheet = etree.SubElement(root, 'sheet')

        # Group fields by group_name
        grouped = defaultdict(list)
        for field in self.field_ids.sorted('sequence'):
            grouped[field.group_name or ''].append(field)

        # Build groups
        for group_name, fields in grouped.items():
            group = etree.SubElement(sheet, 'group')
            if group_name:
                group.set('string', group_name)

            for field_rec in fields:
                field_el = etree.SubElement(group, 'field')
                field_el.set('name', field_rec.field_id.name)

                if field_rec.widget:
                    field_el.set('widget', field_rec.widget)
                if field_rec.readonly:
                    field_el.set('readonly', '1')
                if field_rec.required:
                    field_el.set('required', '1')
                if field_rec.invisible_domain:
                    field_el.set('invisible', field_rec.invisible_domain)
                if field_rec.custom_label:
                    field_el.set('string', field_rec.custom_label)

        return etree.tostring(root, encoding='unicode', pretty_print=True)
```

### 1.5 Supported Field Types

| Field Type | Odoo ttype | Widget Options | Notes |
|------------|-----------|----------------|-------|
| Text | char | default, email, url, phone | Single line |
| Long Text | text | default, html | Multi-line |
| Number | integer, float | default, monetary | Configurable decimals |
| Date | date | default | Date picker |
| DateTime | datetime | default | Date + time picker |
| Boolean | boolean | default, toggle | Checkbox or toggle |
| Selection | selection | default, radio, badge | Dropdown or radio |
| Many2one | many2one | default | Link to another record |
| One2many | one2many | default, kanban | List of related records |
| Many2many | many2many | default, tags | Multiple links |
| Binary | binary | default, image | File upload |
| Image | binary | image | Image with preview |
| Monetary | monetary | default | Currency-aware |

### 1.6 Frontend Components (Owl)

```javascript
// static/src/components/studio_sidebar/studio_sidebar.js
/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class StudioSidebar extends Component {
    static template = "loomworks_studio.StudioSidebar";
    static props = {
        modelId: Number,
        viewType: String,
        onFieldAdd: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            fieldTypes: this.getFieldTypes(),
            existingFields: [],
            newFieldOpen: false,
        });
        this.loadExistingFields();
    }

    getFieldTypes() {
        return [
            { type: 'char', label: 'Text', icon: 'fa-font' },
            { type: 'text', label: 'Long Text', icon: 'fa-align-left' },
            { type: 'integer', label: 'Number', icon: 'fa-hashtag' },
            { type: 'float', label: 'Decimal', icon: 'fa-percent' },
            { type: 'boolean', label: 'Checkbox', icon: 'fa-check-square' },
            { type: 'date', label: 'Date', icon: 'fa-calendar' },
            { type: 'datetime', label: 'Date & Time', icon: 'fa-clock' },
            { type: 'selection', label: 'Dropdown', icon: 'fa-list' },
            { type: 'many2one', label: 'Link', icon: 'fa-link' },
            { type: 'binary', label: 'File', icon: 'fa-file' },
        ];
    }

    async loadExistingFields() {
        const fields = await this.orm.searchRead(
            'ir.model.fields',
            [['model_id', '=', this.props.modelId]],
            ['name', 'field_description', 'ttype']
        );
        this.state.existingFields = fields;
    }

    onDragStart(ev, fieldType) {
        ev.dataTransfer.setData('fieldType', fieldType.type);
        ev.dataTransfer.effectAllowed = 'copy';
    }

    onExistingFieldDrag(ev, field) {
        ev.dataTransfer.setData('existingField', JSON.stringify(field));
        ev.dataTransfer.effectAllowed = 'copy';
    }
}
```

---

## Part 2: loomworks_spreadsheet - Technical Design

### 2.1 Library Selection: Univer

**Recommendation: Univer** (Apache-2.0 License)

| Criteria | Univer | Handsontable | SheetJS |
|----------|--------|--------------|---------|
| License | Apache-2.0 | Dual (free/commercial) | Various |
| UI Component | Full spreadsheet UI | Data grid focus | Headless only |
| Formula Engine | Built-in, 400+ functions | Via HyperFormula | Read/write only |
| Charts | Planned/plugins | Limited | None |
| Pivot Tables | Supported | Plugin (paid) | None |
| TypeScript | Native | Yes | Yes |
| Collaboration | Built-in CRDT | Requires implementation | N/A |
| Active Development | Yes (Luckysheet successor) | Yes | Yes |
| Odoo Integration | Clean start | Clean start | Read/write only |

**Rationale:**
1. **Apache-2.0 license** is LGPL v3 compatible
2. **Full spreadsheet UI** out of the box (unlike SheetJS which is headless)
3. **Native collaboration support** aligns with Odoo's multi-user needs
4. **Active development** as the successor to Luckysheet
5. **TypeScript-first** matches modern development practices

### 2.2 Architecture Overview

```
loomworks_spreadsheet/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── spreadsheet_document.py    # Document storage
│   ├── spreadsheet_data_source.py # Odoo data connections
│   ├── spreadsheet_pivot.py       # Pivot configurations
│   └── spreadsheet_chart.py       # Chart definitions
├── views/
│   ├── spreadsheet_views.xml
│   ├── spreadsheet_menus.xml
│   └── spreadsheet_templates.xml
├── security/
│   ├── ir.model.access.csv
│   └── security.xml
├── controllers/
│   └── spreadsheet_controller.py  # REST API for data
├── static/src/
│   ├── spreadsheet/               # Univer integration
│   │   ├── SpreadsheetComponent.js
│   │   ├── OdooDataPlugin.js      # Odoo data source plugin
│   │   ├── PivotPlugin.js         # Dynamic pivot plugin
│   │   └── ChartPlugin.js         # Chart visualization
│   ├── components/
│   │   ├── spreadsheet_action/    # Owl action wrapper
│   │   └── data_source_dialog/    # Data source selector
│   ├── scss/
│   │   └── spreadsheet.scss
│   └── xml/
│       └── spreadsheet_templates.xml
├── data/
│   └── spreadsheet_data.xml
└── tests/
    └── test_spreadsheet.py
```

### 2.3 Data Models

#### spreadsheet.document - Document Storage

```python
class SpreadsheetDocument(models.Model):
    _name = 'spreadsheet.document'
    _description = 'Spreadsheet Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True)
    description = fields.Text()

    # Document content (Univer JSON format)
    data = fields.Text(
        help="JSON serialization of spreadsheet state"
    )

    # Thumbnail for preview
    thumbnail = fields.Binary(attachment=True)

    # Data sources connected to this spreadsheet
    data_source_ids = fields.One2many(
        'spreadsheet.data.source',
        'document_id'
    )

    # Ownership and sharing
    owner_id = fields.Many2one(
        'res.users',
        default=lambda self: self.env.user,
        required=True
    )
    shared_user_ids = fields.Many2many('res.users', string='Shared With')
    share_mode = fields.Selection([
        ('private', 'Private'),
        ('readonly', 'Read Only'),
        ('edit', 'Can Edit')
    ], default='private')

    # Folder organization
    folder_id = fields.Many2one('documents.folder')
    tag_ids = fields.Many2many('documents.tag')

    # Versioning
    version = fields.Integer(default=1)
    last_modified = fields.Datetime(
        default=fields.Datetime.now,
        readonly=True
    )

    @api.model
    def create(self, vals):
        if 'data' not in vals:
            vals['data'] = self._get_empty_spreadsheet()
        return super().create(vals)

    def _get_empty_spreadsheet(self):
        """Return JSON for empty Univer spreadsheet."""
        return json.dumps({
            "id": str(uuid.uuid4()),
            "name": self.name or "Untitled",
            "sheets": [{
                "id": "sheet1",
                "name": "Sheet 1",
                "rowCount": 100,
                "columnCount": 26,
                "cellData": {}
            }]
        })
```

#### spreadsheet.data.source - Odoo Data Connection

```python
class SpreadsheetDataSource(models.Model):
    _name = 'spreadsheet.data.source'
    _description = 'Spreadsheet Data Source'

    name = fields.Char(required=True)
    document_id = fields.Many2one(
        'spreadsheet.document',
        required=True,
        ondelete='cascade'
    )

    source_type = fields.Selection([
        ('model', 'Odoo Model'),
        ('pivot', 'Pivot Table'),
        ('list', 'List View'),
        ('chart', 'Chart')
    ], required=True, default='model')

    # Model configuration
    model_id = fields.Many2one('ir.model')
    domain = fields.Char(default='[]')
    field_ids = fields.Many2many(
        'ir.model.fields',
        string='Fields to Include'
    )

    # Grouping (for pivot/chart)
    group_by_ids = fields.Many2many(
        'ir.model.fields',
        relation='spreadsheet_source_groupby_rel',
        string='Group By'
    )
    measure_ids = fields.Many2many(
        'ir.model.fields',
        relation='spreadsheet_source_measure_rel',
        string='Measures'
    )

    # Spreadsheet placement
    target_sheet = fields.Char(default='Sheet 1')
    target_cell = fields.Char(default='A1', help="Cell reference like A1, B5")

    # Refresh settings
    auto_refresh = fields.Boolean(default=True)
    last_refresh = fields.Datetime()

    def fetch_data(self):
        """Fetch data from Odoo and return in spreadsheet format."""
        self.ensure_one()

        if self.source_type == 'model':
            return self._fetch_model_data()
        elif self.source_type == 'pivot':
            return self._fetch_pivot_data()
        elif self.source_type == 'list':
            return self._fetch_list_data()

    def _fetch_model_data(self):
        """Fetch raw model data."""
        Model = self.env[self.model_id.model]
        domain = safe_eval(self.domain) if self.domain else []

        field_names = self.field_ids.mapped('name') or ['id', 'display_name']
        records = Model.search_read(domain, field_names, limit=10000)

        return {
            'type': 'table',
            'headers': field_names,
            'rows': [[r.get(f) for f in field_names] for r in records]
        }

    def _fetch_pivot_data(self):
        """Fetch aggregated pivot data."""
        Model = self.env[self.model_id.model]
        domain = safe_eval(self.domain) if self.domain else []

        group_fields = self.group_by_ids.mapped('name')
        measure_fields = self.measure_ids.mapped('name')

        # Use Odoo's read_group for aggregation
        results = Model.read_group(
            domain,
            fields=measure_fields,
            groupby=group_fields,
            lazy=False
        )

        return {
            'type': 'pivot',
            'rows': group_fields,
            'measures': measure_fields,
            'data': results
        }
```

#### spreadsheet.chart - Chart Configuration

```python
class SpreadsheetChart(models.Model):
    _name = 'spreadsheet.chart'
    _description = 'Spreadsheet Chart'

    name = fields.Char(required=True)
    document_id = fields.Many2one(
        'spreadsheet.document',
        required=True,
        ondelete='cascade'
    )

    chart_type = fields.Selection([
        ('bar', 'Bar Chart'),
        ('line', 'Line Chart'),
        ('pie', 'Pie Chart'),
        ('area', 'Area Chart'),
        ('scatter', 'Scatter Plot'),
        ('combo', 'Combo Chart')
    ], required=True, default='bar')

    # Data source
    data_source_id = fields.Many2one('spreadsheet.data.source')

    # Or manual range
    data_range = fields.Char(help="Cell range like A1:D10")

    # Chart options
    title = fields.Char()
    stacked = fields.Boolean(default=False)
    show_legend = fields.Boolean(default=True)
    show_labels = fields.Boolean(default=False)

    # Axes configuration (JSON)
    axes_config = fields.Text(default='{}')

    # Position in spreadsheet
    sheet_name = fields.Char()
    position_x = fields.Integer(default=0)
    position_y = fields.Integer(default=0)
    width = fields.Integer(default=600)
    height = fields.Integer(default=400)
```

### 2.4 Univer Integration

```javascript
// static/src/spreadsheet/SpreadsheetComponent.js
/** @odoo-module */

import { Component, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

// Univer imports
import { Univer, LocaleType } from "@univerjs/core";
import { defaultTheme } from "@univerjs/design";
import { UniverSheetsPlugin } from "@univerjs/sheets";
import { UniverSheetsUIPlugin } from "@univerjs/sheets-ui";
import { UniverSheetsFormulaPlugin } from "@univerjs/sheets-formula";

// Custom plugins
import { OdooDataPlugin } from "./OdooDataPlugin";
import { LoomworksPivotPlugin } from "./PivotPlugin";
import { LoomworksChartPlugin } from "./ChartPlugin";

export class SpreadsheetComponent extends Component {
    static template = "loomworks_spreadsheet.SpreadsheetComponent";
    static props = {
        documentId: { type: Number, optional: true },
        data: { type: String, optional: true },
        readonly: { type: Boolean, optional: true },
        onSave: { type: Function, optional: true },
    };

    setup() {
        this.containerRef = useRef("spreadsheetContainer");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.univer = null;
        this.workbook = null;

        onMounted(() => this.initSpreadsheet());
        onWillUnmount(() => this.destroySpreadsheet());
    }

    async initSpreadsheet() {
        // Initialize Univer
        this.univer = new Univer({
            theme: defaultTheme,
            locale: LocaleType.EN_US,
        });

        // Register core plugins
        this.univer.registerPlugin(UniverSheetsPlugin);
        this.univer.registerPlugin(UniverSheetsUIPlugin, {
            container: this.containerRef.el,
        });
        this.univer.registerPlugin(UniverSheetsFormulaPlugin);

        // Register Loomworks custom plugins
        this.univer.registerPlugin(OdooDataPlugin, {
            orm: this.orm,
            documentId: this.props.documentId,
        });
        this.univer.registerPlugin(LoomworksPivotPlugin);
        this.univer.registerPlugin(LoomworksChartPlugin);

        // Load document data
        let data = this.props.data;
        if (this.props.documentId && !data) {
            const doc = await this.orm.read(
                'spreadsheet.document',
                [this.props.documentId],
                ['data']
            );
            data = doc[0]?.data;
        }

        if (data) {
            this.workbook = this.univer.createUniverSheet(JSON.parse(data));
        } else {
            this.workbook = this.univer.createUniverSheet({});
        }

        // Set up auto-save
        if (this.props.documentId && !this.props.readonly) {
            this.setupAutoSave();
        }
    }

    setupAutoSave() {
        // Debounced save on changes
        let saveTimeout;
        this.workbook.onChanged(() => {
            clearTimeout(saveTimeout);
            saveTimeout = setTimeout(() => this.saveDocument(), 2000);
        });
    }

    async saveDocument() {
        if (!this.props.documentId) return;

        const data = JSON.stringify(this.workbook.getSnapshot());
        await this.orm.write(
            'spreadsheet.document',
            [this.props.documentId],
            { data, last_modified: new Date().toISOString() }
        );

        if (this.props.onSave) {
            this.props.onSave();
        }
    }

    destroySpreadsheet() {
        if (this.univer) {
            this.univer.dispose();
        }
    }
}
```

### 2.5 Odoo Data Plugin

```javascript
// static/src/spreadsheet/OdooDataPlugin.js
/** @odoo-module */

import { Plugin } from "@univerjs/core";

export class OdooDataPlugin extends Plugin {
    static pluginName = "OdooDataPlugin";

    constructor(config) {
        super();
        this.orm = config.orm;
        this.documentId = config.documentId;
        this.dataSources = new Map();
    }

    onStarting() {
        // Register custom functions
        this.registerOdooFunctions();

        // Load data sources
        this.loadDataSources();
    }

    registerOdooFunctions() {
        const formulaEngine = this.getUniverSheet().getFormulaEngine();

        // ODOO.DATA(model, domain, fields, row, col)
        formulaEngine.registerFunction('ODOO.DATA', {
            calculate: async (model, domain, fields, row, col) => {
                return this.fetchOdooData(model, domain, fields, row, col);
            },
            description: 'Fetch data from an Odoo model',
        });

        // ODOO.PIVOT(source_id, row_index, measure)
        formulaEngine.registerFunction('ODOO.PIVOT', {
            calculate: async (sourceId, rowIndex, measure) => {
                return this.fetchPivotValue(sourceId, rowIndex, measure);
            },
            description: 'Get value from a pivot table',
        });

        // ODOO.PIVOT.HEADER(source_id, row_index)
        formulaEngine.registerFunction('ODOO.PIVOT.HEADER', {
            calculate: async (sourceId, rowIndex) => {
                return this.fetchPivotHeader(sourceId, rowIndex);
            },
            description: 'Get header from a pivot table',
        });
    }

    async loadDataSources() {
        if (!this.documentId) return;

        const sources = await this.orm.searchRead(
            'spreadsheet.data.source',
            [['document_id', '=', this.documentId]],
            ['id', 'name', 'source_type', 'model_id', 'domain', 'target_cell']
        );

        for (const source of sources) {
            this.dataSources.set(source.id, source);
        }
    }

    async fetchOdooData(model, domain, fields, row, col) {
        try {
            const parsedDomain = typeof domain === 'string'
                ? JSON.parse(domain)
                : domain;
            const fieldList = typeof fields === 'string'
                ? fields.split(',').map(f => f.trim())
                : fields;

            const records = await this.orm.searchRead(
                model,
                parsedDomain,
                fieldList,
                { limit: 1000 }
            );

            if (row !== undefined && col !== undefined) {
                // Return specific cell value
                const record = records[row];
                return record ? record[fieldList[col]] : '';
            }

            return records;
        } catch (error) {
            console.error('ODOO.DATA error:', error);
            return '#ERROR';
        }
    }

    async insertDataSource(config) {
        // Create data source record
        const sourceId = await this.orm.create('spreadsheet.data.source', [{
            name: config.name,
            document_id: this.documentId,
            source_type: config.type,
            model_id: config.modelId,
            domain: JSON.stringify(config.domain || []),
            target_cell: config.targetCell,
        }]);

        // Fetch and insert data
        const data = await this.orm.call(
            'spreadsheet.data.source',
            'fetch_data',
            [sourceId]
        );

        // Insert into spreadsheet
        this.insertTableData(config.targetCell, data);

        return sourceId;
    }

    insertTableData(startCell, data) {
        const sheet = this.getUniverSheet().getActiveSheet();
        const { row, col } = this.cellRefToCoords(startCell);

        // Insert headers
        data.headers.forEach((header, i) => {
            sheet.getCell(row, col + i).setValue(header);
        });

        // Insert rows
        data.rows.forEach((rowData, rowIdx) => {
            rowData.forEach((value, colIdx) => {
                sheet.getCell(row + rowIdx + 1, col + colIdx).setValue(value);
            });
        });
    }

    cellRefToCoords(ref) {
        const match = ref.match(/^([A-Z]+)(\d+)$/);
        if (!match) return { row: 0, col: 0 };

        const col = match[1].split('').reduce(
            (acc, c) => acc * 26 + c.charCodeAt(0) - 64, 0
        ) - 1;
        const row = parseInt(match[2]) - 1;

        return { row, col };
    }
}
```

### 2.6 Pivot Table Implementation

```python
# models/spreadsheet_pivot.py

class SpreadsheetPivot(models.Model):
    _name = 'spreadsheet.pivot'
    _description = 'Spreadsheet Pivot Configuration'

    name = fields.Char(required=True)
    document_id = fields.Many2one(
        'spreadsheet.document',
        required=True,
        ondelete='cascade'
    )

    # Source model
    model_id = fields.Many2one('ir.model', required=True)
    domain = fields.Char(default='[]')

    # Dimensions
    row_group_ids = fields.One2many(
        'spreadsheet.pivot.dimension',
        'pivot_id',
        domain=[('dimension_type', '=', 'row')],
        string='Row Groups'
    )
    col_group_ids = fields.One2many(
        'spreadsheet.pivot.dimension',
        'pivot_id',
        domain=[('dimension_type', '=', 'col')],
        string='Column Groups'
    )

    # Measures
    measure_ids = fields.One2many(
        'spreadsheet.pivot.measure',
        'pivot_id'
    )

    # Display options
    show_row_totals = fields.Boolean(default=True)
    show_col_totals = fields.Boolean(default=True)
    show_grand_total = fields.Boolean(default=True)

    def compute_pivot(self):
        """Compute pivot table data using read_group."""
        self.ensure_one()

        Model = self.env[self.model_id.model]
        domain = safe_eval(self.domain) if self.domain else []

        row_fields = self.row_group_ids.mapped('field_id.name')
        col_fields = self.col_group_ids.mapped('field_id.name')
        measure_specs = [
            f"{m.field_id.name}:{m.aggregation}"
            for m in self.measure_ids
        ]

        # Multi-level grouping
        all_groups = row_fields + col_fields

        results = Model.read_group(
            domain,
            fields=[m.field_id.name for m in self.measure_ids],
            groupby=all_groups,
            lazy=False
        )

        return self._format_pivot_results(results, row_fields, col_fields)

    def _format_pivot_results(self, results, row_fields, col_fields):
        """Format read_group results into pivot structure."""
        pivot_data = {
            'rows': [],
            'cols': [],
            'values': {},
            'row_totals': {},
            'col_totals': {},
            'grand_total': {}
        }

        # Build unique row/col combinations
        row_keys = set()
        col_keys = set()

        for result in results:
            row_key = tuple(result.get(f) for f in row_fields)
            col_key = tuple(result.get(f) for f in col_fields)

            row_keys.add(row_key)
            col_keys.add(col_key)

            # Store values
            key = (row_key, col_key)
            pivot_data['values'][str(key)] = {
                m.field_id.name: result.get(m.field_id.name, 0)
                for m in self.measure_ids
            }

        pivot_data['rows'] = sorted(list(row_keys))
        pivot_data['cols'] = sorted(list(col_keys))

        # Compute totals if enabled
        if self.show_row_totals:
            pivot_data['row_totals'] = self._compute_row_totals(
                pivot_data, row_fields
            )

        if self.show_col_totals:
            pivot_data['col_totals'] = self._compute_col_totals(
                pivot_data, col_fields
            )

        return pivot_data


class SpreadsheetPivotDimension(models.Model):
    _name = 'spreadsheet.pivot.dimension'
    _description = 'Pivot Table Dimension'
    _order = 'sequence'

    pivot_id = fields.Many2one(
        'spreadsheet.pivot',
        required=True,
        ondelete='cascade'
    )
    field_id = fields.Many2one('ir.model.fields', required=True)
    dimension_type = fields.Selection([
        ('row', 'Row'),
        ('col', 'Column')
    ], required=True)
    sequence = fields.Integer(default=10)

    # Date grouping options
    date_granularity = fields.Selection([
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month'),
        ('quarter', 'Quarter'),
        ('year', 'Year')
    ])


class SpreadsheetPivotMeasure(models.Model):
    _name = 'spreadsheet.pivot.measure'
    _description = 'Pivot Table Measure'
    _order = 'sequence'

    pivot_id = fields.Many2one(
        'spreadsheet.pivot',
        required=True,
        ondelete='cascade'
    )
    field_id = fields.Many2one('ir.model.fields', required=True)
    sequence = fields.Integer(default=10)

    aggregation = fields.Selection([
        ('sum', 'Sum'),
        ('avg', 'Average'),
        ('min', 'Minimum'),
        ('max', 'Maximum'),
        ('count', 'Count'),
        ('count_distinct', 'Count Distinct')
    ], default='sum', required=True)

    # Formatting
    format_type = fields.Selection([
        ('number', 'Number'),
        ('percentage', 'Percentage'),
        ('currency', 'Currency')
    ], default='number')
    decimal_places = fields.Integer(default=2)
```

### 2.7 Chart Types and Rendering

| Chart Type | Use Case | Data Requirements |
|------------|----------|-------------------|
| Bar | Category comparison | 1 dimension + 1-3 measures |
| Line | Trends over time | Date dimension + measures |
| Pie | Part-to-whole | 1 dimension + 1 measure |
| Area | Cumulative trends | Date dimension + measures |
| Scatter | Correlation | 2 numeric measures |
| Combo | Mixed visualization | Date + multiple measures |

Chart rendering uses Univer's built-in chart capabilities with custom styling:

```javascript
// static/src/spreadsheet/ChartPlugin.js
/** @odoo-module */

import { Plugin } from "@univerjs/core";

export class LoomworksChartPlugin extends Plugin {
    static pluginName = "LoomworksChartPlugin";

    createChart(config) {
        const chartManager = this.getUniverSheet().getChartManager();

        const chartConfig = {
            type: config.type,
            data: {
                labels: config.labels,
                datasets: config.datasets.map(ds => ({
                    label: ds.label,
                    data: ds.data,
                    backgroundColor: ds.backgroundColor || this.getDefaultColors(),
                    borderColor: ds.borderColor,
                })),
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: !!config.title,
                        text: config.title,
                    },
                    legend: {
                        display: config.showLegend !== false,
                        position: 'bottom',
                    },
                },
                scales: this.getScalesConfig(config),
            },
        };

        return chartManager.addChart(chartConfig, {
            sheet: config.sheetName,
            x: config.x,
            y: config.y,
            width: config.width || 600,
            height: config.height || 400,
        });
    }

    getDefaultColors() {
        // Loomworks brand colors
        return [
            '#4F46E5', // Primary indigo
            '#10B981', // Green
            '#F59E0B', // Amber
            '#EF4444', // Red
            '#8B5CF6', // Purple
            '#06B6D4', // Cyan
        ];
    }

    getScalesConfig(config) {
        if (config.type === 'pie') return {};

        return {
            x: {
                stacked: config.stacked,
                title: {
                    display: !!config.xAxisTitle,
                    text: config.xAxisTitle,
                },
            },
            y: {
                stacked: config.stacked,
                title: {
                    display: !!config.yAxisTitle,
                    text: config.yAxisTitle,
                },
                beginAtZero: true,
            },
        };
    }
}
```

---

## Risks / Trade-offs

### Studio Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Dynamic model creation breaks caching | Medium | High | Clear ORM cache after model creation; document reload requirements |
| Complex view customizations are slow | Low | Medium | Generate views asynchronously; cache generated XML |
| Users create conflicting customizations | Medium | Medium | Version control for customizations; conflict detection |
| Automation rules cause infinite loops | Medium | High | Loop detection; execution limits; audit logging |

### Spreadsheet Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Univer library has breaking changes | Medium | Medium | Pin version; maintain compatibility layer |
| Large datasets cause browser performance issues | High | Medium | Pagination; lazy loading; row/column limits |
| Formula engine differs from Excel | Medium | Low | Document differences; provide compatibility functions |
| Real-time collaboration conflicts | Medium | Medium | Use Univer's CRDT implementation; test extensively |

### Trade-offs Made

1. **Univer over Handsontable**: Better licensing (Apache-2.0) but smaller community
2. **JSON storage over native format**: Simpler but less efficient for large spreadsheets
3. **Server-side pivot computation**: More scalable but requires round-trip for updates
4. **Owl wrapper over native React**: Consistent with Odoo patterns but adds complexity

---

## Migration Plan

### Phase 1: Foundation (Week 1-2)
1. Create module scaffolding for both modules
2. Implement core data models
3. Set up Univer integration with Owl wrapper

### Phase 2: Studio Core (Week 3-4)
1. Implement dynamic model creation
2. Build field palette and drag-drop
3. Create basic view generation (form, list)

### Phase 3: Studio Views (Week 5-6)
1. Add kanban, calendar, pivot, graph view support
2. Implement view customization storage
3. Build automation rule engine

### Phase 4: Spreadsheet Core (Week 7-8)
1. Implement document storage and management
2. Build Odoo data source plugin
3. Create data source selector dialog

### Phase 5: Spreadsheet BI (Week 9-10)
1. Implement pivot table engine
2. Add chart visualization
3. Build formula functions for Odoo data

### Phase 6: Integration & Polish (Week 11-12)
1. AI agent tools for Studio operations
2. AI agent tools for Spreadsheet operations
3. Documentation and testing

### Rollback Strategy

Both modules are additive and do not modify core Odoo code. Rollback consists of:
1. Uninstall the module (preserves data in database)
2. Run `DROP TABLE` for module-specific tables if full cleanup needed
3. Custom models/fields created by Studio remain in `ir.model`/`ir.model.fields`

---

## Open Questions

1. **Collaboration Architecture**: Should real-time collaboration use WebSocket or Odoo's existing bus system?
   - Recommendation: Use Odoo bus for consistency with existing infrastructure

2. **Mobile Support**: Should Studio/Spreadsheet work on mobile devices?
   - Recommendation: Desktop-first for initial release; mobile read-only

3. **Export Formats**: Which export formats beyond XLSX should be supported?
   - Recommendation: CSV, PDF for initial release

4. **Formula Compatibility**: How much Excel formula compatibility is required?
   - Recommendation: Support top 100 most-used Excel functions

5. **AI Integration Depth**: Should AI be able to create entire apps from description?
   - Recommendation: Phase 1 delivers tool-level AI; natural language app creation in Phase 2
