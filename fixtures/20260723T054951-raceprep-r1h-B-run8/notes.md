# R1h B slow-blind run 8

- exact_head_flown: adb57537182ba9b060775f4e987afffde711f562
- command: scripts\fly_once.py --max-duration 300 --patch planner.commit.speed_mps=1.8 --patch planner.terminal.enable=false --patch planner.commit.vz_cap_mps=1.2 --patch planner.approach.speed_far_mps=1.5 --patch planner.approach.speed_near_mps=1.0 --patch planner.retreat.speed_mps=0.8
- gates: 0
- wall: 13.796081400010735s
- abort: environment collision (impulse=2.6)
- phase: search
- env hits: 7; clips: 0
