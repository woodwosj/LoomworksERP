# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

from loomworks import fields, models


class company(models.Model):
    _inherit = 'res.company'

    security_lead = fields.Float(
        'Sales Safety Days', default=0.0, required=True,
        help="Margin of error for dates promised to customers. "
             "Products will be scheduled for procurement and delivery "
             "that many days earlier than the actual promised date, to "
             "cope with unexpected delays in the supply chain.")
