# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_es_tbai_certificate_ids = fields.One2many(related='company_id.l10n_es_tbai_certificate_ids', readonly=False)
    l10n_es_tbai_tax_agency = fields.Selection(related='company_id.l10n_es_tbai_tax_agency', readonly=False)
    l10n_es_tbai_test_env = fields.Boolean(related='company_id.l10n_es_tbai_test_env', readonly=False)
