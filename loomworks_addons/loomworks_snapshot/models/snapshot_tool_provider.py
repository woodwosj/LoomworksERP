# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Snapshot Tool Provider - AI Tools for Snapshot Management

This module provides AI-accessible tools for snapshot operations,
following the M4 tool registration pattern from Phase 2.

Tools provided:
- snapshot_create: Create a manual snapshot
- snapshot_list: List available snapshots
- snapshot_restore: Restore to a snapshot point
- ai_operation_rollback: Rollback a specific AI operation

References:
- PATCH_NOTES_M1_M4.md: M4 AI Tool Registration Pattern
- design.md: Decision 2 - Snapshot Strategy
"""

from odoo import api, models
import logging

_logger = logging.getLogger(__name__)


class SnapshotToolProvider(models.AbstractModel):
    """
    Tool provider for snapshot management AI tools.

    Inherits from loomworks.ai.tool.provider (defined in Phase 2)
    to register snapshot-related AI tools.
    """
    _name = 'snapshot.tool.provider'
    _inherit = 'loomworks.ai.tool.provider'
    _description = 'Snapshot AI Tool Provider'

    @api.model
    def _get_tool_definitions(self):
        """
        Return snapshot tool definitions for AI registration.

        Returns:
            list: Tool definitions following the M4 pattern
        """
        return [
            {
                'name': 'Create Snapshot',
                'technical_name': 'snapshot_create',
                'category': 'system',
                'description': """Create a database snapshot for backup or rollback purposes.

A snapshot captures the current state of the database using PostgreSQL's
Write-Ahead Log (WAL) position. This allows point-in-time recovery to
restore the database to exactly this moment.

Use cases:
- Before making significant changes
- Before bulk operations
- Manual backup points
- Pre-deployment checkpoints

The snapshot is created instantly (sub-second) as it only records the
WAL position, not a full database copy.""",
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'name': {
                            'type': 'string',
                            'description': 'Descriptive name for the snapshot',
                        },
                        'description': {
                            'type': 'string',
                            'description': 'Optional detailed description',
                        },
                        'snapshot_type': {
                            'type': 'string',
                            'enum': ['manual', 'pre_ai', 'pre_upgrade'],
                            'description': 'Type of snapshot (default: manual)',
                            'default': 'manual',
                        },
                    },
                    'required': ['name'],
                },
                'implementation_method': 'loomworks_snapshot.services.snapshot_service.create_snapshot',
                'risk_level': 'safe',
                'requires_confirmation': False,
                'returns_description': 'Snapshot record with ID, name, WAL position, and creation timestamp',
                'sequence': 10,
            },
            {
                'name': 'List Snapshots',
                'technical_name': 'snapshot_list',
                'category': 'data',
                'description': """List available database snapshots.

Returns snapshots that can be used for restore operations. By default,
shows only 'ready' snapshots (those that completed successfully).

Use this to:
- Find a snapshot to restore to
- Review backup history
- Check snapshot retention status
- Verify pre-operation snapshots exist""",
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'state': {
                            'type': 'string',
                            'enum': ['creating', 'ready', 'restoring', 'restored', 'failed', 'expired', 'all'],
                            'description': 'Filter by snapshot state (default: ready)',
                            'default': 'ready',
                        },
                        'snapshot_type': {
                            'type': 'string',
                            'enum': ['auto', 'manual', 'pre_ai', 'pre_upgrade', 'all'],
                            'description': 'Filter by snapshot type (default: all)',
                            'default': 'all',
                        },
                        'limit': {
                            'type': 'integer',
                            'description': 'Maximum number of snapshots to return (default: 20)',
                            'default': 20,
                            'minimum': 1,
                            'maximum': 100,
                        },
                    },
                    'required': [],
                },
                'implementation_method': 'loomworks_snapshot.services.snapshot_service.list_snapshots',
                'risk_level': 'safe',
                'requires_confirmation': False,
                'returns_description': 'List of snapshot records with ID, name, type, state, WAL position, and timestamps',
                'sequence': 20,
            },
            {
                'name': 'Restore Snapshot',
                'technical_name': 'snapshot_restore',
                'category': 'system',
                'description': """Restore the database to a previous snapshot point.

WARNING: This is a DESTRUCTIVE operation that will:
1. Stop all active sessions
2. Restore the database to the snapshot point
3. All changes made AFTER the snapshot will be LOST
4. Restart the application

This uses PostgreSQL Point-in-Time Recovery (PITR) to replay the
Write-Ahead Log to the exact moment the snapshot was created.

Use cases:
- Undo bulk changes that went wrong
- Recover from data corruption
- Rollback failed deployments
- Disaster recovery

For rolling back individual AI operations, consider using
ai_operation_rollback instead, which is faster and less disruptive.""",
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'snapshot_id': {
                            'type': 'integer',
                            'description': 'ID of the snapshot to restore to',
                        },
                        'snapshot_name': {
                            'type': 'string',
                            'description': 'Name of the snapshot to restore to (alternative to ID)',
                        },
                        'confirm': {
                            'type': 'boolean',
                            'description': 'Explicit confirmation required (must be true)',
                            'default': False,
                        },
                    },
                    'required': ['confirm'],
                    'oneOf': [
                        {'required': ['snapshot_id']},
                        {'required': ['snapshot_name']},
                    ],
                },
                'implementation_method': 'loomworks_snapshot.services.snapshot_service.restore_snapshot',
                'risk_level': 'critical',
                'requires_confirmation': True,
                'returns_description': 'Restore operation status and details',
                'sequence': 30,
            },
            {
                'name': 'Rollback AI Operation',
                'technical_name': 'ai_operation_rollback',
                'category': 'system',
                'description': """Rollback a specific AI operation by undoing its changes.

This provides granular rollback for individual AI operations without
requiring a full database restore. It uses the captured before/after
values to reverse the operation:

- CREATE operations: Deletes the created records
- UPDATE operations: Restores previous field values
- DELETE operations: Recreates the deleted records

This is faster and less disruptive than full snapshot restore:
- Instant execution (no database restore needed)
- Other concurrent operations are not affected
- No application restart required

Use snapshot_restore for:
- Multiple operations that need to be rolled back together
- Operations where before values weren't captured
- Disaster recovery scenarios""",
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'operation_id': {
                            'type': 'integer',
                            'description': 'ID of the AI operation log to rollback',
                        },
                        'confirm': {
                            'type': 'boolean',
                            'description': 'Explicit confirmation required (must be true)',
                            'default': False,
                        },
                    },
                    'required': ['operation_id', 'confirm'],
                },
                'implementation_method': 'loomworks_snapshot.services.snapshot_service.rollback_ai_operation',
                'risk_level': 'high',
                'requires_confirmation': True,
                'returns_description': 'Rollback status and details of reversed changes',
                'sequence': 40,
            },
            {
                'name': 'Get Snapshot Status',
                'technical_name': 'snapshot_status',
                'category': 'data',
                'description': """Get detailed status of a specific snapshot.

Returns comprehensive information about a snapshot including:
- Current state (creating, ready, restoring, etc.)
- WAL position and recovery target time
- Database size at snapshot time
- Related AI operations
- Expiration date

Useful for:
- Verifying snapshot is ready before restore
- Checking if a snapshot has expired
- Reviewing what operations are covered by a snapshot""",
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'snapshot_id': {
                            'type': 'integer',
                            'description': 'ID of the snapshot to check',
                        },
                    },
                    'required': ['snapshot_id'],
                },
                'implementation_method': 'loomworks_snapshot.services.snapshot_service.get_snapshot_status',
                'risk_level': 'safe',
                'requires_confirmation': False,
                'returns_description': 'Detailed snapshot status including state, timestamps, and metadata',
                'sequence': 50,
            },
            {
                'name': 'List Rollback Options',
                'technical_name': 'list_rollback_options',
                'category': 'data',
                'description': """List recent AI operations that can be rolled back.

Returns a list of recent AI operations with rollback capability,
helping users identify what can be undone. Each entry includes:
- Operation details (tool, type, model, records affected)
- When it was executed
- Whether it can be rolled back
- Associated snapshot (if any)

Use this to find operations to undo before calling ai_operation_rollback.""",
                'parameters_schema': {
                    'type': 'object',
                    'properties': {
                        'limit': {
                            'type': 'integer',
                            'description': 'Maximum number of operations to return (default: 10)',
                            'default': 10,
                            'minimum': 1,
                            'maximum': 50,
                        },
                        'session_id': {
                            'type': 'integer',
                            'description': 'Filter by specific AI session (optional)',
                        },
                        'only_rollbackable': {
                            'type': 'boolean',
                            'description': 'Only show operations that can be rolled back (default: true)',
                            'default': True,
                        },
                    },
                    'required': [],
                },
                'implementation_method': 'loomworks_snapshot.services.snapshot_service.list_rollback_options',
                'risk_level': 'safe',
                'requires_confirmation': False,
                'returns_description': 'List of AI operations with rollback status and details',
                'sequence': 60,
            },
        ]
