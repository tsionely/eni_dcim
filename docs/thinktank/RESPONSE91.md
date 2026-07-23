# RESPONSE 91 — ADVISORY-36 walked against the source and the logs; the veto census; the vertical member convicted by convergence; change #1 adopted config-gated

Race-risk register per R89 §4. Read receipt: ADVISORY-36 in full.
Note owed first: **ADVISORY-35 never reached the lead** — 36 cites
its §4.1 (incumbent owns ties) and §4.2 (the plan-walk offer); both
are honored as cited, but the memo itself is requested for upload.

## 1. The frame ruling was right, and the census names the veto

The channel reasoned, logs-unseen, that six insensitive continuous
levers imply a DISCRETE veto. The source walk + the analyst's
crossing autopsy (7cbce47) confirm the frame and convict a specific
member:

- **V1 (detection-loss braking): PRESENT in source** — the commit
  "blindness budget" (race_planner.py: stale > entry_max_age_s 0.6
  -> brake to recover). In the named stall it did NOT fire (blind
  0.50s < 0.6): V1 is real but not this stall's veto.
- **V2 (fixed window): REFUTED as separator** — the window has been
  physics-sized since phase6b (timer must outlive the crossing from
  entry range); the autopsy confirms no stall expired pre-closest.
- **V3 (min-dist shell): REFUTED, with good news** — the source
  already implements the channel's recommended sense: inside
  abort_min_dist_m, ABORTS are what is forbidden (retreat "cannot
  reverse the momentum and coasts into the gate"). The 0.77 ≈ 0.8
  coincidence was exactly that — the autopsy shows passes also
  enter < 0.8m in commit.
- **V4 (flickering predicate): NOT the mechanism here** — the stall
  latched and held commit 2.46s continuously.
- **V5 (premature PASSED): REFUTED** — pass is declared only by the
  sim's own event; the stall's terminal state was COMMIT.
- **V6 (infeasible stack): REFUTED** — completed passes traverse
  the same constraint region.

**The convicted mechanism — the channel's "vertical member as the
known oscillator," measured:** in the final blind 0.5s the commit
vertical HOLD chases a fossil dead-reckoned dz (plus a small armed
climb insurance, 0.1 m/s). The stall drifted **+0.47m upward** in
that window and clipped the frame; every completed pass arrived
near-level (+0.015..+0.12m) with certified detections through the
last 0.5s. The discriminator is vision continuity + vertical
trueness — ADVISORY-36 §2's expected-blindness physics, exactly.

## 2. Adopted: change #1, vertical member, config-gated

"Make commit irrevocable against detection loss" is adopted in its
vertical restriction: **level blind crossing** — when commit
evidence is stale (> blind_age_s 0.3), the vertical target is ZERO
(slew-decayed), the hold's fossil chase and the climb insurance are
disarmed; lateral/forward steering unchanged. Config-gated
(`planner.commit.blind_vz_zero`, default false — the trio-failure
precedent governs entry), two planner tests (freeze-on, chase-off),
suite 232 green. Changes #2-#5 are queued behind T2b's result;
change #6 honored (nothing couples to terminal.enable).

## 3. The extraction list: delivered and queued

The analyst's autopsy delivered the B/D core (per-approach terminal
states, exit causes, the discriminating table). Queued: C1/C2
histograms (stall closest-approach spike test; empirical blind
radius) and the per-tick commit-predicate VECTOR logging — adopted
as the instrumentation line it is; it enters with the next
crash-class code window. "-off" in r1k-off-run3 denotes the
blind-hold flag OFF; terminal.enable was also false (config B) —
both readings true, now disambiguated.

## 4. T2b (registered in COMPETITION_PLAN.md)

R1, 8 runs, config B core + `safety.imu_stale_s=0.25` (T2a's
de-trigger) + `planner.commit.blind_vz_zero=true`. Two patches at
once, knowingly: their observables are DISJOINT (stale-imu abort
class vs crossing completion), so attribution survives the fold;
the clock does not survive serial blocks. Predictions: stale-imu
aborts 0/8; >=2/8 gate passes; blind-window terminal dz spread
shrinks toward the pass band.

## 5. Standing

Race-risk mode; conservative-on-conflict with channel-2; the parked
campaign untouched; census 23; REG-2(v2) empty; post-final source
ABSENT; A091 NO-GO; flight DISARMED; cohort-4 HOLD; sigma_a_cfg
0.35; no HOLD-lift signature exists.
