# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

{
    'name': 'Loomworks Field Service',
    'version': '18.0.1.0.0',
    'category': 'Services/Field Service',
    'summary': 'Mobile-first field service management',
    'description': """
Loomworks Field Service Management
==================================

A comprehensive field service management solution for dispatching technicians,
tracking work completion, and managing on-site operations with mobile support.

Features:
---------
* Mobile-optimized task management
* GPS location tracking and map integration
* Work timer with automatic timesheet integration
* Digital worksheets with customizable templates
* Customer signature capture
* Materials/parts consumption tracking
* PWA offline capability (sync when connected)
* Route optimization suggestions

Mobile Experience:
-----------------
* Touch-optimized kanban views
* One-tap timer start/stop
* Photo capture and attachment
* Signature pad for customer sign-off
* Offline task viewing and updates

PWA Support (M2 Resolution):
---------------------------
* FSM-specific route filtering
* Offline data caching
* Background sync for pending operations
* Works in areas with poor connectivity

AI Integration:
---------------
* fsm_dispatch_technician: Assign tasks to field workers
* fsm_complete_order: Mark tasks as completed with signature

This is part of Loomworks ERP, a fork of Odoo Community v18 (LGPL v3).
    """,
    'author': 'Loomworks',
    'website': 'https://loomworks.app',
    'license': 'LGPL-3',
    'depends': [
        'project',
        'hr_timesheet',
        'base_geolocalize',
        'stock',
        'mail',
        'loomworks_core',
        'loomworks_ai',
    ],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/fsm_data.xml',
        # Views
        'views/project_task_views.xml',
        'views/fsm_worksheet_views.xml',
        'views/fsm_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'loomworks_fsm/static/src/scss/fsm.scss',
            'loomworks_fsm/static/src/js/fsm_timer_widget.js',
            'loomworks_fsm/static/src/xml/fsm_timer_widget.xml',
            'loomworks_fsm/static/src/components/signature_pad/signature_pad.js',
            'loomworks_fsm/static/src/components/signature_pad/signature_pad.xml',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 22,
}
