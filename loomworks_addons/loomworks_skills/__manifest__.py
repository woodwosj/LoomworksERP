# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

{
    'name': 'Loomworks Skills',
    'version': '18.0.1.0.0',
    'category': 'Productivity/AI',
    'summary': 'AI Workflow Automation and Reusable Skills Framework',
    'description': """
Loomworks Skills Framework
==========================

This module provides AI workflow automation through reusable skill definitions
that enable natural language commands and recordable user actions.

Features:
---------
* **Skill Definitions**: Define reusable workflows with steps, triggers, and parameters
* **Natural Language Triggers**: Match user intent to skills via trigger phrases
* **Session Recording**: Record user actions and convert to reusable skills
* **Skill Execution Engine**: Multi-step workflow execution with state management
* **Rollback Support**: Transaction-based rollback with optional PITR via Phase 5
* **Built-in Skills**: Pre-installed skills for common ERP operations

Skill Workflow Steps:
--------------------
* tool_call: Invoke MCP tools
* user_input: Request user input
* condition: Conditional branching
* loop: Iteration over collections
* validation: Data validation
* confirmation: User confirmation
* subskill: Execute nested skills
* action: Execute Odoo actions

Built-in Skills:
---------------
* Create Sales Quote
* Check Inventory
* Generate Invoice
* Approve Purchase
* Create Contact
* Schedule Meeting

Phase Dependencies:
------------------
* **Phase 2 (loomworks_ai)**: REQUIRED - MCP tools, sessions, operation logging
* **Phase 5 (loomworks_snapshot)**: OPTIONAL - Full PITR rollback (graceful degradation)

Graceful Degradation (M3 Resolution):
------------------------------------
When loomworks_snapshot is not installed:
* Falls back to PostgreSQL SAVEPOINT for transaction-scoped rollback
* Rollback limited to current transaction only
* No post-commit undo capability
* User notification of degraded mode

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
        'loomworks_ai',  # Phase 2: REQUIRED dependency
    ],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/skill_data.xml',
        # Views
        'views/skill_views.xml',
        'views/skill_step_views.xml',
        'views/skill_execution_views.xml',
        'views/skill_recording_views.xml',
        'views/skill_menus.xml',
        # Wizards
        'wizard/skill_creation_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # Stylesheets
            'loomworks_skills/static/src/scss/skills.scss',
            # Services
            'loomworks_skills/static/src/services/skill_recorder_service.js',
            'loomworks_skills/static/src/services/skill_intent_service.js',
            # Components
            'loomworks_skills/static/src/components/skill_panel/skill_panel.js',
            'loomworks_skills/static/src/components/skill_panel/skill_panel.xml',
            'loomworks_skills/static/src/components/skill_execution_progress/skill_execution_progress.js',
            'loomworks_skills/static/src/components/skill_execution_progress/skill_execution_progress.xml',
            'loomworks_skills/static/src/components/skill_recording_indicator/skill_recording_indicator.js',
            'loomworks_skills/static/src/components/skill_recording_indicator/skill_recording_indicator.xml',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 20,
}
