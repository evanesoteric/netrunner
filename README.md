# Netrunner

A browser-based hacker game inspired by the atmosphere of Uplink. Django 5.2 and PostgreSQL 17 own the game state; Vue 3 and Vite power the interface. Hacking takes place entirely inside a fictional, simulated network.

## Playable first slice

- Create an account or sign in with a runner handle and passphrase.
- Maintain three independent save slots, enforced by database constraints.
- Accept broker contracts at your rank, one above, or one below.
- Complete `scan → breach → extract → wipe → disconnect` in the remote terminal before its 180-second trace window expires. `help` lists commands; `abort` abandons the job.
- Earn **Cipher (CPH)**, a provisional fictional currency with no blockchain integration. Payments and purchases appear in each save's separate bank terminal.
- Gain reputation and rise through Ghost, Signal, Operator, Spectre, and Architect at 0, 100, 250, 450, and 700 reputation. Failed/abandoned contracts deduct 60 reputation, with a floor of zero; ranks can fall.
- Upgrade hardware, gateway, and software independently from levels 1–5. System power is their sum; contracts require `3 + 2 × contract rank`. Upgrades cost `base price × current level²`.

All game mutations are authenticated, protected by CSRF, and scoped to the save owner. Financial and mission updates lock the save row within a PostgreSQL transaction. Contract rewards are awarded only once per completed mission. Contracts are currently repeatable; ranks, upgrade prices, and currency are centralized in `backend/game/catalog.py`.

## Download and run on your computer

Install Docker Desktop (Windows/macOS) or Docker Engine with Compose (Linux). Extract the source ZIP, open a terminal in the extracted `netrunner` directory, and run:

```bash
docker compose up --build
```

When Django finishes migrations and Vite reports ready, open `http://localhost:5173` **on your own computer**. Register an account, then initialize a save slot. The first run downloads images and dependencies. The database is stored in a Docker volume and survives stopping and restarting the application.

Stop with Ctrl+C, then `docker compose down`. Start again with `docker compose up`. To rebuild after code changes, use `docker compose up --build`. Avoid `docker compose down -v` unless you intend to delete all local game saves.

If port 5173 is busy, create a `.env` file next to `compose.yaml` containing `NETRUNNER_HTTP_PORT=5273`, then use port 5273 in your browser. The container setup is for local testing, with development-only database credentials and debug mode enabled.

Run the backend tests in Docker while the stack is running:

```bash
docker compose exec backend python backend/manage.py test game --noinput
```

The native cloud setup and application tests have been verified. The Compose configuration validates, but a complete container build could not be verified inside this cloud machine because its DNS/proxy trust configuration is not inherited by Docker builds.

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

This runs the Django suite against a separate PostgreSQL test database, builds Vue, and runs Chromium browser tests. The database role needs permission to create the test database. Browser tests create accounts prefixed `e2e_` in the development database. They test registration, three slots, contract execution, payouts, bank entries, upgrades, sign-out/sign-in, persistence, mobile layout, and server validation. Set `CHROMIUM_PATH` if Chromium is not at `/usr/bin/chromium`.

Backend-only checks:

```bash
source scripts/local-db.sh
.venv/bin/python backend/manage.py test game --noinput
.venv/bin/python backend/manage.py check
```

## Project map

- `backend/game/models.py`: save slots and financial ledger.
- `backend/game/catalog.py`: currency, rank thresholds, contracts, upgrade pricing.
- `backend/game/views.py`: session authentication and transactional game API.
- `frontend/src/App.vue`: Vue views, terminal, and API client.
- `frontend/src/style.css`: responsive interface, including ANSI bright green `#00ff00` terminal output.
- `scripts/`: repeatable setup, database, startup, and validation commands.

## Scope and next steps

This is a development prototype, not a production deployment. Missions currently use a fixed five-command sequence and a server-validated trace deadline; elapsed missions resolve when the next command is submitted. There is no background simulation, email recovery, transfer system, real cryptocurrency, or external network hacking. Upgrade power controls target access; richer equipment effects, generated contracts, and narrative events are future gameplay work.

Before public hosting, add authentication rate limiting and password recovery, use a production WSGI/ASGI server and managed PostgreSQL with proper credentials, serve the built frontend behind HTTPS, set `DJANGO_DEBUG=0`, provide a unique secret key and exact allowed hosts/trusted origins, and run Django deployment checks. External Google fonts are optional; local font fallbacks are included.
