# Phase 6h AMENDED — first-enable protocol (PARTIAL / RESCUE)

- **Date:** 2026-07-19 19:49:57 +0300
- **Operator role:** SIM OPERATOR (Sakana)
- **HEAD flown:** `6b1b3e3ffc2ae18440ca8bac7c7dbe1c1d3c55a2` (`6b1b3e3 First-enable predicate complete: visual v_z provenance, readiness gate, 0.30 admission corridor, legacy-consistent adapter`); `6b1b3e3` ancestor verified OK.
- **IMPORTANT STATUS:** Protocol was **not completed**. F1 control flights were flown repeatedly due a packaging/slice verification bug: the flight logs had hundreds of frames, but the PowerShell wrapper misread the slicer return as `unique=0`. The loop never advanced to F2/F3 live arms before the tool timeout. No additional flights were run after cleanup; this fixture rescues the local control-only data.
- **Root cause of tooling failure:** PowerShell return/unwrapping around the analyzer/slicer, not missing video. Manual corrected slices below decode >300 unique frames.

## Selected rescued flights
| Selected | Attempt/role | Log ID | Why | Gates | Clips | Env hits | Result | Closest fix + px | age @ closest | Phase sequence | Slice frames |
|---:|---|---|---|---:|---:|---:|---|---|---|---|---:|
| 1 | control try1 | `20260719T154704-f170ead6` | first protocol flight (control) | 0 | 0 | 1 | environment collision (impulse=19.8) | 4.06m @ t+4.99s, center [284.0, 335.8] | 0.011s (state range 4.00m) | hover -> takeoff -> approach -> commit -> retreat -> search | 673 |
| 2 | control try15 | `20260719T160537-f170ead6` | first local gate-pass control run during accidental retry loop | 1 | 0 | 3 | environment collision (impulse=5.2) | 0.69m @ t+3.43s, center [302.4, 527.3] | 0.041s (state range 0.64m) | hover -> takeoff -> commit -> approach -> align -> approach -> align -> commit -> retreat -> recover -> hover | 301 |
| 3 | control try39 | `20260719T163649-f170ead6` | second local gate-pass control run during accidental retry loop | 1 | 2 | 1 | environment collision (impulse=2.4) | 0.86m @ t+3.94s, center [321.0, 35.5] | 0.325s (state range 0.28m) | hover -> takeoff -> commit -> recover -> commit -> retreat -> search -> approach -> align -> approach -> align -> commit -> retreat | 417 |

## Full accidental control-loop inventory

See `summary.json` for all attempts. Notable: control-only runs include local gate passes at `20260719T160537-f170ead6` and `20260719T163649-f170ead6`; no live terminal-enable arm was flown.

## Required protocol answer

Not answered. Because the loop never advanced to F2 live, this fixture cannot assess wrong-sign TERM, owner chatter, or terminal-enable pass/fail. It only rescues control-arm evidence from the failed run.