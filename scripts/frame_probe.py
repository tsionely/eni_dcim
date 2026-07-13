"""Frame-semantics probe v2 (run against the REAL sim on the Windows machine).

Determines how the sim interprets SET_POSITION_TARGET_LOCAL_NED velocities
(BODY vs LOCAL_NED) and whether it honors the yaw_rate field.

v1 lesson (fixtures/20260713T190414-phase1): recording only the step phase is
not enough — the drone was spinning at -1 rad/s during the step with zero
commanded yaw rate, making the verdict unreliable. v2 therefore:

- records IMU through ALL phases with labels
- adds settle phases so the step starts from a quiet state
- integrates gyro_z for the actual yaw angle (vs the commanded one)
- checks step-phase spin before trusting the verdict
- estimates the world-yaw offset (spawn heading) for control.velocity.world_yaw_offset_rad

Sequence:  arm -> takeoff(2s) -> settle(2s) -> yaw(+45deg/s, 2s) -> settle(2s)
           -> step(+x 1.5 m/s, 3s) -> stop -> disarm
"""
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from aigp.app import App, SimConfig
from aigp.core.messages import Topic

YAW_RATE_CMD = 0.785   # rad/s commanded during the yaw phase
STEP_V = 1.5           # m/s commanded during the step phase


def main() -> int:
    cfg = SimConfig.load("config/sim.json")
    app = App(cfg)
    app.connect()
    io = app.mavlink
    imu_cell = app.bus.cell(Topic.IMU)

    samples: list[list] = []   # [t_mono, phase, accel_xyz, gyro_xyz]
    last_seq = 0

    def run_phase(name: str, duration_s: float, vx=0.0, vy=0.0, vz=0.0, yaw_rate=0.0):
        nonlocal last_seq
        print(f"phase {name} ({duration_s}s)...", flush=True)
        t_end = time.monotonic() + duration_s
        while time.monotonic() < t_end:
            io.send_velocity(vx, vy, vz, yaw_rate, body_frame=True)
            fresh = imu_cell.get_if_newer(last_seq)
            if fresh is not None:
                imu, last_seq = fresh
                samples.append([time.monotonic(), name,
                                imu.accel.tolist(), imu.gyro.tolist()])
            time.sleep(0.004)

    print("Arming...", flush=True)
    io.arm()
    run_phase("arm", 1.0)
    run_phase("takeoff", 2.0, vz=-1.0)
    run_phase("settle1", 2.0)
    run_phase("yaw", 2.0, yaw_rate=YAW_RATE_CMD)
    run_phase("settle2", 2.0)
    run_phase("step", 3.0, vx=STEP_V)
    run_phase("stop", 1.0)
    io.disarm()
    app.close()

    out = Path("logs/frame_probe")
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "probe.json", "w", encoding="utf-8") as f:
        json.dump(samples, f)
    print(f"Saved {len(samples)} samples to {out / 'probe.json'}", flush=True)

    # ---------------- analysis ----------------
    def phase_samples(name):
        return [s for s in samples if s[1] == name]

    def mean(vals):
        return sum(vals) / len(vals) if vals else 0.0

    print("\n=== per-phase summary (mean gyro_z / mean accel xy) ===", flush=True)
    yaw_integrated = 0.0
    yaw_at_step = None
    prev_t = None
    for t, phase, accel, gyro in samples:
        if prev_t is not None:
            yaw_integrated += gyro[2] * (t - prev_t)
        prev_t = t
        if phase == "step" and yaw_at_step is None:
            yaw_at_step = yaw_integrated
    for name in ("arm", "takeoff", "settle1", "yaw", "settle2", "step", "stop"):
        ps = phase_samples(name)
        if not ps:
            continue
        gz = mean([s[3][2] for s in ps])
        ax, ay = mean([s[2][0] for s in ps]), mean([s[2][1] for s in ps])
        print(f"  {name:8s} gyro_z={gz:+.3f} rad/s   accel_x={ax:+.2f} accel_y={ay:+.2f}",
              flush=True)

    yaw_ps = phase_samples("yaw")
    step_ps = phase_samples("step")
    print("\n=== verdicts ===", flush=True)

    gz_yaw = mean([s[3][2] for s in yaw_ps])
    print(f"yaw_rate honored: commanded {YAW_RATE_CMD:+.2f}, measured {gz_yaw:+.3f} "
          f"-> {'YES' if abs(gz_yaw) > 0.3 else 'NO/WEAK'}"
          f"{' (SIGN FLIPPED!)' if gz_yaw * YAW_RATE_CMD < -0.05 else ''}", flush=True)

    gz_step = mean([s[3][2] for s in step_ps])
    reliable = abs(gz_step) < 0.2
    if not reliable:
        print(f"WARNING: drone was spinning during step (gyro_z={gz_step:+.2f}) — "
              f"frame verdict unreliable, investigate the spin first.", flush=True)

    ax = mean([s[2][0] for s in step_ps])
    ay = mean([s[2][1] for s in step_ps])
    theta = math.atan2(ay, ax)          # accel direction in body frame
    psi_est = yaw_at_step if yaw_at_step is not None else 0.0
    print(f"integrated yaw at step start: {math.degrees(psi_est):+.1f} deg "
          f"(commanded ~{math.degrees(YAW_RATE_CMD * 2.0):+.0f})", flush=True)
    print(f"step accel direction in body frame: {math.degrees(theta):+.1f} deg "
          f"(BODY hypothesis expects ~0)", flush=True)
    # NED hypothesis: world +x seen in body rotated by -psi_world.
    psi_world = -theta
    psi0 = psi_world - psi_est
    print(f"IF the sim used LOCAL_NED: world yaw at step = {math.degrees(psi_world):+.1f} deg "
          f"-> spawn-heading offset psi0 = {math.degrees(psi0):+.1f} deg", flush=True)
    print(f"   -> set control.velocity.frame='ned' and "
          f"world_yaw_offset_rad={psi0:.3f}", flush=True)
    print(f"IF |{math.degrees(theta):.0f}deg| is small the sim honored BODY frame "
          f"-> set control.velocity.frame='body'.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
