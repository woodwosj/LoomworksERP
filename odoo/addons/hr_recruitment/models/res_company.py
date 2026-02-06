# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    candidate_properties_definition = fields.PropertiesDefinition('Candidate Properties')
    job_properties_definition = fields.PropertiesDefinition("Job Properties")
