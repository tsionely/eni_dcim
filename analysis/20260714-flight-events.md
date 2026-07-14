# Flight event mining

Source logs: `C:\Users\tsion\Projects\eni_dcim_phase1\logs`

## `20260713T190311-db4c58dd`

- span: 20.0s
- topics: `{'fsm': 5, 'imu': 2295, 'state': 1001, 'setpoint': 1001, 'actuator': 1884, 'race': 160, 'heartbeat': 396, 'loop_stats': 1}`
- detections in log: 0
- min gate distance: None
- result: `{"finished":false,"aborted":true,"abort_reason":"max duration","gates_passed":0,"lap_time_s":null,"gate_clips":0,"env_hits":0,"duration_s":20.00046030001249,"loop_overrun_frac":0.0,"loop_stats":{"ticks":5000,"overruns":0,"overrun_frac":0.0,"max_late_us":0},"flight_id":"20260713T190311-db4c58dd","log_dir":"logs\\20260713T190311-db4c58dd"}`
- race changes:
  - t=0.092s started=None gate=0 rstart=4750352 boot=7503489
  - t=0.101s started=None gate=0 rstart=-1 boot=167969
  - t=0.343s started=None gate=0 rstart=4750352 boot=7503739
  - t=0.351s started=None gate=0 rstart=-1 boot=168219
  - t=0.593s started=None gate=0 rstart=4750352 boot=7503990
  - t=0.602s started=None gate=0 rstart=-1 boot=168469
  - t=0.844s started=None gate=0 rstart=4750352 boot=7504240
  - t=0.852s started=None gate=0 rstart=-1 boot=168720
  - t=1.095s started=None gate=0 rstart=4750352 boot=7504491
  - t=1.103s started=None gate=0 rstart=-1 boot=168971
  - t=1.345s started=None gate=0 rstart=4750352 boot=7504742
  - t=1.354s started=None gate=0 rstart=-1 boot=169222
- FSM:
  - t=0.0s IDLE -> ARMING
  - t=0.1s ARMING -> TAKEOFF
  - t=1.604s TAKEOFF -> RACING
  - t=20.0s RACING -> ABORTED
  - t=20.0s ABORTED -> DONE
- proposed slices:

## `20260713T202513-ea4b5f0c`

- span: 45.998s
- topics: `{'imu': 5300, 'actuator': 4341, 'heartbeat': 461, 'race': 187, 'fsm': 5, 'state': 2251, 'setpoint': 2251, 'frame': 11025, 'detection': 529, 'loop_stats': 1}`
- detections in log: 529
- min gate distance: 11.973
- result: `{"finished":false,"aborted":true,"abort_reason":"max duration","gates_passed":0,"lap_time_s":null,"gate_clips":0,"env_hits":0,"duration_s":45.00086550001288,"loop_overrun_frac":0.0,"loop_stats":{"ticks":11250,"overruns":0,"overrun_frac":0.0,"max_late_us":0},"flight_id":"20260713T202513-ea4b5f0c","log_dir":"logs\\20260713T202513-ea4b5f0c"}`
- race changes:
  - t=0.137s started=None gate=0 rstart=11435767 boot=12426287
  - t=13.144s started=None gate=0 rstart=-1 boot=12439293
  - t=16.178s started=None gate=0 rstart=12445162 boot=12442328
- FSM:
  - t=0.996s IDLE -> ARMING
  - t=1.096s ARMING -> TAKEOFF
  - t=2.596s TAKEOFF -> RACING
  - t=45.997s RACING -> ABORTED
  - t=45.997s ABORTED -> DONE
- proposed slices:
  - `closest_gate` start_s=11.7780712 dur=4.0 — min gate distance 11.97m at t=13.28s
  - `countdown_future_start` start_s=15.678 dur=5.0 — race_start=12445162 > boot=12442328 (delta 2834 ms) at t=16.178s

## `20260714T041536-88e6e576`

- span: 44.809s
- topics: `{'actuator': 4218, 'imu': 5145, 'heartbeat': 449, 'race': 183, 'fsm': 6, 'state': 2191, 'setpoint': 2191, 'frame': 8535, 'detection': 7890, 'loop_stats': 1}`
- detections in log: 7890
- min gate distance: 13.461
- result: `{"finished":false,"aborted":true,"abort_reason":"stale channels: frame","gates_passed":0,"lap_time_s":null,"gate_clips":0,"env_hits":0,"duration_s":43.800316700013354,"loop_overrun_frac":0.000273972602739726,"loop_stats":{"ticks":10950,"overruns":3,"overrun_frac":0.000273972602739726,"max_late_us":3314},"flight_id":"20260714T041536-88e6e576","log_dir":"logs\\20260714T041536-88e6e576"}`
- race changes:
  - t=0.183s started=None gate=0 rstart=3321 boot=219835
  - t=12.365s started=None gate=0 rstart=-1 boot=232017
  - t=15.215s started=None gate=0 rstart=237696 boot=234867
- FSM:
  - t=1.008s IDLE -> ARMING
  - t=1.105s ARMING -> THROTTLE_DOWN
  - t=2.608s THROTTLE_DOWN -> TAKEOFF
  - t=4.109s TAKEOFF -> RACING
  - t=44.809s RACING -> ABORTED
  - t=44.809s ABORTED -> DONE
- proposed slices:
  - `closest_gate` start_s=28.6819459 dur=4.0 — min gate distance 13.46m at t=30.18s
  - `countdown_future_start` start_s=14.715 dur=5.0 — race_start=237696 > boot=234867 (delta 2829 ms) at t=15.215s

## `20260714T045635-b9a568ab`

- span: 47.093s
- topics: `{'actuator': 4451, 'imu': 5429, 'race': 192, 'heartbeat': 472, 'fsm': 6, 'state': 2305, 'setpoint': 2305, 'frame': 12512, 'detection': 691, 'loop_stats': 1}`
- detections in log: 691
- min gate distance: 13.621
- result: `{"finished":false,"aborted":true,"abort_reason":"stale channels: frame","gates_passed":0,"lap_time_s":null,"gate_clips":0,"env_hits":0,"duration_s":46.09218270005658,"loop_overrun_frac":8.678295582747549e-05,"loop_stats":{"ticks":11523,"overruns":1,"overrun_frac":8.678295582747549e-05,"max_late_us":2217},"flight_id":"20260714T045635-b9a568ab","log_dir":"logs\\20260714T045635-b9a568ab"}`
- race changes:
  - t=0.038s started=None gate=0 rstart=3295 boot=292005
  - t=12.276s started=None gate=0 rstart=-1 boot=304243
  - t=15.076s started=None gate=0 rstart=309934 boot=307043
- FSM:
  - t=0.999s IDLE -> ARMING
  - t=1.099s ARMING -> THROTTLE_DOWN
  - t=4.103s THROTTLE_DOWN -> TAKEOFF
  - t=5.604s TAKEOFF -> RACING
  - t=47.091s RACING -> ABORTED
  - t=47.092s ABORTED -> DONE
- proposed slices:
  - `closest_gate` start_s=13.5308514 dur=4.0 — min gate distance 13.62m at t=15.03s
  - `countdown_future_start` start_s=14.576 dur=5.0 — race_start=309934 > boot=307043 (delta 2891 ms) at t=15.076s

## `20260714T072732-8ff375f3`

- span: 42.588s
- topics: `{'actuator': 4002, 'imu': 4883, 'heartbeat': 427, 'race': 174, 'fsm': 6, 'state': 2080, 'setpoint': 2080, 'frame': 9920, 'detection': 1201, 'loop_stats': 1}`
- detections in log: 1201
- min gate distance: 3.973
- result: `{"finished":false,"aborted":true,"abort_reason":"stale channels: frame","gates_passed":0,"lap_time_s":null,"gate_clips":0,"env_hits":0,"duration_s":41.580346299975645,"loop_overrun_frac":0.0,"loop_stats":{"ticks":10395,"overruns":0,"overrun_frac":0.0,"max_late_us":0},"flight_id":"20260714T072732-8ff375f3","log_dir":"logs\\20260714T072732-8ff375f3"}`
- race changes:
  - t=0.133s started=None gate=0 rstart=4017263 boot=9349116
  - t=13.433s started=None gate=0 rstart=-1 boot=9362417
  - t=16.171s started=None gate=0 rstart=9367936 boot=9365155
- FSM:
  - t=1.007s IDLE -> ARMING
  - t=1.1s ARMING -> THROTTLE_DOWN
  - t=16.172s THROTTLE_DOWN -> TAKEOFF
  - t=17.676s TAKEOFF -> RACING
  - t=42.588s RACING -> ABORTED
  - t=42.588s ABORTED -> DONE
- proposed slices:
  - `closest_gate` start_s=23.2218697 dur=4.0 — min gate distance 3.97m at t=24.72s
  - `countdown_future_start` start_s=15.671 dur=5.0 — race_start=9367936 > boot=9365155 (delta 2781 ms) at t=16.171s

## `20260714T081945-bb5494d6`

- span: 43.082s
- topics: `{'actuator': 4060, 'imu': 4960, 'race': 176, 'heartbeat': 432, 'fsm': 6, 'state': 2105, 'setpoint': 2105, 'frame': 7499, 'detection': 1321, 'loop_stats': 1}`
- detections in log: 1321
- min gate distance: 6.98
- result: `{"finished":false,"aborted":true,"abort_reason":"stale channels: frame","gates_passed":0,"lap_time_s":null,"gate_clips":0,"env_hits":0,"duration_s":42.08015770005295,"loop_overrun_frac":0.0,"loop_stats":{"ticks":10520,"overruns":0,"overrun_frac":0.0,"max_late_us":0},"flight_id":"20260714T081945-bb5494d6","log_dir":"logs\\20260714T081945-bb5494d6"}`
- race changes:
  - t=0.083s started=None gate=0 rstart=11873367 boot=12482444
  - t=14.469s started=None gate=0 rstart=-1 boot=12496831
  - t=17.377s started=None gate=0 rstart=12502490 boot=12499739
- FSM:
  - t=1.0s IDLE -> ARMING
  - t=1.1s ARMING -> THROTTLE_DOWN
  - t=20.136s THROTTLE_DOWN -> TAKEOFF
  - t=21.64s TAKEOFF -> RACING
  - t=43.08s RACING -> ABORTED
  - t=43.08s ABORTED -> DONE
- proposed slices:
  - `closest_gate` start_s=20.0413919 dur=4.0 — min gate distance 6.98m at t=21.54s
  - `countdown_future_start` start_s=16.877 dur=5.0 — race_start=12502490 > boot=12499739 (delta 2751 ms) at t=17.377s
