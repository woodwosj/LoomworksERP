# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.
from loomworks import fields, models


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    employee_id = fields.Many2one('hr.employee', string="Employee", help="The employee who made the cash move.")
