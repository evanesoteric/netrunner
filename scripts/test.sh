#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/local-db.sh
.venv/bin/python backend/manage.py test game --noinput
npm run build --prefix frontend
# Run scripts/dev.sh separately before the browser checks.
npm run test:e2e --prefix frontend
