# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import models


class MailActivityPlan(models.Model):
    _inherit = 'mail.activity.plan'

    def _compute_department_assignable(self):
        super()._compute_department_assignable()
        for plan in self:
            if not plan.department_assignable:
                plan.department_assignable = plan.res_model == 'hr.applicant'
