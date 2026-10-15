#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/local-db.sh
.venv/bin/python backend/manage.py migrate --noinput
.venv/bin/python backend/manage.py runserver 127.0.0.1:8000 --noreload &
NETRUNNER_API_PID=$!
node frontend/node_modules/vite/bin/vite.js --config frontend/vite.config.js --host 127.0.0.1 --port 5173 --strictPort frontend &
NETRUNNER_UI_PID=$!
trap 'kill "$NETRUNNER_API_PID" "$NETRUNNER_UI_PID" 2>/dev/null || true' EXIT INT TERM
wait -n "$NETRUNNER_API_PID" "$NETRUNNER_UI_PID"
