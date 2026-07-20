# RESPONSE 26 — The rung's last blocker is its rate row; a ruling question

State after the a150ece rerun (fdd19a8) and the certificate-boundary
patch (5a9aa79): the latch works (SIDE alive through FULL loss — 394
rows in the 29-sweep), exact pairing works, transitions occur, and
the two-component sigma design produced honest numbers:

    sigma_e (paired, n=202):        0.038   — better than FULL's 0.05
    sigma_v paired-switch:          0.277
    sigma_v maintenance (§7B):      0.195
    release sigma_v (max of both):  0.277

The arithmetic that follows is the whole story: with sigma_v = 0.277
at the 0.5s tail, the side rung's own continuous-test floor is
2·sqrt(0.038² + (0.5·0.277)²) + 0.06 = **0.349 > 0.30** — the rung
fails its corridor even for MAINTENANCE, demotes to neutral-decay,
and ownership cannot be held through FULL→SIDE. That is exactly what
the harness observes (zero owner_term_side_rows). Position is earned
and excellent; the RATE is the blocker.

## The ruling question (one decision, three options)

During side-maintenance, where does v_z come from?

(a) **Frozen-rate maintenance**: at the transition, HOLD the last
    full-quad-derived v_z (the servo's own damping schedule already
    de-weights rate near the plane; the tail is ≤0.5s). Sigma_v for
    the crossing test becomes the FULL rate sigma plus a drift term —
    passable floor. The side rung contributes POSITION only (its
    earned 0.038), which is precisely its strength.
(b) **Longer side rate windows**: Theil-Sen over the full side tail
    (not recent-12) to average the row noise — costs latency, may not
    reach 0.15 in time.
(c) **Accept the rung as position-only maintenance with faster
    neutral-decay** — the most conservative; the final 0.5s flies on
    the servo's damping design as it already does today.

Our recommendation: (a), pre-registered and fixtured — it uses each
source for what it measured well (FULL: rate history; SIDE: fresh
position), never fits a slope across the boundary, and the frozen
rate is exactly the "measurement-model change, not a phase change"
doctrine applied to the rate channel. Awaiting both channels' ruling
before any build.

Meanwhile green and holding: certificate boundary patched per the
audit (promote 1.6, no fresh identity in the terminal band, relock
clears — the successor-inheritance root wire is closed and pinned);
the 0.744 contradiction resolved (all Class C frontal clips); the
archive caps h_up < 0.70 / h_down < 0.719; the brake-pitch file
CLOSED (no nose-up enrichment — the queued fix is not justified).
