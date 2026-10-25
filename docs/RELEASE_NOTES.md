# Release notes

Historical feature and migration notes. See the [README](../README.md) for the current project overview and [development guide](DEVELOPMENT.md) for setup and maintenance.

## v0.18 — erase all copies contracts

Added three authored deletion jobs: Ashfall audit (SSH), Juniper CMS (WordPress), and Glasshouse ledger (RDP). These briefs name two or three exact files, including backups. The active broker card and terminal brief track per-path receipts; payment requires all named files deleted and a clean exit. Partial deletion, unrelated files and restored copies do not qualify. Ordinary single-file jobs retain their existing rules. Fresh broker replacements preserve the multi-copy requirement while changing host and filenames. The offline generator now accepts repeatable `--delete-copy` paths; examples are in the development guide. Existing save data needs no schema migration; startup hooks allocate public IDs for the new templates.

## v0.17 — populated remote filesystems

Every server now has a persistent virtual directory tree with service-specific application files, logs, configuration, notes, backups and reference copies. Added `ls [path]`, `cd`, `pwd`, `cat` and `find`, plus discovered-path Tab completion and working-directory prompts. Some contract artifacts remain at root; others live in folders such as `/var/www`, `/Users/admin/Documents` or database data directories. Scans no longer reveal nested artifact locations. Any file can be copied or deleted, but only the exact objective path produces broker proof; same-named reference files do not count. File previews and downloads never touch the host filesystem. Directory browsing adds bounded trace work without new CPH fees.

The offline generator supports `--placement root|nested|mixed`, `--artifact-dir` and `--filename`; WordPress missions can use `users.db`. Migration 0014 adds background files to existing servers while preserving their objective paths, encrypted/deleted states and histories. Maintenance restores background data and relocates the objective into its revision archive. Local downloads, storage cleanup and decryption remain available after disconnecting.

## v0.16 — diverse services without mandatory exploit costs

Expanded to eleven service families: SSH, HTTP, RDP, WordPress CMS, PHP 5, VOIP/SIP, Telnet, FTP, SMTP, MySQL and Redis. Added 45 built-in contracts, service labels in briefs and the directory, UDP-aware SIP scan output, and service variation in replacement assignments. Every new Ghost service contract is playable with starter software through Lockpick; paid exploits remain optional and retain existing pricing rules. IRC now offers permanent and single-use exploits for every family, matching application release as well as auth class and patch revision. Generic HTTP packets cannot unlock WordPress or PHP targets. Existing discovered server identities and legacy exploit licenses remain valid. The offline generator accepts `--service` for both contracts and directory servers. No schema migration is required; startup migration hooks allocate IDs for the additional templates.

## v0.15.1 — continuous background IRC

IRC advances through the shared game clock on every page, including an idle desktop. Long absences now fill the latest 200 messages instead of a small catch-up batch, with generation bounded to the history window. Reaching 200 keeps replacing the oldest lines; chat never stops or automatically wipes itself. `/clear` still preserves purchases and delivery cursors. Idle pages refresh every ten seconds without adding an IRC workstation process or consuming game RAM.

## v0.15 — populated IRC and bounded scrollback

IRC Underground now has more than 60 ambient regulars, coherent three-person conversations every 10 seconds, an expandable roster, and red exploit drops every 30 seconds. A small local JSON library combines authored threads and vocabulary templates without runtime AI or external services. Saved and displayed scrollback are capped at 200 messages. `/clear` removes chat without affecting purchases or bank history; durable delivery cursors prevent cleared or pruned messages from replaying. Offline catch-up and overlapping client polls are bounded. Migration 0013 adds per-save channel cursors while retaining existing chat and exploit ownership.

## v0.14 — IRC Underground and fingerprint exploits

Added a separate IRC Underground sidebar page with persistent per-save chat, simulated bot traders, server-timed advertisements, and CPH purchases recorded in Cipher bank. Lifetime licenses and single-use copies target exact SSH, HTTP or RDP authentication fingerprints including patch revision. Scanning reveals those fingerprints; `exploits` lists owned tools, and `exploit <id>` opens an immediate admin shell on a match. Normal trace, log cleanup, RAM and contract rules still apply. Invalid attempts do not consume copies. Later server patches require new scans and matching intelligence. Public directory servers now include HTTP and RDP services alongside SSH; existing discovered server states remain intact. Migration 0012 adds inventory and chat history without resetting native saves.

## v0.13.1 — Store and clear resale controls

Renamed the shopping menu to Store, added an all-owned inventory view, and made resale buttons and blocking reasons explicit. Owned software can be selected directly in Store. Starter items remain resellable; fitted components require replacement and remote connections must be closed before trading.

## v0.13 — one terminal and fresh broker assignments

All hacking software is now licensed terminal applets, including Cartograph, Rosetta, Tripwire, Wraith, Eclipse, and Lockpick's login modal. Atlas remains separate. Commercial services are page-only and no longer create processes or Workspace panels. Saved tool selections and useful logs migrate to the primary terminal; other save progress is retained.

Accepted assignments leave the board permanently for that runner. Timed replacements have new identities, targets, and artifacts. Private per-save assignments avoid exhausting the global authored-content ID pool; 8-bit public ticket numbers stay unique among live offers. Migrations `0010` and `0011` preserve current jobs and retire previously consumed offers.

## v0.12 — local workstation, visible traces, and public directory

The trace HUD now ticks elapsed time without Tripwire, uses a server deadline for monitored countdowns, and stays above login modals. Local files persist and consume aggregate drive space: use disconnected `ls`/`rm`, download ciphertext, and decrypt it locally with Rosetta before submission. Hardware fittings have their own installation animation. Sidebar services open full pages from Workspace, with a dedicated hardware/software shortcut. Atlas gains 40 public-access proxies available to Ghost players.

Migration `0009` preserves the current recoverable legacy download and its delivery proof. Older builds discarded previously submitted copies; those cannot be reconstructed. Local files are included in PostgreSQL backups and reset only when the save is restarted or the development database is reset.

## v0.11 — terminal completion and optional Cartograph panel

Terminals preserve scrollback during polls and new output, with an explicit jump to latest output. Tab supports prefix completion, fuzzy fallback, and contextual arguments. The main terminal can run Cartograph scans using owned software while the separate app remains available. Logged-out file commands now identify the missing login explicitly.

## v0.10 — terminal workflow and trace tracker

Added a fixed floating trace tracker, a terminal-launched login modal with admin credentials and decoding inside the password field, explicit Login after decoding, and a short software purchase build animation. Logcleaner replaces Ashfall as a licensed terminal extension. Migration `0008` retires cleaner processes and panels while retaining licenses, other panels, and save progress. See the [gameplay guide](GAMEPLAY.md).

## v0.9 — graphical password breaker

Lockpick now opens as a graphical application with a rolling character decoder, timed progress, and cancellation. Connected servers present a login before filesystem access. The trace begins on successful authentication; the server controls attempt timing, charges, capability checks, and completion across reloads. Both standalone and Workspace views share the same process. See the [gameplay reference](GAMEPLAY.md#graphical-password-breaker).

## v0.8 — personal multi-tool Workspace

The sidebar now includes a separate **Workspace**. All previous screens and launchers remain available. Start with four panels—local terminal, Atlas, Cartograph, and Lockpick—then use **Launch visible tools** to start the available applications without leaving the page. Every console has its own command field, history, output, and cursor focus. A command updates the same runner state across all panels.

Use **Add a panel** to open built-in services, an owned software variant, Field Notes, Server Histories, or an unlocked black-market/backdoor service. Adding a tool launches it in place; adding an already-running tool reuses its process. Atlas routing, broker acceptance/abort, the exchange, bank commands, notes, histories, and Wraith connections all work inside panels. The main app's terminal launcher and process dock also open/focus panels while you are on Workspace.

The Workspace Atlas is map-only and fills its panel. Click saved server markers in route order (click again to remove a hop); numbered markers and connecting lines show the chain. Commit the route on the map. Directory management remains available on the full Atlas screen.

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

Wraith links remain installed across maintenance. Direct links still bypass proxy leases, suppress remote access logging, and have no trace countdown. Eclipse keeps the existing three-instance cap, two-minute duration, and payout values. The economy-balancing work remains deferred in [TODO.md](../TODO.md).

Migration `0006` preserves known active mission state, deleted/decrypted artifacts, dirty logs, existing backdoors, and pending operations. It does not invent a history of visits from before this feature. Notes, server state, and journal events survive normal restarts, sign-out, and PostgreSQL dump/restore. Restarting a runner clears that save's notes and world histories along with its other progress; other saves are untouched. The existing development-build database reset policy still applies, so export before a fresh build if you want to retain progress.

## v0.6 — generated world content and the hidden market

### Offline development administration

`generate_content` is a local Django management command, available only with `DJANGO_DEBUG=1`. It has no web endpoint and needs no external service. After the initial fresh build, PostgreSQL must be running and migrated; the backend web server may be stopped while you author content.

Linux / Bash:

```bash
docker compose stop backend
bash scripts/generate-content.sh missions --count 5 --rank 0
bash scripts/generate-content.sh missions --count 2 --rank 1 --objective retrieve --encrypted
bash scripts/generate-content.sh servers --count 5 --rank 0
bash scripts/generate-content.sh servers --count 4 --rank 0 --exploitable
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
docker compose up -d --no-build
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

## v0.3 — sidebar services and server directory

Cipher bank, the contract broker, and Atlas are available directly from the left sidebar, including on mobile. These shortcuts launch/open the same applications and respect their existing RAM requirements.

Atlas routes chain **individual named servers**, such as `Intel Corp: Public Access → MilTech Research Center → NY Public Library Terminal`. Each server has its own fictional address, organization, category, clearance, fee, and trace delay; geography remains a secondary map coordinate.

Use **Atlas → Network directory** to search the built-in and generated servers and filter by server type or saved entries. **Add to Atlas** saves a server in the current runner's personal directory and makes it visible on their routing map. **Remove from Atlas** removes that bookmark and prunes the server from their committed proxy chain while preserving the remaining hop order. Directory changes save immediately; routing changes still use **Commit route**. Live remote connections lock directory and route edits. Bookmarking a restricted server does not bypass its proxy clearance.

New runners start with Intel, MilTech, NY Library, and Northstar University in Atlas. Migration `0003_atlas_server_directory` preserves all 12 previously visible nodes for existing saves, along with committed routes, route costs, balances, and live sessions. Restarting a slot restores the new four-server starter directory.

Back up the database, pull `main`, and rebuild as shown below. Django applies the migrations automatically.

