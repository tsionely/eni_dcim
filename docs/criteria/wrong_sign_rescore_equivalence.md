# CRITERION REGISTRATION — Wrong-sign re-score: definitions, margins, and what will NOT be claimed

Registered BEFORE the re-score artifact exists (advisory-24 round,
channel-1 binding addition: the ancestry law applies to margins — a
margin chosen after seeing the paired deltas is the
retrospective-definition sin in miniature). The re-score artifact's
generator commit must have THIS commit as an ancestor, verified by
the release-manifest checker.

## What was seen before this registration, declared

The UNPAIRED aggregates of the R26-1 shadow-restamp trial rows were
seen (old path ~24/96 opposition-to-velocity, new ~6/13; wrong-sign
vs needed-correction 0/96 and 0/13). The PAIRED per-timestamp
deltas have NOT been computed or seen by anyone. Margins below bind
regardless of what the paired artifact shows.

## 1. Wrong-sign violations (the safety criterion)

Definition (per the channel-1 ruling, to be confirmed or corrected
by the archaeology): sign(command) opposes sign(needed correction
e) with deadband 0.02 m/s on the command and 0.02 m on e.

Equivalence margin: **ZERO.** On the paired common-support row set,
the new (shadow) path may introduce NO violation absent in the old
path at the same timestamp. Any nonzero paired excess = regression
flag; row 4 fails closed, no averaging, no rate argument.

**Support definition (second amendment, still pre-evidence —
channel-2 correction order): support is counted in UNIQUE COMMAND
EVENTS, never trace rows, and ZERO IS A COMMAND.** The earlier
"16->13 mask accounting" formulation is WITHDRAWN — it conflated
trace rows with events and treated command == 0.0 as absence,
violating two of this program's own laws (rows-are-not-units;
zero-is-a-command / only None is absence). The layered accounting
for the current R26-1 fixture, binding on the artifact:

- TRACEABILITY LAYER: 16 populated CSV rows (feature/feature_side
  duplication retained for provenance);
- COMMAND-EVENT SUPPORT: 9 unique events, keyed at minimum by
  (flight_id, trial, mono_ns), selecting the fed=True event row;
- SIGN-EVALUABLE SUBSET: 7 events outside the 0.02 m/s command
  deadband;
- ZERO/NEUTRAL SUBSET: 2 events with command == 0.0 — ON SUPPORT,
  scored as nonviolations;
- OFF SUPPORT: ONLY events whose candidate command is absent/None,
  or failing a separately pre-registered availability predicate.
  A numeric zero may NEVER be used as an absence test.

The verdict accounting deduplicates to the nine events and
publishes both the 9-event support and the 7-event sign-evaluable
subset. Off-support events are not excused by lacking a pair:

- a NEW-path violation on an off-support row ALSO fails row 4
  closed — the safety criterion is absolute for the candidate path,
  on support or off it;
- an OLD-path violation on an off-support row is reported
  descriptively (it informs the historical record; it cannot indict
  or excuse the repair);
- every off-support row is listed with the reason it left the
  support, so the mask can never silently discard a violation.

## 2. Opposition-to-velocity rate (telemetry descriptor)

Renamed per the ruling; carries NO pass/fail semantics. **No
equivalence claim will be made on this descriptor in the restamp
verdict** — this is declared now so no margin is ever back-derived
for it after the fact. It is reported per approach, both paths,
descriptively.

## 3. If a rate-equivalence claim is ever needed (pre-registered in advance)

Should any future verdict require an equivalence statement on the
opposition-to-velocity rate (e.g., a liveness argument), the margin
is registered NOW: **10 percentage points at the approach level**,
paired common support, both paths scored by the identical mask. If
the paired difference exceeds 10 pp, equivalence is NOT claimed and
the difference is named and investigated. This margin was chosen
from the descriptor's role (damping-activity character, where the
unattenuated anchor is EXPECTED to act somewhat more) before any
paired delta existed.

## 4. Mask and accounting requirements (binding on the artifact)

(Third amendment, still pre-evidence: this section previously
demanded an explanation of "why 16 owner-term rows yield 13
new-command rows" — the WITHDRAWN row mask surviving as a normative
requirement. Removed: 13 was obtained by treating numeric zero as
absence. The count 13 may appear ONLY as a labeled LEGACY
TRACE-LEVEL COUNT — produced by incorrectly treating zero as
absence — and must not define support, the verdict denominator, or
any acceptance requirement.)

The re-score publishes: the exact formula and conventions; the
old/new event-selection masks in COMMAND-EVENT terms (16 trace rows
-> 9 unique command events -> 7 sign-evaluable + 2 zero-command
nonviolations, per §1's layering); the provenance of the historical
count 28 — reconstructed, or declared unreconstructible from the
identified historical harness with the harness evidence shown;
paired counts on the identical COMMAND-EVENT KEY
(flight_id, trial, mono_ns) — never trace-row timestamps;
approach-level summaries (never row pseudo-replication); and the
criterion commit hash of THIS file beside the evidence commit.
Wherever earlier sections say paired "row set" or "same timestamp",
the verdict unit is the unique command event at its exact event
key; trace rows persist for provenance only.
