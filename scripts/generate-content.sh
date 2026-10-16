#!/usr/bin/env bash
# Offline development admin CLI. Start PostgreSQL first; the web app can stay stopped.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose run --rm --no-deps backend python backend/manage.py generate_content "$@"
