param(
    [Parameter(Mandatory=$true)][ValidateSet("backup", "restore")][string]$Action,
    [string]$Archive = ("netrunner-" + (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ") + ".dump"),
    [string]$Confirmation = ""
)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
function Invoke-NetrunnerDocker {
    & docker @args
    if ($LASTEXITCODE -ne 0) { throw "Docker command failed with exit code $LASTEXITCODE." }
}
if ($Archive -cnotmatch '^[a-zA-Z0-9][a-zA-Z0-9._-]*\.dump$') { throw "Use a filename such as snapshot.dump (no directory components)." }
if ($Action -eq "restore" -and $Confirmation -cne "ERASE-ALL-DATA") { throw "Restore replaces ALL current data. Supply -Confirmation ERASE-ALL-DATA." }
Invoke-NetrunnerDocker compose up -d --wait db
if ($Action -eq "backup") {
    Invoke-NetrunnerDocker compose exec -T db test ! -e "/backups/$Archive"
    Invoke-NetrunnerDocker compose exec -T db pg_dump -U netrunner -d netrunner --format=custom --no-owner --no-acl "--file=/backups/$Archive"
    Write-Host "Backup saved: .data/backups/$Archive"
} else {
    Invoke-NetrunnerDocker compose exec -T db pg_restore --list "/backups/$Archive" | Out-Null
    Invoke-NetrunnerDocker compose stop backend
    Invoke-NetrunnerDocker compose exec -T db dropdb -U netrunner --if-exists --force netrunner
    Invoke-NetrunnerDocker compose exec -T db createdb -U netrunner netrunner
    Invoke-NetrunnerDocker compose exec -T db pg_restore -U netrunner -d netrunner --no-owner --no-acl --exit-on-error --single-transaction "/backups/$Archive"
    Invoke-NetrunnerDocker compose run --rm --no-deps backend python backend/manage.py prepare_dev --preserve
    Invoke-NetrunnerDocker compose up -d --no-build backend frontend
    Write-Host "Restored .data/backups/$Archive"
}
