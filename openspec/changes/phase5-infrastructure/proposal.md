# Change: Phase 5 - Hosting Infrastructure and Snapshots

## Why

Loomworks ERP's revenue model depends on hosted database services with AI rollback capabilities. Users must be able to undo AI mistakes without data loss, requiring robust snapshot and point-in-time recovery infrastructure. Multi-tenancy enables efficient resource utilization and scalable hosting across customers. This phase establishes the complete infrastructure layer that powers the hosted SaaS offering.

## What Changes

### Multi-Tenant Architecture
- **NEW** `loomworks.tenant` model for database, subdomain, and resource limit management
- **NEW** Database-per-tenant isolation architecture with subdomain routing
- **NEW** Tenant provisioning and lifecycle management workflows
- **NEW** Resource quota enforcement (users, storage, AI operations)
- **NEW** Subdomain-based database routing via `dbfilter` configuration

### Snapshot System (loomworks_snapshot module)
- **NEW** `loomworks.snapshot` model for snapshot metadata and WAL positions
- **NEW** `ai.operation.log` model for granular AI operation tracking
- **NEW** PostgreSQL WAL archiving configuration for PITR
- **NEW** Snapshot creation workflow (auto/manual/pre-AI triggers)
- **NEW** Point-in-time restore process with tenant isolation
- **NEW** Granular undo capability for individual AI operations

### Docker Infrastructure
- **NEW** Multi-stage Dockerfile for Odoo + Loomworks
- **NEW** `docker-compose.yml` with PostgreSQL WAL configuration
- **NEW** Environment variable configuration for all components
- **NEW** Volume mounts for data persistence and WAL archiving
- **NEW** Health check configuration for all services

### Kubernetes Infrastructure
- **NEW** StatefulSet manifests for PostgreSQL with persistent storage
- **NEW** Deployment manifests for Odoo application tier
- **NEW** Service and Ingress configurations with subdomain routing
- **NEW** PersistentVolumeClaim templates for data and WAL archives
- **NEW** HorizontalPodAutoscaler for application scaling
- **NEW** ConfigMaps and Secrets for configuration management

## Impact

- Affected specs:
  - `loomworks-tenant` (new capability)
  - `loomworks-snapshot` (new capability)
  - `infrastructure-docker` (new capability)
  - `infrastructure-kubernetes` (new capability)
- Affected code:
  - `/loomworks_addons/loomworks_tenant/` (new module)
  - `/loomworks_addons/loomworks_snapshot/` (new module)
  - `/infrastructure/docker/` (new directory)
  - `/infrastructure/kubernetes/` (new directory)
- Dependencies:
  - Requires Phase 2 AI Integration (`loomworks_ai` module) for operation logging
  - PostgreSQL 15+ with WAL archiving support
  - Docker 24+ and Kubernetes 1.28+

## Technical Architecture Overview

### Multi-Tenancy Strategy: Database-Per-Tenant

After evaluating multi-tenant patterns, database-per-tenant is selected for:
1. **Complete data isolation** - Critical for enterprise customers and compliance
2. **Independent backup/restore** - Each tenant can be restored without affecting others
3. **Odoo compatibility** - Odoo natively supports multiple databases
4. **Performance isolation** - Heavy tenants don't impact others
5. **Flexible scaling** - Large tenants can migrate to dedicated resources

Trade-offs accepted:
- Higher infrastructure cost per tenant (mitigated by resource pooling)
- More complex provisioning (automated via tenant management module)
- Connection pooling complexity (solved with PgBouncer)

### Snapshot Strategy: WAL-Based PITR with Granular Undo

Two-tier approach:
1. **Full PITR** - PostgreSQL WAL archiving for disaster recovery
2. **Granular Undo** - Operation log replay for AI mistake correction

This hybrid approach provides:
- Fast rollback for small AI mistakes (< 1 second)
- Complete database recovery for catastrophic failures
- Audit trail of all AI operations
- Compliance with data retention requirements

### Backup Targets

| Metric | Target | Justification |
|--------|--------|---------------|
| RPO (Recovery Point Objective) | 5 minutes | WAL archive_timeout setting |
| RTO (Recovery Time Objective) | 15 minutes | Base backup + WAL replay |
| Snapshot Retention | 30 days | Balance storage cost with recovery needs |
| AI Operation Log Retention | 90 days | Audit compliance and debugging |

## Scope

This proposal covers **Phase 5 (Weeks 39-46)** of the implementation plan:

1. **Weeks 39-40**: Multi-tenant architecture and `loomworks_tenant` module
2. **Weeks 41-42**: Snapshot system and `loomworks_snapshot` module
3. **Weeks 43-44**: Docker infrastructure with WAL configuration
4. **Weeks 45-46**: Kubernetes deployment and autoscaling

## Success Criteria

1. Tenant databases are fully isolated with no cross-tenant data access
2. Subdomain routing correctly maps `tenant.loomworks.app` to tenant database
3. Snapshots capture consistent database state with WAL position
4. PITR restore recovers database to any point within retention window
5. Granular undo can reverse specific AI operations without full restore
6. Docker Compose stack starts and runs all services with health checks passing
7. Kubernetes deployment handles rolling updates with zero downtime
8. HPA scales pods based on CPU/memory utilization
9. All tests pass including multi-tenant isolation verification

## Security Considerations

### Tenant Isolation
- Database-level isolation prevents SQL injection across tenants
- Connection credentials are tenant-specific
- dbfilter prevents tenant from accessing other databases
- Network policies restrict inter-pod communication in Kubernetes

### Credential Management
- All secrets stored in Kubernetes Secrets or external vault
- Database passwords generated with cryptographic randomness
- API keys rotated on configurable schedule
- Audit logging for all administrative operations

### Backup Security
- WAL archives encrypted at rest
- Base backups stored with tenant-specific encryption keys
- Restore operations require elevated permissions
- Backup access logged and monitored

## References

- [PostgreSQL PITR Documentation](https://www.postgresql.org/docs/current/continuous-archiving.html)
- [Multi-Tenant Database Architecture Patterns](https://www.bytebase.com/blog/multi-tenant-database-architecture-patterns-explained/)
- [Odoo Multi-Database Deployment](https://www.odoo.com/documentation/19.0/administration/on_premise/deploy.html)
- [Kubernetes StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
- [Docker Multi-Stage Builds](https://docs.docker.com/build/building/multi-stage/)
