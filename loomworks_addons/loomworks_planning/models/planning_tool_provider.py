# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import api, fields, models, _


class PlanningToolProvider(models.AbstractModel):
    """AI Tool Provider for Planning operations."""
    _name = 'planning.tool.provider'
    _inherit = 'ai.tool.provider.mixin'
    _description = 'Planning AI Tool Provider'

    @api.model
    def _get_ai_tools(self):
        """Return available planning AI tools."""
        return [
            {
                'name': 'planning_create_shift',
                'description': 'Create a new planning slot/shift assignment',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'employee_id': {
                            'type': 'integer',
                            'description': 'Employee ID to assign',
                        },
                        'employee_name': {
                            'type': 'string',
                            'description': 'Employee name to search if ID not provided',
                        },
                        'role_id': {
                            'type': 'integer',
                            'description': 'Planning role ID',
                        },
                        'role_name': {
                            'type': 'string',
                            'description': 'Role name to search if ID not provided',
                        },
                        'start_datetime': {
                            'type': 'string',
                            'format': 'date-time',
                            'description': 'Start date and time (ISO format)',
                        },
                        'end_datetime': {
                            'type': 'string',
                            'format': 'date-time',
                            'description': 'End date and time (ISO format)',
                        },
                        'duration_hours': {
                            'type': 'number',
                            'description': 'Duration in hours (if end_datetime not provided)',
                        },
                        'project_id': {
                            'type': 'integer',
                            'description': 'Optional project ID to link',
                        },
                        'publish': {
                            'type': 'boolean',
                            'description': 'Publish immediately after creation',
                            'default': False,
                        },
                    },
                    'required': ['start_datetime'],
                },
            },
            {
                'name': 'planning_get_availability',
                'description': 'Check employee availability for planning',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'employee_id': {
                            'type': 'integer',
                            'description': 'Employee ID to check',
                        },
                        'employee_name': {
                            'type': 'string',
                            'description': 'Employee name to search',
                        },
                        'date_from': {
                            'type': 'string',
                            'format': 'date',
                            'description': 'Start date (YYYY-MM-DD)',
                        },
                        'date_to': {
                            'type': 'string',
                            'format': 'date',
                            'description': 'End date (YYYY-MM-DD)',
                        },
                    },
                    'required': ['date_from', 'date_to'],
                },
            },
            {
                'name': 'planning_detect_conflicts',
                'description': 'Find scheduling conflicts in a date range',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'date_from': {
                            'type': 'string',
                            'format': 'date',
                            'description': 'Start date (YYYY-MM-DD)',
                        },
                        'date_to': {
                            'type': 'string',
                            'format': 'date',
                            'description': 'End date (YYYY-MM-DD)',
                        },
                        'employee_id': {
                            'type': 'integer',
                            'description': 'Optional: check specific employee only',
                        },
                    },
                    'required': ['date_from', 'date_to'],
                },
            },
            {
                'name': 'planning_get_schedule',
                'description': 'Get planning schedule for employees or date range',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'date_from': {
                            'type': 'string',
                            'format': 'date',
                            'description': 'Start date (YYYY-MM-DD)',
                        },
                        'date_to': {
                            'type': 'string',
                            'format': 'date',
                            'description': 'End date (YYYY-MM-DD)',
                        },
                        'employee_id': {
                            'type': 'integer',
                            'description': 'Filter by employee',
                        },
                        'role_id': {
                            'type': 'integer',
                            'description': 'Filter by role',
                        },
                        'state': {
                            'type': 'string',
                            'enum': ['draft', 'published', 'done', 'cancelled'],
                            'description': 'Filter by state',
                        },
                    },
                    'required': ['date_from', 'date_to'],
                },
            },
            {
                'name': 'planning_publish_slots',
                'description': 'Publish planning slots to make visible to employees',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'slot_ids': {
                            'type': 'array',
                            'items': {'type': 'integer'},
                            'description': 'List of slot IDs to publish',
                        },
                        'date_from': {
                            'type': 'string',
                            'format': 'date',
                            'description': 'Publish all draft slots from this date',
                        },
                        'date_to': {
                            'type': 'string',
                            'format': 'date',
                            'description': 'Publish all draft slots until this date',
                        },
                    },
                },
            },
        ]

    @api.model
    def _execute_ai_tool(self, tool_name, parameters):
        """Execute a planning AI tool."""
        if tool_name == 'planning_create_shift':
            return self._tool_create_shift(parameters)
        elif tool_name == 'planning_get_availability':
            return self._tool_get_availability(parameters)
        elif tool_name == 'planning_detect_conflicts':
            return self._tool_detect_conflicts(parameters)
        elif tool_name == 'planning_get_schedule':
            return self._tool_get_schedule(parameters)
        elif tool_name == 'planning_publish_slots':
            return self._tool_publish_slots(parameters)
        else:
            return {'error': f'Unknown tool: {tool_name}'}

    def _tool_create_shift(self, params):
        """Create a new planning slot."""
        PlanningSlot = self.env['planning.slot']

        # Find employee
        employee = None
        if params.get('employee_id'):
            employee = self.env['hr.employee'].browse(params['employee_id']).exists()
        elif params.get('employee_name'):
            employee = self.env['hr.employee'].search([
                ('name', 'ilike', params['employee_name'])
            ], limit=1)

        # Find role
        role = None
        if params.get('role_id'):
            role = self.env['planning.role'].browse(params['role_id']).exists()
        elif params.get('role_name'):
            role = self.env['planning.role'].search([
                ('name', 'ilike', params['role_name'])
            ], limit=1)

        # Parse dates
        start_dt = fields.Datetime.from_string(params['start_datetime'])

        if params.get('end_datetime'):
            end_dt = fields.Datetime.from_string(params['end_datetime'])
        elif params.get('duration_hours'):
            end_dt = start_dt + timedelta(hours=params['duration_hours'])
        else:
            end_dt = start_dt + timedelta(hours=8)  # Default 8 hours

        # Create slot
        vals = {
            'start_datetime': start_dt,
            'end_datetime': end_dt,
            'state': 'draft',
        }

        if employee:
            vals['employee_id'] = employee.id
        if role:
            vals['role_id'] = role.id
        if params.get('project_id'):
            vals['project_id'] = params['project_id']

        slot = PlanningSlot.create(vals)

        # Optionally publish
        if params.get('publish') and not slot.has_conflict:
            slot.action_publish()

        return {
            'success': True,
            'slot_id': slot.id,
            'name': slot.name,
            'employee': employee.name if employee else None,
            'role': role.name if role else None,
            'start': slot.start_datetime.isoformat(),
            'end': slot.end_datetime.isoformat(),
            'hours': slot.allocated_hours,
            'state': slot.state,
            'has_conflict': slot.has_conflict,
            'conflict_description': slot.conflict_description,
        }

    def _tool_get_availability(self, params):
        """Get employee availability."""
        date_from = fields.Date.from_string(params['date_from'])
        date_to = fields.Date.from_string(params['date_to'])

        # Find employees
        employees = self.env['hr.employee']
        if params.get('employee_id'):
            employees = self.env['hr.employee'].browse(params['employee_id']).exists()
        elif params.get('employee_name'):
            employees = self.env['hr.employee'].search([
                ('name', 'ilike', params['employee_name'])
            ])
        else:
            # All active employees
            employees = self.env['hr.employee'].search([('active', '=', True)])

        results = []
        for emp in employees:
            available = emp.get_availability(
                datetime.combine(date_from, datetime.min.time()),
                datetime.combine(date_to, datetime.max.time())
            )
            results.append({
                'employee_id': emp.id,
                'employee_name': emp.name,
                'available_hours': available,
                'default_role': emp.default_planning_role_id.name if emp.default_planning_role_id else None,
            })

        return {
            'date_from': params['date_from'],
            'date_to': params['date_to'],
            'employees': results,
        }

    def _tool_detect_conflicts(self, params):
        """Find scheduling conflicts."""
        date_from = fields.Date.from_string(params['date_from'])
        date_to = fields.Date.from_string(params['date_to'])

        domain = [
            ('has_conflict', '=', True),
            ('start_datetime', '>=', datetime.combine(date_from, datetime.min.time())),
            ('start_datetime', '<=', datetime.combine(date_to, datetime.max.time())),
            ('state', 'not in', ['cancelled']),
        ]

        if params.get('employee_id'):
            domain.append(('employee_id', '=', params['employee_id']))

        conflicts = self.env['planning.slot'].search(domain)

        return {
            'date_from': params['date_from'],
            'date_to': params['date_to'],
            'conflict_count': len(conflicts),
            'conflicts': [{
                'slot_id': slot.id,
                'employee': slot.employee_id.name,
                'start': slot.start_datetime.isoformat(),
                'end': slot.end_datetime.isoformat(),
                'role': slot.role_id.name if slot.role_id else None,
                'conflict_description': slot.conflict_description,
            } for slot in conflicts[:20]],  # Limit to 20
        }

    def _tool_get_schedule(self, params):
        """Get planning schedule."""
        date_from = fields.Date.from_string(params['date_from'])
        date_to = fields.Date.from_string(params['date_to'])

        domain = [
            ('start_datetime', '>=', datetime.combine(date_from, datetime.min.time())),
            ('start_datetime', '<=', datetime.combine(date_to, datetime.max.time())),
        ]

        if params.get('employee_id'):
            domain.append(('employee_id', '=', params['employee_id']))
        if params.get('role_id'):
            domain.append(('role_id', '=', params['role_id']))
        if params.get('state'):
            domain.append(('state', '=', params['state']))
        else:
            domain.append(('state', '!=', 'cancelled'))

        slots = self.env['planning.slot'].search(domain, order='start_datetime')

        return {
            'date_from': params['date_from'],
            'date_to': params['date_to'],
            'slot_count': len(slots),
            'total_hours': sum(slots.mapped('allocated_hours')),
            'slots': [{
                'slot_id': slot.id,
                'name': slot.name,
                'employee': slot.employee_id.name if slot.employee_id else 'Unassigned',
                'role': slot.role_id.name if slot.role_id else None,
                'start': slot.start_datetime.isoformat(),
                'end': slot.end_datetime.isoformat(),
                'hours': slot.allocated_hours,
                'state': slot.state,
                'has_conflict': slot.has_conflict,
            } for slot in slots[:50]],  # Limit to 50
        }

    def _tool_publish_slots(self, params):
        """Publish planning slots."""
        PlanningSlot = self.env['planning.slot']

        if params.get('slot_ids'):
            slots = PlanningSlot.browse(params['slot_ids']).exists()
        elif params.get('date_from') and params.get('date_to'):
            date_from = fields.Date.from_string(params['date_from'])
            date_to = fields.Date.from_string(params['date_to'])
            slots = PlanningSlot.search([
                ('state', '=', 'draft'),
                ('start_datetime', '>=', datetime.combine(date_from, datetime.min.time())),
                ('start_datetime', '<=', datetime.combine(date_to, datetime.max.time())),
            ])
        else:
            return {'error': 'Must provide slot_ids or date range'}

        # Filter out slots with conflicts
        publishable = slots.filtered(lambda s: not s.has_conflict)
        with_conflicts = slots.filtered(lambda s: s.has_conflict)

        if publishable:
            publishable.action_publish()

        return {
            'success': True,
            'published_count': len(publishable),
            'skipped_conflicts': len(with_conflicts),
            'published_slots': [{
                'slot_id': s.id,
                'name': s.name,
            } for s in publishable],
            'conflict_slots': [{
                'slot_id': s.id,
                'name': s.name,
                'conflict': s.conflict_description,
            } for s in with_conflicts],
        }
