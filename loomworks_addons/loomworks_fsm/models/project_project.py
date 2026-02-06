# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.

from loomworks import api, fields, models, _


class ProjectProject(models.Model):
    """
    Extension of project.project for FSM functionality.

    When a project is marked as FSM, tasks created within it
    automatically inherit FSM capabilities.
    """
    _inherit = 'project.project'

    # FSM flag
    is_fsm = fields.Boolean(
        string='Field Service Project',
        default=False,
        help="Enable field service features for tasks in this project. "
             "Tasks created in this project will have FSM capabilities.")

    # FSM task counts
    fsm_task_count = fields.Integer(
        string='FSM Tasks',
        compute='_compute_fsm_counts')
    fsm_done_count = fields.Integer(
        string='Completed FSM Tasks',
        compute='_compute_fsm_counts')

    # Default worksheet template for FSM tasks
    default_worksheet_template_id = fields.Many2one(
        'fsm.worksheet.template',
        string='Default Worksheet Template',
        help="Default worksheet template for FSM tasks in this project")

    @api.depends('task_ids.is_fsm', 'task_ids.fsm_done')
    def _compute_fsm_counts(self):
        for project in self:
            fsm_tasks = project.task_ids.filtered('is_fsm')
            project.fsm_task_count = len(fsm_tasks)
            project.fsm_done_count = len(fsm_tasks.filtered('fsm_done'))

    @api.model_create_multi
    def create(self, vals_list):
        projects = super().create(vals_list)
        return projects

    def action_view_fsm_tasks(self):
        """Open FSM tasks for this project."""
        self.ensure_one()
        return {
            'name': _('Field Service Tasks'),
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_mode': 'kanban,list,form,calendar',
            'domain': [('project_id', '=', self.id), ('is_fsm', '=', True)],
            'context': {
                'default_project_id': self.id,
                'default_is_fsm': True,
            },
        }
