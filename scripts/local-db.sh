#!/usr/bin/env bash
# Source this file to start the private development database and export PG*.
set -euo pipefail
NETRUNNER_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NETRUNNER_PG_BIN="${NETRUNNER_PG_BIN:-/workspace/.netrunner-tools/postgres/usr/lib/postgresql/17/bin}"
if [[ ! -x "$NETRUNNER_PG_BIN/pg_ctl" ]]; then
  echo 'PostgreSQL binaries missing. Run scripts/install-postgres.sh or set NETRUNNER_PG_BIN.' >&2
  return 1 2>/dev/null || exit 1
fi
mkdir -p "$NETRUNNER_ROOT/.local"
chmod 700 "$NETRUNNER_ROOT/.local"
export PGHOST="$NETRUNNER_ROOT/.local/socket" PGPORT=5432 PGUSER=netrunner PGDATABASE=netrunner
mkdir -p "$PGHOST"
chmod 700 "$PGHOST"
NETRUNNER_PG_DATA="$NETRUNNER_ROOT/.local/pgdata"
if [[ ! -f "$NETRUNNER_PG_DATA/PG_VERSION" ]]; then
  "$NETRUNNER_PG_BIN/initdb" -D "$NETRUNNER_PG_DATA" -U netrunner --auth-local=trust --auth-host=scram-sha-256 --encoding=UTF8 --locale=C.UTF-8 > "$NETRUNNER_ROOT/.local/initdb.log"
fi
if ! "$NETRUNNER_PG_BIN/pg_ctl" -D "$NETRUNNER_PG_DATA" status >/dev/null 2>&1; then
  "$NETRUNNER_PG_BIN/pg_ctl" -D "$NETRUNNER_PG_DATA" -l "$NETRUNNER_ROOT/.local/postgres.log" -o "-k $PGHOST -h ''" -w start
fi
if ! "$NETRUNNER_PG_BIN/psql" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='netrunner'" | rg -q '^1$'; then
  "$NETRUNNER_PG_BIN/createdb" netrunner
fi
"$NETRUNNER_PG_BIN/pg_isready"
