# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3
#
# Loomworks ERP Docker Image
# Multi-stage build for optimized production image
#
# References:
# - Odoo Official Docker: https://hub.docker.com/_/odoo
# - Phase 5 Design: openspec/changes/phase5-infrastructure/design.md
#syntax=docker/dockerfile:1

# === Build Arguments ===
ARG PYTHON_VERSION=3.11
ARG LOOMWORKS_VERSION=1.0.0

# ============================================================================
# Stage 1: Build stage - Compile Python dependencies
# ============================================================================
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
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff5-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/loomworks/venv
ENV PATH="/opt/loomworks/venv/bin:$PATH"

# Install Python dependencies
# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip wheel setuptools \
    && pip install --no-cache-dir -r requirements.txt


# ============================================================================
# Stage 2: Runtime stage - Minimal production image
# ============================================================================
FROM python:${PYTHON_VERSION}-slim-bookworm

ARG LOOMWORKS_VERSION
LABEL org.opencontainers.image.title="Loomworks ERP"
LABEL org.opencontainers.image.description="AI-first ERP based on Odoo Community"
LABEL org.opencontainers.image.version="${LOOMWORKS_VERSION}"
LABEL org.opencontainers.image.vendor="Loomworks"
LABEL org.opencontainers.image.licenses="LGPL-3.0"
LABEL org.opencontainers.image.source="https://github.com/loomworks/loomworks-erp"

# Environment configuration
ENV PYTHONUNBUFFERED=1
ENV LANG=en_US.UTF-8
ENV PATH="/opt/loomworks/venv/bin:$PATH"
ENV ODOO_RC=/etc/loomworks/loomworks.conf
ENV LOOMWORKS_VERSION=${LOOMWORKS_VERSION}

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # PostgreSQL client for database operations
    postgresql-client \
    # PDF generation with wkhtmltopdf
    wkhtmltopdf \
    # Fonts for PDF rendering
    fonts-dejavu-core \
    fonts-dejavu-extra \
    fonts-noto-cjk \
    fonts-liberation \
    # XML/XSLT processing
    libxml2 \
    libxslt1.1 \
    # Image processing libraries
    libjpeg62-turbo \
    libfreetype6 \
    liblcms2-2 \
    libopenjp2-7 \
    libtiff6 \
    libpng16-16 \
    # LDAP support
    libldap-2.5-0 \
    libsasl2-2 \
    # SSL/TLS
    ca-certificates \
    # Node.js for frontend assets (rtlcss)
    nodejs \
    npm \
    # Network tools for healthchecks
    curl \
    # Process management
    dumb-init \
    && npm install -g rtlcss less \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /root/.npm \
    # Create odoo user and directories
    && useradd -r -m -d /opt/loomworks -s /bin/bash odoo \
    && mkdir -p /var/lib/loomworks /etc/loomworks /var/log/loomworks \
    && chown -R odoo:odoo /var/lib/loomworks /etc/loomworks /var/log/loomworks

# Copy virtual environment from builder
COPY --from=builder /opt/loomworks/venv /opt/loomworks/venv

# Copy Loomworks ERP source code
# Note: In CI/CD, this copies from the build context (repo root)
COPY --chown=odoo:odoo odoo /opt/loomworks/odoo
COPY --chown=odoo:odoo loomworks_addons /opt/loomworks/addons

# Copy configuration and scripts
COPY --chown=odoo:odoo infrastructure/docker/loomworks.conf /etc/loomworks/loomworks.conf
COPY --chown=odoo:odoo infrastructure/docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set working directory and user
WORKDIR /opt/loomworks
USER odoo

# Volumes for persistent data
# /var/lib/loomworks: Filestore, sessions, attachments
VOLUME ["/var/lib/loomworks"]

# Expose Odoo ports
# 8069: HTTP/HTTPS (main web interface)
# 8071: Gevent (websocket for real-time features)
# 8072: Longpolling (legacy bus)
EXPOSE 8069 8071 8072

# Health check endpoint
# Odoo provides /web/health for readiness checks
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8069/web/health || exit 1

# Use dumb-init to handle signals properly
ENTRYPOINT ["/usr/bin/dumb-init", "--", "/entrypoint.sh"]
CMD ["loomworks"]
