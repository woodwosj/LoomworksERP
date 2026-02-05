# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

{
    'name': 'Loomworks Spreadsheet',
    'version': '18.0.1.0.0',
    'category': 'Productivity/Documents',
    'summary': 'Excel-like Spreadsheets with Odoo Data Integration',
    'description': """
Loomworks Spreadsheet - BI and Data Analysis
=============================================

A powerful spreadsheet system built on the Univer library (Apache-2.0),
providing Excel-like functionality with deep Odoo integration.

Features:
---------
* Excel-like interface using Univer
* Pivot tables with Odoo data
* Charts (bar, line, pie, scatter, etc.)
* Data connections to any Odoo model
* Custom formulas for Odoo data (ODOO.DATA, ODOO.PIVOT, etc.)
* Collaborative editing (real-time sync)
* Export to Excel/PDF
* Import from Excel

Univer Integration:
------------------
Uses the Univer spreadsheet library (Apache-2.0 license) which provides:
* Full formula support (100+ Excel functions)
* Cell formatting and styling
* Conditional formatting
* Data validation
* Charts and visualizations

React Integration (M1 Resolution):
---------------------------------
Per the architecture specification, React 18 is loaded in this module
as a dependency of Univer. The React libraries are available globally
for use by Phase 4 Dashboard components.

AI Integration (M4 Pattern):
---------------------------
* spreadsheet_create - Create new spreadsheets
* spreadsheet_insert_data - Add Odoo data to spreadsheet
* spreadsheet_create_pivot - Build pivot tables
* spreadsheet_create_chart - Generate visualizations

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
        'data/spreadsheet_data.xml',
        # Views (data_source, pivot, chart before document - document form refs their actions)
        'views/spreadsheet_data_source_views.xml',
        'views/spreadsheet_pivot_views.xml',
        'views/spreadsheet_chart_views.xml',
        'views/spreadsheet_document_views.xml',
        'views/spreadsheet_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # React and dependencies (M1 Resolution - loaded for Univer)
            ('prepend', 'loomworks_spreadsheet/static/lib/react/react.production.min.js'),
            ('prepend', 'loomworks_spreadsheet/static/lib/react/react-dom.production.min.js'),
            ('prepend', 'loomworks_spreadsheet/static/lib/rxjs/rxjs.umd.min.js'),
            # Univer libraries
            'loomworks_spreadsheet/static/lib/univer/presets.js',
            'loomworks_spreadsheet/static/lib/univer/preset-sheets-core.js',
            'loomworks_spreadsheet/static/lib/univer/preset-sheets-core.css',
            # Stylesheets
            'loomworks_spreadsheet/static/src/scss/spreadsheet.scss',
            # Services
            'loomworks_spreadsheet/static/src/services/spreadsheet_service.js',
            # Univer integration
            'loomworks_spreadsheet/static/src/univer/univer_wrapper.js',
            'loomworks_spreadsheet/static/src/univer/odoo_data_plugin.js',
            'loomworks_spreadsheet/static/src/univer/pivot_plugin.js',
            'loomworks_spreadsheet/static/src/univer/chart_plugin.js',
            # Components
            'loomworks_spreadsheet/static/src/components/spreadsheet_view/spreadsheet_view.js',
            'loomworks_spreadsheet/static/src/components/spreadsheet_view/spreadsheet_view.xml',
            'loomworks_spreadsheet/static/src/components/data_source_dialog/data_source_dialog.js',
            'loomworks_spreadsheet/static/src/components/data_source_dialog/data_source_dialog.xml',
            # XML Templates
            'loomworks_spreadsheet/static/src/xml/spreadsheet_templates.xml',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 11,
}
