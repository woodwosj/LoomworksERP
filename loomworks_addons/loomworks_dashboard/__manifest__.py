# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

{
    'name': 'Loomworks Dashboard',
    'version': '18.0.1.0.0',
    'category': 'Productivity/BI',
    'summary': 'Drag-Drop Dashboard Builder with AI Generation',
    'description': """
Loomworks Dashboard - Business Intelligence Platform
=====================================================

A powerful dashboard system providing visual, interactive dashboards to monitor
KPIs, trends, and operational metrics without writing code or SQL.

Features:
---------
* Drag-drop widget placement using Gridstack.js
* Real-time data connections to any Odoo model
* Multiple widget types: KPI cards, charts, tables, filters
* Tabbed dashboard organization
* Dashboard templates (Sales, Inventory, HR, CRM)
* Export/share capabilities
* AI-generated dashboards from natural language

Widget Types:
-------------
* KPI - Single metric with trend indicator and sparkline
* Chart - Line, bar, area, and pie charts via Recharts
* Table - Paginated data tables with sorting
* Filter - Global filters affecting connected widgets
* Gauge - Progress toward targets

React Integration (M1 Pattern):
-------------------------------
This module reuses React 18 loaded by loomworks_spreadsheet (Phase 3.1).
The React bridge pattern enables Owl-React interop for the dashboard canvas.

AI Integration (M4 Pattern):
---------------------------
Implements AIToolProvider mixin with tools:
* dashboard_create - Create new dashboards
* dashboard_add_widget - Add widgets to canvas
* dashboard_add_kpi - Add KPI cards
* dashboard_add_chart - Generate visualizations
* dashboard_get_data - Fetch widget data

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
        'loomworks_spreadsheet',  # Provides React 18 (M1 Resolution)
    ],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/dashboard_templates.xml',
        # Views
        'views/dashboard_views.xml',
        'views/dashboard_widget_views.xml',
        'views/dashboard_data_source_views.xml',
        'views/dashboard_menus.xml',
        'views/dashboard_public_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # Gridstack library
            'loomworks_dashboard/static/src/lib/gridstack/gridstack-all.min.js',
            'loomworks_dashboard/static/src/lib/gridstack/gridstack.min.css',
            # Recharts library (bundled)
            'loomworks_dashboard/static/src/lib/recharts/recharts.min.js',
            # Stylesheets
            'loomworks_dashboard/static/src/scss/dashboard.scss',
            # Services
            'loomworks_dashboard/static/src/services/dashboard_service.js',
            # Owl Components
            'loomworks_dashboard/static/src/components/dashboard_action/dashboard_action.js',
            'loomworks_dashboard/static/src/components/dashboard_action/dashboard_action.xml',
            # React Components (compiled bundle)
            'loomworks_dashboard/static/src/react/dashboard_bundle.js',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 12,
}
