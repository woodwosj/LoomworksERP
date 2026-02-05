# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

{
    'name': 'Loomworks Core',
    'version': '18.0.1.0.0',
    'category': 'Hidden/Tools',
    'summary': 'Loomworks ERP Branding and Core Configuration',
    'description': """
Loomworks ERP Core Module
=========================

This module provides:
- Loomworks branding (logos, colors, favicon)
- Custom color palette for backend and frontend
- Default company configuration
- Base dependencies for all Loomworks modules

This is a fork of Odoo Community v18 (LGPL v3).
Original software: https://github.com/odoo/odoo
    """,
    'author': 'Loomworks',
    'website': 'https://loomworks.app',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/webclient_templates.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            ('prepend', 'loomworks_core/static/src/scss/primary_variables.scss'),
        ],
        'web.assets_backend': [
            'loomworks_core/static/src/scss/loomworks_backend.scss',
            'loomworks_core/static/src/xml/webclient_templates.xml',
        ],
        'web.assets_frontend': [
            'loomworks_core/static/src/scss/loomworks_backend.scss',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': False,
    'sequence': 1,
}
