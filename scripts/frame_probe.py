"""Phase-1 experiment: does the sim honor MAV_FRAME_BODY_NED velocities?

Run against the REAL sim on the Windows machine. The probe:

1. arms, takes off (climbs for 2s)
2. yaws 90 degrees in place
3. commands +x velocity in BODY frame for 3s
4. records IMU the whole time (logs/frame_probe/)

Interpretation (see docs/02): after a 90-degree yaw, a BODY-frame +x command
accelerates along the drone's new heading; a LOCAL_NED interpretation
accelerates along the original heading. The IMU accelerometer trace (lateral
vs longitudinal specific force at the onset of step 3) distinguishes the two.
Set control.velocity.frame in config/params_default.json accordingly.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from aigp.app import App, SimConfig
from aigp.core.messages import Topic


def main() -> int:
    cfg = SimConfig.load("config/sim.json")
    app = App(cfg)
    app.connect()
    io = app.mavlink
    imu_cell = app.bus.cell(Topic.IMU)

    # (t_mono, label, accel_xyz, gyro_xyz)
    samples: list[tuple[float, str, list[float], list[float]]] = []

    print("Arming...", flush=True)
    io.arm()
    time.sleep(1.0)

    print("Takeoff (2s climb)...", flush=True)
    t_end = time.monotonic() + 2.0
    while time.monotonic() < t_end:
        io.send_velocity(0.0, 0.0, -1.0, 0.0, body_frame=True)
        time.sleep(0.02)

    print("Yawing 90 degrees...", flush=True)
    t_end = time.monotonic() + 2.0
    while time.monotonic() < t_end:
        io.send_velocity(0.0, 0.0, 0.0, 0.785, body_frame=True)   # ~45 deg/s * 2s
        time.sleep(0.02)

    print("BODY +x step (3s) — recording IMU...", flush=True)
    t_end = time.monotonic() + 3.0
    last_seq = 0
    while time.monotonic() < t_end:
        io.send_velocity(1.5, 0.0, 0.0, 0.0, body_frame=True)
        fresh = imu_cell.get_if_newer(last_seq)
        if fresh is not None:
            imu, last_seq = fresh
            samples.append((time.monotonic(), "step", imu.accel.tolist(), imu.gyro.tolist()))
        time.sleep(0.005)

    io.send_velocity(0.0, 0.0, 0.0, 0.0, body_frame=True)
    time.sleep(0.5)
    io.disarm()
    app.close()

    out = Path("logs/frame_probe")
    out.mkdir(parents=True, exist_ok=True)
    import json
    with open(out / "probe.json", "w", encoding="utf-8") as f:
        json.dump(samples, f)

    # Quick verdict: mean specific force during the step, body x vs y.
    step = [s for s in samples if s[1] == "step"]
    if step:
        n = len(step)
        ax = sum(s[2][0] for s in step) / n
        ay = sum(s[2][1] for s in step) / n
        print(f"step-phase mean specific force: body_x={ax:.2f} body_y={ay:.2f}", flush=True)
        print("If |body_x| >> |body_y|: sim honors BODY frame -> keep "
              "control.velocity.frame='body'.", flush=True)
        print("If |body_y| is dominant: sim used LOCAL_NED -> set frame='ned' "
              "(and see docs/02 for yaw compensation).", flush=True)
    print(f"Saved {len(samples)} samples to {out / 'probe.json'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
