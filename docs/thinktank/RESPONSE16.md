# RESPONSE 16 — P1's verdict repaired at the actuation end; A8 collapse and the expiry collision, both routed for ruling

Three analyst deliveries and the calibrated mock A/B landed together.
§1 is the repair for the binding constraint (built, fixtured, smoked);
§2-§3 are two findings that need your ruling — both dispositioned
conservatively meanwhile; §4 is the mock's first actuation.

## 1. P1 verdict → the commit vertical damper (built)

The analyst's adjudication: FOV-leave 5/6 (bloom exonerated —
red_frac normal at every loss frame), vz oscillation 6/6, slot
geometry identical to cohort-1. The vertical chain chasing the
between-fix velocity-estimate sawtooth (vz peak-to-peak 2.0-4.65 m/s
at loss, against a hold cap of 0.8!) bobs the airframe, and the gate
— already low in the +29°-up camera's frame at 3-4.5m — exits the
bottom.

The repair, at the actuation end: **the in-commit vertical is a TRIM,
not a chase** (commit is entered pre-aligned; align owns big
deficits). Deadband 0.15m around the aim, hard cap 0.35 m/s, slew
1.5 m/s² — estimate noise cannot ring the airframe; the once-decided
sink insurance (≤0.1) rides on top so the no-arm rule's covered class
stays covered. Fixture pair per the pattern book: oscillating
believed bounded (SAFETY), steady trim deficit still climbs
(LIVENESS). 169/169 green.

Honest note on the root: the sawtooth is the caged gravity residual's
signature — velocity error accumulating between fixes, snapped back
at each fix. The damper treats the symptom at the last, safest joint;
the frame-unification package remains the cure, its canary already
pre-registered.

Pre-registered for cohort 3 (phase6l): commit vision survival past 3m
rises materially from 1/6; the 4.3-4.8m blind-brake cluster
disappears or re-attributes to honest scene causes; the fork metric
(first commit reaching <1.1m ⇒ pass) resumes expressing.

## 2. A8 collapse — ruling requested (chain HELD conservative meanwhile)

The rider verification you ordered found the base: 3/11 of the graze
samples used FAR-STATE belief (R≈5.2m) for true_dz; contact-valid
repair leaves **h_drone unsupported** (the contact-valid extraction
yields no usable vertical half-extent; scatter max 1.30 mixes low
grazes and must not tighten the chain).

Disposition pending your ruling: **all chain constants HELD** —
cmd_clamp 0.10 and C_contact 0.18 sit on h=0.62; if the true h is
SMALLER, C_contact is larger and 0.10 is conservative-safe (the error
direction cannot license contact). Block B ±0.12 remains legal under
any h ≤ 0.68. The derivation table's base row is marked UNSUPPORTED.
Requested: a re-extraction spec — contact-instant states only,
minimum n, both tails, sim collision-model cross-check — before the
chain tightens OR loosens. The lateral debt stands (zero side
events; the mock has no airframe half-width to borrow).

## 3. The expiry collision — CORRIDOR_INTERIM does NOT execute its expiry

R5's library exists (n=55, containment 100%) and the analyst read the
expiry key as triggered. Two reasons it cannot execute yet, submitted
for ruling: (a) expiry assigns corridor := C_contact, whose base h
just became unsupported (§2) — a corridor may not re-derive from a
constant in collapse; (b) the library is CONTROL-ARM ONLY (the
treatment axis was mute this cohort; zero live-arm crossings). The
interim stays 0.30; proposed re-arm condition: {valid contact-grade h
extraction} ∧ {live-arm crossings in the library}.

## 4. The mock's first actuation, decomposed

owner=term in 2/10 runs — 104 rows, sign clean, zero chatter, zero
wrong-sign: the wire, calibration, arithmetic and door compose for
the first time in any domain outside the real F4. The 8 no-capture
runs decompose: 2 oracle-starved (ready=0), 6 ready-but-unadmitted
(mock e_z quality at 320px vs the corridor — a mock-domain
resolution question, not a wiring fault). The door's 281 rejects are
believed-drift consistent — the tier-2 probation door (your §2
tier-2) is queued as the next terminal build with these runs as its
liveness fixtures.

## 5. What flies

Phase6l = cohort 3 on the damper build: same alternating six at 1.8,
same treatment variable, endpoints re-registered in §1. The stop
policy, retrace escalation, geometry-relative door, and ratified
admission all carry. Sakana flies on release of this note.
