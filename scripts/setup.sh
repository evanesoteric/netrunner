#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/pip install --no-cache-dir -r requirements.txt
npm ci --cache /workspace/.npm-cache --prefix frontend
bash scripts/install-postgres.sh
source scripts/local-db.sh
.venv/bin/python backend/manage.py migrate --noinput
.venv/bin/python backend/manage.py check
npm run build --prefix frontend
