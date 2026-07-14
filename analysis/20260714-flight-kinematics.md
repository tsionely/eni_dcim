# Flight kinematics report

Generated from operator `logs/*/flight.jsonl` using `aigp.telemetry.plots`.
Plots live under `analysis/kinematics/<flight_id>/`.

## `20260713T190311-db4c58dd`

- result: aborted=True reason=`max duration` gates=0 dur=20.00046030001249
- IMU |a| mean±std: 26.65±0.00 m/s²; gyro p95 |ω|=14.44 rad/s
- accel_std xyz: [0.0, 0.0, 0.0]; gyro_std xyz: [0.0, 0.0, 0.0]
- detections in log: 0; min/median gate dist: None/None m
- FSM:
  - t=0.000s IDLE -> ARMING
  - t=0.100s ARMING -> TAKEOFF
  - t=1.604s TAKEOFF -> RACING
  - t=20.000s RACING -> ABORTED
  - t=20.000s ABORTED -> DONE
- setpoint phases:
  - t=0.0s `hover`
  - t=0.096s `takeoff`
  - t=1.616s `search`
- plots:
  - `analysis/kinematics/20260713T190311-db4c58dd/flight.png`
  - `analysis/kinematics/20260713T190311-db4c58dd/imu.png`
- findings: high angular rates (tumble/aggressive motion)

## `20260713T202513-ea4b5f0c`

- result: aborted=True reason=`max duration` gates=0 dur=45.00086550001288
- IMU |a| mean±std: 9.81±0.00 m/s²; gyro p95 |ω|=0.00 rad/s
- accel_std xyz: [0.002, 0.004, 0.002]; gyro_std xyz: [0.0, 0.0, 0.0]
- detections in log: 529; min/median gate dist: 11.973139123336507/15.08627123840411 m
- FSM:
  - t=0.000s IDLE -> ARMING
  - t=0.100s ARMING -> TAKEOFF
  - t=1.600s TAKEOFF -> RACING
  - t=45.001s RACING -> ABORTED
  - t=45.001s ABORTED -> DONE
- setpoint phases:
  - t=0.0s `hover`
  - t=0.096s `takeoff`
  - t=1.596s `search`
  - t=12.296s `approach`
- plots:
  - `analysis/kinematics/20260713T202513-ea4b5f0c/flight.png`
  - `analysis/kinematics/20260713T202513-ea4b5f0c/imu.png`
- findings: near-frozen IMU (parked/menu-like)

## `20260714T041536-88e6e576`

- result: aborted=True reason=`stale channels: frame` gates=0 dur=43.800316700013354
- IMU |a| mean±std: 9.81±0.01 m/s²; gyro p95 |ω|=0.00 rad/s
- accel_std xyz: [1.342, 0.009, 0.218]; gyro_std xyz: [0.0, 0.0, 0.0]
- detections in log: 7890; min/median gate dist: 13.461472867628872/13.949836541934394 m
- FSM:
  - t=0.000s IDLE -> ARMING
  - t=0.096s ARMING -> THROTTLE_DOWN
  - t=1.600s THROTTLE_DOWN -> TAKEOFF
  - t=3.100s TAKEOFF -> RACING
  - t=43.800s RACING -> ABORTED
  - t=43.800s ABORTED -> DONE
- setpoint phases:
  - t=0.0s `hover`
  - t=1.596s `takeoff`
  - t=3.096s `search`
  - t=11.896s `approach`
  - t=43.796s `hover`
- plots:
  - `analysis/kinematics/20260714T041536-88e6e576/flight.png`
  - `analysis/kinematics/20260714T041536-88e6e576/imu.png`
- findings: near-frozen IMU (parked/menu-like); aborted on stale vision channel

## `20260714T045635-b9a568ab`

- result: aborted=True reason=`stale channels: frame` gates=0 dur=46.09218270005658
- IMU |a| mean±std: 11.73±6.36 m/s²; gyro p95 |ω|=9.80 rad/s
- accel_std xyz: [3.613, 6.251, 11.184]; gyro_std xyz: [5.201, 2.976, 0.097]
- detections in log: 691; min/median gate dist: 13.62055641267596/14.181094549936661 m
- FSM:
  - t=0.000s IDLE -> ARMING
  - t=0.100s ARMING -> THROTTLE_DOWN
  - t=3.104s THROTTLE_DOWN -> TAKEOFF
  - t=4.604s TAKEOFF -> RACING
  - t=46.092s RACING -> ABORTED
  - t=46.092s ABORTED -> DONE
- setpoint phases:
  - t=0.0s `hover`
  - t=3.116s `takeoff`
  - t=4.616s `search`
  - t=11.916s `approach`
- plots:
  - `analysis/kinematics/20260714T045635-b9a568ab/flight.png`
  - `analysis/kinematics/20260714T045635-b9a568ab/imu.png`
- findings: high angular rates (tumble/aggressive motion); aborted on stale vision channel

## `20260714T072732-8ff375f3`

- result: aborted=True reason=`stale channels: frame` gates=0 dur=41.580346299975645
- IMU |a| mean±std: 17.26±15.97 m/s²; gyro p95 |ω|=8.19 rad/s
- accel_std xyz: [4.945, 4.733, 19.992]; gyro_std xyz: [2.035, 1.97, 1.778]
- detections in log: 1201; min/median gate dist: 3.9727935977084057/14.384816702957046 m
- FSM:
  - t=0.000s IDLE -> ARMING
  - t=0.092s ARMING -> THROTTLE_DOWN
  - t=15.164s THROTTLE_DOWN -> TAKEOFF
  - t=16.668s TAKEOFF -> RACING
  - t=41.580s RACING -> ABORTED
  - t=41.580s ABORTED -> DONE
- setpoint phases:
  - t=0.0s `hover`
  - t=15.176s `takeoff`
  - t=16.676s `approach`
  - t=41.576s `hover`
- plots:
  - `analysis/kinematics/20260714T072732-8ff375f3/flight.png`
  - `analysis/kinematics/20260714T072732-8ff375f3/imu.png`
- findings: high angular rates (tumble/aggressive motion); aborted on stale vision channel

## `20260714T081945-bb5494d6`

- result: aborted=True reason=`stale channels: frame` gates=0 dur=42.08015770005295
- IMU |a| mean±std: 13.40±9.26 m/s²; gyro p95 |ω|=8.85 rad/s
- accel_std xyz: [6.087, 5.546, 11.918]; gyro_std xyz: [2.207, 2.313, 1.826]
- detections in log: 1321; min/median gate dist: 6.979653886100852/14.028954061850703 m
- FSM:
  - t=0.000s IDLE -> ARMING
  - t=0.100s ARMING -> THROTTLE_DOWN
  - t=19.136s THROTTLE_DOWN -> TAKEOFF
  - t=20.640s TAKEOFF -> RACING
  - t=42.080s RACING -> ABORTED
  - t=42.080s ABORTED -> DONE
- setpoint phases:
  - t=0.0s `hover`
  - t=19.136s `takeoff`
  - t=20.636s `approach`
  - t=42.076s `hover`
- plots:
  - `analysis/kinematics/20260714T081945-bb5494d6/flight.png`
  - `analysis/kinematics/20260714T081945-bb5494d6/imu.png`
- findings: high angular rates (tumble/aggressive motion); aborted on stale vision channel

## Cross-flight takeaways

- Flights that enter TAKEOFF before the scheduled race start show high |ω| and sparse detections — consistent with early-start DSQ + tumble.
- Parked/race-waiting flights (`20260713T202513`, `20260714T041536`) keep high detection counts and modest IMU motion.
- Closest logged approach so far: phase2b `20260714T072732` at ~3.97 m (still gates_passed=0).
