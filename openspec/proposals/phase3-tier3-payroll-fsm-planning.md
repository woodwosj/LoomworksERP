# Change: Phase 3 Tier 3 - Payroll, FSM, and Planning Modules

## Why

Loomworks ERP requires comprehensive workforce management capabilities to compete with enterprise ERP solutions. Phase 3 Tier 3 delivers three critical modules: payroll for salary computation and tax compliance, field service management (FSM) for mobile workforce operations, and workforce planning with visual scheduling. These modules address core business needs for companies with field workers, shift-based operations, and US-based employees requiring compliant payroll processing.

**With a fully forked Odoo core**, we can implement these features as first-class citizens rather than add-on modules, enabling deeper integration, native view types, and core-level mobile/PWA support.

## What Changes

### New Modules

- **NEW** `loomworks_payroll` - Salary computation engine with rules-based calculations (US locale: Federal + California)
- **NEW** `loomworks_fsm` - Mobile-first field service management extending project.task
- **NEW** `loomworks_planning` - Visual workforce scheduling with Gantt views and shift management

### Core Fork Modifications

- **MODIFY** `odoo/addons/hr/` - Extend HR models with payroll structure type support
- **MODIFY** `odoo/addons/project/` - Add FSM fields and mobile views to core project.task
- **ADD** `odoo/addons/web/static/src/views/gantt/` - Native Gantt view type in core web client
- **MODIFY** `odoo/addons/web/static/src/` - PWA service worker and offline capabilities
- **ADD** `odoo/addons/base_geolocalize/` - Enhanced geolocation field type (if not present)

### Dependencies

- `hr` (Odoo Community - forked) - Employee management base
- `project` (Odoo Community - forked) - Task management for FSM
- `hr_timesheet` (Odoo Community) - Time tracking integration
- `hr_contract` (Odoo Community - forked) - Contract management with payroll integration
- `loomworks_core` - Branding and base configuration

## Impact

- Affected specs: `loomworks-payroll`, `loomworks-fsm`, `loomworks-planning` (new capabilities)
- Affected code:
  - `/odoo/addons/hr/models/` (core modifications for payroll)
  - `/odoo/addons/project/models/` (core modifications for FSM)
  - `/odoo/addons/web/static/src/views/gantt/` (new native view type)
  - `/odoo/addons/web/static/src/core/pwa/` (new PWA infrastructure)
  - `/loomworks_addons/loomworks_payroll/` (new module)
  - `/loomworks_addons/loomworks_fsm/` (new module)
  - `/loomworks_addons/loomworks_planning/` (new module)
- External dependencies:
  - Frappe Gantt (MIT) or SVAR React Gantt (MIT) for planning visualization (fallback; prefer native)
  - PDF generation for payslips (wkhtmltopdf)
  - Canvas API for signature capture

## Scope

This proposal covers **Phase 3 Tier 3 (Weeks 27-30)** of the implementation plan.

---

# Part 0: Core Fork Modifications

This section details modifications to the forked Odoo core that enable deep integration for Phase 3.3 modules.

## 0.1 HR Core Extensions (`odoo/addons/hr/`)

### Payroll Structure Type in Core hr_contract

Extend `hr.contract` to support payroll structure references. This exists in the forked `odoo/addons/hr_contract/` module:

```python
# odoo/addons/hr_contract/models/hr_contract.py (extension)

class HrContract(models.Model):
    _inherit = 'hr.contract'

    # Payroll integration fields (in core for loomworks_payroll to use)
    structure_type_id = fields.Many2one(
        'hr.payroll.structure.type',
        string='Salary Structure Type',
        help="Defines the default salary structure for this contract type"
    )

    # Filing status for tax calculations
    filing_status = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married Filing Jointly'),
        ('married_separate', 'Married Filing Separately'),
        ('head_household', 'Head of Household'),
    ], string='Filing Status', default='single')

    # Federal and state withholding allowances
    federal_allowances = fields.Integer(string='Federal Allowances', default=0)
    state_allowances = fields.Integer(string='State Allowances', default=0)

    # Additional withholding
    additional_federal_withholding = fields.Monetary(string='Additional Federal Withholding')
    additional_state_withholding = fields.Monetary(string='Additional State Withholding')
```

### Payroll Structure Type Model (Core)

Add the structure type model to core HR for cleaner payroll integration:

```python
# odoo/addons/hr_contract/models/hr_payroll_structure_type.py (new file)

class HrPayrollStructureType(models.Model):
    _name = 'hr.payroll.structure.type'
    _description = 'Salary Structure Type'

    name = fields.Char('Salary Structure Type', required=True)
    default_resource_calendar_id = fields.Many2one(
        'resource.calendar',
        string='Default Working Hours',
        default=lambda self: self.env.company.resource_calendar_id
    )
    country_id = fields.Many2one(
        'res.country',
        string='Country',
        default=lambda self: self.env.company.country_id
    )
    country_code = fields.Char(related="country_id.code")
    wage_type = fields.Selection([
        ('monthly', 'Monthly Fixed Wage'),
        ('hourly', 'Hourly Wage'),
    ], default='monthly', required=True)
    default_struct_id = fields.Many2one(
        'hr.payroll.structure',
        string='Default Structure',
        help="Default payroll structure for contracts of this type"
    )
```

## 0.2 Project Core Extensions (`odoo/addons/project/`)

### FSM Fields in Core project.task

Add FSM-related fields directly to core project.task for deeper integration:

```python
# odoo/addons/project/models/project_task.py (extension)

class ProjectTask(models.Model):
    _inherit = 'project.task'

    # FSM flag - enables FSM features on this task
    is_fsm = fields.Boolean(
        string='Field Service Task',
        default=False,
        help="Enable field service features for this task"
    )

    # Geolocation fields (native support)
    partner_latitude = fields.Float(
        related='partner_id.partner_latitude',
        string='Latitude',
        store=True
    )
    partner_longitude = fields.Float(
        related='partner_id.partner_longitude',
        string='Longitude',
        store=True
    )

    # Scheduling fields
    planned_date_start = fields.Datetime(string='Planned Start')
    planned_date_end = fields.Datetime(string='Planned End')

    # Timer infrastructure (core support)
    timer_start = fields.Datetime(string='Timer Started')
    timer_pause = fields.Datetime(string='Timer Paused')

    # Signature field type (core binary with signature widget)
    customer_signature = fields.Binary(string='Customer Signature', attachment=False)
    customer_signed_by = fields.Char(string='Signed By')
    customer_signed_on = fields.Datetime(string='Signed On')
```

### FSM Project Type

Add project type configuration:

```python
# odoo/addons/project/models/project_project.py (extension)

class Project(models.Model):
    _inherit = 'project.project'

    is_fsm = fields.Boolean(
        string='Field Service Project',
        default=False,
        help="Enable field service features for tasks in this project"
    )

    # Auto-enable FSM on tasks created in this project
    @api.model_create_multi
    def create(self, vals_list):
        projects = super().create(vals_list)
        # Any FSM-specific project setup
        return projects
```

## 0.3 Gantt View as Native View Type (`odoo/addons/web/static/src/views/gantt/`)

Since we own the fork, implement Gantt as a first-class view type in the core web client, following Odoo's Controller/Model/Renderer pattern.

### Directory Structure

```
odoo/addons/web/static/src/views/gantt/
    gantt_view.js           # View registration
    gantt_controller.js     # User interaction handling
    gantt_model.js          # Data management
    gantt_renderer.js       # DOM rendering
    gantt_arch_parser.js    # XML arch parsing
    gantt_renderer.xml      # OWL templates
    gantt_renderer.scss     # Styling
```

### View Registration

```javascript
/** @odoo-module **/
// odoo/addons/web/static/src/views/gantt/gantt_view.js

import { registry } from "@web/core/registry";
import { GanttController } from "./gantt_controller";
import { GanttRenderer } from "./gantt_renderer";
import { GanttModel } from "./gantt_model";
import { GanttArchParser } from "./gantt_arch_parser";

export const ganttView = {
    type: "gantt",
    display_name: "Gantt",
    icon: "fa fa-tasks",
    multiRecord: true,
    Controller: GanttController,
    Renderer: GanttRenderer,
    Model: GanttModel,
    ArchParser: GanttArchParser,

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

registry.category("views").add("gantt", ganttView);
```

### Gantt Arch Parser

```javascript
/** @odoo-module **/
// odoo/addons/web/static/src/views/gantt/gantt_arch_parser.js

import { XMLParser } from "@web/core/utils/xml";

export class GanttArchParser extends XMLParser {
    parse(arch) {
        const xmlDoc = this.parseXML(arch);
        const ganttEl = xmlDoc.querySelector("gantt");

        return {
            dateStartField: ganttEl.getAttribute("date_start") || "date_start",
            dateStopField: ganttEl.getAttribute("date_stop") || "date_stop",
            colorField: ganttEl.getAttribute("color"),
            defaultGroupBy: ganttEl.getAttribute("default_group_by"),
            progressField: ganttEl.getAttribute("progress"),
            consolidation: ganttEl.getAttribute("consolidation"),
            consolidationMax: ganttEl.getAttribute("consolidation_max"),
            consolidationExclude: ganttEl.getAttribute("consolidation_exclude"),
            string: ganttEl.getAttribute("string") || "Gantt",
            precision: {
                day: ganttEl.getAttribute("precision_day") || "hour:full",
                week: ganttEl.getAttribute("precision_week") || "day:full",
                month: ganttEl.getAttribute("precision_month") || "day:full",
                year: ganttEl.getAttribute("precision_year") || "month:full",
            },
            canCreate: ganttEl.getAttribute("create") !== "false",
            canEdit: ganttEl.getAttribute("edit") !== "false",
            canDelete: ganttEl.getAttribute("delete") !== "false",
            displayUnavailability: ganttEl.getAttribute("display_unavailability") === "true",
            totalRow: ganttEl.getAttribute("total_row") === "true",
            collapseFirstLevel: ganttEl.getAttribute("collapse_first_level") === "true",
            thumbnails: this.parseThumbnails(ganttEl),
            pillDecorations: this.parsePillDecorations(ganttEl),
        };
    }

    parseThumbnails(ganttEl) {
        const thumbnails = {};
        for (const node of ganttEl.querySelectorAll("field[widget='image']")) {
            thumbnails[node.getAttribute("name")] = true;
        }
        return thumbnails;
    }

    parsePillDecorations(ganttEl) {
        const decorations = {};
        for (const attr of ganttEl.attributes) {
            if (attr.name.startsWith("decoration-")) {
                const decorationName = attr.name.slice(11);
                decorations[decorationName] = attr.value;
            }
        }
        return decorations;
    }
}
```

### Gantt Model

```javascript
/** @odoo-module **/
// odoo/addons/web/static/src/views/gantt/gantt_model.js

import { KeepLast } from "@web/core/utils/concurrency";

export class GanttModel {
    constructor(orm, resModel, fields, archInfo, domain, context) {
        this.orm = orm;
        this.resModel = resModel;
        this.fields = fields;
        this.archInfo = archInfo;
        this.domain = domain;
        this.context = context;
        this.keepLast = new KeepLast();

        this.dateStartField = archInfo.dateStartField;
        this.dateStopField = archInfo.dateStopField;
        this.colorField = archInfo.colorField;
        this.progressField = archInfo.progressField;

        this.scale = "week"; // day, week, month, year
        this.focusDate = luxon.DateTime.now();

        this.data = {
            records: [],
            groups: [],
        };
    }

    async load() {
        const { startDate, stopDate } = this.getDateRange();

        const dateFilterDomain = [
            "&",
            [this.dateStartField, "<=", stopDate.toISODate()],
            [this.dateStopField, ">=", startDate.toISODate()],
        ];

        const finalDomain = [...this.domain, ...dateFilterDomain];

        const fieldNames = this.getFieldNames();

        const { length, records } = await this.keepLast.add(
            this.orm.webSearchRead(this.resModel, finalDomain, fieldNames, {
                context: this.context,
            })
        );

        this.data.records = records.map((r) => this.processRecord(r));
        this.data.recordsLength = length;

        // Group records if default_group_by specified
        if (this.archInfo.defaultGroupBy) {
            this.data.groups = this.groupRecords(this.data.records);
        }
    }

    getDateRange() {
        const now = this.focusDate;
        let startDate, stopDate;

        switch (this.scale) {
            case "day":
                startDate = now.startOf("day");
                stopDate = now.endOf("day");
                break;
            case "week":
                startDate = now.startOf("week");
                stopDate = now.endOf("week");
                break;
            case "month":
                startDate = now.startOf("month");
                stopDate = now.endOf("month");
                break;
            case "year":
                startDate = now.startOf("year");
                stopDate = now.endOf("year");
                break;
        }

        return { startDate, stopDate };
    }

    getFieldNames() {
        const fields = [this.dateStartField, this.dateStopField, "display_name"];
        if (this.colorField) fields.push(this.colorField);
        if (this.progressField) fields.push(this.progressField);
        if (this.archInfo.defaultGroupBy) fields.push(this.archInfo.defaultGroupBy);
        return fields;
    }

    processRecord(record) {
        return {
            ...record,
            startDate: luxon.DateTime.fromISO(record[this.dateStartField]),
            stopDate: luxon.DateTime.fromISO(record[this.dateStopField]),
            progress: this.progressField ? record[this.progressField] : 0,
            color: this.colorField ? record[this.colorField] : 0,
        };
    }

    groupRecords(records) {
        const groupField = this.archInfo.defaultGroupBy;
        const groups = new Map();

        for (const record of records) {
            const groupValue = record[groupField];
            const groupKey = Array.isArray(groupValue) ? groupValue[0] : groupValue;

            if (!groups.has(groupKey)) {
                groups.set(groupKey, {
                    id: groupKey,
                    name: Array.isArray(groupValue) ? groupValue[1] : groupValue,
                    records: [],
                });
            }
            groups.get(groupKey).records.push(record);
        }

        return Array.from(groups.values());
    }

    setScale(scale) {
        this.scale = scale;
    }

    setFocusDate(date) {
        this.focusDate = luxon.DateTime.fromJSDate(date);
    }

    navigatePrevious() {
        const unit = this.scale === "day" ? "days" : this.scale + "s";
        this.focusDate = this.focusDate.minus({ [unit]: 1 });
    }

    navigateNext() {
        const unit = this.scale === "day" ? "days" : this.scale + "s";
        this.focusDate = this.focusDate.plus({ [unit]: 1 });
    }

    navigateToday() {
        this.focusDate = luxon.DateTime.now();
    }
}
```

### Gantt Renderer

```javascript
/** @odoo-module **/
// odoo/addons/web/static/src/views/gantt/gantt_renderer.js

import { Component, useRef, onMounted, onWillUnmount, useState } from "@odoo/owl";

export class GanttRenderer extends Component {
    static template = "web.GanttRenderer";
    static props = {
        model: Object,
        archInfo: Object,
        onRecordClick: Function,
        onRecordDrop: Function,
    };

    setup() {
        this.containerRef = useRef("ganttContainer");
        this.state = useState({
            hoveredRecord: null,
        });

        onMounted(() => this.renderGantt());
        onWillUnmount(() => this.cleanup());
    }

    renderGantt() {
        // Native implementation using Canvas/SVG
        // or wrapper around Frappe Gantt for initial implementation
        this.drawGanttChart();
    }

    drawGanttChart() {
        const container = this.containerRef.el;
        const { records, groups } = this.props.model.data;
        const { dateStartField, dateStopField } = this.props.archInfo;
        const { startDate, stopDate } = this.props.model.getDateRange();

        // Calculate dimensions
        const rowHeight = 40;
        const headerHeight = 50;
        const leftPanelWidth = 200;
        const timelineWidth = container.clientWidth - leftPanelWidth;

        // Calculate time scale
        const totalDuration = stopDate.diff(startDate).as("hours");
        const pixelsPerHour = timelineWidth / totalDuration;

        // Create SVG
        const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        svg.setAttribute("width", "100%");
        svg.setAttribute("height", (groups.length || records.length) * rowHeight + headerHeight);
        svg.classList.add("o_gantt_svg");

        // Draw header
        this.drawHeader(svg, startDate, stopDate, leftPanelWidth, timelineWidth, headerHeight);

        // Draw rows
        const rowsToRender = groups.length > 0 ? groups : [{ records }];
        let yOffset = headerHeight;

        for (const group of rowsToRender) {
            if (group.name) {
                // Draw group header
                this.drawGroupHeader(svg, group.name, yOffset, leftPanelWidth);
            }

            for (const record of group.records) {
                this.drawRecord(
                    svg,
                    record,
                    startDate,
                    pixelsPerHour,
                    leftPanelWidth,
                    yOffset,
                    rowHeight
                );
                yOffset += rowHeight;
            }
        }

        container.innerHTML = "";
        container.appendChild(svg);
    }

    drawHeader(svg, startDate, stopDate, leftPanelWidth, timelineWidth, headerHeight) {
        // Draw time scale header
        const headerGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
        headerGroup.classList.add("o_gantt_header");

        // Background
        const headerBg = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        headerBg.setAttribute("width", "100%");
        headerBg.setAttribute("height", headerHeight);
        headerBg.setAttribute("fill", "#f8f9fa");
        headerGroup.appendChild(headerBg);

        // Time labels based on scale
        const scale = this.props.model.scale;
        let current = startDate;

        while (current < stopDate) {
            const x = leftPanelWidth + current.diff(startDate).as("hours") *
                (timelineWidth / stopDate.diff(startDate).as("hours"));

            const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
            text.setAttribute("x", x);
            text.setAttribute("y", headerHeight / 2 + 5);
            text.setAttribute("font-size", "12");
            text.textContent = current.toFormat(scale === "day" ? "HH:mm" : "MMM dd");
            headerGroup.appendChild(text);

            // Vertical grid line
            const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
            line.setAttribute("x1", x);
            line.setAttribute("y1", headerHeight);
            line.setAttribute("x2", x);
            line.setAttribute("y2", "100%");
            line.setAttribute("stroke", "#e0e0e0");
            line.setAttribute("stroke-width", "1");
            headerGroup.appendChild(line);

            // Increment based on scale
            current = current.plus({
                hours: scale === "day" ? 1 : 0,
                days: scale === "week" ? 1 : scale === "month" ? 1 : 0,
                months: scale === "year" ? 1 : 0,
            });
        }

        svg.appendChild(headerGroup);
    }

    drawRecord(svg, record, startDate, pixelsPerHour, leftPanelWidth, y, height) {
        const recordGroup = document.createElementNS("http://www.w3.org/2000/svg", "g");
        recordGroup.classList.add("o_gantt_record");
        recordGroup.setAttribute("data-record-id", record.id);

        // Row background
        const rowBg = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        rowBg.setAttribute("x", 0);
        rowBg.setAttribute("y", y);
        rowBg.setAttribute("width", "100%");
        rowBg.setAttribute("height", height);
        rowBg.setAttribute("fill", y % (height * 2) === 0 ? "#ffffff" : "#f8f9fa");
        recordGroup.appendChild(rowBg);

        // Left panel label
        const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
        label.setAttribute("x", 10);
        label.setAttribute("y", y + height / 2 + 5);
        label.setAttribute("font-size", "13");
        label.textContent = record.display_name;
        recordGroup.appendChild(label);

        // Gantt bar
        const barX = leftPanelWidth + record.startDate.diff(startDate).as("hours") * pixelsPerHour;
        const barWidth = record.stopDate.diff(record.startDate).as("hours") * pixelsPerHour;

        const bar = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        bar.setAttribute("x", barX);
        bar.setAttribute("y", y + 8);
        bar.setAttribute("width", Math.max(barWidth, 10));
        bar.setAttribute("height", height - 16);
        bar.setAttribute("rx", 4);
        bar.setAttribute("fill", this.getColorForRecord(record));
        bar.setAttribute("cursor", "pointer");
        bar.addEventListener("click", () => this.props.onRecordClick(record.id));
        recordGroup.appendChild(bar);

        // Progress bar (if applicable)
        if (record.progress > 0) {
            const progressBar = document.createElementNS("http://www.w3.org/2000/svg", "rect");
            progressBar.setAttribute("x", barX);
            progressBar.setAttribute("y", y + 8);
            progressBar.setAttribute("width", barWidth * (record.progress / 100));
            progressBar.setAttribute("height", height - 16);
            progressBar.setAttribute("rx", 4);
            progressBar.setAttribute("fill", "rgba(0,0,0,0.2)");
            recordGroup.appendChild(progressBar);
        }

        svg.appendChild(recordGroup);
    }

    drawGroupHeader(svg, name, y, width) {
        const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
        text.setAttribute("x", 10);
        text.setAttribute("y", y + 15);
        text.setAttribute("font-size", "14");
        text.setAttribute("font-weight", "bold");
        text.textContent = name;
        svg.appendChild(text);
    }

    getColorForRecord(record) {
        const colors = [
            "#4F46E5", "#10B981", "#F59E0B", "#EF4444",
            "#8B5CF6", "#06B6D4", "#EC4899", "#84CC16"
        ];
        const colorIndex = record.color || record.id % colors.length;
        return colors[colorIndex % colors.length];
    }

    cleanup() {
        // Cleanup any event listeners or resources
    }
}
```

### View Type Registration in ir.ui.view

```python
# odoo/addons/base/models/ir_ui_view.py (modification)

class IrUIView(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[
        ('gantt', 'Gantt'),
    ], ondelete={'gantt': 'cascade'})
```

### Gantt View XML Usage

```xml
<!-- Example usage in any module -->
<record id="planning_slot_view_gantt" model="ir.ui.view">
    <field name="name">planning.slot.gantt</field>
    <field name="model">planning.slot</field>
    <field name="arch" type="xml">
        <gantt string="Planning"
               date_start="start_datetime"
               date_stop="end_datetime"
               color="role_id"
               default_group_by="employee_id"
               progress="progress"
               decoration-danger="has_conflict">
            <field name="employee_id"/>
            <field name="role_id"/>
            <field name="has_conflict"/>
        </gantt>
    </field>
</record>
```

## 0.4 Mobile/PWA Core Infrastructure (`odoo/addons/web/static/src/core/pwa/`)

### PWA Service Worker URL Filtering Strategy (M2 Resolution)

**Issue**: The PWA service worker registers with scope `/`, which could affect all Odoo URLs including non-FSM workflows. This needs careful URL filtering to prevent unintended caching behavior for modules that don't need offline support.

**Resolution**: Implement a route whitelist that restricts offline caching and sync operations to FSM-specific routes only. Non-FSM routes are handled with pass-through behavior (no caching interference).

**Research Sources**:
- [Service Worker Scope Best Practices - web.dev](https://web.dev/learn/pwa/service-workers)
- [Service Worker URL Filtering - MDN](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API/Using_Service_Workers)
- [PWA Best Practices - Microsoft](https://learn.microsoft.com/en-us/microsoft-edge/progressive-web-apps/how-to/best-practices)

### PWA Service Worker

```javascript
// odoo/addons/web/static/src/core/pwa/service_worker.js
// Registered from web client for offline-capable pages

const CACHE_NAME = 'loomworks-v1';
const OFFLINE_URLS = [
    '/web/static/src/core/pwa/offline.html',
    '/web/static/lib/fontawesome/fonts/',
];

// --- M2 RESOLUTION: FSM-Specific Route Whitelist ---
// Only these routes receive full offline caching and sync support.
// All other routes pass through without PWA interference.
const FSM_ROUTE_WHITELIST = [
    '/fsm/',                      // FSM main routes
    '/my/tasks/',                 // Portal task views
    '/my/fsm/',                   // Portal FSM views
    '/web/dataset/call_kw/project.task/action_fsm',  // FSM actions
    '/web/dataset/call_kw/project.task/get_fsm',     // FSM data fetches
    '/web/dataset/call_kw/fsm.',                     // All FSM model calls
    '/project/task/',             // Direct task access with FSM context
    '/loomworks_fsm/',            // Module-specific routes
];

// Static assets that should be cached for FSM offline use
const FSM_STATIC_WHITELIST = [
    '/web/static/src/views/kanban/',   // Kanban view assets
    '/web/static/src/core/pwa/',       // PWA core assets
    '/loomworks_fsm/static/',          // FSM module assets
    '/web/static/lib/',                // Common libraries
];

/**
 * Check if a URL should be handled by the FSM offline system.
 * Non-matching URLs pass through without PWA interference.
 */
function isFSMRoute(url) {
    return FSM_ROUTE_WHITELIST.some(route => url.includes(route));
}

/**
 * Check if a static asset should be cached for FSM offline use.
 */
function isFSMStaticAsset(url) {
    return FSM_STATIC_WHITELIST.some(route => url.includes(route));
}

// Install event - cache critical assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(OFFLINE_URLS);
        })
    );
});

// Fetch event - network-first with offline fallback
// M2 RESOLUTION: Only intercept FSM-related routes
self.addEventListener('fetch', (event) => {
    // Only handle same-origin requests
    if (!event.request.url.startsWith(self.location.origin)) {
        return;
    }

    const url = event.request.url;

    // --- M2 RESOLUTION: Skip non-FSM routes entirely ---
    // This prevents the service worker from interfering with other modules
    // like accounting, sales, or manufacturing that don't need offline support
    if (!isFSMRoute(url) && !isFSMStaticAsset(url) && !url.includes('/web/static/')) {
        // Pass through to network without any caching
        return;
    }

    // API requests for FSM - queue for sync if offline
    if (url.includes('/web/dataset/') && isFSMRoute(url)) {
        event.respondWith(
            fetch(event.request).catch(() => {
                return handleOfflineApiRequest(event.request);
            })
        );
        return;
    }

    // Non-FSM API requests - pass through without offline handling
    if (url.includes('/web/dataset/') && !isFSMRoute(url)) {
        return; // Let the browser handle normally
    }

    // Static assets - cache-first
    if (event.request.url.includes('/web/static/')) {
        event.respondWith(
            caches.match(event.request).then((response) => {
                return response || fetch(event.request).then((fetchResponse) => {
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(event.request, fetchResponse.clone());
                    });
                    return fetchResponse;
                });
            })
        );
        return;
    }

    // Default - network first
    event.respondWith(
        fetch(event.request).catch(() => {
            return caches.match(event.request);
        })
    );
});

// Background sync for queued operations
self.addEventListener('sync', (event) => {
    if (event.tag === 'sync-pending-operations') {
        event.waitUntil(syncPendingOperations());
    }
});

async function syncPendingOperations() {
    const db = await openIndexedDB();
    const operations = await getAllPendingOperations(db);

    for (const op of operations) {
        try {
            await fetch(op.url, {
                method: op.method,
                headers: op.headers,
                body: op.body,
            });
            await removePendingOperation(db, op.id);
        } catch (e) {
            console.error('Sync failed for operation:', op.id);
        }
    }
}

async function handleOfflineApiRequest(request) {
    // Queue write operations for later sync
    if (['POST', 'PUT', 'DELETE'].includes(request.method)) {
        const body = await request.clone().text();
        await queueOperation({
            url: request.url,
            method: request.method,
            headers: Object.fromEntries(request.headers),
            body: body,
            timestamp: Date.now(),
        });
        return new Response(JSON.stringify({ queued: true }), {
            headers: { 'Content-Type': 'application/json' },
        });
    }

    // Return cached data for read operations
    return caches.match(request) || new Response(
        JSON.stringify({ error: 'offline', message: 'Data not available offline' }),
        { status: 503, headers: { 'Content-Type': 'application/json' } }
    );
}
```

### PWA Manifest and Registration

```javascript
// odoo/addons/web/static/src/core/pwa/pwa_service.js
/** @odoo-module **/

import { registry } from "@web/core/registry";

export const pwaService = {
    dependencies: [],

    start() {
        if ('serviceWorker' in navigator) {
            this.registerServiceWorker();
        }

        return {
            isOnline: () => navigator.onLine,
            queueOperation: (op) => this.queueOperation(op),
            syncNow: () => this.requestSync(),
        };
    },

    async registerServiceWorker() {
        try {
            const registration = await navigator.serviceWorker.register(
                '/web/static/src/core/pwa/service_worker.js',
                { scope: '/' }
            );
            console.log('Service Worker registered:', registration.scope);
        } catch (error) {
            console.error('Service Worker registration failed:', error);
        }
    },

    async queueOperation(operation) {
        // Store in IndexedDB for later sync
        const db = await this.openDB();
        const tx = db.transaction('pendingOperations', 'readwrite');
        await tx.objectStore('pendingOperations').add({
            ...operation,
            timestamp: Date.now(),
        });
    },

    async requestSync() {
        const registration = await navigator.serviceWorker.ready;
        if ('sync' in registration) {
            await registration.sync.register('sync-pending-operations');
        }
    },

    openDB() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open('LoomworksPWA', 1);
            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result);
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                if (!db.objectStoreNames.contains('pendingOperations')) {
                    db.createObjectStore('pendingOperations', {
                        keyPath: 'id',
                        autoIncrement: true,
                    });
                }
                if (!db.objectStoreNames.contains('cachedRecords')) {
                    db.createObjectStore('cachedRecords', {
                        keyPath: ['model', 'id'],
                    });
                }
            };
        });
    },
};

registry.category("services").add("pwa", pwaService);
```

### Responsive View Layouts

```scss
// odoo/addons/web/static/src/core/pwa/mobile.scss

// Mobile-optimized layout mixins
@mixin mobile-card {
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    margin-bottom: 12px;
    padding: 16px;
    background: white;
}

@mixin touch-target {
    min-height: 44px;
    min-width: 44px;
}

// FSM mobile view optimizations
.o_fsm_mobile {
    .o_kanban_record {
        @include mobile-card;

        .o_kanban_record_title {
            font-size: 16px;
            font-weight: 600;
        }

        .o_kanban_record_bottom {
            display: flex;
            justify-content: space-between;
            margin-top: 12px;
        }
    }

    .o_fsm_action_button {
        @include touch-target;
        padding: 12px 20px;
        border-radius: 8px;
        font-size: 16px;
    }

    .o_fsm_timer {
        font-size: 32px;
        font-family: 'SF Mono', 'Monaco', monospace;
        text-align: center;
        padding: 20px;
    }

    .o_fsm_signature_pad {
        border: 2px dashed #ccc;
        border-radius: 8px;
        background: #fafafa;
        touch-action: none; // Prevent scroll while drawing
    }
}

// Planning Gantt mobile adaptations
.o_gantt_mobile {
    .o_gantt_header {
        position: sticky;
        top: 0;
        z-index: 10;
        background: white;
    }

    .o_gantt_row {
        @include touch-target;
    }

    // Horizontal scroll for timeline
    .o_gantt_timeline {
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
    }
}

// Touch-optimized widgets
.o_touch_widget {
    @include touch-target;

    &.o_signature_widget {
        canvas {
            touch-action: none;
            width: 100%;
            height: 200px;
        }
    }

    &.o_geolocation_widget {
        .o_map_button {
            @include touch-target;
            display: flex;
            align-items: center;
            gap: 8px;
        }
    }
}
```

## 0.5 Geolocation Field Type Enhancement

### Enhanced Geolocation Widget

```javascript
// odoo/addons/base_geolocalize/static/src/widgets/geolocation_widget.js
/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class GeolocationWidget extends Component {
    static template = "base_geolocalize.GeolocationWidget";
    static props = {
        ...standardFieldProps,
        latitudeField: { type: String, optional: true },
        longitudeField: { type: String, optional: true },
    };

    setup() {
        this.state = useState({
            loading: false,
            error: null,
        });
    }

    get latitude() {
        const field = this.props.latitudeField || 'partner_latitude';
        return this.props.record.data[field];
    }

    get longitude() {
        const field = this.props.longitudeField || 'partner_longitude';
        return this.props.record.data[field];
    }

    get hasLocation() {
        return this.latitude && this.longitude;
    }

    get mapsUrl() {
        if (!this.hasLocation) return null;
        return `https://www.google.com/maps?q=${this.latitude},${this.longitude}`;
    }

    async getCurrentLocation() {
        if (!navigator.geolocation) {
            this.state.error = "Geolocation not supported";
            return;
        }

        this.state.loading = true;
        this.state.error = null;

        try {
            const position = await new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(resolve, reject, {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 60000,
                });
            });

            const latField = this.props.latitudeField || 'partner_latitude';
            const lngField = this.props.longitudeField || 'partner_longitude';

            await this.props.record.update({
                [latField]: position.coords.latitude,
                [lngField]: position.coords.longitude,
            });

        } catch (error) {
            this.state.error = this.getGeolocationError(error);
        } finally {
            this.state.loading = false;
        }
    }

    getGeolocationError(error) {
        switch (error.code) {
            case error.PERMISSION_DENIED:
                return "Location permission denied";
            case error.POSITION_UNAVAILABLE:
                return "Location unavailable";
            case error.TIMEOUT:
                return "Location request timed out";
            default:
                return "Unknown location error";
        }
    }

    openMaps() {
        if (this.mapsUrl) {
            window.open(this.mapsUrl, '_blank');
        }
    }
}

registry.category("fields").add("geolocation", GeolocationWidget);
```

---

# Module 1: loomworks_payroll

## Overview

A salary computation engine with a flexible rules framework, starting with US Federal and California state tax compliance. The system supports multiple pay structures, configurable salary rules with Python-based computation, payslip generation workflows, and PDF report output.

**CRITICAL**: This module is independently developed. No code copying from Odoo Enterprise hr_payroll. Enterprise module serves only as feature reference.

## Architecture

### Integration with Core HR Extensions

The payroll module leverages the core HR extensions defined in Part 0:

```
odoo/addons/hr_contract/              # Core (forked)
    models/
        hr_contract.py                # Filing status, allowances
        hr_payroll_structure_type.py  # Structure type model

loomworks_addons/loomworks_payroll/   # Loomworks module
    models/
        hr_payroll_structure.py       # Full structure definition
        hr_salary_rule.py             # Computation rules
        hr_payslip.py                 # Payslip processing
```

## Technical Design

### Data Models

#### hr.payroll.structure

Defines pay structures (salary templates) that group salary rules.

```python
class HrPayrollStructure(models.Model):
    _name = 'hr.payroll.structure'
    _description = 'Payroll Structure'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Reference', required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    country_id = fields.Many2one('res.country', string='Country')
    state_id = fields.Many2one('res.country.state', string='State')

    # Link to core structure type
    type_id = fields.Many2one(
        'hr.payroll.structure.type',
        string='Structure Type',
        required=True
    )

    # Rule configuration
    rule_ids = fields.Many2many('hr.salary.rule', string='Salary Rules')
    parent_id = fields.Many2one('hr.payroll.structure', string='Parent Structure')

    # Pay period
    schedule_pay = fields.Selection([
        ('weekly', 'Weekly'),
        ('bi-weekly', 'Bi-Weekly'),
        ('semi-monthly', 'Semi-Monthly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annually', 'Annually'),
    ], string='Scheduled Pay', default='monthly', required=True)

    active = fields.Boolean(default=True)
    note = fields.Text(string='Description')

    def get_all_rules(self):
        """Get all rules including from parent structures."""
        self.ensure_one()
        rules = self.rule_ids
        if self.parent_id:
            rules |= self.parent_id.get_all_rules()
        return rules.sorted('sequence')
```

#### hr.salary.rule

Individual computation rules with Python code execution.

```python
class HrSalaryRule(models.Model):
    _name = 'hr.salary.rule'
    _description = 'Salary Rule'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    code = fields.Char(required=True, help='Unique code for referencing in computations')
    sequence = fields.Integer(default=100, help='Determines computation order')

    # Category for grouping (GROSS, NET, DED, COMP, etc.)
    category_id = fields.Many2one('hr.salary.rule.category', required=True)

    # Computation method
    amount_select = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage'),
        ('code', 'Python Code'),
    ], string='Amount Type', default='fixed', required=True)

    amount_fix = fields.Float(string='Fixed Amount')
    amount_percentage = fields.Float(string='Percentage')
    amount_percentage_base = fields.Char(string='Percentage Base')
    amount_python_compute = fields.Text(string='Python Code')

    # Conditions
    condition_select = fields.Selection([
        ('none', 'Always True'),
        ('range', 'Range'),
        ('python', 'Python Expression'),
    ], string='Condition Type', default='none')
    condition_range_min = fields.Float(string='Minimum Range')
    condition_range_max = fields.Float(string='Maximum Range')
    condition_python = fields.Text(string='Python Condition')

    # Tax configuration
    is_tax = fields.Boolean(string='Is Tax Rule')
    tax_type = fields.Selection([
        ('federal_income', 'Federal Income Tax'),
        ('state_income', 'State Income Tax'),
        ('social_security', 'Social Security'),
        ('medicare', 'Medicare'),
        ('state_disability', 'State Disability Insurance'),
        ('state_unemployment', 'State Unemployment'),
        ('local', 'Local Tax'),
    ], string='Tax Type')

    # Appears on payslip
    appears_on_payslip = fields.Boolean(default=True)
    note = fields.Html(string='Description')
```

#### hr.salary.rule.category

Categories for organizing rules (BASIC, GROSS, DED, NET, COMP).

```python
class HrSalaryRuleCategory(models.Model):
    _name = 'hr.salary.rule.category'
    _description = 'Salary Rule Category'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    parent_id = fields.Many2one('hr.salary.rule.category')
    note = fields.Text()
```

#### hr.payslip

The core payslip document with computation workflow.

```python
class HrPayslip(models.Model):
    _name = 'hr.payslip'
    _description = 'Payslip'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc, id desc'

    name = fields.Char(string='Payslip Name', compute='_compute_name', store=True)
    number = fields.Char(string='Reference', readonly=True, copy=False)

    employee_id = fields.Many2one('hr.employee', required=True, tracking=True)
    contract_id = fields.Many2one('hr.contract', string='Contract')
    struct_id = fields.Many2one('hr.payroll.structure', string='Structure', required=True)

    # Period
    date_from = fields.Date(required=True, tracking=True)
    date_to = fields.Date(required=True, tracking=True)

    # State workflow
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Waiting Verification'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    # Computed lines
    line_ids = fields.One2many('hr.payslip.line', 'slip_id', string='Payslip Lines')
    input_line_ids = fields.One2many('hr.payslip.input', 'payslip_id', string='Input Lines')
    worked_days_line_ids = fields.One2many('hr.payslip.worked_days', 'payslip_id')

    # Totals
    gross_wage = fields.Monetary(compute='_compute_totals', store=True)
    net_wage = fields.Monetary(compute='_compute_totals', store=True)
    total_deductions = fields.Monetary(compute='_compute_totals', store=True)

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')

    # Batch processing
    payslip_run_id = fields.Many2one('hr.payslip.run', string='Batch')

    # Notes
    note = fields.Text()
    credit_note = fields.Boolean(string='Credit Note', help='Indicates correction payslip')
```

#### hr.payslip.line

Individual computed line items on a payslip.

```python
class HrPayslipLine(models.Model):
    _name = 'hr.payslip.line'
    _description = 'Payslip Line'
    _order = 'sequence, id'

    slip_id = fields.Many2one('hr.payslip', required=True, ondelete='cascade')
    salary_rule_id = fields.Many2one('hr.salary.rule', required=True)

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    category_id = fields.Many2one('hr.salary.rule.category')
    sequence = fields.Integer()

    quantity = fields.Float(default=1.0)
    rate = fields.Float(default=100.0)
    amount = fields.Float()
    total = fields.Float(compute='_compute_total', store=True)

    @api.depends('quantity', 'rate', 'amount')
    def _compute_total(self):
        for line in self:
            line.total = line.quantity * line.rate * line.amount / 100
```

### Computation Engine

The rule computation engine executes Python code in a sandboxed environment with access to:

```python
# Available in rule Python code context
localdict = {
    'categories': CategoryDict,      # Access computed categories (GROSS, NET, etc.)
    'rules': RuleDict,               # Access other rules by code
    'payslip': payslip,              # Current payslip record
    'employee': employee,            # Employee record
    'contract': contract,            # Contract record (with filing_status from core)
    'worked_days': worked_days,      # Worked days dictionary
    'inputs': inputs,                # Input lines dictionary
    'result': None,                  # Set computation result
    'result_qty': 1.0,               # Quantity multiplier
    'result_rate': 100.0,            # Rate percentage
}
```

Example rule for federal income tax:

```python
# Federal Income Tax (2026) - Simplified progressive brackets
# Uses IRS Publication 15-T tables
annual_gross = categories.GROSS * 12  # Annualize
filing_status = contract.filing_status or 'single'

# 2026 Single filer brackets (example)
brackets = [
    (11925, 0.10),
    (48475, 0.12),
    (103350, 0.22),
    (197300, 0.24),
    (250525, 0.32),
    (626350, 0.35),
    (float('inf'), 0.37),
]

tax = 0
prev_bracket = 0
for bracket, rate in brackets:
    if annual_gross > bracket:
        tax += (bracket - prev_bracket) * rate
        prev_bracket = bracket
    else:
        tax += (annual_gross - prev_bracket) * rate
        break

# De-annualize and set result
result = -tax / 12
```

### Tax Framework

#### US Federal Taxes (2026)

| Tax | Employee Rate | Employer Rate | Wage Base |
|-----|---------------|---------------|-----------|
| Social Security | 6.20% | 6.20% | $184,500 |
| Medicare | 1.45% | 1.45% | No limit |
| Additional Medicare | 0.9% (>$200k) | N/A | N/A |
| Federal Income Tax | Progressive brackets | N/A | N/A |

#### California State Taxes (2026)

| Tax | Rate | Notes |
|-----|------|-------|
| State Income Tax (PIT) | Progressive brackets | DE-4 filing status |
| State Disability Insurance (SDI) | 1.3% | No wage cap (per SB 951) |
| Employment Training Tax (ETT) | 0.1% | Employer-paid, first $7k |
| Unemployment Insurance (UI) | 1.5% - 6.2% | Employer-paid, Schedule F+ |

### Payslip PDF Report

QWeb template for payslip PDF generation:

```xml
<template id="report_payslip">
    <t t-call="web.html_container">
        <t t-foreach="docs" t-as="o">
            <t t-call="web.external_layout">
                <div class="page">
                    <h2>Payslip: <span t-field="o.name"/></h2>

                    <!-- Employee Info -->
                    <div class="row">
                        <div class="col-6">
                            <strong>Employee:</strong> <span t-field="o.employee_id.name"/>
                        </div>
                        <div class="col-6">
                            <strong>Period:</strong>
                            <span t-field="o.date_from"/> - <span t-field="o.date_to"/>
                        </div>
                    </div>

                    <!-- Earnings -->
                    <h4>Earnings</h4>
                    <table class="table table-sm">
                        <t t-foreach="o.line_ids.filtered(lambda l: l.total >= 0)" t-as="line">
                            <tr>
                                <td t-field="line.name"/>
                                <td class="text-end" t-field="line.total"
                                    t-options="{'widget': 'monetary'}"/>
                            </tr>
                        </t>
                    </table>

                    <!-- Deductions -->
                    <h4>Deductions</h4>
                    <table class="table table-sm">
                        <t t-foreach="o.line_ids.filtered(lambda l: l.total < 0)" t-as="line">
                            <tr>
                                <td t-field="line.name"/>
                                <td class="text-end" t-field="line.total"
                                    t-options="{'widget': 'monetary'}"/>
                            </tr>
                        </t>
                    </table>

                    <!-- Totals -->
                    <div class="row mt-4">
                        <div class="col-6 offset-6">
                            <table class="table table-sm">
                                <tr><td>Gross Pay</td>
                                    <td class="text-end" t-field="o.gross_wage"/></tr>
                                <tr><td>Total Deductions</td>
                                    <td class="text-end" t-field="o.total_deductions"/></tr>
                                <tr class="fw-bold"><td>Net Pay</td>
                                    <td class="text-end" t-field="o.net_wage"/></tr>
                            </table>
                        </div>
                    </div>
                </div>
            </t>
        </t>
    </t>
</template>
```

### Default Data - US Federal + California

Provide initial salary structures and rules for:

1. **US Salaried Employee** structure
2. **US Hourly Employee** structure
3. **California Salaried Employee** structure (inherits from US Salaried)

Default rules:
- `BASIC` - Base salary/hourly wage
- `GROSS` - Gross wages
- `FED_INC` - Federal income tax withholding
- `SS_EE` - Social Security (employee)
- `MED_EE` - Medicare (employee)
- `CA_PIT` - California Personal Income Tax
- `CA_SDI` - California State Disability Insurance
- `NET` - Net pay calculation

### Security

Access groups:
- `loomworks_payroll.group_payroll_user` - View payslips, run computations
- `loomworks_payroll.group_payroll_manager` - Full access, configure rules
- `loomworks_payroll.group_payroll_admin` - System configuration, tax tables

Record rules ensure employees see only their own payslips unless user has manager access.

---

# Module 2: loomworks_fsm (Field Service Management)

## Overview

A mobile-first field service management module extending Odoo's project.task model. Enables dispatching technicians to customer locations, tracking work completion, capturing signatures, and integrating with timesheets. Designed for offline capability with sync-when-connected patterns.

**CRITICAL**: This module is independently developed. No code copying from Odoo Enterprise industry_fsm.

## Architecture

### Integration with Core Modifications

FSM leverages the core extensions from Part 0:

```
odoo/addons/project/                  # Core (forked)
    models/
        project_task.py               # is_fsm, timer, signature fields
        project_project.py            # is_fsm project flag

odoo/addons/web/static/src/core/pwa/  # Core PWA infrastructure
    service_worker.js                 # Offline support
    pwa_service.js                    # Queue operations

loomworks_addons/loomworks_fsm/       # Loomworks module
    models/
        project_task_fsm.py           # FSM-specific extensions
        fsm_worksheet.py              # Worksheet templates
```

## Technical Design

### Data Models

#### project.task (Extension)

Extend project.task for field service capabilities (building on core FSM fields):

```python
class ProjectTaskFSM(models.Model):
    _inherit = 'project.task'

    # Extended FSM fields (core provides is_fsm, timer, signature)
    fsm_user_id = fields.Many2one(
        'res.users',
        string='Field Technician',
        domain=[('share', '=', False)]
    )

    # Worksheets
    worksheet_template_id = fields.Many2one('fsm.worksheet.template')
    worksheet_data = fields.Json(string='Worksheet Data')

    # Materials/Products used
    material_line_ids = fields.One2many('fsm.material.line', 'task_id')

    # Photos/Attachments
    photo_ids = fields.One2many(
        'ir.attachment',
        'res_id',
        domain=[('res_model', '=', 'project.task'), ('mimetype', 'like', 'image%')]
    )

    # GPS check-in/out (uses core geolocation widget)
    checkin_latitude = fields.Float()
    checkin_longitude = fields.Float()
    checkin_time = fields.Datetime()
    checkout_latitude = fields.Float()
    checkout_longitude = fields.Float()
    checkout_time = fields.Datetime()

    # Computed
    fsm_done = fields.Boolean(string='Task Done', default=False)
    total_hours_spent = fields.Float(compute='_compute_total_hours', store=True)

    @api.depends('timesheet_ids.unit_amount')
    def _compute_total_hours(self):
        for task in self:
            task.total_hours_spent = sum(task.timesheet_ids.mapped('unit_amount'))

    def action_fsm_checkin(self):
        """Record GPS check-in using browser geolocation."""
        self.ensure_one()
        # Geolocation captured via frontend widget, saved here
        return True

    def action_fsm_checkout(self):
        """Record GPS checkout and stop timer."""
        self.ensure_one()
        self.action_timer_stop()
        return True
```

#### fsm.worksheet.template

Configurable worksheet templates for different service types:

```python
class FSMWorksheetTemplate(models.Model):
    _name = 'fsm.worksheet.template'
    _description = 'FSM Worksheet Template'

    name = fields.Char(required=True)
    code = fields.Char(required=True)

    # Template definition (JSON schema)
    field_ids = fields.One2many('fsm.worksheet.field', 'template_id')

    # Usage
    project_ids = fields.Many2many('project.project', string='Projects')
    active = fields.Boolean(default=True)
```

#### fsm.worksheet.field

Individual fields within a worksheet template:

```python
class FSMWorksheetField(models.Model):
    _name = 'fsm.worksheet.field'
    _description = 'Worksheet Field'
    _order = 'sequence, id'

    template_id = fields.Many2one('fsm.worksheet.template', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)

    name = fields.Char(string='Label', required=True)
    technical_name = fields.Char(required=True)
    field_type = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('checkbox', 'Checkbox'),
        ('select', 'Selection'),
        ('date', 'Date'),
        ('datetime', 'Date & Time'),
        ('photo', 'Photo'),
        ('signature', 'Signature'),
        ('section', 'Section Header'),
    ], required=True, default='text')

    # For selection fields
    selection_options = fields.Text(help='One option per line')

    required = fields.Boolean(default=False)
    placeholder = fields.Char()
```

#### fsm.material.line

Materials/products used during service:

```python
class FSMMaterialLine(models.Model):
    _name = 'fsm.material.line'
    _description = 'FSM Material Used'

    task_id = fields.Many2one('project.task', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', required=True)
    quantity = fields.Float(default=1.0)

    # Pricing (optional - for invoicing)
    price_unit = fields.Float(related='product_id.list_price')
    subtotal = fields.Float(compute='_compute_subtotal', store=True)

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit
```

### Mobile Interface

#### FSM Mobile Views (XML)

Mobile-optimized kanban view leveraging core PWA styling:

```xml
<record id="project_task_view_kanban_fsm_mobile" model="ir.ui.view">
    <field name="name">project.task.kanban.fsm.mobile</field>
    <field name="model">project.task</field>
    <field name="arch" type="xml">
        <kanban class="o_fsm_mobile o_kanban_mobile"
                default_group_by="stage_id"
                quick_create="false">
            <field name="id"/>
            <field name="name"/>
            <field name="partner_id"/>
            <field name="partner_latitude"/>
            <field name="partner_longitude"/>
            <field name="planned_date_start"/>
            <field name="fsm_done"/>
            <field name="timer_start"/>
            <templates>
                <t t-name="kanban-card">
                    <div class="o_kanban_record o_fsm_task_card">
                        <div class="o_kanban_record_title">
                            <field name="name"/>
                        </div>
                        <div class="o_kanban_record_subtitle">
                            <field name="partner_id"/>
                        </div>
                        <div class="o_fsm_location" t-if="record.partner_latitude.raw_value">
                            <button type="object" name="action_open_maps"
                                    class="btn btn-link p-0">
                                <i class="fa fa-map-marker"/> Open in Maps
                            </button>
                        </div>
                        <div class="o_kanban_record_bottom">
                            <field name="planned_date_start" widget="date"/>
                            <span t-if="record.fsm_done.raw_value"
                                  class="badge bg-success">Done</span>
                        </div>
                    </div>
                </t>
            </templates>
        </kanban>
    </field>
</record>
```

#### Owl Components

**FSM Task Card** - Kanban card optimized for mobile:

```javascript
/** @odoo-module **/
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class FSMTaskCard extends Component {
    static template = "loomworks_fsm.TaskCard";
    static props = {
        task: Object,
        onSelect: Function,
    };

    setup() {
        this.pwa = useService("pwa");
        this.state = useState({
            timerRunning: false,
            elapsed: 0,
        });
    }

    get formattedAddress() {
        return this.props.task.partner_address || 'No address';
    }

    async openMaps() {
        const { partner_latitude, partner_longitude } = this.props.task;
        if (partner_latitude && partner_longitude) {
            window.open(
                `https://maps.google.com/?q=${partner_latitude},${partner_longitude}`,
                '_blank'
            );
        }
    }

    async startTimer() {
        // Queue operation for offline sync if needed
        if (!this.pwa.isOnline()) {
            await this.pwa.queueOperation({
                type: 'timer_start',
                taskId: this.props.task.id,
                timestamp: Date.now(),
            });
        }
        // Update UI immediately (optimistic update)
        this.state.timerRunning = true;
    }
}
```

**Signature Capture Component** (uses core signature widget):

```javascript
/** @odoo-module **/
import { Component, useRef, onMounted } from "@odoo/owl";

export class SignatureCapture extends Component {
    static template = "loomworks_fsm.SignatureCapture";
    static props = {
        onSave: Function,
        width: { type: Number, optional: true },
        height: { type: Number, optional: true },
    };

    setup() {
        this.canvasRef = useRef("canvas");
        this.isDrawing = false;
        this.lastX = 0;
        this.lastY = 0;

        onMounted(() => {
            this.initCanvas();
        });
    }

    initCanvas() {
        const canvas = this.canvasRef.el;
        this.ctx = canvas.getContext('2d');
        this.ctx.strokeStyle = '#000';
        this.ctx.lineWidth = 2;
        this.ctx.lineCap = 'round';

        // Touch events for mobile
        canvas.addEventListener('touchstart', (e) => this.startDrawing(e), { passive: false });
        canvas.addEventListener('touchmove', (e) => this.draw(e), { passive: false });
        canvas.addEventListener('touchend', () => this.stopDrawing());

        // Mouse events for desktop testing
        canvas.addEventListener('mousedown', (e) => this.startDrawing(e));
        canvas.addEventListener('mousemove', (e) => this.draw(e));
        canvas.addEventListener('mouseup', () => this.stopDrawing());
    }

    getCoordinates(e) {
        const canvas = this.canvasRef.el;
        const rect = canvas.getBoundingClientRect();
        const touch = e.touches ? e.touches[0] : e;
        return {
            x: touch.clientX - rect.left,
            y: touch.clientY - rect.top,
        };
    }

    startDrawing(e) {
        e.preventDefault();
        this.isDrawing = true;
        const coords = this.getCoordinates(e);
        this.lastX = coords.x;
        this.lastY = coords.y;
    }

    draw(e) {
        if (!this.isDrawing) return;
        e.preventDefault();

        const coords = this.getCoordinates(e);
        this.ctx.beginPath();
        this.ctx.moveTo(this.lastX, this.lastY);
        this.ctx.lineTo(coords.x, coords.y);
        this.ctx.stroke();

        this.lastX = coords.x;
        this.lastY = coords.y;
    }

    stopDrawing() {
        this.isDrawing = false;
    }

    clear() {
        const canvas = this.canvasRef.el;
        this.ctx.clearRect(0, 0, canvas.width, canvas.height);
    }

    save() {
        const canvas = this.canvasRef.el;
        const dataUrl = canvas.toDataURL('image/png');
        // Remove data URL prefix, keep base64
        const base64 = dataUrl.split(',')[1];
        this.props.onSave(base64);
    }
}
```

### Offline Capability (Leveraging Core PWA)

FSM uses the core PWA infrastructure for offline support:

```javascript
/** @odoo-module **/
import { useService } from "@web/core/utils/hooks";

export class FSMOfflineManager {
    constructor() {
        this.pwa = useService("pwa");
    }

    async saveTaskOffline(task) {
        // Cache task data locally
        const db = await this.pwa.openDB();
        const tx = db.transaction('cachedRecords', 'readwrite');
        await tx.objectStore('cachedRecords').put({
            model: 'project.task',
            id: task.id,
            data: task,
            timestamp: Date.now(),
        });
    }

    async queueTimerAction(taskId, action) {
        await this.pwa.queueOperation({
            url: '/web/dataset/call_kw/project.task/' + action,
            method: 'POST',
            body: JSON.stringify({
                model: 'project.task',
                method: action,
                args: [[taskId]],
                kwargs: {},
            }),
        });
    }

    async queueSignatureSave(taskId, signatureBase64) {
        await this.pwa.queueOperation({
            url: '/web/dataset/call_kw/project.task/write',
            method: 'POST',
            body: JSON.stringify({
                model: 'project.task',
                method: 'write',
                args: [[taskId], {
                    customer_signature: signatureBase64,
                    customer_signed_on: new Date().toISOString(),
                }],
                kwargs: {},
            }),
        });
    }
}
```

### Route Optimization Hints

Provide basic route optimization suggestions (not full optimization engine):

```python
class FSMRouteHelper(models.TransientModel):
    _name = 'fsm.route.helper'
    _description = 'FSM Route Helper'

    @api.model
    def get_suggested_route(self, task_ids, start_location=None):
        """
        Returns tasks ordered by proximity using nearest-neighbor heuristic.
        For production use, integrate with Google Maps Directions API or similar.
        """
        tasks = self.env['project.task'].browse(task_ids)

        if start_location:
            current_lat, current_lng = start_location
        else:
            # Use first task or company location
            current_lat = tasks[0].partner_latitude or 0
            current_lng = tasks[0].partner_longitude or 0

        ordered = []
        remaining = list(tasks)

        while remaining:
            # Find nearest task
            nearest = min(remaining, key=lambda t: self._distance(
                current_lat, current_lng,
                t.partner_latitude or 0, t.partner_longitude or 0
            ))
            ordered.append(nearest.id)
            current_lat = nearest.partner_latitude or current_lat
            current_lng = nearest.partner_longitude or current_lng
            remaining.remove(nearest)

        return ordered

    def _distance(self, lat1, lng1, lat2, lng2):
        """Haversine distance calculation"""
        from math import radians, sin, cos, sqrt, atan2

        R = 6371  # Earth's radius in km
        dlat = radians(lat2 - lat1)
        dlng = radians(lng2 - lng1)

        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))

        return R * c
```

### Time Tracking Integration

Automatically create timesheet entries from FSM timer:

```python
def action_timer_stop(self):
    self.ensure_one()
    if not self.timer_start:
        return

    end_time = fields.Datetime.now()
    hours = (end_time - self.timer_start).total_seconds() / 3600

    # Create timesheet entry
    self.env['account.analytic.line'].create({
        'task_id': self.id,
        'project_id': self.project_id.id,
        'employee_id': self.env.user.employee_id.id,
        'name': f'FSM: {self.name}',
        'unit_amount': hours,
        'date': fields.Date.today(),
    })

    self.write({
        'timer_start': False,
        'timer_pause': False,
    })
```

### Security

Access groups:
- `loomworks_fsm.group_fsm_user` - Field technicians, see assigned tasks
- `loomworks_fsm.group_fsm_dispatcher` - Assign tasks, view all technicians
- `loomworks_fsm.group_fsm_manager` - Full configuration access

Record rules:
- Technicians see only their assigned tasks
- Dispatchers see all tasks in their company
- Customer portal users see only their own service requests

---

# Module 3: loomworks_planning (Workforce Scheduling)

## Overview

A visual workforce scheduling module with Gantt view capabilities for shift planning, resource allocation, and conflict detection. Integrates with HR employees for availability tracking and supports recurring shift templates.

**CRITICAL**: This module is independently developed. No code copying from Odoo Enterprise planning module.

## Architecture

### Integration with Core Gantt View

Planning uses the native Gantt view type implemented in Part 0:

```
odoo/addons/web/static/src/views/gantt/  # Core Gantt view
    gantt_view.js
    gantt_controller.js
    gantt_model.js
    gantt_renderer.js

loomworks_addons/loomworks_planning/     # Loomworks module
    models/
        planning_slot.py
        planning_role.py
    views/
        planning_views.xml               # Uses <gantt> view type
```

## Technical Design

### Data Models

#### planning.slot

Core model for scheduled shifts/assignments:

```python
class PlanningSlot(models.Model):
    _name = 'planning.slot'
    _description = 'Planning Slot'
    _inherit = ['mail.thread']
    _order = 'start_datetime'

    name = fields.Char(compute='_compute_name', store=True)

    # Resource assignment
    resource_id = fields.Many2one('resource.resource', string='Resource')
    employee_id = fields.Many2one('hr.employee', string='Employee',
        compute='_compute_employee', store=True, readonly=False)
    user_id = fields.Many2one('res.users', related='employee_id.user_id')

    # Timing
    start_datetime = fields.Datetime(required=True, tracking=True)
    end_datetime = fields.Datetime(required=True, tracking=True)
    allocated_hours = fields.Float(compute='_compute_allocated_hours', store=True)

    # Allocation percentage (for partial assignments)
    allocated_percentage = fields.Float(default=100.0)

    # Role/Position
    role_id = fields.Many2one('planning.role', string='Role')

    # Project/Task link
    project_id = fields.Many2one('project.project')
    task_id = fields.Many2one('project.task')

    # Recurrence
    recurrence_id = fields.Many2one('planning.recurrence')
    recurrency_update = fields.Selection([
        ('this', 'This Shift Only'),
        ('subsequent', 'This and Following'),
        ('all', 'All Occurrences'),
    ], default='this')

    # Template
    template_id = fields.Many2one('planning.slot.template')

    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True)

    # Publication
    is_published = fields.Boolean(default=False)
    publication_warning = fields.Boolean(compute='_compute_publication_warning')

    # Conflict detection
    has_conflict = fields.Boolean(compute='_compute_conflicts', store=True)
    conflict_description = fields.Char(compute='_compute_conflicts', store=True)

    # Progress (for Gantt view)
    progress = fields.Float(compute='_compute_progress', store=True)

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    color = fields.Integer(related='role_id.color')

    @api.depends('start_datetime', 'end_datetime')
    def _compute_allocated_hours(self):
        for slot in self:
            if slot.start_datetime and slot.end_datetime:
                delta = slot.end_datetime - slot.start_datetime
                slot.allocated_hours = delta.total_seconds() / 3600
            else:
                slot.allocated_hours = 0

    @api.depends('state')
    def _compute_progress(self):
        for slot in self:
            slot.progress = 100 if slot.state == 'done' else 0

    @api.depends('employee_id', 'start_datetime', 'end_datetime')
    def _compute_conflicts(self):
        for slot in self:
            slot.has_conflict = False
            slot.conflict_description = False

            if not slot.employee_id or not slot.start_datetime or not slot.end_datetime:
                continue

            # Check overlapping slots
            overlapping = self.search([
                ('id', '!=', slot.id),
                ('employee_id', '=', slot.employee_id.id),
                ('state', 'not in', ['cancelled']),
                ('start_datetime', '<', slot.end_datetime),
                ('end_datetime', '>', slot.start_datetime),
            ])

            if overlapping:
                slot.has_conflict = True
                slot.conflict_description = f"Overlaps with: {', '.join(overlapping.mapped('name'))}"

            # Check employee availability (time off)
            leave = self.env['hr.leave'].search([
                ('employee_id', '=', slot.employee_id.id),
                ('state', '=', 'validate'),
                ('date_from', '<=', slot.end_datetime),
                ('date_to', '>=', slot.start_datetime),
            ], limit=1)

            if leave:
                slot.has_conflict = True
                slot.conflict_description = f"Employee on leave: {leave.holiday_status_id.name}"
```

#### planning.role

Roles/positions for shift assignments:

```python
class PlanningRole(models.Model):
    _name = 'planning.role'
    _description = 'Planning Role'

    name = fields.Char(required=True)
    color = fields.Integer(string='Color Index')

    # Default hourly cost for budgeting
    default_hourly_cost = fields.Float()

    # Employees who can fill this role
    employee_ids = fields.Many2many('hr.employee', string='Qualified Employees')

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    active = fields.Boolean(default=True)
```

#### planning.slot.template

Reusable shift templates:

```python
class PlanningSlotTemplate(models.Model):
    _name = 'planning.slot.template'
    _description = 'Shift Template'

    name = fields.Char(required=True)
    role_id = fields.Many2one('planning.role')

    # Time pattern
    start_time = fields.Float(string='Start Time', help='Hour of day (0-24)')
    duration = fields.Float(string='Duration (hours)')

    # Default assignment
    employee_id = fields.Many2one('hr.employee')

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    active = fields.Boolean(default=True)
```

#### planning.recurrence

Recurring shift patterns:

```python
class PlanningRecurrence(models.Model):
    _name = 'planning.recurrence'
    _description = 'Planning Recurrence'

    slot_ids = fields.One2many('planning.slot', 'recurrence_id')

    # Recurrence pattern
    repeat_type = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ], default='weekly', required=True)

    repeat_interval = fields.Integer(default=1, string='Repeat Every')

    # For weekly: which days
    mon = fields.Boolean('Monday')
    tue = fields.Boolean('Tuesday')
    wed = fields.Boolean('Wednesday')
    thu = fields.Boolean('Thursday')
    fri = fields.Boolean('Friday')
    sat = fields.Boolean('Saturday')
    sun = fields.Boolean('Sunday')

    # End condition
    repeat_until = fields.Date(string='Repeat Until')
    repeat_count = fields.Integer(string='Number of Occurrences')

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
```

### Gantt View Implementation (Using Core View Type)

#### Gantt View Definition

```xml
<record id="planning_slot_view_gantt" model="ir.ui.view">
    <field name="name">planning.slot.gantt</field>
    <field name="model">planning.slot</field>
    <field name="arch" type="xml">
        <gantt string="Planning"
               date_start="start_datetime"
               date_stop="end_datetime"
               color="role_id"
               default_group_by="employee_id"
               progress="progress"
               decoration-danger="has_conflict"
               display_unavailability="true">
            <field name="employee_id"/>
            <field name="role_id"/>
            <field name="has_conflict"/>
            <field name="conflict_description"/>
            <field name="allocated_hours"/>
        </gantt>
    </field>
</record>

<record id="planning_slot_action" model="ir.actions.act_window">
    <field name="name">Planning</field>
    <field name="res_model">planning.slot</field>
    <field name="view_mode">gantt,list,form,calendar</field>
</record>
```

### Employee Availability

Integration with HR time off:

```python
class HrEmployeePlanning(models.Model):
    _inherit = 'hr.employee'

    planning_slot_ids = fields.One2many('planning.slot', 'employee_id')

    def get_availability(self, date_from, date_to):
        """
        Returns available hours for planning in the given date range.
        Considers working schedule and approved time off.
        """
        self.ensure_one()

        # Get working hours from resource calendar
        calendar = self.resource_calendar_id or self.company_id.resource_calendar_id
        if not calendar:
            return 0

        # Calculate total working hours
        working_hours = calendar.get_work_hours_count(
            date_from, date_to,
            compute_leaves=True,
            resource=self.resource_id,
        )

        # Subtract already allocated hours
        allocated = sum(self.planning_slot_ids.filtered(
            lambda s: s.start_datetime >= date_from and
                      s.end_datetime <= date_to and
                      s.state not in ['cancelled']
        ).mapped('allocated_hours'))

        return max(0, working_hours - allocated)
```

### Conflict Detection

Real-time conflict checking with visual indicators:

```python
@api.constrains('employee_id', 'start_datetime', 'end_datetime')
def _check_overlap(self):
    for slot in self:
        if slot.has_conflict and slot.state == 'published':
            raise ValidationError(_(
                "Cannot publish slot with conflicts: %s"
            ) % slot.conflict_description)
```

### Shift Templates and Quick Assignment

Wizard for batch shift creation:

```python
class PlanningSlotQuickCreate(models.TransientModel):
    _name = 'planning.slot.quick.create'
    _description = 'Quick Create Shifts'

    template_id = fields.Many2one('planning.slot.template', required=True)
    employee_ids = fields.Many2many('hr.employee', required=True)

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)

    # Recurrence
    create_recurrence = fields.Boolean()
    repeat_type = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
    ], default='weekly')

    def action_create_slots(self):
        slots = self.env['planning.slot']
        template = self.template_id

        current_date = self.date_from
        while current_date <= self.date_to:
            for employee in self.employee_ids:
                # Calculate start/end datetime from template time
                start_dt = datetime.combine(
                    current_date,
                    datetime.min.time()
                ) + timedelta(hours=template.start_time)

                end_dt = start_dt + timedelta(hours=template.duration)

                slots |= self.env['planning.slot'].create({
                    'template_id': template.id,
                    'employee_id': employee.id,
                    'role_id': template.role_id.id,
                    'start_datetime': start_dt,
                    'end_datetime': end_dt,
                    'state': 'draft',
                })

            current_date += timedelta(days=1)

        return {
            'type': 'ir.actions.act_window',
            'name': 'Created Slots',
            'res_model': 'planning.slot',
            'domain': [('id', 'in', slots.ids)],
            'view_mode': 'gantt,list,form',
        }
```

### Security

Access groups:
- `loomworks_planning.group_planning_user` - View own schedule
- `loomworks_planning.group_planning_manager` - Create/edit all schedules
- `loomworks_planning.group_planning_admin` - System configuration

Record rules:
- Users see only their own slots unless they have manager access
- Managers see all slots in their company

---

# Implementation Tasks

## Phase 0: Core Fork Modifications (Week 26-27)

- [ ] 0.1 Extend hr.contract with payroll fields (filing_status, allowances)
- [ ] 0.2 Create hr.payroll.structure.type model in core
- [ ] 0.3 Add FSM fields to core project.task (is_fsm, timer, signature)
- [ ] 0.4 Add is_fsm flag to project.project
- [ ] 0.5 Implement native Gantt view type in web client
- [ ] 0.6 Create Gantt arch parser, model, controller, renderer
- [ ] 0.7 Register Gantt in ir.ui.view type selection
- [ ] 0.8 Implement PWA service worker infrastructure
- [ ] 0.9 Create pwa_service for offline queue management
- [ ] 0.10 Add mobile.scss responsive styles
- [ ] 0.11 Enhance geolocation widget with capture button
- [ ] 0.12 Write unit tests for core modifications

## Phase 1: loomworks_payroll (Week 27-28)

- [ ] 1.1 Create module structure and manifest
- [ ] 1.2 Implement hr.payroll.structure model (using core type)
- [ ] 1.3 Implement hr.salary.rule and category models
- [ ] 1.4 Implement hr.payslip model with computation engine
- [ ] 1.5 Create rule evaluation sandbox and localdict
- [ ] 1.6 Implement US Federal tax rules (2026 brackets)
- [ ] 1.7 Implement California state tax rules (PIT, SDI)
- [ ] 1.8 Create payslip PDF report template
- [ ] 1.9 Add default data (structures, rules, categories)
- [ ] 1.10 Create security groups and record rules
- [ ] 1.11 Write unit tests for computation engine
- [ ] 1.12 Create user documentation

## Phase 2: loomworks_fsm (Week 28-29)

- [ ] 2.1 Create module structure and manifest
- [ ] 2.2 Extend project.task with FSM-specific fields (building on core)
- [ ] 2.3 Create fsm.worksheet.template and field models
- [ ] 2.4 Implement fsm.material.line model
- [ ] 2.5 Create signature capture Owl component
- [ ] 2.6 Create FSM mobile-optimized views (kanban, form)
- [ ] 2.7 Implement timer start/stop with timesheet integration
- [ ] 2.8 Create route optimization helper
- [ ] 2.9 Integrate with core PWA for offline sync
- [ ] 2.10 Add security groups and record rules
- [ ] 2.11 Write unit tests
- [ ] 2.12 Create mobile usage documentation

## Phase 3: loomworks_planning (Week 29-30)

- [ ] 3.1 Create module structure and manifest
- [ ] 3.2 Implement planning.slot model
- [ ] 3.3 Implement planning.role model
- [ ] 3.4 Implement planning.slot.template model
- [ ] 3.5 Implement planning.recurrence model
- [ ] 3.6 Create Gantt view definition (using core view type)
- [ ] 3.7 Style Gantt for planning colors and conflict indicators
- [ ] 3.8 Implement conflict detection
- [ ] 3.9 Add employee availability calculations
- [ ] 3.10 Create quick shift creation wizard
- [ ] 3.11 Add security groups and record rules
- [ ] 3.12 Write unit tests
- [ ] 3.13 Create planning documentation

---

# Success Criteria

## Core Fork Modifications

1. Native Gantt view renders planning slots with drag-drop
2. PWA service worker caches offline data successfully
3. Core FSM fields on project.task work with existing projects
4. Geolocation widget captures device location on mobile
5. Mobile styles provide touch-friendly interface

## loomworks_payroll

1. Payslips compute correctly for US Federal taxes
2. California state taxes (PIT, SDI) calculate accurately
3. PDF payslips generate with all line items
4. Batch payslip processing works for multiple employees
5. Salary rules with Python code execute in sandbox
6. Tax withholding matches IRS/EDD 2026 tables (within rounding)

## loomworks_fsm

1. Field technicians can view assigned tasks on mobile
2. Timer tracking creates timesheet entries
3. Customer signature capture works on touch devices
4. Worksheet data saves and displays correctly
5. Route suggestions provide reasonable ordering
6. Photos attach to tasks successfully
7. Offline operations queue and sync when online

## loomworks_planning

1. Native Gantt view displays slots with drag-drop editing
2. Conflict detection identifies overlapping assignments
3. Employee availability respects time off
4. Shift templates create slots correctly
5. Recurrence generates future slots
6. Published slots visible to assigned employees

---

# Research References

## Odoo Core Architecture

- [Odoo 18 View Architectures](https://www.odoo.com/documentation/18.0/developer/reference/user_interface/view_architectures.html)
- [Odoo Web Client Architecture - DeepWiki](https://deepwiki.com/odoo/odoo/3-web-client-architecture)
- [Odoo 18 Framework Overview](https://www.odoo.com/documentation/18.0/developer/reference/frontend/framework_overview.html)
- [Custom View Implementation Tutorial](https://www.odoo.com/documentation/18.0/developer/howtos/javascript_view)

## PWA and Mobile

- [Odoo 18 Mobile Apps Documentation](https://www.odoo.com/documentation/18.0/administration/mobile.html)
- [Odoo 18 Point of Sale PWA](https://sdlccorp.com/post/odoo-18-point-of-sale-pwa/)
- [PWA for Odoo - Future of Mobile Apps](https://medium.com/@jacobweber005/the-future-of-mobile-odoo-apps-for-enterprises-530bae14c751)
- [Service Worker Scope Best Practices - web.dev](https://web.dev/learn/pwa/service-workers) - M2 Resolution research
- [Service Worker URL Filtering - MDN](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API/Using_Service_Workers)
- [PWA Best Practices - Microsoft](https://learn.microsoft.com/en-us/microsoft-edge/progressive-web-apps/how-to/best-practices)

## Geolocation

- [Odoo 18 Geolocation Integration](https://www.odoo.com/documentation/18.0/applications/general/integrations/geolocation.html)
- [Partner Geolocation Module](https://apps.odoo.com/apps/modules/18.0/hoz_partner_geolocation)

## Payroll

- [2026 Federal Payroll Tax Rates - Abacus Payroll](https://abacuspay.com/resources/payroll-tax-wage-rates/2026-federal-payroll-tax-rates/)
- [IRS General Instructions for Forms W-2 and W-3 (2026)](https://www.irs.gov/instructions/iw2w3)
- [California EDD Contribution Rates 2026](https://edd.ca.gov/en/payroll_taxes/rates_and_withholding/)
- [California 2026 SDI Rate Changes](https://vensure.com/employment-law-updates/reminder-for-california-employers-2026-state-disability-insurance-rate-di-pfl-benefit-changes/)
- [Payroll Software Architecture - Medium](https://medium.com/pythoneers/software-architecture-snippets-payroll-app-9626d0552cfa)

## Field Service Management

- [Field Service Management 2026 - Flowdit](https://flowdit.com/field-service-management/)
- [15 FSM Best Practices - FieldEx](https://www.fieldex.com/en/blog/field-service-management-best-practices)
- [Capture E-Signatures with Lightning Web Components - Salesforce](https://developer.salesforce.com/blogs/2023/07/capture-e-signatures-with-lightning-web-components-on-mobile)
- [D365 Field Service Signature Capture](https://www.microsoft.com/en-us/dynamics-365/blog/it-professional/2024/04/01/capture-customer-signatures-with-the-new-signature-control-in-dynamics-365-field-service-mobile/)

## Gantt Libraries

- [Top 6 JavaScript Gantt Libraries 2026 - DEV](https://dev.to/lenormor/top-6-javascript-gantt-task-scheduling-libraries-in-2026-30mj)
- [Best JavaScript Gantt Chart Libraries 2025-2026 - AnyChart](https://www.anychart.com/blog/2025/11/05/best-javascript-gantt-chart-libraries/)
- [Frappe Gantt - GitHub](https://github.com/frappe/gantt)
- [SVAR React Gantt](https://svar.dev/blog/top-react-gantt-charts/)

## Odoo Development

- [Odoo 18 Developer Documentation](https://www.odoo.com/documentation/18.0/developer.html)
- [Odoo Model Inheritance](https://www.odoo.com/documentation/18.0/developer/tutorials/server_framework_101/12_inheritance)
