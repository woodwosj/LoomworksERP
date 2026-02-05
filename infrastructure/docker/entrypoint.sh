#!/bin/bash
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This file is part of Loomworks ERP, a fork of Odoo Community.
# Original software copyright: Odoo S.A.
# Loomworks modifications copyright: Loomworks
# License: LGPL-3
#
# Docker entrypoint script for Loomworks ERP
# Handles database readiness checks and configuration generation

set -e

# ============================================================================
# Functions
# ============================================================================

wait_for_postgres() {
    local host="${DB_HOST:-db}"
    local port="${DB_PORT:-5432}"
    local max_attempts="${DB_MAX_ATTEMPTS:-30}"
    local attempt=1

    echo "Waiting for PostgreSQL at ${host}:${port}..."
    while [ $attempt -le $max_attempts ]; do
        if pg_isready -h "$host" -p "$port" -q 2>/dev/null; then
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

generate_config() {
    local config_file="${ODOO_RC:-/etc/loomworks/loomworks.conf}"

    # Only generate if file doesn't exist or REGENERATE_CONFIG is set
    if [ ! -f "$config_file" ] || [ "${REGENERATE_CONFIG:-false}" = "true" ]; then
        echo "Generating configuration at $config_file..."
        cat > "$config_file" << EOF
[options]
; Addons paths
addons_path = /opt/loomworks/odoo/addons,/opt/loomworks/addons

; Data directory for filestore
data_dir = /var/lib/loomworks

; Database configuration
db_host = ${DB_HOST:-db}
db_port = ${DB_PORT:-5432}
db_user = ${DB_USER:-odoo}
db_password = ${DB_PASSWORD:-odoo}
db_name = ${DB_NAME:-False}
db_sslmode = ${DB_SSLMODE:-prefer}
dbfilter = ${DB_FILTER:-.*}

; Admin password for database management
admin_passwd = ${ADMIN_PASSWD:-admin}

; Proxy configuration
proxy_mode = ${PROXY_MODE:-True}

; Worker configuration
workers = ${WORKERS:-4}
max_cron_threads = ${MAX_CRON_THREADS:-2}

; Memory limits (bytes)
limit_memory_hard = ${LIMIT_MEMORY_HARD:-2684354560}
limit_memory_soft = ${LIMIT_MEMORY_SOFT:-2147483648}

; Time limits (seconds)
limit_time_cpu = ${LIMIT_TIME_CPU:-600}
limit_time_real = ${LIMIT_TIME_REAL:-1200}
limit_time_real_cron = ${LIMIT_TIME_REAL_CRON:-3600}

; Logging
log_level = ${LOG_LEVEL:-info}
log_handler = ${LOG_HANDLER:-:INFO}
logfile = ${LOG_FILE:-}

; Server configuration
http_port = 8069
longpolling_port = 8072
http_interface = ${HTTP_INTERFACE:-0.0.0.0}

; Security
list_db = ${LIST_DB:-True}
server_wide_modules = base,web

; Performance tuning
osv_memory_age_limit = ${OSV_MEMORY_AGE_LIMIT:-1.0}
transient_age_limit = ${TRANSIENT_AGE_LIMIT:-1.0}

; SMTP Configuration (if needed)
smtp_server = ${SMTP_SERVER:-localhost}
smtp_port = ${SMTP_PORT:-25}
smtp_ssl = ${SMTP_SSL:-False}
smtp_user = ${SMTP_USER:-}
smtp_password = ${SMTP_PASSWORD:-}
email_from = ${EMAIL_FROM:-}
EOF
        echo "Configuration generated."
    fi
}

show_help() {
    echo "Loomworks ERP Container"
    echo ""
    echo "Usage: docker run loomworks-erp [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  loomworks       Start Loomworks ERP server (default)"
    echo "  shell           Start Odoo shell for interactive debugging"
    echo "  scaffold NAME   Create new module skeleton"
    echo "  test MODULE     Run tests for a module"
    echo "  upgrade MODULE  Upgrade a module"
    echo "  help            Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  DB_HOST         PostgreSQL host (default: db)"
    echo "  DB_PORT         PostgreSQL port (default: 5432)"
    echo "  DB_USER         PostgreSQL user (default: odoo)"
    echo "  DB_PASSWORD     PostgreSQL password (default: odoo)"
    echo "  DB_NAME         Database name (default: False = multi-db)"
    echo "  ADMIN_PASSWD    Master admin password"
    echo "  WORKERS         Number of workers (default: 4)"
    echo "  LOG_LEVEL       Log level (default: info)"
    echo ""
}

# ============================================================================
# Main entrypoint logic
# ============================================================================

case "${1}" in
    loomworks|odoo|"")
        wait_for_postgres
        generate_config
        echo "Starting Loomworks ERP..."
        exec python /opt/loomworks/odoo/odoo-bin \
            --config="$ODOO_RC" \
            "${@:2}"
        ;;

    shell)
        wait_for_postgres
        generate_config
        echo "Starting Loomworks shell..."
        exec python /opt/loomworks/odoo/odoo-bin shell \
            --config="$ODOO_RC" \
            "${@:2}"
        ;;

    scaffold)
        if [ -z "${2}" ]; then
            echo "Usage: scaffold MODULE_NAME [DESTINATION]"
            exit 1
        fi
        exec python /opt/loomworks/odoo/odoo-bin scaffold "${@:2}"
        ;;

    test)
        if [ -z "${2}" ]; then
            echo "Usage: test MODULE_NAME"
            exit 1
        fi
        wait_for_postgres
        generate_config
        echo "Running tests for module: ${2}"
        exec python /opt/loomworks/odoo/odoo-bin \
            --config="$ODOO_RC" \
            --test-enable \
            --stop-after-init \
            -i "${2}" \
            "${@:3}"
        ;;

    upgrade)
        if [ -z "${2}" ]; then
            echo "Usage: upgrade MODULE_NAME"
            exit 1
        fi
        wait_for_postgres
        generate_config
        echo "Upgrading module: ${2}"
        exec python /opt/loomworks/odoo/odoo-bin \
            --config="$ODOO_RC" \
            --stop-after-init \
            -u "${2}" \
            "${@:3}"
        ;;

    help|--help|-h)
        show_help
        exit 0
        ;;

    *)
        # Pass through any other commands
        exec "$@"
        ;;
esac
