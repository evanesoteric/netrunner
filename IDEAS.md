# Netrunner ideas

Exploratory concepts, not committed tasks. These may change or never be implemented. Agreed work belongs in [TODO.md](TODO.md).

## Contracts that intersect

Separate assignments could reference the same people, organizations, servers, or evidence. A routine recovery might expose wrongdoing by the employer; two clients might want incompatible outcomes for the same archive. Another runner's logs might contain a distress message.

Let discoveries and terminal actions drive decisions. Consider how conflicting objectives, evidence ownership, payment, reputation, and consequences would work before committing to the feature. Avoid making mandatory story choices into a sequence of next-step buttons.

## Forensic workstation

A dedicated application could examine recovered logs, compare file versions, validate checksums, assemble timelines, and decode intercepted messages. It could support investigations where interpreting evidence matters as much as obtaining it.

Explore how findings would connect to server histories, Field Notes, and optional mysteries. Keep findings understandable and distinguish evidence from assumptions. This is a future possibility, not an approved implementation task.

## Player-controlled automation

A small fictional scripting language or saved terminal routines could let experienced players automate workflows they already understand. RAM usage, execution time, limited error handling, and tool requirements could create useful tradeoffs.

Explore a narrow set of game commands first. Automation should run only through the server-authoritative game simulation, obey normal ownership, access, resource, and payout rules, and never execute host commands or contact external infrastructure. Decide how interruption, failed steps, loops, and repeated financial actions should behave before implementation.

## Exploit broker — design discussion

Agreed direction: reusable exploit engines with consumable exploit intelligence, matched to exact service fingerprints such as `SSH / auth-v2`, rather than any server using a protocol. Keep this at the design stage.

Open design decisions include how intelligence is consumed on failed attempts, whether packets bind to a host or service revision, how patches invalidate stale packets, pricing, and the distinction between an initial foothold and administrator access. Successful exploitation should fit the existing login/trace/log-cleanup rules; Wraith's persistent log-free entry remains a separate capability.
