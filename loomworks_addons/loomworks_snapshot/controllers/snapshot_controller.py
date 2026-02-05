# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Snapshot Controller - REST API Endpoints

Provides HTTP endpoints for snapshot operations, complementing the
AI tool interface for direct programmatic access.

Endpoints:
- POST /snapshot/create - Create a new snapshot
- GET /snapshot/list - List available snapshots
- POST /snapshot/<id>/restore - Restore to a snapshot
- GET /snapshot/<id>/status - Get snapshot status
- GET /snapshot/pitr-status - Check PITR configuration
- POST /snapshot/rollback/<operation_id> - Rollback AI operation
"""

from odoo import http
from odoo.http import request, Response
import json
import logging

_logger = logging.getLogger(__name__)


class SnapshotController(http.Controller):
    """
    REST API controller for snapshot operations.

    All endpoints require authentication and appropriate permissions.
    """

    def _json_response(self, data, status=200):
        """Create a JSON response with proper headers."""
        return Response(
            json.dumps(data, default=str),
            status=status,
            content_type='application/json'
        )

    def _error_response(self, message, status=400):
        """Create an error response."""
        return self._json_response({
            'success': False,
            'error': message,
        }, status=status)

    @http.route('/snapshot/create', type='json', auth='user', methods=['POST'])
    def create_snapshot(self, **kwargs):
        """
        Create a new database snapshot.

        Request body:
        {
            "name": "My Snapshot",
            "description": "Optional description",
            "snapshot_type": "manual"  // optional, default: manual
        }

        Returns:
            Snapshot details including ID, name, WAL position
        """
        name = kwargs.get('name')
        if not name:
            return {'success': False, 'error': 'Name is required'}

        service = request.env['loomworks.snapshot.service']
        return service.create_snapshot(
            name=name,
            description=kwargs.get('description'),
            snapshot_type=kwargs.get('snapshot_type', 'manual'),
        )

    @http.route('/snapshot/list', type='json', auth='user', methods=['POST', 'GET'])
    def list_snapshots(self, **kwargs):
        """
        List available snapshots.

        Query parameters / Request body:
        {
            "state": "ready",      // optional, default: ready
            "snapshot_type": "all", // optional, default: all
            "limit": 20            // optional, default: 20
        }

        Returns:
            List of snapshot summaries
        """
        service = request.env['loomworks.snapshot.service']
        return service.list_snapshots(
            state=kwargs.get('state', 'ready'),
            snapshot_type=kwargs.get('snapshot_type', 'all'),
            limit=kwargs.get('limit', 20),
        )

    @http.route('/snapshot/<int:snapshot_id>/restore', type='json', auth='user', methods=['POST'])
    def restore_snapshot(self, snapshot_id, **kwargs):
        """
        Restore database to a snapshot point.

        Request body:
        {
            "confirm": true  // Required for safety
        }

        WARNING: This is a destructive operation. All changes after
        the snapshot will be lost.

        Returns:
            Restore operation status
        """
        confirm = kwargs.get('confirm', False)
        service = request.env['loomworks.snapshot.service']
        return service.restore_snapshot(
            snapshot_id=snapshot_id,
            confirm=confirm,
        )

    @http.route('/snapshot/<int:snapshot_id>/status', type='json', auth='user', methods=['GET', 'POST'])
    def get_snapshot_status(self, snapshot_id, **kwargs):
        """
        Get detailed status of a snapshot.

        Returns:
            Detailed snapshot information including state, timestamps,
            and related operations
        """
        service = request.env['loomworks.snapshot.service']
        return service.get_snapshot_status(snapshot_id=snapshot_id)

    @http.route('/snapshot/pitr-status', type='json', auth='user', methods=['GET', 'POST'])
    def get_pitr_status(self, **kwargs):
        """
        Check PostgreSQL PITR configuration status.

        Returns information about WAL archiving configuration
        to help diagnose PITR setup issues.

        Returns:
            PITR configuration status with warnings if misconfigured
        """
        service = request.env['loomworks.snapshot.service']
        return service.get_pitr_status()

    @http.route('/snapshot/rollback/<int:operation_id>', type='json', auth='user', methods=['POST'])
    def rollback_operation(self, operation_id, **kwargs):
        """
        Rollback a specific AI operation.

        Request body:
        {
            "confirm": true  // Required for safety
        }

        This provides granular rollback for individual operations
        without requiring full database restore.

        Returns:
            Rollback operation status
        """
        confirm = kwargs.get('confirm', False)
        service = request.env['loomworks.snapshot.service']
        return service.rollback_ai_operation(
            operation_id=operation_id,
            confirm=confirm,
        )

    @http.route('/snapshot/rollback-options', type='json', auth='user', methods=['GET', 'POST'])
    def list_rollback_options(self, **kwargs):
        """
        List recent AI operations that can be rolled back.

        Query parameters / Request body:
        {
            "limit": 10,              // optional, default: 10
            "session_id": 123,        // optional
            "only_rollbackable": true // optional, default: true
        }

        Returns:
            List of operations with rollback status
        """
        service = request.env['loomworks.snapshot.service']
        return service.list_rollback_options(
            limit=kwargs.get('limit', 10),
            session_id=kwargs.get('session_id'),
            only_rollbackable=kwargs.get('only_rollbackable', True),
        )

    @http.route('/snapshot/cleanup', type='json', auth='user', methods=['POST'])
    def run_cleanup(self, **kwargs):
        """
        Manually trigger snapshot cleanup.

        This runs the same cleanup that the scheduled action performs,
        useful for testing or manual maintenance.

        Returns:
            Cleanup summary with counts of expired/kept snapshots
        """
        # Check if user has admin rights
        if not request.env.user.has_group('base.group_system'):
            return {
                'success': False,
                'error': 'Insufficient permissions',
                'message': 'Admin access required for manual cleanup',
            }

        service = request.env['loomworks.snapshot.service']
        result = service.cleanup_old_snapshots()
        return {
            'success': True,
            'result': result,
            'message': 'Cleanup completed',
        }


class TenantController(http.Controller):
    """
    REST API controller for tenant operations.

    For multi-tenant deployments only.
    """

    @http.route('/tenant/info', type='json', auth='user', methods=['GET', 'POST'])
    def get_tenant_info(self, **kwargs):
        """
        Get information about the current tenant.

        For multi-tenant deployments, returns tenant details including
        resource limits and usage.

        Returns:
            Tenant information or null for single-tenant deployments
        """
        # Get database name from request
        db_name = request.env.cr.dbname

        Tenant = request.env['loomworks.tenant']
        tenant = Tenant.search([('database_name', '=', db_name)], limit=1)

        if not tenant:
            return {
                'success': True,
                'tenant': None,
                'message': 'Single-tenant deployment or tenant not found',
            }

        return {
            'success': True,
            'tenant': {
                'id': tenant.id,
                'name': tenant.name,
                'subdomain': tenant.subdomain,
                'state': tenant.state,
                'tier': tenant.tier,
                'limits': {
                    'max_users': tenant.max_users,
                    'max_storage_gb': tenant.max_storage_gb,
                    'max_ai_operations_daily': tenant.max_ai_operations_daily,
                    'max_snapshots': tenant.max_snapshots,
                },
                'usage': {
                    'current_users': tenant.current_users,
                    'current_storage_gb': tenant.current_storage_gb,
                    'ai_operations_today': tenant.current_ai_operations_today,
                    'snapshot_count': tenant.snapshot_count,
                },
                'subscription': {
                    'start': tenant.subscription_start.isoformat() if tenant.subscription_start else None,
                    'expires': tenant.subscription_expires.isoformat() if tenant.subscription_expires else None,
                },
            },
        }

    @http.route('/tenant/resource-check/<string:resource_type>', type='json', auth='user', methods=['GET', 'POST'])
    def check_resource_limit(self, resource_type, **kwargs):
        """
        Check if a resource limit would be exceeded.

        URL parameter:
            resource_type: 'users', 'storage', 'ai_operations', 'snapshots'

        Query parameters:
            current_value: Optional current value to check against

        Returns:
            Limit check result with remaining capacity
        """
        valid_types = ['users', 'storage', 'ai_operations', 'snapshots']
        if resource_type not in valid_types:
            return {
                'success': False,
                'error': f"Invalid resource_type. Must be one of: {valid_types}",
            }

        db_name = request.env.cr.dbname
        Tenant = request.env['loomworks.tenant']
        tenant = Tenant.search([('database_name', '=', db_name)], limit=1)

        if not tenant:
            # Single-tenant: no limits
            return {
                'success': True,
                'is_within_limit': True,
                'remaining': -1,  # Unlimited
                'limit': -1,
                'message': 'Single-tenant deployment (no limits)',
            }

        current_value = kwargs.get('current_value')
        is_within, remaining, limit = tenant.check_resource_limit(
            resource_type,
            current_value=current_value
        )

        return {
            'success': True,
            'resource_type': resource_type,
            'is_within_limit': is_within,
            'remaining': remaining,
            'limit': limit,
        }
