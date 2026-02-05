# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

{
    'name': 'Loomworks Studio',
    'version': '18.0.1.0.0',
    'category': 'Customization/No-Code',
    'summary': 'No-Code Application Builder for Loomworks ERP',
    'description': """
Loomworks Studio - No-Code Application Builder
===============================================

A powerful no-code application builder that allows business users to create
and customize applications without writing code.

Features:
---------
* Visual drag-drop field editor
* View designer (form, list, kanban, calendar)
* Menu builder
* Custom model creation
* Automation/workflow builder
* Export/import app definitions

This is an LGPL alternative to Odoo Enterprise web_studio, built from
scratch for the Loomworks ERP fork.

AI Integration (M4 Pattern):
---------------------------
* studio_create_app - Create new custom applications
* studio_add_field - Add fields to models
* studio_customize_view - Modify view layouts
* studio_create_automation - Define workflow rules

Security:
---------
* Group-based access control
* Audit logging of all customizations
* Sandbox mode for testing changes

This is part of Loomworks ERP, a fork of Odoo Community v18 (LGPL v3).
    """,
    'author': 'Loomworks',
    'website': 'https://loomworks.app',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'mail',
        'loomworks_core',
        'loomworks_ai',
    ],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/studio_data.xml',
        # Views
        'views/studio_app_views.xml',
        'views/studio_view_customization_views.xml',
        'views/studio_automation_views.xml',
        'views/ir_model_views.xml',
        'views/studio_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # Stylesheets
            'loomworks_studio/static/src/scss/studio.scss',
            # Services
            'loomworks_studio/static/src/services/studio_service.js',
            # Components
            'loomworks_studio/static/src/components/field_palette/field_palette.js',
            'loomworks_studio/static/src/components/field_palette/field_palette.xml',
            'loomworks_studio/static/src/components/view_designer/view_designer.js',
            'loomworks_studio/static/src/components/view_designer/view_designer.xml',
            'loomworks_studio/static/src/components/automation_builder/automation_builder.js',
            'loomworks_studio/static/src/components/automation_builder/automation_builder.xml',
            # XML Templates
            'loomworks_studio/static/src/xml/studio_templates.xml',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 10,
}
