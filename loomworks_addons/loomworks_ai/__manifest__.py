# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

{
    'name': 'Loomworks AI',
    'version': '18.0.1.0.0',
    'category': 'Productivity/AI',
    'summary': 'AI-Powered ERP Assistant with Claude Integration',
    'description': """
Loomworks AI Integration
========================

This module provides AI-first interaction with Loomworks ERP through Claude AI agents.

Features:
---------
* Natural language interface for all ERP operations
* Claude AI agent configuration and management
* MCP (Model Context Protocol) server for Odoo tool access
* Chat session tracking with message history
* Operation audit logging with undo/rollback capability
* Security sandbox with forbidden models and field filtering
* Streaming responses via Server-Sent Events (SSE)
* Owl-based chat component for web interface

MCP Tools Available:
-------------------
* search_records - Query any allowed Odoo model
* create_record - Create new records with logging
* update_record - Modify records with before/after capture
* delete_record - Delete records with confirmation
* execute_action - Run server actions and workflows
* generate_report - Analytics and aggregations

Security:
---------
* Inherits user's Odoo permissions
* Hardcoded blocklist for sensitive models (res.users, ir.rule, etc.)
* Forbidden fields stripped (password, api_key, etc.)
* Savepoint-based transaction rollback
* Operation limits per conversation turn

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
    ],
    'external_dependencies': {
        'python': ['anthropic'],
    },
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/ai_tool_data.xml',
        # Views
        'views/ai_agent_views.xml',
        'views/ai_session_views.xml',
        'views/ai_tool_views.xml',
        'views/ai_operation_log_views.xml',
        'views/ai_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'loomworks_ai/static/src/scss/ai_chat.scss',
            'loomworks_ai/static/src/components/ai_message/ai_message.js',
            'loomworks_ai/static/src/components/ai_message/ai_message.xml',
            'loomworks_ai/static/src/components/ai_chat/ai_chat.js',
            'loomworks_ai/static/src/components/ai_chat/ai_chat.xml',
            'loomworks_ai/static/src/xml/ai_systray.xml',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
    'sequence': 5,
}
