#!/bin/bash
set -euo pipefail

exec 200>/var/lock/postgis_maintenance.lock
flock -n 200 || { echo "Another instance is running"; exit 1; }

DB_HOST=${POSTGIS_HOST:?}
DB_USER=${POSTGIS_USER:?}
DB_PASS=${POSTGIS_PASSWORD:?}
DB_NAME=${POSTGIS_DB:-postgres}
DRY_RUN=${DRY_RUN:-false}

export PGPASSWORD="$DB_PASS"

echo "Starting maintenance (Dry run: $DRY_RUN)..."

psql -v ON_ERROR_STOP=1 -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" <<EOF
SELECT auto_maintain_indexes(p_dry_run => $DRY_RUN);
EOF

echo "Maintenance completed successfully."