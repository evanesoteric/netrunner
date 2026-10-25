# Development and maintenance

Run the commands below from the repository root. Linux/Bash examples precede PowerShell equivalents.

### Development builds erase the old database

```bash
git pull --ff-only origin main
docker compose up --build
```

A changed backend or frontend image fingerprint triggers **DROP DATABASE, CREATE DATABASE, and Django migrations** before the backend starts. This removes all accounts, saves, sessions, and game progress. It leaves backup archives intact. The first v0.5 startup also resets an existing development database. Ordinary container restarts preserve data. Rebuilding identical cached source keeps the same fingerprint and also preserves data.

To force an empty database every cycle, even with unchanged source:

Linux / Bash:

```bash
bash scripts/fresh-build.sh
```

PowerShell:

```powershell
.\scripts\fresh-build.ps1
```

These scripts stop the stack, force a fresh build identity, drop/recreate the database, and restart. Refresh your browser and register again afterward.

To explicitly reset without rebuilding, stop the backend first:

```bash
docker compose stop backend
docker compose run --rm --no-deps backend python backend/manage.py reset_dev --confirm ERASE-ALL-DATA
docker compose up -d --no-build
```

Reset commands require `DJANGO_DEBUG=1` and refuse PostgreSQL maintenance databases. This is a local development policy. To retain progress across changed builds, set `NETRUNNER_RESET_ON_BUILD=0` in your root `.env` before starting Compose; migrations still run.

### Export and import with PostgreSQL tools

Create a consistent custom-format `pg_dump` archive without stopping the app:

Linux / Bash:

```bash
bash scripts/database.sh backup snapshot.dump
```

PowerShell:

```powershell
.\scripts\database.ps1 backup snapshot.dump
```

The file is **`.data/backups/snapshot.dump`** on your computer. Omit the filename to generate a timestamped name. Existing archives are never overwritten. Copy these archives to another disk for durable backups; automatic backup scheduling is not implemented yet.

Import an archive from `.data/backups/`, replacing the current database:

Linux / Bash:

```bash
bash scripts/database.sh restore snapshot.dump ERASE-ALL-DATA
```

PowerShell:

```powershell
.\scripts\database.ps1 restore snapshot.dump -Confirmation ERASE-ALL-DATA
```

Restore checks the archive listing, stops the backend, drops/recreates the database, and runs `pg_restore --single-transaction --exit-on-error`. It migrates the restored schema and records the current image fingerprint before restarting, so startup keeps the imported data. If restoration fails, the backend stays stopped; the archive remains available to retry. Restore trusted archives only. These scripts run PostgreSQL tools inside the database container, avoiding PowerShell binary-output redirection problems. They preserve game state and IDs, but do not export cluster roles or PostgreSQL server configuration.

### Existing Docker volumes

Before v0.4, PostgreSQL used a Docker-managed `netrunner-db` volume. That unmounted volume is retained as a recovery option; it is not automatically imported. `docker compose down -v` does not erase the bind-mounted `.data/` directories. The native cloud workflow uses its separate ignored `.local/pgdata` directory and ordinary migration startup; use the explicit development reset command there when needed.

## Download and run on your computer

Install Docker Engine with Compose (Linux) or Docker Desktop (Windows/macOS). Clone this repository, open a terminal in the `netrunner` directory, and run:

```bash
docker compose up --build
```

When Django finishes migrations and Vite reports ready, open `http://localhost:5173` **on your own computer**. Register an account, then initialize a save slot. The first run downloads images and dependencies. The database is stored in the ignored `.data/postgres/` folder and survives stopping and restarting the application. Use the fresh-build scripts above for a clean development cycle.

Stop with Ctrl+C, then `docker compose down`. Start again with `docker compose up`. To rebuild after code changes, use `docker compose up --build`. Changed builds reset the database; the fresh-build scripts force a reset even with cached source; `down -v` does not remove bind-mounted files.

If port 5173 is busy, create a `.env` file next to `compose.yaml` containing `NETRUNNER_HTTP_PORT=5273`, then use port 5273 in your browser. The container setup is for local testing, with development-only database credentials and debug mode enabled.

Run the backend tests in Docker while the stack is running:

```bash
docker compose exec backend python backend/manage.py test game --noinput
```

The native cloud setup and application tests have been verified. The Compose configuration validates, but a complete container build could not be verified inside this cloud machine because its DNS/proxy trust configuration is not inherited by Docker builds. PowerShell is not installed in this cloud workspace, so the PowerShell wrappers have not been executed here.

## Run in the cloud workspace

Prerequisites: Python 3.12+, Node 22.12+ (24 recommended), and Debian 13 for the included non-root PostgreSQL installer. Use the existing checkout at `/workspace/netrunner`; tasks already have an isolated environment, so no extra Git worktree is needed.

```bash
cd /workspace/netrunner
bash scripts/setup.sh
bash scripts/dev.sh
```

The development script starts Django on port 8000 and Vue on port 5173. Vue proxies `/api` to Django. Stop the script to stop those two servers. PostgreSQL remains running and can be stopped separately:

```bash
source scripts/local-db.sh
"$NETRUNNER_PG_BIN/pg_ctl" -D "$NETRUNNER_PG_DATA" -w stop
```

The local database uses a private Unix socket, no TCP listener, and a directory accessible only to the current user. Its local trust authentication is for development only. Data lives in ignored `.local/pgdata`; dependencies and generated outputs are also ignored. The installer extracts PostgreSQL from Debian packages verified through signed APT metadata, outside the checkout under `/workspace/.netrunner-tools`.

On another OS, install PostgreSQL and set `NETRUNNER_PG_BIN` to its executable directory, or manage PostgreSQL separately and export the `PG*` variables in `.env.example`. The app reads exported variables; it does not load `.env` automatically. To use a separately managed database, run migrations and the two development servers directly instead of `scripts/dev.sh`.

## Validate

With `scripts/dev.sh` running:

```bash
bash scripts/test.sh
```

This runs the Django suite against a separate PostgreSQL test database, builds Vue, and runs Chromium browser tests. The database role needs permission to create the test database and a disposable lifecycle database. The lifecycle check uses `pg_dump` and `pg_restore` from PATH or `NETRUNNER_PG_BIN`, and verifies actual drop/recreation, restart persistence, and an archive round trip including generated content, backdoors, pending operations, Field Notes, workspace arrangements, local files, and persistent server journals. It is skipped if those client tools are unavailable. Browser tests create accounts prefixed `e2e_` in the development database. They verify complete multi-tool workspace contracts, drag/resize persistence, layout conflicts, mobile stacking, notebook autosave, conflicting edits and draft recovery, persistent server maintenance, hidden-market purchases, persistent direct backdoors, ransomware deployment, the manual tools-and-proxy contract loop, persistent cursor focus (including failed requests), bank charges, purchases/fitting/resale, three saves, sign-in persistence, confirmed bankruptcy recovery, and mobile layouts. The epic-market browser scenario uses the native Django environment to seed an offline test account with funds and memory; no public cheat API is provided. Set `CHROMIUM_PATH` if Chromium is not at `/usr/bin/chromium`.

Backend-only checks:

```bash
source scripts/local-db.sh
.venv/bin/python backend/manage.py test game --noinput
.venv/bin/python backend/manage.py check
```

## Project map

- `backend/game/models.py`: save slots, owned products, running processes, routes, mission state, and ledger.
- `backend/game/catalog.py`: named products, servers, currency, jobs, ranks, and cooldowns.
- `backend/game/mechanics.py`: deterministic command simulation, routing, compute costs, traces, trade, and contract evidence.
- `backend/game/views.py`: authentication and transactional game API.
- `frontend/src/components/TerminalConsole.vue`: focus, command input, per-app history and output.
- `frontend/src/components/NetworkMap.vue`: world map, pan/zoom, ordered proxy editor and personal server directory.
- `frontend/src/components/AppLauncher.vue`: system applications and installed software.
- `frontend/src/components/ExchangeView.vue`: individual product inventory and trading.
- `scripts/`: setup, database, startup, and validation commands.

## Scope and future development

This is a development prototype with a fictional network. Contracts combine authored content with fresh per-save assignments; accepted jobs are never reoffered to that runner. Failure is determined by tools, funds, memory, storage, trace time, and remote evidence; there is no hidden random success roll. Timers are checked on server requests, with active connections, pending operations, and the broker page refreshing automatically. Closing the browser does not pause a trace. All running processes represent game state, not real software execution.

Future gameplay can add generated clients and stories, relay outages, richer remote filesystems, consumable exploits, hardware compatibility, and recurring operating expenses. There is no email recovery, transfer system, real cryptocurrency, or external network hacking.

Before public hosting, add authentication rate limiting and password recovery, use a production WSGI/ASGI server and managed PostgreSQL with proper credentials, serve the built frontend behind HTTPS, set `DJANGO_DEBUG=0`, provide a unique secret key and exact allowed hosts/trusted origins, and run Django deployment checks. External Google fonts are optional; local font fallbacks are included.

## Offline content generation

`generate_content` is a local Django management command, available only with `DJANGO_DEBUG=1`. It has no web endpoint and needs no external service. After the initial fresh build, PostgreSQL must be running and migrated; the backend web server may be stopped while you author content.

Linux / Bash:

```bash
docker compose stop backend
bash scripts/generate-content.sh missions --count 5 --rank 0
bash scripts/generate-content.sh missions --count 2 --rank 1 --objective retrieve --encrypted
bash scripts/generate-content.sh servers --count 5 --rank 0
bash scripts/generate-content.sh servers --count 4 --rank 0 --exploitable
bash scripts/generate-content.sh missions --count 3 --rank 0 --service wordpress
bash scripts/generate-content.sh servers --count 3 --rank 0 --service sip
docker compose up -d --no-build
```

On the native cloud setup:

```bash
source scripts/local-db.sh
.venv/bin/python backend/manage.py generate_content missions --count 5 --rank 0
.venv/bin/python backend/manage.py generate_content servers --count 4 --rank 0 --exploitable
```

PowerShell:

```powershell
docker compose stop backend
.\scripts\generate-content.ps1 missions --count 5 --rank 0
.\scripts\generate-content.ps1 missions --count 2 --rank 1 --objective retrieve --encrypted
.\scripts\generate-content.ps1 servers --count 5 --rank 0
.\scripts\generate-content.ps1 servers --count 4 --rank 0 --exploitable
.\scripts\generate-content.ps1 missions --count 3 --rank 0 --service wordpress
.\scripts\generate-content.ps1 servers --count 3 --rank 0 --service sip
docker compose up -d --no-build
```

Ranks are 0 Ghost through 4 Architect. Each call creates unique server addresses and mission identities. Missions receive unused numbers from the existing 0–255 pool; a request exceeding remaining capacity fails without creating partial content. Use `--objective retrieve` or `--objective delete` for a specific mission type; `--encrypted` creates encrypted retrieval jobs. Omitting both chooses randomly. Generated proxy servers appear in Atlas's directory on the next refresh and can be bookmarked and routed through. `--exploitable` gives a server an amber opportunity marker and ransomware eligibility.

Generated content lives in PostgreSQL and is included in normal `pg_dump` archives. Development database resets erase it along with accounts; back it up before another fresh build. These commands generate new content without changing or deleting existing content.



The offline generator's `--service` option accepts `ssh`, `http`, `rdp`, `wordpress`, `php`, `sip`, `telnet`, `ftp`, `smtp`, `mysql`, and `redis`. Omitting it randomly selects a supported service. Ports and application release banners come from `backend/game/services.py`. Adding a new family there makes it available to the generator and IRC; authored contract assignments live in `backend/game/catalog.py`. Persistent discovered servers keep their saved service identity. Service profiles model fictional game access, not real vulnerabilities.


### Authoring mission file placement

Follow the [offline content generation setup](#offline-content-generation) above before running these examples.

Generated missions use mixed placement by default: roughly 70 percent at root and 30 percent in their service's normal directory. Background folders and files are automatic for generated contracts and directory servers. Use explicit options when authoring a particular mission:

```bash
bash scripts/generate-content.sh missions --count 3 --rank 0 --service wordpress --objective retrieve --filename users.db --artifact-dir /var/www
bash scripts/generate-content.sh missions --count 3 --rank 0 --service rdp --placement nested
bash scripts/generate-content.sh missions --count 3 --rank 0 --service mysql --placement root
```

```powershell
.\scripts\generate-content.ps1 missions --count 3 --rank 0 --service wordpress --objective retrieve --filename users.db --artifact-dir /var/www
.\scripts\generate-content.ps1 missions --count 3 --rank 0 --service rdp --placement nested
.\scripts\generate-content.ps1 missions --count 3 --rank 0 --service mysql --placement root
```

`--filename` accepts a basename (up to 64 characters), and `--artifact-dir` accepts an absolute virtual directory (up to 70 characters). An explicit directory overrides random placement. These options apply only to missions. The authoring command prints the actual artifact path for review; the broker shows the filename without exposing the hidden directory. Target addresses and contract identities remain unique even when multiple missions use the same filename.

Templates and service paths live in `backend/game/filesystem.py`; terminal actions live in `backend/game/remote_files.py`. Each tree stays bounded, and paths are normalized entirely inside the game's JSON filesystem. No file command invokes the host shell or operates on real paths.


### Authoring erase all copies contracts

Add `--delete-copy /absolute/file/path` to require an additional backup deletion. Repeat it for up to four backups (five required files including the primary). Follow the [offline generation prerequisites](#offline-content-generation) first.

```bash
bash scripts/generate-content.sh missions --count 1 --rank 0 --service ssh --objective delete --filename audit.txt --artifact-dir /root --delete-copy /bak/audit.log
bash scripts/generate-content.sh missions --count 1 --rank 0 --service wordpress --objective delete --filename users.db --artifact-dir /var/www --delete-copy /backup/nightly/users.db
```

```powershell
.\scripts\generate-content.ps1 missions --count 1 --rank 0 --service ssh --objective delete --filename audit.txt --artifact-dir /root --delete-copy /bak/audit.log
.\scripts\generate-content.ps1 missions --count 1 --rank 0 --service wordpress --objective delete --filename users.db --artifact-dir /var/www --delete-copy /backup/nightly/users.db
```

The option selects a deletion mission if `--objective` is omitted. It cannot be combined with retrieval, encryption, or directory-server generation. Every required file path must be distinct and cannot conflict with a directory. The generator creates the actual required copies and puts their exact paths in the broker brief. It does not make every other backup on that server an objective. Requirements, file states and per-path receipts persist in PostgreSQL and normal backups.


### Persistent fictional addresses

Migration 0015 creates `NetworkAddress`, mapping each canonical virtual host to a unique fictional IPv4 address. Addresses are assigned on first lookup and retained in normal PostgreSQL backups. Allocation uses the documentation ranges before falling back to private 10/8; concurrent lookups for one host return the same committed mapping. Requests preload existing mappings to avoid an individual lookup for every directory row.

Keep existing `target`/`address` host keys when authoring or importing saved content. They preserve filesystem state, routes, contract evidence and old command aliases. The API adds `ip_address`, `target_name`, `remote_ip`, `remote_name` and `target_directory` for display. Generated missions include organization and specific server labels; the web client presents these names and the assigned IP rather than requiring legacy `.internal` aliases. Address resolution does not bypass directory visibility, rank checks or ownership of a private mission.
