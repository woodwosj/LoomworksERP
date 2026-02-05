# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

{
    'name': 'Loomworks Sign',
    'version': '18.0.1.0.0',
    'category': 'Productivity/Sign',
    'summary': 'Electronic Signatures for Documents',
    'description': """
Loomworks Sign - Electronic Document Signing
=============================================

This module provides legally-compliant electronic signature capabilities.

Features:
---------
* Signature request workflows with multiple signers
* PDF document manipulation and signature embedding
* Reusable document templates with field placement
* Multiple signature types (drawn, typed, uploaded)
* Blockchain-style audit trail for legal compliance
* Email notifications and reminders
* Public portal for external signers

Legal Compliance:
----------------
* US: ESIGN Act and UETA compliant
* EU: eIDAS compatible (Simple Electronic Signatures)
* Captures intent, consent, and document association
* Tamper-evident audit logs with hash chains

Security:
---------
* Token-based access for signers
* IP and user-agent tracking
* Document hash verification
* Secure signature storage

This is part of Loomworks ERP, a fork of Odoo Community v18 (LGPL v3).
    """,
    'author': 'Loomworks',
    'website': 'https://loomworks.app',
    'license': 'LGPL-3',
    'depends': [
        'mail',
        'portal',
        'web',
        'loomworks_core',
        'loomworks_ai',
    ],
    'external_dependencies': {
        'python': ['PyMuPDF'],  # pip install PyMuPDF
    },
    'data': [
        # Security
        'security/sign_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/sign_sequence_data.xml',
        'data/sign_item_type_data.xml',
        'data/sign_role_data.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        # Views
        'views/sign_template_views.xml',
        'views/sign_request_views.xml',
        'views/sign_role_views.xml',
        'views/sign_menus.xml',
        # Portal
        'views/portal_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'loomworks_sign/static/src/scss/sign_backend.scss',
        ],
        'web.assets_frontend': [
            'loomworks_sign/static/src/scss/sign_portal.scss',
            'loomworks_sign/static/src/js/sign_portal.js',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 15,
}
