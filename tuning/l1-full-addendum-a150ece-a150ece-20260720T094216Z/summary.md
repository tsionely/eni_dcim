# L1 Shadow Capture Addendum

Role: QA & MOCK-TUNER.
Scope: recorded video replay only; no real simulator was launched, reset, clicked, or commanded.
Source commit under test: `a150ece6b6ef41c48d3f573c35d25ee2b72f0b32`.
Repo HEAD while running: `a150ece6b6ef41c48d3f573c35d25ee2b72f0b32`.
Non-tuning delta from `a150ece`: `[]`.
Runtime patches: `[]`.

## Inputs

- `primary_f2_f4` `F2` `20260720T071112-cd18c5fb`: 141 frames, detector fixes 125, tracker fixes 13, feature rows 108, feature_side rows 18.
- `primary_f2_f4` `F4` `20260720T071333-cd18c5fb`: 120 frames, detector fixes 115, tracker fixes 2, feature rows 70, feature_side rows 12.
- `sweep29` `20260719T154704-f170ead6` `20260719T154704-f170ead6`: 673 frames, detector fixes 90, tracker fixes 0, feature rows 79, feature_side rows 0.
- `sweep29` `20260719T160537-f170ead6` `20260719T160537-f170ead6`: 301 frames, detector fixes 175, tracker fixes 12, feature rows 163, feature_side rows 29.
- `sweep29` `20260719T163649-f170ead6` `20260719T163649-f170ead6`: 417 frames, detector fixes 304, tracker fixes 6, feature rows 243, feature_side rows 25.
- `sweep29` `20260719T173050-f170ead6` `20260719T173050-f170ead6`: 345 frames, detector fixes 127, tracker fixes 8, feature rows 102, feature_side rows 11.
- `sweep29` `20260719T173427-50f9dcc8` `20260719T173427-50f9dcc8`: 402 frames, detector fixes 267, tracker fixes 26, feature rows 162, feature_side rows 0.
- `sweep29` `20260719T200816-f170ead6` `20260719T200816-f170ead6`: 360 frames, detector fixes 196, tracker fixes 24, feature rows 114, feature_side rows 22.
- `sweep29` `20260719T201038-50f9dcc8` `20260719T201038-50f9dcc8`: 7435 frames, detector fixes 45, tracker fixes 0, feature rows 44, feature_side rows 0.
- `sweep29` `20260719T201630-f170ead6` `20260719T201630-f170ead6`: 610 frames, detector fixes 307, tracker fixes 31, feature rows 211, feature_side rows 0.
- `sweep29` `20260719T201851-50f9dcc8` `20260719T201851-50f9dcc8`: 523 frames, detector fixes 320, tracker fixes 28, feature rows 257, feature_side rows 34.
- `sweep29` `20260719T202445-f170ead6` `20260719T202445-f170ead6`: 559 frames, detector fixes 144, tracker fixes 3, feature rows 88, feature_side rows 2.
- `sweep29` `20260719T202720-50f9dcc8` `20260719T202720-50f9dcc8`: 389 frames, detector fixes 196, tracker fixes 1, feature rows 150, feature_side rows 0.
- `sweep29` `20260720T053402-f170ead6` `20260720T053402-f170ead6`: 235 frames, detector fixes 123, tracker fixes 11, feature rows 66, feature_side rows 0.
- `sweep29` `20260720T053514-5cebc2b2` `20260720T053514-5cebc2b2`: 473 frames, detector fixes 198, tracker fixes 2, feature rows 124, feature_side rows 0.
- `sweep29` `20260720T053635-f170ead6` `20260720T053635-f170ead6`: 229 frames, detector fixes 109, tracker fixes 10, feature rows 85, feature_side rows 13.
- `sweep29` `20260720T053745-5cebc2b2` `20260720T053745-5cebc2b2`: 470 frames, detector fixes 265, tracker fixes 53, feature rows 125, feature_side rows 8.
- `sweep29` `20260720T053905-f170ead6` `20260720T053905-f170ead6`: 235 frames, detector fixes 128, tracker fixes 11, feature rows 74, feature_side rows 0.
- `sweep29` `20260720T054016-5cebc2b2` `20260720T054016-5cebc2b2`: 217 frames, detector fixes 123, tracker fixes 6, feature rows 125, feature_side rows 20.
- `sweep29` `20260720T062804-c38fd469` `20260720T062804-c38fd469`: 385 frames, detector fixes 180, tracker fixes 1, feature rows 160, feature_side rows 36.
- `sweep29` `20260720T062921-790186c4` `20260720T062921-790186c4`: 514 frames, detector fixes 131, tracker fixes 29, feature rows 113, feature_side rows 0.
- `sweep29` `20260720T063042-c38fd469` `20260720T063042-c38fd469`: 81 frames, detector fixes 54, tracker fixes 0, feature rows 32, feature_side rows 0.
- `sweep29` `20260720T063147-790186c4` `20260720T063147-790186c4`: 246 frames, detector fixes 69, tracker fixes 7, feature rows 46, feature_side rows 0.
- `sweep29` `20260720T063258-c38fd469` `20260720T063258-c38fd469`: 519 frames, detector fixes 162, tracker fixes 9, feature rows 60, feature_side rows 7.
- `sweep29` `20260720T063419-790186c4` `20260720T063419-790186c4`: 223 frames, detector fixes 85, tracker fixes 4, feature rows 40, feature_side rows 0.
- `sweep29` `20260720T071008-5b501b4c` `20260720T071008-5b501b4c`: 32 frames, detector fixes 30, tracker fixes 1, feature rows 23, feature_side rows 0.
- `sweep29` `20260720T071112-cd18c5fb` `20260720T071112-cd18c5fb`: 141 frames, detector fixes 125, tracker fixes 13, feature rows 108, feature_side rows 18.
- `sweep29` `20260720T071220-5b501b4c` `20260720T071220-5b501b4c`: 299 frames, detector fixes 91, tracker fixes 13, feature rows 49, feature_side rows 0.
- `sweep29` `20260720T071333-cd18c5fb` `20260720T071333-cd18c5fb`: 120 frames, detector fixes 115, tracker fixes 2, feature rows 70, feature_side rows 12.
- `sweep29` `20260720T071439-5b501b4c` `20260720T071439-5b501b4c`: 107 frames, detector fixes 60, tracker fixes 1, feature rows 34, feature_side rows 0.
- `sweep29` `20260720T071545-cd18c5fb` `20260720T071545-cd18c5fb`: 104 frames, detector fixes 103, tracker fixes 1, feature rows 94, feature_side rows 7.

## Shadow Capture Bar

| Sweep | Flight | Commit rows | Ready | Capture rows | Captures <=2.2m | First capture R | First source | TERM rows | TERM/SIDE rows | Min score | Sigma abort rows | Transitions | Held full->side |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|
| `baseline` | `20260719T154704-f170ead6` | 2 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `baseline` | `20260719T160537-f170ead6` | 83 | 76 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.624 | 0 | 0 | `False` |
| `baseline` | `20260719T163649-f170ead6` | 151 | 125 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `baseline` | `20260719T173050-f170ead6` | 41 | 23 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.651 | 0 | 0 | `False` |
| `baseline` | `20260719T173427-50f9dcc8` | 46 | 17 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `baseline` | `20260719T200816-f170ead6` | 56 | 41 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.621 | 0 | 0 | `False` |
| `baseline` | `20260719T201630-f170ead6` | 122 | 103 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `baseline` | `20260719T201851-50f9dcc8` | 128 | 90 | 6 | 6 | 1.268 | `FULL_QUAD` | 55 | 0 | 0.265 | 7 | 0 | `False` |
| `baseline` | `20260719T202445-f170ead6` | 20 | 7 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `baseline` | `20260719T202720-50f9dcc8` | 29 | 19 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.651 | 0 | 0 | `False` |
| `baseline` | `20260720T053402-f170ead6` | 21 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `baseline` | `20260720T053514-5cebc2b2` | 56 | 46 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `baseline` | `20260720T053635-f170ead6` | 47 | 40 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.650 | 0 | 0 | `False` |
| `baseline` | `20260720T053745-5cebc2b2` | 32 | 3 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.651 | 0 | 0 | `False` |
| `baseline` | `20260720T053905-f170ead6` | 33 | 13 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `baseline` | `20260720T054016-5cebc2b2` | 74 | 56 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `baseline` | `20260720T062804-c38fd469` | 112 | 92 | 11 | 11 | 1.317 | `FULL_QUAD` | 36 | 0 | 0.200 | 2 | 0 | `False` |
| `baseline` | `20260720T062921-790186c4` | 33 | 7 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.651 | 0 | 0 | `False` |
| `baseline` | `20260720T063258-c38fd469` | 3 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `baseline` | `20260720T063419-790186c4` | 2 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `baseline` | `20260720T071112-cd18c5fb` | 43 | 10 | 2 | 2 | 1.903 | `FULL_QUAD` | 27 | 0 | 0.221 | 2 | 0 | `False` |
| `baseline` | `20260720T071220-5b501b4c` | 1 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `baseline` | `20260720T071333-cd18c5fb` | 38 | 33 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.639 | 0 | 0 | `False` |
| `baseline` | `20260720T071545-cd18c5fb` | 18 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `baseline` | `F2` | 43 | 10 | 2 | 2 | 1.903 | `FULL_QUAD` | 27 | 0 | 0.221 | 2 | 0 | `False` |
| `baseline` | `F4` | 38 | 33 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.639 | 0 | 0 | `False` |
| `drop_all_0p16s_after_first_below_2m` | `20260719T154704-f170ead6` | 2 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_all_0p16s_after_first_below_2m` | `20260719T160537-f170ead6` | 83 | 76 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.624 | 0 | 0 | `False` |
| `drop_all_0p16s_after_first_below_2m` | `20260719T163649-f170ead6` | 151 | 119 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `drop_all_0p16s_after_first_below_2m` | `20260719T173050-f170ead6` | 41 | 32 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.651 | 0 | 0 | `False` |
| `drop_all_0p16s_after_first_below_2m` | `20260719T173427-50f9dcc8` | 46 | 17 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `drop_all_0p16s_after_first_below_2m` | `20260719T200816-f170ead6` | 56 | 41 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.621 | 0 | 0 | `False` |
| `drop_all_0p16s_after_first_below_2m` | `20260719T201630-f170ead6` | 122 | 103 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `drop_all_0p16s_after_first_below_2m` | `20260719T201851-50f9dcc8` | 128 | 80 | 7 | 7 | 1.129 | `FULL_QUAD` | 51 | 0 | 0.189 | 0 | 0 | `False` |
| `drop_all_0p16s_after_first_below_2m` | `20260719T202445-f170ead6` | 20 | 7 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `drop_all_0p16s_after_first_below_2m` | `20260719T202720-50f9dcc8` | 29 | 19 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.651 | 0 | 0 | `False` |
| `drop_all_0p16s_after_first_below_2m` | `20260720T053402-f170ead6` | 21 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_all_0p16s_after_first_below_2m` | `20260720T053514-5cebc2b2` | 56 | 46 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `drop_all_0p16s_after_first_below_2m` | `20260720T053635-f170ead6` | 47 | 40 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.650 | 0 | 0 | `False` |
| `drop_all_0p16s_after_first_below_2m` | `20260720T053745-5cebc2b2` | 32 | 5 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `drop_all_0p16s_after_first_below_2m` | `20260720T053905-f170ead6` | 33 | 13 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `drop_all_0p16s_after_first_below_2m` | `20260720T054016-5cebc2b2` | 74 | 56 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `drop_all_0p16s_after_first_below_2m` | `20260720T062804-c38fd469` | 112 | 82 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.330 | 7 | 0 | `False` |
| `drop_all_0p16s_after_first_below_2m` | `20260720T062921-790186c4` | 33 | 7 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.651 | 0 | 0 | `False` |
| `drop_all_0p16s_after_first_below_2m` | `20260720T063258-c38fd469` | 3 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_all_0p16s_after_first_below_2m` | `20260720T063419-790186c4` | 2 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_all_0p16s_after_first_below_2m` | `20260720T071112-cd18c5fb` | 43 | 7 | 3 | 3 | 1.064 | `FULL_QUAD` | 3 | 0 | 0.291 | 2 | 0 | `False` |
| `drop_all_0p16s_after_first_below_2m` | `20260720T071220-5b501b4c` | 1 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_all_0p16s_after_first_below_2m` | `20260720T071333-cd18c5fb` | 38 | 33 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.639 | 0 | 0 | `False` |
| `drop_all_0p16s_after_first_below_2m` | `20260720T071545-cd18c5fb` | 18 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_all_0p16s_after_first_below_2m` | `F2` | 43 | 7 | 3 | 3 | 1.064 | `FULL_QUAD` | 3 | 0 | 0.291 | 2 | 0 | `False` |
| `drop_all_0p16s_after_first_below_2m` | `F4` | 38 | 33 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.639 | 0 | 0 | `False` |
| `drop_all_0p30s_after_first_below_2m` | `20260719T154704-f170ead6` | 2 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_all_0p30s_after_first_below_2m` | `20260719T160537-f170ead6` | 83 | 76 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.624 | 0 | 0 | `False` |
| `drop_all_0p30s_after_first_below_2m` | `20260719T163649-f170ead6` | 151 | 125 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `drop_all_0p30s_after_first_below_2m` | `20260719T173050-f170ead6` | 41 | 32 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.651 | 0 | 0 | `False` |
| `drop_all_0p30s_after_first_below_2m` | `20260719T173427-50f9dcc8` | 46 | 17 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `drop_all_0p30s_after_first_below_2m` | `20260719T200816-f170ead6` | 56 | 41 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.621 | 0 | 0 | `False` |
| `drop_all_0p30s_after_first_below_2m` | `20260719T201630-f170ead6` | 122 | 93 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.651 | 0 | 0 | `False` |
| `drop_all_0p30s_after_first_below_2m` | `20260719T201851-50f9dcc8` | 128 | 83 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.649 | 0 | 0 | `False` |
| `drop_all_0p30s_after_first_below_2m` | `20260719T202445-f170ead6` | 20 | 5 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `drop_all_0p30s_after_first_below_2m` | `20260719T202720-50f9dcc8` | 29 | 19 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.651 | 0 | 0 | `False` |
| `drop_all_0p30s_after_first_below_2m` | `20260720T053402-f170ead6` | 21 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_all_0p30s_after_first_below_2m` | `20260720T053514-5cebc2b2` | 56 | 46 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `drop_all_0p30s_after_first_below_2m` | `20260720T053635-f170ead6` | 47 | 40 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.650 | 0 | 0 | `False` |
| `drop_all_0p30s_after_first_below_2m` | `20260720T053745-5cebc2b2` | 32 | 5 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `drop_all_0p30s_after_first_below_2m` | `20260720T053905-f170ead6` | 33 | 13 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `drop_all_0p30s_after_first_below_2m` | `20260720T054016-5cebc2b2` | 74 | 56 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `drop_all_0p30s_after_first_below_2m` | `20260720T062804-c38fd469` | 112 | 85 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `drop_all_0p30s_after_first_below_2m` | `20260720T062921-790186c4` | 33 | 7 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.651 | 0 | 0 | `False` |
| `drop_all_0p30s_after_first_below_2m` | `20260720T063258-c38fd469` | 3 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_all_0p30s_after_first_below_2m` | `20260720T063419-790186c4` | 2 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_all_0p30s_after_first_below_2m` | `20260720T071112-cd18c5fb` | 43 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_all_0p30s_after_first_below_2m` | `20260720T071220-5b501b4c` | 1 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_all_0p30s_after_first_below_2m` | `20260720T071333-cd18c5fb` | 38 | 33 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.639 | 0 | 0 | `False` |
| `drop_all_0p30s_after_first_below_2m` | `20260720T071545-cd18c5fb` | 18 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_all_0p30s_after_first_below_2m` | `F2` | 43 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_all_0p30s_after_first_below_2m` | `F4` | 38 | 33 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.639 | 0 | 0 | `False` |
| `drop_full_below_1p5m` | `20260719T154704-f170ead6` | 2 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_full_below_1p5m` | `20260719T160537-f170ead6` | 83 | 76 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.624 | 0 | 0 | `False` |
| `drop_full_below_1p5m` | `20260719T163649-f170ead6` | 151 | 129 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.607 | 0 | 0 | `False` |
| `drop_full_below_1p5m` | `20260719T173050-f170ead6` | 41 | 23 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.651 | 0 | 0 | `False` |
| `drop_full_below_1p5m` | `20260719T173427-50f9dcc8` | 46 | 34 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `drop_full_below_1p5m` | `20260719T200816-f170ead6` | 56 | 44 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `drop_full_below_1p5m` | `20260719T201630-f170ead6` | 122 | 93 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.651 | 0 | 0 | `False` |
| `drop_full_below_1p5m` | `20260719T201851-50f9dcc8` | 128 | 92 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.349 | 8 | 2 | `False` |
| `drop_full_below_1p5m` | `20260719T202445-f170ead6` | 20 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_full_below_1p5m` | `20260719T202720-50f9dcc8` | 29 | 19 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.651 | 0 | 0 | `False` |
| `drop_full_below_1p5m` | `20260720T053402-f170ead6` | 21 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_full_below_1p5m` | `20260720T053514-5cebc2b2` | 56 | 46 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `drop_full_below_1p5m` | `20260720T053635-f170ead6` | 47 | 40 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.650 | 0 | 0 | `False` |
| `drop_full_below_1p5m` | `20260720T053745-5cebc2b2` | 32 | 5 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `drop_full_below_1p5m` | `20260720T053905-f170ead6` | 33 | 13 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `drop_full_below_1p5m` | `20260720T054016-5cebc2b2` | 74 | 61 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `drop_full_below_1p5m` | `20260720T062804-c38fd469` | 112 | 99 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.413 | 8 | 2 | `False` |
| `drop_full_below_1p5m` | `20260720T062921-790186c4` | 33 | 7 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.651 | 0 | 0 | `False` |
| `drop_full_below_1p5m` | `20260720T063258-c38fd469` | 3 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_full_below_1p5m` | `20260720T063419-790186c4` | 2 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_full_below_1p5m` | `20260720T071112-cd18c5fb` | 43 | 27 | 2 | 2 | 1.903 | `FULL_QUAD` | 27 | 0 | 0.221 | 2 | 0 | `False` |
| `drop_full_below_1p5m` | `20260720T071220-5b501b4c` | 1 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_full_below_1p5m` | `20260720T071333-cd18c5fb` | 38 | 33 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.639 | 0 | 0 | `False` |
| `drop_full_below_1p5m` | `20260720T071545-cd18c5fb` | 18 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_full_below_1p5m` | `F2` | 43 | 27 | 2 | 2 | 1.903 | `FULL_QUAD` | 27 | 0 | 0.221 | 2 | 0 | `False` |
| `drop_full_below_1p5m` | `F4` | 38 | 33 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.639 | 0 | 0 | `False` |
| `drop_full_below_2p0m` | `20260719T154704-f170ead6` | 2 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_full_below_2p0m` | `20260719T160537-f170ead6` | 83 | 62 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.651 | 0 | 1 | `False` |
| `drop_full_below_2p0m` | `20260719T163649-f170ead6` | 151 | 129 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `drop_full_below_2p0m` | `20260719T173050-f170ead6` | 41 | 32 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.651 | 0 | 0 | `False` |
| `drop_full_below_2p0m` | `20260719T173427-50f9dcc8` | 46 | 34 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `drop_full_below_2p0m` | `20260719T200816-f170ead6` | 56 | 44 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `drop_full_below_2p0m` | `20260719T201630-f170ead6` | 122 | 93 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.651 | 0 | 0 | `False` |
| `drop_full_below_2p0m` | `20260719T201851-50f9dcc8` | 128 | 92 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.349 | 8 | 2 | `False` |
| `drop_full_below_2p0m` | `20260719T202445-f170ead6` | 20 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_full_below_2p0m` | `20260719T202720-50f9dcc8` | 29 | 19 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.651 | 0 | 0 | `False` |
| `drop_full_below_2p0m` | `20260720T053402-f170ead6` | 21 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_full_below_2p0m` | `20260720T053514-5cebc2b2` | 56 | 46 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `drop_full_below_2p0m` | `20260720T053635-f170ead6` | 47 | 40 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.650 | 0 | 0 | `False` |
| `drop_full_below_2p0m` | `20260720T053745-5cebc2b2` | 32 | 5 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `drop_full_below_2p0m` | `20260720T053905-f170ead6` | 33 | 13 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `drop_full_below_2p0m` | `20260720T054016-5cebc2b2` | 74 | 61 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.610 | 0 | 0 | `False` |
| `drop_full_below_2p0m` | `20260720T062804-c38fd469` | 112 | 99 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.413 | 8 | 2 | `False` |
| `drop_full_below_2p0m` | `20260720T062921-790186c4` | 33 | 7 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.651 | 0 | 0 | `False` |
| `drop_full_below_2p0m` | `20260720T063258-c38fd469` | 3 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_full_below_2p0m` | `20260720T063419-790186c4` | 2 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_full_below_2p0m` | `20260720T071112-cd18c5fb` | 43 | 18 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.433 | 18 | 1 | `False` |
| `drop_full_below_2p0m` | `20260720T071220-5b501b4c` | 1 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_full_below_2p0m` | `20260720T071333-cd18c5fb` | 38 | 33 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.639 | 0 | 0 | `False` |
| `drop_full_below_2p0m` | `20260720T071545-cd18c5fb` | 18 | 0 | 0 | 0 | n/a | `n/a` | 0 | 0 | n/a | 0 | 0 | `False` |
| `drop_full_below_2p0m` | `F2` | 43 | 18 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.433 | 18 | 1 | `False` |
| `drop_full_below_2p0m` | `F4` | 38 | 33 | 0 | 0 | n/a | `n/a` | 0 | 0 | 0.639 | 0 | 0 | `False` |

## Transition Log

| Sweep | Flight | t | Range | From | To | Paired overlaps | Median delta | Jump grace consumed | Sigma abort after |
|---|---|---:|---:|---|---|---:|---:|---|---|
| `drop_full_below_2p0m` | `F2` | 6.867 | 1.649 | `FULL_QUAD` | `SIDE_PAIR` | 0 | n/a | `False` | `True` |
| `drop_full_below_2p0m` | `20260719T160537-f170ead6` | 5.963 | 1.609 | `FULL_QUAD` | `SIDE_PAIR` | 0 | n/a | `False` | `False` |
| `drop_full_below_2p0m` | `20260719T201851-50f9dcc8` | 6.523 | 1.715 | `FULL_QUAD` | `SIDE_PAIR` | 0 | n/a | `False` | `True` |
| `drop_full_below_2p0m` | `20260719T201851-50f9dcc8` | 11.589 | 6.650 | `SIDE_PAIR` | `FULL_QUAD` | 0 | n/a | `False` | `False` |
| `drop_full_below_2p0m` | `20260720T062804-c38fd469` | 6.000 | 1.699 | `FULL_QUAD` | `SIDE_PAIR` | 0 | n/a | `False` | `True` |
| `drop_full_below_2p0m` | `20260720T062804-c38fd469` | 8.035 | n/a | `SIDE_PAIR` | `FULL_QUAD` | 0 | n/a | `False` | `False` |
| `drop_full_below_2p0m` | `20260720T071112-cd18c5fb` | 6.867 | 1.649 | `FULL_QUAD` | `SIDE_PAIR` | 0 | n/a | `False` | `True` |
| `drop_full_below_1p5m` | `20260719T201851-50f9dcc8` | 6.691 | 1.268 | `FULL_QUAD` | `SIDE_PAIR` | 0 | n/a | `False` | `True` |
| `drop_full_below_1p5m` | `20260719T201851-50f9dcc8` | 11.589 | 6.650 | `SIDE_PAIR` | `FULL_QUAD` | 0 | n/a | `False` | `False` |
| `drop_full_below_1p5m` | `20260720T062804-c38fd469` | 6.202 | 1.241 | `FULL_QUAD` | `SIDE_PAIR` | 0 | n/a | `False` | `True` |
| `drop_full_below_1p5m` | `20260720T062804-c38fd469` | 8.035 | n/a | `SIDE_PAIR` | `FULL_QUAD` | 0 | n/a | `False` | `True` |

## Earned Sigma Row

| Cohort | Range bin | n | bias_e | sigma_e | paired-switch sigma_v | n_v |
|---|---|---:|---:|---:|---:|---:|
| `primary_f2_f4` | `all` | 21 | -0.028 | 0.049 | 0.509 | 18 |
| `primary_f2_f4` | `3p0-3p5` | 8 | 0.000 | 0.000 | 0.000 | 7 |
| `primary_f2_f4` | `2p5-3p0` | 4 | 0.000 | 0.000 | 0.000 | 3 |
| `primary_f2_f4` | `2p0-2p5` | 5 | -0.027 | 0.020 | 0.795 | 4 |
| `primary_f2_f4` | `1p5-2p0` | 3 | -0.084 | 0.027 | 0.451 | 2 |
| `primary_f2_f4` | `1p0-1p5` | 1 | -0.196 | n/a | n/a | 0 |
| `sweep29` | `all` | 189 | -0.011 | 0.035 | 0.277 | 167 |
| `sweep29` | `3p0-3p5` | 60 | 0.000 | 0.000 | 0.000 | 45 |
| `sweep29` | `2p5-3p0` | 45 | 0.000 | 0.000 | 0.000 | 36 |
| `sweep29` | `2p0-2p5` | 39 | -0.004 | 0.012 | 0.311 | 31 |
| `sweep29` | `1p5-2p0` | 29 | -0.023 | 0.057 | 0.412 | 21 |
| `sweep29` | `1p0-1p5` | 14 | -0.093 | 0.037 | 0.675 | 11 |
| `sweep29` | `0p5-1p0` | 1 | -0.066 | n/a | n/a | 0 |

## Two-Component Sigma-v

| Cohort | Range bin | paired n | paired-switch sigma_v | maintenance n | maintenance sigma_v | release sigma_v | source |
|---|---|---:|---:|---:|---:|---:|---|
| `primary_f2_f4` | `all` | 21 | 0.509 | 5 | 0.290 | 0.509 | `paired_switch` |
| `primary_f2_f4` | `3p0-3p5` | 8 | 0.000 | 0 | n/a | 0.000 | `paired_switch` |
| `primary_f2_f4` | `2p5-3p0` | 4 | 0.000 | 0 | n/a | 0.000 | `paired_switch` |
| `primary_f2_f4` | `2p0-2p5` | 5 | 0.795 | 0 | n/a | 0.795 | `paired_switch` |
| `primary_f2_f4` | `1p5-2p0` | 3 | 0.451 | 3 | 0.360 | 0.451 | `paired_switch` |
| `primary_f2_f4` | `1p0-1p5` | 1 | n/a | 2 | 0.019 | 0.019 | `maintenance` |
| `sweep29` | `all` | 189 | 0.277 | 58 | 0.195 | 0.277 | `paired_switch` |
| `sweep29` | `3p0-3p5` | 60 | 0.000 | 0 | n/a | 0.000 | `paired_switch` |
| `sweep29` | `2p5-3p0` | 45 | 0.000 | 0 | n/a | 0.000 | `paired_switch` |
| `sweep29` | `2p0-2p5` | 39 | 0.311 | 0 | n/a | 0.311 | `paired_switch` |
| `sweep29` | `1p5-2p0` | 29 | 0.412 | 28 | 0.142 | 0.412 | `paired_switch` |
| `sweep29` | `1p0-1p5` | 14 | 0.675 | 28 | 0.145 | 0.675 | `paired_switch` |
| `sweep29` | `0p5-1p0` | 1 | n/a | 2 | 0.028 | 0.028 | `maintenance` |

## Maintenance Sigma Strata

| Cohort | Sweep | Range bin | Anchor age bin | n | median age | median range | maintenance sigma_v |
|---|---|---|---|---:|---:|---:|---:|
| `primary_f2_f4` | `drop_full_below_1p5m` | `all` | `all` | 1 | 0.299 | 1.064 | n/a |
| `primary_f2_f4` | `drop_full_below_1p5m` | `1p0-1p5` | `all` | 1 | 0.299 | 1.064 | n/a |
| `primary_f2_f4` | `drop_full_below_2p0m` | `all` | `all` | 4 | 0.097 | 1.735 | 0.321 |
| `primary_f2_f4` | `drop_full_below_2p0m` | `1p5-2p0` | `all` | 3 | 0.062 | 1.821 | 0.360 |
| `primary_f2_f4` | `drop_full_below_2p0m` | `1p0-1p5` | `all` | 1 | 0.431 | 1.064 | n/a |
| `primary_f2_f4` | `all_full_withheld` | `all` | `all` | 5 | 0.132 | 1.649 | 0.290 |
| `primary_f2_f4` | `all_full_withheld` | `all` | `0p00-0p10` | 2 | 0.048 | 1.862 | 0.378 |
| `primary_f2_f4` | `all_full_withheld` | `all` | `0p10-0p25` | 1 | 0.132 | 1.649 | n/a |
| `primary_f2_f4` | `all_full_withheld` | `all` | `0p25-0p50` | 2 | 0.365 | 1.064 | 0.019 |
| `primary_f2_f4` | `all_full_withheld` | `1p5-2p0` | `all` | 3 | 0.062 | 1.821 | 0.360 |
| `primary_f2_f4` | `all_full_withheld` | `1p5-2p0` | `0p00-0p10` | 2 | 0.048 | 1.862 | 0.378 |
| `primary_f2_f4` | `all_full_withheld` | `1p5-2p0` | `0p10-0p25` | 1 | 0.132 | 1.649 | n/a |
| `primary_f2_f4` | `all_full_withheld` | `1p0-1p5` | `all` | 2 | 0.365 | 1.064 | 0.019 |
| `primary_f2_f4` | `all_full_withheld` | `1p0-1p5` | `0p25-0p50` | 2 | 0.365 | 1.064 | 0.019 |
| `sweep29` | `drop_full_below_1p5m` | `all` | `all` | 15 | 0.132 | 1.241 | 0.191 |
| `sweep29` | `drop_full_below_1p5m` | `1p0-1p5` | `all` | 14 | 0.132 | 1.254 | 0.186 |
| `sweep29` | `drop_full_below_1p5m` | `0p5-1p0` | `all` | 1 | 0.229 | 0.989 | n/a |
| `sweep29` | `drop_full_below_2p0m` | `all` | `all` | 43 | 0.201 | 1.649 | 0.165 |
| `sweep29` | `drop_full_below_2p0m` | `1p5-2p0` | `all` | 28 | 0.132 | 1.813 | 0.142 |
| `sweep29` | `drop_full_below_2p0m` | `1p0-1p5` | `all` | 14 | 0.316 | 1.254 | 0.071 |
| `sweep29` | `drop_full_below_2p0m` | `0p5-1p0` | `all` | 1 | 0.430 | 0.989 | n/a |
| `sweep29` | `all_full_withheld` | `all` | `all` | 58 | 0.167 | 1.492 | 0.195 |
| `sweep29` | `all_full_withheld` | `all` | `0p00-0p10` | 17 | 0.062 | 1.845 | 0.241 |
| `sweep29` | `all_full_withheld` | `all` | `0p10-0p25` | 24 | 0.167 | 1.522 | 0.182 |
| `sweep29` | `all_full_withheld` | `all` | `0p25-0p50` | 14 | 0.333 | 1.183 | 0.096 |
| `sweep29` | `all_full_withheld` | `all` | `0p50-1p00` | 1 | 1.000 | 1.912 | n/a |
| `sweep29` | `all_full_withheld` | `all` | `gte1p00` | 2 | 4.551 | 1.892 | 0.000 |
| `sweep29` | `all_full_withheld` | `1p5-2p0` | `all` | 28 | 0.132 | 1.813 | 0.142 |
| `sweep29` | `all_full_withheld` | `1p5-2p0` | `0p00-0p10` | 12 | 0.063 | 1.903 | 0.154 |
| `sweep29` | `all_full_withheld` | `1p5-2p0` | `0p10-0p25` | 12 | 0.149 | 1.674 | 0.134 |
| `sweep29` | `all_full_withheld` | `1p5-2p0` | `0p25-0p50` | 1 | 0.264 | 1.523 | n/a |
| `sweep29` | `all_full_withheld` | `1p5-2p0` | `0p50-1p00` | 1 | 1.000 | 1.912 | n/a |
| `sweep29` | `all_full_withheld` | `1p5-2p0` | `gte1p00` | 2 | 4.551 | 1.892 | 0.000 |
| `sweep29` | `all_full_withheld` | `1p0-1p5` | `all` | 28 | 0.232 | 1.254 | 0.145 |
| `sweep29` | `all_full_withheld` | `1p0-1p5` | `0p00-0p10` | 5 | 0.062 | 1.397 | 0.247 |
| `sweep29` | `all_full_withheld` | `1p0-1p5` | `0p10-0p25` | 11 | 0.194 | 1.241 | 0.136 |
| `sweep29` | `all_full_withheld` | `1p0-1p5` | `0p25-0p50` | 12 | 0.333 | 1.183 | 0.067 |
| `sweep29` | `all_full_withheld` | `0p5-1p0` | `all` | 2 | 0.329 | 0.989 | 0.028 |
| `sweep29` | `all_full_withheld` | `0p5-1p0` | `0p10-0p25` | 1 | 0.229 | 0.989 | n/a |
| `sweep29` | `all_full_withheld` | `0p5-1p0` | `0p25-0p50` | 1 | 0.430 | 0.989 | n/a |

## Verdict

NO-PASS: shadow capture or full->side hold was not observed in this recorded-video replay set. Treat this as a liveness gap, not a real sim run.

Artifacts: `features.csv`, `observer_timeline.csv`, `shadow_capture_timeline.csv`, `shadow_capture_summary.csv`, `shadow_source_transitions.csv`, `observer_source_transitions.csv`, `earned_sigma_pairs.csv`, `earned_sigma_summary.csv`, `maintenance_sigma_rows.csv`, `maintenance_sigma_summary.csv`, `two_component_sigma_summary.csv`, and `summary.json`.
