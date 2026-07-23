# R1j 3390 launch diagnosis (raceprep-r1j3390-diag-1)

- exact_head_flown: ce3a774be4e6a001758857da8490b8f69efc231a
- sim: v1.0.3390 at C:\Users\tsion\Downloads\AI-GP Simulator v1.0.3390\FlightSim.exe
- event selected: R2-TRAINING (proven harness, r2training template)
- command: scripts\fly_once.py --max-duration 300 --patch planner.commit.speed_mps=1.8 --patch planner.commit.vz_cap_mps=1.2

## Ordered launch diagnosis
1. LAUNCH PATH: launched FlightSim.exe from the NEW 3390 root (not 3385/launch_sim.ps1). Command: Start-Process 'C:\Users\tsion\Downloads\AI-GP Simulator v1.0.3390\FlightSim.exe'.
2. SIM LOGIN/TRACK: credentials were pre-saved on the 3390 install; login submitted and reached the event list + R2-TRAINING track view. select_ok=False.
3. MAVLINK LINK: pilot 'Connected. Starting IO agents' = True (udp:14550 heartbeat). heartbeat_count=11, armed_true=1.
4. ARM: reached_ARMING=True, reached_THROTTLE_DOWN=True.
5. RACE GO: reached_TAKEOFF=False, reached_RACING=False. race_records=5, race_start_ms_distinct=-1, race_ever_armed=False.
- imu_msg_count=0; abort_reason=stale channels: imu; duration_s=0.0880582999670878; gates=0.

## FIRST FAILING STEP: STEP2 (sim login/track view / event selection) failed
