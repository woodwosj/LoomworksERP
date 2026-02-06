# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import fields, models


class HolidaysType(models.Model):
    _inherit = "hr.leave.type"

    l10n_in_is_sandwich_leave = fields.Boolean(
        help="""If a leave is covering holidays, the holiday period will be included in the requested time.
        The time took in addition will have the same treatment (allocation, pay, reports) as the initial request.
        Holidays includes public holidays, national days, paid holidays and week-ends.""")
