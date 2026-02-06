# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

{
    'name': 'Upwork Integration',
    'version': '18.0.1.0.0',
    'category': 'Project',
    'summary': 'Integrate Upwork contracts, time logs, earnings and proposals with Odoo',
    'description': """
Upwork Integration for Loomworks ERP
=====================================

This module provides full integration between Upwork and Odoo, including:

Features:
---------
* OAuth2 authentication with Upwork API
* Automatic sync of contracts, time logs, and earnings
* Invoice generation from Upwork earnings
* Timesheet creation from Upwork time logs
* Proposal management with rich HTML templates
* AI tool provider for Upwork operations
* Configurable financial account mapping

This is part of Loomworks ERP, a fork of Odoo Community v18 (LGPL v3).
    """,
    'author': 'Loomworks',
    'website': 'https://loomworks.app',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'project',
        'hr_timesheet',
        'account',
        'loomworks_core',
        'loomworks_ai',
    ],
    'external_dependencies': {
        'python': ['requests'],
    },
    'data': [
        # Security
        'security/upwork_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/ir_cron_data.xml',
        # Views
        'views/upwork_account_views.xml',
        'views/upwork_contract_views.xml',
        'views/upwork_timelog_views.xml',
        'views/upwork_earning_views.xml',
        'views/upwork_proposal_views.xml',
        'views/upwork_menus.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 20,
}
