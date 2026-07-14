from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from aigp.app import App, SimConfig
from aigp.core.params import ParamSet
from aigp.learning.campaign import Campaign
from aigp.learning.optimizers import CEM
from aigp.learning.results_db import ResultsDB
from simtools.mock_sim import MockSim

TRIM_BOUNDS = {
    "control.att_rate.vel_i": (0.02, 0.3),
    "control.att_rate.vz_i": (0.1, 0.8),
    "estimation.vision_vel_blend": (0.1, 0.6),
    "estimation.vel_leak": (0.02, 0.15),
}


def main() -> int:
    cfg = SimConfig.load(ROOT / "tuning" / "campaign-configs" / "low-load-trim-cem.json")
    params = ParamSet.load(ROOT / "config" / "params_default.json")

    cfg.control_hz = 125
    cfg.record_vision = False

    sim = MockSim(
        mav_addr=("127.0.0.1", cfg.mavlink_port),
        video_addr=("127.0.0.1", cfg.vision_port),
        video_hz=12.0,
        imu_hz=100.0,
        physics_hz=125.0,
        image_size=(320, 180),
    )
    sim.start()

    app = App(cfg)
    app.connect()
    db = ResultsDB(Path(cfg.log_dir) / "results.sqlite")
    campaign_id = datetime.now(timezone.utc).strftime("trim-camp-%Y%m%dT%H%M%S")
    optimizer = CEM(TRIM_BOUNDS)
    campaign = Campaign(
        campaign_id,
        params,
        optimizer,
        db,
        fly_fn=lambda p: app.reset_and_fly(p, max_duration_s=120.0),
    )
    try:
        best = campaign.run(40)
        if best is not None:
            best_params, best_score = best
            print(f"[trim] best score={best_score:.6f} params={best_params}", flush=True)
            patch = " ".join(f"--patch {k}={v}" for k, v in best_params.items())
            print(f"[trim] sakana_patch {patch}", flush=True)
    finally:
        app.close()
        db.close()
        sim.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())