# Docker Infrastructure

Docker containerization for Loomworks ERP development and deployment.

## ADDED Requirements

### Requirement: Multi-Stage Dockerfile
The system SHALL provide a multi-stage Dockerfile that builds a minimal, secure production image for Odoo with Loomworks addons.

#### Scenario: Build production image
- **WHEN** the Dockerfile is built with `docker build -t loomworks/erp:latest .`
- **THEN** a production-ready image is created
- **AND** the image contains Odoo, Loomworks addons, and all Python dependencies
- **AND** build-time dependencies are not included in the final image

#### Scenario: Image size optimization
- **WHEN** the production image is built
- **THEN** the image size is less than 1GB
- **AND** only runtime dependencies are included

#### Scenario: Non-root user execution
- **WHEN** a container is started from the image
- **THEN** the Odoo process runs as a non-root user (uid 1000)
- **AND** file permissions are correctly set for the Odoo user

---

### Requirement: Container Health Checks
The system SHALL include health check configurations that verify application readiness.

#### Scenario: HTTP health check passes
- **WHEN** the Odoo application is running and healthy
- **THEN** the health check endpoint `/web/health` returns HTTP 200
- **AND** Docker marks the container as healthy

#### Scenario: Health check fails on startup
- **WHEN** the Odoo application is still initializing
- **THEN** the health check fails
- **AND** Docker waits for the start period before marking unhealthy

#### Scenario: Health check fails on database disconnect
- **WHEN** the database connection is lost
- **THEN** the health check fails
- **AND** Docker marks the container as unhealthy
- **AND** orchestration systems can restart the container

---

### Requirement: Entrypoint Script
The system SHALL provide an entrypoint script that handles initialization, configuration, and graceful shutdown.

#### Scenario: Wait for database availability
- **WHEN** the container starts before PostgreSQL is ready
- **THEN** the entrypoint script waits for PostgreSQL to accept connections
- **AND** retries with exponential backoff up to 60 seconds
- **AND** fails with a clear error if database is unavailable

#### Scenario: Apply database migrations
- **WHEN** the container starts with a new version
- **THEN** database migrations are applied automatically
- **AND** the migration status is logged

#### Scenario: Graceful shutdown
- **WHEN** the container receives SIGTERM
- **THEN** the entrypoint script initiates graceful shutdown
- **AND** in-progress requests are completed (up to 30 seconds)
- **AND** the process exits cleanly

---

### Requirement: Docker Compose Stack
The system SHALL provide a Docker Compose configuration that runs all required services for development and production.

#### Scenario: Start development stack
- **WHEN** `docker compose up` is executed
- **THEN** PostgreSQL, Redis, Odoo, and Nginx services start
- **AND** all services pass health checks
- **AND** the application is accessible at http://localhost:8069

#### Scenario: Service dependency ordering
- **WHEN** the stack starts
- **THEN** PostgreSQL starts and becomes healthy before Odoo starts
- **AND** Odoo starts and becomes healthy before Nginx starts

#### Scenario: Persistent data across restarts
- **WHEN** the stack is stopped and started again
- **THEN** database data is preserved
- **AND** Odoo filestore data is preserved
- **AND** WAL archives are preserved

---

### Requirement: PostgreSQL WAL Configuration
The system SHALL configure PostgreSQL for WAL archiving to support point-in-time recovery.

#### Scenario: WAL archiving enabled
- **WHEN** PostgreSQL container starts
- **THEN** WAL level is set to "replica"
- **AND** archive_mode is enabled
- **AND** archive_command compresses and copies WAL to archive volume

#### Scenario: Archive directory structure
- **WHEN** WAL segments are archived
- **THEN** segments are stored in `/wal_archive/` volume
- **AND** segments are compressed with gzip
- **AND** the naming convention is `{original_name}.gz`

#### Scenario: Archive timeout configuration
- **WHEN** PostgreSQL is configured
- **THEN** archive_timeout is set to 300 seconds (5 minutes)
- **AND** partial WAL segments are archived at the timeout interval

---

### Requirement: Environment Variable Configuration
The system SHALL support configuration via environment variables for all deployment-specific settings.

#### Scenario: Database connection configuration
- **WHEN** environment variables DB_HOST, DB_PORT, DB_USER, DB_PASSWORD are set
- **THEN** Odoo connects to the specified PostgreSQL instance
- **AND** no database credentials are hardcoded in configuration files

#### Scenario: Admin password configuration
- **WHEN** ODOO_ADMIN_PASSWD environment variable is set
- **THEN** the Odoo master password is configured
- **AND** the password is not logged or exposed

#### Scenario: Proxy mode configuration
- **WHEN** PROXY_MODE=True environment variable is set
- **THEN** Odoo trusts X-Forwarded-* headers from the reverse proxy
- **AND** correct client IPs are logged

#### Scenario: Default configuration values
- **WHEN** optional environment variables are not set
- **THEN** sensible defaults are used
- **AND** the application starts without errors

---

### Requirement: Volume Mounts for Persistence
The system SHALL define volume mounts that ensure data persistence across container restarts.

#### Scenario: PostgreSQL data persistence
- **WHEN** a named volume `postgres_data` is mounted to `/var/lib/postgresql/data`
- **THEN** database files persist across container restarts
- **AND** data survives container recreation

#### Scenario: Odoo filestore persistence
- **WHEN** a named volume `odoo_data` is mounted to `/var/lib/odoo`
- **THEN** uploaded files and attachments persist
- **AND** session data persists

#### Scenario: WAL archive persistence
- **WHEN** a named volume `wal_archive` is mounted to `/wal_archive`
- **THEN** WAL segments persist for point-in-time recovery
- **AND** archives survive container and host restarts

---

### Requirement: Development Override Configuration
The system SHALL provide a development-specific Docker Compose override for live code reloading.

#### Scenario: Live code mounting
- **WHEN** docker-compose.dev.yml is used
- **THEN** local source directories are mounted into the container
- **AND** code changes are reflected without rebuilding the image

#### Scenario: Debug port exposure
- **WHEN** docker-compose.dev.yml is used
- **THEN** port 5678 is exposed for debugger attachment
- **AND** developers can attach debugpy for remote debugging

#### Scenario: Relaxed resource limits
- **WHEN** docker-compose.dev.yml is used
- **THEN** no CPU or memory limits are enforced
- **AND** developers have full system resources available

---

### Requirement: Nginx Reverse Proxy Configuration
The system SHALL provide Nginx configuration for SSL termination and subdomain routing.

#### Scenario: SSL termination
- **WHEN** a request arrives on port 443
- **THEN** Nginx terminates SSL
- **AND** forwards the request to Odoo over HTTP

#### Scenario: Subdomain routing
- **WHEN** a request arrives for "acme.loomworks.app"
- **THEN** the Host header is passed to Odoo
- **AND** Odoo's dbfilter routes to the correct database

#### Scenario: WebSocket support for longpolling
- **WHEN** a WebSocket connection is initiated to /longpolling
- **THEN** Nginx upgrades the connection
- **AND** forwards to Odoo port 8072
- **AND** maintains the persistent connection

#### Scenario: Request size limits
- **WHEN** a file upload exceeds 100MB
- **THEN** Nginx rejects the request with 413 error
- **AND** a clear error message is returned
