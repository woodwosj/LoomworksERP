# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

{
    'name': 'Loomworks Planning',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Planning',
    'summary': 'Visual workforce scheduling with Gantt views',
    'description': """
Loomworks Planning - Workforce Scheduling
=========================================

A visual workforce scheduling module with Gantt view capabilities for shift
planning, resource allocation, and conflict detection.

Features:
---------
* Interactive Gantt view with drag-and-drop editing
* Shift scheduling with role-based assignments
* Conflict detection for overlapping schedules
* Employee availability tracking
* Integration with HR time off
* Recurring shift patterns (daily, weekly, monthly)
* Shift templates for quick assignment
* Publication workflow for schedule visibility
* Project and task linking

Planning Workflow:
------------------
1. Create shift templates with standard times and roles
2. Use quick assignment wizard to generate shifts
3. Review and resolve any conflicts
4. Publish schedules for employee visibility
5. Employees view their upcoming shifts

Gantt View:
-----------
* Visual timeline of all scheduled shifts
* Grouped by employee, role, or project
* Drag-and-drop for easy rescheduling
* Color-coded by role or conflict status
* Zoom levels: day, week, month

AI Integration:
---------------
* planning_create_shift: Create new planning slots
* planning_get_availability: Check employee availability
* planning_detect_conflicts: Find scheduling conflicts

This is part of Loomworks ERP, a fork of Odoo Community v18 (LGPL v3).
    """,
    'author': 'Loomworks',
    'website': 'https://loomworks.app',
    'license': 'LGPL-3',
    'depends': [
        'hr',
        'hr_skills',
        'resource',
        'project',
        'hr_holidays',
        'mail',
        'loomworks_core',
        'loomworks_ai',
    ],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/planning_data.xml',
        # Views
        'views/planning_slot_views.xml',
        'views/planning_role_views.xml',
        'views/planning_template_views.xml',
        'views/hr_employee_views.xml',
        'views/planning_menus.xml',
        # Wizard
        'wizard/planning_slot_quick_create_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'loomworks_planning/static/src/scss/planning.scss',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 23,
}
