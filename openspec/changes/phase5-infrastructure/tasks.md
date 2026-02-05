# Phase 5: Hosting Infrastructure and Snapshots - Implementation Tasks

## 1. Multi-Tenant Architecture (Weeks 39-40)

### 1.1 Tenant Management Module
- [ ] 1.1.1 Create `loomworks_tenant` module structure
  - `__manifest__.py` with dependencies on `base`, `loomworks_core`
  - `models/__init__.py`, `views/__init__.py`, `security/`
- [ ] 1.1.2 Implement `loomworks.tenant` model
  - Core fields: name, database_name, subdomain, state
  - Resource limits: max_users, max_storage_gb, max_ai_operations_daily
  - Billing fields: tier, subscription_expires
  - Relationship to snapshots
- [ ] 1.1.3 Create tenant provisioning wizard
  - Subdomain validation (alphanumeric, unique)
  - Database creation via `psql` subprocess
  - Initial module installation
  - Admin user creation
- [ ] 1.1.4 Implement tenant lifecycle management
  - Suspend/resume tenant
  - Archive tenant (soft delete with data retention)
  - Destroy tenant (hard delete after retention period)

### 1.2 Subdomain Routing
- [ ] 1.2.1 Configure Odoo dbfilter for subdomain matching
  - Update `odoo.conf` template with `dbfilter = ^%d$`
  - Implement `proxy_mode = True` for reverse proxy support
- [ ] 1.2.2 Create Nginx configuration template
  - Wildcard SSL certificate configuration
  - Subdomain to Odoo routing rules
  - WebSocket support for Odoo longpolling
- [ ] 1.2.3 Implement database discovery middleware
  - Validate subdomain against `loomworks.tenant` records
  - Return 404 for unknown subdomains
  - Cache tenant lookups for performance

### 1.3 Resource Quota Enforcement
- [ ] 1.3.1 Implement storage quota checking
  - Query PostgreSQL `pg_database_size()`
  - Block operations when quota exceeded
  - Send warning notifications at 80% usage
- [ ] 1.3.2 Implement user count enforcement
  - Override `res.users` create to check quota
  - Display remaining user slots in UI
- [ ] 1.3.3 Implement AI operation rate limiting
  - Track daily AI operations per tenant
  - Enforce limits based on subscription tier
  - Reset counters at midnight UTC

### 1.4 Tenant Security
- [ ] 1.4.1 Create security groups for tenant management
  - `loomworks_tenant.group_tenant_admin` for hosting admins
  - `loomworks_tenant.group_tenant_user` for self-service
- [ ] 1.4.2 Implement access rules
  - Tenants can only see own record in management portal
  - Super admins can manage all tenants
- [ ] 1.4.3 Create isolation verification tests
  - Test database connection isolation
  - Test subdomain routing isolation
  - Test cross-tenant access prevention

## 2. Snapshot System (Weeks 41-42)

### 2.1 Snapshot Module Foundation
- [ ] 2.1.1 Create `loomworks_snapshot` module structure
  - `__manifest__.py` with dependencies on `loomworks_tenant`, `loomworks_ai`
  - Standard Odoo module directories
- [ ] 2.1.2 Implement `loomworks.snapshot` model
  - Core fields: tenant_id, name, created_at, state
  - PITR fields: wal_position (LSN), wal_file, base_backup_path
  - Type: `selection([('auto', 'Automatic'), ('manual', 'Manual'), ('pre_ai', 'Pre-AI Operation')])`
  - Size tracking: size_bytes (computed from backup)
- [ ] 2.1.3 Implement `ai.operation.log` model
  - Link to session: `session_id` (Many2one to `loomworks.ai.session`)
  - Operation metadata: model, record_ids (JSON), operation_type
  - Undo data: values_before (JSON), values_after (JSON)
  - Snapshot reference for rollback target

### 2.2 PostgreSQL WAL Configuration
- [ ] 2.2.1 Create PostgreSQL configuration template
  - `wal_level = replica`
  - `archive_mode = on`
  - `archive_command` with error handling and compression
  - `archive_timeout = 300` (5 minutes)
- [ ] 2.2.2 Implement WAL archive management
  - Archive to tenant-specific directory
  - Compress with gzip or zstd
  - Clean up archives older than retention period
- [ ] 2.2.3 Implement base backup scheduling
  - Daily pg_basebackup with --wal-method=stream
  - Parallel compression of backup
  - Verification of backup integrity

### 2.3 Snapshot Creation Workflow
- [ ] 2.3.1 Implement manual snapshot creation
  - User-triggered from UI or API
  - Capture current WAL position via `pg_current_wal_lsn()`
  - Create metadata record with status tracking
- [ ] 2.3.2 Implement automatic snapshot creation
  - Scheduled via ir.cron (configurable frequency)
  - Triggered after significant operations (e.g., large imports)
- [ ] 2.3.3 Implement pre-AI operation snapshots
  - Hook into AI session start
  - Lightweight savepoint for small operations
  - Full snapshot for destructive operations

### 2.4 Point-in-Time Restore
- [ ] 2.4.1 Implement restore wizard
  - Select snapshot or specify timestamp
  - Validate timestamp within retention window
  - Confirm destructive operation with user
- [ ] 2.4.2 Implement restore process
  - Stop Odoo instance for tenant database
  - Restore base backup to new location
  - Configure recovery.conf with target_time
  - Replay WAL to specified point
  - Swap database names atomically
- [ ] 2.4.3 Implement restore verification
  - Validate database integrity post-restore
  - Run consistency checks on critical tables
  - Send notification on completion

### 2.5 Granular Undo Capability
- [ ] 2.5.1 Implement operation undo for creates
  - Delete records created by AI operation
  - Handle cascade deletes appropriately
- [ ] 2.5.2 Implement operation undo for updates
  - Restore `values_before` to affected records
  - Handle concurrent modifications gracefully
- [ ] 2.5.3 Implement operation undo for deletes
  - Re-create deleted records from `values_before`
  - Restore relationships where possible
- [ ] 2.5.4 Create undo UI in AI chat
  - "Undo last action" button
  - Undo history with selective rollback
  - Confirmation for multi-record undo

## 3. Docker Infrastructure (Weeks 43-44)

### 3.1 Dockerfile Creation
- [ ] 3.1.1 Create multi-stage Dockerfile
  - Builder stage: install Python dependencies
  - Runtime stage: minimal image with Odoo + Loomworks
  - Include wkhtmltopdf for PDF generation
- [ ] 3.1.2 Configure entrypoint script
  - Wait for PostgreSQL availability
  - Run database migrations
  - Initialize Odoo configuration
  - Handle graceful shutdown
- [ ] 3.1.3 Add health check configuration
  - HTTP health endpoint on /web/health
  - Database connectivity check
  - Redis connectivity check (if using)

### 3.2 Docker Compose Configuration
- [ ] 3.2.1 Create `docker-compose.yml`
  - Odoo service with environment variables
  - PostgreSQL 15 with WAL configuration
  - Redis for session storage
  - Nginx reverse proxy
- [ ] 3.2.2 Configure PostgreSQL for PITR
  - Mount custom postgresql.conf
  - Volume for WAL archive storage
  - Volume for base backups
- [ ] 3.2.3 Create environment file template
  - Database credentials
  - Odoo configuration options
  - AI API keys placeholder
  - Backup configuration

### 3.3 Docker Volumes and Persistence
- [ ] 3.3.1 Define volume structure
  - `odoo_data` for filestore
  - `postgres_data` for database files
  - `wal_archive` for WAL segments
  - `backups` for base backups
- [ ] 3.3.2 Implement backup volume management
  - Rotation of old backups
  - Offsite backup sync script
  - Restore from backup procedure

### 3.4 Local Development Setup
- [ ] 3.4.1 Create `docker-compose.dev.yml` override
  - Volume mounts for live code reload
  - Debug port exposure (5678 for debugpy)
  - Relaxed resource limits
- [ ] 3.4.2 Create development helper scripts
  - `./scripts/dev-start.sh` for development stack
  - `./scripts/dev-shell.sh` for Odoo shell access
  - `./scripts/dev-test.sh` for running tests

## 4. Kubernetes Infrastructure (Weeks 45-46)

### 4.1 PostgreSQL StatefulSet
- [ ] 4.1.1 Create PostgreSQL StatefulSet manifest
  - Single replica with persistent storage
  - Resource requests and limits
  - Liveness and readiness probes
- [ ] 4.1.2 Configure PersistentVolumeClaims
  - Data volume: 100Gi (expandable)
  - WAL archive volume: 50Gi
  - Backup volume: 200Gi
- [ ] 4.1.3 Create ConfigMap for postgresql.conf
  - WAL archiving settings
  - Performance tuning parameters
  - Logging configuration
- [ ] 4.1.4 Create Secret for credentials
  - PostgreSQL superuser password
  - Replication user credentials
  - Backup encryption key

### 4.2 Odoo Deployment
- [ ] 4.2.1 Create Odoo Deployment manifest
  - Multiple replicas for high availability
  - Rolling update strategy
  - Resource requests and limits
- [ ] 4.2.2 Configure ConfigMap for odoo.conf
  - Database connection parameters
  - Worker configuration
  - Proxy mode settings
- [ ] 4.2.3 Create Secret for Odoo credentials
  - Admin password
  - Database user credentials
  - AI API keys
- [ ] 4.2.4 Configure PersistentVolumeClaim for filestore
  - ReadWriteMany access mode
  - Shared across all Odoo pods

### 4.3 Services and Ingress
- [ ] 4.3.1 Create ClusterIP Service for Odoo
  - Port 8069 for HTTP
  - Port 8072 for longpolling
- [ ] 4.3.2 Create Headless Service for PostgreSQL
  - For StatefulSet DNS resolution
- [ ] 4.3.3 Create Ingress with wildcard subdomain
  - TLS termination with Let's Encrypt
  - Subdomain routing rules
  - WebSocket upgrade support
- [ ] 4.3.4 Configure cert-manager for TLS
  - ClusterIssuer for Let's Encrypt
  - Wildcard certificate for *.loomworks.app

### 4.4 Horizontal Pod Autoscaling
- [ ] 4.4.1 Create HorizontalPodAutoscaler for Odoo
  - Min replicas: 2
  - Max replicas: 10
  - Target CPU utilization: 70%
  - Target memory utilization: 80%
- [ ] 4.4.2 Configure resource requests appropriately
  - CPU: 500m request, 2000m limit
  - Memory: 1Gi request, 4Gi limit
- [ ] 4.4.3 Test scaling behavior
  - Load test to trigger scale-up
  - Verify scale-down after load reduction
  - Validate session continuity during scaling

### 4.5 Monitoring and Observability
- [ ] 4.5.1 Create ServiceMonitor for Prometheus
  - Odoo metrics endpoint
  - PostgreSQL metrics via postgres_exporter
- [ ] 4.5.2 Configure logging
  - Structured JSON logging from Odoo
  - Log aggregation configuration
- [ ] 4.5.3 Create alerting rules
  - Pod restart alerts
  - Database connection pool exhaustion
  - Disk space warnings for backup volumes

## 5. Testing and Verification

### 5.1 Unit Tests
- [ ] 5.1.1 Test tenant model CRUD operations
- [ ] 5.1.2 Test snapshot model CRUD operations
- [ ] 5.1.3 Test AI operation log recording
- [ ] 5.1.4 Test quota enforcement logic

### 5.2 Integration Tests
- [ ] 5.2.1 Test tenant provisioning workflow
- [ ] 5.2.2 Test subdomain routing with multiple tenants
- [ ] 5.2.3 Test snapshot creation and metadata capture
- [ ] 5.2.4 Test PITR restore to specific timestamp
- [ ] 5.2.5 Test granular undo of AI operations

### 5.3 Infrastructure Tests
- [ ] 5.3.1 Test Docker Compose stack startup
- [ ] 5.3.2 Test Kubernetes deployment rollout
- [ ] 5.3.3 Test HPA scaling behavior
- [ ] 5.3.4 Test backup and restore procedures
- [ ] 5.3.5 Test zero-downtime deployment

### 5.4 Security Tests
- [ ] 5.4.1 Test tenant database isolation
- [ ] 5.4.2 Test cross-tenant access prevention
- [ ] 5.4.3 Test backup encryption verification
- [ ] 5.4.4 Test credential rotation procedures

## 6. Documentation

### 6.1 Operations Documentation
- [ ] 6.1.1 Document tenant provisioning procedure
- [ ] 6.1.2 Document backup and restore procedures
- [ ] 6.1.3 Document disaster recovery runbook
- [ ] 6.1.4 Document scaling procedures

### 6.2 Developer Documentation
- [ ] 6.2.1 Document local development setup
- [ ] 6.2.2 Document snapshot API usage
- [ ] 6.2.3 Document tenant management API
- [ ] 6.2.4 Document infrastructure configuration options
