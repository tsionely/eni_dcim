# R1h B slow-blind run 1

- exact_head_flown: 34c1a77987de2c40252890446f22cd0180ad22c6
- command: scripts\fly_once.py --max-duration 300 --patch planner.commit.speed_mps=1.8 --patch planner.terminal.enable=false --patch planner.commit.vz_cap_mps=1.2 --patch planner.approach.speed_far_mps=1.5 --patch planner.approach.speed_near_mps=1.0 --patch planner.retreat.speed_mps=0.8
- gates: 0
- wall: 11.700039900024422s
- abort: environment collision (impulse=1.2)
- phase: hover
- env hits: 3; clips: 0
