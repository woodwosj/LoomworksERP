# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

{
    'name': 'DIN 5008 - Purchase',
    'category': 'Accounting/Localizations',
    'depends': [
        'l10n_din5008',
        'purchase',
    ],
    'data': [
        'report/din5008_purchase_order_templates.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
