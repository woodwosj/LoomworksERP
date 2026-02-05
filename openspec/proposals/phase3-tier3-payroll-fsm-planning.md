# Change: Phase 3 Tier 3 - Payroll, FSM, and Planning Modules

## Why

Loomworks ERP requires comprehensive workforce management capabilities to compete with enterprise ERP solutions. Phase 3 Tier 3 delivers three critical modules: payroll for salary computation and tax compliance, field service management (FSM) for mobile workforce operations, and workforce planning with visual scheduling. These modules address core business needs for companies with field workers, shift-based operations, and US-based employees requiring compliant payroll processing.

## What Changes

### New Modules

- **NEW** `loomworks_payroll` - Salary computation engine with rules-based calculations (US locale: Federal + California)
- **NEW** `loomworks_fsm` - Mobile-first field service management extending project.task
- **NEW** `loomworks_planning` - Visual workforce scheduling with Gantt views and shift management

### Dependencies

- `hr` (Odoo Community) - Employee management base
- `project` (Odoo Community) - Task management for FSM
- `hr_timesheet` (Odoo Community) - Time tracking integration
- `loomworks_core` - Branding and base configuration

## Impact

- Affected specs: `loomworks-payroll`, `loomworks-fsm`, `loomworks-planning` (new capabilities)
- Affected code:
  - `/loomworks_addons/loomworks_payroll/` (new module)
  - `/loomworks_addons/loomworks_fsm/` (new module)
  - `/loomworks_addons/loomworks_planning/` (new module)
- External dependencies:
  - Frappe Gantt (MIT) or SVAR React Gantt (MIT) for planning visualization
  - PDF generation for payslips
  - Canvas API for signature capture

## Scope

This proposal covers **Phase 3 Tier 3 (Weeks 27-30)** of the implementation plan.

---

# Module 1: loomworks_payroll

## Overview

A salary computation engine with a flexible rules framework, starting with US Federal and California state tax compliance. The system supports multiple pay structures, configurable salary rules with Python-based computation, payslip generation workflows, and PDF report output.

**CRITICAL**: This module is independently developed. No code copying from Odoo Enterprise hr_payroll. Enterprise module serves only as feature reference.

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
    'contract': contract,            # Contract record
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

## Technical Design

### Data Models

#### project.task (Extension)

Extend project.task for field service capabilities:

```python
class ProjectTaskFSM(models.Model):
    _inherit = 'project.task'

    # FSM-specific fields
    is_fsm = fields.Boolean(string='Is Field Service', default=False)

    # Location
    partner_id = fields.Many2one('res.partner', string='Customer')
    partner_address = fields.Char(related='partner_id.contact_address', string='Site Address')
    partner_latitude = fields.Float(related='partner_id.partner_latitude')
    partner_longitude = fields.Float(related='partner_id.partner_longitude')

    # Scheduling
    planned_date_start = fields.Datetime(string='Planned Start')
    planned_date_end = fields.Datetime(string='Planned End')
    date_deadline = fields.Date(string='Deadline')

    # Assignment
    fsm_user_id = fields.Many2one('res.users', string='Field Technician',
        domain=[('share', '=', False)])

    # Work tracking
    fsm_done = fields.Boolean(string='Task Done', default=False)
    timer_start = fields.Datetime(string='Timer Started')
    timer_pause = fields.Datetime(string='Timer Paused')
    total_hours_spent = fields.Float(compute='_compute_total_hours', store=True)

    # Customer sign-off
    customer_signature = fields.Binary(string='Customer Signature')
    customer_signed_by = fields.Char(string='Signed By')
    customer_signed_on = fields.Datetime(string='Signed On')

    # Worksheets
    worksheet_template_id = fields.Many2one('fsm.worksheet.template')
    worksheet_data = fields.Json(string='Worksheet Data')

    # Materials/Products used
    material_line_ids = fields.One2many('fsm.material.line', 'task_id')

    # Photos/Attachments
    photo_ids = fields.One2many('ir.attachment', 'res_id',
        domain=[('res_model', '=', 'project.task'), ('mimetype', 'like', 'image%')])

    # GPS tracking (optional)
    checkin_latitude = fields.Float()
    checkin_longitude = fields.Float()
    checkin_time = fields.Datetime()
    checkout_latitude = fields.Float()
    checkout_longitude = fields.Float()
    checkout_time = fields.Datetime()
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
```

### Mobile Interface

#### Owl Components

**FSM Task Card** - Kanban card optimized for mobile:

```javascript
/** @odoo-module **/
import { Component, useState } from "@odoo/owl";

export class FSMTaskCard extends Component {
    static template = "loomworks_fsm.TaskCard";
    static props = {
        task: Object,
        onSelect: Function,
    };

    setup() {
        this.state = useState({
            timerRunning: false,
            elapsed: 0,
        });
    }

    get formattedAddress() {
        return this.props.task.partner_address || 'No address';
    }

    openMaps() {
        const { partner_latitude, partner_longitude } = this.props.task;
        if (partner_latitude && partner_longitude) {
            window.open(
                `https://maps.google.com/?q=${partner_latitude},${partner_longitude}`,
                '_blank'
            );
        }
    }
}
```

**Signature Capture Component**:

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
        canvas.addEventListener('touchstart', (e) => this.startDrawing(e));
        canvas.addEventListener('touchmove', (e) => this.draw(e));
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

### Offline Capability Considerations

Design patterns for offline-first mobile experience:

1. **Local Storage Cache**: Store assigned tasks in IndexedDB/localStorage
2. **Optimistic Updates**: Update UI immediately, sync when online
3. **Conflict Resolution**: Server timestamp wins, notify user of conflicts
4. **Queue System**: Store actions (timer start/stop, signatures, photos) in queue
5. **Background Sync**: Use Service Worker for automatic sync when connection restored

```javascript
// Offline sync manager pattern
class FSMSyncManager {
    constructor() {
        this.queue = [];
        this.isOnline = navigator.onLine;

        window.addEventListener('online', () => this.processQueue());
    }

    addToQueue(action) {
        this.queue.push({
            ...action,
            timestamp: Date.now(),
            retries: 0,
        });
        this.saveQueue();

        if (this.isOnline) {
            this.processQueue();
        }
    }

    async processQueue() {
        while (this.queue.length > 0) {
            const action = this.queue[0];
            try {
                await this.executeAction(action);
                this.queue.shift();
                this.saveQueue();
            } catch (e) {
                action.retries++;
                if (action.retries > 3) {
                    this.queue.shift(); // Give up after 3 retries
                }
                break;
            }
        }
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

## Technical Design

### Gantt Library Selection

After evaluating multiple options, recommended libraries for Odoo integration:

| Library | License | Pros | Cons |
|---------|---------|------|------|
| **Frappe Gantt** | MIT | Zero dependencies, lightweight, beautiful | Basic features |
| **SVAR React Gantt** | MIT | Modern React, comprehensive | Requires React bridge |
| **DHTMLX Gantt** | GPL/Commercial | Feature-rich | Commercial for full features |
| **Bryntum Gantt** | Commercial | Enterprise-grade | $940+/developer |

**Recommendation**: Start with **Frappe Gantt** for simplicity. Migrate to **SVAR React Gantt** if advanced features needed, leveraging existing Owl-React bridge from loomworks_dashboard.

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

### Gantt View Implementation

#### Using Frappe Gantt

Integration via Owl component wrapping Frappe Gantt:

```javascript
/** @odoo-module **/
import { Component, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import Gantt from "frappe-gantt";

export class PlanningGanttView extends Component {
    static template = "loomworks_planning.GanttView";
    static props = {
        slots: Array,
        onTaskChange: Function,
        onTaskClick: Function,
        viewMode: { type: String, optional: true },
    };

    setup() {
        this.containerRef = useRef("gantt-container");
        this.gantt = null;

        onMounted(() => this.renderGantt());
        onWillUnmount(() => this.destroyGantt());
    }

    renderGantt() {
        const tasks = this.props.slots.map(slot => ({
            id: String(slot.id),
            name: slot.employee_name || 'Unassigned',
            start: slot.start_datetime,
            end: slot.end_datetime,
            progress: slot.state === 'done' ? 100 : 0,
            custom_class: slot.has_conflict ? 'gantt-conflict' : `gantt-role-${slot.role_id}`,
        }));

        this.gantt = new Gantt(this.containerRef.el, tasks, {
            view_mode: this.props.viewMode || 'Day',
            date_format: 'YYYY-MM-DD HH:mm',
            on_click: (task) => this.props.onTaskClick(parseInt(task.id)),
            on_date_change: (task, start, end) => {
                this.props.onTaskChange(parseInt(task.id), {
                    start_datetime: start,
                    end_datetime: end,
                });
            },
        });
    }

    destroyGantt() {
        if (this.gantt) {
            // Cleanup
            this.gantt = null;
        }
    }
}
```

#### Gantt View Registration

Register as Odoo view type:

```python
class PlanningGanttView(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[
        ('planning_gantt', 'Planning Gantt'),
    ], ondelete={'planning_gantt': 'cascade'})
```

```javascript
/** @odoo-module **/
import { registry } from "@web/core/registry";
import { PlanningGanttController } from "./planning_gantt_controller";
import { PlanningGanttRenderer } from "./planning_gantt_renderer";
import { PlanningGanttModel } from "./planning_gantt_model";
import { PlanningGanttArchParser } from "./planning_gantt_arch_parser";

export const planningGanttView = {
    type: "planning_gantt",
    display_name: "Planning Gantt",
    icon: "fa fa-tasks",
    multiRecord: true,
    Controller: PlanningGanttController,
    Renderer: PlanningGanttRenderer,
    Model: PlanningGanttModel,
    ArchParser: PlanningGanttArchParser,
};

registry.category("views").add("planning_gantt", planningGanttView);
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
            'view_mode': 'planning_gantt,tree,form',
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

## Phase 1: loomworks_payroll (Week 27-28)

- [ ] 1.1 Create module structure and manifest
- [ ] 1.2 Implement hr.payroll.structure model
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
- [ ] 2.2 Extend project.task with FSM fields
- [ ] 2.3 Create fsm.worksheet.template and field models
- [ ] 2.4 Implement fsm.material.line model
- [ ] 2.5 Create signature capture Owl component
- [ ] 2.6 Create FSM mobile-optimized views (kanban, form)
- [ ] 2.7 Implement timer start/stop with timesheet integration
- [ ] 2.8 Create route optimization helper
- [ ] 2.9 Design offline sync patterns (documentation)
- [ ] 2.10 Add security groups and record rules
- [ ] 2.11 Write unit tests
- [ ] 2.12 Create mobile usage documentation

## Phase 3: loomworks_planning (Week 29-30)

- [ ] 3.1 Create module structure and manifest
- [ ] 3.2 Implement planning.slot model
- [ ] 3.3 Implement planning.role model
- [ ] 3.4 Implement planning.slot.template model
- [ ] 3.5 Implement planning.recurrence model
- [ ] 3.6 Integrate Frappe Gantt library
- [ ] 3.7 Create planning_gantt view type
- [ ] 3.8 Implement conflict detection
- [ ] 3.9 Add employee availability calculations
- [ ] 3.10 Create quick shift creation wizard
- [ ] 3.11 Add security groups and record rules
- [ ] 3.12 Write unit tests
- [ ] 3.13 Create planning documentation

---

# Success Criteria

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

## loomworks_planning

1. Gantt view displays slots with drag-drop editing
2. Conflict detection identifies overlapping assignments
3. Employee availability respects time off
4. Shift templates create slots correctly
5. Recurrence generates future slots
6. Published slots visible to assigned employees

---

# Research References

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
