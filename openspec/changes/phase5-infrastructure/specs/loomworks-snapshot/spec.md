# Loomworks Snapshot System

Database snapshot and point-in-time recovery system for AI rollback capabilities.

## ADDED Requirements

### Requirement: Snapshot Model
The system SHALL provide a `loomworks.snapshot` model that stores snapshot metadata including WAL position, snapshot type, and state.

#### Scenario: Create snapshot record
- **WHEN** a snapshot is initiated for tenant "acme"
- **THEN** a `loomworks.snapshot` record is created with state "creating"
- **AND** the current WAL position (LSN) is captured

#### Scenario: Snapshot ready state
- **WHEN** snapshot creation completes successfully
- **THEN** the snapshot state transitions to "ready"
- **AND** the snapshot is available for restore operations

#### Scenario: Snapshot expiration
- **WHEN** a snapshot reaches its expiration date (retention period exceeded)
- **THEN** the snapshot state transitions to "expired"
- **AND** the snapshot is no longer available for restore
- **AND** associated storage can be reclaimed

---

### Requirement: Manual Snapshot Creation
The system SHALL allow users to create manual snapshots on demand with a descriptive name.

#### Scenario: User creates manual snapshot
- **WHEN** a user clicks "Create Snapshot" and enters name "Before major changes"
- **THEN** a snapshot is created with type "manual"
- **AND** the user receives confirmation with the snapshot name and timestamp

#### Scenario: Snapshot creation in progress
- **WHEN** a snapshot is being created
- **THEN** the UI displays a progress indicator
- **AND** the user cannot create another snapshot until the current one completes

---

### Requirement: Automatic Snapshot Scheduling
The system SHALL automatically create snapshots based on a configurable schedule.

#### Scenario: Scheduled automatic snapshot
- **WHEN** the configured snapshot schedule time is reached (e.g., daily at 2:00 AM UTC)
- **THEN** an automatic snapshot is created with type "auto"
- **AND** the snapshot is named with timestamp format "auto_YYYYMMDD_HHMMSS"

#### Scenario: Configure snapshot frequency
- **WHEN** an administrator sets snapshot_frequency to "hourly"
- **THEN** automatic snapshots are created every hour
- **AND** the next scheduled snapshot time is displayed in the UI

---

### Requirement: Pre-AI Operation Snapshots
The system SHALL create lightweight snapshots before AI operations that modify data.

#### Scenario: Snapshot before AI create operation
- **WHEN** an AI session is about to create records
- **THEN** a snapshot is created with type "pre_ai"
- **AND** the snapshot is linked to the AI session

#### Scenario: Snapshot before AI bulk operation
- **WHEN** an AI session is about to perform a bulk update affecting more than 10 records
- **THEN** a full snapshot is created with type "pre_ai"
- **AND** a warning is logged about the large operation

#### Scenario: Skip snapshot for read-only operations
- **WHEN** an AI session performs only read operations (search, read)
- **THEN** no pre-AI snapshot is created

---

### Requirement: Point-in-Time Restore
The system SHALL support restoring a tenant database to any point in time within the retention window.

#### Scenario: Restore to specific snapshot
- **WHEN** an administrator selects a snapshot and clicks "Restore"
- **THEN** a confirmation dialog is displayed warning of data loss
- **AND** upon confirmation, the restore process begins
- **AND** the tenant database is restored to the snapshot state

#### Scenario: Restore to specific timestamp
- **WHEN** an administrator enters a specific timestamp "2024-01-15 14:30:00 UTC"
- **THEN** the system validates the timestamp is within the retention window
- **AND** upon confirmation, the database is restored to that exact point in time

#### Scenario: Restore timestamp out of range
- **WHEN** an administrator enters a timestamp older than the retention period
- **THEN** an error message indicates the timestamp is not available
- **AND** the earliest available restore point is displayed

#### Scenario: Restore process isolation
- **WHEN** a restore is in progress for tenant "acme"
- **THEN** users cannot access the "acme" tenant
- **AND** other tenants are unaffected
- **AND** a maintenance page is displayed to "acme" users

---

### Requirement: AI Operation Logging
The system SHALL log all AI operations with sufficient detail to enable granular undo.

#### Scenario: Log AI create operation
- **WHEN** an AI session creates a new sales order
- **THEN** an `ai.operation.log` record is created
- **AND** operation_type is "create"
- **AND** record_ids contains the new record ID
- **AND** values_after contains the created field values

#### Scenario: Log AI update operation
- **WHEN** an AI session updates a partner record
- **THEN** an `ai.operation.log` record is created
- **AND** operation_type is "write"
- **AND** values_before contains the original field values
- **AND** values_after contains the new field values

#### Scenario: Log AI delete operation
- **WHEN** an AI session deletes records
- **THEN** an `ai.operation.log` record is created
- **AND** operation_type is "unlink"
- **AND** values_before contains all field values of deleted records

---

### Requirement: Granular Undo Capability
The system SHALL allow users to undo specific AI operations without a full database restore.

#### Scenario: Undo create operation
- **WHEN** a user clicks "Undo" on an AI create operation
- **THEN** the created records are deleted
- **AND** the operation log is marked as undone
- **AND** the user receives confirmation

#### Scenario: Undo update operation
- **WHEN** a user clicks "Undo" on an AI update operation
- **THEN** the records are restored to their previous values (values_before)
- **AND** the operation log is marked as undone

#### Scenario: Undo delete operation
- **WHEN** a user clicks "Undo" on an AI delete operation
- **THEN** the deleted records are re-created with their original values
- **AND** relationships are restored where possible
- **AND** the operation log is marked as undone

#### Scenario: Undo already undone operation
- **WHEN** a user attempts to undo an operation that was already undone
- **THEN** an error message indicates the operation was already undone
- **AND** the undo action is blocked

#### Scenario: Undo with conflicting changes
- **WHEN** a user attempts to undo an update operation
- **AND** the affected records have been modified since the AI operation
- **THEN** a warning is displayed about potential conflicts
- **AND** the user can choose to proceed or cancel

---

### Requirement: Snapshot Retention Management
The system SHALL automatically manage snapshot retention based on configurable policies.

#### Scenario: Apply retention policy
- **WHEN** a snapshot exceeds the retention period (default 30 days)
- **THEN** the snapshot state changes to "expired"
- **AND** the snapshot is queued for deletion

#### Scenario: Prevent deletion of recent snapshots
- **WHEN** the retention cleanup runs
- **THEN** the most recent 3 snapshots are always preserved regardless of age

#### Scenario: Storage cleanup
- **WHEN** expired snapshots are deleted
- **THEN** associated WAL segments no longer needed are deleted
- **AND** storage usage is recalculated for the tenant

---

### Requirement: WAL Archiving Configuration
The system SHALL configure PostgreSQL WAL archiving to support point-in-time recovery.

#### Scenario: WAL segment archived
- **WHEN** a WAL segment file is filled (16MB default)
- **THEN** the segment is compressed and copied to the archive location
- **AND** the archive command succeeds before the segment is recycled

#### Scenario: Archive timeout trigger
- **WHEN** archive_timeout (5 minutes) elapses without a full WAL segment
- **THEN** a partial WAL segment is archived
- **AND** the RPO target of 5 minutes is maintained

#### Scenario: Archive failure handling
- **WHEN** WAL archiving fails
- **THEN** PostgreSQL retains the segment and retries
- **AND** an alert is triggered for operations team
- **AND** the segment is archived once the issue is resolved
