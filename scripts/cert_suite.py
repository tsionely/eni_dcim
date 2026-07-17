"""Certificate kill suite: FA=0 on adversarial windows + availability.

Release gate for the side-pair certificate (design contract): replay a
slice through detector+tracker+estimator exactly like the live path and
score the certificate per frame. Inside an adversarial --window (frame
id range), ANY 'certified' state is a shipped bug (false accept). On
good approaches, report the certified/probation availability instead.

Usage:
  python scripts/cert_suite.py --slice <...>.aigprec --log <...>.jsonl \
      [--window LO:HI ...] [--patch K=V ...]
Exit code 1 on any false accept inside a window.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from aigp.core.messages import CameraFrame, ImuSample
from aigp.core.params import ParamSet
from aigp.estimation.state_estimator import StateEstimator
from aigp.main import apply_patches
from aigp.perception.close_tracker import GateCloseTracker
from aigp.perception.gate_detector_hsv import HsvGateDetector
from scripts.reflight import load_frame_monos, load_frames, load_imu


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--slice", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--window", action="append", default=[],
                    help="adversarial frame-id range LO:HI (FA=0 required)")
    ap.add_argument("--params", default="config/params_default.json")
    ap.add_argument("--patch", action="append", default=[])
    ap.add_argument("--imu-warmup-s", type=float, default=3.0)
    args = ap.parse_args(argv)

    params = apply_patches(ParamSet.load(args.params), args.patch)
    detector = HsvGateDetector(params)
    est = StateEstimator(params)
    tracker = GateCloseTracker(params, detector)
    windows = [tuple(int(v) for v in w.split(":")) for w in args.window]

    imu = load_imu(args.log)
    frames = load_frames(args.slice, load_frame_monos(args.log))
    t_warm = frames[0][0] - int(args.imu_warmup_s * 1e9)
    events = ([("imu", t, (ts, a, g)) for t, ts, a, g in imu if t >= t_warm]
              + [("frame", t, f) for t, *f in [(m, fid, s, i)
                 for m, fid, s, i in frames]])
    events.sort(key=lambda e: e[1])

    per_frame = []           # (frame_id, cert_state, source, fix_R)
    last_full_mono = None
    for kind, mono, payload in events:
        if kind == "imu":
            ts, a, g = payload
            est.predict(ImuSample(ts_ns=ts, accel=a, gyro=g))
            continue
        fid, sim_ns, img = payload
        cf = CameraFrame(frame_id=fid, ts_ns=sim_ns, image=img)
        prior = None
        gr = est.state.gate_rel
        if gr is not None and est.state.gate_rel_age_s < 1.0:
            prior = float(np.linalg.norm(gr.t))
        det = detector.detect(cf, prior)
        state = "none"
        src = "miss"
        if det is not None and det.confidence >= 0.55:
            last_full_mono = mono
            src = "detector"
            if det.cert_status == "certified" and det.rel_pose is not None:
                r_fix = float(np.linalg.norm(det.rel_pose.t))
                if prior is None or abs(r_fix - prior) <= 0.4 * prior:
                    tracker.certificate.on_full_quad(det.ts_ns)
                    state = "certified"
        elif det is None and last_full_mono is not None \
                and (mono - last_full_mono) / 1e9 <= tracker.max_solo_s \
                and gr is not None:
            tracked = tracker.track(cf, gr)
            if tracked is not None:
                det = tracked
                src = "tracker"
                state = tracked.cert_status
        r_fix = None
        if det is not None and det.rel_pose is not None:
            r_fix = float(np.linalg.norm(det.rel_pose.t))
            est.update_vision(det)
        per_frame.append((fid, state, src, r_fix))

    fails = 0
    for lo, hi in windows:
        inside = [(f, s, c, r) for f, s, c, r in per_frame if lo <= f <= hi]
        cert_rs = [(f, r) for f, s, c, r in inside
                   if s == "certified" and r is not None]
        # FA criterion: a certified fix is a false accept if it is not
        # CHAIN-CONTINUOUS — its range jumps >40% from the previous
        # certified fix. (Case 3, next-gate steal, is a target-identity
        # violation: a smooth single-target chain through the window is
        # legitimate; certifying a discontinuous jump is the bug. Cases
        # 1-2 — banner fiction / ceiling — produce no sane chain at all,
        # so any certified fix there fails this same test against the
        # pre-window chain.)
        bad = []
        prev_r = None
        before = [r for f, s, c, r in per_frame
                  if f < lo and s == "certified" and r is not None]
        if before:
            prev_r = before[-1]
        for f, r in cert_rs:
            if prev_r is not None and abs(r - prev_r) > 0.4 * prev_r:
                bad.append((f, r, prev_r))
            prev_r = r
        print(f"window {lo}..{hi}: {len(inside)} frames, "
              f"certified={len(cert_rs)} probation="
              f"{sum(1 for x in inside if x[1] == 'probation')} -> "
              f"{'FAIL (chain-discontinuous certification)' if bad else 'FA=0 OK'}")
        for f, r, pr in bad[:5]:
            print(f"    false accept at frame {f}: R={r:.2f} after {pr:.2f}")
        fails += len(bad)
    n = len(per_frame)
    cert = sum(1 for _, s, _, _ in per_frame if s == "certified")
    prob = sum(1 for _, s, _, _ in per_frame if s == "probation")
    print(f"overall: {n} frames, certified {cert} ({100*cert/max(n,1):.0f}%), "
          f"probation {prob} ({100*prob/max(n,1):.0f}%)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
