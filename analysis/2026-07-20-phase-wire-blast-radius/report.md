# Phase-wire blast radius — tau-at-TERM retro audit

RESPONSE34 §3: before the fix, `terminal_override` passed constant `position` to the arbiter;
no-return latch never engaged; first-capture-in-damping existed only in unit tests.
Corrected wire: `guidance_phase(tau_s, ...)` with `position_until_s=0.45`.

## RETRO_VERDICT: **NO_CHANGE**

No first-capture at tau<=0.45 in archive; handbacks at low tau do not imply recorded verdict change without refused captures.

## Data mined
- Flight logs scanned: **1248**
- Shadow CSVs with `shadow_owner`: **16**
- TERM-owned rows — live: **604**, replay: **95**, total: **699**

## Tau while TERM owned (seconds)
- All rows with tau: **679**
- min: **0.027606491409039466**
- p5: **0.28443937580295364**
- p25: **0.8511294943503335**
- p50: **1.132477928886628**
- p75: **1.3457594215138342**
- p90: **1.564363978871805**
- p95: **1.6987554077004874**
- max: **3.940316842786559**
- mean: **1.1078477645679456**

## Episodes (gap >0.5s or new flight splits)
- Episodes: **19**
- Episodes with any tick tau ≤ 0.45: **4**
- First-capture (episode start) tau ≤ 0.45: **0**

## Handbacks (live term_status TERM→ALT)
- Total handbacks: **13**
- Handbacks at tau ≤ 0.45: **0**

## Deliverables
- `term_owned_ticks.csv`
- `term_episodes.csv`
- `summary.json`
