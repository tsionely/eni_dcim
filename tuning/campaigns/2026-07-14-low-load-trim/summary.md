# Low-Load Hover/Velocity-Trim Mock Campaign - 2026-07-14

Role: QA & MOCK-TUNER.

Commit: `2cc8df981f2a804ed8893ad3d1ca3ab5d13e87f9`
Checkout: `C:\Users\tsion\Projects\eni_dcim_qa` (outside OneDrive).
All commands used `--sim mock --low-load`; the real simulator was not launched, reset, clicked, or commanded.

Priority trim bounds: `control.att_rate.vel_i (0.02-0.3)`, `control.att_rate.vz_i (0.1-0.8)`, `estimation.vision_vel_blend (0.1-0.6)`, `estimation.vel_leak (0.02-0.15)`.

Sakana next patch starting point:

```powershell
--patch control.att_rate.vel_i=0.16282943078713075 --patch control.att_rate.vz_i=0.7381184156532321 --patch estimation.vision_vel_blend=0.32977692042316653 --patch estimation.vel_leak=0.09511782342063133
```

## CEM low-load hover/velocity-trim bounds - `trim-camp-20260714T140605`

- Flights: 40
- Best score: -220.471900
- Worst score: -240.764000
- Gates passed: min 0, max 0, total 0
- Aborted: 40/40
- Finished: 0/40
- Gate clips: 0 total
- Environment hits: 41 total

Score progression by 10-flight window:
- 01-10: avg -222.592, best -220.503, worst -240.764
- 11-20: avg -220.545, best -220.480, worst -220.611
- 21-30: avg -220.537, best -220.472, worst -220.641
- 31-40: avg -220.548, best -220.472, worst -220.672

Best tuned parameters:

```json
{
  "control.att_rate.vel_i": 0.16282943078713075,
  "control.att_rate.vz_i": 0.7381184156532321,
  "estimation.vel_leak": 0.09511782342063133,
  "estimation.vision_vel_blend": 0.32977692042316653
}
```

## Overall Finding

Across 40 flights: total gates `0`, aborted `40/40`.
Best overall run: `trim-camp-20260714T140605` score `-220.471900`.
