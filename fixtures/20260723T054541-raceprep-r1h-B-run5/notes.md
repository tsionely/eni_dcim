# R1h B slow-blind run 5

- exact_head_flown: 50aa5385734a9518fb7442a63ea0ddc2e5f2ad7a
- command: scripts\fly_once.py --max-duration 300 --patch planner.commit.speed_mps=1.8 --patch planner.terminal.enable=false --patch planner.commit.vz_cap_mps=1.2 --patch planner.approach.speed_far_mps=1.5 --patch planner.approach.speed_near_mps=1.0 --patch planner.retreat.speed_mps=0.8
- gates: 0
- wall: 10.66418620001059s
- abort: environment collision (impulse=3.2)
- phase: recover
- env hits: 2; clips: 0
