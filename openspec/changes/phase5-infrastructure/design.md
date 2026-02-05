# Phase 5: Hosting Infrastructure and Snapshots - Technical Design

## Context

Loomworks ERP requires a production-grade hosting infrastructure that supports:
1. Multi-tenant isolation for SaaS hosting
2. Database snapshots for AI rollback capabilities
3. Containerized deployment for cloud portability
4. Horizontal scaling for high availability

This design document captures the key technical decisions, alternatives considered, and implementation patterns for Phase 5.

## Stakeholders

- **End Users**: Need reliable undo capability for AI mistakes
- **Tenant Admins**: Need self-service database management
- **Platform Operators**: Need efficient multi-tenant management
- **Developers**: Need local development environment parity

## Goals / Non-Goals

### Goals
- Complete tenant isolation with no data leakage
- Sub-30-second snapshot creation
- Sub-15-minute PITR restore for any point in retention window
- Zero-downtime deployments and scaling
- Local development environment that mirrors production

### Non-Goals
- Multi-region active-active replication (future enhancement)
- Real-time streaming replication to standby (Phase 6+)
- Tenant database migration between clusters
- Custom PostgreSQL extensions per tenant

---

## Module Dependencies

### loomworks_tenant Module

```python
# __manifest__.py
{
    'name': 'Loomworks Tenant Management',
    'version': '18.0.1.0.0',
    'depends': ['loomworks_core'],
    'license': 'LGPL-3',
}
```

### loomworks_snapshot Module

```python
# __manifest__.py
{
    'name': 'Loomworks Database Snapshots',
    'version': '18.0.1.0.0',
    'depends': [
        'loomworks_tenant',
        'loomworks_ai',  # Required: extends loomworks.ai.operation.log model
    ],
    'license': 'LGPL-3',
}
```

**Dependency Rationale:**
- `loomworks_tenant`: Required for tenant isolation and database management
- `loomworks_ai`: **Required** - The snapshot module extends `loomworks.ai.operation.log` (defined in Phase 2) to add `snapshot_id` field for PITR integration. This creates the bridge between granular AI operation rollback and full database Point-in-Time Recovery.

---

## Decision 1: Multi-Tenancy Architecture

### Decision
Use **database-per-tenant** architecture with shared application tier.

### Alternatives Considered

| Pattern | Pros | Cons |
|---------|------|------|
| **Shared Schema (tenant_id column)** | Low cost, simple deployment | No isolation, noisy neighbor, compliance issues |
| **Schema-Per-Tenant** | Good isolation, moderate cost | Migration complexity, PostgreSQL schema limits |
| **Database-Per-Tenant** | Complete isolation, independent backups | Higher cost, connection management |

### Rationale

1. **Odoo Native Support**: Odoo's `dbfilter` mechanism natively supports database-per-tenant routing
2. **Isolation Requirements**: Enterprise customers require complete data isolation for compliance
3. **Independent Backups**: Each tenant can be restored independently without affecting others
4. **AI Rollback**: Snapshots can target individual tenant databases
5. **Performance Isolation**: Heavy tenant workloads don't impact others

### Trade-offs Accepted
- Higher infrastructure cost (~$5-10/tenant/month for database resources)
- Connection pooling complexity (mitigated with PgBouncer)
- More complex provisioning automation (worth the isolation benefits)

### Implementation Pattern

```python
# loomworks_tenant/models/tenant.py
class LoomworksTenant(models.Model):
    _name = "loomworks.tenant"
    _description = "Loomworks Tenant"

    name = fields.Char(required=True)
    database_name = fields.Char(required=True, readonly=True)
    subdomain = fields.Char(required=True, index=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('provisioning', 'Provisioning'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('archived', 'Archived'),
    ], default='draft')

    # Resource Limits
    max_users = fields.Integer(default=10)
    max_storage_gb = fields.Float(default=5.0)
    max_ai_operations_daily = fields.Integer(default=100)

    # Billing
    tier = fields.Selection([
        ('basic', 'Basic'),
        ('pro', 'Pro'),
        ('enterprise', 'Enterprise'),
    ], default='basic')
    subscription_expires = fields.Date()

    # Relationships
    snapshot_ids = fields.One2many('loomworks.snapshot', 'tenant_id')

    @api.constrains('subdomain')
    def _check_subdomain(self):
        for record in self:
            if not re.match(r'^[a-z][a-z0-9-]{2,62}$', record.subdomain):
                raise ValidationError("Subdomain must be lowercase alphanumeric, 3-63 chars, start with letter")
```

---

## Decision 2: Snapshot Strategy

### Decision
Use **hybrid WAL-based PITR with granular operation logging** for two-tier rollback.

### Alternatives Considered

| Strategy | Pros | Cons |
|----------|------|------|
| **pg_dump snapshots** | Simple, portable | Slow for large DBs, no PITR |
| **WAL-only PITR** | Fine-grained recovery | Requires full restore for any rollback |
| **Logical replication** | Selective sync | Complex, not point-in-time |
| **Hybrid (WAL + operation log)** | Fast granular undo + full PITR | Two systems to maintain |

### Rationale

1. **Fast Undo**: Most AI mistakes are small (few records) - operation log provides instant rollback
2. **Disaster Recovery**: WAL PITR handles catastrophic failures and corruption
3. **Audit Trail**: Operation log provides compliance-ready audit history
4. **User Experience**: Sub-second undo for common cases, < 15 min for full restore

### Implementation Pattern

```python
# loomworks_snapshot/models/snapshot.py
class LoomworksSnapshot(models.Model):
    _name = "loomworks.snapshot"
    _description = "Database Snapshot"

    tenant_id = fields.Many2one('loomworks.tenant', required=True, ondelete='cascade')
    name = fields.Char(required=True)
    created_at = fields.Datetime(default=fields.Datetime.now, readonly=True)
    state = fields.Selection([
        ('creating', 'Creating'),
        ('ready', 'Ready'),
        ('restoring', 'Restoring'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    ], default='creating')

    # PITR Data
    wal_position = fields.Char(help="PostgreSQL LSN at snapshot time")
    wal_file = fields.Char(help="WAL segment file name")
    base_backup_id = fields.Char(help="Associated base backup identifier")

    snapshot_type = fields.Selection([
        ('auto', 'Automatic'),
        ('manual', 'Manual'),
        ('pre_ai', 'Pre-AI Operation'),
    ], required=True)

    # Metadata
    size_bytes = fields.Integer(compute='_compute_size')
    expires_at = fields.Datetime()

    def action_create_snapshot(self):
        """Create snapshot by capturing current WAL position."""
        self.ensure_one()
        # Get current WAL position
        self.env.cr.execute("SELECT pg_current_wal_lsn()")
        lsn = self.env.cr.fetchone()[0]
        self.write({
            'wal_position': str(lsn),
            'state': 'ready',
        })


# loomworks_snapshot/models/ai_operation_log.py
#
# NOTE: This module EXTENDS the `loomworks.ai.operation.log` model defined in
# Phase 2 (loomworks_ai). The canonical model definition lives in Phase 2.
# This extension adds snapshot integration fields for PITR rollback capability.
#
# Model Ownership: Phase 2 (loomworks_ai) owns `loomworks.ai.operation.log`
# This Extension: Phase 5 (loomworks_snapshot) adds snapshot_id for PITR integration
#
# Dependency Chain: loomworks_snapshot depends on loomworks_ai
#
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

    This extension adds:
    - snapshot_id: Links to pre-operation PITR snapshot for disaster recovery
    - undone, undone_at: Granular undo tracking
    - action_undo(): Method for single-operation rollback
    """
    _inherit = 'loomworks.ai.operation.log'

    # Snapshot integration for PITR rollback
    snapshot_id = fields.Many2one(
        'loomworks.snapshot',
        string='Pre-Operation Snapshot',
        help="PITR snapshot taken before this operation for disaster recovery"
    )

    # Granular undo tracking (extends base state field)
    undone = fields.Boolean(
        string='Undone',
        default=False,
        help="Whether this operation has been reversed"
    )
    undone_at = fields.Datetime(
        string='Undone At',
        help="Timestamp when operation was reversed"
    )

    def action_undo(self):
        """
        Undo this operation by restoring previous values.

        This provides granular single-operation rollback without requiring
        full PITR restore. For catastrophic failures, use snapshot restore.

        Returns:
            bool: True if undo succeeded

        Raises:
            UserError: If operation already undone or undo not possible
        """
        self.ensure_one()
        if self.undone:
            raise UserError("Operation already undone")

        # Use model_name field from base class (Phase 2)
        Model = self.env[self.model_name]
        record_ids = json.loads(self.record_ids) if self.record_ids else []
        values_before = json.loads(self.values_before) if self.values_before else {}

        if self.operation_type == 'create':
            # Delete created records
            Model.browse(record_ids).unlink()
        elif self.operation_type in ('write', 'update'):
            # Restore previous values
            for rec_id, vals in values_before.items():
                Model.browse(int(rec_id)).write(vals)
        elif self.operation_type in ('unlink', 'delete'):
            # Re-create deleted records
            for rec_id, vals in values_before.items():
                Model.create(vals)

        self.write({
            'undone': True,
            'undone_at': fields.Datetime.now(),
            'state': 'rolled_back',  # Update base state field
        })
        return True
```

### WAL Configuration

```ini
# postgresql.conf for PITR
wal_level = replica
archive_mode = on
archive_command = 'gzip < %p > /wal_archive/%f.gz && test -f /wal_archive/%f.gz'
archive_timeout = 300
max_wal_senders = 3
wal_keep_size = 1GB
```

---

## Decision 3: Docker Image Architecture

### Decision
Use **multi-stage build** with Alpine-based Python image for minimal footprint.

### Implementation Pattern

```dockerfile
# infrastructure/docker/Dockerfile
#syntax=docker/dockerfile:1

# === Build stage: Install dependencies ===
FROM python:3.10-alpine AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/venv/bin:$PATH"

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    postgresql-dev \
    libffi-dev \
    libxml2-dev \
    libxslt-dev \
    jpeg-dev \
    zlib-dev

# Create virtual environment and install dependencies
RUN python -m venv /app/venv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# === Runtime stage: Minimal image ===
FROM python:3.10-alpine

ENV PYTHONUNBUFFERED=1
ENV PATH="/app/venv/bin:$PATH"
ENV ODOO_RC=/etc/odoo/odoo.conf

WORKDIR /app

# Install runtime dependencies
RUN apk add --no-cache \
    postgresql-client \
    libxml2 \
    libxslt \
    jpeg \
    wkhtmltopdf \
    fontconfig \
    ttf-dejavu \
    && adduser -D -u 1000 odoo

# Copy virtual environment from builder
COPY --from=builder /app/venv /app/venv

# Copy Odoo and Loomworks addons
COPY --chown=odoo:odoo odoo /app/odoo
COPY --chown=odoo:odoo loomworks_addons /app/loomworks_addons
COPY --chown=odoo:odoo infrastructure/docker/entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh && mkdir -p /var/lib/odoo /etc/odoo && chown odoo:odoo /var/lib/odoo /etc/odoo

USER odoo

EXPOSE 8069 8072

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:8069/web/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["odoo"]
```

### Docker Compose Configuration

```yaml
# infrastructure/docker/docker-compose.yml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-odoo}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-odoo}
      POSTGRES_DB: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - wal_archive:/wal_archive
      - ./postgresql.conf:/etc/postgresql/postgresql.conf:ro
    command: >
      postgres
      -c config_file=/etc/postgresql/postgresql.conf
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-odoo}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  odoo:
    build:
      context: ../..
      dockerfile: infrastructure/docker/Dockerfile
    depends_on:
      db:
        condition: service_healthy
    environment:
      - DB_HOST=db
      - DB_PORT=5432
      - DB_USER=${POSTGRES_USER:-odoo}
      - DB_PASSWORD=${POSTGRES_PASSWORD:-odoo}
      - ODOO_ADMIN_PASSWD=${ODOO_ADMIN_PASSWD:-admin}
      - PROXY_MODE=True
    volumes:
      - odoo_data:/var/lib/odoo
    ports:
      - "8069:8069"
      - "8072:8072"
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:8069/web/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    depends_on:
      - odoo
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    ports:
      - "80:80"
      - "443:443"
    restart: unless-stopped

volumes:
  postgres_data:
  wal_archive:
  odoo_data:
  redis_data:
```

---

## Decision 4: Kubernetes Architecture

### Decision
Use **StatefulSet for PostgreSQL** and **Deployment for Odoo** with shared filestore PVC.

### Rationale

1. **PostgreSQL**: StatefulSet provides stable network identities and persistent storage ordering
2. **Odoo**: Stateless Deployment allows horizontal scaling and rolling updates
3. **Filestore**: Shared PVC with ReadWriteMany enables consistent file access across pods

### Implementation Pattern

```yaml
# infrastructure/kubernetes/postgres-statefulset.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: loomworks
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: postgres:15-alpine
          ports:
            - containerPort: 5432
          envFrom:
            - secretRef:
                name: postgres-credentials
          volumeMounts:
            - name: postgres-data
              mountPath: /var/lib/postgresql/data
            - name: wal-archive
              mountPath: /wal_archive
            - name: postgres-config
              mountPath: /etc/postgresql/postgresql.conf
              subPath: postgresql.conf
          resources:
            requests:
              cpu: "500m"
              memory: "1Gi"
            limits:
              cpu: "2000m"
              memory: "4Gi"
          livenessProbe:
            exec:
              command: ["pg_isready", "-U", "odoo"]
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            exec:
              command: ["pg_isready", "-U", "odoo"]
            initialDelaySeconds: 5
            periodSeconds: 5
      volumes:
        - name: postgres-config
          configMap:
            name: postgres-config
  volumeClaimTemplates:
    - metadata:
        name: postgres-data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 100Gi
    - metadata:
        name: wal-archive
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 50Gi
```

```yaml
# infrastructure/kubernetes/odoo-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: odoo
  namespace: loomworks
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: odoo
  template:
    metadata:
      labels:
        app: odoo
    spec:
      containers:
        - name: odoo
          image: loomworks/erp:latest
          ports:
            - containerPort: 8069
            - containerPort: 8072
          envFrom:
            - configMapRef:
                name: odoo-config
            - secretRef:
                name: odoo-credentials
          volumeMounts:
            - name: filestore
              mountPath: /var/lib/odoo
          resources:
            requests:
              cpu: "500m"
              memory: "1Gi"
            limits:
              cpu: "2000m"
              memory: "4Gi"
          livenessProbe:
            httpGet:
              path: /web/health
              port: 8069
            initialDelaySeconds: 60
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /web/health
              port: 8069
            initialDelaySeconds: 30
            periodSeconds: 10
      volumes:
        - name: filestore
          persistentVolumeClaim:
            claimName: odoo-filestore
```

```yaml
# infrastructure/kubernetes/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: odoo-hpa
  namespace: loomworks
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: odoo
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15
```

```yaml
# infrastructure/kubernetes/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: loomworks-ingress
  namespace: loomworks
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"
    nginx.ingress.kubernetes.io/websocket-services: "odoo"
spec:
  tls:
    - hosts:
        - "*.loomworks.app"
        - "loomworks.app"
      secretName: loomworks-tls
  rules:
    - host: "*.loomworks.app"
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: odoo
                port:
                  number: 8069
          - path: /longpolling
            pathType: Prefix
            backend:
              service:
                name: odoo
                port:
                  number: 8072
```

---

## Risks / Trade-offs

### Risk 1: Database Connection Exhaustion
- **Risk**: Database-per-tenant can exhaust PostgreSQL connections
- **Mitigation**: Deploy PgBouncer for connection pooling (future phase)
- **Monitoring**: Alert on connection pool utilization > 80%

### Risk 2: WAL Archive Storage Growth
- **Risk**: High-transaction tenants can generate large WAL archives
- **Mitigation**: Compress archives, enforce retention policies, monitor growth
- **Capacity**: Plan for 1GB WAL/day/active tenant

### Risk 3: Restore Time for Large Databases
- **Risk**: Large tenant databases may exceed 15-minute RTO
- **Mitigation**: More frequent base backups for large tenants, parallel WAL replay
- **Monitoring**: Test restore times monthly, alert if RTO trending up

### Risk 4: Shared Filestore Conflicts
- **Risk**: ReadWriteMany PVC providers have varying reliability
- **Mitigation**: Use proven storage classes (EFS, NFS-based), consider per-tenant PVCs for enterprise
- **Fallback**: Migrate to S3-compatible object storage for filestore

---

## Migration Plan

### Phase 5a: Local Docker (Weeks 43-44)
1. Deploy Docker Compose stack locally
2. Validate WAL archiving and snapshot creation
3. Test PITR restore procedure
4. Document development workflow

### Phase 5b: Kubernetes Staging (Week 45)
1. Deploy to staging Kubernetes cluster
2. Validate StatefulSet persistence
3. Test rolling updates with zero downtime
4. Validate HPA scaling behavior

### Phase 5c: Production Deployment (Week 46)
1. Deploy to production cluster
2. Migrate existing development data
3. Enable monitoring and alerting
4. Document runbooks for operations team

### Rollback Plan
- Keep previous deployment available for 7 days
- Database can be restored from most recent backup
- Kubernetes Deployment allows instant rollback with `kubectl rollout undo`

---

## Open Questions

1. **PgBouncer**: Should we include PgBouncer in Phase 5 or defer to Phase 6?
   - Recommendation: Defer unless connection limits become an issue

2. **Backup Encryption**: What encryption standard for at-rest backup encryption?
   - Recommendation: AES-256-GCM with tenant-specific keys stored in Vault

3. **Multi-Region**: When should we plan for multi-region deployment?
   - Recommendation: Phase 7+ after initial production validation

4. **Object Storage**: Should filestore use S3-compatible storage instead of PVC?
   - Recommendation: Start with PVC, migrate to S3 if scaling issues arise
