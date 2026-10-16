# Offline development admin CLI. Start PostgreSQL first; the web app can stay stopped.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
& docker compose run --rm --no-deps backend python backend/manage.py generate_content @args
if ($LASTEXITCODE -ne 0) { throw "Content generation failed with exit code $LASTEXITCODE." }
