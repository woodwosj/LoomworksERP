# -*- coding: utf-8 -*-
# Part of Loomworks ERP (based on Odoo by Odoo S.A.). See LICENSE file for full copyright and licensing details.

{
    'name': 'LoomBot',
    'version': '1.2',
    'category': 'Productivity/Discuss',
    'summary': 'Add LoomBot in discussions',
    'website': 'https://loomworks.solutions/app/discuss',
    'depends': ['mail'],
    'auto_install': True,
    'installable': True,
    'data': [
        'views/res_users_views.xml',
        'data/mailbot_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'mail_bot/static/src/scss/odoobot_style.scss',
        ],
    },
    'license': 'LGPL-3',
}
