# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

{
    'name': 'Loomworks Appointment',
    'version': '18.0.1.0.0',
    'category': 'Services/Appointment',
    'summary': 'Online Appointment Booking System',
    'description': """
Loomworks Appointment - Online Booking System
==============================================

This module provides a complete online appointment booking solution.

Features:
---------
* Public booking portal for customers
* Appointment types with customizable duration and options
* Resource management (staff, rooms, equipment)
* Calendar integration with availability calculation
* Automatic scheduling conflict detection
* Email confirmations and reminders
* Recurring appointment support
* Customer self-service (book, reschedule, cancel)

Calendar Integration:
--------------------
* Syncs with employee calendars
* Respects working hours and time off
* Buffer time between appointments
* Maximum appointments per day/week limits

Customer Experience:
-------------------
* Mobile-friendly booking interface
* Real-time availability display
* Confirmation emails with calendar invites
* Easy rescheduling and cancellation
* Questions/intake forms

This is part of Loomworks ERP, a fork of Odoo Community v18 (LGPL v3).
    """,
    'author': 'Loomworks',
    'website': 'https://loomworks.app',
    'license': 'LGPL-3',
    'depends': [
        'calendar',
        'hr',
        'mail',
        'portal',
        'resource',
        'loomworks_core',
        'loomworks_ai',
    ],
    'data': [
        # Security
        'security/appointment_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/appointment_sequence_data.xml',
        'data/appointment_data.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        # Views
        'views/appointment_type_views.xml',
        'views/appointment_booking_views.xml',
        'views/appointment_resource_views.xml',
        'views/appointment_slot_views.xml',
        'views/appointment_menus.xml',
        # Portal
        'views/portal_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'loomworks_appointment/static/src/scss/appointment_backend.scss',
        ],
        'web.assets_frontend': [
            'loomworks_appointment/static/src/scss/appointment_portal.scss',
            'loomworks_appointment/static/src/js/appointment_portal.js',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 20,
}
