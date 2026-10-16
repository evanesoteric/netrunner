#!/usr/bin/env bash
# Local development: rebuilding with this command erases all accounts and saves.
set -euo pipefail
cd "$(dirname "$0")/.."
echo 'Fresh development build: all accounts, saves, and game progress will be erased.'
docker compose down
docker compose build
docker compose up -d --wait db
docker compose run --rm --no-deps backend python backend/manage.py reset_dev --confirm ERASE-ALL-DATA
docker compose up -d --no-build
