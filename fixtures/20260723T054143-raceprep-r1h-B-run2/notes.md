# R1h B slow-blind run 2

- exact_head_flown: 6de7bd555a21044ee80d29f038d9aea28b30b363
- command: scripts\fly_once.py --max-duration 300 --patch planner.commit.speed_mps=1.8 --patch planner.terminal.enable=false --patch planner.commit.vz_cap_mps=1.2 --patch planner.approach.speed_far_mps=1.5 --patch planner.approach.speed_near_mps=1.0 --patch planner.retreat.speed_mps=0.8
- gates: 0
- wall: 10.252843499998562s
- abort: gate clip budget exceeded (11)
- phase: recover
- env hits: 0; clips: 11
