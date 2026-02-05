#!/bin/bash
# PostgreSQL initialization script for Loomworks ERP
# Part of Loomworks ERP. See LICENSE file for full copyright and licensing details.
#
# This script runs on first database initialization to:
# 1. Create WAL archive directory
# 2. Set up permissions
# 3. Create initial database if specified

set -e

# Ensure WAL archive directory exists and has correct permissions
mkdir -p /wal_archive
chown postgres:postgres /wal_archive
chmod 700 /wal_archive

echo "WAL archive directory configured at /wal_archive"

# Create initial Loomworks database if DB_NAME is specified
if [ -n "$LOOMWORKS_DB_NAME" ]; then
    echo "Creating initial database: $LOOMWORKS_DB_NAME"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
        CREATE DATABASE "$LOOMWORKS_DB_NAME"
            WITH OWNER = "$POSTGRES_USER"
            ENCODING = 'UTF8'
            LC_COLLATE = 'en_US.UTF-8'
            LC_CTYPE = 'en_US.UTF-8'
            TEMPLATE = template0;

        -- Grant privileges
        GRANT ALL PRIVILEGES ON DATABASE "$LOOMWORKS_DB_NAME" TO "$POSTGRES_USER";
EOSQL
    echo "Database $LOOMWORKS_DB_NAME created successfully"
fi

echo "PostgreSQL initialization complete"
