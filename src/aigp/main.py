"""Entry point.

Use --patch KEY=VALUE (repeatable) to override ParamSet values per run
without editing config files — the sim-operator agent is not allowed to edit
config, but runtime experiments are fine.

    aigp --mode fly       one flight against the real sim (Windows machine)
    aigp --mode mock      one flight against the in-process mock sim
    aigp --mode campaign  N-flight tuning campaign (--sim mock|real)
    aigp --mode replay    run the detector over a recorded vision stream
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from aigp.app import App, SimConfig
from aigp.core.params import ParamSet


# Default tuning surface for campaigns: dot-key -> (low, high).
# Matches the att_rate backend (the interface the real sim honors).
DEFAULT_TUNE_BOUNDS = {
    "planner.approach.speed_far_mps": (1.5, 6.0),
    "planner.approach.speed_near_mps": (0.8, 3.0),
    "planner.approach.near_distance_m": (2.0, 8.0),
    "planner.commit.distance_m": (1.0, 3.5),
    "planner.commit.duration_s": (0.6, 2.0),
    "planner.commit.speed_mps": (1.5, 5.0),
    "control.att_rate.vel_p": (0.15, 0.6),
    "control.att_rate.vz_p": (0.4, 1.5),
    "control.att_rate.tilt_max_rad": (0.2, 0.6),
    "control.att_rate.hover_thrust": (0.35, 0.65),
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI-GP autonomous pilot")
    parser.add_argument("--mode", choices=["fly", "mock", "campaign", "replay"],
                        default="fly")
    parser.add_argument("--config", default="config/sim.json")
    parser.add_argument("--params", default="config/params_default.json")
    parser.add_argument("--max-duration", type=float, default=None,
                        help="safety cap on flight duration [s]")
    parser.add_argument("--flights", type=int, default=20,
                        help="campaign: number of flights")
    parser.add_argument("--optimizer", choices=["random", "cem", "cmaes"],
                        default="cem", help="campaign: optimizer")
    parser.add_argument("--sim", choices=["real", "mock"], default="real",
                        help="campaign: which sim to fly against")
    parser.add_argument("--recording", default=None,
                        help="replay: path to an .aigprec recording")
    parser.add_argument("--patch", action="append", default=[],
                        metavar="KEY=VALUE",
                        help="override a ParamSet value for this run, e.g. "
                             "--patch control.att_rate.rate_sign_pitch=-1 "
                             "(repeatable; numbers parsed automatically)")
    return parser.parse_args(argv)


def apply_patches(params: ParamSet, patches: list[str]) -> ParamSet:
    overrides = {}
    for item in patches:
        key, _, raw = item.partition("=")
        if not _:
            raise SystemExit(f"--patch needs KEY=VALUE, got: {item}")
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            value = raw
        overrides[key.strip()] = value
    if overrides:
        print(f"param overrides: {overrides}", flush=True)
        return params.patch(overrides)
    return params


def run_flight(cfg: SimConfig, params: ParamSet, max_duration: float | None) -> dict:
    app = App(cfg)
    app.connect()
    try:
        result = app.fly(params, max_duration_s=max_duration)
    finally:
        app.close()
    print(f"Flight result: {result}", flush=True)
    return result


def run_mock(cfg: SimConfig, params: ParamSet, max_duration: float | None) -> dict:
    from simtools.mock_sim import MockSim

    sim = MockSim(mav_addr=(cfg.mavlink_ip if cfg.mavlink_ip != "0.0.0.0" else "127.0.0.1",
                            cfg.mavlink_port),
                  video_addr=("127.0.0.1", cfg.vision_port))
    sim.start()
    try:
        return run_flight(cfg, params, max_duration or 60.0)
    finally:
        sim.stop()


def run_campaign(cfg: SimConfig, params: ParamSet, args: argparse.Namespace) -> None:
    from aigp.learning.campaign import Campaign
    from aigp.learning.optimizers import OPTIMIZERS
    from aigp.learning.results_db import ResultsDB

    sim = None
    if args.sim == "mock":
        from simtools.mock_sim import MockSim
        sim = MockSim(mav_addr=("127.0.0.1", cfg.mavlink_port),
                      video_addr=("127.0.0.1", cfg.vision_port))
        sim.start()

    app = App(cfg)
    app.connect()
    db = ResultsDB(Path(cfg.log_dir) / "results.sqlite")
    campaign_id = datetime.now(timezone.utc).strftime("camp-%Y%m%dT%H%M%S")
    optimizer = OPTIMIZERS[args.optimizer](DEFAULT_TUNE_BOUNDS)
    campaign = Campaign(
        campaign_id, params, optimizer, db,
        fly_fn=lambda p: app.reset_and_fly(p, max_duration_s=args.max_duration or 120.0),
    )
    try:
        campaign.run(args.flights)
    finally:
        app.close()
        db.close()
        if sim is not None:
            sim.stop()


def run_replay(params: ParamSet, recording: str) -> None:
    import cv2
    import numpy as np

    from aigp.core.messages import CameraFrame
    from aigp.io.udp_tap import STREAM_VISION, read_recording
    from aigp.io.vision_rx import ChunkAssembler
    from aigp.perception.gate_detector_hsv import HsvGateDetector

    detector = HsvGateDetector(params)
    assembler = ChunkAssembler()
    frames = detections = 0
    for _, stream_id, data in read_recording(recording):
        if stream_id != STREAM_VISION:
            continue
        done = assembler.feed(data)
        if done is None:
            continue
        frame_id, ts_ns, jpeg = done
        img = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue
        frames += 1
        det = detector.detect(CameraFrame(frame_id, ts_ns, img))
        if det is not None:
            detections += 1
    rate = 100.0 * detections / frames if frames else 0.0
    print(f"Replay: {frames} frames, {detections} detections ({rate:.1f}%)", flush=True)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cfg = SimConfig.load(args.config)
    params = apply_patches(ParamSet.load(args.params), args.patch)

    if args.mode == "fly":
        run_flight(cfg, params, args.max_duration)
    elif args.mode == "mock":
        run_mock(cfg, params, args.max_duration)
    elif args.mode == "campaign":
        run_campaign(cfg, params, args)
    elif args.mode == "replay":
        if not args.recording:
            print("--recording is required for replay mode", file=sys.stderr)
            return 2
        run_replay(params, args.recording)
    return 0


if __name__ == "__main__":
    sys.exit(main())
