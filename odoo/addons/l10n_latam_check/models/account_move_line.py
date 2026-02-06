# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.
from loomworks import fields, models


class AccountMoveLine(models.Model):

    _inherit = 'account.move.line'

    l10n_latam_check_ids = fields.One2many('l10n_latam.check', 'outstanding_line_id', string='Checks')
