# Local development: rebuilding with this command erases all accounts and saves.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
function Invoke-NetrunnerDocker {
    & docker @args
    if ($LASTEXITCODE -ne 0) { throw "Docker command failed with exit code $LASTEXITCODE." }
}
Write-Host "Fresh development build: all accounts, saves, and game progress will be erased."
Invoke-NetrunnerDocker compose down
Invoke-NetrunnerDocker compose build
Invoke-NetrunnerDocker compose up -d --wait db
Invoke-NetrunnerDocker compose run --rm --no-deps backend python backend/manage.py reset_dev --confirm ERASE-ALL-DATA
Invoke-NetrunnerDocker compose up -d --no-build
