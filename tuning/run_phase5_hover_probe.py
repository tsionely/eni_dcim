"""Phase 5 Windows hover telemetry probe.

This is mock-only and writes a compact summary under tuning/.
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from aigp.app import App, SimConfig
from aigp.core.params import ParamSet
from simtools.mock_sim import Gate, MockSim


OUT_DIR = ROOT / "tuning" / "phase5-hover-9fe3702"
RUNTIME_DIR = OUT_DIR / "runtime"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if RUNTIME_DIR.exists():
        shutil.rmtree(RUNTIME_DIR)
    cfg = SimConfig(
        mavlink_ip="127.0.0.1", mavlink_port=24650,
        heartbeat_timeout_s=10.0,
        vision_ip="127.0.0.1", vision_port=25700,
        control_hz=250, planner_div=5, timesync_hz=10.0,
        log_dir=str(RUNTIME_DIR),
    )
    sim = MockSim(
        mav_addr=("127.0.0.1", 24650),
        video_addr=("127.0.0.1", 25700),
        gates=[Gate(pos=np.array([50.0, 0.0, -1.5]), travel_yaw=0.0)],
    )
    app: App | None = None
    try:
        sim.start()
        app = App(cfg)
        app.connect()
        params = ParamSet.load("config/params_default.json").patch({
            "safety.imu_stale_s": 0.25,
            "planner.search.yaw_rate_rps": 0.4,
            "perception.hsv.red1_sat_min": 255,
        })
        result = app.fly(params, max_duration_s=6.0)
        app.mavlink.sim_reset()
        time.sleep(0.5)
    finally:
        if app is not None:
            app.close()
        sim.stop()

    summary = {
        "aborted": result["aborted"],
        "abort_reason": result["abort_reason"],
        "gates_passed": result["gates_passed"],
        "env_hits": result["env_hits"],
        "gate_clips": result["gate_clips"],
        "loop_stats": result["loop_stats"],
    }
    (OUT_DIR / "hover-overrun-telemetry.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    if RUNTIME_DIR.exists():
        shutil.rmtree(RUNTIME_DIR)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
