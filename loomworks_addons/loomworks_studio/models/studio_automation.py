# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Studio Automation Model - Workflow rules and server actions.

This model allows users to create automations that trigger on various
events (create, update, time-based) and execute actions.
"""

import logging

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools.safe_eval import safe_eval, test_python_expr

_logger = logging.getLogger(__name__)


class StudioAutomation(models.Model):
    """
    Automation rule created via Studio.

    Automations define when and what actions should be triggered,
    such as sending emails, updating fields, or executing code.
    """
    _name = 'studio.automation'
    _description = 'Studio Automation Rule'
    _order = 'sequence, name'

    name = fields.Char(
        string='Name',
        required=True,
        help="Descriptive name for this automation"
    )
    app_id = fields.Many2one(
        'studio.app',
        string='Studio App',
        ondelete='cascade'
    )
    active = fields.Boolean(
        default=True
    )
    sequence = fields.Integer(
        default=10
    )

    # Trigger Configuration
    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        required=True,
        ondelete='cascade',
        help="Model this automation applies to"
    )
    model_name = fields.Char(
        related='model_id.model',
        store=True
    )
    trigger_type = fields.Selection([
        ('on_create', 'On Creation'),
        ('on_write', 'On Update'),
        ('on_create_or_write', 'On Creation & Update'),
        ('on_unlink', 'On Deletion'),
        ('on_time', 'Based on Time Condition'),
        ('on_condition', 'Based on Condition'),
    ], string='Trigger', required=True, default='on_create')

    # Filter conditions
    filter_domain = fields.Char(
        string='Apply On',
        default='[]',
        help="Domain to filter which records trigger this automation"
    )
    filter_pre_domain = fields.Char(
        string='Before Update Domain',
        help="For 'on_write': condition before the update"
    )

    # Time-based trigger settings
    trg_date_id = fields.Many2one(
        'ir.model.fields',
        string='Trigger Date Field',
        domain="[('model_id', '=', model_id), ('ttype', 'in', ['date', 'datetime'])]",
        help="Date field to trigger on"
    )
    trg_date_range = fields.Integer(
        string='Delay',
        default=0,
        help="Delay after the trigger date field"
    )
    trg_date_range_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('months', 'Months'),
    ], string='Delay Type', default='days')

    # Action Configuration
    action_type = fields.Selection([
        ('update_record', 'Update Record'),
        ('create_record', 'Create New Record'),
        ('send_email', 'Send Email'),
        ('add_followers', 'Add Followers'),
        ('remove_followers', 'Remove Followers'),
        ('create_activity', 'Create Activity'),
        ('send_sms', 'Send SMS'),
        ('python_code', 'Execute Python Code'),
        ('webhook', 'Call Webhook'),
        ('multi', 'Execute Multiple Actions'),
    ], string='Action Type', required=True, default='update_record')

    # Update Record Action
    update_field_ids = fields.One2many(
        'studio.automation.update',
        'automation_id',
        string='Field Updates'
    )

    # Create Record Action
    create_model_id = fields.Many2one(
        'ir.model',
        string='Target Model',
        help="Model to create record in"
    )
    create_field_ids = fields.One2many(
        'studio.automation.update',
        'automation_id',
        string='Values to Set',
        domain=[('is_create_action', '=', True)]
    )

    # Email Action
    email_template_id = fields.Many2one(
        'mail.template',
        string='Email Template'
    )

    # Activity Action
    activity_type_id = fields.Many2one(
        'mail.activity.type',
        string='Activity Type'
    )
    activity_summary = fields.Char(
        string='Activity Summary'
    )
    activity_note = fields.Html(
        string='Activity Note'
    )
    activity_user_id = fields.Many2one(
        'res.users',
        string='Responsible User'
    )
    activity_user_field_id = fields.Many2one(
        'ir.model.fields',
        string='Responsible Field',
        domain="[('model_id', '=', model_id), ('ttype', '=', 'many2one'), ('relation', '=', 'res.users')]"
    )
    activity_date_deadline_range = fields.Integer(
        string='Due Date Delay',
        default=0
    )
    activity_date_deadline_range_type = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ], string='Due Date Type', default='days')

    # Python Code Action
    python_code = fields.Text(
        string='Python Code',
        default="""# Available variables:
#  - env: Odoo Environment
#  - model: Model of the record (e.g., env['res.partner'])
#  - records: Recordset that triggered the action
#  - record: First record (shortcut for records[0])
#  - time, datetime, dateutil, timezone: Python libraries
#  - log: Logging function (log(message, level='info'))
#  - Warning: odoo.exceptions.Warning exception class
#
# Example:
# for record in records:
#     record.write({'field_name': 'new_value'})
""",
        help="Python code to execute when triggered"
    )

    # Webhook Action
    webhook_url = fields.Char(
        string='Webhook URL'
    )
    webhook_payload = fields.Text(
        string='Webhook Payload (JSON)',
        help="JSON template for webhook body. Use {{field_name}} for dynamic values."
    )

    # Multi Action
    child_ids = fields.One2many(
        'studio.automation',
        'parent_id',
        string='Sub-Actions'
    )
    parent_id = fields.Many2one(
        'studio.automation',
        string='Parent Action'
    )

    # Generated server action
    server_action_id = fields.Many2one(
        'ir.actions.server',
        string='Server Action',
        readonly=True,
        help="Generated Odoo server action"
    )

    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('disabled', 'Disabled'),
    ], string='Status', default='draft')

    # Statistics
    execution_count = fields.Integer(
        string='Execution Count',
        readonly=True,
        help="Number of times this automation has run"
    )
    last_run = fields.Datetime(
        string='Last Run',
        readonly=True
    )

    @api.constrains('python_code')
    def _check_python_code(self):
        """Validate Python code syntax."""
        for automation in self.filtered('python_code'):
            if automation.action_type == 'python_code':
                msg = test_python_expr(
                    expr=automation.python_code.strip(),
                    mode='exec'
                )
                if msg:
                    raise ValidationError(_(
                        "Python code error:\n%(error)s",
                        error=msg
                    ))

    @api.constrains('filter_domain')
    def _check_filter_domain(self):
        """Validate filter domain syntax."""
        for automation in self:
            try:
                domain = safe_eval(automation.filter_domain or '[]')
                if not isinstance(domain, list):
                    raise ValidationError(_("Filter domain must be a list."))
            except Exception as e:
                raise ValidationError(_(
                    "Invalid filter domain: %(error)s",
                    error=str(e)
                ))

    # ---------------------------------
    # Actions
    # ---------------------------------

    def action_activate(self):
        """Activate the automation."""
        for automation in self:
            automation._generate_server_action()
            automation.state = 'active'
        return True

    def action_deactivate(self):
        """Deactivate the automation."""
        self.write({'state': 'disabled'})
        return True

    def action_test(self):
        """Test the automation with sample records."""
        self.ensure_one()

        if not self.model_name or self.model_name not in self.env:
            raise UserError(_("Model not found."))

        # Get sample records
        Model = self.env[self.model_name]
        domain = safe_eval(self.filter_domain or '[]')
        records = Model.search(domain, limit=3)

        if not records:
            raise UserError(_(
                "No records match the filter domain. "
                "Cannot test automation."
            ))

        # Execute in test mode (no actual changes)
        try:
            self._execute_action(records, test_mode=True)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Test Successful"),
                    'message': _("Automation would execute on %d record(s).", len(records)),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_(
                "Test failed with error:\n%(error)s",
                error=str(e)
            ))

    def _generate_server_action(self):
        """Generate the underlying ir.actions.server record."""
        self.ensure_one()

        action_vals = {
            'name': f"Studio: {self.name}",
            'model_id': self.model_id.id,
            'state': self._get_server_action_state(),
            'binding_type': 'action',
        }

        if self.action_type == 'python_code':
            action_vals['code'] = self._prepare_python_code()
        elif self.action_type == 'update_record':
            action_vals['state'] = 'object_write'
            action_vals['update_path'] = 'record'
            # Field updates handled separately
        elif self.action_type == 'send_email' and self.email_template_id:
            action_vals['state'] = 'mail_post'
            action_vals['mail_template_id'] = self.email_template_id.id
        elif self.action_type == 'create_activity':
            action_vals['state'] = 'next_activity'
            action_vals['activity_type_id'] = self.activity_type_id.id
            action_vals['activity_summary'] = self.activity_summary
            action_vals['activity_note'] = self.activity_note

        if self.server_action_id:
            self.server_action_id.write(action_vals)
        else:
            action = self.env['ir.actions.server'].sudo().create(action_vals)
            self.server_action_id = action

        # Create base automation
        self._create_base_automation()

    def _get_server_action_state(self):
        """Map Studio action type to ir.actions.server state."""
        mapping = {
            'python_code': 'code',
            'update_record': 'object_write',
            'create_record': 'object_create',
            'send_email': 'mail_post',
            'add_followers': 'followers',
            'create_activity': 'next_activity',
            'multi': 'multi',
        }
        return mapping.get(self.action_type, 'code')

    def _prepare_python_code(self):
        """Prepare Python code with proper context setup."""
        return f"""
# Studio Automation: {self.name}
records = env['{self.model_name}'].browse(active_ids or [])
record = records[0] if records else env['{self.model_name}']

import logging
_logger = logging.getLogger('studio.automation')

def log(message, level='info'):
    getattr(_logger, level)(message)

# User code:
{self.python_code or 'pass'}
"""

    def _create_base_automation(self):
        """Create base.automation record for triggers."""
        BaseAutomation = self.env['base.automation']

        trigger_mapping = {
            'on_create': 'on_create',
            'on_write': 'on_write',
            'on_create_or_write': 'on_create_or_write',
            'on_unlink': 'on_unlink',
            'on_time': 'on_time',
            'on_condition': 'on_change',
        }

        automation_vals = {
            'name': f"Studio: {self.name}",
            'model_id': self.model_id.id,
            'trigger': trigger_mapping.get(self.trigger_type, 'on_create'),
            'action_server_ids': [(6, 0, [self.server_action_id.id])],
            'filter_domain': self.filter_domain,
            'active': self.state == 'active',
        }

        if self.trigger_type == 'on_time' and self.trg_date_id:
            automation_vals.update({
                'trg_date_id': self.trg_date_id.id,
                'trg_date_range': self.trg_date_range,
                'trg_date_range_type': self.trg_date_range_type,
            })

        # Check for existing base automation
        existing = BaseAutomation.search([
            ('name', '=', f"Studio: {self.name}"),
            ('model_id', '=', self.model_id.id),
        ], limit=1)

        if existing:
            existing.write(automation_vals)
        else:
            BaseAutomation.sudo().create(automation_vals)

    def _execute_action(self, records, test_mode=False):
        """Execute the automation action on records."""
        self.ensure_one()

        if test_mode:
            _logger.info(
                "Test execution of automation '%s' on %d records",
                self.name, len(records)
            )
            return True

        # Update execution stats
        self.write({
            'execution_count': self.execution_count + 1,
            'last_run': fields.Datetime.now(),
        })

        if self.server_action_id:
            ctx = dict(self.env.context, active_ids=records.ids)
            self.server_action_id.with_context(ctx).run()

        return True


class StudioAutomationUpdate(models.Model):
    """Field update configuration for automation actions."""
    _name = 'studio.automation.update'
    _description = 'Studio Automation Field Update'

    automation_id = fields.Many2one(
        'studio.automation',
        string='Automation',
        required=True,
        ondelete='cascade'
    )
    is_create_action = fields.Boolean(
        string='For Create Action',
        default=False
    )

    field_id = fields.Many2one(
        'ir.model.fields',
        string='Field',
        required=True,
        ondelete='cascade'
    )
    field_name = fields.Char(
        related='field_id.name'
    )
    field_type = fields.Selection(
        related='field_id.ttype'
    )

    # Value configuration
    value_type = fields.Selection([
        ('value', 'Static Value'),
        ('reference', 'Reference Field'),
        ('python', 'Python Expression'),
    ], string='Value Type', default='value', required=True)

    value_char = fields.Char(string='Text Value')
    value_integer = fields.Integer(string='Integer Value')
    value_float = fields.Float(string='Decimal Value')
    value_boolean = fields.Boolean(string='Boolean Value')
    value_date = fields.Date(string='Date Value')
    value_datetime = fields.Datetime(string='DateTime Value')
    value_reference = fields.Char(string='Reference Field Path')
    value_python = fields.Char(string='Python Expression')
    value_selection = fields.Char(string='Selection Value')
    value_many2one = fields.Integer(string='Many2one ID')

    def get_value(self, record):
        """Get the computed value for this update."""
        self.ensure_one()

        if self.value_type == 'reference' and self.value_reference:
            # Navigate through field path
            value = record
            for attr in self.value_reference.split('.'):
                value = getattr(value, attr, False)
            return value

        elif self.value_type == 'python' and self.value_python:
            return safe_eval(
                self.value_python,
                {'record': record, 'env': self.env}
            )

        else:
            # Static value based on field type
            field_type = self.field_type
            if field_type == 'char':
                return self.value_char
            elif field_type == 'integer':
                return self.value_integer
            elif field_type == 'float':
                return self.value_float
            elif field_type == 'boolean':
                return self.value_boolean
            elif field_type == 'date':
                return self.value_date
            elif field_type == 'datetime':
                return self.value_datetime
            elif field_type == 'selection':
                return self.value_selection
            elif field_type == 'many2one':
                return self.value_many2one

        return False
