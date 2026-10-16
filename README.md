# Netrunner

A browser-based hacker game inspired by the atmosphere of Uplink. Django 5.2 and PostgreSQL 17 own the game state; Vue 3 and Vite power the interface. Hacking takes place entirely inside a fictional, simulated network.

## v0.8 — personal multi-tool Workspace

The sidebar now includes a separate **Workspace**. All previous screens and launchers remain available. Start with four panels—local terminal, Atlas, Cartograph, and Lockpick—then use **Launch visible tools** to start the available applications without leaving the page. Every console has its own command field, history, output, and cursor focus. A command updates the same runner state across all panels.

Use **Add a panel** to open built-in services, an owned software variant, Field Notes, Server Histories, or an unlocked black-market/backdoor service. Adding a tool launches it in place; adding an already-running tool reuses its process. Atlas routing, broker acceptance/abort, the exchange, bank commands, notes, histories, and Wraith connections all work inside panels. The main app's terminal launcher and process dock also open/focus panels while you are on Workspace.

On desktop, drag a panel's grip to move it or drag its lower corner to resize. Panels snap to a 12-column grid; overlapping panels move down into free space. Focus a grip or resize handle and use arrow keys for the same controls. Panel positions, sizes, visibility, and preferred software variants autosave to PostgreSQL for that save. Restore starter arrangement resets the panel arrangement without stopping processes.

**Remove panel** hides its window and leaves its process running. **Stop** closes the process and frees RAM. Launch visible tools stops at a launch failure rather than ignoring a RAM limit. Your existing hardware, ownership, trace, contract, and payment rules still apply: the workspace adds no free capabilities and does not automate mission steps.

At widths of 1050 px or less, panels stack vertically and layout handles are disabled. The saved desktop geometry is retained, so using a phone does not replace your desktop arrangement. Each panel scrolls independently.

Layout saves have visible status and Retry. Failed/unsaved arrangements have a per-tab browser recovery copy; conflicting edits in another window require Reload saved arrangement or Keep my arrangement. A restarted runner has a new layout identity, preventing delayed layout saves from restoring old preferences. Database backups include workspace preferences; restarting a save resets only its arrangement. The development fresh-build database reset policy still applies.

## v0.7 — Field Notes and persistent server histories

**Field Notes** is a sidebar notebook for the current save. It supports 50,000 characters and autosaves after 800 ms without typing. Saving status, manual Save now, failure messages, and Retry make persistence visible. Each save has its own PostgreSQL text, revision, and update time.

Switching panels keeps the editor and its draft alive. An unsaved recovery draft is also stored in this browser, scoped to the account, slot, and runner creation identity. Each tab keeps its own session recovery copy, with a browser-wide last-draft fallback. Failed saves survive a reload in the same browser; this recovery draft is not a database backup or cross-device sync. If browser storage is unavailable, the editor warns you. Closing a tab with unsaved edits prompts the browser's normal warning. Two windows editing older revisions receive a conflict instead of silently overwriting each other: inspect the saved version, then choose Use saved version or Save my draft. A delayed autosave from a restarted runner cannot write into the new life.

**Server Histories** is a sidebar journal of the servers this save has discovered. Contract targets, generated missions, directory servers, the hidden market, and Wraith links share durable identities by fictional hostname. Saves have independent server worlds. Visits, proxy transits, scans, authentication, file retrieval/deletion/decryption, remote log cleanup, connections, contract completion, rootkit installation, ransomware deployment/payment, and administrator maintenance are recorded. The local terminal's `history` command also shows recent events for its current or reserved target.

Files no longer reset when you reconnect. A removed archive stays missing; a decrypted archive stays readable. Remote access-log entries persist until cleared or archived by maintenance. Ashfall clears remote logs but leaves your private operator journal intact. The history viewer shows your **last observed** filesystem and service fingerprint, not an automatically refreshed scan, and supports loading older journal events.

Administrator maintenance is deterministic and processed on the next game request after its deadline, including after time away:

- Verified contracts schedule archive replacement at their five-minute broker cooldown.
- File deletion, detected intrusion, and completed ransomware operations schedule maintenance in ten minutes; an earlier existing deadline wins.
- Maintenance restores the original archive, moves it to `archive/r<revision>/<filename>`, rotates authentication ports between 22/2222 or 443/8443, and records the patch revision. Security capability classes remain stable.
- An active connection to that server postpones its maintenance until disconnect. Other servers can still undergo maintenance.
- Scan again after a patch: old fingerprints cannot authenticate the changed service. Use the current archive path shown by a scan or directory listing for `get`, `rm`, and `decrypt`. Broker briefs retain the original artifact name.

Wraith links remain installed across maintenance. Direct links still bypass proxy leases, suppress remote access logging, and have no trace countdown. Eclipse keeps the existing three-instance cap, two-minute duration, and payout values. The economy-balancing work remains deferred in [TODO.md](TODO.md).

Migration `0006` preserves known active mission state, deleted/decrypted artifacts, dirty logs, existing backdoors, and pending operations. It does not invent a history of visits from before this feature. Notes, server state, and journal events survive normal restarts, sign-out, and PostgreSQL dump/restore. Restarting a runner clears that save's notes and world histories along with its other progress; other saves are untouched. The existing development-build database reset policy still applies, so export before a fresh build if you want to retain progress.

## v0.6 — generated world content and the hidden market

### Offline development administration

`generate_content` is a local Django management command, available only with `DJANGO_DEBUG=1`. It has no web endpoint and needs no external service. After the initial fresh build, PostgreSQL must be running and migrated; the backend web server may be stopped while you author content.

PowerShell:

```powershell
docker compose stop backend
.\scripts\generate-content.ps1 missions --count 5 --rank 0
.\scripts\generate-content.ps1 missions --count 2 --rank 1 --objective retrieve --encrypted
.\scripts\generate-content.ps1 servers --count 5 --rank 0
.\scripts\generate-content.ps1 servers --count 4 --rank 0 --exploitable
docker compose up -d --no-build
```

Bash equivalents use `bash scripts/generate-content.sh` with the same arguments. On the native cloud setup:

```bash
source scripts/local-db.sh
.venv/bin/python backend/manage.py generate_content missions --count 5 --rank 0
.venv/bin/python backend/manage.py generate_content servers --count 4 --rank 0 --exploitable
```

Ranks are 0 Ghost through 4 Architect. Each call creates unique server addresses and mission identities. Missions receive unused numbers from the existing 0–255 pool; a request exceeding remaining capacity fails without creating partial content. Use `--objective retrieve` or `--objective delete` for a specific mission type; `--encrypted` creates encrypted retrieval jobs. Omitting both chooses randomly. Generated proxy servers appear in Atlas's directory on the next refresh and can be bookmarked and routed through. `--exploitable` gives a server an amber opportunity marker and ransomware eligibility.

Generated content lives in PostgreSQL and is included in normal `pg_dump` archives. Development database resets erase it along with accounts; back it up before another fresh build. These commands generate new content without changing or deleting existing content.

### Null Exchange and epic software

The hidden server is absent from a new runner's public directory. Enter `rumors` in the local terminal for an invitation, then `connect null-exchange.internal` while disconnected and without a reserved contract. This unlocks **Null Exchange** in that save's sidebar. It sells two perpetual epic licenses:

| Software | Price | RAM | Commands |
| --- | ---: | ---: | --- |
| Wraith Rootkit | 2,400 CPH | 3 GB | `install` in Wraith's console; later `jump <host>` in the local terminal |
| Eclipse Ransomware | 1,800 CPH | 3 GB | `deploy <host>` in Eclipse's console |

Purchase licenses at Null Exchange and launch them through Applications. Upgrade memory or close other tools if you exceed your RAM capacity. Each save has its own discovery state, licenses, backdoors, and operations.

**Backdoors:** scan a contract target or directory server with Cartograph, connect from the local terminal, crack its discovered port with Lockpick, then run `install` in Wraith's console. Installation requires mounted filesystem access. Clean the initial intrusion logs with Ashfall before disconnecting. Backdoors persist after contract completion and sign-out.

**Backdoored Servers** appears only while the Wraith license is owned. Its Connect buttons launch/open your terminal and connect directly to the selected server. You can also use `jump <host>`. These later connections bypass the saved proxy chain and its lease, grant filesystem access, suppress remote access logs, and have no trace countdown. Your saved proxy route remains available for ordinary connections. A reserved contract still must match the server you visit, and objective evidence plus a clean disconnect and `submit` are still required for payment.

**Ransomware:** four starter opportunity servers appear in amber in Atlas's directory. Add them to your map if desired. Scan, connect, and crack one, then run `deploy <host>` in Eclipse. Contract targets and ordinary proxy-only servers refuse deployment. At most **three instances** may be active per save, with one per server. Each completes after **120 seconds**, pays **800 CPH** on a starter server, and removes itself. Higher-rank generated opportunities pay `800 + 200 × rank` CPH. You may deploy again after completion; the perpetual license remains owned. Clean your access logs and disconnect while operations run, or use an existing Wraith backdoor.

Pending operations continue by server time while you are away. Payments settle on the next game request; the open app polls while instances are pending. Eclipse logs the completion message, the bank records the payment, and the active-instance panel frees the slot. Row locks prevent duplicate payments from simultaneous requests. Restarting a save clears its hidden-market progress and pending operations; other saves are preserved.

All tools operate on fictional game records. No payloads are generated, no host commands are run, and no external servers are contacted.

## v0.5 — broker controls, numeric IDs, and PostgreSQL lifecycle

The broker now has **Accept** and **Abort** buttons. The terminal still accepts `accept <id>` and `abort`; all scanning, routing, remote work, cleanup, and delivery remain manual. Aborting applies the displayed liability, up to 60 reputation loss, and a ten-minute replacement cooldown. You can reserve one assignment per save.

Contract IDs are randomly allocated, unique decimal numbers in the **8-bit range 0–255**. For example, a displayed ID of `173` is accepted with `accept 173`. Numbers are stored in PostgreSQL, survive restarts and dump/restore, and are allocated again for a fresh database. They do not encode rank. Private template keys preserve existing active missions and cooldowns when migrating a retained database.

PostgreSQL 17 runs as a real server in the database container. Its binary data directory is **`.data/postgres/`**, inside your local checkout and bind-mounted into the container. Backups live in **`.data/backups/`**; build initialization state lives in **`.data/build-state/`**. All of `.data/` is excluded from Git and image build context. Browser storage holds no game database.

### Development builds erase the old database

```bash
git pull --ff-only origin main
docker compose up --build
```

A changed backend or frontend image fingerprint triggers **DROP DATABASE, CREATE DATABASE, and Django migrations** before the backend starts. This removes all accounts, saves, sessions, and game progress. It leaves backup archives intact. The first v0.5 startup also resets an existing development database. Ordinary container restarts preserve data. Rebuilding identical cached source keeps the same fingerprint and also preserves data.

To force an empty database every cycle, even with unchanged source:

```powershell
.\scripts\fresh-build.ps1
```

```bash
bash scripts/fresh-build.sh
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

```powershell
.\scripts\database.ps1 backup snapshot.dump
```

```bash
bash scripts/database.sh backup snapshot.dump
```

The file is **`.data/backups/snapshot.dump`** on your computer. Omit the filename to generate a timestamped name. Existing archives are never overwritten. Copy these archives to another disk for durable backups; automatic backup scheduling is not implemented yet.

Import an archive from `.data/backups/`, replacing the current database:

```powershell
.\scripts\database.ps1 restore snapshot.dump -Confirmation ERASE-ALL-DATA
```

```bash
bash scripts/database.sh restore snapshot.dump ERASE-ALL-DATA
```

Restore checks the archive listing, stops the backend, drops/recreates the database, and runs `pg_restore --single-transaction --exit-on-error`. It migrates the restored schema and records the current image fingerprint before restarting, so startup keeps the imported data. If restoration fails, the backend stays stopped; the archive remains available to retry. Restore trusted archives only. These scripts run PostgreSQL tools inside the database container, avoiding PowerShell binary-output redirection problems. They preserve game state and IDs, but do not export cluster roles or PostgreSQL server configuration.

### Existing Docker volumes

Before v0.4, PostgreSQL used a Docker-managed `netrunner-db` volume. That unmounted volume is retained as a recovery option; it is not automatically imported. `docker compose down -v` does not erase the bind-mounted `.data/` directories. The native cloud workflow uses its separate ignored `.local/pgdata` directory and ordinary migration startup; use the explicit development reset command there when needed.

## v0.3 — sidebar services and server directory

Cipher bank, the contract broker, and Atlas are available directly from the left sidebar, including on mobile. These shortcuts launch/open the same applications and respect their existing RAM requirements.

Atlas routes chain **individual named servers**, such as `Intel Corp: Public Access → MilTech Research Center → NY Public Library Terminal`. Each server has its own fictional address, organization, category, clearance, fee, and trace delay; geography remains a secondary map coordinate.

Use **Atlas → Network directory** to search the built-in and generated servers and filter by server type or saved entries. **Add to Atlas** saves a server in the current runner's personal directory and makes it visible on their routing map. **Remove from Atlas** removes that bookmark and prunes the server from their committed proxy chain while preserving the remaining hop order. Directory changes save immediately; routing changes still use **Commit route**. Live remote connections lock directory and route edits. Bookmarking a restricted server does not bypass its proxy clearance.

New runners start with Intel, MilTech, NY Library, and Northstar University in Atlas. Migration `0003_atlas_server_directory` preserves all 12 previously visible nodes for existing saves, along with committed routes, route costs, balances, and live sessions. Restarting a slot restores the new four-server starter directory.

Back up the database, pull `main`, and rebuild as shown below. Django applies the migrations automatically.

## Operator desktop

- **Persistent terminal focus:** Enter and button submissions keep the command input focused, including failed requests. Up/Down recalls command history. Output can still be selected, and Tab can leave the terminal.
- **Independent launchers:** the top bar launches the local terminal; the sidebar opens Atlas, the broker, and Cipher bank; the application launcher also starts the exchange and each installed tool. Running processes have their own consoles and share your machine's RAM. Closing a window does not disconnect a remote session.
- **Custom machines:** 40 named hardware products across five tiers: two processors, gateways, memory modules, and drives per tier. Hardware purchases enter inventory and must be fitted. Spare components can be sold at half price.
- **Specialized software:** 50 individual licenses: Cartograph network mappers, Lockpick authentication crackers, Rosetta decryptors, Ashfall log cleaners, and Tripwire trace monitors. Each has five capability classes and Pro/Micro variants. Micro trades speed for lower memory use. Purchased tools must be launched separately.
- **World routing:** Atlas contains named fictional servers at 12 map locations. Select an ordered proxy chain, reorder/remove hops, and commit it. The route is drawn from your home gateway through the proxies to the reserved target. Pan and zoom the map or use the accessible saved-server list. Routes remain committed across sessions.
- **Manual contracts:** reserve with the broker or local shell, then submit through the shell. The broker publishes target, artifact, objective, clearance, and reward. There are retrieval, encrypted recovery, and deletion jobs at each rank.
- **An economy with consequences:** routing leases and tool computation consume Cipher (CPH). Failed jobs cost up to `90 + 80 × job rank` CPH and 60 reputation (both balances floor at zero). Completed jobs return after five minutes; failed ones after ten, using server time. A bankrupt runner can sell spare equipment or explicitly restart that slot by typing their alias.

Accounts retain three independent saves. Ranks are Ghost, Signal, Operator, Spectre, and Architect at 0, 100, 250, 450, and 700 reputation. Contracts are available at the runner's rank, one rank above, and one below. Products are purchasable through tier `min(5, rank + 2)`.

### Contract IDs and starter clearance

A new Ghost runner can reserve all six Ghost and Signal assignments, using **Accept** on the broker or `accept <id>` with the displayed numeric ID. Unknown IDs produce an explicit ID error; valid jobs outside your clearance report the actual job rank and your allowed range.

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

Export with the scripts above before rebuilding. Development builds intentionally reset progress by default. Set `NETRUNNER_RESET_ON_BUILD=0` before a rebuild to retain data and apply migrations, or restore your archive afterward. Migration `0004_contractidentity` assigns public numeric IDs without changing private mission keys. Existing balances, equipment, active missions, and cooldowns remain intact when using the preserve policy.

## Download and run on your computer

Install Docker Desktop (Windows/macOS) or Docker Engine with Compose (Linux). Clone this repository, open a terminal in the `netrunner` directory, and run:

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

This runs the Django suite against a separate PostgreSQL test database, builds Vue, and runs Chromium browser tests. The database role needs permission to create the test database and a disposable lifecycle database. The lifecycle check uses `pg_dump` and `pg_restore` from PATH or `NETRUNNER_PG_BIN`, and verifies actual drop/recreation, restart persistence, and an archive round trip including generated content, backdoors, pending operations, Field Notes, workspace arrangements, and persistent server journals. It is skipped if those client tools are unavailable. Browser tests create accounts prefixed `e2e_` in the development database. They verify complete multi-tool workspace contracts, drag/resize persistence, layout conflicts, mobile stacking, notebook autosave, conflicting edits and draft recovery, persistent server maintenance, hidden-market purchases, persistent direct backdoors, ransomware deployment, the manual tools-and-proxy contract loop, persistent cursor focus (including failed requests), bank charges, purchases/fitting/resale, three saves, sign-in persistence, confirmed bankruptcy recovery, and mobile layouts. The epic-market browser scenario uses the native Django environment to seed an offline test account with funds and memory; no public cheat API is provided. Set `CHROMIUM_PATH` if Chromium is not at `/usr/bin/chromium`.

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
