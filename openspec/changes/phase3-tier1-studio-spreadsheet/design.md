# Design: Phase 3 Tier 1 - Studio and Spreadsheet (Core Fork Edition)

## Context

Loomworks ERP is a **fully forked** Odoo Community v18 codebase (LGPL v3). This changes our implementation strategy fundamentally: rather than building Studio and Spreadsheet as pure addons that work around Odoo's limitations, we can modify the core view system directly to provide deep, seamless integration.

This design document supersedes the previous addon-only approach and describes how to leverage core modifications alongside addon code for maximum capability.

### Stakeholders

- End users (business users who customize without coding)
- AI agents (programmatic customization via MCP tools)
- System administrators (managing custom apps and permissions)
- Developers (maintaining the forked codebase)

### Constraints

- **Legal**: LGPL v3 only, no Odoo Enterprise code copying
- **Technical**: Core modifications must be maintainable and well-documented
- **Upgrade Path**: Changes should be isolated enough to facilitate upstream merges
- **Performance**: View rendering < 1 second, field creation < 3 seconds
- **Security**: Respect Odoo's access control, sandbox custom code execution

### Runtime Requirements

| Component | Version | Notes |
|-----------|---------|-------|
| **Node.js** | >= 20.0.0 (LTS) | Required for Univer spreadsheet library |
| **npm** | >= 9.0.0 | Package management |
| **Python** | >= 3.10 | Odoo v18 requirement |
| **PostgreSQL** | >= 15 | Required for WAL features |

---

## Architecture Strategy: Core vs Addon

### Core Modifications (Fork Changes)

These modifications live in the forked Odoo source code itself:

| Area | Files | Purpose |
|------|-------|---------|
| **View Edit Mode** | `odoo/addons/web/static/src/views/` | Add Studio toggle to all view types |
| **Field Palette** | `odoo/addons/web/static/src/core/` | Drag-drop field insertion framework |
| **Spreadsheet View Type** | `odoo/addons/web/static/src/views/spreadsheet/` | New core view type |
| **Dynamic Model Registry** | `odoo/odoo/models.py` | Enhanced runtime model registration |
| **View Customization Storage** | `odoo/odoo/addons/base/models/ir_ui_view.py` | Studio customization persistence |
| **Model Extension Support** | `odoo/odoo/addons/base/models/ir_model.py` | Enhanced dynamic field support |

### Addon Code (loomworks_addons)

Business logic and configuration that builds on core modifications:

| Module | Purpose |
|--------|---------|
| **loomworks_studio** | Studio app registry, automation engine, MCP tools |
| **loomworks_spreadsheet** | Document management, data sources, pivot/chart config |

---

## Part 1: Core View System Enhancements

### 1.1 Studio Edit Mode in Core Views

Every Odoo view (form, list, kanban, etc.) will have a built-in Studio toggle. This is implemented at the core level for seamless integration.

**Modified File: `odoo/addons/web/static/src/views/view.js`**

```javascript
// Core view base class enhancement
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class View extends Component {
    setup() {
        super.setup();
        this.studioService = useService("studio");
        this.studioState = useState({
            editMode: false,
            selectedField: null,
            hoveredElement: null,
        });
    }

    toggleStudioMode() {
        if (!this.studioService.hasAccess()) return;
        this.studioState.editMode = !this.studioState.editMode;
        if (this.studioState.editMode) {
            this.studioService.enterEditMode(this.props.resModel, this.props.type);
        } else {
            this.studioService.exitEditMode();
        }
    }

    get showStudioToggle() {
        return this.studioService.hasAccess() && !this.props.disableStudio;
    }
}
```

**Modified File: `odoo/addons/web/static/src/views/form/form_controller.js`**

```javascript
import { FormController as BaseFormController } from "./form_controller_base";
import { StudioFormOverlay } from "@web/studio/form_overlay";

export class FormController extends BaseFormController {
    static components = {
        ...BaseFormController.components,
        StudioFormOverlay,
    };

    static template = "web.FormView"; // Template includes studio overlay

    setup() {
        super.setup();
        this.setupStudioDragDrop();
    }

    setupStudioDragDrop() {
        if (!this.studioState?.editMode) return;

        // Enable drop zones for field palette
        this.dropZones = this.computeDropZones();
    }

    computeDropZones() {
        // Analyze form arch to identify valid drop positions
        const zones = [];
        const arch = this.props.archInfo;
        // Parse groups, notebooks, pages for drop targets
        return zones;
    }

    async onFieldDrop(event, dropZone) {
        const fieldData = JSON.parse(event.dataTransfer.getData("field"));
        await this.studioService.addFieldToView({
            model: this.props.resModel,
            viewType: "form",
            field: fieldData,
            position: dropZone.position,
            afterField: dropZone.afterField,
        });
        // Trigger view reload
        await this.model.load();
    }
}
```

**Modified File: `odoo/addons/web/static/src/views/list/list_controller.js`**

```javascript
import { ListController as BaseListController } from "./list_controller_base";
import { StudioColumnEditor } from "@web/studio/column_editor";

export class ListController extends BaseListController {
    static components = {
        ...BaseListController.components,
        StudioColumnEditor,
    };

    setup() {
        super.setup();
        this.setupColumnCustomization();
    }

    setupColumnCustomization() {
        if (!this.studioState?.editMode) return;
        // Add column resize, reorder, hide handlers
    }

    async onColumnAdd(fieldName, position) {
        await this.studioService.addColumnToList({
            model: this.props.resModel,
            field: fieldName,
            position,
        });
    }

    async onColumnRemove(fieldName) {
        await this.studioService.removeColumnFromList({
            model: this.props.resModel,
            field: fieldName,
        });
    }

    async onColumnReorder(fromIndex, toIndex) {
        await this.studioService.reorderListColumns({
            model: this.props.resModel,
            fromIndex,
            toIndex,
        });
    }
}
```

### 1.2 Studio Service (Core)

**New File: `odoo/addons/web/static/src/studio/studio_service.js`**

```javascript
/** @odoo-module */

import { registry } from "@web/core/registry";

export const studioService = {
    dependencies: ["orm", "user", "notification"],

    start(env, { orm, user, notification }) {
        let currentEditSession = null;

        return {
            hasAccess() {
                // Check if user has studio permission
                return user.hasGroup("loomworks_studio.group_studio_user");
            },

            enterEditMode(resModel, viewType) {
                currentEditSession = {
                    model: resModel,
                    viewType,
                    changes: [],
                    startTime: Date.now(),
                };
                env.bus.trigger("STUDIO:EDIT_MODE_ENTERED", currentEditSession);
            },

            exitEditMode() {
                if (currentEditSession) {
                    env.bus.trigger("STUDIO:EDIT_MODE_EXITED", currentEditSession);
                    currentEditSession = null;
                }
            },

            async addFieldToView({ model, viewType, field, position, afterField }) {
                // Create or get field on model
                const fieldId = await this._ensureField(model, field);

                // Update view arch
                await orm.call("studio.view.customization", "add_field_to_view", [], {
                    model,
                    view_type: viewType,
                    field_id: fieldId,
                    position,
                    after_field: afterField,
                });

                notification.add("Field added successfully", { type: "success" });
            },

            async _ensureField(model, fieldDef) {
                if (fieldDef.existingFieldId) {
                    return fieldDef.existingFieldId;
                }

                // Create new field via ir.model.fields
                const fieldId = await orm.create("ir.model.fields", [{
                    model_id: fieldDef.modelId,
                    name: `x_${fieldDef.name}`,
                    field_description: fieldDef.label,
                    ttype: fieldDef.type,
                    state: "manual",
                    required: fieldDef.required || false,
                    index: fieldDef.index || false,
                    ...this._getFieldTypeSpecificAttrs(fieldDef),
                }]);

                return fieldId;
            },

            _getFieldTypeSpecificAttrs(fieldDef) {
                const attrs = {};
                switch (fieldDef.type) {
                    case "selection":
                        attrs.selection = JSON.stringify(fieldDef.selection || []);
                        break;
                    case "many2one":
                    case "one2many":
                    case "many2many":
                        attrs.relation = fieldDef.relation;
                        if (fieldDef.type === "one2many") {
                            attrs.relation_field = fieldDef.relationField;
                        }
                        break;
                }
                return attrs;
            },

            async addColumnToList({ model, field, position }) {
                await orm.call("studio.view.customization", "add_list_column", [], {
                    model,
                    field_name: field,
                    position,
                });
            },

            async removeColumnFromList({ model, field }) {
                await orm.call("studio.view.customization", "remove_list_column", [], {
                    model,
                    field_name: field,
                });
            },

            async reorderListColumns({ model, fromIndex, toIndex }) {
                await orm.call("studio.view.customization", "reorder_list_columns", [], {
                    model,
                    from_index: fromIndex,
                    to_index: toIndex,
                });
            },
        };
    },
};

registry.category("services").add("studio", studioService);
```

### 1.3 Field Palette Component (Core)

**New File: `odoo/addons/web/static/src/studio/field_palette/field_palette.js`**

```javascript
/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class FieldPalette extends Component {
    static template = "web.FieldPalette";
    static props = {
        modelId: Number,
        onClose: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            activeTab: "new", // "new" or "existing"
            searchQuery: "",
            fieldTypes: this.getFieldTypes(),
            existingFields: [],
            loading: true,
        });
        this.loadExistingFields();
    }

    getFieldTypes() {
        return [
            { type: "char", label: "Text", icon: "fa-font", description: "Single line text" },
            { type: "text", label: "Long Text", icon: "fa-align-left", description: "Multi-line text" },
            { type: "html", label: "Rich Text", icon: "fa-code", description: "HTML content" },
            { type: "integer", label: "Integer", icon: "fa-hashtag", description: "Whole numbers" },
            { type: "float", label: "Decimal", icon: "fa-percent", description: "Decimal numbers" },
            { type: "monetary", label: "Monetary", icon: "fa-dollar", description: "Currency values" },
            { type: "boolean", label: "Checkbox", icon: "fa-check-square", description: "Yes/No" },
            { type: "date", label: "Date", icon: "fa-calendar", description: "Date picker" },
            { type: "datetime", label: "Date & Time", icon: "fa-clock", description: "Date and time" },
            { type: "selection", label: "Dropdown", icon: "fa-list", description: "Choose from options" },
            { type: "many2one", label: "Link", icon: "fa-link", description: "Link to another record" },
            { type: "one2many", label: "Related List", icon: "fa-list-ul", description: "List of related records" },
            { type: "many2many", label: "Tags", icon: "fa-tags", description: "Multiple links" },
            { type: "binary", label: "File", icon: "fa-file", description: "File attachment" },
            { type: "image", label: "Image", icon: "fa-image", description: "Image with preview" },
        ];
    }

    async loadExistingFields() {
        this.state.loading = true;
        try {
            const fields = await this.orm.searchRead(
                "ir.model.fields",
                [["model_id", "=", this.props.modelId]],
                ["id", "name", "field_description", "ttype", "state"]
            );
            this.state.existingFields = fields;
        } finally {
            this.state.loading = false;
        }
    }

    get filteredFieldTypes() {
        if (!this.state.searchQuery) return this.state.fieldTypes;
        const query = this.state.searchQuery.toLowerCase();
        return this.state.fieldTypes.filter(
            (ft) =>
                ft.label.toLowerCase().includes(query) ||
                ft.description.toLowerCase().includes(query)
        );
    }

    get filteredExistingFields() {
        if (!this.state.searchQuery) return this.state.existingFields;
        const query = this.state.searchQuery.toLowerCase();
        return this.state.existingFields.filter(
            (f) =>
                f.name.toLowerCase().includes(query) ||
                f.field_description.toLowerCase().includes(query)
        );
    }

    onDragStart(ev, data) {
        ev.dataTransfer.setData("field", JSON.stringify(data));
        ev.dataTransfer.effectAllowed = "copy";
        document.body.classList.add("studio-dragging");
    }

    onDragEnd() {
        document.body.classList.remove("studio-dragging");
    }
}
```

### 1.4 View Customization Storage (Core Python)

**Modified File: `odoo/odoo/addons/base/models/ir_ui_view.py`**

```python
# Add to existing ir.ui.view model

class IrUIView(models.Model):
    _inherit = 'ir.ui.view'

    # Studio customization tracking
    studio_customized = fields.Boolean(
        string='Studio Customized',
        default=False,
        help="Indicates this view was modified via Studio"
    )
    studio_customization_id = fields.Many2one(
        'studio.view.customization',
        string='Studio Customization',
        ondelete='set null'
    )
    studio_arch_backup = fields.Text(
        string='Original Arch',
        help="Backup of original arch before Studio modifications"
    )

    def _studio_backup_arch(self):
        """Backup original arch before first Studio modification."""
        for view in self:
            if not view.studio_arch_backup and view.arch:
                view.studio_arch_backup = view.arch

    def _studio_restore_arch(self):
        """Restore original arch, removing all Studio customizations."""
        for view in self:
            if view.studio_arch_backup:
                view.write({
                    'arch': view.studio_arch_backup,
                    'studio_arch_backup': False,
                    'studio_customized': False,
                    'studio_customization_id': False,
                })

    @api.model
    def _apply_studio_customizations(self, model, view_type, arch):
        """Apply Studio customizations to a view arch.

        This method is called during view processing to merge
        Studio modifications into the base view architecture.
        """
        StudioCustomization = self.env['studio.view.customization']
        customization = StudioCustomization.search([
            ('model_name', '=', model),
            ('view_type', '=', view_type),
            ('active', '=', True)
        ], limit=1)

        if not customization:
            return arch

        return customization._apply_to_arch(arch)
```

### 1.5 Enhanced Dynamic Model Support (Core Python)

**Modified File: `odoo/odoo/addons/base/models/ir_model.py`**

```python
# Enhancements to ir.model for Studio integration

class IrModel(models.Model):
    _inherit = 'ir.model'

    # Studio integration fields
    studio_app_id = fields.Many2one(
        'studio.app',
        string='Studio Application',
        ondelete='set null'
    )
    studio_origin = fields.Selection([
        ('odoo', 'Odoo Core'),
        ('studio', 'Studio Created'),
        ('customized', 'Studio Customized')
    ], string='Origin', compute='_compute_studio_origin', store=True)

    # Runtime model metadata
    studio_icon = fields.Char(string='Icon', default='fa-cube')
    studio_color = fields.Integer(string='Color Index', default=0)
    studio_description = fields.Text(string='Description')

    @api.depends('state', 'studio_app_id')
    def _compute_studio_origin(self):
        for model in self:
            if model.studio_app_id:
                model.studio_origin = 'studio'
            elif model.state == 'manual':
                model.studio_origin = 'customized'
            else:
                model.studio_origin = 'odoo'

    def _studio_create_model(self, vals):
        """Create a new model via Studio with enhanced validation.

        Args:
            vals: Dictionary containing:
                - name: Human-readable model name
                - model: Technical name (will be validated/prefixed)
                - studio_app_id: Optional Studio app reference
                - fields: List of field definitions
                - create_menu: Whether to auto-create menu
                - create_views: List of view types to auto-generate

        Returns:
            Created ir.model record
        """
        # Validate and normalize model name
        technical_name = vals.get('model', '')
        if not technical_name.startswith('x_'):
            technical_name = f"x_{technical_name}"

        # Validate technical name format
        if not re.match(r'^x_[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$', technical_name):
            raise ValidationError(_(
                "Invalid model name '%s'. Model names must start with 'x_' "
                "and contain only lowercase letters, numbers, and underscores."
            ) % technical_name)

        # Check for name collision
        if self.search([('model', '=', technical_name)]):
            raise ValidationError(_(
                "A model with technical name '%s' already exists."
            ) % technical_name)

        # Create the model
        model_vals = {
            'name': vals.get('name', technical_name),
            'model': technical_name,
            'state': 'manual',
            'studio_app_id': vals.get('studio_app_id'),
            'studio_icon': vals.get('icon', 'fa-cube'),
            'studio_color': vals.get('color', 0),
            'studio_description': vals.get('description', ''),
        }
        model = self.create(model_vals)

        # Create fields
        for field_def in vals.get('fields', []):
            model._studio_create_field(field_def)

        # Clear ORM cache to recognize new model
        self.pool.setup_models(self._cr)
        self.env.registry.init_models(
            self._cr,
            [technical_name],
            {'module': 'loomworks_studio'}
        )

        # Auto-create views if requested
        create_views = vals.get('create_views', ['form', 'list'])
        if create_views:
            model._studio_create_default_views(create_views)

        # Auto-create menu if requested
        if vals.get('create_menu', True):
            model._studio_create_menu()

        return model

    def _studio_create_field(self, field_def):
        """Create a field on this model via Studio.

        Args:
            field_def: Dictionary with field configuration
        """
        self.ensure_one()
        IrModelFields = self.env['ir.model.fields']

        # Normalize field name
        field_name = field_def.get('name', '')
        if not field_name.startswith('x_'):
            field_name = f"x_{field_name}"

        # Build field values
        vals = {
            'model_id': self.id,
            'name': field_name,
            'field_description': field_def.get('label', field_name),
            'ttype': field_def.get('type', 'char'),
            'state': 'manual',
            'required': field_def.get('required', False),
            'index': field_def.get('index', False),
            'copied': field_def.get('copied', True),
            'help': field_def.get('help', ''),
        }

        # Type-specific attributes
        ttype = vals['ttype']
        if ttype == 'selection':
            vals['selection_ids'] = [
                (0, 0, {'value': opt[0], 'name': opt[1], 'sequence': idx})
                for idx, opt in enumerate(field_def.get('selection', []))
            ]
        elif ttype in ('many2one', 'one2many', 'many2many'):
            vals['relation'] = field_def.get('relation')
            if ttype == 'one2many':
                vals['relation_field'] = field_def.get('relation_field')
            elif ttype == 'many2many':
                # Auto-generate relation table name
                relation = field_def.get('relation', '')
                if relation:
                    vals['relation_table'] = f"x_{self.model.replace('.', '_')}_{relation.replace('.', '_')}_rel"
        elif ttype in ('char', 'text'):
            vals['size'] = field_def.get('size', 0)
        elif ttype == 'float':
            vals['digits'] = field_def.get('digits', (16, 2))
        elif ttype == 'monetary':
            vals['currency_field'] = field_def.get('currency_field', 'currency_id')

        return IrModelFields.create(vals)

    def _studio_create_default_views(self, view_types):
        """Generate default views for a Studio-created model."""
        self.ensure_one()
        IrUIView = self.env['ir.ui.view']

        for view_type in view_types:
            arch = self._studio_generate_view_arch(view_type)
            IrUIView.create({
                'name': f"studio.{self.model}.{view_type}",
                'model': self.model,
                'type': view_type,
                'arch': arch,
                'priority': 16,  # Default priority for Studio views
                'studio_customized': True,
            })

    def _studio_generate_view_arch(self, view_type):
        """Generate view architecture XML for a view type."""
        self.ensure_one()

        # Get all manual fields
        fields = self.field_id.filtered(lambda f: f.state == 'manual')

        if view_type == 'form':
            return self._studio_generate_form_arch(fields)
        elif view_type == 'list':
            return self._studio_generate_list_arch(fields)
        elif view_type == 'kanban':
            return self._studio_generate_kanban_arch(fields)
        elif view_type == 'search':
            return self._studio_generate_search_arch(fields)

        return f"<{view_type}/>"

    def _studio_generate_form_arch(self, fields):
        """Generate form view XML."""
        root = etree.Element('form')
        sheet = etree.SubElement(root, 'sheet')
        group = etree.SubElement(sheet, 'group')

        # Add name field prominently if exists
        name_field = fields.filtered(lambda f: f.name in ('x_name', 'name'))
        if name_field:
            field_el = etree.SubElement(group, 'field')
            field_el.set('name', name_field[0].name)

        # Add other fields in a two-column layout
        left_group = etree.SubElement(group, 'group')
        right_group = etree.SubElement(group, 'group')

        for idx, field in enumerate(fields.filtered(lambda f: f.name not in ('x_name', 'name'))):
            target_group = left_group if idx % 2 == 0 else right_group
            field_el = etree.SubElement(target_group, 'field')
            field_el.set('name', field.name)

        return etree.tostring(root, encoding='unicode', pretty_print=True)

    def _studio_generate_list_arch(self, fields):
        """Generate list view XML."""
        root = etree.Element('list')

        # Prioritize name-like fields
        priority_fields = ['x_name', 'name', 'display_name']
        sorted_fields = sorted(
            fields,
            key=lambda f: (0 if f.name in priority_fields else 1, f.name)
        )

        for field in sorted_fields[:10]:  # Limit to 10 columns
            field_el = etree.SubElement(root, 'field')
            field_el.set('name', field.name)

        return etree.tostring(root, encoding='unicode', pretty_print=True)

    def _studio_create_menu(self):
        """Create menu item for a Studio model."""
        self.ensure_one()

        # Create action
        action = self.env['ir.actions.act_window'].create({
            'name': self.name,
            'res_model': self.model,
            'view_mode': 'list,form',
            'target': 'current',
        })

        # Create menu under Studio Apps
        studio_menu = self.env.ref('loomworks_studio.menu_studio_apps', raise_if_not_found=False)
        parent_id = studio_menu.id if studio_menu else False

        self.env['ir.ui.menu'].create({
            'name': self.name,
            'parent_id': parent_id,
            'action': f'ir.actions.act_window,{action.id}',
            'sequence': 100,
        })
```

---

## Part 2: Spreadsheet as Core View Type

### 2.1 Spreadsheet View Registration

The spreadsheet becomes a first-class citizen in Odoo's view system, not just a standalone document viewer.

**New File: `odoo/addons/web/static/src/views/spreadsheet/spreadsheet_view.js`**

```javascript
/** @odoo-module */

import { registry } from "@web/core/registry";
import { SpreadsheetController } from "./spreadsheet_controller";
import { SpreadsheetArchParser } from "./spreadsheet_arch_parser";
import { SpreadsheetModel } from "./spreadsheet_model";
import { SpreadsheetRenderer } from "./spreadsheet_renderer";

export const spreadsheetView = {
    type: "spreadsheet",
    display_name: "Spreadsheet",
    icon: "fa fa-table",
    multiRecord: true,
    searchMenuTypes: ["filter", "groupBy"],
    Controller: SpreadsheetController,
    ArchParser: SpreadsheetArchParser,
    Model: SpreadsheetModel,
    Renderer: SpreadsheetRenderer,

    props(genericProps, view) {
        const { ArchParser } = view;
        const { arch } = genericProps;
        const archInfo = new ArchParser().parse(arch);

        return {
            ...genericProps,
            Model: view.Model,
            Renderer: view.Renderer,
            archInfo,
        };
    },
};

registry.category("views").add("spreadsheet", spreadsheetView);
```

**New File: `odoo/addons/web/static/src/views/spreadsheet/spreadsheet_controller.js`**

```javascript
/** @odoo-module */

import { Layout } from "@web/search/layout";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, onWillUnmount, useState } from "@odoo/owl";

export class SpreadsheetController extends Component {
    static template = "web.SpreadsheetView";
    static components = { Layout };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.actionService = useService("action");

        this.model = useState(
            new this.props.Model(
                this.orm,
                this.props.resModel,
                this.props.fields,
                this.props.archInfo,
                this.props.domain
            )
        );

        onWillStart(async () => {
            await this.model.load();
        });

        onMounted(() => {
            this.setupKeyboardShortcuts();
        });

        onWillUnmount(() => {
            this.cleanupKeyboardShortcuts();
        });
    }

    setupKeyboardShortcuts() {
        this.keyHandler = (ev) => {
            if (ev.ctrlKey && ev.key === "s") {
                ev.preventDefault();
                this.save();
            }
        };
        document.addEventListener("keydown", this.keyHandler);
    }

    cleanupKeyboardShortcuts() {
        document.removeEventListener("keydown", this.keyHandler);
    }

    async save() {
        await this.model.save();
        this.notification.add("Spreadsheet saved", { type: "success" });
    }

    async onExport(format) {
        const data = await this.model.exportData(format);
        this.downloadFile(data, `${this.props.resModel}_export.${format}`);
    }

    downloadFile(data, filename) {
        const blob = new Blob([data], { type: "application/octet-stream" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }
}
```

**New File: `odoo/addons/web/static/src/views/spreadsheet/spreadsheet_model.js`**

```javascript
/** @odoo-module */

import { KeepLast } from "@web/core/utils/concurrency";

export class SpreadsheetModel {
    constructor(orm, resModel, fields, archInfo, domain) {
        this.orm = orm;
        this.resModel = resModel;
        this.fields = fields;
        this.archInfo = archInfo;
        this.domain = domain;
        this.keepLast = new KeepLast();

        // Spreadsheet data
        this.records = [];
        this.recordsLength = 0;
        this.columns = [];
        this.pivotData = null;

        // State tracking
        this.isDirty = false;
        this.lastSave = null;
    }

    async load() {
        const { columns, measures, groupBy } = this.archInfo;

        if (groupBy && measures) {
            // Pivot mode
            await this.loadPivotData(columns, measures, groupBy);
        } else {
            // Raw data mode
            await this.loadRecords(columns);
        }
    }

    async loadRecords(columns) {
        const fieldNames = columns.map((c) => c.name);

        const { length, records } = await this.keepLast.add(
            this.orm.webSearchRead(this.resModel, this.domain, fieldNames, {
                limit: 10000,
            })
        );

        this.columns = columns;
        this.records = records;
        this.recordsLength = length;
    }

    async loadPivotData(columns, measures, groupBy) {
        const results = await this.keepLast.add(
            this.orm.call(this.resModel, "read_group", [], {
                domain: this.domain,
                fields: measures.map((m) => m.name),
                groupby: groupBy,
                lazy: false,
            })
        );

        this.pivotData = {
            columns,
            measures,
            groupBy,
            results,
        };
    }

    toUniverData() {
        // Convert model data to Univer spreadsheet format
        const sheetData = {
            id: "sheet1",
            name: this.resModel,
            rowCount: this.recordsLength + 1,
            columnCount: this.columns.length,
            cellData: {},
        };

        // Headers
        this.columns.forEach((col, colIdx) => {
            sheetData.cellData[`0:${colIdx}`] = {
                v: col.label || col.name,
                s: { bg: "#f0f0f0", b: 1 },
            };
        });

        // Data rows
        this.records.forEach((record, rowIdx) => {
            this.columns.forEach((col, colIdx) => {
                const value = record[col.name];
                sheetData.cellData[`${rowIdx + 1}:${colIdx}`] = {
                    v: this.formatCellValue(value, col),
                };
            });
        });

        return {
            id: `odoo_${this.resModel}`,
            name: this.resModel,
            sheets: [sheetData],
        };
    }

    formatCellValue(value, column) {
        if (value === null || value === undefined) return "";

        // Handle relational fields
        if (Array.isArray(value) && value.length === 2) {
            return value[1]; // Display name
        }

        return value;
    }

    async save() {
        // Save changes back to Odoo records
        // Implementation depends on edit mode
        this.isDirty = false;
        this.lastSave = Date.now();
    }

    async exportData(format) {
        // Export to XLSX, CSV, etc.
        // Uses Univer's export capabilities
    }
}
```

### 2.2 Python Backend for Spreadsheet View

**Modified File: `odoo/odoo/addons/base/models/ir_ui_view.py`**

```python
# Add spreadsheet to view type selection

class IrUIView(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[
        ('spreadsheet', 'Spreadsheet')
    ], ondelete={'spreadsheet': 'cascade'})

    def _get_view_info(self):
        info = super()._get_view_info()
        info['spreadsheet'] = {'icon': 'fa fa-table'}
        return info
```

**Modified File: `odoo/odoo/addons/base/models/ir_actions.py`**

```python
# Add spreadsheet to action view modes

class IrActionsActWindow(models.Model):
    _inherit = 'ir.actions.act_window'

    # view_mode already accepts any view type registered
    # Just ensure spreadsheet is available
```

---

## Part 3: loomworks_studio Addon

Business logic that builds on core modifications.

### 3.1 Architecture Overview

```
loomworks_studio/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── studio_app.py              # Custom app registry
│   ├── studio_view_customization.py # View modification storage
│   ├── studio_automation.py       # Workflow rules
│   └── ir_model_inherit.py        # Extends core ir.model
├── views/
│   ├── studio_app_views.xml
│   ├── studio_menus.xml
│   └── studio_templates.xml
├── security/
│   ├── ir.model.access.csv
│   └── security.xml
├── controllers/
│   └── studio_controller.py       # REST endpoints
├── static/src/
│   ├── components/                # Addon-specific Owl components
│   │   ├── app_wizard/
│   │   └── automation_builder/
│   └── xml/
│       └── studio_templates.xml
└── tests/
    └── test_studio.py
```

### 3.2 Studio App Model

```python
# models/studio_app.py

class StudioApp(models.Model):
    _name = 'studio.app'
    _description = 'Studio Custom Application'
    _order = 'name'

    name = fields.Char(required=True)
    technical_name = fields.Char(
        required=True,
        help="Used as prefix for models: x_[technical_name]_"
    )
    icon = fields.Char(default='fa-cube')
    color = fields.Integer(default=0)
    description = fields.Text()

    # Related components
    model_ids = fields.One2many('ir.model', 'studio_app_id', string='Models')
    menu_id = fields.Many2one('ir.ui.menu', string='Root Menu')
    action_id = fields.Many2one('ir.actions.act_window', string='Default Action')

    # State management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived')
    ], default='draft')

    # Audit
    created_by_id = fields.Many2one(
        'res.users',
        default=lambda self: self.env.user,
        readonly=True
    )
    published_date = fields.Datetime(readonly=True)

    # Statistics
    model_count = fields.Integer(compute='_compute_model_count')
    record_count = fields.Integer(compute='_compute_record_count')

    @api.depends('model_ids')
    def _compute_model_count(self):
        for app in self:
            app.model_count = len(app.model_ids)

    def _compute_record_count(self):
        for app in self:
            count = 0
            for model in app.model_ids:
                try:
                    count += self.env[model.model].search_count([])
                except Exception:
                    pass
            app.record_count = count

    @api.constrains('technical_name')
    def _check_technical_name(self):
        for app in self:
            if not re.match(r'^[a-z][a-z0-9_]*$', app.technical_name):
                raise ValidationError(_(
                    "Technical name must contain only lowercase letters, "
                    "numbers, and underscores, and start with a letter."
                ))

    def action_create_model(self, vals):
        """Create a new model for this Studio app.

        Delegates to core ir.model._studio_create_model with app context.
        """
        self.ensure_one()
        vals['studio_app_id'] = self.id

        # Prefix model name with app technical name
        model_name = vals.get('model', vals.get('name', '')).lower()
        model_name = re.sub(r'[^a-z0-9_]', '_', model_name)
        vals['model'] = f"x_{self.technical_name}_{model_name}"

        return self.env['ir.model']._studio_create_model(vals)

    def action_publish(self):
        """Publish the app, making it available to users."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_("Only draft apps can be published."))

        self.write({
            'state': 'published',
            'published_date': fields.Datetime.now(),
        })

    def action_archive(self):
        """Archive the app, hiding it from users."""
        self.write({'state': 'archived'})

    def action_unarchive(self):
        """Restore an archived app."""
        self.write({'state': 'published'})
```

### 3.3 View Customization Model

```python
# models/studio_view_customization.py

class StudioViewCustomization(models.Model):
    _name = 'studio.view.customization'
    _description = 'Studio View Customization'

    name = fields.Char(required=True)
    model_name = fields.Char(required=True, index=True)
    model_id = fields.Many2one(
        'ir.model',
        compute='_compute_model_id',
        store=True
    )
    view_type = fields.Selection([
        ('form', 'Form'),
        ('list', 'List'),
        ('kanban', 'Kanban'),
        ('calendar', 'Calendar'),
        ('pivot', 'Pivot'),
        ('graph', 'Graph'),
        ('search', 'Search'),
        ('spreadsheet', 'Spreadsheet'),
    ], required=True)

    # Original view reference
    base_view_id = fields.Many2one('ir.ui.view', string='Base View')

    # Generated view
    generated_view_id = fields.Many2one(
        'ir.ui.view',
        string='Generated View',
        readonly=True
    )

    # Customization storage (JSON)
    arch_json = fields.Text(
        help="JSON representation of view customizations"
    )

    # Field configuration
    field_ids = fields.One2many(
        'studio.view.field',
        'customization_id',
        string='Fields'
    )

    active = fields.Boolean(default=True)

    @api.depends('model_name')
    def _compute_model_id(self):
        IrModel = self.env['ir.model']
        for cust in self:
            cust.model_id = IrModel.search([
                ('model', '=', cust.model_name)
            ], limit=1)

    def add_field_to_view(self, model, view_type, field_id, position, after_field=None):
        """Add a field to a view via Studio.

        Called from JavaScript StudioService.
        """
        customization = self.search([
            ('model_name', '=', model),
            ('view_type', '=', view_type),
            ('active', '=', True)
        ], limit=1)

        if not customization:
            # Create new customization
            base_view = self.env['ir.ui.view'].search([
                ('model', '=', model),
                ('type', '=', view_type),
            ], order='priority', limit=1)

            customization = self.create({
                'name': f"Studio: {model} {view_type}",
                'model_name': model,
                'view_type': view_type,
                'base_view_id': base_view.id if base_view else False,
            })

        # Add field to customization
        sequence = 10
        if after_field:
            after = customization.field_ids.filtered(
                lambda f: f.field_id.name == after_field
            )
            if after:
                sequence = after.sequence + 1

        self.env['studio.view.field'].create({
            'customization_id': customization.id,
            'field_id': field_id,
            'sequence': sequence,
        })

        # Regenerate view
        customization._generate_view()

        return customization

    def add_list_column(self, model, field_name, position):
        """Add a column to a list view."""
        return self.add_field_to_view(
            model, 'list',
            self._get_field_id(model, field_name),
            position
        )

    def remove_list_column(self, model, field_name):
        """Remove a column from a list view."""
        customization = self.search([
            ('model_name', '=', model),
            ('view_type', '=', 'list'),
            ('active', '=', True)
        ], limit=1)

        if customization:
            field = customization.field_ids.filtered(
                lambda f: f.field_id.name == field_name
            )
            field.unlink()
            customization._generate_view()

    def reorder_list_columns(self, model, from_index, to_index):
        """Reorder columns in a list view."""
        customization = self.search([
            ('model_name', '=', model),
            ('view_type', '=', 'list'),
            ('active', '=', True)
        ], limit=1)

        if customization:
            fields = customization.field_ids.sorted('sequence')
            if 0 <= from_index < len(fields) and 0 <= to_index < len(fields):
                # Recompute sequences
                for idx, field in enumerate(fields):
                    if idx == from_index:
                        field.sequence = (to_index * 10) + 5
                    else:
                        field.sequence = idx * 10
                customization._generate_view()

    def _get_field_id(self, model, field_name):
        """Get ir.model.fields ID for a field."""
        return self.env['ir.model.fields'].search([
            ('model', '=', model),
            ('name', '=', field_name)
        ], limit=1).id

    def _generate_view(self):
        """Generate or update the ir.ui.view from customization."""
        self.ensure_one()

        arch = self._build_arch()

        view_vals = {
            'name': f"studio.{self.model_name}.{self.view_type}",
            'model': self.model_name,
            'type': self.view_type,
            'arch': arch,
            'priority': 99,
            'studio_customized': True,
            'studio_customization_id': self.id,
        }

        if self.base_view_id:
            view_vals['inherit_id'] = self.base_view_id.id

        if self.generated_view_id:
            self.generated_view_id.write(view_vals)
        else:
            view = self.env['ir.ui.view'].create(view_vals)
            self.generated_view_id = view

    def _build_arch(self):
        """Build XML architecture from customization."""
        builder = getattr(self, f'_build_{self.view_type}_arch', None)
        if builder:
            return builder()
        return f"<{self.view_type}/>"

    def _build_form_arch(self):
        """Build form view XML."""
        root = etree.Element('form')
        sheet = etree.SubElement(root, 'sheet')

        # Group fields
        grouped = defaultdict(list)
        for field in self.field_ids.sorted('sequence'):
            grouped[field.group_name or ''].append(field)

        for group_name, fields in grouped.items():
            group = etree.SubElement(sheet, 'group')
            if group_name:
                group.set('string', group_name)

            for field_rec in fields:
                self._add_field_to_element(group, field_rec)

        return etree.tostring(root, encoding='unicode', pretty_print=True)

    def _build_list_arch(self):
        """Build list view XML."""
        root = etree.Element('list')

        for field_rec in self.field_ids.sorted('sequence'):
            self._add_field_to_element(root, field_rec)

        return etree.tostring(root, encoding='unicode', pretty_print=True)

    def _add_field_to_element(self, parent, field_rec):
        """Add a field element to parent XML."""
        field_el = etree.SubElement(parent, 'field')
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

    def _apply_to_arch(self, base_arch):
        """Apply customizations to a base view arch.

        Called from core ir.ui.view during view processing.
        """
        self.ensure_one()

        if not self.arch_json:
            return base_arch

        customizations = json.loads(self.arch_json)
        # Apply JSON customizations to XML arch
        # ... implementation

        return base_arch
```

---

## Part 4: loomworks_spreadsheet Addon

### 4.1 Architecture Overview

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
│   └── spreadsheet_controller.py  # REST API
├── static/src/
│   ├── univer/                    # Univer integration
│   │   ├── univer_wrapper.js
│   │   ├── odoo_data_plugin.js
│   │   ├── pivot_plugin.js
│   │   └── chart_plugin.js
│   ├── components/
│   │   ├── spreadsheet_action/
│   │   ├── data_source_dialog/
│   │   └── pivot_config/
│   └── xml/
│       └── templates.xml
└── tests/
    └── test_spreadsheet.py
```

### 4.2 Univer Integration

**File: `static/src/univer/univer_wrapper.js`**

```javascript
/** @odoo-module */

import { Component, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

// Univer imports
import { Univer, LocaleType } from "@univerjs/core";
import { defaultTheme } from "@univerjs/design";
import { UniverSheetsPlugin } from "@univerjs/sheets";
import { UniverSheetsUIPlugin } from "@univerjs/sheets-ui";
import { UniverSheetsFormulaPlugin } from "@univerjs/sheets-formula";

import { OdooDataPlugin } from "./odoo_data_plugin";
import { LoomworksPivotPlugin } from "./pivot_plugin";
import { LoomworksChartPlugin } from "./chart_plugin";

export class UniverWrapper extends Component {
    static template = "loomworks_spreadsheet.UniverWrapper";
    static props = {
        data: { type: Object, optional: true },
        documentId: { type: Number, optional: true },
        readonly: { type: Boolean, optional: true },
        onSave: { type: Function, optional: true },
        onDataChange: { type: Function, optional: true },
    };

    setup() {
        this.containerRef = useRef("univerContainer");
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.univer = null;
        this.workbook = null;

        onMounted(() => this.initUniver());
        onWillUnmount(() => this.destroyUniver());
    }

    async initUniver() {
        // Initialize Univer instance
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

        // Register Loomworks plugins
        this.univer.registerPlugin(OdooDataPlugin, {
            orm: this.orm,
            documentId: this.props.documentId,
        });
        this.univer.registerPlugin(LoomworksPivotPlugin, {
            orm: this.orm,
        });
        this.univer.registerPlugin(LoomworksChartPlugin);

        // Load data
        const data = this.props.data || await this.loadDocument();
        this.workbook = this.univer.createUniverSheet(data);

        // Setup change tracking
        if (!this.props.readonly) {
            this.setupChangeTracking();
        }
    }

    async loadDocument() {
        if (!this.props.documentId) {
            return this.getEmptySpreadsheet();
        }

        const [doc] = await this.orm.read(
            "spreadsheet.document",
            [this.props.documentId],
            ["data"]
        );

        return doc?.data ? JSON.parse(doc.data) : this.getEmptySpreadsheet();
    }

    getEmptySpreadsheet() {
        return {
            id: `new_${Date.now()}`,
            name: "New Spreadsheet",
            sheets: [{
                id: "sheet1",
                name: "Sheet 1",
                rowCount: 100,
                columnCount: 26,
                cellData: {},
            }],
        };
    }

    setupChangeTracking() {
        let saveTimeout;
        this.workbook.onChanged(() => {
            if (this.props.onDataChange) {
                this.props.onDataChange(this.getSnapshot());
            }

            // Debounced auto-save
            clearTimeout(saveTimeout);
            saveTimeout = setTimeout(() => this.autoSave(), 3000);
        });
    }

    getSnapshot() {
        return this.workbook?.getSnapshot();
    }

    async autoSave() {
        if (!this.props.documentId || this.props.readonly) return;

        try {
            const data = JSON.stringify(this.getSnapshot());
            await this.orm.write(
                "spreadsheet.document",
                [this.props.documentId],
                { data, last_modified: new Date().toISOString() }
            );

            if (this.props.onSave) {
                this.props.onSave();
            }
        } catch (error) {
            this.notification.add("Failed to save spreadsheet", { type: "danger" });
            console.error("Auto-save failed:", error);
        }
    }

    destroyUniver() {
        if (this.univer) {
            this.univer.dispose();
            this.univer = null;
            this.workbook = null;
        }
    }

    // Public API for external control
    insertOdooData(config) {
        const plugin = this.univer.getPlugin(OdooDataPlugin);
        return plugin?.insertDataSource(config);
    }

    createPivot(config) {
        const plugin = this.univer.getPlugin(LoomworksPivotPlugin);
        return plugin?.createPivot(config);
    }

    createChart(config) {
        const plugin = this.univer.getPlugin(LoomworksChartPlugin);
        return plugin?.createChart(config);
    }
}
```

### 4.3 Odoo Data Plugin

**File: `static/src/univer/odoo_data_plugin.js`**

```javascript
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
        this.registerOdooFunctions();
        if (this.documentId) {
            this.loadDataSources();
        }
    }

    registerOdooFunctions() {
        const formulaEngine = this.getUniverSheet().getFormulaEngine();

        // ODOO.DATA(model, domain, fields, row, col)
        formulaEngine.registerFunction("ODOO.DATA", {
            calculate: async (model, domain, fields, row, col) => {
                return this.fetchOdooData(model, domain, fields, row, col);
            },
            description: "Fetch data from an Odoo model",
            parameters: [
                { name: "model", type: "string" },
                { name: "domain", type: "string" },
                { name: "fields", type: "string" },
                { name: "row", type: "number", optional: true },
                { name: "col", type: "number", optional: true },
            ],
        });

        // ODOO.PIVOT(pivot_id, row, measure)
        formulaEngine.registerFunction("ODOO.PIVOT", {
            calculate: async (pivotId, row, measure) => {
                return this.fetchPivotValue(pivotId, row, measure);
            },
            description: "Get a value from an Odoo pivot",
        });

        // ODOO.PIVOT.HEADER(pivot_id, row)
        formulaEngine.registerFunction("ODOO.PIVOT.HEADER", {
            calculate: async (pivotId, row) => {
                return this.fetchPivotHeader(pivotId, row);
            },
            description: "Get a header from an Odoo pivot",
        });

        // ODOO.FIELD(model, id, field)
        formulaEngine.registerFunction("ODOO.FIELD", {
            calculate: async (model, recordId, field) => {
                return this.fetchFieldValue(model, recordId, field);
            },
            description: "Get a field value from an Odoo record",
        });
    }

    async loadDataSources() {
        const sources = await this.orm.searchRead(
            "spreadsheet.data.source",
            [["document_id", "=", this.documentId]],
            ["id", "name", "source_type", "model_id", "domain", "target_cell"]
        );

        for (const source of sources) {
            this.dataSources.set(source.id, source);
        }
    }

    async fetchOdooData(model, domain, fields, row, col) {
        try {
            const parsedDomain = typeof domain === "string"
                ? JSON.parse(domain || "[]")
                : domain || [];
            const fieldList = typeof fields === "string"
                ? fields.split(",").map((f) => f.trim())
                : fields || [];

            const records = await this.orm.searchRead(
                model,
                parsedDomain,
                fieldList,
                { limit: 1000 }
            );

            if (row !== undefined && col !== undefined) {
                const record = records[row];
                if (!record) return "";
                const value = record[fieldList[col]];
                return this.formatValue(value);
            }

            return records;
        } catch (error) {
            console.error("ODOO.DATA error:", error);
            return "#ERROR";
        }
    }

    async fetchFieldValue(model, recordId, field) {
        try {
            const [record] = await this.orm.read(model, [recordId], [field]);
            return record ? this.formatValue(record[field]) : "";
        } catch (error) {
            return "#ERROR";
        }
    }

    formatValue(value) {
        if (value === null || value === undefined) return "";
        if (Array.isArray(value) && value.length === 2) {
            return value[1]; // Many2one display name
        }
        return value;
    }

    async insertDataSource(config) {
        // Create data source record
        const sourceId = await this.orm.create("spreadsheet.data.source", [{
            name: config.name,
            document_id: this.documentId,
            source_type: config.type || "model",
            model_id: config.modelId,
            domain: JSON.stringify(config.domain || []),
            target_cell: config.targetCell || "A1",
            field_ids: [[6, 0, config.fieldIds || []]],
        }]);

        // Fetch and insert data
        const data = await this.orm.call(
            "spreadsheet.data.source",
            "fetch_data",
            [sourceId]
        );

        this.insertTableData(config.targetCell || "A1", data);
        this.dataSources.set(sourceId, { id: sourceId, ...config });

        return sourceId;
    }

    insertTableData(startCell, data) {
        const sheet = this.getUniverSheet().getActiveSheet();
        const { row, col } = this.cellRefToCoords(startCell);

        // Insert headers
        data.headers.forEach((header, i) => {
            const cell = sheet.getCell(row, col + i);
            cell.setValue(header);
            cell.setStyle({ fontWeight: "bold", backgroundColor: "#f0f0f0" });
        });

        // Insert data rows
        data.rows.forEach((rowData, rowIdx) => {
            rowData.forEach((value, colIdx) => {
                sheet.getCell(row + rowIdx + 1, col + colIdx).setValue(
                    this.formatValue(value)
                );
            });
        });
    }

    cellRefToCoords(ref) {
        const match = ref.match(/^([A-Z]+)(\d+)$/i);
        if (!match) return { row: 0, col: 0 };

        const colStr = match[1].toUpperCase();
        const col = colStr.split("").reduce(
            (acc, c) => acc * 26 + c.charCodeAt(0) - 64,
            0
        ) - 1;
        const row = parseInt(match[2]) - 1;

        return { row, col };
    }
}
```

---

## Risks / Trade-offs

### Core Modification Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Upstream merge conflicts | High | Medium | Isolate changes to specific files; document all modifications |
| Breaking changes in Odoo 19 | Medium | High | Abstract core dependencies; maintain compatibility layer |
| Increased maintenance burden | High | Medium | Comprehensive test coverage; clear documentation |
| Developer onboarding complexity | Medium | Low | Training materials; architecture documentation |

### Technical Trade-offs

1. **Core vs Addon**: Deeper integration but higher maintenance cost
2. **Univer vs alternatives**: Modern architecture but smaller community than Handsontable
3. **JSON view storage**: Flexible but requires migration tooling
4. **Runtime model creation**: Powerful but requires careful ORM cache management

---

## React Dependency Clarification (M1 Resolution)

### Univer Requires React

**Research Finding**: The Univer spreadsheet library requires React as a runtime dependency. Based on official Univer documentation (https://docs.univer.ai/guides/sheets/getting-started/installation/cdn), Univer's preset mode requires:

- React 18.3.1+
- ReactDOM 18.3.1+
- RxJS
- ECharts (for charts)

### Resolution: React Integration in Phase 3.1

To resolve the timing conflict between Phase 3.1 (Spreadsheet) and Phase 4 (Dashboard/React Bridge), the following approach is adopted:

#### Option Selected: Early React Loading in Phase 3.1

1. **React Libraries in Phase 3.1 Asset Bundle**: The React libraries (`react`, `react-dom`) will be included in Phase 3.1's asset bundle as a dependency of the spreadsheet view type:

   ```
   odoo/addons/web/static/lib/react/
   ├── react.production.min.js      # React 18+
   ├── react-dom.production.min.js  # ReactDOM 18+
   └── rxjs.umd.min.js              # RxJS dependency
   ```

2. **Asset Loading Order**: The `web.assets_backend` bundle will load React libraries before Univer:

   ```xml
   <!-- In web/__manifest__.py assets -->
   'web.assets_backend': [
       # React libraries (Phase 3.1 - required for Univer)
       ('prepend', 'web/static/lib/react/react.production.min.js'),
       ('prepend', 'web/static/lib/react/react-dom.production.min.js'),
       ('prepend', 'web/static/lib/react/rxjs.umd.min.js'),
       # Univer libraries
       'web/static/lib/univer/*.js',
       # Spreadsheet components
       'web/static/src/views/spreadsheet/*.js',
   ]
   ```

3. **React Bridge in Phase 4 Reuses Libraries**: Phase 4's React Bridge will not re-bundle React but will use the already-loaded React instance from Phase 3.1, adding only the bridging logic:

   ```javascript
   // Phase 4: React Bridge uses existing React global
   const React = window.React;
   const ReactDOM = window.ReactDOM;
   ```

#### Owl-to-React Bridge Pattern (For Univer)

Phase 3.1 implements a minimal Owl-to-React bridge specifically for Univer integration:

```javascript
// odoo/addons/web/static/src/views/spreadsheet/univer_wrapper.js
import { Component, useRef, onMounted, onWillUnmount } from "@odoo/owl";

export class UniverWrapper extends Component {
    static template = "web.UniverWrapper";

    setup() {
        this.containerRef = useRef("container");
        onMounted(() => this._mountUniver());
        onWillUnmount(() => this._unmountUniver());
    }

    _mountUniver() {
        // Uses global React/ReactDOM loaded in asset bundle
        const { createUniver } = window.UniverPresets;
        this.univerInstance = createUniver({
            locale: window.UniverCore.LocaleType.EN_US,
            presets: [window.UniverPresetSheetsCore.UniverSheetsCorePreset()],
        });
    }

    _unmountUniver() {
        if (this.univerInstance) {
            this.univerInstance.dispose();
        }
    }
}
```

#### Phase 4 Enhancement

Phase 4 Dashboard will extend this foundation with:
- Full React Bridge service (`reactBridgeService`) for mounting arbitrary React components
- React Flow, Tremor, and Recharts integration
- Bidirectional data binding between Owl and React

### Impact on Compatibility Review

- **Issue M1 Status**: RESOLVED
- **Resolution**: React is loaded in Phase 3.1 as a Univer dependency; Phase 4 reuses it
- **No Breaking Change**: The asset bundle order ensures React is available for all downstream consumers

---

## Migration Plan

### Phase 1: Core Foundation (Week 1-2)
1. Apply core view system modifications
2. Implement Studio service in core
3. Add spreadsheet view type to core

### Phase 2: Studio Addon (Week 3-5)
1. Create loomworks_studio addon structure
2. Implement studio.app and view customization models
3. Build field palette and automation engine

### Phase 3: Spreadsheet Addon (Week 6-8)
1. Create loomworks_spreadsheet addon structure
2. Integrate Univer with Owl wrapper
3. Implement data source and pivot plugins

### Phase 4: Integration (Week 9-10)
1. Connect Studio to AI agent via MCP tools
2. Connect Spreadsheet to AI agent via MCP tools
3. End-to-end testing and polish

### Rollback Strategy

1. **Core changes**: Maintain git branches; can revert to vanilla Odoo
2. **Addon code**: Standard module uninstall
3. **Data**: Views/models created by Studio remain in database; provide cleanup scripts

---

## Open Questions

1. **Collaboration**: Use Odoo bus or dedicated WebSocket for real-time sync?
   - Recommendation: Odoo bus for consistency

2. **View Inheritance**: How to handle Studio customizations that conflict with module updates?
   - Recommendation: Studio views have lower priority; provide conflict resolution UI

3. **Formula Compatibility**: Which Excel formulas are must-have?
   - Recommendation: Top 100 most-used functions

4. **AI Integration Depth**: Should AI be able to design full apps from description?
   - Recommendation: Phase 1 delivers tools; natural language in Phase 2
