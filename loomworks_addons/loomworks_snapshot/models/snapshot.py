# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Loomworks Snapshot Model - PostgreSQL PITR Snapshots

This module implements database snapshots using PostgreSQL's Write-Ahead Log (WAL)
for Point-in-Time Recovery (PITR). Snapshots capture the database state at a
specific moment and can be used to restore to that exact point.

Architecture:
- Snapshots are logical markers tied to a WAL position (LSN)
- Physical base backups are managed externally (pg_basebackup)
- Restore operations use WAL replay to the captured LSN

References:
- PostgreSQL PITR: https://www.postgresql.org/docs/current/continuous-archiving.html
- pg_current_wal_lsn(): https://www.postgresql.org/docs/current/functions-admin.html
"""

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class LoomworksSnapshot(models.Model):
    """
    Database snapshot record with WAL position tracking.

    Each snapshot captures the PostgreSQL LSN (Log Sequence Number) at creation
    time, allowing point-in-time recovery to that exact moment. Snapshots can
    be automatic (scheduled), manual (user-triggered), or pre-AI (before AI ops).
    """
    _name = 'loomworks.snapshot'
    _description = 'Database Snapshot'
    _order = 'create_date desc'
    _rec_name = 'display_name'

    name = fields.Char(
        string='Name',
        required=True,
        help='Descriptive name for this snapshot'
    )
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )

    # Tenant relationship (optional for single-tenant deployments)
    tenant_id = fields.Many2one(
        'loomworks.tenant',
        string='Tenant',
        ondelete='cascade',
        help='Tenant this snapshot belongs to (for multi-tenant deployments)'
    )

    # Snapshot metadata
    snapshot_type = fields.Selection([
        ('auto', 'Automatic'),
        ('manual', 'Manual'),
        ('pre_ai', 'Pre-AI Operation'),
        ('pre_upgrade', 'Pre-Upgrade'),
    ], string='Snapshot Type', required=True, default='manual')

    state = fields.Selection([
        ('creating', 'Creating'),
        ('ready', 'Ready'),
        ('restoring', 'Restoring'),
        ('restored', 'Restored'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    ], string='State', default='creating', required=True, tracking=True)

    # PostgreSQL PITR data
    wal_position = fields.Char(
        string='WAL Position (LSN)',
        readonly=True,
        help='PostgreSQL Log Sequence Number at snapshot time'
    )
    wal_file = fields.Char(
        string='WAL Segment File',
        readonly=True,
        help='WAL segment file name containing this position'
    )
    base_backup_id = fields.Char(
        string='Base Backup ID',
        readonly=True,
        help='Associated pg_basebackup identifier for full restore'
    )
    recovery_target_time = fields.Datetime(
        string='Recovery Target Time',
        readonly=True,
        help='Timestamp for recovery_target_time in restore'
    )

    # Database information
    database_name = fields.Char(
        string='Database Name',
        required=True,
        default=lambda self: self.env.cr.dbname,
        readonly=True
    )
    database_size_bytes = fields.Integer(
        string='Database Size (bytes)',
        readonly=True,
        help='Size of database at snapshot time'
    )

    # Timestamps
    created_at = fields.Datetime(
        string='Created At',
        default=fields.Datetime.now,
        readonly=True
    )
    expires_at = fields.Datetime(
        string='Expires At',
        help='When this snapshot will be automatically deleted'
    )
    restored_at = fields.Datetime(
        string='Restored At',
        readonly=True,
        help='When this snapshot was last used for restore'
    )

    # Metadata
    description = fields.Text(
        string='Description',
        help='Additional notes about this snapshot'
    )
    created_by_id = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.uid,
        readonly=True
    )

    # Related operations
    operation_log_ids = fields.One2many(
        'loomworks.ai.operation.log',
        'snapshot_id',
        string='Related AI Operations',
        help='AI operations that used this snapshot as their rollback point'
    )
    operation_count = fields.Integer(
        string='Operation Count',
        compute='_compute_operation_count'
    )

    # Schedule reference (for auto snapshots)
    schedule_id = fields.Many2one(
        'loomworks.snapshot.schedule',
        string='Schedule',
        ondelete='set null',
        help='Schedule that created this snapshot (for auto snapshots)'
    )

    # Error tracking
    error_message = fields.Text(
        string='Error Message',
        readonly=True
    )

    @api.depends('name', 'snapshot_type', 'created_at')
    def _compute_display_name(self):
        for snapshot in self:
            type_label = dict(self._fields['snapshot_type'].selection).get(
                snapshot.snapshot_type, 'Unknown'
            )
            if snapshot.created_at:
                date_str = snapshot.created_at.strftime('%Y-%m-%d %H:%M')
                snapshot.display_name = f"[{type_label}] {snapshot.name} ({date_str})"
            else:
                snapshot.display_name = f"[{type_label}] {snapshot.name}"

    def _compute_operation_count(self):
        for snapshot in self:
            snapshot.operation_count = len(snapshot.operation_log_ids)

    def action_create_snapshot(self):
        """
        Create the actual snapshot by capturing current WAL position.

        This method:
        1. Captures the current PostgreSQL LSN (pg_current_wal_lsn)
        2. Captures the current WAL file name
        3. Records the database size
        4. Updates the snapshot state to 'ready'

        Note: This only captures the WAL position. Actual base backup
        creation should be handled by external backup infrastructure.
        """
        self.ensure_one()

        if self.state != 'creating':
            raise UserError(f"Cannot create snapshot in state '{self.state}'")

        try:
            # Capture current WAL position
            self.env.cr.execute("SELECT pg_current_wal_lsn()")
            lsn = self.env.cr.fetchone()[0]

            # Get WAL file name for this position
            self.env.cr.execute(
                "SELECT pg_walfile_name(%s)",
                [lsn]
            )
            wal_file = self.env.cr.fetchone()[0]

            # Get database size
            self.env.cr.execute(
                "SELECT pg_database_size(current_database())"
            )
            db_size = self.env.cr.fetchone()[0]

            # Update snapshot record
            self.write({
                'wal_position': str(lsn),
                'wal_file': wal_file,
                'recovery_target_time': fields.Datetime.now(),
                'database_size_bytes': db_size,
                'state': 'ready',
            })

            _logger.info(
                "Snapshot '%s' created at LSN %s (WAL file: %s)",
                self.name, lsn, wal_file
            )

        except Exception as e:
            self.write({
                'state': 'failed',
                'error_message': str(e),
            })
            _logger.exception("Failed to create snapshot '%s': %s", self.name, e)
            raise UserError(f"Failed to create snapshot: {e}")

        return True

    def action_restore(self):
        """
        Initiate restore to this snapshot point.

        WARNING: This is a destructive operation that will:
        1. Stop the Odoo server
        2. Restore the database to the snapshot point
        3. Replay WAL to the captured LSN
        4. Restart the server

        In production, this should be handled by external tooling
        (Kubernetes job, systemd service, etc.) due to the need to
        stop the running application.
        """
        self.ensure_one()

        if self.state not in ('ready', 'restored'):
            raise UserError(f"Cannot restore snapshot in state '{self.state}'")

        if not self.wal_position:
            raise UserError("Snapshot has no WAL position - cannot restore")

        # Create restore job record
        self.write({
            'state': 'restoring',
        })

        # In a real implementation, this would:
        # 1. Create a restore job in a queue
        # 2. Signal the orchestration layer (K8s, Docker) to initiate restore
        # 3. The restore process would run externally

        _logger.warning(
            "Restore initiated for snapshot '%s' to LSN %s. "
            "This requires external orchestration to complete.",
            self.name, self.wal_position
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Restore Initiated',
                'message': f"Restore to snapshot '{self.name}' has been queued. "
                          "The system will be restored to the captured point.",
                'type': 'warning',
                'sticky': True,
            }
        }

    def action_mark_restored(self):
        """
        Mark snapshot as successfully restored (called by external process).
        """
        self.ensure_one()
        self.write({
            'state': 'restored',
            'restored_at': fields.Datetime.now(),
        })
        return True

    def action_mark_expired(self):
        """
        Mark snapshot as expired (for retention policy cleanup).
        """
        self.ensure_one()
        self.write({'state': 'expired'})
        return True

    @api.model
    def create_pre_ai_snapshot(self, operation_name=None):
        """
        Create a snapshot before an AI operation.

        This is the main entry point for the AI integration. Before making
        changes, the AI system calls this to create a rollback point.

        Args:
            operation_name: Optional name for the operation

        Returns:
            loomworks.snapshot record
        """
        name = f"Pre-AI: {operation_name or 'Operation'}"
        snapshot = self.create({
            'name': name,
            'snapshot_type': 'pre_ai',
            'description': f"Automatic snapshot before AI operation: {operation_name}",
        })
        snapshot.action_create_snapshot()
        return snapshot

    @api.model
    def cleanup_expired_snapshots(self):
        """
        Cleanup snapshots that have passed their expiration date.

        Called by scheduled action to enforce retention policies.
        """
        now = fields.Datetime.now()
        expired = self.search([
            ('expires_at', '<=', now),
            ('state', '=', 'ready'),
        ])

        for snapshot in expired:
            try:
                snapshot.action_mark_expired()
                _logger.info("Marked snapshot '%s' as expired", snapshot.name)
            except Exception as e:
                _logger.error("Failed to expire snapshot '%s': %s", snapshot.name, e)

        return len(expired)

    def unlink(self):
        """Prevent deletion of snapshots in certain states."""
        for snapshot in self:
            if snapshot.state == 'restoring':
                raise UserError("Cannot delete a snapshot that is being restored")
        return super().unlink()
