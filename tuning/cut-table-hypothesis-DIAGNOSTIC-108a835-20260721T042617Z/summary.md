# Repair-Worsened Cut Cross-Tab

Scope: DIAGNOSTIC CSV-only; no FlightSim/DCGame launch and no intervention rerun.
Repo HEAD: `108a835f417df568018ad9d2f48e1d989bae97a1`.
Criterion commit: `9a85c7365994e87941636ccd567a87f42c417a21`.

## Why No Rerun

The requested `26fb3b4` content is an ancestor, but current tip also includes `RESPONSE64`, which makes the valid-stream intervention rerun NO-GO until REG-2 and machine fixtures are ancestors.

## Source Note

The full 23 forced sample CSV has `r_v_new_mps == r_v_mps` on every row, so it cannot classify repair-worsened cuts. The primary cut-level cross-tab therefore uses `taskB-five-cluster-DIAGNOSTIC.../DIAGNOSTIC_anchor_policy_samples.csv`, which has real old/new residual columns but only five diagnostic clusters. A 23-approach appendix uses `02_shadow_b0_new_per_cluster_split.csv`, which is approach-level, not cut-level.

## Cut-Level Headline

Cut units total: `26`.
Cut units estimable: `12`.
Cut repair-worsened units: `0`.
Cut worsened fraction: `0.0`.

## 23-Approach Appendix Headline

Approach units total: `23`.
Approach units analyzable: `23`.
Approach repair-worsened units: `2`.
Approach worsened fraction: `0.08695652173913043`.

