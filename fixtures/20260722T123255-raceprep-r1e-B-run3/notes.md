# R1e B estimate-fix run 3

- exact_head_flown: 648a3135449b7dbee98b4bb851928fcf149856a8
- command: scripts\fly_once.py --max-duration 300 --patch planner.commit.speed_mps=1.8 --patch planner.terminal.enable=false --patch planner.commit.vz_cap_mps=1.2 --patch estimation.vision_blend=0.9
- gates: 0
- wall: 8.75200550002046s
- abort: gate clip budget exceeded (11)
- phase: recover
- env hits: 12; clips: 11
