# Netrunner

A browser-based hacker game inspired by the atmosphere of Uplink. Django 5.2 and PostgreSQL 17 own the game state; Vue 3 and Vite power the interface. Hacking takes place entirely inside a fictional, simulated network.

## v0.3 — sidebar services and server directory

Cipher bank, the contract broker, and Atlas are available directly from the left sidebar, including on mobile. These shortcuts launch/open the same applications and respect their existing RAM requirements.

Atlas routes chain **individual named servers**, such as `Intel Corp: Public Access → MilTech Research Center → NY Public Library Terminal`. Each server has its own fictional address, organization, category, clearance, fee, and trace delay; geography remains a secondary map coordinate.

Use **Atlas → Network directory** to search the 12 listed servers and filter by server type or saved entries. **Add to Atlas** saves a server in the current runner's personal directory and makes it visible on their routing map. **Remove from Atlas** removes that bookmark and prunes the server from their committed proxy chain while preserving the remaining hop order. Directory changes save immediately; routing changes still use **Commit route**. Live remote connections lock directory and route edits. Bookmarking a restricted server does not bypass its proxy clearance.

New runners start with Intel, MilTech, NY Library, and Northstar University in Atlas. Migration `0003_atlas_server_directory` preserves all 12 previously visible nodes for existing saves, along with committed routes, route costs, balances, and live sessions. Restarting a slot restores the new four-server starter directory.

Back up the database, pull `main`, and rebuild as shown below. Django applies the migrations automatically.

## Operator desktop

- **Persistent terminal focus:** Enter and button submissions keep the command input focused, including failed requests. Up/Down recalls command history. Output can still be selected, and Tab can leave the terminal.
- **Independent launchers:** the top bar launches the local terminal; the sidebar opens Atlas, the broker, and Cipher bank; the application launcher also starts the exchange and each installed tool. Running processes have their own consoles and share your machine's RAM. Closing a window does not disconnect a remote session.
- **Custom machines:** 40 named hardware products across five tiers: two processors, gateways, memory modules, and drives per tier. Hardware purchases enter inventory and must be fitted. Spare components can be sold at half price.
- **Specialized software:** 50 individual licenses: Cartograph network mappers, Lockpick authentication crackers, Rosetta decryptors, Ashfall log cleaners, and Tripwire trace monitors. Each has five capability classes and Pro/Micro variants. Micro trades speed for lower memory use. Purchased tools must be launched separately.
- **World routing:** Atlas contains named fictional servers at 12 map locations. Select an ordered proxy chain, reorder/remove hops, and commit it. The route is drawn from your home gateway through the proxies to the reserved target. Pan and zoom the map or use the accessible saved-server list. Routes remain committed across sessions.
- **Manual contracts:** reserve and submit assignments through the local shell. The broker publishes target, artifact, objective, clearance, and reward. There are retrieval, encrypted recovery, and deletion jobs at each rank.
- **An economy with consequences:** routing leases and tool computation consume Cipher (CPH). Failed jobs cost up to `90 + 80 × job rank` CPH and 60 reputation (both balances floor at zero). Completed jobs return after five minutes; failed ones after ten, using server time. A bankrupt runner can sell spare equipment or explicitly restart that slot by typing their alias.

Accounts retain three independent saves. Ranks are Ghost, Signal, Operator, Spectre, and Architect at 0, 100, 250, 450, and 700 reputation. Contracts are available at the runner's rank, one rank above, and one below. Products are purchasable through tier `min(5, rank + 2)`.

### Tool reference

Each console has its own `help` manual. Commands run entirely inside the game's simulation; they never execute OS commands or access an external target.

| Application | Commands / purpose |
| --- | --- |
| Local terminal | `apps`, `contracts`, `accept <id>`, `brief`, `route`, `connect <host>`, `status`, `ls`, `get <file>`, `rm <file>`, `disconnect`, `submit`, `abort`, `clear` |
| Cartograph | `scan <host>` discovers authentication ports and archive metadata |
| Lockpick | `crack <port>` works against a discovered service with sufficient tool capability |
| Rosetta | `decrypt <file>` operates on an accessible encrypted archive |
| Ashfall | `erase` removes remote access logs; later remote operations leave new logs |
| Tripwire | `trace` reads the live trace; keep a capable monitor running for the desktop countdown |
| Cipher bank | `balance`, `history` display this save's independent account |

The trace begins when the player connects, not when reserving a contract. Wall-clock time and simulated computation both consume it. CPU speed and tool speed affect computation time. Gateway stealth and proxy delays extend trace time; gateway bandwidth affects transfers. Hop order changes geographical latency. Connections and equipment changes lock the route while online. Copying a file does not automatically complete a contract: the broker verifies objective evidence and a clean exit before paying a manual submission. Higher security can defeat underpowered tools, encrypted files require a decryptor, and local disk space must fit the recovered archive.

Every mutation checks authentication, CSRF, save ownership, and current game state. PostgreSQL row locks protect financial updates and mission completion from concurrent/replayed requests. The test suite exercises both concurrent payment and purchase requests.

### Upgrade an existing installation

Back up your database first. With the old Docker stack running:

```bash
docker compose exec -T db pg_dump -U netrunner netrunner > ../netrunner-before-v0.3.sql
```

Then pull and rebuild:

```bash
git pull --ff-only origin main
docker compose up --build
```

Django automatically applies pending migrations, including `0002_runner_desktop` and `0003_atlas_server_directory`. Existing balances, reputation, completed contracts, saves, and ledger entries are preserved. Old hardware/gateway levels map to named components; old software levels map to appropriate tool licenses. An active v0.1 session is safely closed without a fine or reputation loss. Newly launched applications start from the desktop. Back up before rolling versions back: the old schema cannot represent the new loadout and process state.

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

This runs the Django suite against a separate PostgreSQL test database, builds Vue, and runs Chromium browser tests. The database role needs permission to create the test database. Browser tests create accounts prefixed `e2e_` in the development database. They verify the manual tools-and-proxy contract loop, persistent cursor focus (including failed requests), bank charges, purchases/fitting/resale, three saves, sign-in persistence, confirmed bankruptcy recovery, and mobile layouts. Set `CHROMIUM_PATH` if Chromium is not at `/usr/bin/chromium`.

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

This is a development prototype with a fictional network. Contracts are a finite authored pool that recycles after cooldowns. Failure is determined by tools, funds, memory, storage, trace time, and remote evidence; there is no hidden random success roll. Timers are checked on server requests, with the desktop polling active connections every five seconds. Closing the browser does not pause a trace. All running processes represent game state, not real software execution.

Future gameplay can add generated clients and stories, relay outages, richer remote filesystems, consumable exploits, hardware compatibility, and recurring operating expenses. There is no email recovery, transfer system, real cryptocurrency, or external network hacking.

Before public hosting, add authentication rate limiting and password recovery, use a production WSGI/ASGI server and managed PostgreSQL with proper credentials, serve the built frontend behind HTTPS, set `DJANGO_DEBUG=0`, provide a unique secret key and exact allowed hosts/trusted origins, and run Django deployment checks. External Google fonts are optional; local font fallbacks are included.
