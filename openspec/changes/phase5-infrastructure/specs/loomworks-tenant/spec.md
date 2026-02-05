# Loomworks Tenant Management

Multi-tenant hosting management for Loomworks ERP SaaS platform.

## ADDED Requirements

### Requirement: Tenant Model
The system SHALL provide a `loomworks.tenant` model that stores tenant configuration including database name, subdomain, resource limits, and subscription tier.

#### Scenario: Create tenant record
- **WHEN** an administrator creates a new tenant with name "Acme Corp", subdomain "acme", and tier "pro"
- **THEN** a `loomworks.tenant` record is created with state "draft"
- **AND** database_name is auto-generated as "loomworks_acme"

#### Scenario: Validate subdomain uniqueness
- **WHEN** an administrator attempts to create a tenant with subdomain "acme" that already exists
- **THEN** a validation error is raised indicating the subdomain is already in use

#### Scenario: Validate subdomain format
- **WHEN** an administrator attempts to create a tenant with subdomain "Acme-Corp!" (invalid characters)
- **THEN** a validation error is raised indicating subdomain must be lowercase alphanumeric with hyphens only

---

### Requirement: Tenant Provisioning
The system SHALL provide a provisioning workflow that creates the tenant database, installs required modules, and creates the initial admin user.

#### Scenario: Provision new tenant
- **WHEN** an administrator triggers provisioning for a tenant in "draft" state
- **THEN** a new PostgreSQL database is created with the tenant's database_name
- **AND** core Loomworks modules are installed in the new database
- **AND** an admin user is created with the specified credentials
- **AND** the tenant state transitions to "active"

#### Scenario: Provisioning failure handling
- **WHEN** database creation fails during provisioning
- **THEN** the tenant state transitions to "failed"
- **AND** an error message is logged with the failure reason
- **AND** any partially created resources are cleaned up

---

### Requirement: Subdomain Routing
The system SHALL route HTTP requests to the correct tenant database based on the subdomain in the request URL.

#### Scenario: Route request by subdomain
- **WHEN** a user accesses "https://acme.loomworks.app"
- **THEN** Odoo connects to the "loomworks_acme" database
- **AND** the user sees the Acme Corp instance

#### Scenario: Unknown subdomain returns error
- **WHEN** a user accesses "https://unknown.loomworks.app" where no tenant exists
- **THEN** a 404 error page is displayed indicating the tenant was not found

#### Scenario: Suspended tenant access denied
- **WHEN** a user accesses a subdomain for a tenant in "suspended" state
- **THEN** a 403 error page is displayed indicating the account is suspended
- **AND** contact information for support is provided

---

### Requirement: Resource Limits
The system SHALL enforce configurable resource limits per tenant including maximum users, storage size, and daily AI operations.

#### Scenario: User limit enforcement
- **WHEN** a tenant has max_users=10 and attempts to create an 11th user
- **THEN** the user creation is blocked
- **AND** an error message indicates the user limit has been reached

#### Scenario: Storage quota warning
- **WHEN** a tenant's database size reaches 80% of max_storage_gb
- **THEN** a warning notification is sent to the tenant administrator
- **AND** a warning banner is displayed in the UI

#### Scenario: Storage quota enforcement
- **WHEN** a tenant's database size exceeds max_storage_gb
- **THEN** write operations that increase storage are blocked
- **AND** read operations continue to function normally

#### Scenario: AI operation rate limiting
- **WHEN** a tenant has used all daily AI operations (max_ai_operations_daily)
- **THEN** new AI operations are blocked until the next day
- **AND** a message indicates the daily limit has been reached
- **AND** the counter resets at midnight UTC

---

### Requirement: Tenant Lifecycle Management
The system SHALL support tenant state transitions including suspension, archival, and destruction with appropriate data retention.

#### Scenario: Suspend tenant
- **WHEN** an administrator suspends an active tenant
- **THEN** the tenant state transitions to "suspended"
- **AND** users can no longer log in
- **AND** all data is preserved

#### Scenario: Resume suspended tenant
- **WHEN** an administrator resumes a suspended tenant
- **THEN** the tenant state transitions to "active"
- **AND** users can log in normally

#### Scenario: Archive tenant
- **WHEN** an administrator archives a tenant
- **THEN** the tenant state transitions to "archived"
- **AND** a final backup is created
- **AND** active database connections are terminated
- **AND** the database is renamed with "_archived_YYYYMMDD" suffix

#### Scenario: Destroy archived tenant
- **WHEN** an administrator destroys an archived tenant after the retention period
- **THEN** the database is permanently deleted
- **AND** all backups are removed
- **AND** the tenant record is deleted

---

### Requirement: Tenant Security Access Control
The system SHALL restrict tenant management operations based on user roles with appropriate audit logging.

#### Scenario: Tenant admin can view own tenant
- **WHEN** a user with tenant_user role accesses the tenant management portal
- **THEN** they can view only their own tenant record
- **AND** they cannot view other tenant records

#### Scenario: Platform admin can manage all tenants
- **WHEN** a user with tenant_admin role accesses the tenant management portal
- **THEN** they can view and manage all tenant records

#### Scenario: Audit logging for tenant operations
- **WHEN** any tenant lifecycle operation is performed (create, suspend, archive, destroy)
- **THEN** an audit log entry is created with operator, timestamp, and operation details
