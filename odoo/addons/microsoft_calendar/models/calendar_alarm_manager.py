# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import api, models
from loomworks.tools import SQL


class AlarmManager(models.AbstractModel):
    _inherit = 'calendar.alarm_manager'

    @api.model
    def _get_notify_alert_extra_conditions(self):
        base = super()._get_notify_alert_extra_conditions()
        return SQL("%s AND event.microsoft_id IS NULL", base)
