# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Snapshot Service - Business Logic for Snapshot Operations

This service provides the implementation methods for snapshot AI tools
and centralizes snapshot-related business logic.

The methods here are called by:
1. AI tools (via tool provider registration)
2. Controllers (REST API endpoints)
3. Scheduled actions (automated cleanup)

References:
- PostgreSQL PITR: https://www.postgresql.org/docs/current/continuous-archiving.html
- design.md: Decision 2 - Snapshot Strategy
"""

from odoo import api, models, fields
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class SnapshotService(models.AbstractModel):
    """
    Service class for snapshot operations.

    Provides business logic for creating, listing, and restoring snapshots,
    as well as AI operation rollback functionality.
    """
    _name = 'loomworks.snapshot.service'
    _description = 'Snapshot Service'

    @api.model
    def create_snapshot(self, name, description=None, snapshot_type='manual', tenant_id=None):
        """
        Create a database snapshot.

        Args:
            name: Descriptive name for the snapshot
            description: Optional detailed description
            snapshot_type: Type of snapshot ('manual', 'pre_ai', 'pre_upgrade')
            tenant_id: Optional tenant ID for multi-tenant deployments

        Returns:
            dict: Snapshot details including ID, name, WAL position
        """
        Snapshot = self.env['loomworks.snapshot']

        # Validate snapshot_type
        valid_types = ['manual', 'pre_ai', 'pre_upgrade', 'auto']
        if snapshot_type not in valid_types:
            raise ValidationError(f"Invalid snapshot_type: {snapshot_type}")

        try:
            # Create snapshot record
            snapshot = Snapshot.create({
                'name': name,
                'description': description or '',
                'snapshot_type': snapshot_type,
                'tenant_id': tenant_id,
            })

            # Execute snapshot creation (captures WAL position)
            snapshot.action_create_snapshot()

            _logger.info(
                "Created snapshot '%s' (ID: %d) at WAL position %s",
                name, snapshot.id, snapshot.wal_position
            )

            return {
                'success': True,
                'snapshot': {
                    'id': snapshot.id,
                    'name': snapshot.name,
                    'type': snapshot.snapshot_type,
                    'state': snapshot.state,
                    'wal_position': snapshot.wal_position,
                    'created_at': snapshot.created_at.isoformat() if snapshot.created_at else None,
                    'database_name': snapshot.database_name,
                },
                'message': f"Snapshot '{name}' created successfully",
            }

        except Exception as e:
            _logger.exception("Failed to create snapshot '%s': %s", name, e)
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to create snapshot: {e}",
            }

    @api.model
    def list_snapshots(self, state='ready', snapshot_type='all', limit=20, tenant_id=None):
        """
        List available snapshots.

        Args:
            state: Filter by state ('ready', 'all', or specific state)
            snapshot_type: Filter by type ('auto', 'manual', 'pre_ai', 'all')
            limit: Maximum number of results
            tenant_id: Optional tenant ID filter

        Returns:
            dict: List of snapshot summaries
        """
        Snapshot = self.env['loomworks.snapshot']

        # Build domain
        domain = []

        if state and state != 'all':
            domain.append(('state', '=', state))

        if snapshot_type and snapshot_type != 'all':
            domain.append(('snapshot_type', '=', snapshot_type))

        if tenant_id:
            domain.append(('tenant_id', '=', tenant_id))

        # Search snapshots
        snapshots = Snapshot.search(
            domain,
            order='create_date desc',
            limit=min(limit, 100)
        )

        result = []
        for snapshot in snapshots:
            result.append({
                'id': snapshot.id,
                'name': snapshot.name,
                'display_name': snapshot.display_name,
                'type': snapshot.snapshot_type,
                'state': snapshot.state,
                'wal_position': snapshot.wal_position,
                'created_at': snapshot.created_at.isoformat() if snapshot.created_at else None,
                'expires_at': snapshot.expires_at.isoformat() if snapshot.expires_at else None,
                'database_name': snapshot.database_name,
                'operation_count': snapshot.operation_count,
            })

        return {
            'success': True,
            'count': len(result),
            'snapshots': result,
        }

    @api.model
    def restore_snapshot(self, snapshot_id=None, snapshot_name=None, confirm=False):
        """
        Restore database to a snapshot point.

        Args:
            snapshot_id: ID of snapshot to restore
            snapshot_name: Name of snapshot to restore (alternative to ID)
            confirm: Must be True to proceed with restore

        Returns:
            dict: Restore operation result
        """
        if not confirm:
            return {
                'success': False,
                'error': 'Confirmation required',
                'message': "Restore requires explicit confirmation. Set confirm=true to proceed.",
            }

        Snapshot = self.env['loomworks.snapshot']

        # Find snapshot
        if snapshot_id:
            snapshot = Snapshot.browse(snapshot_id).exists()
        elif snapshot_name:
            snapshot = Snapshot.search([('name', '=', snapshot_name)], limit=1)
        else:
            return {
                'success': False,
                'error': 'Missing parameter',
                'message': "Either snapshot_id or snapshot_name is required",
            }

        if not snapshot:
            return {
                'success': False,
                'error': 'Snapshot not found',
                'message': f"No snapshot found with ID={snapshot_id} or name={snapshot_name}",
            }

        if snapshot.state != 'ready':
            return {
                'success': False,
                'error': 'Invalid snapshot state',
                'message': f"Snapshot is in state '{snapshot.state}', must be 'ready' to restore",
            }

        try:
            # Initiate restore
            result = snapshot.action_restore()

            _logger.warning(
                "Initiated restore to snapshot '%s' (ID: %d) at WAL position %s",
                snapshot.name, snapshot.id, snapshot.wal_position
            )

            return {
                'success': True,
                'snapshot': {
                    'id': snapshot.id,
                    'name': snapshot.name,
                    'wal_position': snapshot.wal_position,
                },
                'message': f"Restore to snapshot '{snapshot.name}' has been initiated. "
                          "The system will be restored to the snapshot point.",
                'warning': "This operation requires external orchestration to complete. "
                          "All changes after the snapshot will be lost.",
            }

        except Exception as e:
            _logger.exception("Failed to restore snapshot %d: %s", snapshot.id, e)
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to initiate restore: {e}",
            }

    @api.model
    def get_snapshot_status(self, snapshot_id):
        """
        Get detailed status of a snapshot.

        Args:
            snapshot_id: ID of the snapshot

        Returns:
            dict: Detailed snapshot information
        """
        Snapshot = self.env['loomworks.snapshot']
        snapshot = Snapshot.browse(snapshot_id).exists()

        if not snapshot:
            return {
                'success': False,
                'error': 'Snapshot not found',
                'message': f"No snapshot found with ID={snapshot_id}",
            }

        # Get related operations summary
        operations = snapshot.operation_log_ids
        op_summary = {
            'total': len(operations),
            'by_type': {},
        }
        for op in operations:
            op_type = op.operation_type
            op_summary['by_type'][op_type] = op_summary['by_type'].get(op_type, 0) + 1

        return {
            'success': True,
            'snapshot': {
                'id': snapshot.id,
                'name': snapshot.name,
                'display_name': snapshot.display_name,
                'type': snapshot.snapshot_type,
                'state': snapshot.state,
                'description': snapshot.description,
                # PITR data
                'wal_position': snapshot.wal_position,
                'wal_file': snapshot.wal_file,
                'recovery_target_time': snapshot.recovery_target_time.isoformat()
                    if snapshot.recovery_target_time else None,
                'base_backup_id': snapshot.base_backup_id,
                # Database info
                'database_name': snapshot.database_name,
                'database_size_bytes': snapshot.database_size_bytes,
                'database_size_mb': round(snapshot.database_size_bytes / (1024 * 1024), 2)
                    if snapshot.database_size_bytes else None,
                # Timestamps
                'created_at': snapshot.created_at.isoformat() if snapshot.created_at else None,
                'expires_at': snapshot.expires_at.isoformat() if snapshot.expires_at else None,
                'restored_at': snapshot.restored_at.isoformat() if snapshot.restored_at else None,
                # Created by
                'created_by': {
                    'id': snapshot.created_by_id.id,
                    'name': snapshot.created_by_id.name,
                } if snapshot.created_by_id else None,
                # Operations
                'operations': op_summary,
                # Error info
                'error_message': snapshot.error_message,
            },
        }

    @api.model
    def rollback_ai_operation(self, operation_id, confirm=False):
        """
        Rollback a specific AI operation.

        Args:
            operation_id: ID of the AI operation log to rollback
            confirm: Must be True to proceed

        Returns:
            dict: Rollback result
        """
        if not confirm:
            return {
                'success': False,
                'error': 'Confirmation required',
                'message': "Rollback requires explicit confirmation. Set confirm=true to proceed.",
            }

        OperationLog = self.env['loomworks.ai.operation.log']
        operation = OperationLog.browse(operation_id).exists()

        if not operation:
            return {
                'success': False,
                'error': 'Operation not found',
                'message': f"No AI operation found with ID={operation_id}",
            }

        if not operation.can_rollback:
            return {
                'success': False,
                'error': 'Cannot rollback',
                'message': f"Operation {operation_id} cannot be rolled back. "
                          f"State: {operation.state}, Undone: {operation.undone}, "
                          f"Type: {operation.operation_type}",
            }

        try:
            # Perform rollback
            operation.action_undo()

            _logger.info(
                "Rolled back AI operation %d (%s on %s)",
                operation.id, operation.operation_type, operation.model_name
            )

            return {
                'success': True,
                'operation': {
                    'id': operation.id,
                    'tool_name': operation.tool_name,
                    'operation_type': operation.operation_type,
                    'model_name': operation.model_name,
                    'state': operation.state,
                    'undone_at': operation.undone_at.isoformat() if operation.undone_at else None,
                },
                'message': f"Successfully rolled back {operation.operation_type} operation "
                          f"on {operation.model_name}",
            }

        except Exception as e:
            _logger.exception("Failed to rollback operation %d: %s", operation_id, e)
            return {
                'success': False,
                'error': str(e),
                'message': f"Failed to rollback operation: {e}",
            }

    @api.model
    def list_rollback_options(self, limit=10, session_id=None, only_rollbackable=True):
        """
        List recent AI operations that can be rolled back.

        Args:
            limit: Maximum number of results
            session_id: Optional session ID filter
            only_rollbackable: Only show operations that can be rolled back

        Returns:
            dict: List of operations with rollback status
        """
        OperationLog = self.env['loomworks.ai.operation.log']

        # Build domain
        domain = [
            ('operation_type', 'not in', ['search', 'read', 'report']),
        ]

        if session_id:
            domain.append(('session_id', '=', session_id))

        if only_rollbackable:
            domain.extend([
                ('can_rollback', '=', True),
                ('undone', '=', False),
            ])

        # Search operations
        operations = OperationLog.search(
            domain,
            order='create_date desc',
            limit=min(limit, 50)
        )

        result = []
        for op in operations:
            result.append({
                'id': op.id,
                'tool_name': op.tool_name,
                'operation_type': op.operation_type,
                'model_name': op.model_name,
                'record_count': op.record_count,
                'state': op.state,
                'can_rollback': op.can_rollback,
                'undone': op.undone,
                'created_at': op.create_date.isoformat() if op.create_date else None,
                'has_snapshot': bool(op.snapshot_id),
                'snapshot_id': op.snapshot_id.id if op.snapshot_id else None,
                'ai_reasoning': op.ai_reasoning,
            })

        return {
            'success': True,
            'count': len(result),
            'operations': result,
        }

    @api.model
    def cleanup_old_snapshots(self):
        """
        Run cleanup of expired snapshots and retention policies.

        Called by scheduled action.

        Returns:
            dict: Cleanup summary
        """
        Snapshot = self.env['loomworks.snapshot']
        Retention = self.env['loomworks.snapshot.retention']

        # Cleanup expired snapshots
        expired_count = Snapshot.cleanup_expired_snapshots()

        # Run retention policies
        retention_result = Retention.run_all_retention_policies()

        result = {
            'expired_by_date': expired_count,
            'expired_by_policy': retention_result.get('total_expired', 0),
            'kept': retention_result.get('total_kept', 0),
        }

        _logger.info(
            "Snapshot cleanup complete: %d expired by date, %d by policy, %d kept",
            result['expired_by_date'],
            result['expired_by_policy'],
            result['kept']
        )

        return result

    @api.model
    def get_pitr_status(self):
        """
        Check PostgreSQL PITR configuration status.

        Returns information about WAL archiving configuration
        to help diagnose PITR issues.

        Returns:
            dict: PITR configuration status
        """
        result = {
            'wal_level': None,
            'archive_mode': None,
            'archive_command': None,
            'current_wal_lsn': None,
            'is_configured': False,
            'warnings': [],
        }

        try:
            # Check wal_level
            self.env.cr.execute("SHOW wal_level")
            result['wal_level'] = self.env.cr.fetchone()[0]

            # Check archive_mode
            self.env.cr.execute("SHOW archive_mode")
            result['archive_mode'] = self.env.cr.fetchone()[0]

            # Check archive_command
            self.env.cr.execute("SHOW archive_command")
            result['archive_command'] = self.env.cr.fetchone()[0]

            # Get current WAL position
            self.env.cr.execute("SELECT pg_current_wal_lsn()")
            result['current_wal_lsn'] = str(self.env.cr.fetchone()[0])

            # Check configuration
            if result['wal_level'] not in ('replica', 'logical'):
                result['warnings'].append(
                    f"wal_level is '{result['wal_level']}', should be 'replica' or 'logical' for PITR"
                )

            if result['archive_mode'] != 'on':
                result['warnings'].append(
                    f"archive_mode is '{result['archive_mode']}', should be 'on' for PITR"
                )

            if not result['archive_command']:
                result['warnings'].append(
                    "archive_command is not configured"
                )

            result['is_configured'] = (
                result['wal_level'] in ('replica', 'logical') and
                result['archive_mode'] == 'on' and
                bool(result['archive_command'])
            )

        except Exception as e:
            result['error'] = str(e)
            result['warnings'].append(f"Failed to check PITR configuration: {e}")

        return result
