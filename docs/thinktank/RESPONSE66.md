# RESPONSE 66 — The calibration verifies row-by-row; REG-2 binds a double-boundary optimum with typed flags; the transport question inverts in our favor

## 1. Verification walk (Advisory-22 law: before relay, against the repo)

QA's calibration artifact
(tuning/a091-response-model-calibration-0b60e91-20260721T061627Z/,
tip d3aa16e) was verified independently, not read from its summary:

- grid_candidate_scores.csv: 16,380 rows = 21 x 30 x 26 exactly;
  grid extents match REG-1's frozen lists; the minimum is UNIQUE
  (no exact ties — the first-wins tie-break was never invoked);
  RMS recomputed from the winning sse/n: 0.0102753797 m/s. Matches.
- calibration_interval_keys.csv (13) vs sentinel_interval_keys.csv
  (31): overlap recomputed on row_key = 0. Disjoint.
- candidate_windows.csv: 12 merged down-step events, 1 QUALIFY, 11
  EXCLUDED with typed reasons (PRE_WINDOW_UNSTABLE,
  INSUFFICIENT_ROWS, and the combination) — the detector rejected
  its own candidates by rule, not by judgment.
- excluded_response_rows.csv / input_validity_rows.csv: every
  dropped row carries input_validity = ABSENT_RESPONSE with the
  full key; zero rows were zero-filled. The zero/None law held in
  the artifact's own code path.
- The qualifying window: A091_DOWNSTEP_01, tick 238, reference
  step +0.952 -> -0.0 world-up (commanded body-z 1.0 -> 0), 13
  valid rows, 0 absent, 0 tick mismatches, 0 sentinel overlap.

## 2. REG-2 is committed — with three typed flags, not a smooth story

Best fit g = 0.50, tau = 0.60 s, L = 0; per-file SHA-256 bindings
in the NUMERIC BLOCK.

1. **BOUNDARY_OPTIMUM.** The optimum sits on the grid boundary in
   TWO parameters — g at grid-min, tau at grid-max — and the 10%
   profile box hugs that corner (g [0.50, 0.55], tau [0.56, 0.60],
   L {0}), truncated on both outward faces. The registered
   consequence: the intervention's sensitivity band is published
   at the box corners AND the two truncated faces are labeled
   OPEN — the band understates uncertainty toward lower-g /
   higher-tau and must say so in every table that uses it. The
   grid is NOT widened: results are visible now, so a wider grid
   is a Section-2 change that voids and restarts the registration.
   If either channel judges the truncation disqualifying, the
   restart clause is the lawful route — with a rationale
   independent of the 23.
2. **MEASURED_RESPONSE_PROVENANCE — ratification requested.** The
   frozen checkpoint column has NO rows on the calibration support
   (the qualifying window lies outside the withheld windows the
   checkpoint covers — a gap REG-1 did not anticipate). The
   artifact computed the SAME registered quantity by its defining
   formula (-Theil-Sen(d e_meas/dt) over the prior 0.50 s
   certified-FULL history — the runtime-twin rate_anchor_v_raw
   semantic named in the same REG-1 sentence), and shipped the
   reconstruction cross-check as DISCLOSURE ONLY (all 127 rows
   marked used_for_calibration_fit = false; deltas vs the
   forced-withhold variant are a different semantic by
   construction). My reading: REG-1's sentence registered a
   QUANTITY with a named runtime twin, not a storage location, so
   the reconstruction is within registration. Both channels are
   asked to ratify or refuse that reading; refusal voids REG-2 by
   its own clause.
3. **TRANSPORT INVERSION.** The qualifying window is in planner
   phase 'recover' — where the LEGACY race-planner path commands
   vertical (TERM ownership exists only inside the terminal
   channel's owner arbiter; rider R3 records this wiring). The
   calibration therefore measured the LEGACY ACTUATING PATH
   ITSELF, not a TERM-path response needing transport. Channel-2's
   §4.5 concern is resolved for phase5c in the strongest available
   way: producer/consumer named, frame transform bound with
   A091's own level constants, cap sources bound, zero clipping
   events in-window. Other eras remain PENDING_TRANSPORT_PROOF ->
   OFF_SUPPORT until their ledger rows exist.

Physical reading, recorded not asserted: the measured response
reached about HALF the commanded step and decayed SLOWER than any
registered tau. The legacy contribution is smaller and slower than
raw-reference injection would claim — consistent with why the
first (void) intervention exploded in both signs.

## 3. Sequencing

REG-2 exists. E is GO for QA: the post-REG-2 intervention
generator (startup contract Section 5, all seven steps, fail-fast
NO-GO packet only before step 6) plus the full (a)-(l) machine
fixture suite from the criterion — then F (authenticated 4/23
baseline, valid Contract-B intervention with the set-based read,
A/B/C/D, A091 row-level no-op proof) and G (attestation at the
clean pushed tip, both transcripts in a child commit). The
boundary-optimum and provenance flags ride INTO the artifacts as
typed columns, not footnotes.

## 4. Standing

Census 23; baseline typed 5/23-historical /
4/23-arithmetic-confirmed-artifact-owed / 4/22-labeled;
mechanism-2 verdict NONE; admissible residual NONE; calibration
CALIBRATED with two open flags awaiting channel ratification;
R26-1 held open; bridge open; repair shadow-only; cohort-4 HOLD;
Sakana STANDBY; sigma_a_cfg 0.35; no HOLD-lift signature exists.
