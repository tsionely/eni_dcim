# Final-meter ledger — 2026-07-24

## Provenance and scope

Implements the user-requested +1.0 m-aligned control-tick ledger and
the extractables from channel-2 `ADVISORY_36.md` §4 (Downloads). The
literal memo titled **“RACE-RISK ADVISORY 1”** with the A–D stall labels
was not present on disk; A–D are applied from the analyst task wording,
with ADVISORY_36 as the extraction parent.

Method (corrected after first-pass frame bugs):
- **Signed plane** = camera-forward depth `gate_rel.t[2]` (planner
  convention). `signed_plane_dot_n` is logged as a secondary column.
- **Along-plane cmd/est** = body-x (controller forward) — not a camera
  normal dotted into body velocity.
- Ledger **continues through retreat/recover** until geometric behind
  (`s < -0.5`), race pass, collision, or 4 s post-alignment.
- Sampling: setpoint ticks, state/detection fill ≤40 ms.

## Verdicts

| Fixture / approach | Class | Deciding values |
| --- | --- | --- |
| `stall_t2r1_B_run2` / 1 | **INCONCLUSIVE (needs UNLOGGED exit/predicate)** | s_ahead_min=0.486 m; s_signed_min=0.48642551440903925; ρ=1.3608512624336826 (n=14); cmd@closest=1.5443155920867573; withdraw=False; pass_counter=False; crossed=False. final phase=recover, withdraw=False, rho=1.3608512624336826, closest_ahead=0.486 m, s_min_signed=0.48642551440903925. |
| `pass_r1k_off_run3` / 1 | **D scoring-order** | s_ahead_min=0.247 m; s_signed_min=0.24683438404436975; ρ=1.5894295921417314 (n=1); cmd@closest=-1.2; withdraw=True; pass_counter=True; crossed=False. gate index incremented while estimated plane stayed positive (last_s_before=0.24683438404436975, s_min_signed=0.24683438404436975). If result.json gates_passed>0 this is a scored pass with estimator still in front — scoring/estimate order, not a stall. |
| `pass_r1k_off_run3` / 2 | **POST_PASS_OR_PHANTOM_CROSS** | s_ahead_min=0.027 m; s_signed_min=-0.5061385850895675; ρ=1.5679484484391113 (n=1); cmd@closest=-1.2; withdraw=True; pass_counter=False; crossed=True. plane went non-positive (s_min_signed=-0.506 m) without a race-counter event in-window — post-pass DR or phantom cross. |
| `pass_r1k_off_run3` / 3 | **POST_PASS_OR_PHANTOM_CROSS** | s_ahead_min=0.013 m; s_signed_min=-0.5401143031371063; ρ=7.139224180554812 (n=12); cmd@closest=0.0; withdraw=True; pass_counter=False; crossed=True. plane went non-positive (s_min_signed=-0.540 m) without a race-counter event in-window — post-pass DR or phantom cross. |
| `stall_r1j3390_val_run2` / 1 | **A command-withdrawal** | s_ahead_min=0.018 m; s_signed_min=-0.3147675852076194; ρ=1.426517269942629 (n=6); cmd@closest=0.0; withdraw=True; pass_counter=False; crossed=True. phantom/estimate cross (s_min_signed=-0.315 m) then command/phase withdrawal without race score; rho=1.426517269942629. |

## Discriminating observations

- **stall_t2r1_B_run2 a1** → INCONCLUSIVE (needs UNLOGGED exit/predicate): closest_ahead=0.486 m / true_dz=0.4689446562489606; ρ_mean=1.3608512624336826; Δs(last 0.5s)=None.
- **pass_r1k_off_run3 a1** → D scoring-order: closest_ahead=0.247 m / true_dz=0.11957400948063639; ρ_mean=1.5894295921417314; Δs(last 0.5s)=14.613281228482984.
- **pass_r1k_off_run3 a2** → POST_PASS_OR_PHANTOM_CROSS: closest_ahead=0.027 m / true_dz=0.1276226605433009; ρ_mean=1.5679484484391113; Δs(last 0.5s)=-0.7558771733395774.
- **pass_r1k_off_run3 a3** → POST_PASS_OR_PHANTOM_CROSS: closest_ahead=0.013 m / true_dz=0.042295852828002856; ρ_mean=7.139224180554812; Δs(last 0.5s)=-1.5379712482474148.
- **stall_r1j3390_val_run2 a1** → A command-withdrawal: closest_ahead=0.018 m / true_dz=0.17073388793259114; ρ_mean=1.426517269942629; Δs(last 0.5s)=None.

## UNLOGGED instrumentation backlog

1. commit_predicate_vector (per-conjunct booleans and sustain counter)
2. speed_cap_mps and binding-rule source
3. planner exit_cause enum (EXPIRED/DETECTION_LOST/CORRIDOR/MIN_DIST/etc.)
4. logged approach-axis / gate-plane orientation convention
5. logged opening dimensions and aim-up target

Literal `UNLOGGED` cells are retained in the CSV ledgers.

## Artifacts

- `ledger_*.csv` — §4 identity/geometry/command/exit tick tables
- `paired_traces_*.csv` — §5 cmd vs est along/lat/vert
- `summary.json` — metrics + classifications
- `run_final_meter_ledger.py` — reproducible extractor
