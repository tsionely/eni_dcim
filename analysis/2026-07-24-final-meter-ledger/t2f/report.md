# T2f final-meter ledger — impossibility audit + residual classes

HEAD at analysis time: `9653371`.
Block coverage: **1/8** fixtures (PARTIAL — re-run when remaining sim-runs land).

## Questions

1. Did any withdrawal happen with believed s in [-0.9, -0.4] or on
   evidence older than 0.3s? *(should be IMPOSSIBLE under T2f)*
   → **NO — PREDICTION HELD** (impossible events=0: s-band=0, stale=0).

2. What class are the residual stalls?

   - **INCONCLUSIVE (needs UNLOGGED exit/predicate)**: 1

Same §4–5 control-tick ledger as the parent directory,
extended to every discovered T2f stall. Impossibility checks encode
the T2f block prediction (COMPETITION_PLAN): no retreat on believed
s∈[-0.9,-0.4] and none on evidence
older than 0.3s.

## Block summary

- Flights discovered: **1** (stalls=1, passes=0)
- Stall approaches ledgered: **1**
- Impossible withdrawals (any): **0** (s-band=0, stale=0)
- Verdict: **PREDICTION HELD** — no withdrawal in the forbidden band or on stale>0.3s evidence.

## Per-flight geom patches

| Fixture | gates | geom_term_z_m | geom_term_fresh_s | looks_like_t2f |
| --- | ---: | ---: | ---: | --- |
| `t2f-B-run1` | 0 | -0.9 | 0.3 | True |

## Stall classifications

| Fixture / approach | Class | s_ahead | ρ | impossible wd |
| --- | --- | ---: | ---: | ---: |
| `t2f-B-run1` / 1 | **INCONCLUSIVE (needs UNLOGGED exit/predicate)** | 0.324 | 1.5815344349415676 | 0 |

## Withdrawal events (all approaches)

- `t2f-B-run1` a1 t=+0.440s commit→recover s=2.981475280652389 age=0.0753686 → **ok**

## Artifacts

- `ledger_*.csv` / `paired_traces_*.csv` — per stall/pass approach
- `summary.json` — machine-readable audit
- `run_t2f_extension.py` — this runner (also scans sibling eni_dcim/fixtures)

