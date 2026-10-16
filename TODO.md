# Netrunner planned work

Committed features and follow-up work. Speculative features belong in [IDEAS.md](IDEAS.md).

## Next: Field Notes sidebar panel

- [ ] Add a Field Notes / Notepad editor accessible from the sidebar.
- [ ] Save notes in PostgreSQL separately for each of the three save slots.
- [ ] Support freeform notes for server addresses, routes, clues, aliases, and investigations.
- [ ] Show saving, saved, and failed-save states; protect unsaved text when changing panels or saves.
- [ ] Verify ownership checks, persistence after sign-out, backup/restore, and behavior when restarting a save.

Start with a simple text editor. Links, tags, multiple documents, and an evidence board can be considered later.

## Must-have: Persistent servers with histories

- [ ] Give servers durable state instead of recreating a fresh filesystem and security posture for each visit.
- [ ] Record relevant events: visits, file retrieval/deletion, access-log cleanup, installed backdoors, ransomware activity, administrator responses, and patches.
- [ ] Let subsequent visits reflect earlier actions: moved or missing files, changed services, patched weaknesses, and administrator notices.
- [ ] Integrate contract targets, ordinary directory servers, generated content, and saved backdoor links with persistent server identities.
- [ ] Decide the scope of server state. Prefer a separate world state per save initially, consistent with three independent lives; shared multiplayer consequences need a deliberate later design.
- [ ] Define server-time recovery and maintenance rules, including offline progress, without unexpectedly changing a live session underneath the player.
- [ ] Persist state and history through sign-out, container restarts, and PostgreSQL dump/restore; define migration and save-restart behavior.

Design goal: revisiting a familiar server should reveal the consequences of previous activity and tell an ongoing story. Give players observable clues and opportunities to respond to security changes.

## Deferred: Ransomware and permanent-backdoor economy balance

- [ ] Revisit this after the current feature work; do not change payouts or backdoor behavior yet.
- [ ] Measure how repeatable ransomware income compares with contract income, tool costs, and hardware progression.
- [ ] Review the combined effect of repeatable payouts and permanent direct access with no proxy cost or access logs. The combination could make contracts and routing unnecessary.
- [ ] Consider target recovery periods, diminishing returns from repeatedly targeting the same server, administrator sweeps, and a separate heat system. These are options to evaluate, not agreed implementation requirements.
- [ ] Connect any future response to persistent server history so consequences are understandable rather than arbitrary.
- [ ] Preserve reasons to explore, take contracts, and maintain equipment; provide visible warnings and counterplay before access is lost.
- [ ] Keep payout correctness separate from balancing: enforce the active-instance limit and prevent duplicate payments regardless of the eventual economy rules.

Reminder for a future economy/persistent-server planning session: discuss this balance before expanding passive income or making backdoors more powerful. No timed reminder has been scheduled.
