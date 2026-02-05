# Change: Phase 3 Tier 2 - PLM, Sign, Appointment Modules

## Why

Loomworks ERP needs enterprise-grade features for manufacturing lifecycle management, legally-compliant document signing, and online appointment booking to compete with proprietary ERPs. These three modules address critical business needs: managing engineering changes and BOM revisions (PLM), enabling paperless contract execution (Sign), and streamlining customer scheduling (Appointment).

## What Changes

- **NEW**: `loomworks_plm` module for Product Lifecycle Management with Engineering Change Orders
- **NEW**: `loomworks_sign` module for electronic signature workflows
- **NEW**: `loomworks_appointment` module for online booking and calendar synchronization
- Integrations with existing `mrp.bom`, `calendar.event`, and `mail.template` models

## Impact

- Affected specs: None (new capabilities)
- Affected code: `loomworks_addons/` directory (3 new modules)
- Dependencies: `mrp`, `calendar`, `mail`, `portal`, `website` Odoo Community modules

---

# Module 1: loomworks_plm (Product Lifecycle Management)

## Overview

The PLM module provides Engineering Change Order (ECO) management and Bill of Materials (BOM) versioning capabilities. It enables manufacturers to formally propose, review, approve, and implement product changes while maintaining complete revision history and traceability.

### Key Capabilities

1. **Engineering Change Orders (ECOs)**: Formal change requests with multi-stage approval workflows
2. **BOM Versioning**: Track revisions with comparison tools and rollback capability
3. **Impact Analysis**: Identify affected components, documents, and production orders
4. **Change Control Board (CCB)**: Configurable approval routing with role-based access
5. **Audit Trail**: Complete history of all changes for regulatory compliance

### Industry Standards Reference

Based on industry best practices from [Arena Solutions](https://www.arenasolutions.com/resources/articles/engineering-change-order/), [Duro Labs](https://durolabs.co/blog/engineering-change-order/), and [ComplianceQuest](https://www.compliancequest.com/bloglet/bom-and-revision-control-systems/):

- ECOs should include header info (number, title, reason, priority, risk level)
- Cross-functional collaboration from engineering, manufacturing, quality, and supply chain
- Structured documentation with complete impact assessment
- Form, Fit, Function (FFF) evaluation for revision vs. new part number decisions

## Technical Design

### Data Models

#### plm.eco (Engineering Change Order)

Primary model for managing change requests.

```python
class PlmEco(models.Model):
    _name = 'plm.eco'
    _description = 'Engineering Change Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'

    name = fields.Char(
        string='ECO Number',
        required=True,
        readonly=True,
        default='New',
        copy=False,
        tracking=True
    )
    title = fields.Char(
        string='Title',
        required=True,
        tracking=True
    )
    description = fields.Html(
        string='Description',
        help='Detailed explanation of the proposed change'
    )

    # Classification
    type_id = fields.Many2one(
        'plm.eco.type',
        string='ECO Type',
        required=True,
        tracking=True
    )
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Critical')
    ], default='1', string='Priority', tracking=True)

    reason_code = fields.Selection([
        ('cost_reduction', 'Cost Reduction'),
        ('quality_improvement', 'Quality Improvement'),
        ('regulatory_compliance', 'Regulatory Compliance'),
        ('customer_request', 'Customer Request'),
        ('supplier_change', 'Supplier Change'),
        ('design_error', 'Design Error Correction'),
        ('obsolescence', 'Component Obsolescence'),
        ('performance', 'Performance Enhancement'),
        ('other', 'Other')
    ], string='Reason Code', required=True, tracking=True)

    # Workflow
    stage_id = fields.Many2one(
        'plm.eco.stage',
        string='Stage',
        group_expand='_read_group_stage_ids',
        default=lambda self: self._get_default_stage(),
        tracking=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('approved', 'Approved'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], default='draft', string='Status', tracking=True)

    # Dates
    request_date = fields.Date(
        string='Request Date',
        default=fields.Date.today,
        tracking=True
    )
    target_date = fields.Date(
        string='Target Implementation Date',
        tracking=True
    )
    effective_date = fields.Date(
        string='Effective Date',
        help='Date when the change becomes active'
    )
    completion_date = fields.Date(
        string='Completion Date',
        readonly=True
    )

    # Stakeholders
    requester_id = fields.Many2one(
        'res.users',
        string='Requester',
        default=lambda self: self.env.user,
        tracking=True
    )
    responsible_id = fields.Many2one(
        'res.users',
        string='Responsible Engineer',
        tracking=True
    )
    approver_ids = fields.Many2many(
        'res.users',
        'plm_eco_approver_rel',
        'eco_id', 'user_id',
        string='Approvers (CCB)'
    )

    # Affected Items
    bom_id = fields.Many2one(
        'mrp.bom',
        string='Affected BOM',
        tracking=True
    )
    product_id = fields.Many2one(
        'product.product',
        string='Affected Product',
        related='bom_id.product_id',
        store=True
    )
    affected_bom_line_ids = fields.Many2many(
        'mrp.bom.line',
        string='Affected BOM Lines'
    )

    # Change Details
    change_line_ids = fields.One2many(
        'plm.eco.change.line',
        'eco_id',
        string='Change Lines'
    )

    # Versioning
    current_bom_revision = fields.Char(
        string='Current Revision',
        compute='_compute_bom_revision'
    )
    new_bom_revision = fields.Char(
        string='New Revision',
        help='Revision code after ECO implementation'
    )
    new_bom_id = fields.Many2one(
        'mrp.bom',
        string='New BOM Version',
        readonly=True,
        help='BOM created after ECO approval'
    )

    # Approval Tracking
    approval_ids = fields.One2many(
        'plm.eco.approval',
        'eco_id',
        string='Approvals'
    )
    approval_state = fields.Selection([
        ('pending', 'Pending'),
        ('partial', 'Partially Approved'),
        ('approved', 'Fully Approved'),
        ('rejected', 'Rejected')
    ], compute='_compute_approval_state', store=True)

    # Impact Analysis
    impact_production = fields.Boolean(
        string='Impacts Production',
        help='Will affect ongoing manufacturing orders'
    )
    impact_inventory = fields.Boolean(
        string='Impacts Inventory',
        help='Requires inventory adjustments or dispositions'
    )
    impact_cost = fields.Float(
        string='Estimated Cost Impact',
        help='Expected change in unit cost'
    )
    impact_notes = fields.Text(
        string='Impact Analysis Notes'
    )

    # Attachments and Documents
    document_ids = fields.Many2many(
        'ir.attachment',
        string='Supporting Documents'
    )
```

#### plm.eco.type (ECO Type Configuration)

```python
class PlmEcoType(models.Model):
    _name = 'plm.eco.type'
    _description = 'ECO Type'
    _order = 'sequence, name'

    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer(default=10)
    description = fields.Text(string='Description')

    # Workflow Configuration
    stage_ids = fields.Many2many(
        'plm.eco.stage',
        string='Stages'
    )
    default_stage_id = fields.Many2one(
        'plm.eco.stage',
        string='Default Stage'
    )

    # Approval Configuration
    require_approval = fields.Boolean(
        string='Requires Approval',
        default=True
    )
    min_approvers = fields.Integer(
        string='Minimum Approvers',
        default=1
    )
    auto_approve_user_ids = fields.Many2many(
        'res.users',
        string='Auto-Approvers',
        help='Users who can single-handedly approve this ECO type'
    )
```

#### plm.eco.stage (Workflow Stages)

```python
class PlmEcoStage(models.Model):
    _name = 'plm.eco.stage'
    _description = 'ECO Stage'
    _order = 'sequence, name'

    name = fields.Char(string='Stage Name', required=True)
    sequence = fields.Integer(default=10)
    fold = fields.Boolean(
        string='Folded in Kanban',
        help='Fold this stage in kanban view'
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('approved', 'Approved'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='Related State', required=True)

    # Stage Behavior
    is_blocking = fields.Boolean(
        string='Blocking Stage',
        help='ECO cannot proceed without approval at this stage'
    )
    require_approval = fields.Boolean(
        string='Requires Approval'
    )
    mail_template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        help='Email sent when ECO enters this stage'
    )
```

#### plm.eco.change.line (Detailed Change Items)

```python
class PlmEcoChangeLine(models.Model):
    _name = 'plm.eco.change.line'
    _description = 'ECO Change Line'

    eco_id = fields.Many2one(
        'plm.eco',
        string='ECO',
        required=True,
        ondelete='cascade'
    )

    change_type = fields.Selection([
        ('add', 'Add Component'),
        ('remove', 'Remove Component'),
        ('replace', 'Replace Component'),
        ('modify_qty', 'Modify Quantity'),
        ('modify_operation', 'Modify Operation'),
        ('other', 'Other Change')
    ], string='Change Type', required=True)

    # Component References
    old_component_id = fields.Many2one(
        'product.product',
        string='Current Component'
    )
    new_component_id = fields.Many2one(
        'product.product',
        string='New Component'
    )

    # Quantity Changes
    old_quantity = fields.Float(
        string='Current Quantity',
        digits='Product Unit of Measure'
    )
    new_quantity = fields.Float(
        string='New Quantity',
        digits='Product Unit of Measure'
    )

    # Operation Changes (if applicable)
    old_operation_id = fields.Many2one(
        'mrp.routing.workcenter',
        string='Current Operation'
    )
    new_operation_id = fields.Many2one(
        'mrp.routing.workcenter',
        string='New Operation'
    )

    notes = fields.Text(string='Notes')

    # Impact
    cost_impact = fields.Float(
        string='Cost Impact',
        compute='_compute_cost_impact',
        store=True
    )
```

#### plm.eco.approval (Approval Tracking)

```python
class PlmEcoApproval(models.Model):
    _name = 'plm.eco.approval'
    _description = 'ECO Approval'
    _order = 'create_date desc'

    eco_id = fields.Many2one(
        'plm.eco',
        string='ECO',
        required=True,
        ondelete='cascade'
    )
    user_id = fields.Many2one(
        'res.users',
        string='Approver',
        required=True
    )
    status = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ], default='pending', string='Status')

    approval_date = fields.Datetime(string='Approval Date')
    comments = fields.Text(string='Comments')

    # Digital Signature (optional integration with loomworks_sign)
    signature = fields.Binary(string='Signature')
```

#### plm.bom.revision (BOM Revision History)

```python
class PlmBomRevision(models.Model):
    _name = 'plm.bom.revision'
    _description = 'BOM Revision History'
    _order = 'revision_date desc'

    bom_id = fields.Many2one(
        'mrp.bom',
        string='BOM',
        required=True,
        ondelete='cascade'
    )
    revision_code = fields.Char(
        string='Revision Code',
        required=True,
        help='e.g., A, B, C or 1.0, 1.1, 2.0'
    )
    revision_date = fields.Datetime(
        string='Revision Date',
        default=fields.Datetime.now
    )

    # Change Reference
    eco_id = fields.Many2one(
        'plm.eco',
        string='Source ECO'
    )

    # Snapshot of BOM at this revision
    snapshot_data = fields.Text(
        string='BOM Snapshot (JSON)',
        help='Serialized BOM structure at this revision'
    )

    # Metadata
    created_by_id = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user
    )
    notes = fields.Text(string='Revision Notes')

    # Status
    is_active = fields.Boolean(
        string='Active Revision',
        default=True
    )
    is_released = fields.Boolean(
        string='Released',
        help='Revision has been released to production'
    )
```

### MRP.BOM Extension

Extend the standard `mrp.bom` model for versioning support:

```python
class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    # Revision Tracking
    revision_code = fields.Char(
        string='Revision',
        default='A',
        tracking=True
    )
    revision_ids = fields.One2many(
        'plm.bom.revision',
        'bom_id',
        string='Revision History'
    )
    revision_count = fields.Integer(
        compute='_compute_revision_count'
    )

    # ECO References
    eco_ids = fields.One2many(
        'plm.eco',
        'bom_id',
        string='Engineering Change Orders'
    )
    pending_eco_count = fields.Integer(
        compute='_compute_pending_eco_count'
    )

    # Lifecycle Status
    lifecycle_state = fields.Selection([
        ('draft', 'Draft'),
        ('review', 'Under Review'),
        ('released', 'Released'),
        ('obsolete', 'Obsolete')
    ], default='draft', string='Lifecycle State', tracking=True)

    # Parent/Previous Version
    previous_bom_id = fields.Many2one(
        'mrp.bom',
        string='Previous Version'
    )

    def action_create_revision(self):
        """Create a new revision of this BOM."""
        # Implementation creates snapshot and increments revision
        pass

    def action_compare_revisions(self, other_bom_id):
        """Compare two BOM revisions and return differences."""
        pass
```

### Key Business Logic

#### ECO Workflow Methods

```python
class PlmEco(models.Model):
    # ... fields defined above ...

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('plm.eco') or 'New'
        return super().create(vals)

    def action_confirm(self):
        """Move ECO from draft to confirmed, request approvals."""
        self.ensure_one()
        if not self.change_line_ids:
            raise UserError(_('Please add at least one change line before confirming.'))

        self.write({
            'state': 'confirmed',
            'stage_id': self._get_stage_by_state('confirmed').id
        })
        self._request_approvals()

    def action_start_review(self):
        """Begin the review/approval process."""
        self.write({
            'state': 'in_progress',
            'stage_id': self._get_stage_by_state('in_progress').id
        })

    def action_approve(self):
        """Record current user's approval."""
        self.ensure_one()
        approval = self.approval_ids.filtered(
            lambda a: a.user_id == self.env.user and a.status == 'pending'
        )
        if approval:
            approval.write({
                'status': 'approved',
                'approval_date': fields.Datetime.now()
            })
        self._check_full_approval()

    def action_reject(self, reason=None):
        """Reject the ECO."""
        self.ensure_one()
        approval = self.approval_ids.filtered(
            lambda a: a.user_id == self.env.user and a.status == 'pending'
        )
        if approval:
            approval.write({
                'status': 'rejected',
                'approval_date': fields.Datetime.now(),
                'comments': reason
            })
        self.write({
            'state': 'cancelled',
            'stage_id': self._get_stage_by_state('cancelled').id
        })

    def action_implement(self):
        """Implement the approved ECO - create new BOM revision."""
        self.ensure_one()
        if self.approval_state != 'approved':
            raise UserError(_('ECO must be fully approved before implementation.'))

        new_bom = self._create_new_bom_version()
        self.write({
            'state': 'done',
            'stage_id': self._get_stage_by_state('done').id,
            'new_bom_id': new_bom.id,
            'completion_date': fields.Date.today(),
            'effective_date': fields.Date.today()
        })
        return new_bom

    def _create_new_bom_version(self):
        """Create new BOM version based on ECO changes."""
        self.ensure_one()
        old_bom = self.bom_id

        # Create snapshot of old BOM
        self.env['plm.bom.revision'].create({
            'bom_id': old_bom.id,
            'revision_code': old_bom.revision_code,
            'eco_id': self.id,
            'snapshot_data': self._serialize_bom(old_bom),
            'notes': f'Revision before ECO {self.name}'
        })

        # Copy BOM and apply changes
        new_bom = old_bom.copy({
            'revision_code': self.new_bom_revision or self._get_next_revision(old_bom.revision_code),
            'previous_bom_id': old_bom.id,
            'lifecycle_state': 'released'
        })

        # Apply change lines
        for change in self.change_line_ids:
            self._apply_change_to_bom(new_bom, change)

        # Mark old BOM as obsolete
        old_bom.write({'lifecycle_state': 'obsolete'})

        return new_bom

    def _apply_change_to_bom(self, bom, change_line):
        """Apply a single change line to the BOM."""
        BomLine = self.env['mrp.bom.line']

        if change_line.change_type == 'add':
            BomLine.create({
                'bom_id': bom.id,
                'product_id': change_line.new_component_id.id,
                'product_qty': change_line.new_quantity,
            })
        elif change_line.change_type == 'remove':
            line = bom.bom_line_ids.filtered(
                lambda l: l.product_id == change_line.old_component_id
            )
            line.unlink()
        elif change_line.change_type == 'replace':
            line = bom.bom_line_ids.filtered(
                lambda l: l.product_id == change_line.old_component_id
            )
            line.write({
                'product_id': change_line.new_component_id.id,
                'product_qty': change_line.new_quantity or line.product_qty
            })
        elif change_line.change_type == 'modify_qty':
            line = bom.bom_line_ids.filtered(
                lambda l: l.product_id == change_line.old_component_id
            )
            line.write({'product_qty': change_line.new_quantity})

    def _request_approvals(self):
        """Create approval records for all CCB members."""
        for user in self.approver_ids:
            self.env['plm.eco.approval'].create({
                'eco_id': self.id,
                'user_id': user.id,
                'status': 'pending'
            })
        # Send notification emails
        template = self.env.ref('loomworks_plm.mail_template_eco_approval_request', raise_if_not_found=False)
        if template:
            for approval in self.approval_ids:
                template.send_mail(approval.id)

    @api.depends('approval_ids.status')
    def _compute_approval_state(self):
        for eco in self:
            approvals = eco.approval_ids
            if not approvals:
                eco.approval_state = 'pending'
            elif any(a.status == 'rejected' for a in approvals):
                eco.approval_state = 'rejected'
            elif all(a.status == 'approved' for a in approvals):
                eco.approval_state = 'approved'
            elif any(a.status == 'approved' for a in approvals):
                eco.approval_state = 'partial'
            else:
                eco.approval_state = 'pending'
```

### Views

#### ECO Kanban View

```xml
<record id="plm_eco_view_kanban" model="ir.ui.view">
    <field name="name">plm.eco.kanban</field>
    <field name="model">plm.eco</field>
    <field name="arch" type="xml">
        <kanban default_group_by="stage_id" class="o_kanban_small_column">
            <field name="name"/>
            <field name="title"/>
            <field name="priority"/>
            <field name="approval_state"/>
            <field name="responsible_id"/>
            <field name="color"/>
            <templates>
                <t t-name="kanban-box">
                    <div t-attf-class="oe_kanban_card oe_kanban_global_click">
                        <div class="oe_kanban_content">
                            <div class="o_kanban_record_top">
                                <strong class="o_kanban_record_title">
                                    <field name="name"/>
                                </strong>
                                <field name="priority" widget="priority"/>
                            </div>
                            <div class="o_kanban_record_body">
                                <field name="title"/>
                            </div>
                            <div class="o_kanban_record_bottom">
                                <div class="oe_kanban_bottom_left">
                                    <field name="approval_state" widget="badge"
                                           decoration-success="approval_state == 'approved'"
                                           decoration-warning="approval_state == 'partial'"
                                           decoration-danger="approval_state == 'rejected'"/>
                                </div>
                                <div class="oe_kanban_bottom_right">
                                    <field name="responsible_id" widget="many2one_avatar_user"/>
                                </div>
                            </div>
                        </div>
                    </div>
                </t>
            </templates>
        </kanban>
    </field>
</record>
```

#### ECO Form View

```xml
<record id="plm_eco_view_form" model="ir.ui.view">
    <field name="name">plm.eco.form</field>
    <field name="model">plm.eco</field>
    <field name="arch" type="xml">
        <form string="Engineering Change Order">
            <header>
                <button name="action_confirm" string="Confirm" type="object"
                        class="btn-primary" invisible="state != 'draft'"/>
                <button name="action_start_review" string="Start Review" type="object"
                        invisible="state != 'confirmed'"/>
                <button name="action_approve" string="Approve" type="object"
                        class="btn-success" invisible="state != 'in_progress'"/>
                <button name="action_reject" string="Reject" type="object"
                        class="btn-danger" invisible="state != 'in_progress'"/>
                <button name="action_implement" string="Implement" type="object"
                        class="btn-primary" invisible="approval_state != 'approved' or state == 'done'"/>
                <field name="state" widget="statusbar" statusbar_visible="draft,confirmed,in_progress,approved,done"/>
            </header>
            <sheet>
                <div class="oe_button_box" name="button_box">
                    <button class="oe_stat_button" type="object" name="action_view_approvals"
                            icon="fa-check-circle">
                        <field name="approval_state" widget="badge"/>
                    </button>
                </div>
                <div class="oe_title">
                    <h1>
                        <field name="name" readonly="1"/>
                    </h1>
                </div>
                <group>
                    <group>
                        <field name="title"/>
                        <field name="type_id"/>
                        <field name="reason_code"/>
                        <field name="priority"/>
                    </group>
                    <group>
                        <field name="requester_id"/>
                        <field name="responsible_id"/>
                        <field name="request_date"/>
                        <field name="target_date"/>
                    </group>
                </group>
                <notebook>
                    <page string="Change Details" name="changes">
                        <group>
                            <group>
                                <field name="bom_id"/>
                                <field name="product_id"/>
                                <field name="current_bom_revision"/>
                                <field name="new_bom_revision"/>
                            </group>
                        </group>
                        <field name="change_line_ids">
                            <tree editable="bottom">
                                <field name="change_type"/>
                                <field name="old_component_id"/>
                                <field name="new_component_id"/>
                                <field name="old_quantity"/>
                                <field name="new_quantity"/>
                                <field name="cost_impact"/>
                                <field name="notes"/>
                            </tree>
                        </field>
                    </page>
                    <page string="Impact Analysis" name="impact">
                        <group>
                            <field name="impact_production"/>
                            <field name="impact_inventory"/>
                            <field name="impact_cost"/>
                        </group>
                        <field name="impact_notes" placeholder="Describe the impact of this change..."/>
                    </page>
                    <page string="Approvals" name="approvals">
                        <field name="approver_ids" widget="many2many_tags"/>
                        <field name="approval_ids">
                            <tree>
                                <field name="user_id"/>
                                <field name="status" widget="badge"/>
                                <field name="approval_date"/>
                                <field name="comments"/>
                            </tree>
                        </field>
                    </page>
                    <page string="Description" name="description">
                        <field name="description"/>
                    </page>
                    <page string="Documents" name="documents">
                        <field name="document_ids" widget="many2many_binary"/>
                    </page>
                </notebook>
            </sheet>
            <div class="oe_chatter">
                <field name="message_follower_ids"/>
                <field name="activity_ids"/>
                <field name="message_ids"/>
            </div>
        </form>
    </field>
</record>
```

### Security

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_plm_eco_user,plm.eco.user,model_plm_eco,mrp.group_mrp_user,1,1,1,0
access_plm_eco_manager,plm.eco.manager,model_plm_eco,mrp.group_mrp_manager,1,1,1,1
access_plm_eco_type_user,plm.eco.type.user,model_plm_eco_type,mrp.group_mrp_user,1,0,0,0
access_plm_eco_type_manager,plm.eco.type.manager,model_plm_eco_type,mrp.group_mrp_manager,1,1,1,1
access_plm_eco_stage_user,plm.eco.stage.user,model_plm_eco_stage,mrp.group_mrp_user,1,0,0,0
access_plm_eco_stage_manager,plm.eco.stage.manager,model_plm_eco_stage,mrp.group_mrp_manager,1,1,1,1
access_plm_eco_change_line,plm.eco.change.line,model_plm_eco_change_line,mrp.group_mrp_user,1,1,1,1
access_plm_eco_approval,plm.eco.approval,model_plm_eco_approval,mrp.group_mrp_user,1,1,1,0
access_plm_bom_revision,plm.bom.revision,model_plm_bom_revision,mrp.group_mrp_user,1,0,0,0
```

### Demo Data

```xml
<record id="plm_eco_type_design" model="plm.eco.type">
    <field name="name">Design Change</field>
    <field name="description">Changes to product design or engineering specifications</field>
    <field name="require_approval">True</field>
    <field name="min_approvers">2</field>
</record>

<record id="plm_eco_type_supplier" model="plm.eco.type">
    <field name="name">Supplier Change</field>
    <field name="description">Component source or supplier modifications</field>
    <field name="require_approval">True</field>
    <field name="min_approvers">1</field>
</record>

<record id="plm_eco_stage_draft" model="plm.eco.stage">
    <field name="name">Draft</field>
    <field name="sequence">10</field>
    <field name="state">draft</field>
</record>

<record id="plm_eco_stage_review" model="plm.eco.stage">
    <field name="name">Under Review</field>
    <field name="sequence">20</field>
    <field name="state">in_progress</field>
    <field name="require_approval">True</field>
</record>

<record id="plm_eco_stage_approved" model="plm.eco.stage">
    <field name="name">Approved</field>
    <field name="sequence">30</field>
    <field name="state">approved</field>
</record>

<record id="plm_eco_stage_done" model="plm.eco.stage">
    <field name="name">Done</field>
    <field name="sequence">40</field>
    <field name="state">done</field>
    <field name="fold">True</field>
</record>
```

---

# Module 2: loomworks_sign (Electronic Signatures)

## Overview

The Sign module provides electronic signature capabilities for documents, enabling paperless workflows for contracts, approvals, and legal documents. It supports multiple signature types (drawn, typed, uploaded) with a complete audit trail for legal compliance.

### Legal Compliance Standards

Based on research from [Portant](https://www.portant.co/post/esign-complete-guide-to-electronic-signatures-in-2026), [eSignly](https://www.esignly.com/electronic-signature/here-s-how-electronic-signature-legally-binding.html), and [Yousign](https://yousign.com/blog/international-compliance-electronic-signatures):

**US Compliance (ESIGN Act & UETA)**:
- Electronic signatures have same legal status as handwritten signatures
- Requires: Intent to Sign, Consent to Conduct Business Electronically, Association with Record

**EU Compliance (eIDAS)**:
- Three tiers: Simple (SES), Advanced (AES), Qualified (QES)
- Advanced signatures must be uniquely linked to signer and under their sole control
- Qualified signatures require Trust Service Provider certificate

**Critical Requirements**:
- Robust, tamper-proof audit trail
- Capture of signer intent, exact document signed, timestamp
- Secure storage of signature data

### PDF Library Selection

Based on research from [PyMuPDF](https://github.com/pymupdf/PyMuPDF) and [pyHanko](https://github.com/MatthiasValvekens/pyHanko):

**Recommended Stack**:
1. **PyMuPDF**: For PDF manipulation, field placement, and rendering
2. **pyHanko**: For cryptographic digital signatures (PAdES compliant)
3. **ReportLab**: For generating signature placeholder PDFs if needed

## Technical Design

### Data Models

#### sign.request (Signature Request)

Main model for signature request workflows.

```python
class SignRequest(models.Model):
    _name = 'sign.request'
    _description = 'Signature Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference',
        required=True,
        readonly=True,
        default='New',
        copy=False
    )

    # Document
    template_id = fields.Many2one(
        'sign.template',
        string='Template',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    attachment_id = fields.Many2one(
        'ir.attachment',
        string='Source Document',
        readonly=True
    )
    signed_attachment_id = fields.Many2one(
        'ir.attachment',
        string='Signed Document',
        readonly=True
    )

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('signing', 'In Progress'),
        ('done', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired')
    ], default='draft', string='Status', tracking=True)

    # Signers
    signer_ids = fields.One2many(
        'sign.request.signer',
        'request_id',
        string='Signers'
    )
    signer_count = fields.Integer(
        compute='_compute_signer_count'
    )
    completed_count = fields.Integer(
        compute='_compute_completed_count'
    )

    # Request Details
    subject = fields.Char(
        string='Email Subject',
        default='Signature Request'
    )
    message = fields.Html(
        string='Message',
        help='Message to include in signature request email'
    )

    # Dates
    create_uid = fields.Many2one(
        'res.users',
        string='Created By',
        readonly=True
    )
    sent_date = fields.Datetime(
        string='Sent Date',
        readonly=True
    )
    expire_date = fields.Date(
        string='Expiration Date',
        help='Request expires after this date'
    )
    completion_date = fields.Datetime(
        string='Completion Date',
        readonly=True
    )

    # Security
    access_token = fields.Char(
        string='Access Token',
        copy=False,
        default=lambda self: self._generate_access_token()
    )

    # Audit
    audit_log_ids = fields.One2many(
        'sign.audit.log',
        'request_id',
        string='Audit Log'
    )

    # Related Document (optional link to source record)
    res_model = fields.Char(string='Related Model')
    res_id = fields.Integer(string='Related Record ID')
```

#### sign.request.signer (Individual Signer)

```python
class SignRequestSigner(models.Model):
    _name = 'sign.request.signer'
    _description = 'Signature Request Signer'
    _order = 'sequence, id'

    request_id = fields.Many2one(
        'sign.request',
        string='Request',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(default=10)

    # Signer Identity
    partner_id = fields.Many2one(
        'res.partner',
        string='Signer',
        required=True
    )
    email = fields.Char(
        string='Email',
        related='partner_id.email',
        store=True
    )

    # Role
    role_id = fields.Many2one(
        'sign.role',
        string='Role',
        required=True
    )

    # Status
    state = fields.Selection([
        ('waiting', 'Waiting'),
        ('sent', 'Email Sent'),
        ('viewed', 'Document Viewed'),
        ('signing', 'Signing'),
        ('done', 'Signed'),
        ('refused', 'Refused')
    ], default='waiting', string='Status')

    # Signing Data
    signed_date = fields.Datetime(string='Signed Date')
    signature_data = fields.Binary(string='Signature Image')
    signature_type = fields.Selection([
        ('draw', 'Drawn'),
        ('type', 'Typed'),
        ('upload', 'Uploaded')
    ], string='Signature Type')

    # Security & Access
    access_token = fields.Char(
        string='Access Token',
        copy=False,
        default=lambda self: self._generate_access_token()
    )

    # Metadata for audit
    signing_ip = fields.Char(string='IP Address')
    signing_user_agent = fields.Char(string='User Agent')

    # Item values (completed fields)
    item_value_ids = fields.One2many(
        'sign.request.item.value',
        'signer_id',
        string='Field Values'
    )
```

#### sign.template (Reusable Document Template)

```python
class SignTemplate(models.Model):
    _name = 'sign.template'
    _description = 'Signature Template'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    active = fields.Boolean(default=True)

    # Source Document
    attachment_id = fields.Many2one(
        'ir.attachment',
        string='PDF Document',
        required=True
    )

    # Template Items (placeholders)
    item_ids = fields.One2many(
        'sign.template.item',
        'template_id',
        string='Signature Fields'
    )

    # Default Settings
    default_role_ids = fields.Many2many(
        'sign.role',
        string='Roles'
    )

    # Usage Statistics
    request_count = fields.Integer(
        compute='_compute_request_count'
    )

    # Tags
    tag_ids = fields.Many2many(
        'sign.template.tag',
        string='Tags'
    )

    # Preview
    preview_image = fields.Binary(
        string='Preview',
        compute='_compute_preview'
    )
```

#### sign.template.item (Field Placeholder)

```python
class SignTemplateItem(models.Model):
    _name = 'sign.template.item'
    _description = 'Template Signature Field'
    _order = 'page, sequence'

    template_id = fields.Many2one(
        'sign.template',
        string='Template',
        required=True,
        ondelete='cascade'
    )

    # Field Type
    type_id = fields.Many2one(
        'sign.item.type',
        string='Field Type',
        required=True
    )

    # Position (percentage-based for responsiveness)
    page = fields.Integer(string='Page Number', default=1)
    pos_x = fields.Float(
        string='X Position (%)',
        help='Horizontal position as percentage of page width'
    )
    pos_y = fields.Float(
        string='Y Position (%)',
        help='Vertical position as percentage of page height'
    )
    width = fields.Float(string='Width (%)', default=20)
    height = fields.Float(string='Height (%)', default=5)

    # Assignment
    role_id = fields.Many2one(
        'sign.role',
        string='Assigned Role',
        required=True
    )

    # Configuration
    sequence = fields.Integer(default=10)
    required = fields.Boolean(string='Required', default=True)
    placeholder = fields.Char(string='Placeholder Text')

    # Validation
    option_ids = fields.One2many(
        'sign.template.item.option',
        'item_id',
        string='Options',
        help='For selection/radio fields'
    )
```

#### sign.item.type (Field Type Configuration)

```python
class SignItemType(models.Model):
    _name = 'sign.item.type'
    _description = 'Signature Field Type'
    _order = 'sequence'

    name = fields.Char(string='Name', required=True, translate=True)
    technical_name = fields.Char(string='Technical Name', required=True)
    sequence = fields.Integer(default=10)

    item_type = fields.Selection([
        ('signature', 'Signature'),
        ('initial', 'Initials'),
        ('text', 'Text Input'),
        ('textarea', 'Text Area'),
        ('checkbox', 'Checkbox'),
        ('selection', 'Selection'),
        ('date', 'Date'),
        ('name', 'Full Name'),
        ('email', 'Email'),
        ('company', 'Company'),
    ], string='Type', required=True)

    # Display
    icon = fields.Char(string='Icon Class', default='fa-pencil')
    color = fields.Integer(string='Color Index')

    # Behavior
    auto_fill = fields.Boolean(
        string='Auto-fill from Signer',
        help='Automatically fill from signer partner data'
    )
    auto_fill_field = fields.Char(
        string='Auto-fill Field',
        help='Partner field to use for auto-fill'
    )
```

#### sign.role (Signer Roles)

```python
class SignRole(models.Model):
    _name = 'sign.role'
    _description = 'Signer Role'
    _order = 'sequence'

    name = fields.Char(string='Role Name', required=True, translate=True)
    sequence = fields.Integer(default=10)
    color = fields.Integer(string='Color')

    # Behavior
    can_reassign = fields.Boolean(
        string='Can Reassign',
        help='Signer can reassign to someone else'
    )
    auth_method = fields.Selection([
        ('email', 'Email Link'),
        ('sms', 'SMS Code'),
        ('email_sms', 'Email + SMS'),
    ], default='email', string='Authentication Method')
```

#### sign.audit.log (Audit Trail)

```python
class SignAuditLog(models.Model):
    _name = 'sign.audit.log'
    _description = 'Signature Audit Log'
    _order = 'timestamp desc'
    _rec_name = 'action'

    request_id = fields.Many2one(
        'sign.request',
        string='Request',
        required=True,
        ondelete='cascade'
    )
    signer_id = fields.Many2one(
        'sign.request.signer',
        string='Signer'
    )

    # Event Details
    timestamp = fields.Datetime(
        string='Timestamp',
        default=fields.Datetime.now,
        required=True
    )
    action = fields.Selection([
        ('create', 'Request Created'),
        ('send', 'Request Sent'),
        ('view', 'Document Viewed'),
        ('sign', 'Signature Applied'),
        ('complete', 'Document Completed'),
        ('refuse', 'Signature Refused'),
        ('cancel', 'Request Cancelled'),
        ('expire', 'Request Expired'),
        ('download', 'Document Downloaded'),
    ], string='Action', required=True)

    description = fields.Char(string='Description')

    # Context
    ip_address = fields.Char(string='IP Address')
    user_agent = fields.Char(string='User Agent')
    geo_location = fields.Char(string='Location')

    # Hash for integrity verification
    hash_value = fields.Char(
        string='Hash',
        help='SHA-256 hash for log integrity'
    )
    previous_hash = fields.Char(
        string='Previous Hash',
        help='Hash of previous log entry (blockchain-style)'
    )
```

#### sign.request.item.value (Completed Field Values)

```python
class SignRequestItemValue(models.Model):
    _name = 'sign.request.item.value'
    _description = 'Signature Field Value'

    signer_id = fields.Many2one(
        'sign.request.signer',
        string='Signer',
        required=True,
        ondelete='cascade'
    )
    template_item_id = fields.Many2one(
        'sign.template.item',
        string='Template Field',
        required=True
    )

    # Value Storage
    value = fields.Text(string='Value')
    signature_image = fields.Binary(string='Signature Image')

    # Metadata
    completed_date = fields.Datetime(
        string='Completed',
        default=fields.Datetime.now
    )
```

### PDF Processing Service

```python
# services/pdf_service.py

import base64
import hashlib
from io import BytesIO

class PDFSignatureService:
    """Service for PDF manipulation and signature embedding."""

    def __init__(self, env):
        self.env = env

    def prepare_document(self, template):
        """Prepare PDF with signature field placeholders."""
        import fitz  # PyMuPDF

        pdf_content = base64.b64decode(template.attachment_id.datas)
        doc = fitz.open(stream=pdf_content, filetype='pdf')

        # Add visual placeholders for each field
        for item in template.item_ids:
            page = doc[item.page - 1]
            rect = self._get_rect_from_position(page, item)

            # Draw placeholder rectangle
            page.draw_rect(rect, color=(0.8, 0.8, 0.8), fill=(0.95, 0.95, 0.95))

            # Add placeholder text
            if item.placeholder:
                page.insert_text(
                    rect.tl + fitz.Point(5, 15),
                    item.placeholder,
                    fontsize=10,
                    color=(0.5, 0.5, 0.5)
                )

        output = BytesIO()
        doc.save(output)
        doc.close()

        return base64.b64encode(output.getvalue())

    def embed_signature(self, request, signer, signature_data, item):
        """Embed signature image into PDF at specified position."""
        import fitz

        pdf_content = base64.b64decode(request.attachment_id.datas)
        doc = fitz.open(stream=pdf_content, filetype='pdf')

        page = doc[item.page - 1]
        rect = self._get_rect_from_position(page, item)

        # Embed signature image
        if item.type_id.item_type in ('signature', 'initial'):
            sig_image = base64.b64decode(signature_data)
            page.insert_image(rect, stream=sig_image)
        else:
            # Text value
            page.insert_text(
                rect.tl + fitz.Point(5, 15),
                signature_data,
                fontsize=12
            )

        output = BytesIO()
        doc.save(output)
        doc.close()

        return base64.b64encode(output.getvalue())

    def finalize_document(self, request):
        """Finalize signed document with digital signature and certificate."""
        # Use pyHanko for PAdES-compliant digital signatures
        # This provides cryptographic proof of document integrity
        from pyhanko.sign import signers
        from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter

        pdf_content = base64.b64decode(request.attachment_id.datas)

        # Create document hash for audit
        doc_hash = hashlib.sha256(pdf_content).hexdigest()

        # Add completion metadata
        # (Full implementation would add PAdES signature)

        return pdf_content, doc_hash

    def _get_rect_from_position(self, page, item):
        """Convert percentage-based position to PDF rectangle."""
        import fitz

        page_rect = page.rect
        x = page_rect.width * (item.pos_x / 100)
        y = page_rect.height * (item.pos_y / 100)
        w = page_rect.width * (item.width / 100)
        h = page_rect.height * (item.height / 100)

        return fitz.Rect(x, y, x + w, y + h)
```

### Key Business Logic

```python
class SignRequest(models.Model):
    # ... fields defined above ...

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('sign.request') or 'New'

        record = super().create(vals)

        # Prepare document from template
        if record.template_id:
            pdf_service = self.env['sign.pdf.service']
            prepared_pdf = pdf_service.prepare_document(record.template_id)
            record.attachment_id = self.env['ir.attachment'].create({
                'name': f'{record.name}.pdf',
                'datas': prepared_pdf,
                'mimetype': 'application/pdf',
            })

        # Log creation
        record._log_audit('create', 'Signature request created')

        return record

    def action_send(self):
        """Send signature request to all signers."""
        self.ensure_one()

        for signer in self.signer_ids:
            self._send_signature_email(signer)
            signer.state = 'sent'

        self.write({
            'state': 'sent',
            'sent_date': fields.Datetime.now()
        })
        self._log_audit('send', 'Signature request sent to signers')

    def _send_signature_email(self, signer):
        """Send email with signing link to signer."""
        template = self.env.ref('loomworks_sign.mail_template_signature_request')

        signing_url = self._get_signing_url(signer)

        template.with_context(
            signing_url=signing_url,
            signer_name=signer.partner_id.name
        ).send_mail(self.id, email_values={
            'email_to': signer.email
        })

    def _get_signing_url(self, signer):
        """Generate unique signing URL for signer."""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f'{base_url}/sign/{self.access_token}/{signer.access_token}'

    def action_sign(self, signer, item_values):
        """Process signature submission from signer."""
        self.ensure_one()

        # Validate signer
        if signer.state == 'done':
            raise UserError(_('You have already signed this document.'))

        # Store item values
        for item, value in item_values.items():
            self.env['sign.request.item.value'].create({
                'signer_id': signer.id,
                'template_item_id': item.id,
                'value': value.get('text'),
                'signature_image': value.get('signature'),
            })

            # Embed into PDF
            pdf_service = self.env['sign.pdf.service']
            self.attachment_id.datas = pdf_service.embed_signature(
                self, signer, value.get('signature') or value.get('text'), item
            )

        # Update signer status
        signer.write({
            'state': 'done',
            'signed_date': fields.Datetime.now(),
        })

        # Log signature
        self._log_audit('sign', f'{signer.partner_id.name} signed the document', signer_id=signer.id)

        # Check if all signed
        if all(s.state == 'done' for s in self.signer_ids):
            self.action_complete()

    def action_complete(self):
        """Finalize the signed document."""
        self.ensure_one()

        pdf_service = self.env['sign.pdf.service']
        final_pdf, doc_hash = pdf_service.finalize_document(self)

        self.signed_attachment_id = self.env['ir.attachment'].create({
            'name': f'{self.name}_signed.pdf',
            'datas': base64.b64encode(final_pdf),
            'mimetype': 'application/pdf',
        })

        self.write({
            'state': 'done',
            'completion_date': fields.Datetime.now()
        })

        self._log_audit('complete', f'Document completed. Hash: {doc_hash}')

        # Send completion notification
        self._send_completion_notification()

    def _log_audit(self, action, description, signer_id=None, ip=None, user_agent=None):
        """Create audit log entry with integrity hash."""
        # Get previous hash for chain integrity
        last_log = self.audit_log_ids.sorted('timestamp', reverse=True)[:1]
        previous_hash = last_log.hash_value if last_log else '0' * 64

        # Create log content for hashing
        log_content = f'{self.id}|{action}|{description}|{fields.Datetime.now()}|{previous_hash}'
        hash_value = hashlib.sha256(log_content.encode()).hexdigest()

        self.env['sign.audit.log'].create({
            'request_id': self.id,
            'signer_id': signer_id,
            'action': action,
            'description': description,
            'ip_address': ip,
            'user_agent': user_agent,
            'hash_value': hash_value,
            'previous_hash': previous_hash,
        })

    @api.model
    def _cron_check_expiration(self):
        """Check and expire overdue requests."""
        expired = self.search([
            ('state', 'in', ['sent', 'signing']),
            ('expire_date', '<', fields.Date.today())
        ])
        for request in expired:
            request.write({'state': 'expired'})
            request._log_audit('expire', 'Request expired')
```

### Portal Controller

```python
# controllers/portal.py

from odoo import http
from odoo.http import request

class SignPortal(http.Controller):

    @http.route('/sign/<string:request_token>/<string:signer_token>',
                type='http', auth='public', website=True)
    def sign_document(self, request_token, signer_token, **kwargs):
        """Public signing page."""
        sign_request = request.env['sign.request'].sudo().search([
            ('access_token', '=', request_token)
        ], limit=1)

        if not sign_request or sign_request.state in ('done', 'cancelled', 'expired'):
            return request.render('loomworks_sign.sign_invalid')

        signer = sign_request.signer_ids.filtered(
            lambda s: s.access_token == signer_token
        )

        if not signer:
            return request.render('loomworks_sign.sign_invalid')

        # Log document view
        if signer.state == 'sent':
            signer.state = 'viewed'
            sign_request._log_audit(
                'view',
                f'{signer.partner_id.name} viewed the document',
                signer_id=signer.id,
                ip=request.httprequest.remote_addr,
                user_agent=request.httprequest.user_agent.string
            )

        return request.render('loomworks_sign.sign_document', {
            'sign_request': sign_request,
            'signer': signer,
            'items': sign_request.template_id.item_ids.filtered(
                lambda i: i.role_id == signer.role_id
            ),
        })

    @http.route('/sign/submit', type='json', auth='public')
    def submit_signature(self, request_token, signer_token, item_values):
        """Submit signature via AJAX."""
        sign_request = request.env['sign.request'].sudo().search([
            ('access_token', '=', request_token)
        ], limit=1)

        signer = sign_request.signer_ids.filtered(
            lambda s: s.access_token == signer_token
        )

        if not sign_request or not signer:
            return {'error': 'Invalid request'}

        # Store IP and user agent
        signer.write({
            'signing_ip': request.httprequest.remote_addr,
            'signing_user_agent': request.httprequest.user_agent.string,
        })

        # Process signature
        sign_request.action_sign(signer, item_values)

        return {'success': True, 'message': 'Thank you for signing!'}
```

### Views

#### Template Form View

```xml
<record id="sign_template_view_form" model="ir.ui.view">
    <field name="name">sign.template.form</field>
    <field name="model">sign.template</field>
    <field name="arch" type="xml">
        <form string="Signature Template">
            <sheet>
                <div class="oe_button_box" name="button_box">
                    <button class="oe_stat_button" type="object"
                            name="action_view_requests" icon="fa-pencil-square-o">
                        <field name="request_count" string="Requests" widget="statinfo"/>
                    </button>
                </div>
                <field name="preview_image" widget="image" class="oe_avatar"/>
                <div class="oe_title">
                    <h1>
                        <field name="name" placeholder="Template Name"/>
                    </h1>
                </div>
                <group>
                    <group>
                        <field name="attachment_id"/>
                        <field name="tag_ids" widget="many2many_tags"/>
                    </group>
                    <group>
                        <field name="default_role_ids" widget="many2many_tags"/>
                        <field name="active"/>
                    </group>
                </group>
                <notebook>
                    <page string="Signature Fields" name="fields">
                        <field name="item_ids">
                            <tree editable="bottom">
                                <field name="sequence" widget="handle"/>
                                <field name="type_id"/>
                                <field name="role_id"/>
                                <field name="page"/>
                                <field name="pos_x"/>
                                <field name="pos_y"/>
                                <field name="width"/>
                                <field name="height"/>
                                <field name="required"/>
                                <field name="placeholder"/>
                            </tree>
                        </field>
                        <div class="alert alert-info">
                            Use the visual editor to drag and drop fields onto the PDF preview.
                        </div>
                    </page>
                </notebook>
            </sheet>
        </form>
    </field>
</record>
```

#### Request Form View

```xml
<record id="sign_request_view_form" model="ir.ui.view">
    <field name="name">sign.request.form</field>
    <field name="model">sign.request</field>
    <field name="arch" type="xml">
        <form string="Signature Request">
            <header>
                <button name="action_send" string="Send" type="object"
                        class="btn-primary" invisible="state != 'draft'"/>
                <button name="action_cancel" string="Cancel" type="object"
                        invisible="state in ('done', 'cancelled')"/>
                <field name="state" widget="statusbar"
                       statusbar_visible="draft,sent,signing,done"/>
            </header>
            <sheet>
                <div class="oe_button_box" name="button_box">
                    <button class="oe_stat_button" type="object"
                            name="action_view_document" icon="fa-file-pdf-o">
                        <span>View Document</span>
                    </button>
                </div>
                <div class="oe_title">
                    <h1>
                        <field name="name"/>
                    </h1>
                </div>
                <group>
                    <group>
                        <field name="template_id"/>
                        <field name="subject"/>
                        <field name="expire_date"/>
                    </group>
                    <group>
                        <field name="sent_date"/>
                        <field name="completion_date"/>
                    </group>
                </group>
                <notebook>
                    <page string="Signers" name="signers">
                        <field name="signer_ids">
                            <tree editable="bottom">
                                <field name="sequence" widget="handle"/>
                                <field name="partner_id"/>
                                <field name="email"/>
                                <field name="role_id"/>
                                <field name="state" widget="badge"
                                       decoration-success="state == 'done'"
                                       decoration-info="state in ('sent', 'viewed')"
                                       decoration-danger="state == 'refused'"/>
                                <field name="signed_date"/>
                            </tree>
                        </field>
                    </page>
                    <page string="Message" name="message">
                        <field name="message"/>
                    </page>
                    <page string="Audit Log" name="audit">
                        <field name="audit_log_ids" readonly="1">
                            <tree>
                                <field name="timestamp"/>
                                <field name="action"/>
                                <field name="description"/>
                                <field name="ip_address"/>
                                <field name="hash_value" string="Integrity Hash"/>
                            </tree>
                        </field>
                    </page>
                </notebook>
            </sheet>
            <div class="oe_chatter">
                <field name="message_follower_ids"/>
                <field name="activity_ids"/>
                <field name="message_ids"/>
            </div>
        </form>
    </field>
</record>
```

### Security

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_sign_template_user,sign.template.user,model_sign_template,base.group_user,1,0,0,0
access_sign_template_manager,sign.template.manager,model_sign_template,loomworks_sign.group_sign_manager,1,1,1,1
access_sign_request_user,sign.request.user,model_sign_request,base.group_user,1,1,1,0
access_sign_request_manager,sign.request.manager,model_sign_request,loomworks_sign.group_sign_manager,1,1,1,1
access_sign_request_signer,sign.request.signer,model_sign_request_signer,base.group_user,1,1,1,1
access_sign_role_user,sign.role.user,model_sign_role,base.group_user,1,0,0,0
access_sign_item_type_user,sign.item.type.user,model_sign_item_type,base.group_user,1,0,0,0
access_sign_audit_log,sign.audit.log,model_sign_audit_log,base.group_user,1,0,0,0
```

---

# Module 3: loomworks_appointment (Booking System)

## Overview

The Appointment module provides online booking capabilities for scheduling meetings, consultations, and services. It integrates with Odoo's calendar system and supports external calendar synchronization with Google Calendar and Outlook.

### Calendar Integration Research

Based on research from [Google Calendar API](https://developers.google.com/calendar/api/guides/overview) and [Simply Schedule Appointments](https://simplyscheduleappointments.com/guides/syncing-google-calendar/):

- **Google Calendar API**: Real-time two-way synchronization, OAuth2 authentication
- **iCal Format**: Universal standard for calendar data exchange (.ics files)
- **Microsoft Graph API**: For Outlook/Microsoft 365 calendar integration
- **Timezone Handling**: Critical for international scheduling (use pytz/IANA timezones)

## Technical Design

### Data Models

#### appointment.type (Appointment Configuration)

```python
class AppointmentType(models.Model):
    _name = 'appointment.type'
    _description = 'Appointment Type'
    _inherit = ['mail.thread']
    _order = 'sequence, name'

    name = fields.Char(
        string='Name',
        required=True,
        translate=True
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    # Duration
    duration = fields.Float(
        string='Duration (hours)',
        default=1.0,
        required=True
    )
    duration_minutes = fields.Integer(
        compute='_compute_duration_minutes'
    )

    # Scheduling Configuration
    min_schedule_hours = fields.Float(
        string='Minimum Notice (hours)',
        default=1.0,
        help='Minimum hours before appointment can be booked'
    )
    max_schedule_days = fields.Integer(
        string='Scheduling Window (days)',
        default=30,
        help='How far in advance appointments can be booked'
    )

    # Buffer Time
    buffer_before = fields.Float(
        string='Buffer Before (minutes)',
        default=0,
        help='Blocked time before appointment'
    )
    buffer_after = fields.Float(
        string='Buffer After (minutes)',
        default=0,
        help='Blocked time after appointment'
    )

    # Slot Configuration
    slot_duration = fields.Selection([
        ('15', '15 minutes'),
        ('30', '30 minutes'),
        ('60', '1 hour'),
        ('custom', 'Same as Duration'),
    ], default='30', string='Time Slot Interval')

    # Availability
    slot_ids = fields.One2many(
        'appointment.slot',
        'appointment_type_id',
        string='Availability Slots'
    )

    # Resources/Staff
    user_ids = fields.Many2many(
        'res.users',
        string='Available Staff',
        help='Users who can be assigned to this appointment type'
    )
    assign_method = fields.Selection([
        ('random', 'Random'),
        ('chosen', 'Let Customer Choose'),
        ('balanced', 'Balanced Workload'),
    ], default='random', string='Staff Assignment')

    # Location
    location = fields.Selection([
        ('online', 'Online Meeting'),
        ('in_person', 'In Person'),
        ('phone', 'Phone Call'),
    ], default='online', string='Location Type')
    location_address = fields.Text(string='Address')
    online_meeting_url = fields.Char(string='Meeting URL Template')

    # Notifications
    reminder_ids = fields.One2many(
        'appointment.reminder',
        'appointment_type_id',
        string='Reminders'
    )
    confirmation_mail_template_id = fields.Many2one(
        'mail.template',
        string='Confirmation Email'
    )

    # Portal/Website
    is_published = fields.Boolean(string='Published', default=True)
    website_url = fields.Char(compute='_compute_website_url')

    # Styling
    color = fields.Integer(string='Color')

    # Questions
    question_ids = fields.One2many(
        'appointment.question',
        'appointment_type_id',
        string='Questions'
    )

    # Statistics
    booking_count = fields.Integer(compute='_compute_booking_count')
```

#### appointment.slot (Availability Definition)

```python
class AppointmentSlot(models.Model):
    _name = 'appointment.slot'
    _description = 'Appointment Availability Slot'
    _order = 'weekday, start_hour'

    appointment_type_id = fields.Many2one(
        'appointment.type',
        string='Appointment Type',
        required=True,
        ondelete='cascade'
    )

    # Time Configuration
    weekday = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday'),
    ], required=True, string='Day of Week')

    start_hour = fields.Float(
        string='Start Time',
        required=True,
        help='24-hour format (e.g., 9.0 for 9:00 AM)'
    )
    end_hour = fields.Float(
        string='End Time',
        required=True
    )

    # Optional: Specific staff for this slot
    user_id = fields.Many2one(
        'res.users',
        string='Specific Staff'
    )
```

#### appointment.booking (Individual Booking)

```python
class AppointmentBooking(models.Model):
    _name = 'appointment.booking'
    _description = 'Appointment Booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_datetime desc'

    name = fields.Char(
        string='Reference',
        required=True,
        readonly=True,
        default='New',
        copy=False
    )

    # Type Reference
    appointment_type_id = fields.Many2one(
        'appointment.type',
        string='Appointment Type',
        required=True
    )

    # Scheduling
    start_datetime = fields.Datetime(
        string='Start',
        required=True,
        tracking=True
    )
    end_datetime = fields.Datetime(
        string='End',
        compute='_compute_end_datetime',
        store=True
    )
    duration = fields.Float(
        related='appointment_type_id.duration',
        store=True
    )

    # Timezone
    timezone = fields.Selection(
        selection='_tz_list',
        string='Timezone',
        required=True,
        default=lambda self: self.env.user.tz or 'UTC'
    )

    # Parties
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True
    )
    user_id = fields.Many2one(
        'res.users',
        string='Assigned Staff',
        tracking=True
    )

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show')
    ], default='draft', string='Status', tracking=True)

    # Calendar Integration
    calendar_event_id = fields.Many2one(
        'calendar.event',
        string='Calendar Event',
        readonly=True
    )
    google_event_id = fields.Char(
        string='Google Calendar Event ID'
    )
    outlook_event_id = fields.Char(
        string='Outlook Event ID'
    )

    # Additional Information
    notes = fields.Text(string='Notes')
    answer_ids = fields.One2many(
        'appointment.answer',
        'booking_id',
        string='Answers'
    )

    # Contact
    email = fields.Char(related='partner_id.email', store=True)
    phone = fields.Char(related='partner_id.phone', store=True)

    # Access
    access_token = fields.Char(
        string='Access Token',
        copy=False,
        default=lambda self: self._generate_access_token()
    )

    # Location
    location_type = fields.Selection(
        related='appointment_type_id.location'
    )
    meeting_url = fields.Char(
        string='Meeting URL',
        compute='_compute_meeting_url'
    )

    # Computed
    is_past = fields.Boolean(compute='_compute_is_past')
    can_cancel = fields.Boolean(compute='_compute_can_cancel')

    @api.depends('start_datetime', 'duration')
    def _compute_end_datetime(self):
        for booking in self:
            if booking.start_datetime and booking.duration:
                booking.end_datetime = booking.start_datetime + timedelta(hours=booking.duration)
            else:
                booking.end_datetime = False

    def _tz_list(self):
        """Return list of timezones for selection."""
        import pytz
        return [(tz, tz) for tz in pytz.common_timezones]
```

#### appointment.reminder (Notification Configuration)

```python
class AppointmentReminder(models.Model):
    _name = 'appointment.reminder'
    _description = 'Appointment Reminder'
    _order = 'time_before'

    appointment_type_id = fields.Many2one(
        'appointment.type',
        string='Appointment Type',
        required=True,
        ondelete='cascade'
    )

    time_before = fields.Integer(
        string='Time Before (hours)',
        required=True,
        default=24
    )

    channel = fields.Selection([
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('both', 'Email + SMS'),
    ], default='email', string='Channel')

    mail_template_id = fields.Many2one(
        'mail.template',
        string='Email Template'
    )

    active = fields.Boolean(default=True)
```

#### appointment.question (Intake Questions)

```python
class AppointmentQuestion(models.Model):
    _name = 'appointment.question'
    _description = 'Appointment Booking Question'
    _order = 'sequence'

    appointment_type_id = fields.Many2one(
        'appointment.type',
        string='Appointment Type',
        required=True,
        ondelete='cascade'
    )

    sequence = fields.Integer(default=10)

    question = fields.Char(
        string='Question',
        required=True,
        translate=True
    )

    question_type = fields.Selection([
        ('text', 'Single Line Text'),
        ('textarea', 'Multi-line Text'),
        ('select', 'Dropdown'),
        ('radio', 'Radio Buttons'),
        ('checkbox', 'Checkboxes'),
    ], default='text', string='Type')

    required = fields.Boolean(string='Required', default=False)

    # For select/radio/checkbox
    option_ids = fields.One2many(
        'appointment.question.option',
        'question_id',
        string='Options'
    )
```

#### appointment.answer (Booking Responses)

```python
class AppointmentAnswer(models.Model):
    _name = 'appointment.answer'
    _description = 'Appointment Booking Answer'

    booking_id = fields.Many2one(
        'appointment.booking',
        string='Booking',
        required=True,
        ondelete='cascade'
    )
    question_id = fields.Many2one(
        'appointment.question',
        string='Question',
        required=True
    )
    value = fields.Text(string='Answer')
```

### Calendar Sync Service

```python
# services/calendar_sync.py

import requests
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

class CalendarSyncService:
    """Service for syncing appointments with external calendars."""

    def __init__(self, env):
        self.env = env

    # ========== Odoo Calendar Integration ==========

    def create_calendar_event(self, booking):
        """Create Odoo calendar event for booking."""
        CalendarEvent = self.env['calendar.event']

        event = CalendarEvent.create({
            'name': f'{booking.appointment_type_id.name} - {booking.partner_id.name}',
            'start': booking.start_datetime,
            'stop': booking.end_datetime,
            'user_id': booking.user_id.id,
            'partner_ids': [(4, booking.partner_id.id)],
            'description': booking.notes,
            'location': self._get_location_string(booking),
            'allday': False,
        })

        booking.calendar_event_id = event.id
        return event

    def update_calendar_event(self, booking):
        """Update existing calendar event."""
        if booking.calendar_event_id:
            booking.calendar_event_id.write({
                'start': booking.start_datetime,
                'stop': booking.end_datetime,
                'user_id': booking.user_id.id,
            })

    def delete_calendar_event(self, booking):
        """Delete calendar event on cancellation."""
        if booking.calendar_event_id:
            booking.calendar_event_id.unlink()

    # ========== Google Calendar Integration ==========

    def sync_to_google_calendar(self, booking, user):
        """Sync booking to user's Google Calendar."""
        credentials = self._get_google_credentials(user)
        if not credentials:
            return False

        service = build('calendar', 'v3', credentials=credentials)

        event_body = {
            'summary': f'{booking.appointment_type_id.name} - {booking.partner_id.name}',
            'description': booking.notes or '',
            'start': {
                'dateTime': booking.start_datetime.isoformat(),
                'timeZone': booking.timezone,
            },
            'end': {
                'dateTime': booking.end_datetime.isoformat(),
                'timeZone': booking.timezone,
            },
            'attendees': [
                {'email': booking.partner_id.email},
            ],
        }

        if booking.location_type == 'online' and booking.meeting_url:
            event_body['conferenceData'] = {
                'createRequest': {
                    'requestId': booking.access_token,
                }
            }

        try:
            if booking.google_event_id:
                # Update existing
                event = service.events().update(
                    calendarId='primary',
                    eventId=booking.google_event_id,
                    body=event_body
                ).execute()
            else:
                # Create new
                event = service.events().insert(
                    calendarId='primary',
                    body=event_body,
                    conferenceDataVersion=1
                ).execute()
                booking.google_event_id = event['id']

            return True
        except Exception as e:
            _logger.error(f'Google Calendar sync failed: {e}')
            return False

    def delete_from_google_calendar(self, booking, user):
        """Remove event from Google Calendar."""
        if not booking.google_event_id:
            return

        credentials = self._get_google_credentials(user)
        if not credentials:
            return

        service = build('calendar', 'v3', credentials=credentials)

        try:
            service.events().delete(
                calendarId='primary',
                eventId=booking.google_event_id
            ).execute()
        except Exception as e:
            _logger.error(f'Google Calendar delete failed: {e}')

    def _get_google_credentials(self, user):
        """Get Google OAuth credentials for user."""
        # Implementation depends on how OAuth tokens are stored
        # This is a placeholder
        token_data = user.google_calendar_token
        if not token_data:
            return None

        return Credentials(
            token=token_data.get('access_token'),
            refresh_token=token_data.get('refresh_token'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=self.env['ir.config_parameter'].sudo().get_param('google_calendar_client_id'),
            client_secret=self.env['ir.config_parameter'].sudo().get_param('google_calendar_client_secret'),
        )

    # ========== iCal Export ==========

    def generate_ical(self, booking):
        """Generate iCal (.ics) file for booking."""
        from icalendar import Calendar, Event, vText

        cal = Calendar()
        cal.add('prodid', '-//Loomworks ERP//Appointments//EN')
        cal.add('version', '2.0')

        event = Event()
        event.add('summary', f'{booking.appointment_type_id.name}')
        event.add('dtstart', booking.start_datetime)
        event.add('dtend', booking.end_datetime)
        event.add('description', booking.notes or '')
        event.add('location', self._get_location_string(booking))
        event.add('uid', f'{booking.name}@loomworks')

        # Add organizer
        if booking.user_id:
            event.add('organizer', f'mailto:{booking.user_id.email}')

        cal.add_component(event)

        return cal.to_ical()

    def _get_location_string(self, booking):
        """Get location string for calendar event."""
        if booking.location_type == 'online':
            return booking.meeting_url or 'Online Meeting'
        elif booking.location_type == 'phone':
            return 'Phone Call'
        else:
            return booking.appointment_type_id.location_address or ''
```

### Availability Calculator

```python
# services/availability.py

from datetime import datetime, timedelta
import pytz

class AvailabilityService:
    """Calculate available appointment slots."""

    def __init__(self, env):
        self.env = env

    def get_available_slots(self, appointment_type, start_date, end_date, user_id=None, timezone='UTC'):
        """Get all available slots for an appointment type in date range."""
        tz = pytz.timezone(timezone)
        slots = []

        current_date = start_date
        while current_date <= end_date:
            day_slots = self._get_day_slots(
                appointment_type, current_date, user_id, tz
            )
            slots.extend(day_slots)
            current_date += timedelta(days=1)

        return slots

    def _get_day_slots(self, appointment_type, date, user_id, tz):
        """Get available slots for a specific day."""
        weekday = str(date.weekday())

        # Get slot definitions for this weekday
        slot_defs = appointment_type.slot_ids.filtered(
            lambda s: s.weekday == weekday
        )

        if user_id:
            slot_defs = slot_defs.filtered(
                lambda s: not s.user_id or s.user_id.id == user_id
            )

        available_slots = []

        for slot_def in slot_defs:
            # Generate time slots within this availability window
            slot_times = self._generate_time_slots(
                date, slot_def, appointment_type, tz
            )

            for slot_time in slot_times:
                if self._is_slot_available(
                    appointment_type, slot_time, user_id
                ):
                    available_slots.append({
                        'datetime': slot_time,
                        'datetime_str': slot_time.strftime('%Y-%m-%d %H:%M'),
                        'display_time': slot_time.astimezone(tz).strftime('%I:%M %p'),
                        'user_id': slot_def.user_id.id if slot_def.user_id else None,
                    })

        return available_slots

    def _generate_time_slots(self, date, slot_def, appointment_type, tz):
        """Generate individual time slots within an availability window."""
        # Determine slot interval
        if appointment_type.slot_duration == 'custom':
            interval_minutes = int(appointment_type.duration * 60)
        else:
            interval_minutes = int(appointment_type.slot_duration)

        slots = []

        # Convert hours to datetime
        start_time = datetime.combine(
            date,
            datetime.min.time()
        ).replace(hour=int(slot_def.start_hour),
                  minute=int((slot_def.start_hour % 1) * 60))

        end_time = datetime.combine(
            date,
            datetime.min.time()
        ).replace(hour=int(slot_def.end_hour),
                  minute=int((slot_def.end_hour % 1) * 60))

        # Localize times
        start_time = tz.localize(start_time)
        end_time = tz.localize(end_time)

        # Account for appointment duration
        last_possible_start = end_time - timedelta(hours=appointment_type.duration)

        current = start_time
        while current <= last_possible_start:
            slots.append(current.astimezone(pytz.UTC))
            current += timedelta(minutes=interval_minutes)

        return slots

    def _is_slot_available(self, appointment_type, slot_datetime, user_id):
        """Check if a specific slot is available."""
        # Check minimum notice
        min_notice = timedelta(hours=appointment_type.min_schedule_hours)
        if slot_datetime < datetime.now(pytz.UTC) + min_notice:
            return False

        # Check maximum scheduling window
        max_date = datetime.now(pytz.UTC) + timedelta(days=appointment_type.max_schedule_days)
        if slot_datetime > max_date:
            return False

        # Check for conflicting bookings
        buffer_before = timedelta(minutes=appointment_type.buffer_before)
        buffer_after = timedelta(minutes=appointment_type.buffer_after)
        duration = timedelta(hours=appointment_type.duration)

        conflict_start = slot_datetime - buffer_before
        conflict_end = slot_datetime + duration + buffer_after

        domain = [
            ('appointment_type_id', '=', appointment_type.id),
            ('state', 'in', ['confirmed', 'draft']),
            ('start_datetime', '<', conflict_end),
            ('end_datetime', '>', conflict_start),
        ]

        if user_id:
            domain.append(('user_id', '=', user_id))

        existing = self.env['appointment.booking'].search_count(domain)

        if existing > 0:
            return False

        # Check staff calendar for other events
        if user_id:
            calendar_conflict = self.env['calendar.event'].search_count([
                ('user_id', '=', user_id),
                ('start', '<', conflict_end),
                ('stop', '>', conflict_start),
            ])
            if calendar_conflict > 0:
                return False

        return True
```

### Key Business Logic

```python
class AppointmentBooking(models.Model):
    # ... fields defined above ...

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('appointment.booking') or 'New'

        booking = super().create(vals)

        # Auto-assign staff if not specified
        if not booking.user_id:
            booking.user_id = booking._assign_staff()

        return booking

    def _assign_staff(self):
        """Assign staff member based on appointment type settings."""
        self.ensure_one()
        apt_type = self.appointment_type_id

        if not apt_type.user_ids:
            return False

        if apt_type.assign_method == 'random':
            import random
            return random.choice(apt_type.user_ids.ids)

        elif apt_type.assign_method == 'balanced':
            # Find user with fewest bookings this week
            week_start = fields.Date.today() - timedelta(days=fields.Date.today().weekday())
            week_end = week_start + timedelta(days=7)

            booking_counts = {}
            for user in apt_type.user_ids:
                count = self.search_count([
                    ('user_id', '=', user.id),
                    ('start_datetime', '>=', week_start),
                    ('start_datetime', '<', week_end),
                    ('state', '!=', 'cancelled'),
                ])
                booking_counts[user.id] = count

            return min(booking_counts, key=booking_counts.get)

        return False

    def action_confirm(self):
        """Confirm the booking."""
        self.ensure_one()

        # Create calendar event
        sync_service = self.env['appointment.calendar.sync']
        sync_service.create_calendar_event(self)

        # Sync to external calendars
        if self.user_id.google_calendar_token:
            sync_service.sync_to_google_calendar(self, self.user_id)

        self.state = 'confirmed'

        # Send confirmation email
        self._send_confirmation_email()

    def action_cancel(self):
        """Cancel the booking."""
        self.ensure_one()

        # Remove calendar events
        sync_service = self.env['appointment.calendar.sync']
        sync_service.delete_calendar_event(self)

        if self.google_event_id:
            sync_service.delete_from_google_calendar(self, self.user_id)

        self.state = 'cancelled'

        # Send cancellation notification
        self._send_cancellation_email()

    def _send_confirmation_email(self):
        """Send confirmation email to customer."""
        template = self.appointment_type_id.confirmation_mail_template_id
        if not template:
            template = self.env.ref('loomworks_appointment.mail_template_booking_confirmation', raise_if_not_found=False)

        if template:
            # Generate iCal attachment
            sync_service = self.env['appointment.calendar.sync']
            ical_data = sync_service.generate_ical(self)

            template.send_mail(self.id, email_values={
                'attachment_ids': [(0, 0, {
                    'name': 'appointment.ics',
                    'datas': base64.b64encode(ical_data),
                    'mimetype': 'text/calendar',
                })]
            })

    @api.model
    def _cron_send_reminders(self):
        """Cron job to send appointment reminders."""
        now = fields.Datetime.now()

        # Get all reminder configurations
        reminders = self.env['appointment.reminder'].search([('active', '=', True)])

        for reminder in reminders:
            remind_time = now + timedelta(hours=reminder.time_before)

            bookings = self.search([
                ('state', '=', 'confirmed'),
                ('start_datetime', '>=', remind_time - timedelta(minutes=30)),
                ('start_datetime', '<', remind_time + timedelta(minutes=30)),
            ])

            for booking in bookings:
                # Check if reminder already sent (use mail tracking)
                if reminder.channel in ('email', 'both'):
                    self._send_reminder_email(booking, reminder)
                # SMS would go here if implemented
```

### Portal Controller

```python
# controllers/portal.py

from odoo import http
from odoo.http import request
from datetime import datetime, timedelta
import pytz

class AppointmentPortal(http.Controller):

    @http.route('/appointment', type='http', auth='public', website=True)
    def appointment_list(self, **kwargs):
        """Public page listing available appointment types."""
        appointment_types = request.env['appointment.type'].sudo().search([
            ('is_published', '=', True)
        ])

        return request.render('loomworks_appointment.appointment_list', {
            'appointment_types': appointment_types,
        })

    @http.route('/appointment/<int:appointment_type_id>', type='http', auth='public', website=True)
    def appointment_schedule(self, appointment_type_id, **kwargs):
        """Booking page for specific appointment type."""
        apt_type = request.env['appointment.type'].sudo().browse(appointment_type_id)

        if not apt_type.exists() or not apt_type.is_published:
            return request.redirect('/appointment')

        # Get timezone from request or default
        timezone = kwargs.get('timezone') or request.env.user.tz or 'UTC'

        return request.render('loomworks_appointment.appointment_schedule', {
            'appointment_type': apt_type,
            'timezone': timezone,
            'timezones': pytz.common_timezones,
        })

    @http.route('/appointment/slots', type='json', auth='public')
    def get_slots(self, appointment_type_id, start_date, end_date, user_id=None, timezone='UTC'):
        """AJAX endpoint to get available slots."""
        apt_type = request.env['appointment.type'].sudo().browse(appointment_type_id)

        if not apt_type.exists():
            return {'error': 'Invalid appointment type'}

        availability = request.env['appointment.availability.service']

        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()

        slots = availability.get_available_slots(
            apt_type, start, end, user_id, timezone
        )

        return {'slots': slots}

    @http.route('/appointment/book', type='json', auth='public')
    def book_appointment(self, appointment_type_id, slot_datetime, partner_data, answers=None, timezone='UTC'):
        """Book an appointment."""
        apt_type = request.env['appointment.type'].sudo().browse(appointment_type_id)

        if not apt_type.exists():
            return {'error': 'Invalid appointment type'}

        # Create or find partner
        Partner = request.env['res.partner'].sudo()
        partner = Partner.search([('email', '=', partner_data.get('email'))], limit=1)

        if not partner:
            partner = Partner.create({
                'name': partner_data.get('name'),
                'email': partner_data.get('email'),
                'phone': partner_data.get('phone'),
            })

        # Parse datetime
        slot_dt = datetime.strptime(slot_datetime, '%Y-%m-%d %H:%M')
        tz = pytz.timezone(timezone)
        slot_dt = tz.localize(slot_dt).astimezone(pytz.UTC)

        # Create booking
        Booking = request.env['appointment.booking'].sudo()
        booking = Booking.create({
            'appointment_type_id': apt_type.id,
            'partner_id': partner.id,
            'start_datetime': slot_dt.replace(tzinfo=None),
            'timezone': timezone,
            'notes': partner_data.get('notes'),
        })

        # Save answers
        if answers:
            for question_id, value in answers.items():
                request.env['appointment.answer'].sudo().create({
                    'booking_id': booking.id,
                    'question_id': int(question_id),
                    'value': value,
                })

        # Confirm booking
        booking.action_confirm()

        return {
            'success': True,
            'booking_id': booking.id,
            'reference': booking.name,
            'confirmation_url': f'/appointment/confirmation/{booking.access_token}',
        }

    @http.route('/appointment/confirmation/<string:token>', type='http', auth='public', website=True)
    def booking_confirmation(self, token, **kwargs):
        """Confirmation page after booking."""
        booking = request.env['appointment.booking'].sudo().search([
            ('access_token', '=', token)
        ], limit=1)

        if not booking:
            return request.redirect('/appointment')

        return request.render('loomworks_appointment.booking_confirmation', {
            'booking': booking,
        })

    @http.route('/appointment/cancel/<string:token>', type='http', auth='public', website=True)
    def cancel_booking(self, token, **kwargs):
        """Cancel a booking."""
        booking = request.env['appointment.booking'].sudo().search([
            ('access_token', '=', token)
        ], limit=1)

        if not booking or not booking.can_cancel:
            return request.render('loomworks_appointment.cancel_error')

        booking.action_cancel()

        return request.render('loomworks_appointment.booking_cancelled', {
            'booking': booking,
        })

    @http.route('/appointment/ical/<string:token>', type='http', auth='public')
    def download_ical(self, token, **kwargs):
        """Download iCal file for booking."""
        booking = request.env['appointment.booking'].sudo().search([
            ('access_token', '=', token)
        ], limit=1)

        if not booking:
            return request.not_found()

        sync_service = request.env['appointment.calendar.sync']
        ical_data = sync_service.generate_ical(booking)

        return request.make_response(
            ical_data,
            headers=[
                ('Content-Type', 'text/calendar'),
                ('Content-Disposition', f'attachment; filename=appointment_{booking.name}.ics'),
            ]
        )
```

### Views

#### Appointment Type Form

```xml
<record id="appointment_type_view_form" model="ir.ui.view">
    <field name="name">appointment.type.form</field>
    <field name="model">appointment.type</field>
    <field name="arch" type="xml">
        <form string="Appointment Type">
            <header>
                <button name="action_view_bookings" string="View Bookings" type="object"
                        class="btn-secondary"/>
            </header>
            <sheet>
                <div class="oe_button_box" name="button_box">
                    <button class="oe_stat_button" type="object"
                            name="action_view_bookings" icon="fa-calendar-check-o">
                        <field name="booking_count" string="Bookings" widget="statinfo"/>
                    </button>
                    <button class="oe_stat_button" type="object"
                            name="action_open_website" icon="fa-globe"
                            invisible="not is_published">
                        <span>View on Website</span>
                    </button>
                </div>
                <widget name="web_ribbon" title="Archived" bg_color="bg-danger"
                        invisible="active"/>
                <div class="oe_title">
                    <h1>
                        <field name="name" placeholder="Appointment Type Name"/>
                    </h1>
                </div>
                <group>
                    <group>
                        <field name="duration" widget="float_time"/>
                        <field name="slot_duration"/>
                        <field name="location"/>
                        <field name="location_address" invisible="location != 'in_person'"/>
                        <field name="online_meeting_url" invisible="location != 'online'"/>
                    </group>
                    <group>
                        <field name="min_schedule_hours"/>
                        <field name="max_schedule_days"/>
                        <field name="buffer_before"/>
                        <field name="buffer_after"/>
                    </group>
                </group>
                <notebook>
                    <page string="Availability" name="availability">
                        <group>
                            <field name="user_ids" widget="many2many_tags"/>
                            <field name="assign_method"/>
                        </group>
                        <field name="slot_ids">
                            <tree editable="bottom">
                                <field name="weekday"/>
                                <field name="start_hour" widget="float_time"/>
                                <field name="end_hour" widget="float_time"/>
                                <field name="user_id"/>
                            </tree>
                        </field>
                    </page>
                    <page string="Questions" name="questions">
                        <field name="question_ids">
                            <tree>
                                <field name="sequence" widget="handle"/>
                                <field name="question"/>
                                <field name="question_type"/>
                                <field name="required"/>
                            </tree>
                        </field>
                    </page>
                    <page string="Notifications" name="notifications">
                        <group>
                            <field name="confirmation_mail_template_id"/>
                        </group>
                        <field name="reminder_ids">
                            <tree editable="bottom">
                                <field name="time_before"/>
                                <field name="channel"/>
                                <field name="mail_template_id"/>
                                <field name="active"/>
                            </tree>
                        </field>
                    </page>
                    <page string="Website" name="website">
                        <group>
                            <field name="is_published"/>
                            <field name="website_url" widget="url" readonly="1"/>
                            <field name="color" widget="color_picker"/>
                        </group>
                    </page>
                </notebook>
            </sheet>
        </form>
    </field>
</record>
```

#### Booking Calendar View

```xml
<record id="appointment_booking_view_calendar" model="ir.ui.view">
    <field name="name">appointment.booking.calendar</field>
    <field name="model">appointment.booking</field>
    <field name="arch" type="xml">
        <calendar string="Appointments" date_start="start_datetime" date_stop="end_datetime"
                  color="appointment_type_id" mode="week" event_open_popup="true">
            <field name="name"/>
            <field name="partner_id"/>
            <field name="user_id"/>
            <field name="state"/>
        </calendar>
    </field>
</record>
```

### Security

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_appointment_type_user,appointment.type.user,model_appointment_type,base.group_user,1,0,0,0
access_appointment_type_manager,appointment.type.manager,model_appointment_type,loomworks_appointment.group_appointment_manager,1,1,1,1
access_appointment_slot_user,appointment.slot.user,model_appointment_slot,base.group_user,1,0,0,0
access_appointment_slot_manager,appointment.slot.manager,model_appointment_slot,loomworks_appointment.group_appointment_manager,1,1,1,1
access_appointment_booking_user,appointment.booking.user,model_appointment_booking,base.group_user,1,1,1,0
access_appointment_booking_manager,appointment.booking.manager,model_appointment_booking,loomworks_appointment.group_appointment_manager,1,1,1,1
access_appointment_reminder,appointment.reminder,model_appointment_reminder,loomworks_appointment.group_appointment_manager,1,1,1,1
access_appointment_question,appointment.question,model_appointment_question,loomworks_appointment.group_appointment_manager,1,1,1,1
access_appointment_answer,appointment.answer,model_appointment_answer,base.group_user,1,1,1,0
```

---

# Implementation Tasks

## 1. loomworks_plm Module

- [ ] 1.1 Create module structure and manifest
- [ ] 1.2 Implement `plm.eco` model with all fields
- [ ] 1.3 Implement `plm.eco.type` and `plm.eco.stage` models
- [ ] 1.4 Implement `plm.eco.change.line` model
- [ ] 1.5 Implement `plm.eco.approval` model
- [ ] 1.6 Implement `plm.bom.revision` model
- [ ] 1.7 Extend `mrp.bom` with versioning fields
- [ ] 1.8 Implement ECO workflow methods (confirm, approve, implement)
- [ ] 1.9 Implement BOM versioning and comparison logic
- [ ] 1.10 Create ECO kanban, form, and tree views
- [ ] 1.11 Create BOM revision views
- [ ] 1.12 Define security groups and access rights
- [ ] 1.13 Create demo data
- [ ] 1.14 Create mail templates for notifications
- [ ] 1.15 Write unit tests

## 2. loomworks_sign Module

- [ ] 2.1 Create module structure and manifest
- [ ] 2.2 Implement `sign.request` model with all fields
- [ ] 2.3 Implement `sign.request.signer` model
- [ ] 2.4 Implement `sign.template` and `sign.template.item` models
- [ ] 2.5 Implement `sign.item.type` and `sign.role` models
- [ ] 2.6 Implement `sign.audit.log` model with hash chain
- [ ] 2.7 Implement `sign.request.item.value` model
- [ ] 2.8 Create PDF service for document manipulation
- [ ] 2.9 Implement signature embedding with PyMuPDF
- [ ] 2.10 Implement signing workflow methods
- [ ] 2.11 Create portal controller for public signing
- [ ] 2.12 Create signing page templates (QWeb)
- [ ] 2.13 Create template and request views
- [ ] 2.14 Implement visual field editor (Owl component)
- [ ] 2.15 Define security groups and access rights
- [ ] 2.16 Create mail templates
- [ ] 2.17 Add cron for expiration checking
- [ ] 2.18 Write unit tests

## 3. loomworks_appointment Module

- [ ] 3.1 Create module structure and manifest
- [ ] 3.2 Implement `appointment.type` model
- [ ] 3.3 Implement `appointment.slot` model
- [ ] 3.4 Implement `appointment.booking` model
- [ ] 3.5 Implement `appointment.reminder` model
- [ ] 3.6 Implement `appointment.question` and `appointment.answer` models
- [ ] 3.7 Create calendar sync service (Odoo calendar)
- [ ] 3.8 Implement Google Calendar integration
- [ ] 3.9 Implement iCal export
- [ ] 3.10 Create availability calculation service
- [ ] 3.11 Implement staff assignment logic
- [ ] 3.12 Create portal controller for public booking
- [ ] 3.13 Create booking portal templates
- [ ] 3.14 Create appointment type and booking views
- [ ] 3.15 Create calendar view for bookings
- [ ] 3.16 Define security groups and access rights
- [ ] 3.17 Create mail templates for confirmations/reminders
- [ ] 3.18 Add cron for sending reminders
- [ ] 3.19 Write unit tests

---

# Dependencies

## Python Packages

```
PyMuPDF>=1.23.0       # PDF manipulation
pyHanko>=0.20.0       # Digital signatures (optional, for PAdES)
icalendar>=5.0.0      # iCal generation
pytz>=2024.1          # Timezone handling
google-api-python-client>=2.0.0  # Google Calendar (optional)
google-auth>=2.0.0    # Google OAuth
```

## Odoo Module Dependencies

```python
# loomworks_plm
'depends': ['mrp', 'mail', 'product'],

# loomworks_sign
'depends': ['mail', 'portal', 'web'],

# loomworks_appointment
'depends': ['calendar', 'mail', 'portal', 'website'],
```

---

# Testing Strategy

## Unit Tests

Each module should include tests for:
- Model CRUD operations
- Workflow state transitions
- Computed field calculations
- Security access rules

## Integration Tests

- **PLM**: ECO approval workflow end-to-end, BOM versioning
- **Sign**: Complete signing workflow, audit log integrity
- **Appointment**: Booking flow, availability calculation, calendar sync

## Performance Benchmarks

- BOM comparison: < 2 seconds for BOMs with 100+ lines
- Availability calculation: < 1 second for 30-day range
- PDF signature embedding: < 3 seconds per document

---

# References

## ECO/PLM Best Practices
- [Arena Solutions - Engineering Change Order](https://www.arenasolutions.com/resources/articles/engineering-change-order/)
- [Duro Labs - ECO Best Practices](https://durolabs.co/blog/engineering-change-order/)
- [ComplianceQuest - BOM and Revision Control](https://www.compliancequest.com/bloglet/bom-and-revision-control-systems/)
- [LinkedIn - BOM Version Control Best Practices](https://www.linkedin.com/advice/0/what-best-practices-bom-version-control)

## E-Signature Legal Standards
- [Portant - eSign Complete Guide 2026](https://www.portant.co/post/esign-complete-guide-to-electronic-signatures-in-2026)
- [eSignly - Legally Binding E-Signatures](https://www.esignly.com/electronic-signature/here-s-how-electronic-signature-legally-binding.html)
- [Yousign - International Compliance](https://yousign.com/blog/international-compliance-electronic-signatures)
- [DocuSign - eIDAS Regulation](https://www.docusign.com/products/electronic-signature/learn/eidas)

## PDF Libraries
- [PyMuPDF GitHub](https://github.com/pymupdf/PyMuPDF)
- [pyHanko Documentation](https://docs.pyhanko.eu/en/latest/)
- [Real Python - Create and Modify PDFs](https://realpython.com/creating-modifying-pdf/)

## Calendar Integration
- [Google Calendar API Overview](https://developers.google.com/calendar/api/guides/overview)
- [Simply Schedule Appointments - Google Sync](https://simplyscheduleappointments.com/guides/syncing-google-calendar/)

## Odoo Documentation
- [Odoo 18 Developer Docs](https://www.odoo.com/documentation/18.0/developer.html)
- [Odoo ORM Reference](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html)
