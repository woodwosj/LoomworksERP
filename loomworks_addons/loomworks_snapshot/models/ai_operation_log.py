# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
AI Operation Log Extension for Snapshot Integration

This module EXTENDS the `loomworks.ai.operation.log` model defined in Phase 2
(loomworks_ai). The canonical model definition lives in Phase 2.

This extension adds:
- snapshot_id: Links operation to pre-operation PITR snapshot
- can_rollback: Computed field indicating rollback capability
- undone/undone_at: Granular undo tracking
- action_undo(): Method for single-operation rollback
- rollback_operation(): Method using PITR or savepoint fallback

Model Ownership: Phase 2 (loomworks_ai) owns `loomworks.ai.operation.log`
This Extension: Phase 5 (loomworks_snapshot) adds snapshot integration

Graceful Degradation (M3 Resolution):
- If snapshot service is available: Uses full PITR snapshot for rollback
- If not: Falls back to PostgreSQL SAVEPOINT for transaction-scoped rollback

References:
- PATCH_NOTES_M1_M4.md: M3 resolution
- design.md: Decision 2 - Snapshot Strategy
"""

from odoo import models, fields, api
from odoo.exceptions import UserError
import json
import logging
from uuid import uuid4

_logger = logging.getLogger(__name__)


class AIOperationLogSnapshotExtension(models.Model):
    """
    Extension of loomworks.ai.operation.log to add snapshot integration.

    The base model is defined in Phase 2 (loomworks_ai) and provides:
    - session_id, agent_id, user_id (relationships)
    - tool_name, operation_type (operation details)
    - model_name, record_ids (target)
    - values_before, values_after (rollback data)
    - state, error_message (execution status)
    - execution_time_ms (performance)
    - ai_reasoning (AI explanation)

    This extension adds:
    - snapshot_id: Links to pre-operation PITR snapshot for disaster recovery
    - can_rollback: Computed field indicating if rollback is possible
    - undone, undone_at: Granular undo tracking
    - action_undo(): Method for single-operation rollback
    - rollback_operation(): PITR or savepoint-based rollback
    """
    _inherit = 'loomworks.ai.operation.log'

    # Snapshot integration for PITR rollback
    snapshot_id = fields.Many2one(
        'loomworks.snapshot',
        string='Pre-Operation Snapshot',
        ondelete='set null',
        help="PITR snapshot taken before this operation for disaster recovery"
    )

    # Granular undo tracking
    undone = fields.Boolean(
        string='Undone',
        default=False,
        help="Whether this operation has been reversed"
    )
    undone_at = fields.Datetime(
        string='Undone At',
        help="Timestamp when operation was reversed"
    )
    undone_by_id = fields.Many2one(
        'res.users',
        string='Undone By',
        help="User who triggered the undo"
    )

    # Computed rollback capability
    can_rollback = fields.Boolean(
        string='Can Rollback',
        compute='_compute_can_rollback',
        store=True,
        help="Whether this operation can be rolled back"
    )

    # Savepoint tracking (for graceful degradation)
    savepoint_id = fields.Char(
        string='Savepoint ID',
        help="PostgreSQL savepoint name (used when PITR not available)"
    )

    @api.depends('state', 'operation_type', 'undone', 'values_before', 'snapshot_id')
    def _compute_can_rollback(self):
        """
        Compute whether this operation can be rolled back.

        Rollback is possible if:
        - Operation completed successfully (state = 'success')
        - Not already undone
        - Operation type is reversible (create, write, unlink)
        - Either snapshot_id exists OR values_before captured
        """
        for log in self:
            if log.state != 'success':
                log.can_rollback = False
                continue

            if log.undone:
                log.can_rollback = False
                continue

            # Read-only operations don't need rollback
            if log.operation_type in ('search', 'read', 'report'):
                log.can_rollback = False
                continue

            # Delete operations need captured state to recreate
            if log.operation_type == 'unlink' and not log.values_before:
                log.can_rollback = False
                continue

            # Must have either snapshot or values_before for rollback
            has_snapshot = bool(log.snapshot_id and log.snapshot_id.state == 'ready')
            has_values = bool(log.values_before)

            log.can_rollback = has_snapshot or has_values

    def action_undo(self):
        """
        Undo this operation by restoring previous values.

        This provides granular single-operation rollback without requiring
        full PITR restore. For catastrophic failures, use snapshot restore.

        Uses values_before to reverse the operation:
        - create: deletes the created records
        - write/update: restores previous field values
        - unlink/delete: recreates the deleted records

        Returns:
            bool: True if undo succeeded

        Raises:
            UserError: If operation already undone or undo not possible
        """
        self.ensure_one()

        if self.undone:
            raise UserError("Operation has already been undone")

        if not self.can_rollback:
            raise UserError("This operation cannot be rolled back")

        try:
            # Get the target model
            if not self.model_name:
                raise UserError("Operation has no target model specified")

            Model = self.env[self.model_name].with_context(skip_ai_logging=True)
            record_ids = json.loads(self.record_ids) if self.record_ids else []
            values_before = json.loads(self.values_before) if self.values_before else {}

            if self.operation_type == 'create':
                # Undo create = delete created records
                if record_ids:
                    records = Model.browse(record_ids).exists()
                    if records:
                        records.unlink()
                        _logger.info(
                            "Undid create operation: deleted %d records from %s",
                            len(records), self.model_name
                        )

            elif self.operation_type in ('write', 'update'):
                # Undo write = restore previous values
                # values_before is {record_id: {field: value, ...}, ...}
                for rec_id_str, vals in values_before.items():
                    rec_id = int(rec_id_str)
                    record = Model.browse(rec_id).exists()
                    if record and vals:
                        record.write(vals)
                _logger.info(
                    "Undid write operation: restored %d records in %s",
                    len(values_before), self.model_name
                )

            elif self.operation_type in ('unlink', 'delete'):
                # Undo delete = recreate with captured values
                # values_before is {record_id: {field: value, ...}, ...}
                created_ids = []
                for rec_id_str, vals in values_before.items():
                    if vals:
                        # Remove id from vals if present (will be auto-generated)
                        vals_copy = {k: v for k, v in vals.items() if k != 'id'}
                        new_record = Model.create(vals_copy)
                        created_ids.append(new_record.id)
                _logger.info(
                    "Undid delete operation: recreated %d records in %s",
                    len(created_ids), self.model_name
                )

            else:
                raise UserError(
                    f"Undo not supported for operation type '{self.operation_type}'"
                )

            # Mark as undone
            self.write({
                'undone': True,
                'undone_at': fields.Datetime.now(),
                'undone_by_id': self.env.uid,
                'state': 'rolled_back',
            })

            return True

        except Exception as e:
            _logger.exception("Failed to undo operation %s: %s", self.id, e)
            raise UserError(f"Failed to undo operation: {e}")

    def rollback_operation(self):
        """
        Rollback this specific AI operation.

        Strategy (M3 graceful degradation):
        1. If snapshot_id exists and is ready: Use PITR restore
        2. Else if values_before captured: Use granular action_undo()
        3. Else if savepoint_id exists: Attempt savepoint rollback
        4. Else: Raise error

        For most cases, action_undo() is preferred as it's faster and
        doesn't require full database restore. PITR is for disaster recovery.

        Returns:
            dict: Action result or True
        """
        self.ensure_one()

        if not self.can_rollback:
            raise UserError("This operation cannot be rolled back")

        # Strategy 1: If we have a snapshot and user explicitly wants PITR
        if self.snapshot_id and self.snapshot_id.state == 'ready':
            # For safety, prefer granular undo if values_before exists
            if self.values_before:
                _logger.info(
                    "Using granular undo for operation %s (snapshot available but "
                    "granular rollback is safer)", self.id
                )
                return self.action_undo()
            else:
                # Full PITR restore
                _logger.warning(
                    "Initiating PITR restore for operation %s via snapshot %s",
                    self.id, self.snapshot_id.name
                )
                return self.snapshot_id.action_restore()

        # Strategy 2: Granular undo using values_before
        if self.values_before:
            return self.action_undo()

        # Strategy 3: Savepoint rollback (transaction-scoped only)
        if self.savepoint_id:
            return self._rollback_via_savepoint()

        raise UserError(
            "No rollback method available. Operation has no snapshot, "
            "captured values, or savepoint."
        )

    def _rollback_via_savepoint(self):
        """
        Attempt rollback via PostgreSQL SAVEPOINT.

        Note: This only works within the same transaction. If the transaction
        has been committed, savepoint rollback is not possible.

        This is the graceful degradation fallback when Phase 5 snapshot
        service is not properly configured.
        """
        self.ensure_one()

        if not self.savepoint_id:
            raise UserError("No savepoint available for this operation")

        try:
            self.env.cr.execute(f"ROLLBACK TO SAVEPOINT {self.savepoint_id}")
            self.write({
                'undone': True,
                'undone_at': fields.Datetime.now(),
                'undone_by_id': self.env.uid,
                'state': 'rolled_back',
            })
            _logger.info(
                "Rolled back operation %s via savepoint %s",
                self.id, self.savepoint_id
            )
            return True

        except Exception as e:
            _logger.warning(
                "Savepoint rollback failed for operation %s: %s "
                "(transaction may have been committed)",
                self.id, e
            )
            raise UserError(
                f"Savepoint rollback failed: {e}. "
                "This may be because the transaction has already been committed. "
                "Try using granular undo if values_before is available."
            )

    @api.model
    def create_with_snapshot(self, session_id, tool_name, operation_type, **kwargs):
        """
        Create an operation log with pre-operation snapshot.

        This is the main entry point for AI operations that want
        rollback capability. It:
        1. Creates a pre-AI snapshot (if snapshot service configured)
        2. Creates a savepoint (as fallback)
        3. Creates the operation log record

        Args:
            session_id: AI session ID
            tool_name: Name of the AI tool
            operation_type: Type of operation
            **kwargs: Additional log fields

        Returns:
            loomworks.ai.operation.log record
        """
        snapshot_id = False
        savepoint_id = None

        # Try to create snapshot (if Phase 5 is properly configured)
        try:
            Snapshot = self.env['loomworks.snapshot']
            snapshot = Snapshot.create_pre_ai_snapshot(
                operation_name=f"{tool_name}: {operation_type}"
            )
            snapshot_id = snapshot.id
        except Exception as e:
            _logger.warning(
                "Could not create pre-AI snapshot (graceful degradation): %s", e
            )

        # Create savepoint as fallback
        try:
            savepoint_id = f"ai_op_{uuid4().hex[:8]}"
            self.env.cr.execute(f"SAVEPOINT {savepoint_id}")
        except Exception as e:
            _logger.warning("Could not create savepoint: %s", e)
            savepoint_id = None

        # Create the operation log
        return self.create_log(
            session_id=session_id,
            tool_name=tool_name,
            operation_type=operation_type,
            snapshot_id=snapshot_id,
            savepoint_id=savepoint_id,
            **kwargs
        )

    def action_view_snapshot(self):
        """
        Open the related snapshot record.
        """
        self.ensure_one()
        if not self.snapshot_id:
            raise UserError("This operation has no associated snapshot")

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'loomworks.snapshot',
            'res_id': self.snapshot_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
