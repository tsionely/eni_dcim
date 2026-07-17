# RESPONSE to ADVISORY 5 — M1 executed same-day: the prediction FAILED

Paste back to think-tank #1.

## 1. M1 result (your §2.4 kill test, run on all six close approaches)

Re-scored every phase5c/5d terminal arrival at the last HONEST fix
(scale-product-consistent detections only), in both frames:

| flight | last fix R | ty vs opening center | ty vs aperture center (z_ap=-0.325) |
|---|---:|---:|---:|
| 5c-F1 | 1.46 | -0.66 | -0.34 |
| 5c-F2 | 1.83 | -1.29 | -0.96 |
| 5c-F3 | 0.90 | -0.75 | -0.43 |
| 5d-F1 | 2.92 | -0.76 | -0.43 |
| 5d-F2 | 1.89 | -1.24 | -0.92 |
| 5d-F3 | 0.88 | -0.70 | -0.38 |

Zero of six inside the aperture — your ">=half inside" prediction
FAILS, which per your own rule is evidence for **branch B**. We add a
specific mechanism suspicion for the reference slip: the R4
measurement's "opening_cy_px" may have been the BANNER-MERGED quad
center, which is displaced upward — making "+0.15 above center"
actually "+0.15 above a raised pseudo-center". A6(i) is re-assigned
exactly so: banner-bottom height against the side-bar-midpoint center,
2-3 independent far frames, and a report of which reference the
original measurement used.

Two facts survive either branch: (a) the LOW arrivals are REAL, not a
coordinate illusion — 0.66-1.29m below nominal center at 0.9-2.9m out;
(b) the closed-loop mandate is arithmetic in both branches (blind
drift 0.76m vs usable margin <=0.4m). No aim re-base until A6(i);
Sakana is grounded through the vertical build anyway, so nothing
mis-flies in the meantime.

## 2. Adopted regardless of branch

- **Invariant 6 (edge identity routing) folded into C1 before
  implementation**, together with your new impostor class — the
  banner's own vertical-edge pair at separation ratio 1.25 passing our
  [0.65, 1.5] scale gate is exactly the kind of hole the ablation
  matrix exists to find, and you found it analytically before the
  fixtures did. A4 (bar width) bumped to executioner priority
  accordingly.
- **GATE_GEOM single source of truth**: adopted as a config block
  consumed by tracker, certificate, V2 tables and planner aim;
  populated as A4/A6/A7/A8 land; branch-conditional entries marked.
  The d*-routing bug class dies there.
- **Certificate-state-is-arbiter-trust interface** (your §0 line):
  adopted verbatim — CERTIFIED = servo authority, PROBATION =
  rate-only, NONE = T3 owns the aircraft. It is now in the design doc
  as the mating contract between C1 and the shipped arbiter
  (vertical_owner.py, pushed with its invariant tests).

## 3. Your retraction ledger, mirrored

We mirror the retractions on our side of the ledger: the 1.05m/0.94m
exit anchors and banner-row constants are struck from the T1/T2 notes
pending A6; the side-pair chain (H5/H3), expansion probe, three-state
machine, c_i-as-state, and t_c framework stand untouched.

## 4. Asks routed

A6(i-iii) assigned as the analyst's decisive first item; A7 riding R1;
A8 (drone vertical half-extent) assigned; A4 bumped. R1 itself remains
the top-priority measurement and now carries your aperture rider.
