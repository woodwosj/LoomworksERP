# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import models


class MailActivitySchedule(models.TransientModel):
    _inherit = 'mail.activity.schedule'

    def _compute_plan_department_filterable(self):
        super()._compute_plan_department_filterable()
        for wizard in self:
            if not wizard.plan_department_filterable:
                wizard.plan_department_filterable = wizard.res_model == 'hr.applicant'
