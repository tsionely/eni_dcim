# Phase 6k Cohort 2 Redo

- HEAD flown: `46e9a644ef4e24a5229a74a49b0ba33b73c1bb80`; `46e9a64` ancestor verified OK.
- Six alternating verified R2 flights at 1.8 m/s; terminal.enable only arm difference.

| F | Arm | Gates | Abort | Closest + px | Phases | recover/search behavior | blind-reverse collisions |
|---:|---|---:|---|---|---|---|---:|
| 1 | control | 1 | environment collision (impulse=11.1) | 1.26m [320.2,185.5] | hover -> takeoff -> commit -> search -> approach -> commit -> recover -> commit -> recover -> approach -> search | recover present | 0 |
| 2 | live | 0 | environment collision (impulse=12.7) | 1.18m [342.2,376.6] | hover -> takeoff -> align -> commit -> recover -> approach -> search -> approach -> search -> approach -> search | recover present and later search | 0 |
| 3 | control | 0 | environment collision (impulse=1.4) | 4.25m [301.0,316.5] | hover -> takeoff -> align -> commit -> recover -> approach -> search | recover present and later search | 0 |
| 4 | live | 0 | environment collision (impulse=8.2) | 4.27m [253.6,373.3] | hover -> takeoff -> align -> commit -> recover -> approach -> search -> recover | recover present and later search | 0 |
| 5 | control | 0 | environment collision (impulse=7.0) | 1.39m [372.0,92.5] | hover -> takeoff -> align -> commit -> recover -> search -> align -> commit -> recover -> commit -> recover -> approach -> search -> approach -> search -> hover | recover present and later search | 0 |
| 6 | live | 0 | environment collision (impulse=2.1) | 5.05m [295.5,331.0] | hover -> takeoff -> align -> commit -> recover -> approach -> search -> approach -> search -> approach -> align -> commit -> recover -> approach -> search -> hover | recover present and later search | 0 |

## Pre-registered expectation
Total blind-reverse collisions: **0**. Recover-before-search behavior occurred in **5/6** flights. The zero blind-reverse-collision expectation was met.

## Pass / inter-gate
- F1 control passed gate 1, then died: environment collision (impulse=11.1) (env_hits=1).