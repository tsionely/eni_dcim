# RESPONSE 47 — The farm WAS on disk: 23 clusters; the big number is the defect's shadow, not physics; the mechanism survives its refutation branch; one FAIL challenged on definition

Tasks A and B landed (commit 5c69823, artifacts under
tuning/taskA-full-archive-retro-census-bb0dbcf-20260720T165623Z/ and
tuning/taskB-five-cluster-DIAGNOSTIC-bb0dbcf-20260720T183318Z/).
Read row by row against the pre-registered criteria. Every number
below carries its artifact; the walk discipline applies to ourselves
first.

## 1. Task A — the census (summary.md, expanded_census_clusters.csv)

61 directories, 115 eligible recordings, **23 legal clusters** —
PASS_GE_6 by nearly 4x. Advisory-20B's instinct ("mine the recorded
world first") is vindicated at scale: the sixth cluster was on disk
eighteen times over, and zero flights were spent finding it.

The censoring ledger's other face (censoring_ledger.csv): 178
approaches examined, 155 censored across six labeled funnels (53
NO_CERTIFIED_FULL_BELOW_3P5, 45 NO_CLOSE_FEATURE_EPOCH_LE4P5, 24
scale-gate class, 20 no-parallel-SIDE, 10 no-maintenance-interval,
3 no-anchor). **Archive-scale Y_eligible ~ 23/178 = 0.13** — the
earlier 0.50 (5/10) was small-sample luck, exactly as the Wilson
interval (0.24-0.76) warned. The availability picture for cohort-4
must be rewritten around ~13%, not half: this is the ledger doing
its job — bounding treatment availability BEFORE a cohort reads
its own census as a surprise.

## 2. The release fit read honestly: inadmissible, not failed

release_fit.csv: 23 clusters, 1638 rows, point sigma_a = 1.307,
profile U95 = 1.400, bootstrap U95 = 1.735 — all far above 0.35.
But this fit ran on the OLD attenuated-anchor residuals, where
every cluster carries its own deterministic signed offset
(b0_j = -(1-auth_j)*v_latch_j — measured at -0.683 on the
auth=0.220 cluster alone). The doctrine both channels ratified
governs: **"a variance model may describe random drift only after
signed deterministic drift has been removed or explicitly
budgeted."** That precondition is unmet, so the number is neither
release-FAIL physics nor simple data-insufficiency — it is the
LATCH DEFECT'S SHADOW measured at archive scale, and the fit is
INADMISSIBLE as a release instrument in this form. (Consistent:
era LOAO found every held-out flight pushes over the gate — no
single-era rescue, because every cluster carries its own bias.
era_heterogeneity.md.)

The decisive experiment is cheap and tasked: the SAME v2.1
pipeline on the SHADOW (repaired-anchor) residuals over the same
23 clusters, DIAGNOSTIC label. If the mechanism is what the
five-cluster table says it is, U95 collapses; if it does not
collapse, the mechanism is not the whole story and the remainder
gets named next.

## 3. Task B — the mechanism survives its refutation branch

DIAGNOSTIC_delta_latch_mechanism.csv: the pre-registered
refutation branch — auth ~ 1 clusters retaining large same-sign
b0 — is EMPTY: all three auth=1.000 clusters sit at |b0| <= 0.020.
The auth=0.220 cluster moved b0 by -0.913 against a predicted
-1.122 (81% of the prediction); regression slope 0.804, intercept
-0.011 over 119 rows. Verdict per the registered test: SUPPORTED,
not yet closed — the unexplained remainder is real and named:
b0_new = +0.231 on the low-auth cluster (and -0.033 on one
auth=1.0). The 23-cluster shadow fit's b0_new distribution
adjudicates whether the remainder is one cluster's local structure
or a second mechanism.

## 4. The R26-1 shadow restamp FAIL — challenged on DEFINITION, with counts

DIAGNOSTIC_r26_1_restamp_verdict.csv: liveness intact (16
owner-term SIDE rows, first capture 1.903 m, max admission 0.2709,
zero phase changes, zero slew breaches) — FAIL rests solely on
"28 wrong-sign command rows." Independent column analysis of
DIAGNOSTIC_r26_1_anchor_trial_rows.csv:

- command vs the NEEDED CORRECTION (e): **0/96 opposed (old),
  0/13 opposed (new)** — with or without deadband.
- command vs the CURRENT true velocity: 24/96 old, 6/13 new
  (threshold-free; 16/80 and 4/11 with a 0.02 deadband).

Every "wrong-sign" count in the family comes from the
cmd-vs-current-velocity comparison. A correction command that
opposes the current velocity is ORDINARY servo behavior — braking
a sink, reversing an overshoot; the registered criterion ("no
wrong-sign command") has always meant commands against the needed
correction. Under that reading both builds score ZERO violations,
and — decisively for the repair question — old and new show the
SAME opposition rates, so no repair-introduced regression exists
in this comparison under EITHER definition. The definitional
question goes to both channels with the raw counts; QA is asked to
disclose the harness's exact formula and re-score under
cmd-vs-correction. The restamp verdict is HELD OPEN, neither
accepted as FAIL nor overturned unilaterally.

## 5. Tasked to QA (instruction issued with this note)

1. Shadow-residual v2.1 fit, same 23 clusters, same pipeline,
   DIAGNOSTIC label; publish b0_new per cluster for all 23.
2. Wrong-sign formula disclosure + re-score under
   command-vs-needed-correction; republish the restamp verdict
   under both definitions side by side.
3. Y_eligible by era from the ledger + the frozen compound-
   signature 2x2 across all 178 approaches (the freeze holds: no
   threshold moved).

## 6. Board

Row 3 (mechanism): SUPPORTED, refutation branch empty, remainder
named — closes on the 23-cluster shadow distribution. Row 6 (U95):
the old-path number is INADMISSIBLE by the ratified precondition;
the admissible read awaits the shadow fit and, for release, the
REPAIRED SHIPPING build per the re-earn rules. Row 4 (R26-1
restamp): HELD OPEN on the definitional question. Rows 1-2 and the
closed list unchanged. Census requirement SATISFIED (23 >= 8: the
full registered tier applies, not 6-7). P2: moot unless the
cluster set shrinks under adjudication. Cohort-4 HOLD; Sakana
STANDBY; sigma_a_cfg 0.35.
