# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

"""
FSM AI Tool Provider - Registers AI tools for field service operations.

Implements the M4 resolution pattern from PATCH_NOTES_M1_M4.md.
"""

from loomworks import api, models


class FSMToolProvider(models.AbstractModel):
    """
    AI Tool Provider for FSM module.

    Provides tools for:
    - Dispatching technicians to tasks
    - Completing service orders
    - Managing route optimization
    """
    _name = 'fsm.tool.provider'
    _inherit = 'loomworks.ai.tool.provider'
    _description = 'FSM AI Tool Provider'

    @api.model
    def _get_tool_definitions(self):
        return [
            {
                'name': 'Dispatch Technician',
                'technical_name': 'fsm_dispatch_technician',
                'category': 'action',
                'description': (
                    "Assign a field service technician to a task. "
                    "Optionally updates the planned start/end times. "
                    "Use this to dispatch technicians to customer sites."
                ),
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'task_id': {
                            'type': 'integer',
                            'description': 'The ID of the FSM task to assign'
                        },
                        'user_id': {
                            'type': 'integer',
                            'description': 'The ID of the user (technician) to assign'
                        },
                        'planned_date_start': {
                            'type': 'string',
                            'format': 'date-time',
                            'description': 'Planned start date/time (ISO format)'
                        },
                        'planned_date_end': {
                            'type': 'string',
                            'format': 'date-time',
                            'description': 'Planned end date/time (ISO format)'
                        }
                    },
                    'required': ['task_id', 'user_id']
                },
                'implementation_method': 'fsm.tool.provider._execute_dispatch_technician',
                'risk_level': 'moderate',
                'requires_confirmation': False,
                'returns_description': 'Updated task details with assigned technician',
            },
            {
                'name': 'Complete Service Order',
                'technical_name': 'fsm_complete_order',
                'category': 'action',
                'description': (
                    "Mark a field service task as complete. "
                    "Records completion time and optionally timesheet hours. "
                    "Note: Customer signature should be captured separately."
                ),
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'task_id': {
                            'type': 'integer',
                            'description': 'The ID of the FSM task to complete'
                        },
                        'hours_worked': {
                            'type': 'number',
                            'description': 'Hours worked (for timesheet entry)'
                        },
                        'notes': {
                            'type': 'string',
                            'description': 'Completion notes'
                        }
                    },
                    'required': ['task_id']
                },
                'implementation_method': 'fsm.tool.provider._execute_complete_order',
                'risk_level': 'moderate',
                'requires_confirmation': True,
                'returns_description': 'Completed task details',
            },
            {
                'name': 'Optimize Route',
                'technical_name': 'fsm_optimize_route',
                'category': 'data',
                'description': (
                    "Get an optimized route order for multiple FSM tasks. "
                    "Uses nearest-neighbor algorithm based on customer locations. "
                    "Returns suggested task order and estimated distances."
                ),
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'task_ids': {
                            'type': 'array',
                            'items': {'type': 'integer'},
                            'description': 'List of task IDs to optimize'
                        },
                        'start_latitude': {
                            'type': 'number',
                            'description': 'Starting point latitude (optional)'
                        },
                        'start_longitude': {
                            'type': 'number',
                            'description': 'Starting point longitude (optional)'
                        }
                    },
                    'required': ['task_ids']
                },
                'implementation_method': 'fsm.tool.provider._execute_optimize_route',
                'risk_level': 'safe',
                'returns_description': 'Optimized route with distances and estimated time',
            },
            {
                'name': 'Get FSM Tasks',
                'technical_name': 'fsm_get_tasks',
                'category': 'data',
                'description': (
                    "Get field service tasks for a technician or project. "
                    "Filter by status, date range, or assigned user."
                ),
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'user_id': {
                            'type': 'integer',
                            'description': 'Filter by assigned technician user ID'
                        },
                        'project_id': {
                            'type': 'integer',
                            'description': 'Filter by project ID'
                        },
                        'date': {
                            'type': 'string',
                            'format': 'date',
                            'description': 'Filter by planned date (YYYY-MM-DD)'
                        },
                        'status': {
                            'type': 'string',
                            'enum': ['pending', 'in_progress', 'done'],
                            'description': 'Filter by task status'
                        },
                        'limit': {
                            'type': 'integer',
                            'description': 'Maximum number of tasks to return',
                            'default': 20
                        }
                    }
                },
                'implementation_method': 'fsm.tool.provider._execute_get_tasks',
                'risk_level': 'safe',
                'returns_description': 'List of FSM tasks matching criteria',
            },
        ]

    @api.model
    def _execute_dispatch_technician(self, task_id, user_id, planned_date_start=None, planned_date_end=None):
        """Execute the fsm_dispatch_technician tool."""
        task = self.env['project.task'].browse(task_id)
        if not task.exists():
            return {'error': f'Task with ID {task_id} not found'}

        if not task.is_fsm:
            return {'error': f'Task {task_id} is not an FSM task'}

        user = self.env['res.users'].browse(user_id)
        if not user.exists():
            return {'error': f'User with ID {user_id} not found'}

        vals = {
            'fsm_user_id': user_id,
            'user_ids': [(4, user_id)],  # Also add to assignees
        }

        if planned_date_start:
            vals['planned_date_start'] = planned_date_start
        if planned_date_end:
            vals['planned_date_end'] = planned_date_end

        task.write(vals)

        return {
            'success': True,
            'task_id': task.id,
            'task_name': task.name,
            'technician': user.name,
            'planned_start': str(task.planned_date_start) if task.planned_date_start else None,
            'planned_end': str(task.planned_date_end) if task.planned_date_end else None,
            'customer': task.partner_id.name if task.partner_id else None,
        }

    @api.model
    def _execute_complete_order(self, task_id, hours_worked=None, notes=None):
        """Execute the fsm_complete_order tool."""
        task = self.env['project.task'].browse(task_id)
        if not task.exists():
            return {'error': f'Task with ID {task_id} not found'}

        if not task.is_fsm:
            return {'error': f'Task {task_id} is not an FSM task'}

        # Add notes if provided
        if notes:
            task.message_post(body=f"Completion notes: {notes}")

        # Create timesheet if hours provided
        if hours_worked and hours_worked > 0:
            task._create_timesheet_entry(hours_worked)

        # Mark as done
        task.write({'fsm_done': True})

        return {
            'success': True,
            'task_id': task.id,
            'task_name': task.name,
            'status': 'done',
            'hours_logged': hours_worked or task.total_hours_spent,
            'customer': task.partner_id.name if task.partner_id else None,
            'has_signature': bool(task.customer_signature),
        }

    @api.model
    def _execute_optimize_route(self, task_ids, start_latitude=None, start_longitude=None):
        """Execute the fsm_optimize_route tool."""
        helper = self.env['fsm.route.helper']

        start_location = None
        if start_latitude and start_longitude:
            start_location = (start_latitude, start_longitude)

        # Get optimized order
        optimized_ids = helper.get_suggested_route(task_ids, start_location)

        # Get route summary
        summary = helper.get_route_summary(optimized_ids, start_location)

        return {
            'success': True,
            'optimized_order': optimized_ids,
            'total_distance_km': summary['total_distance'],
            'estimated_drive_time_minutes': summary['estimated_drive_time_minutes'],
            'stops': summary['tasks'],
        }

    @api.model
    def _execute_get_tasks(self, user_id=None, project_id=None, date=None, status=None, limit=20):
        """Execute the fsm_get_tasks tool."""
        domain = [('is_fsm', '=', True)]

        if user_id:
            domain.append(('fsm_user_id', '=', user_id))
        if project_id:
            domain.append(('project_id', '=', project_id))
        if date:
            domain.extend([
                ('planned_date_start', '>=', f'{date} 00:00:00'),
                ('planned_date_start', '<=', f'{date} 23:59:59'),
            ])
        if status:
            if status == 'done':
                domain.append(('fsm_done', '=', True))
            elif status == 'in_progress':
                domain.extend([
                    ('fsm_done', '=', False),
                    ('timer_start', '!=', False),
                ])
            elif status == 'pending':
                domain.extend([
                    ('fsm_done', '=', False),
                    ('timer_start', '=', False),
                ])

        tasks = self.env['project.task'].search(domain, limit=limit, order='planned_date_start')

        return {
            'count': len(tasks),
            'tasks': [
                {
                    'id': t.id,
                    'name': t.name,
                    'project': t.project_id.name if t.project_id else None,
                    'customer': t.partner_id.name if t.partner_id else None,
                    'address': t.partner_id._display_address(without_company=True) if t.partner_id else None,
                    'technician': t.fsm_user_id.name if t.fsm_user_id else None,
                    'planned_start': str(t.planned_date_start) if t.planned_date_start else None,
                    'fsm_done': t.fsm_done,
                    'has_signature': bool(t.customer_signature),
                }
                for t in tasks
            ]
        }
