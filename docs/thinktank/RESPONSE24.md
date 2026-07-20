# RESPONSE 24 — Rung-2 production unblocked: the parallel side stream

The L1 addendum's precise blocker ("no legal full->side transition in
29 recordings — insufficient SIDE evidence to mature the rung") had a
structural cause: the close tracker — SIDE's only producer — ran only
when the detector FAILED, so the overlap volume that matures the
rung, earns its sigmas, and legalizes transitions never existed by
construction.

Build (176/176, mock-verified): below
`perception.close_tracker.parallel_below_m` (3.5m) the tracker now
runs on the SAME anchored frame as a successful detection, publishing
its SIDE feature on its OWN topic (`feature_side` — a latest-value
cell must not let the side row shadow the full row) and never its
detection (the detector's fix is the better pose; one estimate per
channel). The app observes the side stream into the oracle's side
history every commit tick — same exposure, no extra note_exposure.

Mock end-to-end: 50 side rows in one flight, 47 SIDE_PAIR, 29
certified, **50/50 sharing an exposure with a FULL row** — perfect
paired overlaps. The shadow-capture green (F2 at 1.903m,
admission 0.221) stands from the addendum run; the QA rerun on this
tip is expected to finally produce legal transitions, the earned
sigma row, and the S5 sweeps with a live side rung.
