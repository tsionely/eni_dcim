# R1h B slow-blind run 4

- exact_head_flown: 6e1d8cbfc0f8611aadd51ea13073a2f746e8d37e
- command: scripts\fly_once.py --max-duration 300 --patch planner.commit.speed_mps=1.8 --patch planner.terminal.enable=false --patch planner.commit.vz_cap_mps=1.2 --patch planner.approach.speed_far_mps=1.5 --patch planner.approach.speed_near_mps=1.0 --patch planner.retreat.speed_mps=0.8
- gates: 0
- wall: 9.012061499990523s
- abort: environment collision (impulse=1.4)
- phase: recover
- env hits: 1; clips: 0
