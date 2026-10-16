#!/usr/bin/env bash
# PostgreSQL custom archives stay in the bind mount, avoiding binary shell redirection.
set -euo pipefail
cd "$(dirname "$0")/.."
action="${1:-}"
archive="${2:-netrunner-$(date -u +%Y%m%dT%H%M%SZ).dump}"
if [[ ! "$archive" =~ ^[a-zA-Z0-9][a-zA-Z0-9._-]*\.dump$ ]]; then
  echo 'Use a filename such as snapshot.dump (no directory components).' >&2; exit 1
fi
case "$action" in
  backup)
    docker compose up -d --wait db
    docker compose exec -T db test ! -e "/backups/$archive"
    docker compose exec -T db pg_dump -U netrunner -d netrunner --format=custom --no-owner --no-acl --file="/backups/$archive"
    echo "Backup saved: .data/backups/$archive"
    ;;
  restore)
    [[ "${3:-}" == 'ERASE-ALL-DATA' ]] || { echo 'Restore replaces ALL current data. Add ERASE-ALL-DATA as the third argument.' >&2; exit 1; }
    docker compose up -d --wait db
    docker compose exec -T db pg_restore --list "/backups/$archive" >/dev/null
    docker compose stop backend
    docker compose exec -T db dropdb -U netrunner --if-exists --force netrunner
    docker compose exec -T db createdb -U netrunner netrunner
    docker compose exec -T db pg_restore -U netrunner -d netrunner --no-owner --no-acl --exit-on-error --single-transaction "/backups/$archive"
    docker compose run --rm --no-deps backend python backend/manage.py prepare_dev --preserve
    docker compose up -d --no-build backend frontend
    echo "Restored .data/backups/$archive"
    ;;
  *) echo 'Usage: bash scripts/database.sh backup [name.dump] | restore name.dump ERASE-ALL-DATA' >&2; exit 1 ;;
esac
