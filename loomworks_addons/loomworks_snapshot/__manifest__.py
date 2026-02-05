# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

{
    'name': 'Loomworks Snapshot',
    'version': '18.0.1.0.0',
    'category': 'Technical/Database',
    'summary': 'Database Snapshots and Point-in-Time Recovery for AI Rollback',
    'description': """
Loomworks Snapshot - Database Snapshots and PITR
=================================================

This module provides database snapshot capabilities with PostgreSQL Point-in-Time
Recovery (PITR) for AI operation rollback and disaster recovery.

Features:
---------
* PostgreSQL WAL-based Point-in-Time Recovery
* Pre-AI operation snapshots for guaranteed rollback
* Scheduled automatic snapshots
* Retention policies with configurable cleanup
* Multi-tenant database management
* Integration with AI operation logs for granular undo

Snapshot Types:
--------------
* auto: Scheduled automatic snapshots
* manual: User-triggered snapshots
* pre_ai: Created before AI makes changes
* pre_upgrade: Created before module upgrades

AI Integration:
--------------
Extends loomworks.ai.operation.log (Phase 2) to add:
* snapshot_id: Links operation to pre-operation snapshot
* can_rollback: Computed field indicating rollback capability
* rollback_operation(): Method to undo via PITR or savepoint

Graceful Degradation (M3 Resolution):
------------------------------------
When Phase 5 snapshot service is unavailable:
* Falls back to PostgreSQL SAVEPOINT for transaction-scoped rollback
* Provides user notification of degraded mode
* Full PITR available when snapshot module is properly configured

Dependencies:
------------
* loomworks_ai (REQUIRED): Extends AI operation log model
* loomworks_core (REQUIRED): Base branding and configuration

This is part of Loomworks ERP, a fork of Odoo Community v18 (LGPL v3).
    """,
    'author': 'Loomworks',
    'website': 'https://loomworks.app',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'loomworks_core',
        'loomworks_ai',
    ],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/snapshot_data.xml',
        'data/snapshot_cron.xml',
        # Views
        'views/snapshot_views.xml',
        'views/snapshot_schedule_views.xml',
        'views/snapshot_retention_views.xml',
        'views/tenant_views.xml',
        'views/ai_operation_log_views.xml',
        'views/snapshot_menus.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 15,
    'post_init_hook': 'post_init_hook',
}
