# -*- coding: utf-8 -*-
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3

"""
Rollback Manager - Transaction and Snapshot Rollback for Skills

This service implements the M3 resolution from PATCH_NOTES_M1_M4.md:
- Uses Phase 5 snapshots when loomworks_snapshot is installed (full PITR)
- Falls back to PostgreSQL SAVEPOINT when Phase 5 is not available
- Provides consistent API regardless of rollback mechanism

Graceful Degradation:
| Feature                  | With Phase 5 | Without Phase 5 |
|--------------------------|--------------|-----------------|
| Pre-execution checkpoint | Full PITR    | SAVEPOINT       |
| Rollback scope           | Entire DB    | Current txn     |
| Post-commit undo         | Yes          | No              |
| Cross-transaction        | Yes          | No              |

Usage:
    manager = RollbackManager(env)
    savepoint = manager.create_savepoint("my-skill")
    try:
        # ... execute skill ...
        manager.release_savepoint(savepoint)
    except Exception:
        manager.rollback_to_savepoint(savepoint)
"""

import logging
from uuid import uuid4

_logger = logging.getLogger(__name__)


class RollbackManager:
    """
    Manages transaction savepoints and snapshots for skill execution.

    This class provides a unified interface for rollback operations,
    automatically using the best available mechanism based on installed modules.
    """

    def __init__(self, env):
        """
        Initialize the rollback manager.

        :param env: Odoo environment
        """
        self.env = env
        self.savepoint_stack = []
        self._snapshot_service = None
        self._snapshot_available = None

    @property
    def snapshot_available(self):
        """
        Check if Phase 5 snapshot service is available.

        Caches the result to avoid repeated registry lookups.
        """
        if self._snapshot_available is None:
            self._snapshot_available = 'loomworks.snapshot' in self.env.registry
            if not self._snapshot_available:
                _logger.info(
                    "Skills Framework: Phase 5 (loomworks_snapshot) not installed. "
                    "Running in degraded mode with transaction-level rollback only."
                )
        return self._snapshot_available

    @property
    def snapshot_service(self):
        """Get the snapshot service if available."""
        if self.snapshot_available and self._snapshot_service is None:
            self._snapshot_service = self.env['loomworks.snapshot']
        return self._snapshot_service

    def get_rollback_mode(self):
        """
        Get the current rollback mode.

        :return: 'snapshot' if Phase 5 available, else 'savepoint'
        """
        return 'snapshot' if self.snapshot_available else 'savepoint'

    def create_savepoint(self, name):
        """
        Create a rollback point.

        Uses Phase 5 snapshot if available, otherwise PostgreSQL SAVEPOINT.

        :param name: Descriptive name for the savepoint
        :return: Savepoint identifier (snapshot record or savepoint name string)
        """
        if self.snapshot_available:
            # Phase 5 available: use full PITR snapshot
            try:
                snapshot = self.snapshot_service.create_pre_ai_snapshot(
                    operation_name=name
                )
                _logger.info(
                    "Created snapshot savepoint '%s' at LSN %s",
                    name, snapshot.wal_position
                )
                return snapshot
            except Exception as e:
                _logger.warning(
                    "Failed to create snapshot, falling back to SAVEPOINT: %s", e
                )
                # Fall through to savepoint

        # Phase 5 not available or failed: use PostgreSQL savepoint
        savepoint_id = f"skill_{name}_{uuid4().hex[:8]}"
        try:
            self.env.cr.execute(f"SAVEPOINT {savepoint_id}")
            self.savepoint_stack.append(savepoint_id)
            _logger.debug("Created PostgreSQL savepoint: %s", savepoint_id)
            return savepoint_id
        except Exception as e:
            _logger.error("Failed to create savepoint: %s", e)
            raise

    def rollback_to_savepoint(self, savepoint_ref):
        """
        Rollback to a savepoint.

        Handles both snapshot objects and savepoint name strings.

        :param savepoint_ref: Snapshot record or savepoint name string
        """
        # Check if it's a snapshot record
        if hasattr(savepoint_ref, 'restore') or (
            hasattr(savepoint_ref, '_name') and
            savepoint_ref._name == 'loomworks.snapshot'
        ):
            # Phase 5 snapshot object
            try:
                # Note: Full restore is async and requires orchestration
                # For immediate rollback in same transaction, we still use savepoint
                _logger.info(
                    "Snapshot rollback requested for %s - "
                    "marking for restore (async operation)",
                    savepoint_ref.name
                )
                savepoint_ref.action_restore()
            except Exception as e:
                _logger.error("Snapshot rollback failed: %s", e)
                raise
        elif isinstance(savepoint_ref, str):
            # PostgreSQL savepoint name
            try:
                self.env.cr.execute(f"ROLLBACK TO SAVEPOINT {savepoint_ref}")
                _logger.debug("Rolled back to savepoint: %s", savepoint_ref)

                # Clear savepoints after this one from stack
                if savepoint_ref in self.savepoint_stack:
                    idx = self.savepoint_stack.index(savepoint_ref)
                    self.savepoint_stack = self.savepoint_stack[:idx]
            except Exception as e:
                _logger.error("Savepoint rollback failed: %s", e)
                raise
        else:
            _logger.warning(
                "Unknown savepoint reference type: %s",
                type(savepoint_ref)
            )

    def release_savepoint(self, savepoint_ref):
        """
        Release a savepoint on successful completion.

        For PostgreSQL savepoints, releases them to free resources.
        For snapshots, marks them as no longer needed for immediate rollback.

        :param savepoint_ref: Snapshot record or savepoint name string
        """
        if hasattr(savepoint_ref, '_name') and savepoint_ref._name == 'loomworks.snapshot':
            # Snapshot: keep for potential future rollback
            _logger.debug(
                "Snapshot %s retained for potential rollback",
                savepoint_ref.name
            )
        elif isinstance(savepoint_ref, str):
            # PostgreSQL savepoint
            try:
                self.env.cr.execute(f"RELEASE SAVEPOINT {savepoint_ref}")
                if savepoint_ref in self.savepoint_stack:
                    self.savepoint_stack.remove(savepoint_ref)
                _logger.debug("Released savepoint: %s", savepoint_ref)
            except Exception as e:
                _logger.warning("Failed to release savepoint: %s", e)

    def commit(self):
        """
        Release all savepoints on successful completion.

        Called when skill execution completes successfully.
        """
        # Release all PostgreSQL savepoints in reverse order
        for savepoint_id in reversed(self.savepoint_stack):
            try:
                self.env.cr.execute(f"RELEASE SAVEPOINT {savepoint_id}")
                _logger.debug("Released savepoint on commit: %s", savepoint_id)
            except Exception as e:
                _logger.warning("Failed to release savepoint %s: %s", savepoint_id, e)
        self.savepoint_stack.clear()

    def get_degradation_warning(self):
        """
        Get warning message for degraded mode.

        :return: Warning message string or None if full capability available
        """
        if not self.snapshot_available:
            return (
                "Running in degraded rollback mode: Phase 5 (loomworks_snapshot) "
                "not installed. Rollback is limited to the current transaction only. "
                "Post-commit undo is not available. Install loomworks_snapshot for "
                "full Point-in-Time Recovery capability."
            )
        return None

    def check_snapshot_capability(self):
        """
        Check and log snapshot capability status.

        :return: True if full snapshot capability available, False otherwise
        """
        if not self.snapshot_available:
            _logger.warning(
                "Skills Framework running in degraded mode: "
                "Phase 5 Snapshot System not installed. "
                "Rollback limited to current transaction only."
            )
            return False
        return True


class RollbackContext:
    """
    Context manager for automatic rollback handling.

    Usage:
        with RollbackContext(env, "my-operation") as ctx:
            # ... operations ...
            if error:
                ctx.should_rollback = True
    """

    def __init__(self, env, name, auto_rollback_on_exception=True):
        """
        Initialize rollback context.

        :param env: Odoo environment
        :param name: Name for the savepoint
        :param auto_rollback_on_exception: Rollback on unhandled exceptions
        """
        self.manager = RollbackManager(env)
        self.name = name
        self.auto_rollback = auto_rollback_on_exception
        self.savepoint = None
        self.should_rollback = False

    def __enter__(self):
        self.savepoint = self.manager.create_savepoint(self.name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and self.auto_rollback:
            # Exception occurred - rollback
            self.manager.rollback_to_savepoint(self.savepoint)
            _logger.info(
                "Auto-rolled back due to exception: %s",
                exc_val
            )
        elif self.should_rollback:
            # Explicit rollback requested
            self.manager.rollback_to_savepoint(self.savepoint)
        else:
            # Success - release savepoint
            self.manager.release_savepoint(self.savepoint)

        # Don't suppress exceptions
        return False

    def get_savepoint_ref(self):
        """Get the savepoint reference for external use."""
        return self.savepoint
