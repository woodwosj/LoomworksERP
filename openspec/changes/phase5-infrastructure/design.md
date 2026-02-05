# Phase 5: Hosting Infrastructure and Snapshots - Technical Design

## Context

Loomworks ERP requires a production-grade hosting infrastructure that supports:
1. Multi-tenant isolation for SaaS hosting
2. Database snapshots for AI rollback capabilities
3. Containerized deployment for cloud portability
4. Horizontal scaling for high availability
5. **Distribution of a fully forked Odoo as a standalone product**

This design document captures the key technical decisions, alternatives considered, and implementation patterns for Phase 5.

## Stakeholders

- **End Users**: Need reliable undo capability for AI mistakes
- **Tenant Admins**: Need self-service database management
- **Platform Operators**: Need efficient multi-tenant management
- **Developers**: Need local development environment parity
- **Self-Hosted Customers**: Need easy installation via packages or containers
- **Contributors**: Need clear CI/CD workflows for development

## Goals / Non-Goals

### Goals
- Complete tenant isolation with no data leakage
- Sub-30-second snapshot creation
- Sub-15-minute PITR restore for any point in retention window
- Zero-downtime deployments and scaling
- Local development environment that mirrors production
- **Distribute Loomworks ERP as a complete, installable product (deb, rpm, Docker)**
- **Maintain upstream Odoo security patches via structured merge strategy**
- **Automated CI/CD pipeline for linting, testing, building, and publishing**

### Non-Goals
- Multi-region active-active replication (future enhancement)
- Real-time streaming replication to standby (Phase 6+)
- Tenant database migration between clusters
- Custom PostgreSQL extensions per tenant
- PyPI distribution of core (too large; addons only)

---

## Decision 5: Fork Distribution Strategy

### Decision
Distribute Loomworks ERP as a **single monorepo containing the fully forked Odoo core plus Loomworks addons**, with versioning that tracks the upstream Odoo version.

### Repository Structure

```
LoomworksERP/
├── odoo/                      # Forked Odoo 18 core (LGPL-3)
│   ├── odoo/                  # Core framework
│   ├── addons/                # Standard Odoo addons
│   └── setup/                 # Build scripts (deb, rpm, docker)
├── loomworks_addons/          # Loomworks-specific modules
│   ├── loomworks_core/
│   ├── loomworks_ai/
│   ├── loomworks_tenant/
│   ├── loomworks_snapshot/
│   └── loomworks_dashboard/
├── infrastructure/            # Deployment configurations
│   ├── docker/
│   ├── kubernetes/
│   └── packaging/             # deb/rpm build scripts
├── .github/
│   └── workflows/             # CI/CD pipelines
├── requirements.txt           # Python dependencies
├── CHANGELOG.md               # Version history
└── VERSION                    # Current version string
```

### Versioning Strategy

**Format**: `{loomworks_major}.{loomworks_minor}.{loomworks_patch}+odoo{odoo_version}`

Examples:
- `1.0.0+odoo18.0` - First stable release based on Odoo 18.0
- `1.1.0+odoo18.0` - Feature release with Loomworks improvements
- `1.1.1+odoo18.0` - Patch release with bug fixes
- `2.0.0+odoo19.0` - Major release rebased on Odoo 19.0

**VERSION file**:
```
LOOMWORKS_VERSION=1.0.0
ODOO_VERSION=18.0
ODOO_UPSTREAM_COMMIT=abc123def456
RELEASE_DATE=2025-01-15
```

### Release Tagging

```bash
# Tag format: v{loomworks_version}
git tag -a v1.0.0 -m "Loomworks ERP 1.0.0 (Odoo 18.0)"

# Branch strategy
main                    # Stable releases
develop                 # Integration branch
release/1.x             # Release maintenance branch
upstream/odoo-18.0      # Upstream tracking branch (read-only mirror)
```

### Changelog Format

```markdown
# Changelog

## [1.1.0] - 2025-02-15

### Added
- [loomworks_ai] MCP tools for inventory management
- [loomworks_dashboard] Real-time KPI widgets

### Changed
- [loomworks_core] Improved session handling performance

### Fixed
- [loomworks_snapshot] WAL position capture timing issue

### Security
- [odoo] Merged upstream security patches (CVE-2025-XXXX)

### Upstream Sync
- Merged Odoo 18.0 commits up to `def789abc012`
```

---

## Decision 6: Docker Image Structure for Forked Odoo

### Decision
Build a **self-contained Docker image** that includes the complete forked Odoo core plus Loomworks addons, following the official Odoo Docker image patterns but customized for our distribution.

### Rationale

The official Odoo Docker image (https://hub.docker.com/_/odoo):
- Uses `ubuntu:noble` as base image
- Installs Odoo via `.deb` package from nightly builds
- Mounts `/var/lib/odoo` for filestore and `/mnt/extra-addons` for custom modules
- Exposes ports 8069, 8071, 8072

For Loomworks, we need a **source-based build** that:
1. Includes our forked core modifications
2. Bundles Loomworks addons in the image
3. Supports custom Python dependencies for AI integration
4. Provides smaller image size via multi-stage builds

### Implementation Pattern

```dockerfile
# infrastructure/docker/Dockerfile
#syntax=docker/dockerfile:1

# === Build Arguments ===
ARG PYTHON_VERSION=3.11
ARG LOOMWORKS_VERSION=1.0.0

# === Build stage: Compile Python dependencies ===
FROM python:${PYTHON_VERSION}-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libldap2-dev \
    libsasl2-dev \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/loomworks/venv
ENV PATH="/opt/loomworks/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip wheel \
    && pip install --no-cache-dir -r requirements.txt

# === Runtime stage: Minimal production image ===
FROM python:${PYTHON_VERSION}-slim-bookworm

ARG LOOMWORKS_VERSION
LABEL org.opencontainers.image.title="Loomworks ERP"
LABEL org.opencontainers.image.description="AI-first ERP based on Odoo Community"
LABEL org.opencontainers.image.version="${LOOMWORKS_VERSION}"
LABEL org.opencontainers.image.vendor="Loomworks"
LABEL org.opencontainers.image.licenses="LGPL-3.0"
LABEL org.opencontainers.image.source="https://github.com/loomworks/loomworks-erp"

ENV PYTHONUNBUFFERED=1
ENV LANG=en_US.UTF-8
ENV PATH="/opt/loomworks/venv/bin:$PATH"
ENV ODOO_RC=/etc/loomworks/loomworks.conf

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # PostgreSQL client
    postgresql-client \
    # PDF generation
    wkhtmltopdf \
    # Fonts for PDF
    fonts-dejavu-core \
    fonts-noto-cjk \
    # XML/XSLT processing
    libxml2 \
    libxslt1.1 \
    # Image processing
    libjpeg62-turbo \
    # Node.js for frontend assets (rtlcss)
    nodejs \
    npm \
    # Network tools for healthchecks
    curl \
    && npm install -g rtlcss \
    && rm -rf /var/lib/apt/lists/* \
    # Create odoo user and directories
    && useradd -r -m -d /opt/loomworks -s /bin/bash odoo \
    && mkdir -p /var/lib/loomworks /etc/loomworks /var/log/loomworks \
    && chown -R odoo:odoo /var/lib/loomworks /etc/loomworks /var/log/loomworks

# Copy virtual environment from builder
COPY --from=builder /opt/loomworks/venv /opt/loomworks/venv

# Copy Loomworks ERP (forked Odoo core + addons)
COPY --chown=odoo:odoo odoo /opt/loomworks/odoo
COPY --chown=odoo:odoo loomworks_addons /opt/loomworks/addons

# Copy configuration and entrypoint
COPY --chown=odoo:odoo infrastructure/docker/loomworks.conf /etc/loomworks/loomworks.conf
COPY --chown=odoo:odoo infrastructure/docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set working directory and user
WORKDIR /opt/loomworks
USER odoo

# Volumes for persistent data
VOLUME ["/var/lib/loomworks"]

# Expose Odoo ports
# 8069: HTTP
# 8071: Gevent (websocket)
# 8072: Longpolling
EXPOSE 8069 8071 8072

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8069/web/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["loomworks"]
```

### Entrypoint Script

```bash
#!/bin/bash
# infrastructure/docker/entrypoint.sh
set -e

# Database connection check
wait_for_postgres() {
    local host="${DB_HOST:-db}"
    local port="${DB_PORT:-5432}"
    local max_attempts=30
    local attempt=1

    echo "Waiting for PostgreSQL at ${host}:${port}..."
    while [ $attempt -le $max_attempts ]; do
        if pg_isready -h "$host" -p "$port" -q; then
            echo "PostgreSQL is ready."
            return 0
        fi
        echo "Attempt $attempt/$max_attempts: PostgreSQL not ready, waiting..."
        sleep 2
        ((attempt++))
    done
    echo "ERROR: PostgreSQL not available after $max_attempts attempts"
    exit 1
}

# Generate config from environment if needed
generate_config() {
    if [ ! -f "$ODOO_RC" ] || [ "${REGENERATE_CONFIG:-false}" = "true" ]; then
        cat > "$ODOO_RC" << EOF
[options]
addons_path = /opt/loomworks/odoo/addons,/opt/loomworks/addons
data_dir = /var/lib/loomworks
db_host = ${DB_HOST:-db}
db_port = ${DB_PORT:-5432}
db_user = ${DB_USER:-odoo}
db_password = ${DB_PASSWORD:-odoo}
db_name = ${DB_NAME:-False}
dbfilter = ${DB_FILTER:-.*}
admin_passwd = ${ADMIN_PASSWD:-admin}
proxy_mode = ${PROXY_MODE:-True}
workers = ${WORKERS:-4}
max_cron_threads = ${MAX_CRON_THREADS:-2}
limit_memory_hard = ${LIMIT_MEMORY_HARD:-2684354560}
limit_memory_soft = ${LIMIT_MEMORY_SOFT:-2147483648}
limit_time_cpu = ${LIMIT_TIME_CPU:-600}
limit_time_real = ${LIMIT_TIME_REAL:-1200}
log_level = ${LOG_LEVEL:-info}
EOF
    fi
}

# Main entrypoint
case "${1}" in
    loomworks|odoo)
        wait_for_postgres
        generate_config
        exec python /opt/loomworks/odoo/odoo-bin \
            --config="$ODOO_RC" \
            "${@:2}"
        ;;
    shell)
        wait_for_postgres
        generate_config
        exec python /opt/loomworks/odoo/odoo-bin shell \
            --config="$ODOO_RC" \
            "${@:2}"
        ;;
    scaffold)
        exec python /opt/loomworks/odoo/odoo-bin scaffold "${@:2}"
        ;;
    *)
        exec "$@"
        ;;
esac
```

### Docker Compose for Full Stack

```yaml
# infrastructure/docker/docker-compose.yml
version: '3.8'

services:
  db:
    image: postgres:15-bookworm
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
    networks:
      - loomworks

  loomworks:
    image: ghcr.io/loomworks/loomworks-erp:${LOOMWORKS_VERSION:-latest}
    build:
      context: ../..
      dockerfile: infrastructure/docker/Dockerfile
      args:
        LOOMWORKS_VERSION: ${LOOMWORKS_VERSION:-1.0.0}
    depends_on:
      db:
        condition: service_healthy
    environment:
      - DB_HOST=db
      - DB_PORT=5432
      - DB_USER=${POSTGRES_USER:-odoo}
      - DB_PASSWORD=${POSTGRES_PASSWORD:-odoo}
      - ADMIN_PASSWD=${ADMIN_PASSWD:-admin}
      - PROXY_MODE=True
      - WORKERS=4
    volumes:
      - loomworks_data:/var/lib/loomworks
    ports:
      - "8069:8069"
      - "8072:8072"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8069/web/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    networks:
      - loomworks

  redis:
    image: redis:7-bookworm
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - loomworks

  nginx:
    image: nginx:stable
    depends_on:
      - loomworks
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    ports:
      - "80:80"
      - "443:443"
    restart: unless-stopped
    networks:
      - loomworks

volumes:
  postgres_data:
  wal_archive:
  loomworks_data:
  redis_data:

networks:
  loomworks:
    driver: bridge
```

---

## Decision 7: Package Distribution

### Decision
Build and distribute native packages (deb, rpm) using Docker-based build processes similar to Odoo's nightly build system.

### Rationale

Based on research of Odoo's packaging infrastructure:
- Odoo uses `setup/package.py` to orchestrate Docker-based builds
- DEB packages use `dpkg-buildpackage` within Debian containers
- RPM packages use `rpmbuild` within Fedora containers
- Nightly builds generate packages for multiple distributions

For Loomworks, we adapt this approach with:
1. Custom package names (`loomworks-erp` instead of `odoo`)
2. Different default paths (`/opt/loomworks` instead of `/usr/lib/python3/dist-packages/odoo`)
3. Bundled Loomworks addons in the package
4. Modified dependencies for AI integration

### Package Structure

#### Debian Package (deb)

```
loomworks-erp_1.0.0+odoo18.0_all.deb
├── DEBIAN/
│   ├── control           # Package metadata
│   ├── conffiles         # Config files to preserve on upgrade
│   ├── postinst          # Post-installation script
│   ├── prerm             # Pre-removal script
│   └── postrm            # Post-removal script
├── opt/loomworks/
│   ├── odoo/             # Forked Odoo core
│   └── addons/           # Loomworks addons
├── etc/loomworks/
│   └── loomworks.conf    # Default configuration
├── lib/systemd/system/
│   └── loomworks.service # Systemd unit file
└── usr/bin/
    └── loomworks         # CLI wrapper script
```

**control file**:
```
Package: loomworks-erp
Version: 1.0.0+odoo18.0
Architecture: all
Maintainer: Loomworks Team <dev@loomworks.app>
Depends: python3 (>= 3.10),
         python3-pip,
         python3-venv,
         postgresql-client,
         wkhtmltopdf,
         fonts-dejavu-core,
         nodejs,
         npm
Recommends: postgresql (>= 15)
Section: web
Priority: optional
Homepage: https://loomworks.app
Description: AI-first ERP based on Odoo Community
 Loomworks ERP is an open-source ERP system where users interact
 primarily with AI agents rather than traditional forms and menus.
 Built on Odoo Community v18 (LGPL-3), it provides database snapshots
 for AI rollback, interactive dashboards, and workflow automation.
```

**systemd service**:
```ini
# lib/systemd/system/loomworks.service
[Unit]
Description=Loomworks ERP
Documentation=https://docs.loomworks.app
After=network.target postgresql.service

[Service]
Type=simple
User=loomworks
Group=loomworks
ExecStart=/opt/loomworks/venv/bin/python /opt/loomworks/odoo/odoo-bin \
    --config=/etc/loomworks/loomworks.conf
ExecReload=/bin/kill -HUP $MAINPID
KillMode=mixed
TimeoutStopSec=60
Restart=on-failure
RestartSec=5

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/loomworks /var/log/loomworks

[Install]
WantedBy=multi-user.target
```

#### RPM Package

```
loomworks-erp-1.0.0+odoo18.0-1.noarch.rpm
├── /opt/loomworks/
│   ├── odoo/
│   └── addons/
├── /etc/loomworks/
│   └── loomworks.conf
├── /usr/lib/systemd/system/
│   └── loomworks.service
└── /usr/bin/
    └── loomworks
```

**spec file**:
```rpm-spec
# infrastructure/packaging/loomworks.spec
Name:           loomworks-erp
Version:        1.0.0
Release:        1%{?dist}
Summary:        AI-first ERP based on Odoo Community
License:        LGPL-3.0
URL:            https://loomworks.app
Source0:        loomworks-erp-%{version}.tar.gz

BuildArch:      noarch
Requires:       python3 >= 3.10
Requires:       python3-pip
Requires:       postgresql >= 15
Requires:       wkhtmltopdf
Requires:       nodejs >= 20

%description
Loomworks ERP is an open-source ERP system where users interact
primarily with AI agents rather than traditional forms and menus.

%prep
%setup -q

%install
mkdir -p %{buildroot}/opt/loomworks
mkdir -p %{buildroot}/etc/loomworks
mkdir -p %{buildroot}/var/lib/loomworks
mkdir -p %{buildroot}/usr/lib/systemd/system
mkdir -p %{buildroot}/usr/bin

cp -r odoo %{buildroot}/opt/loomworks/
cp -r loomworks_addons %{buildroot}/opt/loomworks/addons
install -m 644 infrastructure/packaging/loomworks.conf %{buildroot}/etc/loomworks/
install -m 644 infrastructure/packaging/loomworks.service %{buildroot}/usr/lib/systemd/system/
install -m 755 infrastructure/packaging/loomworks-cli %{buildroot}/usr/bin/loomworks

%pre
getent group loomworks >/dev/null || groupadd -r loomworks
getent passwd loomworks >/dev/null || \
    useradd -r -g loomworks -d /opt/loomworks -s /sbin/nologin loomworks

%post
python3 -m venv /opt/loomworks/venv
/opt/loomworks/venv/bin/pip install -r /opt/loomworks/requirements.txt
chown -R loomworks:loomworks /opt/loomworks /var/lib/loomworks
systemctl daemon-reload
systemctl enable loomworks.service

%preun
if [ $1 -eq 0 ]; then
    systemctl stop loomworks.service || true
    systemctl disable loomworks.service || true
fi

%files
%license LICENSE
%doc README.md CHANGELOG.md
/opt/loomworks
%config(noreplace) /etc/loomworks/loomworks.conf
/usr/lib/systemd/system/loomworks.service
/usr/bin/loomworks
%attr(750,loomworks,loomworks) /var/lib/loomworks

%changelog
* Wed Jan 15 2025 Loomworks Team <dev@loomworks.app> - 1.0.0-1
- Initial release based on Odoo 18.0
```

### Build Process

```python
# infrastructure/packaging/build.py
"""
Package builder for Loomworks ERP.
Generates deb, rpm, and Docker images using Docker-based builds.
"""

import os
import subprocess
import argparse
from pathlib import Path

DOCKER_TEMPLATES = {
    'deb': 'infrastructure/packaging/Dockerfile.debian',
    'rpm': 'infrastructure/packaging/Dockerfile.fedora',
}

def read_version():
    """Read version from VERSION file."""
    version_file = Path(__file__).parent.parent.parent / 'VERSION'
    versions = {}
    with open(version_file) as f:
        for line in f:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                versions[key] = value
    return versions

def build_deb(output_dir: Path):
    """Build Debian package using Docker."""
    version = read_version()
    image_tag = f"loomworks-build-deb:{version['LOOMWORKS_VERSION']}"

    # Build Docker image for package building
    subprocess.run([
        'docker', 'build',
        '-f', DOCKER_TEMPLATES['deb'],
        '-t', image_tag,
        '--build-arg', f"VERSION={version['LOOMWORKS_VERSION']}",
        '--build-arg', f"ODOO_VERSION={version['ODOO_VERSION']}",
        '.'
    ], check=True)

    # Run container to generate package
    subprocess.run([
        'docker', 'run', '--rm',
        '-v', f"{output_dir}:/output",
        image_tag,
        'dpkg-buildpackage', '-rfakeroot', '-uc', '-us', '-tc'
    ], check=True)

def build_rpm(output_dir: Path):
    """Build RPM package using Docker."""
    version = read_version()
    image_tag = f"loomworks-build-rpm:{version['LOOMWORKS_VERSION']}"

    subprocess.run([
        'docker', 'build',
        '-f', DOCKER_TEMPLATES['rpm'],
        '-t', image_tag,
        '--build-arg', f"VERSION={version['LOOMWORKS_VERSION']}",
        '.'
    ], check=True)

    subprocess.run([
        'docker', 'run', '--rm',
        '-v', f"{output_dir}:/output",
        image_tag,
        'rpmbuild', '-ba', '/root/rpmbuild/SPECS/loomworks.spec'
    ], check=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build Loomworks packages')
    parser.add_argument('--format', choices=['deb', 'rpm', 'all'], default='all')
    parser.add_argument('--output', type=Path, default=Path('dist'))
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)

    if args.format in ('deb', 'all'):
        build_deb(args.output)
    if args.format in ('rpm', 'all'):
        build_rpm(args.output)
```

### Windows Considerations

Windows support is deferred to a future phase due to complexity:
- Odoo's Windows installer uses Wine-based builds
- Python dependency compilation is more complex
- Lower priority for enterprise/hosting use cases

For Windows development, recommend:
- Docker Desktop with Linux containers
- WSL2 with Ubuntu

---

## Decision 8: CI/CD Pipeline

### Decision
Use **GitHub Actions** for automated linting, testing, building, and publishing, with path-based filtering for efficient monorepo builds.

### Rationale

Based on research of Python monorepo CI/CD best practices:
- Path filtering reduces unnecessary builds (only run tests for changed components)
- Matrix builds parallelize testing across Python versions
- Reusable workflows reduce duplication
- GitHub Container Registry (ghcr.io) integrates well with GitHub Actions

### Workflow Structure

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop, 'release/**']
  pull_request:
    branches: [main, develop]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  # Detect which components changed
  changes:
    runs-on: ubuntu-latest
    outputs:
      odoo-core: ${{ steps.filter.outputs.odoo-core }}
      loomworks-addons: ${{ steps.filter.outputs.loomworks-addons }}
      infrastructure: ${{ steps.filter.outputs.infrastructure }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            odoo-core:
              - 'odoo/**'
              - 'requirements.txt'
            loomworks-addons:
              - 'loomworks_addons/**'
            infrastructure:
              - 'infrastructure/**'
              - 'Dockerfile'

  # Lint Python code
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install lint dependencies
        run: |
          pip install ruff mypy

      - name: Run Ruff (linting + formatting)
        run: |
          ruff check odoo/ loomworks_addons/
          ruff format --check odoo/ loomworks_addons/

      - name: Run mypy (type checking)
        run: |
          mypy loomworks_addons/ --ignore-missing-imports
        continue-on-error: true  # Type hints are aspirational for now

  # Run unit tests
  test-unit:
    needs: [changes, lint]
    if: needs.changes.outputs.odoo-core == 'true' || needs.changes.outputs.loomworks-addons == 'true'
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']
      fail-fast: false

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: odoo
          POSTGRES_PASSWORD: odoo
          POSTGRES_DB: test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'

      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y wkhtmltopdf libldap2-dev libsasl2-dev

      - name: Install Python dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-odoo

      - name: Run Loomworks addon tests
        run: |
          pytest loomworks_addons/*/tests/ \
            --cov=loomworks_addons \
            --cov-report=xml \
            --junitxml=test-results.xml
        env:
          PGHOST: localhost
          PGUSER: odoo
          PGPASSWORD: odoo

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: coverage.xml
          flags: unittests

  # Run integration tests
  test-integration:
    needs: [changes, test-unit]
    if: github.event_name == 'push' && (needs.changes.outputs.odoo-core == 'true' || needs.changes.outputs.loomworks-addons == 'true')
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Start services
        run: |
          docker compose -f infrastructure/docker/docker-compose.yml up -d
          # Wait for Odoo to be healthy
          timeout 300 bash -c 'until curl -s http://localhost:8069/web/health; do sleep 5; done'

      - name: Run integration tests
        run: |
          docker compose -f infrastructure/docker/docker-compose.yml exec -T loomworks \
            python -m pytest /opt/loomworks/addons/*/tests/integration/ -v

      - name: Collect logs on failure
        if: failure()
        run: |
          docker compose -f infrastructure/docker/docker-compose.yml logs > docker-logs.txt

      - name: Upload logs
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: docker-logs
          path: docker-logs.txt

      - name: Stop services
        if: always()
        run: |
          docker compose -f infrastructure/docker/docker-compose.yml down -v

  # Build Docker image
  build-docker:
    needs: [changes, test-unit]
    if: needs.changes.outputs.odoo-core == 'true' || needs.changes.outputs.loomworks-addons == 'true' || needs.changes.outputs.infrastructure == 'true'
    runs-on: ubuntu-latest
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
      image-digest: ${{ steps.build.outputs.digest }}

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=sha,prefix=

      - name: Build image
        id: build
        uses: docker/build-push-action@v6
        with:
          context: .
          file: infrastructure/docker/Dockerfile
          push: false
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          outputs: type=docker,dest=/tmp/image.tar

      - name: Upload image artifact
        uses: actions/upload-artifact@v4
        with:
          name: docker-image
          path: /tmp/image.tar
          retention-days: 1

  # Build packages (on release branches only)
  build-packages:
    needs: [test-unit, test-integration]
    if: github.ref == 'refs/heads/main' || startsWith(github.ref, 'refs/heads/release/')
    runs-on: ubuntu-latest
    strategy:
      matrix:
        format: [deb, rpm]

    steps:
      - uses: actions/checkout@v4

      - name: Build ${{ matrix.format }} package
        run: |
          python infrastructure/packaging/build.py \
            --format ${{ matrix.format }} \
            --output dist/

      - name: Upload package
        uses: actions/upload-artifact@v4
        with:
          name: package-${{ matrix.format }}
          path: dist/*.${{ matrix.format }}
```

### Release Workflow

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write
  packages: write

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Read version
        id: version
        run: |
          source VERSION
          echo "loomworks_version=$LOOMWORKS_VERSION" >> $GITHUB_OUTPUT
          echo "odoo_version=$ODOO_VERSION" >> $GITHUB_OUTPUT

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push Docker image
        uses: docker/build-push-action@v6
        with:
          context: .
          file: infrastructure/docker/Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:${{ steps.version.outputs.loomworks_version }}
            ghcr.io/${{ github.repository }}:latest
          platforms: linux/amd64,linux/arm64
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Build packages
        run: |
          python infrastructure/packaging/build.py --format all --output dist/

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            dist/*.deb
            dist/*.rpm
          body: |
            ## Loomworks ERP ${{ steps.version.outputs.loomworks_version }}

            Based on Odoo ${{ steps.version.outputs.odoo_version }}

            ### Installation

            **Docker:**
            ```bash
            docker pull ghcr.io/${{ github.repository }}:${{ steps.version.outputs.loomworks_version }}
            ```

            **Debian/Ubuntu:**
            ```bash
            sudo dpkg -i loomworks-erp_${{ steps.version.outputs.loomworks_version }}*.deb
            sudo apt-get install -f
            ```

            **RHEL/CentOS/Fedora:**
            ```bash
            sudo rpm -i loomworks-erp-${{ steps.version.outputs.loomworks_version }}*.rpm
            ```

            See [CHANGELOG.md](CHANGELOG.md) for details.
          draft: false
          prerelease: ${{ contains(github.ref, 'alpha') || contains(github.ref, 'beta') || contains(github.ref, 'rc') }}
```

---

## Decision 9: Upstream Update Management

### Decision
Maintain an **upstream tracking branch** and use a structured merge strategy to incorporate Odoo security fixes and updates.

### Rationale

Research on fork maintenance best practices indicates:
- Regular upstream merges reduce conflict complexity
- Security patches must be applied promptly (within 48 hours of disclosure)
- Clear upstream tracking improves auditability
- Cherry-picking specific commits is preferable to full merges for stability

### Branch Strategy

```
main                    # Production releases
├── develop             # Integration branch
├── release/1.x         # Release maintenance
├── feature/*           # New features
└── upstream/odoo-18.0  # Read-only mirror of Odoo 18.0 branch
```

### Upstream Sync Workflow

```yaml
# .github/workflows/upstream-sync.yml
name: Upstream Sync

on:
  schedule:
    # Check for updates daily at 2 AM UTC
    - cron: '0 2 * * *'
  workflow_dispatch:
    inputs:
      force_sync:
        description: 'Force sync even without security updates'
        type: boolean
        default: false

jobs:
  check-upstream:
    runs-on: ubuntu-latest
    outputs:
      has-updates: ${{ steps.check.outputs.has-updates }}
      has-security: ${{ steps.check.outputs.has-security }}
      commits: ${{ steps.check.outputs.commits }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Add upstream remote
        run: |
          git remote add upstream https://github.com/odoo/odoo.git || true
          git fetch upstream 18.0

      - name: Check for updates
        id: check
        run: |
          # Get current upstream commit from VERSION
          source VERSION
          CURRENT=$ODOO_UPSTREAM_COMMIT

          # Get latest upstream commit
          LATEST=$(git rev-parse upstream/18.0)

          if [ "$CURRENT" = "$LATEST" ]; then
            echo "has-updates=false" >> $GITHUB_OUTPUT
            exit 0
          fi

          echo "has-updates=true" >> $GITHUB_OUTPUT

          # Check for security-related commits
          SECURITY_COMMITS=$(git log $CURRENT..$LATEST --oneline --grep="security" --grep="CVE" --grep="XSS" --grep="SQL injection" --grep="CSRF" -i | wc -l)
          if [ "$SECURITY_COMMITS" -gt 0 ]; then
            echo "has-security=true" >> $GITHUB_OUTPUT
          else
            echo "has-security=false" >> $GITHUB_OUTPUT
          fi

          # List commits for review
          git log $CURRENT..$LATEST --oneline > /tmp/commits.txt
          echo "commits<<EOF" >> $GITHUB_OUTPUT
          cat /tmp/commits.txt >> $GITHUB_OUTPUT
          echo "EOF" >> $GITHUB_OUTPUT

  create-sync-pr:
    needs: check-upstream
    if: needs.check-upstream.outputs.has-updates == 'true' && (needs.check-upstream.outputs.has-security == 'true' || github.event.inputs.force_sync == 'true')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Configure git
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"

      - name: Create sync branch
        run: |
          git remote add upstream https://github.com/odoo/odoo.git || true
          git fetch upstream 18.0

          BRANCH="upstream-sync/$(date +%Y%m%d)"
          git checkout -b $BRANCH

          # Attempt merge (may have conflicts)
          git merge upstream/18.0 --no-edit || true

          # Check for conflicts
          if git diff --name-only --diff-filter=U | grep -q .; then
            echo "CONFLICTS DETECTED - Manual review required"
            git diff --name-only --diff-filter=U > /tmp/conflicts.txt
          fi

          git push origin $BRANCH

      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v6
        with:
          title: "chore: sync upstream Odoo 18.0"
          body: |
            ## Upstream Sync

            This PR merges the latest changes from upstream Odoo 18.0.

            ### Commits
            ```
            ${{ needs.check-upstream.outputs.commits }}
            ```

            ### Security Updates
            ${{ needs.check-upstream.outputs.has-security == 'true' && 'Security-related commits detected - HIGH PRIORITY' || 'No security commits detected' }}

            ### Review Checklist
            - [ ] Conflicts resolved (if any)
            - [ ] Loomworks modifications preserved
            - [ ] All tests pass
            - [ ] CHANGELOG updated with upstream sync note
            - [ ] VERSION file updated with new ODOO_UPSTREAM_COMMIT
          branch: upstream-sync/${{ github.run_id }}
          labels: |
            upstream-sync
            ${{ needs.check-upstream.outputs.has-security == 'true' && 'security' || '' }}

  notify-security:
    needs: [check-upstream, create-sync-pr]
    if: needs.check-upstream.outputs.has-security == 'true'
    runs-on: ubuntu-latest
    steps:
      - name: Notify team of security updates
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "Security updates available from upstream Odoo",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*Security Updates Detected*\nUpstream Odoo has security patches that need to be merged."
                  }
                }
              ]
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

### Version Compatibility Matrix

| Loomworks Version | Odoo Version | Python | PostgreSQL | Status |
|-------------------|--------------|--------|------------|--------|
| 1.0.x | 18.0 | 3.10-3.12 | 15+ | Active |
| 1.1.x | 18.0 | 3.10-3.12 | 15+ | Planned |
| 2.0.x | 19.0 | 3.11-3.13 | 16+ | Future |

### Security Patch SLA

| Severity | Response Time | Deployment |
|----------|---------------|------------|
| Critical (CVE 9.0+) | 4 hours | Immediate hotfix release |
| High (CVE 7.0-8.9) | 24 hours | Patch release within 48 hours |
| Medium (CVE 4.0-6.9) | 72 hours | Included in next scheduled release |
| Low (CVE < 4.0) | 1 week | Included in next scheduled release |

---

## Decision 10: Multi-Tenant Architecture for Forked Core

### Decision
Implement multi-tenancy at the **database routing layer** using Odoo's native `dbfilter` mechanism with tenant metadata stored in a central management database.

### Architecture

```
                    ┌─────────────────┐
                    │   Load Balancer │
                    │   (Nginx/HAProxy)│
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │ Loomworks│  │ Loomworks│  │ Loomworks│
        │ Pod 1    │  │ Pod 2    │  │ Pod 3    │
        └────┬─────┘  └────┬─────┘  └────┬─────┘
             │             │             │
             └──────────┬──┴─────────────┘
                        │
                        ▼
        ┌───────────────────────────────────┐
        │         PgBouncer Pool            │
        └───────────────┬───────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
   ┌─────────┐    ┌─────────┐    ┌─────────┐
   │tenant_a │    │tenant_b │    │loomworks│
   │  (DB)   │    │  (DB)   │    │_mgmt(DB)│
   └─────────┘    └─────────┘    └─────────┘
```

### Database Routing in Forked Code

The forked Odoo core includes modifications to enhance tenant isolation:

```python
# odoo/http.py (modified in fork)
class TenantRouter:
    """
    Enhanced database routing for Loomworks multi-tenancy.
    Extends Odoo's dbfilter with subdomain-based routing and
    tenant metadata validation.
    """

    def __init__(self):
        self._tenant_cache = {}
        self._cache_ttl = 300  # 5 minutes

    def get_database_for_request(self, request):
        """
        Determine the database for the current request.

        Order of precedence:
        1. X-Loomworks-Tenant header (for internal services)
        2. Subdomain extraction from Host header
        3. dbfilter regex matching

        Returns:
            str: Database name
            None: If no matching tenant
        """
        # Check for internal tenant header
        tenant_header = request.httprequest.headers.get('X-Loomworks-Tenant')
        if tenant_header:
            return self._validate_tenant(tenant_header)

        # Extract subdomain from host
        host = request.httprequest.host.split(':')[0]
        subdomain = self._extract_subdomain(host)

        if subdomain:
            return self._get_database_for_subdomain(subdomain)

        # Fall back to Odoo's dbfilter
        return None

    def _extract_subdomain(self, host):
        """Extract tenant subdomain from host."""
        # Support patterns:
        # - tenant.loomworks.app
        # - tenant.localhost
        # - tenant.loomworks.local
        parts = host.split('.')
        if len(parts) >= 2 and parts[0] not in ('www', 'api', 'admin'):
            return parts[0]
        return None

    def _get_database_for_subdomain(self, subdomain):
        """Look up database for subdomain with caching."""
        cache_key = f"tenant:{subdomain}"
        if cache_key in self._tenant_cache:
            cached = self._tenant_cache[cache_key]
            if cached['expires'] > time.time():
                return cached['database']

        # Query management database
        database = self._query_tenant_database(subdomain)
        if database:
            self._tenant_cache[cache_key] = {
                'database': database,
                'expires': time.time() + self._cache_ttl
            }
        return database

    def _query_tenant_database(self, subdomain):
        """Query the management database for tenant info."""
        # Connect to management database
        mgmt_db = config.get('loomworks_mgmt_db', 'loomworks_mgmt')
        with db_connect(mgmt_db).cursor() as cr:
            cr.execute("""
                SELECT database_name
                FROM loomworks_tenant
                WHERE subdomain = %s
                  AND state = 'active'
            """, [subdomain])
            result = cr.fetchone()
            return result[0] if result else None
```

### Tenant Isolation at Core Level

```python
# odoo/models.py (security enhancement in fork)
class BaseModel(models.AbstractModel):
    """
    Enhanced BaseModel with tenant isolation checks.
    """
    _inherit = 'base'

    @api.model
    def _check_tenant_isolation(self):
        """
        Verify the current operation respects tenant boundaries.
        Called automatically on security-sensitive operations.
        """
        if not self.env.context.get('skip_tenant_check'):
            expected_db = self.env.cr.dbname
            request_db = getattr(request, 'db', None) if request else None
            if request_db and request_db != expected_db:
                raise AccessError(
                    f"Tenant isolation violation: "
                    f"expected {expected_db}, got {request_db}"
                )

    @api.model_create_multi
    def create(self, vals_list):
        self._check_tenant_isolation()
        return super().create(vals_list)

    def write(self, vals):
        self._check_tenant_isolation()
        return super().write(vals)

    def unlink(self):
        self._check_tenant_isolation()
        return super().unlink()
```

### Configuration

```ini
# /etc/loomworks/loomworks.conf

[options]
; Multi-tenant configuration
db_name = False
dbfilter = ^(?!loomworks_mgmt$).*$
loomworks_mgmt_db = loomworks_mgmt

; Tenant routing
loomworks_tenant_routing = subdomain
loomworks_base_domain = loomworks.app

; Isolation settings
loomworks_strict_isolation = True
loomworks_audit_cross_tenant = True
```

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
Use **multi-stage build** with Debian slim base image for compatibility and minimal footprint.

(See Decision 6 above for complete Docker implementation)

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
          image: postgres:15-bookworm
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
# infrastructure/kubernetes/loomworks-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: loomworks
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
      app: loomworks
  template:
    metadata:
      labels:
        app: loomworks
    spec:
      containers:
        - name: loomworks
          image: ghcr.io/loomworks/loomworks-erp:latest
          ports:
            - containerPort: 8069
            - containerPort: 8072
          envFrom:
            - configMapRef:
                name: loomworks-config
            - secretRef:
                name: loomworks-credentials
          volumeMounts:
            - name: filestore
              mountPath: /var/lib/loomworks
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
            initialDelaySeconds: 120
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /web/health
              port: 8069
            initialDelaySeconds: 60
            periodSeconds: 10
      volumes:
        - name: filestore
          persistentVolumeClaim:
            claimName: loomworks-filestore
```

```yaml
# infrastructure/kubernetes/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: loomworks-hpa
  namespace: loomworks
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: loomworks
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
    nginx.ingress.kubernetes.io/websocket-services: "loomworks"
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
                name: loomworks
                port:
                  number: 8069
          - path: /longpolling
            pathType: Prefix
            backend:
              service:
                name: loomworks
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

### Risk 5: Upstream Merge Conflicts
- **Risk**: Loomworks core modifications may conflict with Odoo updates
- **Mitigation**: Minimize core changes, use extension patterns, frequent upstream syncs
- **Monitoring**: Weekly upstream diff review, automated conflict detection

### Risk 6: Package Distribution Complexity
- **Risk**: Supporting multiple distribution formats increases maintenance burden
- **Mitigation**: Docker-based builds ensure consistency, automated CI/CD reduces manual work
- **Priority**: Docker > deb > rpm (based on expected usage)

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

### Phase 5d: Distribution Pipeline (Weeks 47-48)
1. Set up GitHub Actions CI/CD
2. Build and test deb/rpm packages
3. Publish first release to GitHub Releases
4. Document installation procedures

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

5. **Windows Support**: When should Windows installer be prioritized?
   - Recommendation: Post-1.0, based on self-hosted customer demand

6. **PyPI Distribution**: Should Loomworks addons be published to PyPI separately?
   - Recommendation: Consider for v1.1+ to support plugin ecosystem

---

## References

- [Odoo Official Docker Image](https://hub.docker.com/_/odoo)
- [Odoo Docker Repository](https://github.com/odoo/docker)
- [Odoo Nightly Builds](https://nightly.odoo.com/)
- [Odoo Package Build Script](https://github.com/odoo/odoo/blob/18.0/setup/package.py)
- [PostgreSQL PITR Documentation](https://www.postgresql.org/docs/current/continuous-archiving.html)
- [GitHub Actions for Python Monorepos](https://generalreasoning.com/blog/2025/03/22/github-actions-vanilla-monorepo.html)
- [Fork Maintenance Best Practices](https://github.blog/developer-skills/github/friend-zone-strategies-friendly-fork-management/)
- [setuptools-odoo](https://pypi.org/project/setuptools-odoo/)
- [Kubernetes StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
- [Docker Multi-Stage Builds](https://docs.docker.com/build/building/multi-stage/)
