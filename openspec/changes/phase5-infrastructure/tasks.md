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
  - Builder stage: install Python dependencies in venv
  - Runtime stage: minimal Debian slim image with Loomworks
  - Include wkhtmltopdf for PDF generation
  - Install Node.js and rtlcss for RTL support
- [ ] 3.1.2 Configure entrypoint script
  - Wait for PostgreSQL availability
  - Generate config from environment variables
  - Run database migrations
  - Handle graceful shutdown
  - Support multiple commands (loomworks, shell, scaffold)
- [ ] 3.1.3 Add health check configuration
  - HTTP health endpoint on /web/health
  - Database connectivity check
  - Appropriate start period for Odoo initialization

### 3.2 Docker Compose Configuration
- [ ] 3.2.1 Create `docker-compose.yml`
  - Loomworks service with environment variables
  - PostgreSQL 15 with WAL configuration
  - Redis for session storage
  - Nginx reverse proxy
  - Network isolation
- [ ] 3.2.2 Configure PostgreSQL for PITR
  - Mount custom postgresql.conf
  - Volume for WAL archive storage
  - Volume for base backups
- [ ] 3.2.3 Create environment file template
  - Database credentials
  - Loomworks configuration options
  - AI API keys placeholder
  - Backup configuration

### 3.3 Docker Volumes and Persistence
- [ ] 3.3.1 Define volume structure
  - `loomworks_data` for filestore
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

### 4.2 Loomworks Deployment
- [ ] 4.2.1 Create Loomworks Deployment manifest
  - Multiple replicas for high availability
  - Rolling update strategy
  - Resource requests and limits
- [ ] 4.2.2 Configure ConfigMap for loomworks.conf
  - Database connection parameters
  - Worker configuration
  - Proxy mode settings
- [ ] 4.2.3 Create Secret for Loomworks credentials
  - Admin password
  - Database user credentials
  - AI API keys
- [ ] 4.2.4 Configure PersistentVolumeClaim for filestore
  - ReadWriteMany access mode
  - Shared across all Loomworks pods

### 4.3 Services and Ingress
- [ ] 4.3.1 Create ClusterIP Service for Loomworks
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
- [ ] 4.4.1 Create HorizontalPodAutoscaler for Loomworks
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
  - Loomworks metrics endpoint
  - PostgreSQL metrics via postgres_exporter
- [ ] 4.5.2 Configure logging
  - Structured JSON logging from Loomworks
  - Log aggregation configuration
- [ ] 4.5.3 Create alerting rules
  - Pod restart alerts
  - Database connection pool exhaustion
  - Disk space warnings for backup volumes

## 5. Fork Distribution Strategy (Weeks 47-48)

### 5.1 Repository Structure
- [ ] 5.1.1 Set up monorepo structure
  - Create `odoo/` directory for forked Odoo 18 core
  - Organize `loomworks_addons/` for custom modules
  - Create `infrastructure/` for deployment configs
- [ ] 5.1.2 Create VERSION file
  - Define LOOMWORKS_VERSION
  - Track ODOO_VERSION
  - Record ODOO_UPSTREAM_COMMIT
  - Set RELEASE_DATE
- [ ] 5.1.3 Initialize CHANGELOG.md
  - Follow Keep a Changelog format
  - Include sections: Added, Changed, Fixed, Security, Upstream Sync
- [ ] 5.1.4 Set up upstream tracking branch
  - Add Odoo as upstream remote
  - Create `upstream/odoo-18.0` branch
  - Document merge strategy

### 5.2 Versioning and Tagging
- [ ] 5.2.1 Implement version format
  - Format: `{major}.{minor}.{patch}+odoo{version}`
  - Example: `1.0.0+odoo18.0`
- [ ] 5.2.2 Create release tagging script
  - Read version from VERSION file
  - Create annotated tag
  - Generate release notes from CHANGELOG
- [ ] 5.2.3 Set up branch protection rules
  - Require PR reviews for main
  - Require CI to pass before merge
  - Prevent force pushes to main/develop

## 6. Package Distribution (Weeks 47-48)

### 6.1 Debian Package Build
- [ ] 6.1.1 Create Dockerfile.debian for build environment
  - Based on debian:bookworm
  - Install dpkg-dev, devscripts
- [ ] 6.1.2 Create debian/ directory structure
  - control file with package metadata
  - changelog file
  - conffiles for config preservation
  - postinst/prerm/postrm scripts
- [ ] 6.1.3 Create systemd service file
  - loomworks.service with security hardening
  - Proper user/group configuration
  - ReadWritePaths for data directories
- [ ] 6.1.4 Test deb package installation
  - Install on clean Ubuntu 22.04
  - Verify service starts correctly
  - Test upgrade path

### 6.2 RPM Package Build
- [ ] 6.2.1 Create Dockerfile.fedora for build environment
  - Based on fedora:latest
  - Install rpm-build, rpmdevtools
- [ ] 6.2.2 Create loomworks.spec file
  - Package metadata and dependencies
  - Build and install sections
  - Pre/post install scripts
- [ ] 6.2.3 Test rpm package installation
  - Install on clean Rocky Linux 9
  - Verify service starts correctly
  - Test upgrade path

### 6.3 Package Build Automation
- [ ] 6.3.1 Create infrastructure/packaging/build.py
  - Support deb, rpm, docker builds
  - Read version from VERSION file
  - Output to dist/ directory
- [ ] 6.3.2 Create Makefile for common operations
  - `make build-deb`
  - `make build-rpm`
  - `make build-docker`
  - `make build-all`

## 7. CI/CD Pipeline (Weeks 47-48)

### 7.1 GitHub Actions CI Workflow
- [ ] 7.1.1 Create .github/workflows/ci.yml
  - Trigger on push to main/develop and PRs
  - Path-based filtering for efficiency
- [ ] 7.1.2 Implement change detection job
  - Use dorny/paths-filter action
  - Detect odoo-core, loomworks-addons, infrastructure changes
- [ ] 7.1.3 Create lint job
  - Set up Python 3.11
  - Run Ruff for linting and formatting
  - Run mypy for type checking (non-blocking)
- [ ] 7.1.4 Create unit test job
  - Matrix for Python 3.10, 3.11, 3.12
  - PostgreSQL 15 service container
  - Run pytest with coverage
  - Upload to Codecov

### 7.2 Integration Testing
- [ ] 7.2.1 Create integration test job
  - Start Docker Compose stack
  - Wait for health check
  - Run integration tests
- [ ] 7.2.2 Collect and upload logs on failure
  - Docker compose logs
  - Test output artifacts

### 7.3 Docker Build Job
- [ ] 7.3.1 Create Docker build job
  - Set up Docker Buildx
  - Extract metadata for tagging
  - Build with layer caching
- [ ] 7.3.2 Push to GitHub Container Registry
  - Login with GITHUB_TOKEN
  - Push on main/release branches
  - Tag with version and sha

### 7.4 Package Build Job
- [ ] 7.4.1 Create package build job
  - Only on main/release branches
  - Matrix for deb/rpm formats
  - Upload as artifacts

### 7.5 Release Workflow
- [ ] 7.5.1 Create .github/workflows/release.yml
  - Trigger on version tags (v*)
  - Build multi-arch Docker images
  - Build deb and rpm packages
- [ ] 7.5.2 Create GitHub Release
  - Attach deb and rpm packages
  - Generate release notes
  - Mark pre-release for alpha/beta/rc

## 8. Upstream Update Management (Ongoing)

### 8.1 Upstream Sync Workflow
- [ ] 8.1.1 Create .github/workflows/upstream-sync.yml
  - Schedule: daily at 2 AM UTC
  - Manual trigger option
- [ ] 8.1.2 Implement update detection
  - Compare current and latest upstream commits
  - Check for security-related commits
- [ ] 8.1.3 Auto-create sync PR
  - Attempt merge with upstream
  - Flag conflicts for manual review
  - Add labels for security updates
- [ ] 8.1.4 Set up notifications
  - Slack webhook for security updates
  - Email to security team

### 8.2 Security Patch Process
- [ ] 8.2.1 Document security patch SLA
  - Critical: 4 hours response
  - High: 24 hours response
  - Medium/Low: include in scheduled release
- [ ] 8.2.2 Create hotfix release process
  - Branch from main for critical fixes
  - Fast-track testing and deployment
  - Notify all hosted customers

## 9. Multi-Tenant for Forked Core

### 9.1 Core Modifications
- [ ] 9.1.1 Implement TenantRouter in odoo/http.py
  - Subdomain extraction
  - Management database lookup
  - Tenant caching
- [ ] 9.1.2 Add tenant isolation checks in odoo/models.py
  - Check tenant on create/write/unlink
  - Audit cross-tenant access attempts
- [ ] 9.1.3 Add Loomworks-specific config options
  - loomworks_mgmt_db
  - loomworks_tenant_routing
  - loomworks_strict_isolation

### 9.2 Management Database
- [ ] 9.2.1 Create loomworks_mgmt database schema
  - loomworks_tenant table
  - Indexes for subdomain lookup
- [ ] 9.2.2 Implement tenant CRUD operations
  - Create tenant with database provisioning
  - Update tenant state
  - Archive/delete tenant

## 10. Testing and Verification

### 10.1 Unit Tests
- [ ] 10.1.1 Test tenant model CRUD operations
- [ ] 10.1.2 Test snapshot model CRUD operations
- [ ] 10.1.3 Test AI operation log recording
- [ ] 10.1.4 Test quota enforcement logic

### 10.2 Integration Tests
- [ ] 10.2.1 Test tenant provisioning workflow
- [ ] 10.2.2 Test subdomain routing with multiple tenants
- [ ] 10.2.3 Test snapshot creation and metadata capture
- [ ] 10.2.4 Test PITR restore to specific timestamp
- [ ] 10.2.5 Test granular undo of AI operations

### 10.3 Infrastructure Tests
- [ ] 10.3.1 Test Docker Compose stack startup
- [ ] 10.3.2 Test Kubernetes deployment rollout
- [ ] 10.3.3 Test HPA scaling behavior
- [ ] 10.3.4 Test backup and restore procedures
- [ ] 10.3.5 Test zero-downtime deployment

### 10.4 Security Tests
- [ ] 10.4.1 Test tenant database isolation
- [ ] 10.4.2 Test cross-tenant access prevention
- [ ] 10.4.3 Test backup encryption verification
- [ ] 10.4.4 Test credential rotation procedures

### 10.5 Distribution Tests
- [ ] 10.5.1 Test deb package on Ubuntu 22.04/24.04
- [ ] 10.5.2 Test rpm package on Rocky Linux 9
- [ ] 10.5.3 Test Docker image on clean system
- [ ] 10.5.4 Test upgrade from previous version

## 11. Documentation

### 11.1 Operations Documentation
- [ ] 11.1.1 Document tenant provisioning procedure
- [ ] 11.1.2 Document backup and restore procedures
- [ ] 11.1.3 Document disaster recovery runbook
- [ ] 11.1.4 Document scaling procedures

### 11.2 Developer Documentation
- [ ] 11.2.1 Document local development setup
- [ ] 11.2.2 Document snapshot API usage
- [ ] 11.2.3 Document tenant management API
- [ ] 11.2.4 Document infrastructure configuration options

### 11.3 Installation Documentation
- [ ] 11.3.1 Document Docker installation
  - Quick start with docker-compose
  - Production configuration guide
- [ ] 11.3.2 Document Debian/Ubuntu installation
  - Prerequisites and repository setup
  - Post-install configuration
- [ ] 11.3.3 Document RHEL/CentOS installation
  - Prerequisites and repository setup
  - SELinux considerations
- [ ] 11.3.4 Document Kubernetes deployment
  - Helm chart (future)
  - Manual manifest deployment

### 11.4 Contribution Documentation
- [ ] 11.4.1 Document contribution workflow
  - Fork, branch, PR process
  - Commit message conventions
- [ ] 11.4.2 Document upstream sync process
  - How to handle merge conflicts
  - Testing requirements
- [ ] 11.4.3 Document release process
  - Version bumping procedure
  - Changelog updates
  - Tag creation
