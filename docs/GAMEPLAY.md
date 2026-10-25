# Gameplay reference

## Terminal workflow

All hacking software is bundled into the primary terminal. Buy licenses at the exchange, then use `scan`, `decrypt`, `logcleaner`, `trace`, `install`, and `deploy`. `login` opens the Lockpick modal. Atlas retains its map view. `applets` lists owned licenses; `use <license-id>` selects a variant, and `help <command>` shows its manual. License selections persist per save.

Applets check ownership, capability, funds, and working RAM. Their operations do not leave standalone processes running. A timed Lockpick attempt reserves its RAM until it completes or is cancelled. Closing the primary terminal cancels an unfinished attempt. Owned capable Tripwire licenses decode the embedded trace countdown without a separate window or resident process.

**Tab** completes prefixes and lists multiple matches, with fuzzy fallback and known arguments. **Shift+Tab** retains normal navigation. Scrolling up pauses automatic following; polls and new output leave your place alone. Jump to latest output or submit a command to return to the bottom.

## Fresh broker assignments

Accepting an assignment immediately removes its offer card. Its active summary and Abort button remain available, and `brief` shows its instructions. Accepted jobs never return to that runner's offer list, whether completed or abandoned. The broker sources a fresh assignment after five minutes; an abort postpones an outstanding replacement to ten minutes. New offers have distinct private identities, target servers, and artifact names. They arrive by server time on the next refresh, including after time away. The broker page refreshes automatically.

Public ticket numbers stay in the 8-bit range 0–255, unique among live offers and the active job. Numbers can eventually be reused; assignment identities and targets are not recycled. Authored/generated contracts remain available alongside per-save fresh offers, within the player's rank ± 1.

## Local filesystem and decryption

When disconnected, `ls` lists the files on your workstation and its used/total storage. `rm <file>` deletes a local copy and reclaims its space. While connected, those commands refer to the remote server and require login. The terminal prompt identifies whether you are at the local workstation or logged into a target.

`get <file>` saves a durable local copy, including encrypted archives such as `ledger.enc`. Downloads survive disconnects, submission, failures, sign-out, and reloads. A drive must fit the combined size of all local files. Re-downloading the same server revision replaces its existing copy; same-named files from different servers receive unique local names. Submission retains the file, so clean up copies when you no longer need them. Removing a delivery file before submission invalidates its evidence.

For encrypted recovery, download the archive, clean the remote logs, and disconnect. Then run `decrypt ledger.enc` in the primary terminal with an owned Rosetta license, using the selected Rosetta license. Local decryption checks funds, RAM, and software capability; it changes only the local copy. The broker accepts it after decryption and a clean disconnect. While logged into a remote server, the same `decrypt` command operates on its archive. Local filenames can be completed with Tab.

## Sidebar services and public proxies

Atlas, Cipher bank, the contract broker, and Store open their full pages from the sidebar, including when leaving Workspace. These commercial services are page-only: they do not create workstation processes or Workspace panels.

The directory includes 40 additional Ghost-accessible public servers: libraries, universities, transit networks, museums, civic archives, and telecommunications services. Add chosen servers to Atlas before routing through them. They have distinct fees, trace delays, and latency; gateway hop limits still apply. They are ordinary proxy/exploration servers, not ransomware opportunities.

## Graphical password breaker

Connect to a server from the local terminal and scan its authentication service with Cartograph. **Open password breaker**, or type `lockpick` in the terminal, to open the server-login modal. The modal is shared by the primary terminal on its own and in Workspace.

The login form uses **admin**. Click **Break password** to decode the password in its form field. After decoding, the field shows asterisks. Click **Login** to mount the filesystem and open the target's terminal; this starts the trace. **Exit** closes the modal without logging in. It leaves the connection and any running attempt intact. Closing the modal returns keyboard focus to the primary terminal.

The server controls decoding time using CPU speed, Lockpick speed, target security, and route latency. Each attempt charges compute once. Insufficient capability fails after decoding. Cancel, disconnect, close the primary terminal, or switch its version to stop an unfinished attempt; charges are not refunded. Decoding survives page changes and reloads while its process runs. A decoded password waits for explicit Login without starting a trace. Wraith connections still bypass authentication and tracing.

## Trace tracker

A fixed floating bar keeps the target and trace status visible across pages. Before login it shows an inactive trace; Wraith links show suppressed logging. An owned, sufficiently capable Tripwire reveals the countdown and progress meter. The bar turns red at 30 seconds remaining. Without a suitable monitor, it ticks elapsed time since login and explains that remaining time needs Tripwire. The HUD sits above login modals and stays readable while the background is blurred. The countdown uses a server deadline, so it continues ticking between polls or during a temporary polling interruption.

## Integrated Logcleaner

Buy Logcleaner Pro or Micro licenses at the exchange. In the primary terminal, select an owned license and click **Clean logs**, or enter `logcleaner [license-id]`. Omitting the ID selects the strongest owned version that fits free RAM. Cleanup requires login, enough compute funds and temporary free RAM, and sufficient software capability. It leaves no separate process running. Subsequent remote work can dirty the logs again.

Software purchases show a brief build animation and completion notice. Fitting hardware, including gateways, shows installation progress, diagnostics or link calibration, and a fitting-complete notice. This is a presentation of the completed purchase; skipping an animation does not refund or undo the completed purchase or fitting.

## Operator desktop

- **Persistent terminal focus:** Enter and button submissions keep the command input focused, including failed requests. Up/Down recalls command history. Output can still be selected, and Tab can leave the terminal.
- **Independent launchers:** the top bar launches the local terminal; the sidebar opens Atlas, the broker, and Cipher bank; the exchange has its own sidebar shortcut and is also available through the application launcher. Only the primary terminal and Atlas are resident workstation processes; hacking operations use licensed applets. Closing a window does not disconnect a remote session.
- **Custom machines:** 40 named hardware products across five tiers: two processors, gateways, memory modules, and drives per tier. Hardware purchases enter inventory and must be fitted. Spare components can be sold at half price.
- **Specialized software:** 50 individual licenses: Cartograph network mappers, Lockpick authentication crackers, Rosetta decryptors, Logcleaner terminal extensions, and Tripwire trace monitors. Each has five capability classes and Pro/Micro variants. Micro trades speed for lower memory use. All software runs as primary-terminal applets.
- **World routing:** Atlas contains named fictional servers and dozens of public-access proxies worldwide. Select an ordered proxy chain, reorder/remove hops, and commit it. The route is drawn from your home gateway through the proxies to the reserved target. Pan and zoom the map or use the accessible saved-server list. Routes remain committed across sessions.
- **Manual contracts:** reserve with the broker or local shell, then submit through the shell. The broker publishes target, artifact, objective, clearance, and reward. There are retrieval, encrypted recovery, and deletion jobs at each rank.
- **An economy with consequences:** routing leases and tool computation consume Cipher (CPH). Failed jobs cost up to `90 + 80 × job rank` CPH and 60 reputation (both balances floor at zero). Accepted jobs never return; the broker sources new assignments using server time. A bankrupt runner can sell spare equipment or explicitly restart that slot by typing their alias.

Accounts retain three independent saves. Ranks are Ghost, Signal, Operator, Spectre, and Architect at 0, 100, 250, 450, and 700 reputation. Contracts are available at the runner's rank, one rank above, and one below. Products are purchasable through tier `min(5, rank + 2)`.

### Contract IDs and starter clearance

A new Ghost runner can reserve all six Ghost and Signal assignments, using **Accept** on the broker or `accept <id>` with the displayed numeric ID. Unknown IDs produce an explicit ID error; valid jobs outside your clearance report the actual job rank and your allowed range.

### Tool reference

Each console has its own `help` manual. Commands run entirely inside the game's simulation; they never execute OS commands or access an external target.

| Application | Commands / purpose |
| --- | --- |
| Local terminal | `apps`, `contracts`, `accept <id>`, `brief`, `route`, `connect <host>`, `lockpick`, `scan <host>`, `logcleaner [license-id]`, `decrypt <file>`, `status`, `ls`, `get <file>`, `rm <file>`, `disconnect`, `submit`, `abort`, `clear` |
| Cartograph | `scan <host>` discovers authentication ports and archive metadata |
| Lockpick | Graphical password breaker: scan a server, connect to its login, then click **Break password** |
| Rosetta | `decrypt <file>` supports remote archives while logged in, or local files while disconnected |
| Logcleaner | `logcleaner [license-id]` in the local terminal removes remote access logs |
| Tripwire | `trace` reads the live trace; an owned capable license decodes the embedded countdown without a separate process |
| Cipher bank | `balance`, `history [page]`, `loan`, `repay`, `deposit`, `withdraw` manage this save's accounts |

The trace begins at successful authentication, after Lockpick finishes breaking the password. A connected server login has no active trace. Wall-clock time and simulated computation both consume it. CPU speed and tool speed affect computation time. Gateway stealth and proxy delays extend trace time; gateway bandwidth affects transfers. Hop order changes geographical latency. Connections and equipment changes lock the route while online. Copying a file does not automatically complete a contract: the broker verifies objective evidence and a clean exit before paying a manual submission. Higher security can defeat underpowered tools, encrypted files require a decryptor, and local disk space must fit the recovered archive.

Every mutation checks authentication, CSRF, save ownership, and current game state. PostgreSQL row locks protect financial updates and mission completion from concurrent/replayed requests. The test suite exercises both concurrent payment and purchase requests.

### Null Exchange and epic software

The hidden server is absent from a new runner's public directory. Enter `rumors` in the local terminal for an invitation, then `connect null-exchange.internal` while disconnected and without a reserved contract. This unlocks **Null Exchange** in that save's sidebar. It sells two perpetual epic licenses:

| Software | Price | RAM | Commands |
| --- | ---: | ---: | --- |
| Wraith Rootkit | 2,400 CPH | 3 GB | `install` in the primary terminal; later `jump <host>` in the local terminal |
| Eclipse Ransomware | 1,800 CPH | 3 GB | `deploy <host>` in the primary terminal |

Purchase licenses at Null Exchange and use them from the primary terminal. Upgrade memory or close other tools if you exceed your RAM capacity. Each save has its own discovery state, licenses, backdoors, and operations.

**Backdoors:** scan a contract target or directory server with Cartograph, connect from the local terminal, crack its discovered port with Lockpick, then run `install` in the primary terminal. Installation requires mounted filesystem access. Clean the initial intrusion logs with Logcleaner before disconnecting. Backdoors persist after contract completion and sign-out.

**Backdoored Servers** appears only while the Wraith license is owned. Its Connect buttons launch/open your terminal and connect directly to the selected server. You can also use `jump <host>`. These later connections bypass the saved proxy chain and its lease, grant filesystem access, suppress remote access logs, and have no trace countdown. Your saved proxy route remains available for ordinary connections. A reserved contract still must match the server you visit, and objective evidence plus a clean disconnect and `submit` are still required for payment.

**Ransomware:** four starter opportunity servers appear in amber in Atlas's directory. Add them to your map if desired. Scan, connect, and crack one, then run `deploy <host>` in Eclipse. Contract targets and ordinary proxy-only servers refuse deployment. At most **three instances** may be active per save, with one per server. Each completes after **120 seconds**, pays **800 CPH** on a starter server, and removes itself. Higher-rank generated opportunities pay `800 + 200 × rank` CPH. You may deploy again after completion; the perpetual license remains owned. Clean your access logs and disconnect while operations run, or use an existing Wraith backdoor.

Pending operations continue by server time while you are away. Payments settle on the next game request; the open app polls while instances are pending. Eclipse logs the completion message, the bank records the payment, and the active-instance panel frees the slot. Row locks prevent duplicate payments from simultaneous requests. Restarting a save clears its hidden-market progress and pending operations; other saves are preserved.

All tools operate on fictional game records. No payloads are generated, no host commands are run, and no external servers are contacted.


## Store and resale

Open **Store** in the sidebar to shop with the hardware and software broker. **Owned items** lists everything you can manage or resell across categories. Owned software has **Use in terminal** to select its license; hardware uses **Fit component**. These are different actions.

All owned items, including starter licenses and starter hardware, can be sold for half their purchase price while disconnected. Fitted hardware requires a replacement first. Store cards show Sell with the return value and explain blocked sales. Selling a selected applet clears that preference; an owned fallback can then be selected or chosen automatically.

## IRC Underground and fingerprint exploits

Open **IRC Underground** from the sidebar to join **#zero-day**. The participants are simulated bots in your save, not real IRC users. More than 60 simulated regulars discuss Linux, programming, hardware and underground rumors. Chatter arrives every 10 seconds, with red exploit drops every 30 seconds using server time; the pinned board lets you browse trader offers. Expand the online roster to see the channel members. Messages, purchases and your exploit stash persist in PostgreSQL. The channel stays on its own page and consumes no workstation RAM.

Channel commands:

```text
/help
/list
/msg hexdealer buy ssh-v1-r1-shot
/pay hexdealer 90 ssh-v1-r1-shot
/buy ssh-v1-r1-license
/inventory
/balance
/clear
```

Each purchase debits the same CPH account shown in Cipher bank and creates one ledger entry. `/pay` requires the exact quoted amount and seller; it transfers funds and delivers the item together. Duplicate lifetime purchases, invalid offers and insufficient funds leave the account untouched. Single-use copies can be purchased repeatedly, up to 99 per fingerprint. Prices start at 90 CPH per single-use copy or 360 CPH per lifetime license and scale with authentication class and patch revision.

Use exploits in the primary terminal:

```text
scan helix-0.internal
connect helix-0.internal
exploits
exploit ssh-v1-r1-shot
ls
get research.dat
logcleaner
disconnect
submit
```

Reserve the appropriate contract first if you plan to submit proof. You can also connect first and scan the connected server. Tab completes owned exploit IDs, and `help exploit` explains the rules.

Match the **whole fingerprint**, for example `SSH / auth-v1 / patch r1`. HTTP intelligence does not work on SSH, and revision-one intelligence does not work on a patched revision-two service. A new scan after a patch reveals its current fingerprint and makes matching revision-specific intelligence available from the bots. Lifetime means reusable against that exact fingerprint across hosts, not immunity to patches.

Exploit execution needs 2 GB of free RAM for the command, a current scan, and an unauthenticated remote session. Cancel a running password breaker first. A successful exploit skips password decoding and immediately opens an admin shell, starts the trace and creates access logs. Clean those logs before disconnecting. Only successful entry consumes a single-use copy; mismatch, stale scan, insufficient RAM, or an already-open shell preserves it. Exploits do not install a backdoor. Wraith remains the separate persistent, log-free return path.


### Busy channels without runtime AI

Ambient conversations use the local [`irc_chatter.json`](../backend/game/data/irc_chatter.json) library: 62 nicknames, 48 authored three-person conversations, and 12 conversation templates with software, platform, project, editor, reaction and outcome pools. Deterministic shuffling spreads topics across a cycle; shared template values keep each three-line exchange coherent. No model, external chat server, news API or background worker is needed. Add conversations or expand the vocabulary pools in that file, then restart Django to load changes.

Chat continues while you use other pages. The shared game clock advances the channel, and idle pages refresh every ten seconds. Both the saved transcript and the browser's message list retain the **latest 200 messages**, dropping the oldest automatically; reaching 200 never stops chat or wipes the whole channel. `/clear` (also a channel button) clears saved chat for the current save across sessions. Inventory and bank history remain intact. Separate delivery cursors prevent cleared or pruned messages from replaying. A new channel starts with a short recent conversation history. After a longer absence, the server fills the latest 200 messages (150 chatter lines and 50 exploit drops) rather than replaying the entire absence. Chat timestamps follow server time even across sign-out or a closed browser; there is no need for a separate worker. IRC polling stops when its page closes, while the shared game refresh continues on other pages. Requests do not overlap.


## Service families and optional exploits

Contract targets and public directory servers now include eleven service families:

| Service | Default port / transport | Example exploit ID |
| --- | --- | --- |
| SSH | 22 / TCP | `ssh-v1-r1-shot` |
| HTTP | 443 / TCP | `http-v1-r1-shot` |
| RDP remote desktop | 3389 / TCP | `rdp-v1-r1-shot` |
| WordPress CMS 6.4 | 443 / TCP | `wordpress-6.4-v1-r1-shot` |
| PHP 5.6 | 443 / TCP | `php-5.6-v1-r1-shot` |
| VOIP / SIP 2.0 | 5060 / UDP | `sip-2.0-v1-r1-shot` |
| Telnet | 23 / TCP | `telnet-v1-r1-shot` |
| FTP | 21 / TCP | `ftp-v1-r1-shot` |
| SMTP mail | 25 / TCP | `smtp-v1-r1-shot` |
| MySQL 5.7 | 3306 / TCP | `mysql-5.7-v1-r1-shot` |
| Redis 6.2 | 6379 / TCP | `redis-6.2-v1-r1-shot` |

These are fictional service profiles and simulated access adapters, not real vulnerability or exploit implementations. Each service supports the same **scan → Lockpick → admin login** route. Paid exploits remain optional shortcuts. The service name does not increase the authentication class or require a different cracker purchase. All new Ghost-level service contracts are unencrypted and can be completed with starter software and funding; higher classes still need appropriately capable tools as before. Exploit prices continue to use the existing class/revision formula.

The broker has 63 built-in contract templates, including the original 15. A fresh Ghost sees 27 offers across Ghost and Signal. Briefs show the service family and available access routes. Replacement jobs vary their service family while retaining the source contract's security class, objective and payout. Generated content can also select any supported service.

Scans reveal the full fingerprint, including application release, authentication class and patch revision. **An HTTP exploit does not match WordPress or PHP just because all three use port 443.** A WordPress 6.4 license does not match a 6.5 service. IRC's service filter lists each family; scanning a different release or later patch adds matching intelligence to the trade board. Owned legacy SSH, HTTP and RDP licenses keep working on their matching fingerprints. Existing discovered server profiles remain durable across reconnects and updates.


## Exploring remote filesystems

All servers have a virtual filesystem with ordinary background files: configuration, logs, notes, application assets, backups and service records. WordPress/PHP hosts include `/var/www`; RDP hosts include `/Users/admin/Documents`; FTP uses `/srv/ftp`; MySQL and Redis have database data folders. RDP uses the same slash-based virtual navigation commands as other hosts, with case-sensitive names.

Most mission files start at `/`, while some live in a service folder. The broker gives the filename, and scanning reveals the service without disclosing the artifact's nested path. After logging in, explore:

```text
pwd
ls
cat README.txt
ls /var
cd /var/www
ls
cat wp-config.php
get cms-backup.dat
logcleaner
disconnect
submit
```

`ls [directory]` lists that directory's immediate children. `cd ..` moves up; `cd` alone returns to `/`. File commands accept absolute paths such as `/var/www/users.db` or paths relative to your working directory. Tab completes files and directories you have discovered in the current connection; it does not reveal unopened folders. `find users.db` (or a pattern such as `find *.db`) searches the current subtree and reports matching absolute paths.

Browsing is part of the challenge. The running trace still advances in real time; `ls` adds 2 seconds of work, `cd` and `cat` add 1 each, and `find` adds 8. There are no added CPH fees for these commands. `pwd` adds no work. Transfers and log cleanup keep their existing costs. Better proxy routes and suitable tools still help; the login/cracking screen itself remains trace-free until you enter the server.

You can download or delete ordinary files too. A same-named file in `/backup/reference` is a reference copy and does **not** satisfy a contract. Only downloading or deleting the real objective at its exact path records evidence. Downloading unrelated files later does not overwrite valid proof. Local copies with the same basename receive suffixes such as `_2`, and all copies use your local drive capacity. While disconnected, use `ls`, `rm <local-name>` or `decrypt <local-name>` to manage them.

Filesystem changes persist per save. Existing saves retain the objective's original location and deletion/encryption state when background files are added. Administrator maintenance restores the tree and moves the objective under `/archive/rN/`; the service folders and background records remain available. Scans do not expose the full directory tree. The operator journal retains file metadata discovered through filesystem actions.


## Erase all copies contracts

Three authored contracts require deleting the main file and specific backup copies. They appear in the ordinary broker according to rank, with the **ERASE ALL COPIES** objective and each required path named in the brief:

| Contract | Rank / service | Required files |
| --- | --- | --- |
| Ashfall audit | Ghost / SSH | `/root/audit.txt`, `/bak/audit.log` |
| Juniper CMS | Ghost / WordPress | `/var/www/users.db`, `/backup/nightly/users.db` |
| Glasshouse ledger | Signal / RDP | `/Users/admin/Documents/client-ledger.db`, `/Users/admin/Documents/Archive/client-ledger.bak`, `/backup/workstations/client-ledger.db` |

Use the normal scan and login workflow, delete each named file with `rm`, clean the remote logs, disconnect and `submit`. The active broker card and terminal `brief` track each receipt. Copy order does not matter, and receipts survive clean disconnects. You can return for remaining files; removing only the primary file does not qualify for payment. All copies must still be deleted when the broker verifies submission. If administrator maintenance restores them, old receipts do not qualify for the restored files.

Only the listed paths are required. Ordinary single-file deletion jobs still require just their objective file; unrelated logs, backups and reference copies need not be removed. Replacement assignments retain the multiple-copy requirement but use fresh hosts, filenames and paths.


## Named systems and IP-address workflow

Contracts identify a named organization and a specific system, such as **Helix Research Lab: Research Archive**. Open **Atlas network → Network directory**, search for that organization, and read the system's IPv4 address. Contract destinations are marked **DESTINATION ONLY**; they cannot be added as proxy hops. Public proxy servers remain separate directory entries that you can save and chain on the map.

Reserve the contract, build your route, then use the IP shown in Atlas. The following address is illustrative; your world's assigned address may differ:

```text
ping 203.0.113.42
scan 203.0.113.42
connect 203.0.113.42
login
```

`ping` simulates reachability, displays the server name and IP, and opens no session, starts no trace and charges no CPH. It is optional: an ICMP timeout can mean filtering, so scanning and connecting remain available. A successful login or matching exploit starts the trace as before. The connected prompt uses `admin@<IP>`, and the decoder and trace bar show the IP with the named system.

To look up an exact known server name without probing:

```text
resolve "Helix Research Lab: Research Archive"
ping "Helix Research Lab: Research Archive"
```

A broad organization name can be ambiguous; Atlas lists each specific system. Tab completes known IPs and legacy aliases. Legacy commands such as `scan helix-0.internal` still work, including the older walkthrough examples above. Internally, saved files, backdoors, proxy IDs and histories retain their existing identities; changing the displayed address does not recreate the server.

Addresses persist in PostgreSQL across sessions, restarts and backups. The allocator uses `192.0.2.0/24`, `198.51.100.0/24`, and `203.0.113.0/24` documentation ranges, then private `10.0.0.0/8` for larger worlds. All replies and lookups are simulated locally by the game. No real DNS, ICMP, SSH or HTTP connection is made.


## Cipher Bank accounts, loans and complete statements

Each save has its own current account, reserve account and loan balance. Purchases, route leases, compute and repayments use current funds. Transfers to reserve keep money separate from spending; transfer it back when needed. Transfers are free and stay within the same save. Trace and contract fines collect from current funds first, then reserve. Net worth is current + reserve − outstanding loan debt. Cipher Bank stays on its own page without a resident process or Workspace panel.

The bank offers one active loan at a time, with a principal limit of **1,000 + 750 × rank** CPH (1,000 at Ghost, up to 4,000 at Architect) and a minimum of 100 CPH. A fixed **5% fee, rounded up**, is added to debt once. Borrowing 500 CPH credits the full 500 and creates 525 CPH of debt. There is no compounding, due date, offline charge or automatic repayment. Partial repayments are supported; paying off the loan unlocks borrowing again. Existing debt does not change when rank changes. Forms show the fee and total before borrowing.

Use the bank's forms or terminal:

```text
balance
loan
loan 500
deposit 300
withdraw 100
repay 200
history
history 2
```

**All transaction records remain available:** 25 entries per statement page, or 15 per terminal `history [page]`. Statement pages retain a snapshot so incoming entries do not shift records or cause gaps. **Refresh history** starts a new snapshot including newer transactions. Entries identify their account, amount, time and record ID. New entries also record their closing balance; old records retain their original data and show no closing balance when it was not recorded.

Transfers and loan actions create linked entries showing both sides. A positive loan-account amount increases debt; a negative amount records repayment. Loan proceeds are not profit, and transfers do not change net worth. Retrying the same form request cannot move funds twice. Balances, debt, terms, references and complete history are included in PostgreSQL backups. Restarting a runner clears that save's financial state; other saves remain independent.

Investments and fictional stock trading remain a separate design topic. Reserve funds earn no passive yield in this version.
