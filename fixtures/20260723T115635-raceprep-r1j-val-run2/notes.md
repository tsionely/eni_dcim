# R1j val run 2 (amended protocol)

- exact_head_flown: 58a6768b03616e20380cd9da77de089e798e5ef9
- command: scripts\fly_once.py --max-duration 300 --patch planner.commit.speed_mps=1.8 --patch planner.commit.vz_cap_mps=1.2
- gates: 1
- abort: environment collision (impulse=3.0)
- search ticks: 105
- blind_hold true search ticks: 105
- search collisions: 1
- blind_hold collisions: 1
- search env collisions: 1
- known abort class: True
- harm_clean: False
- mechanism_exercising: True
