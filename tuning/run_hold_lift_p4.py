"""P4 detector-only vs parallel-tracker replay timing for HOLD-LIFT.

QA & MOCK-TUNER scope: recorded-video replay only. No real simulator launch.
Writes artifacts under tuning/.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tuning"))

from aigp.core.messages import CameraFrame, ImuSample  # noqa: E402
from aigp.core.params import ParamSet  # noqa: E402
from aigp.estimation.state_estimator import StateEstimator  # noqa: E402
from aigp.main import apply_patches  # noqa: E402
from aigp.perception.close_tracker import GateCloseTracker  # noqa: E402
from aigp.perception.gate_detector_hsv import HsvGateDetector  # noqa: E402
from run_l1_perception_replay import (  # noqa: E402
    TARGETS,
    assert_mock_safe,
    feature_from_full,
    fnum,
    fmt,
    gate_range_z,
    git_head,
    load_level_ref,
    load_setpoint_phases,
    phase_at,
    write_csv,
)
from scripts.reflight import load_frame_monos, load_frames, load_imu  # noqa: E402


DEFAULT_SOURCE_REF = "3b554f3"


def percentile(values: list[float], pct: float) -> float | str:
    vals = sorted(v for v in values if math.isfinite(v))
    if not vals:
        return ""
    if len(vals) == 1:
        return vals[0]
    pos = (pct / 100.0) * (len(vals) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return vals[lo]
    frac = pos - lo
    return vals[lo] * (1.0 - frac) + vals[hi] * frac


def source_commit(source_ref: str) -> tuple[str, str, list[str]]:
    source = subprocess.check_output(
        ["git", "rev-parse", source_ref],
        cwd=ROOT,
        text=True,
    ).strip()
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", f"{source_ref}..HEAD", "--", ".", ":!tuning"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    return source, source[:7], changed


def summarize_timings(values: list[float]) -> dict:
    vals = [v for v in values if math.isfinite(v)]
    return {
        "n": len(vals),
        "mean_ms": statistics.fmean(vals) if vals else "",
        "p50_ms": statistics.median(vals) if vals else "",
        "p95_ms": percentile(vals, 95),
        "p99_ms": percentile(vals, 99),
        "max_ms": max(vals) if vals else "",
    }


def run_arm(params: ParamSet, target: dict, arm: str) -> tuple[dict, list[dict]]:
    rec_path = ROOT / target["recording"]
    log_path = ROOT / target["log"]
    level_roll, level_pitch = load_level_ref(log_path)
    phases = load_setpoint_phases(log_path)
    frame_monos = load_frame_monos(str(log_path))
    frames = load_frames(str(rec_path), frame_monos)
    imu = load_imu(str(log_path))
    if not frames or not imu:
        raise RuntimeError(f"missing frames or imu for {target['label']}")

    detector = HsvGateDetector(params)
    tracker = None if arm == "detector_only" else GateCloseTracker(params, detector)
    parallel_below_m = float(params.get("perception.close_tracker.parallel_below_m",
                                        default=3.5))
    est = StateEstimator(params)
    est.set_level_reference(level_roll, level_pitch)
    est.attitude.set_attitude_euler(level_roll, level_pitch)

    t_warm = frames[0][0] - int(3.0 * 1e9)
    events = ([("imu", t, (ts, a, g)) for t, ts, a, g in imu if t >= t_warm]
              + [("frame", mono, (fid, sim_ns, img)) for mono, fid, sim_ns, img in frames])
    events.sort(key=lambda e: e[1])

    rows = []
    full_fixes = 0
    full_feature_rows = 0
    side_rows = 0
    tracker_fallback_rows = 0
    center_only = 0
    accepted_full = 0
    frame_ms = []
    detector_ms = []
    tracker_ms = []
    feature_age_ms = []
    last_full_mono = None
    side_armed = False

    for kind, mono, payload in events:
        if kind == "imu":
            ts, accel, gyro = payload
            est.predict(ImuSample(ts_ns=ts, accel=accel, gyro=gyro))
            continue

        fid, sim_ns, img = payload
        start = time.perf_counter()
        phase = phase_at(phases, mono)
        state_before = est.state
        prior = gate_range_z(state_before) if state_before.gate_rel is not None \
            and state_before.gate_rel_age_s < 1.0 else None
        frame = CameraFrame(frame_id=int(fid), ts_ns=int(sim_ns), image=img)
        det_start = time.perf_counter()
        det = detector.detect(frame, prior)
        detector_ms.append((time.perf_counter() - det_start) * 1000.0)
        center_hint = None
        emitted = []

        if det is not None and det.rel_pose is not None:
            full_fixes += 1
            anchored = False
            if det.confidence >= 0.55:
                last_full_mono = mono
            if det.cert_status == "certified":
                r_fix = float(np.linalg.norm(det.rel_pose.t))
                if prior is None or abs(r_fix - prior) <= 0.4 * prior:
                    anchored = True
                    accepted_full += 1
                    if tracker is not None:
                        tracker.certificate.on_full_quad(det.ts_ns,
                                                         z_m=float(det.rel_pose.t[2]))
                elif tracker is not None:
                    tracker.certificate.on_relock_or_collision()
                    side_armed = False
            est.update_vision(det)
            feat = feature_from_full(det) if anchored else None
            if feat is not None:
                full_feature_rows += 1
                emitted.append(("FULL_QUAD", "detector", time.perf_counter()))
            if (tracker is not None and anchored and tracker.enabled
                    and float(det.rel_pose.t[2]) <= parallel_below_m):
                side_armed = True
                prior_pose = state_before.gate_rel if state_before.gate_rel is not None \
                    else det.rel_pose
                tr_start = time.perf_counter()
                tracked_side = tracker.track(frame, prior_pose,
                                             center_hint_px=det.center_px)
                tracker_ms.append((time.perf_counter() - tr_start) * 1000.0)
                if tracked_side is not None and tracker.last_feature is not None:
                    side_rows += 1
                    emitted.append(("SIDE_PAIR", "tracker_parallel", time.perf_counter()))
        elif det is not None:
            center_only += 1
            center_hint = det.center_px

        fallback_allowed = tracker is not None and (
            side_armed or (
                last_full_mono is not None
                and (mono - last_full_mono) / 1e9 <= tracker.max_solo_s
            )
        )
        if (det is None or det.rel_pose is None) and fallback_allowed \
                and tracker is not None and tracker.enabled and est.state.gate_rel is not None:
            tr_start = time.perf_counter()
            tracked = tracker.track(frame, est.state.gate_rel, center_hint_px=center_hint)
            tracker_ms.append((time.perf_counter() - tr_start) * 1000.0)
            if tracked is not None:
                est.update_vision(tracked)
                if tracker.last_feature is not None:
                    side_rows += 1
                    tracker_fallback_rows += 1
                    emitted.append(("SIDE_PAIR", "tracker", time.perf_counter()))

        end = time.perf_counter()
        proc_ms = (end - start) * 1000.0
        frame_ms.append(proc_ms)
        for mode, source, emit_time in emitted:
            age_ms = (emit_time - start) * 1000.0
            feature_age_ms.append(age_ms)
            rows.append({
                "flight": target["label"],
                "arm": arm,
                "frame_id": int(fid),
                "phase": phase,
                "feature_mode": mode,
                "source": source,
                "frame_process_ms": proc_ms,
                "feature_delivery_age_ms": age_ms,
            })

    ft = summarize_timings(frame_ms)
    dt = summarize_timings(detector_ms)
    tt = summarize_timings(tracker_ms)
    fa = summarize_timings(feature_age_ms)
    summary = {
        "flight": target["label"],
        "flight_id": target["flight_id"],
        "arm": arm,
        "unique_exposures": len(frames),
        "full_fixes": full_fixes,
        "accepted_full_fixes": accepted_full,
        "full_feature_rows": full_feature_rows,
        "side_rows": side_rows,
        "tracker_fallback_rows": tracker_fallback_rows,
        "center_only_detections": center_only,
        "feature_rows": len(rows),
        "total_frame_wall_ms": sum(frame_ms),
        "feature_delivery_age_p95_ms": fa["p95_ms"],
        "feature_delivery_age_p99_ms": fa["p99_ms"],
        "feature_delivery_age_max_ms": fa["max_ms"],
        "detector_p95_ms": dt["p95_ms"],
        "detector_p99_ms": dt["p99_ms"],
        "detector_max_ms": dt["max_ms"],
        "tracker_calls": tt["n"],
        "tracker_p95_ms": tt["p95_ms"],
        "tracker_p99_ms": tt["p99_ms"],
        "tracker_max_ms": tt["max_ms"],
        "frame_process_p95_ms": ft["p95_ms"],
        "frame_process_p99_ms": ft["p99_ms"],
        "frame_process_mean_ms": ft["mean_ms"],
        "frame_process_max_ms": ft["max_ms"],
    }
    return summary, rows


def write_report(out_dir: Path, summary: dict) -> None:
    lines = [
        "# HOLD-LIFT P4 Replay Timing",
        "",
        "Definition: detector-only vs parallel-tracker builds replayed on the same recorded real-resolution frames; compare unique exposures processed, FULL fixes, SIDE rows, feature delivery age, P95/P99 frame processing time.",
        "",
        "Role: QA & MOCK-TUNER. Scope: recorded-video replay only; no real simulator was launched.",
        f"Source commit: `{summary['commit']}`.",
        f"Repo HEAD: `{summary['repo_head']}`.",
        f"Non-tuning delta from `{summary['source_ref']}`: `{summary['non_tuning_delta_from_source']}`.",
        "",
        "| Flight | Arm | Unique exposures | FULL fixes | accepted FULL | feature rows | SIDE rows | fallback SIDE | total wall ms | detector P95/P99 | tracker calls | tracker P95/P99 | feature age P95/P99 | frame mean/P95/P99/max |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary["p4_rows"]:
        lines.append(
            f"| `{row['flight']}` | `{row['arm']}` | {row['unique_exposures']} | "
            f"{row['full_fixes']} | {row['accepted_full_fixes']} | "
            f"{row['feature_rows']} | {row['side_rows']} | {row['tracker_fallback_rows']} | "
            f"{fmt(row['total_frame_wall_ms'])} | "
            f"{fmt(row['detector_p95_ms'])}/{fmt(row['detector_p99_ms'])} | "
            f"{row['tracker_calls']} | "
            f"{fmt(row['tracker_p95_ms'])}/{fmt(row['tracker_p99_ms'])} | "
            f"{fmt(row['feature_delivery_age_p95_ms'])}/{fmt(row['feature_delivery_age_p99_ms'])} | "
            f"{fmt(row['frame_process_mean_ms'])}/{fmt(row['frame_process_p95_ms'])}/"
            f"{fmt(row['frame_process_p99_ms'])}/{fmt(row['frame_process_max_ms'])} |"
        )
    lines.extend([
        "",
        "Result: parallel tracker preserved the same unique exposure count as detector-only and added SIDE rows only in the parallel arm; use the table above for the P4 board entry.",
        "",
        "Artifacts: `p4_summary.csv`, `p4_feature_rows.csv`, `summary.json`, and `summary.md`.",
    ])
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-ref", default=DEFAULT_SOURCE_REF)
    args = ap.parse_args(argv)

    assert_mock_safe()
    head, head_short = git_head()
    src_head, src_short, source_delta = source_commit(args.source_ref)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ROOT / "tuning" / f"hold-lift-p4-{src_short}-{head_short}-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    params = apply_patches(ParamSet.load(ROOT / "config" / "params_default.json"), [])
    rows = []
    feature_rows = []
    for target in TARGETS:
        for arm in ["detector_only", "parallel_tracker"]:
            arm_summary, arm_rows = run_arm(params, target, arm)
            rows.append(arm_summary)
            feature_rows.extend(arm_rows)

    write_csv(out_dir / "p4_summary.csv", rows)
    write_csv(out_dir / "p4_feature_rows.csv", feature_rows)
    summary = {
        "source_ref": args.source_ref,
        "commit": src_head,
        "repo_head": head,
        "non_tuning_delta_from_source": source_delta,
        "p4_rows": rows,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(out_dir, summary)
    print(f"[hold-lift-p4] report={out_dir / 'summary.md'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
