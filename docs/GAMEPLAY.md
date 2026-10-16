# Gameplay reference

## Graphical password breaker

Connect to a server from the local terminal and scan its authentication service with Cartograph. **Open password breaker**, or type `lockpick` in the terminal, to open the server-login modal. Lockpick also remains available through Applications and Workspace.

The login form uses **admin**. Click **Break password** to decode the password in its form field. After decoding, the field shows asterisks. Click **Login** to mount the filesystem and open the target's terminal; this starts the trace. **Exit** closes the modal without logging in. It leaves the connection and any running attempt intact. Closing the modal returns keyboard focus to the primary terminal.

The server controls decoding time using CPU speed, Lockpick speed, target security, and route latency. Each attempt charges compute once. Insufficient capability fails after decoding. Cancel, disconnect, stop Lockpick, or switch its version to stop an unfinished attempt; charges are not refunded. Decoding survives page changes and reloads while its process runs. A decoded password waits for explicit Login without starting a trace. Wraith connections still bypass authentication and tracing.

## Trace tracker

A fixed floating bar keeps the target and trace status visible across pages. Before login it shows an inactive trace; Wraith links show suppressed logging. A running, sufficiently capable Tripwire reveals the countdown and progress meter. The bar turns red at 30 seconds remaining. Without a suitable monitor, it shows that the timer is unavailable rather than inventing a countdown.

## Integrated Logcleaner

Buy Logcleaner Pro or Micro licenses at the exchange. In the primary terminal, select an owned license and click **Clean logs**, or enter `logcleaner [license-id]`. Omitting the ID selects the strongest owned version that fits free RAM. Cleanup requires login, enough compute funds and temporary free RAM, and sufficient software capability. It leaves no separate process running. Subsequent remote work can dirty the logs again.

Software purchases show a brief build animation and completion notice. This is a presentation of the completed purchase; skipping it does not refund or cancel the license.

## Operator desktop

- **Persistent terminal focus:** Enter and button submissions keep the command input focused, including failed requests. Up/Down recalls command history. Output can still be selected, and Tab can leave the terminal.
- **Independent launchers:** the top bar launches the local terminal; the sidebar opens Atlas, the broker, and Cipher bank; the application launcher also starts the exchange and each installed tool. Running processes use graphical interfaces or their own consoles and share your machine's RAM. Closing a window does not disconnect a remote session.
- **Custom machines:** 40 named hardware products across five tiers: two processors, gateways, memory modules, and drives per tier. Hardware purchases enter inventory and must be fitted. Spare components can be sold at half price.
- **Specialized software:** 50 individual licenses: Cartograph network mappers, Lockpick authentication crackers, Rosetta decryptors, Logcleaner terminal extensions, and Tripwire trace monitors. Each has five capability classes and Pro/Micro variants. Micro trades speed for lower memory use. Applications launch separately; Logcleaner runs inside the primary terminal.
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
| Local terminal | `apps`, `contracts`, `accept <id>`, `brief`, `route`, `connect <host>`, `lockpick`, `logcleaner [license-id]`, `status`, `ls`, `get <file>`, `rm <file>`, `disconnect`, `submit`, `abort`, `clear` |
| Cartograph | `scan <host>` discovers authentication ports and archive metadata |
| Lockpick | Graphical password breaker: scan a server, connect to its login, then click **Break password** |
| Rosetta | `decrypt <file>` operates on an accessible encrypted archive |
| Logcleaner | `logcleaner [license-id]` in the local terminal removes remote access logs |
| Tripwire | `trace` reads the live trace; keep a capable monitor running for the desktop countdown |
| Cipher bank | `balance`, `history` display this save's independent account |

The trace begins at successful authentication, after Lockpick finishes breaking the password. A connected server login has no active trace. Wall-clock time and simulated computation both consume it. CPU speed and tool speed affect computation time. Gateway stealth and proxy delays extend trace time; gateway bandwidth affects transfers. Hop order changes geographical latency. Connections and equipment changes lock the route while online. Copying a file does not automatically complete a contract: the broker verifies objective evidence and a clean exit before paying a manual submission. Higher security can defeat underpowered tools, encrypted files require a decryptor, and local disk space must fit the recovered archive.

Every mutation checks authentication, CSRF, save ownership, and current game state. PostgreSQL row locks protect financial updates and mission completion from concurrent/replayed requests. The test suite exercises both concurrent payment and purchase requests.

### Null Exchange and epic software

The hidden server is absent from a new runner's public directory. Enter `rumors` in the local terminal for an invitation, then `connect null-exchange.internal` while disconnected and without a reserved contract. This unlocks **Null Exchange** in that save's sidebar. It sells two perpetual epic licenses:

| Software | Price | RAM | Commands |
| --- | ---: | ---: | --- |
| Wraith Rootkit | 2,400 CPH | 3 GB | `install` in Wraith's console; later `jump <host>` in the local terminal |
| Eclipse Ransomware | 1,800 CPH | 3 GB | `deploy <host>` in Eclipse's console |

Purchase licenses at Null Exchange and launch them through Applications. Upgrade memory or close other tools if you exceed your RAM capacity. Each save has its own discovery state, licenses, backdoors, and operations.

**Backdoors:** scan a contract target or directory server with Cartograph, connect from the local terminal, crack its discovered port with Lockpick, then run `install` in Wraith's console. Installation requires mounted filesystem access. Clean the initial intrusion logs with Logcleaner before disconnecting. Backdoors persist after contract completion and sign-out.

**Backdoored Servers** appears only while the Wraith license is owned. Its Connect buttons launch/open your terminal and connect directly to the selected server. You can also use `jump <host>`. These later connections bypass the saved proxy chain and its lease, grant filesystem access, suppress remote access logs, and have no trace countdown. Your saved proxy route remains available for ordinary connections. A reserved contract still must match the server you visit, and objective evidence plus a clean disconnect and `submit` are still required for payment.

**Ransomware:** four starter opportunity servers appear in amber in Atlas's directory. Add them to your map if desired. Scan, connect, and crack one, then run `deploy <host>` in Eclipse. Contract targets and ordinary proxy-only servers refuse deployment. At most **three instances** may be active per save, with one per server. Each completes after **120 seconds**, pays **800 CPH** on a starter server, and removes itself. Higher-rank generated opportunities pay `800 + 200 × rank` CPH. You may deploy again after completion; the perpetual license remains owned. Clean your access logs and disconnect while operations run, or use an existing Wraith backdoor.

Pending operations continue by server time while you are away. Payments settle on the next game request; the open app polls while instances are pending. Eclipse logs the completion message, the bank records the payment, and the active-instance panel frees the slot. Row locks prevent duplicate payments from simultaneous requests. Restarting a save clears its hidden-market progress and pending operations; other saves are preserved.

All tools operate on fictional game records. No payloads are generated, no host commands are run, and no external servers are contacted.

