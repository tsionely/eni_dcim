# RESPONSE to ADVISORY 3 (crossing time / along-track) — same-day results

Paste back to think-tank #1. Three of your asks were answerable the same
day; two produced ship-grade results. Dispositions below.

## 1. T3 — SHIPPED (structural, with the veto you specified)

The no-arm rule is in the planner: the sink-insurance decision is taken
ONCE, at gap entry (fix age crossing 0.3s), from the state the last
fixes left behind — if the altitude hold is already commanding a climb
there, insurance is VETOED; otherwise it arms and holds frozen. Nothing
switches on mid-coast. Unit tests pin both directions: the F1 stacking
class is structurally unreachable (blind coast can never ADD climb to
an already-climbing hold), and the phase3h sink class remains covered
(insurance still arms on a non-climbing entry). Your "replay the F1 log
under the rule" test moves to the analyst with the full recordings.

## 2. H5 — ANSWERED: the deepest absolute range source is ALIVE

Test-pinned, not a log line: sides-only scene, prior with range off by
+0.3m → the tracker recovers Z to 2.00±0.01 from the side bars alone.
The separation direction survives the SVD truncation. The capture basin
is bounded by the search ROI (±20px ≈ 0.4m range error at 2m); beyond
it the tracker returns None — graceful, never wrong. Your T2 therefore
reduces to: (a) the H3 census (assigned), (b) border-exit anchors
(adopted, rides V2), (c) possibly widening the ROI adaptively with
predicted covariance — noted for the T1 work item.

## 3. H1 — ANSWERED, and the harness now reproduces the real failure

Warm/cold split on F1 (chained slices, 2.3s vision history vs 1.2s):

| condition | range error (0.6s blind) | vertical ty error |
|---|---|---|
| cold | +1.77 m | 0.00 / 0.26 m |
| warm | **+0.97 m** | **−0.69 / 0.76 m** |

Two findings. (a) Your mechanism confirmed: ~45% of the along-track
error was cold-start artifact; the honest along-track number for T1's
baseline is ~0.97m per 0.6s. (b) The WARM run's vertical error flips to
−0.69m — the estimator, with a converged (climbing) velocity, now
reproduces the F1 balloon signature inside the harness. The harness has
become a faithful testbed for exactly the failure that killed the real
flight — T1's kill test (iii) will be scored against these warm
conditions.

## 4. Remaining dispositions

- **T1 (plane filter, shared-root t_c, bias stitching)** — ADOPTED as
  the next estimator work item. Your identity (1/s linear/parabolic in
  t, all gate-plane scales sharing one root) replaces the median-ratio
  τ we had adopted; the "no real root ⇒ won't arrive ⇒ abort early"
  bonus is noted as a free retreat trigger. Degree schedule per the
  commanded profile as specified.
- **T2 border-exit anchors** — adopted; implemented with V2 (they share
  the visibility schedule machinery).
- **T4 pairwise separations + shared-t_c RANSAC** — adopted inside T1;
  gated on D6 blur/track numbers as you specified.
- **T5 mask extents** — accepted as last-ditch inside T1's framework.
- **§5 row-consistency check** — adopted; joins D5's 512 px·m product
  as the F2 arbitration pair (both one-liners in the analyst harness).
- **Gap-as-planned-phase (§3)** — adopted wholesale: predictor +
  front-load + freeze + clock-coast + mismatch alarm. Lands with T1
  (the predictor needs Ẑ/Ż from the plane filter).
- **Structure-identity-as-vertical-measurement** (§0 unifying note) —
  noted and folded into V2's design: banner-last ⇒ HIGH is exactly
  F1's final second.

## 5. Assigned (analyst pack, updated)

H2 (harness on F2 + clean pass), H3 (visible-edge identity census over
the last 1.5m of F1/F2 — also validates V2), H4 (=R4 banner band,
already assigned), T3 kill test (i) on the full F1 log.

## 6. Same-day addendum — the analyst pack landed and one more guard shipped

The analyst's round-3 pack (committed) settled several open threads:

- **D5 verdict on F2: systematic garbage.** Nearly every close F2 fix ran
  the 512-product at 0.33–0.46 (R·w_px 169–235) — the detector had locked
  a narrow sub-structure and PnP invented poses; both "believed" and
  "true" ty in the earlier F2 row were fiction. SHIPPED in response: a
  scale-consistency gate in the detector (R·max(w,h)px vs fx·W within
  [0.65, 1.5]) plus a grazing-normal guard (|n_z| ≥ 0.35 — we never
  approach a gate edge-on). Replay diagnostics show surgical behavior:
  flat strip-fits (254×33, 408×78 px quads with |n_z| 0.10–0.32) are
  killed, proper ring quads survive, and the deepest legit fix (1.50 m —
  the same frame the analyst's vertical study independently chose as the
  last trusted fix) is preserved.
- **R4: the banner bottom sits +0.15 m above the OPENING CENTER** — not
  ~0.9 m. This re-frames V4 entirely: the banner's bottom edge is a
  near-center reference line visible to ~1 m. It also explains Test A's
  failure (it was run with the d*≈0.8 top-bar assumption against what
  was, at least partly, banner structure); Test A reruns with the
  measured geometry and a bar/banner identity split.
- **R1: ribbon availability in the last 2 m is 41% (F1) / 62% (F2)**,
  87–100% of it below the compensated horizon — V1 lands as an
  opportunistic measurement, not the primary loop, per your own ≥60% bar
  (borderline).
- **Balloon test: corr(vertical DR error growth, pitch rate) = 0.81 on
  F1** — the blend-lag mechanism is real and feeds T1's noise model as
  you specified.

## 7. For your next turn

T1 is now the critical path and its spec is yours; before we implement,
one design question: the plane filter's state is (Z, Ż[, Z̈]) with
per-source nuisance scales c_i. Recommend the minimal robust scheme for
estimating the c_i of a RELATIVE source that never overlaps an absolute
one (possible for banner feeds if the tracker dies early): pure bias
stitching from Ẑ at handover freezes the current error into c_i — is
there a better anchor (e.g., the border-exit ping retroactively
re-scaling the source's history), and what does its failure look like?
