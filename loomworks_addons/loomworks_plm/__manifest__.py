# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

{
    'name': 'Loomworks PLM',
    'version': '18.0.1.0.0',
    'category': 'Manufacturing/PLM',
    'summary': 'Product Lifecycle Management with Engineering Change Orders',
    'description': """
Loomworks PLM - Product Lifecycle Management
=============================================

This module provides enterprise-grade PLM capabilities for Loomworks ERP.

Features:
---------
* Engineering Change Orders (ECOs) with multi-stage approval workflows
* BOM versioning with revision history and comparison tools
* Change Control Board (CCB) support with role-based approvals
* Impact analysis for production and inventory
* Complete audit trail for regulatory compliance
* Document management for engineering specifications

Key Capabilities:
----------------
* Formal change request workflows
* BOM snapshot and rollback capability
* Cross-functional approval routing
* Form, Fit, Function (FFF) evaluation support
* Integration with manufacturing (MRP) module

This is part of Loomworks ERP, a fork of Odoo Community v18 (LGPL v3).
    """,
    'author': 'Loomworks',
    'website': 'https://loomworks.app',
    'license': 'LGPL-3',
    'depends': [
        'mrp',
        'mail',
        'product',
        'loomworks_core',
        'loomworks_ai',
    ],
    'data': [
        # Security
        'security/plm_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/plm_sequence_data.xml',
        'data/plm_stage_data.xml',
        'data/plm_type_data.xml',
        'data/mail_template_data.xml',
        # Views
        'views/plm_eco_views.xml',
        'views/plm_eco_type_views.xml',
        'views/plm_eco_stage_views.xml',
        'views/plm_bom_revision_views.xml',
        'views/mrp_bom_views.xml',
        'views/plm_menus.xml',
    ],
    'demo': [
        'data/plm_demo_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'loomworks_plm/static/src/scss/plm_kanban.scss',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 10,
}
