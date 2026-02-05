# Kubernetes Infrastructure

Kubernetes deployment manifests for production Loomworks ERP hosting.

## ADDED Requirements

### Requirement: PostgreSQL StatefulSet
The system SHALL deploy PostgreSQL as a StatefulSet with persistent storage for data durability and stable network identity.

#### Scenario: StatefulSet creation
- **WHEN** the PostgreSQL StatefulSet manifest is applied
- **THEN** a single PostgreSQL pod is created
- **AND** the pod has a stable network identity (postgres-0)
- **AND** persistent volumes are created for data and WAL archive

#### Scenario: Pod restart with data preservation
- **WHEN** the PostgreSQL pod is deleted or crashes
- **THEN** the StatefulSet recreates the pod
- **AND** the pod attaches to the existing persistent volumes
- **AND** all data is preserved

#### Scenario: Resource limits enforcement
- **WHEN** PostgreSQL pod runs
- **THEN** CPU is limited to 2000m
- **AND** memory is limited to 4Gi
- **AND** resource requests ensure scheduling on appropriate nodes

---

### Requirement: PostgreSQL Health Probes
The system SHALL configure liveness and readiness probes for PostgreSQL to enable automatic recovery.

#### Scenario: Readiness probe success
- **WHEN** PostgreSQL accepts connections
- **THEN** the readiness probe passes
- **AND** the pod receives traffic via the Service

#### Scenario: Liveness probe failure recovery
- **WHEN** PostgreSQL becomes unresponsive
- **THEN** the liveness probe fails after configured retries
- **AND** Kubernetes restarts the pod
- **AND** the pod recovers and becomes ready

---

### Requirement: Odoo Deployment
The system SHALL deploy Odoo as a Deployment with multiple replicas for high availability.

#### Scenario: Deployment creation
- **WHEN** the Odoo Deployment manifest is applied
- **THEN** the specified number of replicas are created (default: 2)
- **AND** pods are distributed across available nodes

#### Scenario: Rolling update with zero downtime
- **WHEN** the Deployment image is updated
- **THEN** pods are updated one at a time (maxSurge: 1, maxUnavailable: 0)
- **AND** new pods must pass readiness probes before old pods are terminated
- **AND** users experience no downtime

#### Scenario: Rollback on failed deployment
- **WHEN** a new deployment fails readiness probes
- **THEN** the rollout is paused after max retry attempts
- **AND** the previous version continues serving traffic
- **AND** an alert is triggered for the operations team

---

### Requirement: Shared Filestore PersistentVolumeClaim
The system SHALL provide a shared PersistentVolumeClaim for Odoo filestore accessible by all replicas.

#### Scenario: ReadWriteMany access
- **WHEN** the filestore PVC is created
- **THEN** the access mode is ReadWriteMany
- **AND** all Odoo pods can read and write to the volume

#### Scenario: File upload consistency
- **WHEN** a file is uploaded through one Odoo pod
- **THEN** the file is immediately visible to all other pods
- **AND** no data loss occurs during pod restarts

---

### Requirement: ConfigMaps and Secrets
The system SHALL store configuration in ConfigMaps and credentials in Secrets with appropriate access controls.

#### Scenario: Odoo configuration via ConfigMap
- **WHEN** the odoo-config ConfigMap is created
- **THEN** it contains non-sensitive configuration (worker count, proxy mode, etc.)
- **AND** pods mount the ConfigMap as environment variables

#### Scenario: Database credentials via Secret
- **WHEN** the postgres-credentials Secret is created
- **THEN** it contains the database password
- **AND** the Secret is base64 encoded
- **AND** only authorized pods can access the Secret

#### Scenario: Secret rotation
- **WHEN** a Secret is updated
- **THEN** pods using the Secret are restarted to pick up changes
- **AND** the rotation is logged for audit

---

### Requirement: Kubernetes Services
The system SHALL provide Service resources for internal service discovery and external access.

#### Scenario: Odoo ClusterIP Service
- **WHEN** the Odoo Service is created
- **THEN** it exposes ports 8069 (HTTP) and 8072 (longpolling)
- **AND** internal pods can reach Odoo via the service DNS name

#### Scenario: PostgreSQL Headless Service
- **WHEN** the PostgreSQL headless Service is created
- **THEN** DNS returns the pod IP directly
- **AND** clients can connect to specific pods by name (postgres-0.postgres)

---

### Requirement: Ingress with Wildcard Subdomain Routing
The system SHALL provide an Ingress resource that routes wildcard subdomains to the Odoo service.

#### Scenario: Wildcard subdomain routing
- **WHEN** a request arrives for "*.loomworks.app"
- **THEN** the Ingress routes to the Odoo service
- **AND** the Host header is preserved for Odoo's dbfilter

#### Scenario: TLS termination with Let's Encrypt
- **WHEN** the Ingress is created with cert-manager annotations
- **THEN** a wildcard TLS certificate is provisioned
- **AND** HTTPS connections are terminated at the Ingress
- **AND** traffic to Odoo is HTTP (TLS offloaded)

#### Scenario: WebSocket upgrade for longpolling
- **WHEN** a WebSocket connection request arrives for /longpolling
- **THEN** the Ingress upgrades the connection
- **AND** routes to the Odoo longpolling port (8072)
- **AND** maintains the persistent connection

#### Scenario: Large file upload support
- **WHEN** the Ingress is configured
- **THEN** proxy-body-size is set to 100m
- **AND** timeout values support long-running requests

---

### Requirement: Horizontal Pod Autoscaler
The system SHALL automatically scale Odoo pods based on resource utilization.

#### Scenario: Scale up on high CPU
- **WHEN** average CPU utilization exceeds 70% across Odoo pods
- **THEN** the HPA increases replica count
- **AND** new pods are scheduled and become ready
- **AND** load is distributed to new pods

#### Scenario: Scale up on high memory
- **WHEN** average memory utilization exceeds 80% across Odoo pods
- **THEN** the HPA increases replica count

#### Scenario: Scale down on low utilization
- **WHEN** resource utilization drops below targets
- **THEN** the HPA decreases replica count after stabilization window (5 minutes)
- **AND** minimum replicas (2) are always maintained
- **AND** scale down is gradual (max 10% per minute)

#### Scenario: Maximum replica limit
- **WHEN** the system is under extreme load
- **THEN** replicas do not exceed maxReplicas (10)
- **AND** an alert is triggered if max replicas are reached

---

### Requirement: Pod Disruption Budget
The system SHALL define a PodDisruptionBudget to ensure availability during voluntary disruptions.

#### Scenario: Node maintenance
- **WHEN** a node is cordoned for maintenance
- **THEN** at least 1 Odoo pod remains running
- **AND** pods are evicted only when replacements are ready

#### Scenario: Cluster upgrade
- **WHEN** the Kubernetes cluster is upgraded
- **THEN** Odoo availability is maintained
- **AND** disruptions are controlled per PDB rules

---

### Requirement: Network Policies
The system SHALL define NetworkPolicies to restrict pod-to-pod communication.

#### Scenario: Odoo to PostgreSQL access
- **WHEN** network policies are applied
- **THEN** Odoo pods can connect to PostgreSQL on port 5432
- **AND** other pods cannot connect to PostgreSQL

#### Scenario: Ingress to Odoo access
- **WHEN** network policies are applied
- **THEN** the Ingress controller can reach Odoo on ports 8069 and 8072
- **AND** direct external access to pods is blocked

---

### Requirement: Monitoring Integration
The system SHALL provide ServiceMonitor resources for Prometheus metrics collection.

#### Scenario: Odoo metrics collection
- **WHEN** the ServiceMonitor is created
- **THEN** Prometheus discovers and scrapes Odoo metrics endpoints
- **AND** metrics are available in Grafana dashboards

#### Scenario: PostgreSQL metrics collection
- **WHEN** postgres_exporter sidecar is deployed
- **THEN** PostgreSQL metrics are exposed on port 9187
- **AND** Prometheus scrapes database performance metrics

---

### Requirement: Backup CronJob
The system SHALL provide a CronJob for scheduled database backups.

#### Scenario: Daily backup execution
- **WHEN** the backup CronJob schedule triggers (default: 2:00 AM UTC)
- **THEN** pg_basebackup creates a base backup
- **AND** the backup is compressed and stored in the backup volume
- **AND** old backups exceeding retention are deleted

#### Scenario: Backup verification
- **WHEN** a backup completes
- **THEN** the backup integrity is verified
- **AND** backup metadata is logged
- **AND** alerts are triggered if backup fails

---

### Requirement: Resource Quotas
The system SHALL define ResourceQuotas to limit resource consumption per namespace.

#### Scenario: Namespace resource limits
- **WHEN** ResourceQuota is applied to the loomworks namespace
- **THEN** total CPU and memory across all pods is limited
- **AND** storage usage is capped
- **AND** excess resource requests are rejected

#### Scenario: LimitRange defaults
- **WHEN** a pod is created without resource requests
- **THEN** default requests and limits are applied
- **AND** the pod is scheduled with predictable resources
