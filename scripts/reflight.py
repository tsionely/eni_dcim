"""Reflight: run the estimator+detector offline over a REAL recording.

The development loop moved here (2026-07-16): live cycles produce 3 noisy
samples in hours, while the fixtures hold dozens of real close approaches.
Feed a recording slice (frames) + its flight.jsonl (imu) through any
candidate build and measure what actually decides passes:

  - fix coverage vs range (where does the detector go blind?)
  - state error at the crossing (dead-reckoned belief vs event ground truth)
  - lock stability (accepted/rejected fixes, relocks)

Usage:
  python scripts/reflight.py --slice fixtures/<...>.aigprec \
      --log fixtures/<...>-flight.jsonl [--patch KEY=VALUE ...]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
import numpy as np

from aigp.core.messages import CameraFrame, ImuSample
from aigp.core.params import ParamSet
from aigp.estimation.state_estimator import StateEstimator
from aigp.io.udp_tap import read_recording
from aigp.io.vision_rx import ChunkAssembler
from aigp.perception.close_tracker import GateCloseTracker
from aigp.perception.gate_detector_hsv import HsvGateDetector
from aigp.main import apply_patches


def load_imu(log_path: str):
    imu = []
    for line in open(log_path):
        d = json.loads(line)
        if d["topic"] == "imu":
            m = d["data"]
            imu.append((d["mono_ns"], m["ts_ns"], np.array(m["accel"]),
                        np.array(m["gyro"])))
    return imu


def load_frame_monos(log_path: str) -> dict[int, int]:
    """frame_id -> recorder mono_ns, from the flight log's frame topic.

    The slice tool rewrites the recording's own mono timestamps (observed:
    every packet stamped mono_ns=1), which silently front-loaded all frames
    before the first IMU sample in the merged replay. The flight log keeps
    the true arrival time of every frame, so it is the ordering authority.
    """
    monos: dict[int, int] = {}
    for line in open(log_path):
        d = json.loads(line)
        if d["topic"] == "frame":
            monos.setdefault(int(d["data"]["frame_id"]), int(d["mono_ns"]))
    return monos


def load_frames(slice_path: str, frame_monos: dict[int, int] | None = None):
    """Decode unique frames; timestamp from the flight log when available.

    Slices also duplicate payload packets (observed: each frame decoded ~8
    times) — dedupe by frame_id, keep the first decode.
    """
    frames = []
    seen: set[int] = set()
    asm = ChunkAssembler()
    for _, mono_ns, payload in read_recording(slice_path):
        done = asm.feed(payload)
        if done:
            frame_id, sim_ns, jpeg = done
            if frame_id in seen:
                continue
            img = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                continue
            seen.add(frame_id)
            if frame_monos is not None and frame_id in frame_monos:
                mono_ns = frame_monos[frame_id]
            frames.append((mono_ns, frame_id, sim_ns, img))
    frames.sort(key=lambda f: f[0])
    return frames


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--slice", required=True, action="append",
                    help="repeatable: consecutive slices of the SAME flight "
                         "are chained on the log timeline (warm-start the "
                         "estimator with the earlier slice's vision)")
    ap.add_argument("--log", required=True)
    ap.add_argument("--params", default="config/params_default.json")
    ap.add_argument("--patch", action="append", default=[])
    ap.add_argument("--blind-last-s", type=float, default=0.0,
                    help="pseudo-dropout: hide vision from the estimator for "
                         "the final T seconds and report dead-reckoning error "
                         "vs what the detector actually measured")
    ap.add_argument("--imu-warmup-s", type=float, default=3.0,
                    help="IMU history fed before the first frame; the flight "
                         "log spans the whole flight and replaying a cold "
                         "estimator through minutes of IMU-only corrupts the "
                         "state the slice window is judged on")
    ap.add_argument("--no-tracker", action="store_true",
                    help="disable the GateCloseTracker (A/B baseline)")
    args = ap.parse_args(argv)

    params = apply_patches(ParamSet.load(args.params), args.patch)
    detector = HsvGateDetector(params)
    est = StateEstimator(params)
    tracker = None if args.no_tracker else GateCloseTracker(params, detector)

    imu = load_imu(args.log)
    monos = load_frame_monos(args.log)
    frames = []
    seen_ids: set[int] = set()
    for slc in args.slice:
        for f in load_frames(slc, monos):
            if f[1] not in seen_ids:
                seen_ids.add(f[1])
                frames.append(f)
    frames.sort(key=lambda f: f[0])
    print(f"imu samples: {len(imu)}, unique frames: {len(frames)}")
    if not frames or not imu:
        return 1
    span = (frames[-1][0] - frames[0][0]) / 1e9
    print(f"frame mono span: {span:.2f}s "
          f"(ids {frames[0][1]}..{frames[-1][1]})")

    # Merge on the recorder/log mono timeline and replay in order.
    t_warm = frames[0][0] - int(args.imu_warmup_s * 1e9)
    events = ([("imu", t, (ts, a, g)) for t, ts, a, g in imu if t >= t_warm]
              + [("frame", t, (fid, sim_ns, img)) for t, fid, sim_ns, img in frames])
    events.sort(key=lambda e: e[1])

    fix_ranges = []          # ranges at which the detector produced a fix
    coverage = []            # (mono_s, range, accepted?) timeline
    blind = []               # (believed, measured) during the hidden window
    tracker_ranges = []      # ranges of close-tracker (partial-edge) fixes
    t0 = events[0][1]
    blind_from = frames[-1][0] - int(args.blind_last_s * 1e9)
    last_full_mono = None
    for kind, mono, payload in events:
        if kind == "imu":
            ts, a, g = payload
            est.predict(ImuSample(ts_ns=ts, accel=a, gyro=g))
        else:
            fid, sim_ns, img = payload
            cf = CameraFrame(frame_id=fid, ts_ns=sim_ns, image=img)
            prior = None
            gr = est.state.gate_rel
            if gr is not None and est.state.gate_rel_age_s < 1.0:
                prior = float(np.linalg.norm(gr.t))
            det = detector.detect(cf, prior)
            if det is None and tracker is not None and tracker.enabled \
                    and last_full_mono is not None \
                    and (mono - last_full_mono) / 1e9 <= tracker.max_solo_s \
                    and est.state.gate_rel is not None:
                det = tracker.track(cf, est.state.gate_rel)
                if det is not None and det.rel_pose is not None:
                    tracker_ranges.append(float(np.linalg.norm(det.rel_pose.t)))
            elif det is not None and det.confidence >= 0.55:
                last_full_mono = mono
                if tracker is not None and det.cert_status == "certified" \
                        and det.rel_pose is not None:
                    r_fix = float(np.linalg.norm(det.rel_pose.t))
                    if prior is None or abs(r_fix - prior) <= 0.4 * prior:
                        tracker.certificate.on_full_quad(det.ts_ns)
            if det is not None and det.rel_pose is not None:
                rng = float(np.linalg.norm(det.rel_pose.t))
                if args.blind_last_s > 0 and mono >= blind_from:
                    # Pseudo-dropout: the estimator flies on dead
                    # reckoning while we keep the detector's answer as
                    # the reference (advisory Q3 harness). Reference
                    # continuity filter: single-frame far-gate flickers
                    # (10-21m mid-approach) are not the locked target.
                    gr = est.state.gate_rel
                    ref_prev = blind[-1][1] if blind else (
                        float(np.linalg.norm(gr.t)) if gr is not None else None)
                    if gr is not None and ref_prev is not None \
                            and abs(rng - ref_prev) < 2.0:
                        blind.append((float(np.linalg.norm(gr.t)), rng,
                                      float(gr.t[1]), float(det.rel_pose.t[1])))
                    continue
                before = est._gate_rel_ts_ns
                est.update_vision(det)
                accepted = est._gate_rel_ts_ns != before
                fix_ranges.append(rng)
                coverage.append(((mono - t0) / 1e9, rng, accepted))

    fix_ranges = np.array(fix_ranges)
    print(f"\nfixes produced: {len(fix_ranges)}")
    if len(fix_ranges):
        for lo, hi in [(0.0, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 2.0),
                       (2.0, 3.0), (3.0, 5.0), (5.0, 100.0)]:
            n = int(((fix_ranges >= lo) & (fix_ranges < hi)).sum())
            print(f"  range {lo:4.1f}-{hi:4.1f}m: {n:5d} fixes")
        acc = sum(1 for _, _, a in coverage if a)
        print(f"accepted by lock: {acc}/{len(coverage)}")
        close = [r for _, r, _ in coverage if r < 3.0]
        if close:
            print(f"closest fix range: {min(close):.2f}m")
    if tracker_ranges:
        tr = np.array(tracker_ranges)
        print(f"close-tracker fixes: {len(tr)} "
              f"(range {tr.min():.2f}-{tr.max():.2f}m, median {np.median(tr):.2f})")
    if blind:
        errs = np.array([b - m for b, m, _, _ in blind])
        zerr = np.array([bz - mz for _, _, bz, mz in blind])
        print(f"\nblind window ({args.blind_last_s:.1f}s, {len(blind)} ref frames):"
              f" believed-minus-measured range error"
              f" end={errs[-1]:+.2f}m  max|.|={np.abs(errs).max():.2f}m")
        # Vertical channel (advisory-2 standing metric): camera-frame ty,
        # +down — the axis the last real flight actually died on.
        print(f"  vertical (ty) error end={zerr[-1]:+.2f}m "
              f" max|.|={np.abs(zerr).max():.2f}m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
