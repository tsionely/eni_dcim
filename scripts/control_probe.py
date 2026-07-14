"""Control-authority probe (run against the REAL sim, during an active race).

Phase-1e finding: the sim overlays "THROTTLE DOWN please" and never releases
the motors — the drone sits on the pad through the whole race. This probe
performs the throttle-down handshake and then tests each control interface in
turn, reporting which one actually moves the drone:

  reset -> arm -> hold thrust=0 (handshake) -> test mode -> report -> repeat

  mode A: SET_ATTITUDE_TARGET   thrust step (0.65, level)
  mode B: SET_POSITION_TARGET   velocity climb (-1.5 m/s)
  mode C: SET_ACTUATOR_CONTROL  motors at 0.7

Motion is judged from IMU variance, actuator outputs and collisions; the
OPERATOR'S EYES are the ground truth — note per mode whether the overlay
clears and whether the drone visibly lifts/moves.

    python scripts/control_probe.py            # all modes
    python scripts/control_probe.py --modes A  # single mode
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from aigp.app import App, SimConfig
from aigp.core.messages import Topic

HANDSHAKE_S = 3.0
MODE_S = 4.0
SEND_HZ = 100.0


def main() -> int:
    parser = argparse.ArgumentParser(description="Control-authority probe")
    parser.add_argument("--config", default="config/sim.json")
    parser.add_argument("--modes", default="ABC")
    parser.add_argument("--thrust", type=float, default=0.65)
    parser.add_argument("--motor", type=float, default=0.7)
    args = parser.parse_args()

    cfg = SimConfig.load(args.config)
    app = App(cfg)
    app.connect()
    io = app.mavlink
    imu_cell = app.bus.cell(Topic.IMU)
    act_cell = app.bus.cell(Topic.ACTUATOR)
    collision_q = app.bus.events(Topic.COLLISION)

    def sample_phase(name: str, duration_s: float, send) -> dict:
        last_imu = last_act = 0
        accels, motors = [], []
        t_end = time.monotonic() + duration_s
        while time.monotonic() < t_end:
            send()
            fresh = imu_cell.get_if_newer(last_imu)
            if fresh is not None:
                imu, last_imu = fresh
                accels.append(imu.accel.tolist())
            fresh = act_cell.get_if_newer(last_act)
            if fresh is not None:
                act, last_act = fresh
                motors.append(act.motors)
            time.sleep(1.0 / SEND_HZ)
        collisions = collision_q.drain()
        accel_std = 0.0
        if len(accels) > 10:
            accel_std = max(statistics.pstdev([a[i] for a in accels]) for i in range(3))
        motor_span = 0.0
        if motors:
            flat = [m for row in motors for m in row]
            motor_span = max(flat) - min(flat)
        return {"phase": name, "imu_accel_max_std": accel_std,
                "motor_span": motor_span, "collisions": len(collisions),
                "motor_last": motors[-1] if motors else None}

    def report(r: dict) -> None:
        moved = r["imu_accel_max_std"] > 0.5 or r["motor_span"] > 1e-3 or r["collisions"]
        print(f"  {r['phase']:24s} accel_std={r['imu_accel_max_std']:.3f}  "
              f"motor_span={r['motor_span']:.3f}  collisions={r['collisions']}  "
              f"motors={r['motor_last']}  -> {'RESPONSE' if moved else 'no response'}",
              flush=True)

    modes = {
        "A": ("attitude thrust step",
              lambda: io.send_attitude_rates(0.0, 0.0, 0.0, args.thrust)),
        "B": ("velocity climb",
              lambda: io.send_velocity(0.0, 0.0, -1.5, 0.0, body_frame=False)),
        "C": ("motor command",
              lambda: io.send_motor_rpms((args.motor,) * 4)),
        # D: rate response — lift gently, then a pitch-rate pulse; the live
        #    xgyro/ygyro tell whether (and how fast) rates are honored.
        "D": ("rate response", None),
        # H: hover ladder — step the thrust and watch accel_z per step; the
        #    step where the drone stops climbing brackets hover_thrust.
        "H": ("hover-thrust ladder", None),
    }

    def run_mode_d() -> None:
        report(sample_phase("lift (thrust 0.6)", 1.2,
                            lambda: io.send_attitude_rates(0.0, 0.0, 0.0, 0.6)))
        last = 0
        gyros = []
        t_end = time.monotonic() + 0.8
        while time.monotonic() < t_end:
            io.send_attitude_rates(0.0, 0.4, 0.0, 0.55)   # pitch-rate pulse
            fresh = imu_cell.get_if_newer(last)
            if fresh is not None:
                imu, last = fresh
                gyros.append(imu.gyro.tolist())
            time.sleep(1.0 / SEND_HZ)
        if gyros:
            mean = [statistics.mean(g[i] for g in gyros) for i in range(3)]
            print(f"  pitch-rate pulse: commanded q=+0.40, measured "
                  f"p={mean[0]:+.3f} q={mean[1]:+.3f} r={mean[2]:+.3f}", flush=True)
        io.send_attitude_rates(0.0, -0.4, 0.0, 0.55)      # counter-pulse
        time.sleep(0.6)
        io.send_attitude_rates(0.0, 0.0, 0.0, 0.0)

    def run_mode_h() -> None:
        for thrust in (0.40, 0.45, 0.50, 0.55, 0.60, 0.65):
            r = sample_phase(f"thrust={thrust:.2f}", 1.5,
                             lambda t=thrust: io.send_attitude_rates(0.0, 0.0, 0.0, t))
            report(r)
        print("  [OPERATOR] note at which thrust step the drone lifted / held "
              "altitude — that brackets control.att_rate.hover_thrust.", flush=True)

    for mode_key in args.modes:
        title, send = modes[mode_key]
        print(f"\n=== mode {mode_key}: {title} ===", flush=True)
        print("resetting sim + arming...", flush=True)
        io.sim_reset()
        time.sleep(2.0)
        io.arm()
        time.sleep(0.5)
        report(sample_phase("throttle-down handshake", HANDSHAKE_S,
                            lambda: io.send_attitude_rates(0.0, 0.0, 0.0, 0.0)))
        if mode_key == "D":
            run_mode_d()
        elif mode_key == "H":
            run_mode_h()
        else:
            report(sample_phase(title, MODE_S, send))
        print(f"  [OPERATOR] did the drone visibly move in mode {mode_key}? "
              f"did the THROTTLE DOWN overlay clear? note it.", flush=True)
        io.send_attitude_rates(0.0, 0.0, 0.0, 0.0)
        time.sleep(1.0)

    io.disarm()
    app.close()
    print("\ndone — record per-mode observations in notes.md", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
