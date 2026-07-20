# 0.744 contradiction fixture — forensics

**FID:** `20260720T071112-cd18c5fb`  
**Verdict:** All h_up=0.744 rows are Class C (frontal / post-impulse contaminated). Early hit is an independent episode without contact-instant truth — does not adjudicate a tail. Upper-tail premise is NOT tightened by this fixture; the 0.744 number is excluded with explicit frontal-burst reason.

## Class counts

- Class A (pre-impulse, same-gate, fresh, upper, valid): **0**
- Class B (post-contact, geometrically usable): **0**
- Class C (contaminated, excluded with reason): **3**

**Upper-tail premise (h_up≤0.64):** NOT_TIGHTENED — zero Class-A rows above 0.64

## 50ms incompatible-dz test (advisory-15 §1.2)

CONFIRMED on all 0.744 rows: each sits within 50ms of a LOW-tail dz (−0.162) while reading HIGH-tail dz (+0.056) — impossible as two vertical contacts; ordinary as FRONTAL clips carrying no envelope information.

## Early hit (event 0)

- Gap to plane burst: **0.1251s** (> EVENT_GAP=0.05s ⇒ independent episode)
- Verdict: **INDEPENDENT_EPISODE_NO_TAIL**
- Event 0 is ≥EVENT_GAP before the plane burst (independent episode) but every sample lacks contact-instant state (REJECT_no_state_gate / no gate_rel) — cannot adjudicate a tail. Does NOT tighten h_up or h_down.

## Per-row table

| ep | t_ff | Δt_auth | dz | h_up | R | age | pitch° | normal | class | exclusion |
|---:|-----:|--------:|---:|-----:|--:|----:|-------:|--------|:-----:|-----------|
| 1 | 4.6551 | 0.0343 | +0.056 | 0.744 | 0.852 | 0.0 | -43.5 | frontal_or_mixed | **C** | frontal_incompatible_dz_burst |
| 1 | 4.6620 | 0.0412 | +0.056 | 0.744 | 0.852 | 0.0 | -43.5 | frontal_or_mixed | **C** | frontal_incompatible_dz_burst |
| 1 | 4.6690 | 0.0482 | +0.056 | 0.744 | 0.852 | 0.0 | -43.5 | frontal_or_mixed | **C** | frontal_incompatible_dz_burst |

## Support-direction note

Impulse direction is **not logged** (magnitude only). Contact normal / member inferred from crossing-phase geometry (true_dz sign + tz depth). For the 0.744 rows, tz≈0.48m at R≈0.85 ⇒ depth_frac≈0.57 — classified frontal/mixed; combined with the LOW↔HIGH dz flip inside 50ms this is Class C.

## Deliverables

- `summary.json`, `rows_0744.csv`, this report
