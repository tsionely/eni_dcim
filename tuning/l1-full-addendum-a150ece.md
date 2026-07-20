# L1 Addendum Rerun on a150ece

Role: QA & MOCK-TUNER.
Scope: recorded-video replay only; no real simulator was launched, reset, clicked, or commanded.

Run artifacts: `tuning/l1-full-addendum-a150ece-a150ece-20260720T094216Z/`
Source commit under test: `a150ece6b6ef41c48d3f573c35d25ee2b72f0b32`
Repo HEAD while running the detached worktree: `a150ece6b6ef41c48d3f573c35d25ee2b72f0b32`
Non-tuning delta from `a150ece`: `[]`

## Four-Part Verdict

1. Full->side transitions: observed in the forced FULL-withheld sweeps, but they are not legally healthy yet. The replay produced 7 FULL->SIDE transitions, all with `paired_overlap_count=0` at the switch row; `jump_grace_consumed=False` throughout, and 7 transition rows carried `sigma_induced_abort_after=True`.
2. Earned sigma row: exact-exposure pairing is now used for SIDE-vs-FULL overlap. Primary F2/F4: `n=21`, `sigma_e=0.049m`, paired-switch `sigma_v=0.509m/s`. Sweep29: `n=189`, `sigma_e=0.035m`, paired-switch `sigma_v=0.277m/s`.
3. S5/dropout/full-withheld sweeps: SIDE production is alive (`feature_side` rows: 38 primary, 394 sweep29), but TERM ownership never moves to SIDE. The full-withheld sweeps have `owner_term_side_rows=0`.
4. Shadow-capture conjunction: NO-PASS. Some baseline FULL captures exist, but no replay produced the full conjunction of observer-ready, admission score <= 0.30, shadow owner TERM, POSITION phase, valid provenance, and held TERM through FULL->SIDE without sigma abort.

## Two-Component Sigma-v

The previous `0.294m/s` sweep29 number came from short-window inter-source slope differences. On `a150ece`, exact-exposure paired-switch recomputes that component as `0.277m/s`.

The new section-7 FULL-withheld maintenance-interval component is lower:

| Cohort | paired-switch sigma_v | maintenance n | maintenance sigma_v | release sigma_v |
|---|---:|---:|---:|---:|
| `primary_f2_f4` | 0.509 | 5 | 0.290 | 0.509 |
| `sweep29` | 0.277 | 58 | 0.195 | 0.277 |

Release sigma remains governed by paired-switch, not maintenance, for the populated all-range rows.

## Working-vs-Ceremonial

Verdict: SIDE is no longer dead, but it is still ceremonial for ownership on this replay set. The rung emits measurements and can become the active observer source under forced FULL loss, yet it does not maintain TERM ownership and does not pass the shadow-capture gate.

Key files:

- `summary.md`
- `shadow_source_transitions.csv`
- `shadow_capture_summary.csv`
- `earned_sigma_summary.csv`
- `maintenance_sigma_rows.csv`
- `maintenance_sigma_summary.csv`
- `two_component_sigma_summary.csv`
