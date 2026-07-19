# THE TWO PASSES — phase6h first counted passes

Fixture: `20260719T164956-phase6h-first-enable` (sibling `eni_dcim` checkout).
HEAD flown: `6b1b3e3` (first-enable predicate). Protocol was PARTIAL — control-arm only; live TERM enable arm never flew. This report is the record of the campaign's **first counted gate passes** plus the advisory's deterministic readiness backfill.

Timebases: **t_ff** = seconds since race GO; **t_rel** = seconds since log start (user windows ≈ t_rel).

## 3. Denominator — honest pass rate

- Real full-control flights in retry loop: **47** (all_attempts=47)
- Counted passes: **2** `['20260719T160537-f170ead6', '20260719T163649-f170ead6']`
- **Honest pass rate: 2/47 = 4.3%** ← campaign's new baseline number
- Tooling false-REJECT `unique=0` count: 47 (SLICE JSON still reported 300+ unique frames)

All all_attempts entries are REAL flown control-arm flights. The PowerShell slicer bug falsely REJECTED them as unique=0 despite SLICE JSON reporting 300+ unique frames. Denominator for the campaign baseline is the real flight count, not the tooling-accepted count.

Abort-reason rollup:
```json
{
  "environment collision": 44,
  "gate clip budget exceeded": 3
}
```

## F_CLEAN — try15 clean pass (`20260719T160537-f170ead6`)

_gates=1 clips=0; death env impulse=5.2_

### Crossing reconstruction

- Pass time: **t_ff=3.757** / t_rel=7.926 (source=hud_active_gate_index)
- HUD: `[{'t_ff': 3.7571, 't_rel': 7.9255291, 'active_gate_index': 1, 'gates_passed': None}]`
- State tz sign-flips: `[{"t_ff": 3.7160454, "t_rel": 7.8844745, "t_vec": [-0.014538320595417585, 0.026035321304598846, -0.02371276907096503], "age": 0.303939688, "center_px": [241.96493579581846, 173.9880203064816], "sign": "+0.027->-0.024"}, {"t_ff": 3.7761587, "t_rel": 7.9445878, "t_vec": [4.517305051380245, -2.7764156030689007, 5.153085202324654], "age": 0.0, "center_px": [568.0, 182.0], "sign": "-0.098->+5.153"}, {"t_ff": 7.7759398, "t_rel": 11.9443689, "t_vec": [-0.12986372874449936, -0.014110909172468718, -0.03885736636276789], "age": 1.334025896, "center_px": [-397.6640722773175, 19.240567413164598], "sign": "+0.010->-0.039"}]`

**Pixel-truth / state at pass:**

- best live det: t_ff=3.426 R=0.687 t_vec=[-0.025213181645361217, -0.24347347302593217, 0.6422417217703194] e_up=-0.008285874108699395 lat=-0.025213181645361217 cert=none center=[302.4015374076242, 527.3483070318533]
- state: t_ff=3.756 t_vec=[-0.01639064000805472, 0.05995017393840431, -0.09771218595941171] age=0.338608688 e_up=-0.014587722613576791 lat=-0.01639064000805472 center=[241.96493579581846, 173.9880203064816]
- e_up samples near plane (R<1.5 + state): min=-0.015 med=-0.002 max=+0.071  (live-det claim −0.09..+0.01 / centered: CONFIRMED)

Sample table (live dets near pass):

| t_ff | R | t_vec | e_up | lat | cert | center |
|---:|---:|---|---:|---:|---|---|
| 3.367 | 0.82 | `[0.164, -0.361, 0.721]` | +0.071 | +0.164 | none | `[404.90381940160665, 371.3510309093175]` |
| 3.394 | 0.70 | `[0.023, -0.252, 0.648]` | +0.004 | +0.023 | none | `[335.38793272086434, 512.5402815020134]` |
| 3.426 | 0.69 | `[-0.025, -0.243, 0.642]` | -0.008 | -0.025 | none | `[302.4015374076242, 527.3483070318533]` |
| 3.442 | 1.78 | `[1.067, -0.693, 1.246]` | +0.079 | +1.067 | none | `[532.4999389648438, 179.49996948242188]` |
| 3.505 | 1.72 | `[0.979, -0.717, 1.216]` | +0.111 | +0.979 | certified | `[532.25, 179.5]` |

### Deterministic readiness backfill

_Live SHADOW owner=term uses certified-det without the readiness/admission predicate — do NOT read it as READY._

- Live SHADOW owner hist: `{'alt': 2, 'term': 291}`
- commit ticks observed: 293
- ever READY: **True** (onset t_ff=1.8160605)
- ever CAPTURED (ready∧admit∧range≤2.5m): **False** (t_ff=None)
- max unique oracle hist: 40
- ready ticks: 66

**At crossing:** `{"t_ff": 3.7559282, "ready": false, "owner": "alt", "e_meas": null, "vz_cmd_if_term": null, "vz_vis": -0.0, "admit_ok": null, "would_capture": false, "n_hist": 40, "verdict": "IDLED \u2014 oracle never READY (no actuation even with enable)"}`

**TERM verdict: IDLED — oracle never READY (no actuation even with enable)**

### Post-pass autopsy → death

- Death: t_ff=9.9958999 t_rel=14.164329 impulse=5.220639705657959 (user window t_rel≈7.93→14.164329)
- Phases after pass: `[{'t_ff': 3.776169, 'phase': 'approach'}, {'t_ff': 4.0569354, 'phase': 'align'}, {'t_ff': 4.1160296, 'phase': 'approach'}, {'t_ff': 4.1565578, 'phase': 'align'}, {'t_ff': 6.1562121, 'phase': 'commit'}, {'t_ff': 9.7559976, 'phase': 'retreat'}, {'t_ff': 9.7759949, 'phase': 'recover'}, {'t_ff': 9.996151, 'phase': 'hover'}]`
- Chase verdict: **Died with gate_rel=null (lock cleared) — blind into environment**
- Exit vector (first 2s, R>3m): `{"n": 58, "t_med": [0.9009973825550746, -2.555657180620023, 5.049912430426945], "R_med": 5.978354373418433, "azimuth_atan2_tx_tz_deg": 10.116175439584447, "elevation_atan2_ty_tz_deg": 26.843036944293956, "note": "seeds Advisory-6 S4.1 exit-vector banking"}`
- Death state: `{'t_ff': 9.9961463, 'age': None, 't_vec': None, 'R': None, 'center_px': None}`
- Det bands: `{"near_<3": {"n": 0}, "mid_3_10": {"n": 78, "R_med": 5.666329644291214, "tx_med": 1.0491085927284323, "ty_med": -2.198058551140596, "labels": {"RIGHT": 5, "BOTTOM_bar_vehicle_LOW": 44, "TOP_bar_vehicle_HIGH": 20, "LEFT": 6, "FAR": 3}, "cert": {"certified": 59, "probation": 10, "none": 9}}, "far_10_25": {"n": 15, "R_med": 11.777926006445945, "tx_med": -0.11892914726895575, "ty_med": -1.6026045416185772, "labels": {"FAR": 15}, "cert": {"certified": 15}}, "vfar_>25": {"n": 1, "R_med": 34.01280023877142, "tx_med": 14.860954344479836, "ty_med": -0.6044231565192157, "labels": {"FAR": 1}, "cert": {"certified": 1}}}`

## F_CLIP — try39 pass with 2 clips (`20260719T163649-f170ead6`)

_gates=1 clips=2; death env impulse=2.4_

### Crossing reconstruction

- Pass time: **t_ff=4.258** / t_rel=8.589 (source=hud_active_gate_index)
- HUD: `[{'t_ff': 4.2576177, 't_rel': 8.5893861, 'active_gate_index': 1, 'gates_passed': None}]`
- State tz sign-flips: `[{"t_ff": 7.532007, "t_rel": 11.8637754, "t_vec": [-0.036989103772044424, 0.0009539824287010208, -0.03528117951445496], "age": 0.5708724, "center_px": [201.25, 274.25], "sign": "+0.012->-0.035"}]`

**Pixel-truth / state at pass:**

- best live det: t_ff=3.938 R=0.856 t_vec=[0.10909602801388402, -0.6316110131938155, 0.5675848238719153] e_up=0.3685049479949406 lat=0.10909602801388402 cert=certified center=[321.0, 35.5]
- state: t_ff=4.252 t_vec=[3.160487729024946, -6.391502621363828, 3.9058401646798737] age=0.015123144 e_up=0.09063902438271221 lat=3.160487729024946 center=[578.9343215919524, -343.6468346379603]
- e_up samples near plane (R<1.5 + state): min=-0.082 med=+0.011 max=+0.369  (live-det claim −0.09..+0.01 / centered: CONFIRMED)

Sample table (live dets near pass):

| t_ff | R | t_vec | e_up | lat | cert | center |
|---:|---:|---|---:|---:|---|---|
| 3.510 | 1.40 | `[0.036, -0.385, 1.345]` | -0.082 | +0.036 | certified | `[329.28011252636, 311.5070907034559]` |
| 3.621 | 1.07 | `[0.052, -0.323, 1.024]` | -0.069 | +0.052 | certified | `[338.3129837565195, 346.1041160581205]` |
| 3.938 | 0.86 | `[0.109, -0.632, 0.568]` | +0.369 | +0.109 | certified | `[321.0, 35.5]` |

### try39 clip attribution

- t_ff=4.035 (t_rel=8.367) impulse=0.7900810241699219 threat=1 → **FAR** `{'FAR': 5, 'BOTTOM_bar_vehicle_LOW': 1}`
- t_ff=4.042 (t_rel=8.374) impulse=0.6365295052528381 threat=1 → **FAR** `{'FAR': 4, 'BOTTOM_bar_vehicle_LOW': 1, 'RIGHT': 1}`

### Deterministic readiness backfill

_Live SHADOW owner=term uses certified-det without the readiness/admission predicate — do NOT read it as READY._

- Live SHADOW owner hist: `{'alt': 2, 'term': 331}`
- commit ticks observed: 333
- ever READY: **True** (onset t_ff=1.6925552)
- ever CAPTURED (ready∧admit∧range≤2.5m): **False** (t_ff=None)
- max unique oracle hist: 40
- ready ticks: 168

**At crossing:** `{"t_ff": 4.032039, "ready": false, "owner": "alt", "e_meas": null, "vz_cmd_if_term": null, "vz_vis": -0.0, "admit_ok": null, "would_capture": false, "n_hist": 40, "verdict": "IDLED \u2014 oracle never READY (no actuation even with enable)"}`

**TERM verdict: IDLED — oracle never READY (no actuation even with enable)**

### Post-pass autopsy → death

- Death: t_ff=13.8743804 t_rel=18.2061488 impulse=2.395251989364624 (user window t_rel≈8.59→18.2061488)
- Phases after pass: `[{'t_ff': 4.2719659, 'phase': 'recover'}, {'t_ff': 4.8522972, 'phase': 'commit'}, {'t_ff': 7.6920484, 'phase': 'retreat'}, {'t_ff': 9.6919761, 'phase': 'search'}, {'t_ff': 10.0320934, 'phase': 'approach'}, {'t_ff': 10.0991465, 'phase': 'align'}, {'t_ff': 10.3127759, 'phase': 'approach'}, {'t_ff': 10.5122202, 'phase': 'align'}, {'t_ff': 11.0923004, 'phase': 'commit'}, {'t_ff': 12.372056, 'phase': 'retreat'}]`
- Chase verdict: **Died locked on FAR target R≈7.9m (age=1.426841208) — classic post-pass far-gate chase**
- Exit vector (first 2s, R>3m): `{"n": 56, "t_med": [1.4486280258443536, -1.5832385693080284, 6.247473997215588], "R_med": 7.006224279101566, "azimuth_atan2_tx_tz_deg": 13.054711142528449, "elevation_atan2_ty_tz_deg": 14.220551509292894, "note": "seeds Advisory-6 S4.1 exit-vector banking"}`
- Death state: `{'t_ff': 13.8720183, 'age': 1.426841208, 't_vec': [0.5093795647413314, -0.42620118329779505, 7.833702052080662], 'R': 7.861806588208164, 'center_px': [339.0, 84.0]}`
- Det bands: `{"near_<3": {"n": 2, "R_med": 1.7603821195028835, "tx_med": -0.09336414691983108, "ty_med": -0.39320702845565936, "labels": {"TOP_bar_vehicle_HIGH": 2}, "cert": {"probation": 1, "none": 1}}, "mid_3_10": {"n": 112, "R_med": 7.24020822419098, "tx_med": 1.4079855932099463, "ty_med": -2.573760333389729, "labels": {"BOTTOM_bar_vehicle_LOW": 34, "RIGHT": 28, "TOP_bar_vehicle_HIGH": 18, "FAR": 27, "LEFT": 5}, "cert": {"certified": 93, "none": 13, "probation": 6}}, "far_10_25": {"n": 81, "R_med": 12.31471665694265, "tx_med": 0.7652426219360163, "ty_med": -4.083880674203165, "labels": {"FAR": 81}, "cert": {"certified": 81}}, "vfar_>25": {"n": 0}}`

## Synthesis — did TERM help, hurt, or idle?

- **F_CLEAN**: IDLED — oracle never READY (no actuation even with enable)
- **F_CLIP**: IDLED — oracle never READY (no actuation even with enable)

Live shadow `owner=term` counts are **not** readiness evidence (shadow path omits the oracle READY + admission corridor). The backfill is the enable-gate answer.

## Exit-vector banking seed (Advisory-6 S4.1)

Both deaths occur AFTER a counted pass while the planner re-acquires. The early post-pass detection median (R>3m) is the exit-vector observation the banking spec should hold: azimuth/elevation of the next lock relative to the just-passed gate, plus a distance-sanity reject for far-gate steal (already partially in relock code).

- F_CLEAN: `{'n': 58, 't_med': [0.9009973825550746, -2.555657180620023, 5.049912430426945], 'R_med': 5.978354373418433, 'azimuth_atan2_tx_tz_deg': 10.116175439584447, 'elevation_atan2_ty_tz_deg': 26.843036944293956, 'note': 'seeds Advisory-6 S4.1 exit-vector banking'}`
- F_CLIP: `{'n': 56, 't_med': [1.4486280258443536, -1.5832385693080284, 6.247473997215588], 'R_med': 7.006224279101566, 'azimuth_atan2_tx_tz_deg': 13.054711142528449, 'elevation_atan2_ty_tz_deg': 14.220551509292894, 'note': 'seeds Advisory-6 S4.1 exit-vector banking'}`

## Deliverables

- `first-passes.md` (this file)
- `summary.json`, per-flight `*_readiness.csv`, `denominator.csv`

