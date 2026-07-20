"""Full-archive retroactive census + five-cluster diagnostics.

QA & MOCK-TUNER scope: replay/CSV only. This script refuses to run if the
real simulator lock or process is visible, and writes only under tuning/.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tuning"))

from aigp.core.messages import CameraFrame, ImuSample  # noqa: E402
from aigp.core.params import ParamSet  # noqa: E402
from aigp.estimation.state_estimator import StateEstimator  # noqa: E402
from aigp.io.udp_tap import read_recording  # noqa: E402
from aigp.io.vision_rx import ChunkAssembler  # noqa: E402
from aigp.main import apply_patches  # noqa: E402
from aigp.perception.close_tracker import GateCloseTracker  # noqa: E402
from aigp.perception.gate_detector_hsv import HsvGateDetector  # noqa: E402
from aigp.planning.vertical_owner import TERM_OWNER  # noqa: E402
from scripts.reflight import load_frame_monos, load_frames, load_imu  # noqa: E402
import archive_harvest_release_fit_v21 as archive_fit  # noqa: E402
from archive_harvest_release_fit_v21 import (  # noqa: E402
    AGE_BINS,
    MIN_RELEASE_CLUSTERS,
    SIGMA_A_GATE,
    build_forced_withhold_rows,
    certified_full,
    certified_side,
    cluster_balanced_coverage,
    cluster_bootstrap,
    fallback_bound,
    fit_mean_values,
    fit_release,
    flight_loao_sensitivity,
    forecast_pair,
    history_before,
    loao_sensitivity,
    percentile,
    pseudo_samples,
    regime_rows,
    rms,
    slope_rate,
)
from run_anchor_r26 import (  # noqa: E402
    CORRIDOR_M,
    attach_flight_signals,
    exact_pairs,
    full_observation_series,
    replay_anchor_trial,
    summarize_trial,
    terminal_command_update,
)
from run_l1_perception_replay import (  # noqa: E402
    assert_mock_safe,
    feature_e_meas,
    feature_from_full,
    fmt,
    fnum,
    gate_range_z,
    load_level_ref,
    load_setpoint_phases,
    phase_at,
    write_csv,
)


FID_RE = re.compile(r"^(20\d{6}T\d{6}-[0-9a-f]{8})")
FIXTURES = ROOT / "fixtures"
TASK_A_PREFIX = "taskA-full-archive-retro-census"
TASK_B_PREFIX = "taskB-five-cluster-DIAGNOSTIC"
APPROACH_GAP_S = 1.25
CLOSE_EPOCH_RANGE_M = 4.5
FULL_LEGAL_RANGE_M = 3.5
SIDE_MAINT_MIN_AGE_S = 0.10
SIDE_MAINT_MAX_AGE_S = 0.55
COMMAND_ACTIVE_MPS = 0.02
LEGAL_FIVE_IDS = [
    "20260720T071112-cd18c5fb",  # phase6l F2
    "20260720T071333-cd18c5fb",  # phase6l F4
    "20260720T071545-cd18c5fb",  # phase6l F6
    "20260720T134522-9aa0ef5c",  # metrology f2
    "20260720T135008-9aa0ef5c",  # metrology f3
]
P4_CLEARED_IDS = {
    # RESPONSE36/P4(d): HONEST RELOCK, cluster quarantine cleared.
    "20260720T071333-cd18c5fb": "CLEARED_HONEST_RELOCK",
}


def git_head() -> tuple[str, str]:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    return head, head[:7]


def read_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def flight_id_from_name(name: str) -> str | None:
    m = FID_RE.match(name)
    return m.group(1) if m else None


def era_from_dir(path: Path) -> str:
    m = re.search(r"(phase\d+[a-z]?)", path.name)
    return m.group(1) if m else "unknown"


def regime_from_dir(path: Path, fid: str | None = None) -> str:
    name = path.name.lower()
    if "metrology" in name:
        return "metrology"
    if "cohort-3" in name and fid:
        return "terminal_live" if fid.endswith("cd18c5fb") else "control"
    for token in [
        "terminal-live",
        "first-enable",
        "r-rate-ab",
        "rate-ab",
        "block-a",
        "cohort-2",
        "shadow",
        "vertical",
        "confirm",
        "aligned-dash",
    ]:
        if token in name:
            return token
    return "archive"


def first_frame_info(recording: Path) -> dict[str, Any]:
    asm = ChunkAssembler()
    seen = set()
    packets = 0
    for _, mono_ns, payload in read_recording(str(recording)):
        packets += 1
        done = asm.feed(payload)
        if not done:
            continue
        frame_id, sim_ns, jpeg = done
        if frame_id in seen:
            continue
        seen.add(frame_id)
        img = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue
        h, w = img.shape[:2]
        return {
            "frame_sample_ok": True,
            "frame_sample_id": int(frame_id),
            "frame_sample_mono_ns": int(mono_ns),
            "image_w": int(w),
            "image_h": int(h),
            "real_resolution": bool(w >= 640 and h >= 360),
            "recording_packets_scanned_for_sample": packets,
        }
    return {
        "frame_sample_ok": False,
        "frame_sample_id": "",
        "frame_sample_mono_ns": "",
        "image_w": "",
        "image_h": "",
        "real_resolution": False,
        "recording_packets_scanned_for_sample": packets,
    }


def imu_count(log: Path) -> int:
    count = 0
    for rec in read_jsonl(log):
        if rec.get("topic") == "imu":
            count += 1
    return count


def result_notes(path: Path, fid: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    result = path / f"{fid}-result.json"
    if result.exists():
        try:
            data = json.loads(result.read_text(encoding="utf-8"))
            for key in ["gates", "gates_passed", "score", "collision", "collisions", "success"]:
                if key in data:
                    out[key] = data[key]
        except json.JSONDecodeError:
            out["result_parse_error"] = True
    return out


def discover_targets(sample_frames: bool = True) -> tuple[list[dict], list[dict]]:
    eligibility_rows: list[dict] = []
    targets: list[dict] = []
    dirs = sorted([p for p in FIXTURES.iterdir() if p.is_dir()])
    for d in dirs:
        recordings_by_fid: dict[str, list[Path]] = defaultdict(list)
        for rec in sorted(d.glob("*.aigprec")):
            fid = flight_id_from_name(rec.name)
            if fid:
                recordings_by_fid[fid].append(rec)
        logs_by_fid = {}
        for log in sorted(d.glob("*-flight.jsonl")):
            fid = flight_id_from_name(log.name)
            if fid:
                logs_by_fid[fid] = log

        era = era_from_dir(d)
        if not recordings_by_fid:
            eligibility_rows.append({
                "dir": rel(d),
                "frames?": False,
                "IMU?": False,
                "era": era,
                "eligible_recordings": 0,
                "recording_count": 0,
                "flight_log_count": len(logs_by_fid),
                "notes": "excluded: no .aigprec recording files",
            })
            continue

        eligible_in_dir = 0
        dir_notes = []
        frame_sizes = []
        for fid, recs in sorted(recordings_by_fid.items()):
            log = logs_by_fid.get(fid)
            if log is None:
                dir_notes.append(f"{fid}: missing matching flight log")
                continue
            n_imu = imu_count(log)
            sample = first_frame_info(recs[0]) if sample_frames else {
                "frame_sample_ok": True,
                "image_w": "",
                "image_h": "",
                "real_resolution": True,
            }
            if sample.get("image_w") and sample.get("image_h"):
                frame_sizes.append(f"{sample['image_w']}x{sample['image_h']}")
            eligible = bool(sample["frame_sample_ok"] and sample["real_resolution"] and n_imu > 0)
            if eligible:
                eligible_in_dir += 1
                targets.append({
                    "label": f"A{len(targets) + 1:03d}",
                    "flight_id": fid,
                    "fixture_dir": d.name,
                    "fixture_path": rel(d),
                    "era": era,
                    "recording_regime": regime_from_dir(d, fid),
                    "recordings": [rel(r) for r in recs],
                    "recording": rel(recs[0]),
                    "log": rel(log),
                    "contact_offset_m": 0.162,
                    "metrology_only": "metrology" in d.name.lower(),
                    **result_notes(d, fid),
                })
            else:
                reason = []
                if not sample["frame_sample_ok"]:
                    reason.append("frame decode failed")
                if not sample["real_resolution"]:
                    reason.append(f"not real-resolution ({sample.get('image_w')}x{sample.get('image_h')})")
                if n_imu <= 0:
                    reason.append("no IMU samples")
                dir_notes.append(f"{fid}: excluded: {', '.join(reason)}")
        notes = "; ".join(dir_notes) if dir_notes else "eligible"
        eligibility_rows.append({
            "dir": rel(d),
            "frames?": eligible_in_dir > 0,
            "IMU?": any(imu_count(log) > 0 for log in logs_by_fid.values()) if logs_by_fid else False,
            "era": era,
            "eligible_recordings": eligible_in_dir,
            "recording_count": sum(len(v) for v in recordings_by_fid.values()),
            "flight_log_count": len(logs_by_fid),
            "frame_sizes_seen": ",".join(sorted(set(frame_sizes))),
            "notes": notes,
        })
    return targets, eligibility_rows


def load_frames_multi(recordings: list[str], frame_monos: dict[int, int]) -> list[tuple[int, int, int, Any]]:
    frames = []
    seen_ids: set[int] = set()
    for rec_rel in recordings:
        for item in load_frames(str(ROOT / rec_rel), frame_monos):
            mono, fid, sim_ns, img = item
            if fid in seen_ids:
                continue
            seen_ids.add(fid)
            frames.append((mono, fid, sim_ns, img))
    frames.sort(key=lambda f: f[0])
    return frames


def run_video_replay_multi(params: ParamSet, target: dict) -> tuple[list[dict], dict]:
    log_path = ROOT / target["log"]
    level_roll, level_pitch = load_level_ref(log_path)
    phases = load_setpoint_phases(log_path)
    frame_monos = load_frame_monos(str(log_path))
    frames = load_frames_multi(target["recordings"], frame_monos)
    imu = load_imu(str(log_path))
    if not frames or not imu:
        raise RuntimeError(f"missing frames or imu for {target['label']} {target['flight_id']}")

    detector = HsvGateDetector(params)
    tracker = GateCloseTracker(params, detector)
    parallel_below_m = float(params.get("perception.close_tracker.parallel_below_m", default=3.5))
    est = StateEstimator(params)
    est.set_level_reference(level_roll, level_pitch)
    est.attitude.set_attitude_euler(level_roll, level_pitch)

    t_warm = frames[0][0] - int(3.0 * 1e9)
    events = ([("imu", t, (ts, a, g)) for t, ts, a, g in imu if t >= t_warm]
              + [("frame", mono, (fid, sim_ns, img)) for mono, fid, sim_ns, img in frames])
    events.sort(key=lambda e: e[1])
    t0 = events[0][1]

    rows: list[dict] = []
    last_full_mono = None
    raw_detector_fixes = 0
    tracker_fixes = 0
    feature_side_rows = 0
    center_only = 0
    side_armed = False
    for kind, mono, payload in events:
        if kind == "imu":
            ts, accel, gyro = payload
            est.predict(ImuSample(ts_ns=ts, accel=accel, gyro=gyro))
            continue

        fid, sim_ns, img = payload
        phase = phase_at(phases, mono)
        state_before = est.state
        prior = gate_range_z(state_before) if state_before.gate_rel is not None \
            and state_before.gate_rel_age_s < 1.0 else None
        frame = CameraFrame(frame_id=int(fid), ts_ns=int(sim_ns), image=img)
        det = detector.detect(frame, prior)
        emitted: list[tuple[str, str, Any, Any]] = []
        center_hint = None

        if det is not None and det.rel_pose is not None:
            raw_detector_fixes += 1
            anchored = False
            if det.confidence >= 0.55:
                last_full_mono = mono
            if det.cert_status == "certified":
                r_fix = float(np.linalg.norm(det.rel_pose.t))
                if prior is None or abs(r_fix - prior) <= 0.4 * prior:
                    tracker.certificate.on_full_quad(det.ts_ns, z_m=float(det.rel_pose.t[2]))
                    anchored = True
                else:
                    tracker.certificate.on_relock_or_collision()
                    side_armed = False
            est.update_vision(det)
            feat = feature_from_full(det) if anchored else None
            if feat is not None:
                emitted.append(("feature", "detector", feat, det))
            if (anchored and tracker.enabled and det.rel_pose is not None
                    and float(det.rel_pose.t[2]) <= parallel_below_m):
                side_armed = True
                prior_pose = state_before.gate_rel if state_before.gate_rel is not None else det.rel_pose
                tracked_side = tracker.track(frame, prior_pose, center_hint_px=det.center_px)
                if tracked_side is not None and tracker.last_feature is not None:
                    feature_side_rows += 1
                    emitted.append(("feature_side", "tracker_parallel", tracker.last_feature, tracked_side))
        elif det is not None:
            center_only += 1
            center_hint = det.center_px

        fallback_allowed = side_armed or (
            last_full_mono is not None and (mono - last_full_mono) / 1e9 <= tracker.max_solo_s
        )
        if (det is None or det.rel_pose is None) and tracker.enabled \
                and fallback_allowed and est.state.gate_rel is not None:
            tracked = tracker.track(frame, est.state.gate_rel, center_hint_px=center_hint)
            if tracked is not None:
                tracker_fixes += 1
                est.update_vision(tracked)
                if tracker.last_feature is not None:
                    emitted.append(("feature", "tracker", tracker.last_feature, tracked))

        for topic, source, feat, used_det in emitted:
            state = est.state
            e_meas, reject = feature_e_meas(params, state, feat)
            r_z = gate_range_z(state)
            t = state.gate_rel.t if state.gate_rel is not None else np.array([math.nan] * 3)
            rows.append({
                "flight": target["label"],
                "flight_id": target["flight_id"],
                "fixture_dir": target.get("fixture_dir", ""),
                "fixture_path": target.get("fixture_path", ""),
                "era": target.get("era", ""),
                "recording_regime": target.get("recording_regime", ""),
                "metrology_only": bool(target.get("metrology_only", False)),
                "frame_id": int(fid),
                "mono_ns": int(mono),
                "t_rel_s": (int(mono) - t0) / 1e9,
                "feature_ts_ns": int(feat.ts_ns),
                "topic": topic,
                "phase": phase,
                "commit": phase == "commit",
                "source": source,
                "feature_mode": feat.mode,
                "cert_status": feat.cert_status,
                "range_z_m": r_z if r_z is not None else "",
                "range_norm_m": float(np.linalg.norm(t)) if np.isfinite(t).all() else "",
                "x_m": float(t[0]) if np.isfinite(t).all() else "",
                "y_down_m": float(t[1]) if np.isfinite(t).all() else "",
                "gate_age_s": state.gate_rel_age_s,
                "center_x_px": feat.center_x_px,
                "y_top_px": feat.y_top_px,
                "span_px": feat.span_px,
                "span_x_range": (feat.span_px * r_z if r_z is not None else ""),
                "e_meas": e_meas if e_meas is not None else "",
                "e_reject": reject,
                "level_pitch_rad": state.level_pitch,
                "level_roll_rad": state.level_roll,
                "image_w": state.image_size[0] if state.image_size else "",
                "image_h": state.image_size[1] if state.image_size else "",
                "det_confidence": getattr(used_det, "confidence", ""),
                "det_cert_status": getattr(used_det, "cert_status", ""),
            })

    meta = {
        "flight": target["label"],
        "flight_id": target["flight_id"],
        "fixture_dir": target.get("fixture_dir", ""),
        "fixture_path": target.get("fixture_path", ""),
        "era": target.get("era", ""),
        "recording_regime": target.get("recording_regime", ""),
        "recordings": "|".join(target["recordings"]),
        "log": target["log"],
        "frames": len(frames),
        "imu_samples": len(imu),
        "raw_detector_fixes": raw_detector_fixes,
        "tracker_fixes": tracker_fixes,
        "feature_side_rows": feature_side_rows,
        "center_only_detections": center_only,
        "feature_rows": len(rows),
        "level_roll": level_roll,
        "level_pitch": level_pitch,
    }
    return rows, meta


def split_segments(rows: list[dict]) -> list[list[dict]]:
    close_rows = [
        r for r in rows
        if fnum(r.get("range_z_m")) is not None
        and float(r["range_z_m"]) <= CLOSE_EPOCH_RANGE_M
    ]
    close_rows.sort(key=lambda r: float(r["t_rel_s"]))
    if not close_rows:
        return []
    segments = [[close_rows[0]]]
    for row in close_rows[1:]:
        dt = float(row["t_rel_s"]) - float(segments[-1][-1]["t_rel_s"])
        if dt > APPROACH_GAP_S:
            segments.append([row])
        else:
            segments[-1].append(row)
    return segments


def segment_bounds(seg: list[dict]) -> tuple[float, float]:
    return min(float(r["t_rel_s"]) for r in seg), max(float(r["t_rel_s"]) for r in seg)


def approach_diagnostics_for_flight(rows: list[dict], meta: dict) -> tuple[list[dict], list[dict]]:
    diagnostics: list[dict] = []
    clusters: list[dict] = []
    segments = split_segments(rows)
    if not segments:
        diagnostics.append({
            "flight": meta["flight"],
            "flight_id": meta["flight_id"],
            "fixture_dir": meta.get("fixture_dir", ""),
            "era": meta.get("era", ""),
            "recording_regime": meta.get("recording_regime", ""),
            "approach_id": f"{meta['flight_id']}:NO_CLOSE_EPOCH",
            "cluster_ok": False,
            "failure_reason": "NO_CLOSE_FEATURE_EPOCH_LE4P5",
            "notes": "no current-perception feature row at range_z<=4.5m",
        })
        return diagnostics, clusters

    for idx, seg in enumerate(segments, start=1):
        t0, t1 = segment_bounds(seg)
        app_rows = [
            r for r in rows
            if t0 - 0.25 <= float(r["t_rel_s"]) <= t1 + 0.75
        ]
        full_all = certified_full(app_rows)
        full_below = [r for r in full_all if fnum(r.get("range_z_m")) is not None
                      and float(r["range_z_m"]) <= FULL_LEGAL_RANGE_M]
        full_ok = [
            r for r in full_below
            if fnum(r.get("e_meas")) is not None and r.get("e_reject") == "ok"
        ]
        side_all = certified_side(app_rows)
        side_below = [r for r in side_all if fnum(r.get("range_z_m")) is not None
                      and float(r["range_z_m"]) <= FULL_LEGAL_RANGE_M]
        side_row_only = [r for r in app_rows if r.get("feature_mode") == "SIDE_PAIR_ROW_ONLY"]

        legal_cuts = []
        full_ok_sorted = sorted(full_ok, key=lambda r: int(r["feature_ts_ns"]))
        for cut in full_ok_sorted:
            ts_s = float(cut["feature_ts_ns"]) / 1e9
            rate, n_full, span_full, auth = slope_rate(history_before(full_ok_sorted, ts_s))
            if rate is not None and n_full >= 4:
                legal_cuts.append((cut, rate, n_full, span_full, auth))
        side_maintenance = []
        for cut, *_rest in legal_cuts:
            cut_s = float(cut["feature_ts_ns"]) / 1e9
            side_maintenance.extend([
                s for s in side_all
                if SIDE_MAINT_MIN_AGE_S <= float(s["feature_ts_ns"]) / 1e9 - cut_s <= SIDE_MAINT_MAX_AGE_S
            ])

        p4_status = P4_CLEARED_IDS.get(meta["flight_id"], "not_applicable")
        no_p4_contam = p4_status in ("not_applicable", "CLEARED_HONEST_RELOCK")
        valid_gate_lock = bool(full_ok and all(r.get("cert_status") == "certified" for r in full_ok))
        cluster_ok = bool(
            len(full_ok) >= 4
            and legal_cuts
            and len(side_below) >= 2
            and side_maintenance
            and valid_gate_lock
            and no_p4_contam
        )
        if cluster_ok:
            reason = "OK"
        elif not full_below:
            reason = "NO_CERTIFIED_FULL_BELOW_3P5"
        elif len(full_ok) < 4:
            reason = "FULL_BELOW_3P5_NOT_EZ_USABLE"
        elif not legal_cuts:
            reason = "NO_LEGAL_FULL_RATE_ANCHOR"
        elif len(side_below) < 2:
            reason = "NO_PARALLEL_SIDE_PRODUCTION"
        elif not side_maintenance:
            reason = "NO_LEGAL_SIDE_MAINTENANCE_INTERVAL"
        elif not valid_gate_lock:
            reason = "BAD_GATE_LOCK_PROVENANCE"
        elif not no_p4_contam:
            reason = "P4_IDENTITY_CONTAMINATION"
        else:
            reason = "SEGMENT_SPLIT_REJECTED"

        approach_id = f"{meta['flight_id']}:A{idx}"
        diag = {
            "flight": meta["flight"],
            "flight_id": meta["flight_id"],
            "fixture_dir": meta.get("fixture_dir", ""),
            "era": meta.get("era", ""),
            "recording_regime": meta.get("recording_regime", ""),
            "approach_id": approach_id,
            "cluster_ok": cluster_ok,
            "failure_reason": reason,
            "t_start_s": t0,
            "t_end_s": t1,
            "full_certified_below_3p5_any": len(full_below),
            "full_ok_below_3p5": len(full_ok),
            "full_depth_any_m": min([float(r["range_z_m"]) for r in full_below], default=""),
            "full_depth_ok_m": min([float(r["range_z_m"]) for r in full_ok], default=""),
            "legal_full_rate_anchor_count": len(legal_cuts),
            "parallel_side_certified_below_3p5": len(side_below),
            "side_pair_certified_total": len(side_all),
            "side_pair_row_only": len(side_row_only),
            "side_maintenance_rows": len(side_maintenance),
            "valid_gate_lock_provenance": valid_gate_lock,
            "p4_identity_status": p4_status,
            "no_p4_identity_contamination": no_p4_contam,
            "provenance_notes": (
                "current reflight emits FULL rows only after certified, prior-consistent lock; "
                f"P4 status={p4_status}"
            ),
        }
        diagnostics.append(diag)
        if cluster_ok:
            clusters.append({
                "approach_id": approach_id,
                "cluster_id": approach_id,
                "flight": meta["flight"],
                "flight_id": meta["flight_id"],
                "fixture_dir": meta.get("fixture_dir", ""),
                "era": meta.get("era", ""),
                "recording_regime": meta.get("recording_regime", ""),
                "provenance": "valid_gate_lock; no_p4_identity_contamination",
                "metrology_only": bool(meta.get("metrology_only", False)),
                "measurement_latch_mechanism_eligible": True,
                "term_command_regime_eligible": not bool(meta.get("metrology_only", False)),
                "t_start_s": max(0.0, t0 - 0.25),
                "t_end_s": t1 + 0.75,
                "full_rows_below_3p5": len(full_ok),
                "side_rows_est": len(side_maintenance),
                "full_depth_m": min(float(r["range_z_m"]) for r in full_ok),
                "est_rows": len(side_maintenance),
                "census_ok": True,
                "legal_cut_count": len(legal_cuts),
            })
    return diagnostics, clusters


def age_bin(age: float) -> str:
    for label, lo, hi in AGE_BINS:
        if lo <= age < hi:
            return label
    return "unknown"


def build_anchor_policy_samples(params: ParamSet, features: list[dict], approaches: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for app in approaches:
        app_rows = [r for r in features if r.get("flight_id") == app["flight_id"]
                    and float(app["t_start_s"]) <= float(r["t_rel_s"]) <= float(app["t_end_s"])]
        full_rows = certified_full(app_rows)
        side_rows = certified_side(app_rows)
        full_rows.sort(key=lambda r: int(r["feature_ts_ns"]))
        side_rows.sort(key=lambda r: int(r["feature_ts_ns"]))
        full_series = full_observation_series(app_rows)
        cut_rows = []
        for row in full_rows:
            if fnum(row.get("range_z_m")) is None or float(row["range_z_m"]) > FULL_LEGAL_RANGE_M:
                continue
            ts_s = float(row["feature_ts_ns"]) / 1e9
            rate, n_full, span_full, auth = slope_rate(history_before(full_rows, ts_s))
            if rate is None or n_full < 4:
                continue
            after = [s for s in side_rows if SIDE_MAINT_MIN_AGE_S <= float(s["feature_ts_ns"]) / 1e9 - ts_s <= SIDE_MAINT_MAX_AGE_S]
            if after:
                cut_rows.append((row, rate, n_full, span_full, auth))
        if len(cut_rows) > 10:
            step = max(1, len(cut_rows) // 10)
            cut_rows = cut_rows[::step][:10]
        for cut_idx, (cut, v_latch_true, n_full, span_full, auth) in enumerate(cut_rows, start=1):
            cut_ts_ns = int(cut["feature_ts_ns"])
            cut_ts_s = cut_ts_ns / 1e9
            old_anchor = auth * v_latch_true
            new_anchor = v_latch_true
            anchor_applied = fnum(cut.get("setpoint_vz_up_mps")) or 0.0
            delta_latch = old_anchor - v_latch_true
            cut_id = f"{app['approach_id']}:cut{cut_idx:02d}"
            prev_ff = None
            for side in side_rows:
                age = float(side["feature_ts_ns"]) / 1e9 - cut_ts_s
                if not (0.0 <= age <= SIDE_MAINT_MAX_AGE_S):
                    continue
                oracle_ref = withheld_full_ref(full_series, float(side["feature_ts_ns"]) / 1e9, cut_ts_ns)
                v_ref = fnum(oracle_ref.get("oracle_ref_vz_up_mps"))
                if v_ref is None:
                    continue
                applied_now = fnum(side.get("setpoint_vz_up_mps"))
                ff = (applied_now - anchor_applied) if applied_now is not None else 0.0
                e_side = fnum(side.get("e_meas"))
                old_hold = old_anchor + ff
                new_hold = new_anchor + ff
                step_delta = "" if prev_ff is None else ff - prev_ff
                prev_ff = ff
                if abs(old_hold) >= 0.57 or abs(new_hold) >= 0.57:
                    regime = "saturated"
                elif auth < 0.95:
                    regime = "authority_limited"
                elif step_delta != "" and step_delta > COMMAND_ACTIVE_MPS and ff < -COMMAND_ACTIVE_MPS:
                    regime = "down_up_triangular"
                elif step_delta != "" and step_delta < -COMMAND_ACTIVE_MPS and ff > COMMAND_ACTIVE_MPS:
                    regime = "up_down_triangular"
                elif ff > COMMAND_ACTIVE_MPS:
                    regime = "up"
                elif ff < -COMMAND_ACTIVE_MPS:
                    regime = "down"
                else:
                    regime = "flat_no_ff"
                base = {
                    "diagnostic_only": True,
                    "approach_id": app["approach_id"],
                    "cluster_id": app["approach_id"],
                    "flight": app["flight"],
                    "flight_id": app["flight_id"],
                    "fixture_dir": app.get("fixture_dir", ""),
                    "era": app.get("era", ""),
                    "recording_regime": app.get("recording_regime", ""),
                    "cut_id": cut_id,
                    "cut_frame_id": cut["frame_id"],
                    "frame_id": side["frame_id"],
                    "feature_ts_ns": side["feature_ts_ns"],
                    "age_s": age,
                    "age_bin": age_bin(age),
                    "range_z_m": side.get("range_z_m", ""),
                    "v_ref_oracle_mps": v_ref,
                    "v_latch_mps": v_latch_true,
                    "v_latch_true_mps": v_latch_true,
                    "v_full_raw_mps": v_latch_true,
                    "auth_at_latch": auth,
                    "v_anchor_old_mps": old_anchor,
                    "v_anchor_new_mps": new_anchor,
                    "delta_latch_mps": delta_latch,
                    "minus_delta_latch_mps": -delta_latch,
                    "n_full_at_latch": n_full,
                    "span_full_at_latch_s": span_full,
                    "rate_feed_forward_mps": ff,
                    "rate_feed_forward_step_mps": step_delta,
                    "command_regime": regime,
                    "e_meas": e_side if e_side is not None else "",
                    "old_hold_mps": old_hold,
                    "new_hold_mps": new_hold,
                    "r_v_old_mps": v_ref - old_hold,
                    "r_v_new_mps": v_ref - new_hold,
                    "old_minus_new_residual_mps": (v_ref - old_hold) - (v_ref - new_hold),
                    "residual_sign_convention": "r_v = v_ref_oracle - (anchor + feed_forward)",
                    **oracle_ref,
                }
                if e_side is not None:
                    base.update(forecast_pair(params, side, e_side, old_hold, new_hold))
                rows.append(base)
    return rows


def withheld_full_ref(full_series: list[dict], now_ts_s: float, cut_ts_ns: int) -> dict:
    from run_anchor_r26 import withheld_full_vz_ref

    return withheld_full_vz_ref(full_series, now_ts_s, cut_ts_ns)


def fit_policy_rows(samples: list[dict], key: str) -> dict:
    fit_rows = [{**r, "r_v_mps": r[key]} for r in samples if fnum(r.get(key)) is not None]
    if not fit_rows:
        return {"b0": "", "b1": "", "mean_fit_residual_rms_mps": ""}
    b0, b1 = fit_mean_values(fit_rows)
    vals = [float(r["r_v_mps"]) - (float(b0) + float(b1) * float(r["age_s"])) for r in fit_rows]
    return {"b0": b0, "b1": b1, "mean_fit_residual_rms_mps": rms(vals), "n": len(fit_rows)}


def pseudo_samples_both(features: list[dict], approaches: list[dict]) -> tuple[list[dict], list[dict]]:
    old_rows: list[dict] = []
    new_rows: list[dict] = []
    for app in approaches:
        app_rows = [r for r in features if r.get("flight_id") == app["flight_id"]
                    and float(app["t_start_s"]) <= float(r["t_rel_s"]) <= float(app["t_end_s"])]
        full = certified_full(app_rows)
        full.sort(key=lambda r: int(r["feature_ts_ns"]))
        for anchor in full:
            t0 = float(anchor["feature_ts_ns"]) / 1e9
            hist = history_before(full, t0, 0.35)
            v_true, n, span, auth = slope_rate(hist)
            if v_true is None:
                continue
            v_old = float(v_true) * float(auth)
            v_new = float(v_true)
            delta_latch = v_old - v_new
            for age in [0.10, 0.20, 0.30, 0.40, 0.50]:
                eval_pts = [
                    r for r in full
                    if t0 + age <= float(r["feature_ts_ns"]) / 1e9 <= t0 + age + 0.35
                ]
                if len(eval_pts) < 4:
                    continue
                v_ref, eval_n, eval_span, _eval_auth = slope_rate(eval_pts)
                if v_ref is None:
                    continue
                base = {
                    "diagnostic_only": True,
                    "approach_id": app["approach_id"],
                    "cluster_id": app["approach_id"],
                    "flight": app["flight"],
                    "flight_id": app["flight_id"],
                    "era": app.get("era", ""),
                    "recording_regime": app.get("recording_regime", ""),
                    "anchor_frame_id": anchor["frame_id"],
                    "age_s": age,
                    "age_bin": age_bin(age),
                    "v_ref_pseudo_full_mps": v_ref,
                    "v_latch_true_mps": v_true,
                    "auth_at_latch": auth,
                    "delta_latch_mps": delta_latch,
                    "n_full_at_latch": n,
                    "span_full_at_latch_s": span,
                    "eval_n": eval_n,
                    "eval_span_s": eval_span,
                }
                old_rows.append({
                    **base,
                    "anchor_policy": "old_policy_attenuated",
                    "v_anchor_mps": v_old,
                    "r_v_mps": float(v_ref) - v_old,
                    "rv2_m2ps2": (float(v_ref) - v_old) ** 2,
                })
                new_rows.append({
                    **base,
                    "anchor_policy": "new_unattenuated_shadow",
                    "v_anchor_mps": v_new,
                    "r_v_mps": float(v_ref) - v_new,
                    "rv2_m2ps2": (float(v_ref) - v_new) ** 2,
                })
    return old_rows, new_rows


def ols_slope_intercept(xs: list[float], ys: list[float]) -> tuple[float | str, float | str]:
    if len(xs) < 2:
        return "", ""
    xm = statistics.fmean(xs)
    ym = statistics.fmean(ys)
    den = sum((x - xm) ** 2 for x in xs)
    if den <= 1e-12:
        return "", ""
    slope = sum((x - xm) * (y - ym) for x, y in zip(xs, ys)) / den
    return slope, ym - slope * xm


def five_cluster_diagnostics(params: ParamSet, features: list[dict], clusters: list[dict],
                             diagnostics: list[dict], out_dir: Path) -> dict:
    selected = []
    by_fid = {c["flight_id"]: c for c in clusters}
    diagnostics_by_fid: dict[str, list[dict]] = defaultdict(list)
    for row in diagnostics:
        diagnostics_by_fid[row.get("flight_id", "")].append(row)
    missing = []
    for fid in LEGAL_FIVE_IDS:
        c = by_fid.get(fid)
        if c is not None:
            selected.append(c)
            continue
        candidates = diagnostics_by_fid.get(fid, [])
        if not candidates:
            missing.append(fid)
            continue
        best = max(
            candidates,
            key=lambda r: (
                int(float(r.get("full_ok_below_3p5") or 0)),
                int(float(r.get("parallel_side_certified_below_3p5") or 0)),
                int(float(r.get("legal_full_rate_anchor_count") or 0)),
            ),
        )
        selected.append({
            "approach_id": best["approach_id"],
            "cluster_id": best["approach_id"],
            "flight": best["flight"],
            "flight_id": best["flight_id"],
            "fixture_dir": best.get("fixture_dir", ""),
            "era": best.get("era", ""),
            "recording_regime": best.get("recording_regime", ""),
            "provenance": (
                "DIAGNOSTIC forced by RESPONSE38 legal-five list; "
                f"strict current maintenance predicate={best.get('failure_reason', '')}"
            ),
            "metrology_only": best.get("recording_regime") == "metrology",
            "measurement_latch_mechanism_eligible": True,
            "term_command_regime_eligible": best.get("recording_regime") != "metrology",
            "t_start_s": best.get("t_start_s", 0.0),
            "t_end_s": best.get("t_end_s", 0.0),
            "full_rows_below_3p5": best.get("full_ok_below_3p5", 0),
            "side_rows_est": best.get("side_maintenance_rows", 0),
            "full_depth_m": best.get("full_depth_ok_m", ""),
            "est_rows": best.get("side_maintenance_rows", 0),
            "census_ok": False,
            "legal_cut_count": best.get("legal_full_rate_anchor_count", 0),
            "diagnostic_forced_legal_five": True,
            "strict_failure_reason": best.get("failure_reason", ""),
        })
    write_csv(out_dir / "DIAGNOSTIC_selected_clusters.csv", selected)
    samples = build_anchor_policy_samples(params, features, selected)
    write_csv(out_dir / "DIAGNOSTIC_anchor_policy_samples.csv", samples)

    per_cluster = []
    for selected_cluster in selected:
        cid = selected_cluster["cluster_id"]
        group = [s for s in samples if s["cluster_id"] == cid]
        if not group:
            per_cluster.append({
                "diagnostic_only": True,
                "cluster_id": cid,
                "flight_id": selected_cluster["flight_id"],
                "era": selected_cluster.get("era", ""),
                "recording_regime": selected_cluster.get("recording_regime", ""),
                "n": 0,
                "auth_at_latch_median": "",
                "v_latch_median_mps": "",
                "delta_latch_median_mps": "",
                "minus_delta_latch_median_mps": "",
                "b0_old_mps": "",
                "b1_old_mps_per_s": "",
                "b0_new_mps": "",
                "b1_new_mps_per_s": "",
                "b0_old_minus_new_mps": "",
                "mechanism_error_mps": "",
                "high_auth_diff_should_be_near_zero": "",
                "strict_failure_reason": selected_cluster.get("strict_failure_reason", ""),
                "diagnostic_note": "no SIDE maintenance samples in current strict replay window",
            })
            continue
        old_fit = fit_policy_rows(group, "r_v_old_mps")
        new_fit = fit_policy_rows(group, "r_v_new_mps")
        delta_vals = [float(s["delta_latch_mps"]) for s in group if fnum(s.get("delta_latch_mps")) is not None]
        auth_vals = [float(s["auth_at_latch"]) for s in group if fnum(s.get("auth_at_latch")) is not None]
        b0_old = fnum(old_fit.get("b0"))
        b0_new = fnum(new_fit.get("b0"))
        minus_delta = -statistics.median(delta_vals) if delta_vals else ""
        diff = b0_old - b0_new if b0_old is not None and b0_new is not None else ""
        per_cluster.append({
            "diagnostic_only": True,
            "cluster_id": cid,
            "flight_id": group[0]["flight_id"],
            "era": group[0].get("era", ""),
            "recording_regime": group[0].get("recording_regime", ""),
            "n": len(group),
            "auth_at_latch_median": statistics.median(auth_vals) if auth_vals else "",
            "v_latch_median_mps": statistics.median([float(s["v_latch_mps"]) for s in group]) if group else "",
            "delta_latch_median_mps": statistics.median(delta_vals) if delta_vals else "",
            "minus_delta_latch_median_mps": minus_delta,
            "b0_old_mps": old_fit.get("b0", ""),
            "b1_old_mps_per_s": old_fit.get("b1", ""),
            "b0_new_mps": new_fit.get("b0", ""),
            "b1_new_mps_per_s": new_fit.get("b1", ""),
            "b0_old_minus_new_mps": diff,
            "mechanism_error_mps": (
                diff - minus_delta if fnum(diff) is not None and fnum(minus_delta) is not None else ""
            ),
            "high_auth_diff_should_be_near_zero": (
                abs(diff) if fnum(diff) is not None and auth_vals and statistics.median(auth_vals) >= 0.95 else ""
            ),
        })
    write_csv(out_dir / "DIAGNOSTIC_delta_latch_mechanism.csv", per_cluster)
    xs = [float(r["minus_delta_latch_median_mps"]) for r in per_cluster if fnum(r.get("minus_delta_latch_median_mps")) is not None and fnum(r.get("b0_old_minus_new_mps")) is not None]
    ys = [float(r["b0_old_minus_new_mps"]) for r in per_cluster if fnum(r.get("minus_delta_latch_median_mps")) is not None and fnum(r.get("b0_old_minus_new_mps")) is not None]
    slope, intercept = ols_slope_intercept(xs, ys)
    write_csv(out_dir / "DIAGNOSTIC_mechanism_regression.csv", [{
        "diagnostic_only": True,
        "x": "-delta_latch_median_mps",
        "y": "b0_old_minus_new_mps",
        "slope_target": 1.0,
        "intercept_target": 0.0,
        "slope": slope,
        "intercept": intercept,
        "n_clusters": len(xs),
    }])

    regime_rows_out = []
    for cid in sorted({s["cluster_id"] for s in samples}):
        for regime in sorted({s["command_regime"] for s in samples if s["cluster_id"] == cid}):
            group = [s for s in samples if s["cluster_id"] == cid and s["command_regime"] == regime]
            old_fit = fit_policy_rows(group, "r_v_old_mps")
            new_fit = fit_policy_rows(group, "r_v_new_mps")
            regime_rows_out.append({
                "diagnostic_only": True,
                "cluster_id": cid,
                "command_regime": regime,
                "n": len(group),
                "age_range_s": range_str([float(g["age_s"]) for g in group]),
                "b0_old_mps": old_fit.get("b0", ""),
                "b0_new_mps": new_fit.get("b0", ""),
                "b1_old_mps_per_s": old_fit.get("b1", ""),
                "b1_new_mps_per_s": new_fit.get("b1", ""),
            })
    write_csv(out_dir / "DIAGNOSTIC_b0_regime_invariance.csv", regime_rows_out)

    pseudo_old, pseudo_new = pseudo_samples_both(features, selected)
    pfit_old = fit_release(pseudo_old) if pseudo_old else {}
    pfit_new = fit_release(pseudo_new) if pseudo_new else {}
    write_csv(out_dir / "DIAGNOSTIC_pseudo_samples_old_anchor.csv", pseudo_old)
    write_csv(out_dir / "DIAGNOSTIC_pseudo_release_fit_old_anchor.csv", [pfit_old] if pfit_old else [])
    write_csv(out_dir / "DIAGNOSTIC_pseudo_samples_new_anchor.csv", pseudo_new)
    write_csv(out_dir / "DIAGNOSTIC_pseudo_release_fit_new_anchor.csv", [pfit_new] if pfit_new else [])

    command_rows = []
    for s in samples:
        command_rows.append({
            "diagnostic_only": True,
            "cluster_id": s["cluster_id"],
            "flight_id": s["flight_id"],
            "age_s": s["age_s"],
            "range_z_m": s.get("range_z_m", ""),
            "command_regime": s["command_regime"],
            "vz_cmd_old_mps": s.get("shadow_vz_cmd_old_mps", ""),
            "vz_cmd_new_mps": s.get("shadow_vz_cmd_new_mps", ""),
            "command_delta_mps": s.get("shadow_command_delta_mps", ""),
            "e_cross_old_m": s.get("shadow_e_cross_old_m", ""),
            "e_cross_new_m": s.get("shadow_e_cross_new_m", ""),
            "admission_proxy_old_abs_plus_guard_m": (
                abs(float(s["shadow_e_cross_old_m"])) + 0.06 if fnum(s.get("shadow_e_cross_old_m")) is not None else ""
            ),
            "admission_proxy_new_abs_plus_guard_m": (
                abs(float(s["shadow_e_cross_new_m"])) + 0.06 if fnum(s.get("shadow_e_cross_new_m")) is not None else ""
            ),
        })
    write_csv(out_dir / "DIAGNOSTIC_command_step_admission_old_vs_new.csv", command_rows)

    restamp = r26_1_shadow_restamp(params, out_dir)
    summary = {
        "diagnostic_only": True,
        "selected_cluster_count": len(selected),
        "missing_legal_five": missing,
        "sample_rows": len(samples),
        "mechanism_regression_slope": slope,
        "mechanism_regression_intercept": intercept,
        "r26_1_restamp_verdict": restamp.get("verdict", ""),
    }
    with (out_dir / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
    write_task_b_report(out_dir, summary, per_cluster)
    return summary


def range_str(vals: list[float]) -> str:
    clean = [v for v in vals if math.isfinite(v)]
    if not clean:
        return ""
    return f"{min(clean):.6f}..{max(clean):.6f}"


def r26_1_shadow_restamp(params: ParamSet, out_dir: Path) -> dict:
    target = {
        "label": "R26-1-F2",
        "flight_id": "20260720T071112-cd18c5fb",
        "fixture_dir": "20260720T071602-phase6l-cohort-3",
        "fixture_path": "fixtures/20260720T071602-phase6l-cohort-3",
        "era": "phase6l",
        "recording_regime": "terminal_live",
        "recordings": [
            "fixtures/20260720T071602-phase6l-cohort-3/20260720T071112-cd18c5fb_takeoff_to_end.aigprec"
        ],
        "recording": "fixtures/20260720T071602-phase6l-cohort-3/20260720T071112-cd18c5fb_takeoff_to_end.aigprec",
        "log": "fixtures/20260720T071602-phase6l-cohort-3/20260720T071112-cd18c5fb-flight.jsonl",
        "contact_offset_m": 0.162,
        "metrology_only": False,
    }
    rows, meta = run_video_replay_multi(params, target)
    attach_flight_signals(params, rows, target)
    write_csv(out_dir / "DIAGNOSTIC_r26_1_features_f2.csv", rows)
    full_series = full_observation_series(rows)
    pairs = exact_pairs(rows)
    side_sigmas = [float(p["residual_e_m"]) for p in pairs if fnum(p.get("residual_e_m")) is not None]
    side_sigma_e = max(0.038, float(np.std(side_sigmas)) if side_sigmas else 0.038)
    baseline_rows, baseline_transitions = replay_anchor_trial(
        params, rows, "baseline_no_drop", None, side_sigma_e, full_series)
    captures = [r for r in baseline_rows if r.get("shadow_capture") and r.get("active_source") == "FULL_QUAD"]
    if not captures:
        summary = {"verdict": "FAIL_NO_FULL_FIRST_CAPTURE", "owner_term_side_rows": 0}
        write_csv(out_dir / "DIAGNOSTIC_r26_1_trial_summary.csv", [summary])
        return summary
    first_capture_ts = int(captures[0]["feature_ts_ns"])
    first_capture_range = float(captures[0]["range_z_m"])
    candidates = []
    for pair in pairs:
        ts = int(pair["feature_ts_ns"])
        rng = fnum(pair.get("range_z_m"))
        if ts > first_capture_ts and rng is not None and rng <= first_capture_range:
            candidates.append(pair)
    all_rows = list(baseline_rows)
    all_transitions = list(baseline_transitions)
    summaries = [summarize_trial(baseline_rows, baseline_transitions)]
    for pair in candidates:
        trial_rows, transitions = replay_anchor_trial(
            params, rows, f"anchor_drop_frame_{pair['frame_id']}",
            int(pair["feature_ts_ns"]), side_sigma_e, full_series)
        for tr in trial_rows:
            tr["candidate_frame_id"] = pair["frame_id"]
            tr["candidate_range_z_m"] = pair["range_z_m"]
            if tr.get("shadow_owner") == TERM_OWNER and tr.get("active_source") == "SIDE_PAIR":
                old_vz = fnum(tr.get("terminal_vz_up_mps"))
                raw = fnum(tr.get("rate_anchor_v_mps"))
                ff = fnum(tr.get("rate_feed_forward_mps")) or 0.0
                tr["shadow_forecast_note"] = "dual-read replay fields computed by current R26 harness"
                tr["shadow_vz_up_new_proxy_mps"] = tr.get("shadow_vz_up_new_mps", (raw + ff if raw is not None else ""))
        summary = summarize_trial(trial_rows, transitions)
        summary["candidate_frame_id"] = pair["frame_id"]
        summary["candidate_range_z_m"] = pair["range_z_m"]
        summaries.append(summary)
        all_rows.extend(trial_rows)
        all_transitions.extend(transitions)
    write_csv(out_dir / "DIAGNOSTIC_r26_1_anchor_trial_rows.csv", all_rows)
    write_csv(out_dir / "DIAGNOSTIC_r26_1_anchor_transitions.csv", all_transitions)
    write_csv(out_dir / "DIAGNOSTIC_r26_1_trial_summary.csv", summaries)
    legal = [r for r in summaries if str(r.get("trial", "")).startswith("anchor_drop_")
             and int(r.get("full_to_side_count") or 0) > 0]
    owner_side_rows = sum(int(r.get("owner_term_side_rows") or 0) for r in legal)
    side_caps = sum(int(r.get("side_shadow_capture_rows") or 0) for r in legal)
    scores = [float(r["side_admission_max"]) for r in legal if fnum(r.get("side_admission_max")) is not None]
    phase_changes = sum(int(r.get("phase_changed_rows") or 0) for r in legal)
    term_rows = [r for r in all_rows if r.get("shadow_owner") == TERM_OWNER]
    wrong_sign = 0
    step_beyond_slew = 0
    prev = None
    for row in term_rows:
        cmd = fnum(row.get("terminal_vz_up_mps"))
        ez = fnum(row.get("e_meas"))
        if cmd is not None and ez is not None and abs(ez) > 0.03 and cmd * ez < -1e-6:
            wrong_sign += 1
        if prev is not None and cmd is not None and abs(cmd - prev) > 0.08:
            step_beyond_slew += 1
        if cmd is not None:
            prev = cmd
    verdict = "PASS" if (
        legal and owner_side_rows > 0 and side_caps > 0 and scores
        and max(scores) <= CORRIDOR_M and phase_changes == 0
        and wrong_sign == 0 and step_beyond_slew == 0
    ) else "FAIL"
    summary = {
        "verdict": verdict,
        "first_capture_range_m": first_capture_range,
        "legal_trial_count": len(legal),
        "owner_term_side_rows": owner_side_rows,
        "side_shadow_capture_rows": side_caps,
        "max_admission_score": max(scores) if scores else "",
        "phase_changed_rows": phase_changes,
        "wrong_sign_command_rows": wrong_sign,
        "command_step_beyond_slew_rows": step_beyond_slew,
    }
    write_csv(out_dir / "DIAGNOSTIC_r26_1_restamp_verdict.csv", [summary])
    return summary


def write_task_a_report(out_dir: Path, summary: dict) -> None:
    lines = [
        "# TASK A - Full-Archive Retroactive Census",
        "",
        "Scope: replay/CSV only; no FlightSim/DCGame launch.",
        f"Repo HEAD: `{summary['repo_head']}`.",
        "",
        "## Eligibility First",
        "",
        f"- Fixture directories enumerated: `{summary['fixture_dirs_enumerated']}`.",
        f"- Eligible recordings: `{summary['eligible_recordings']}`.",
        "",
        "## Expanded Census",
        "",
        f"- Current-perception clusters found: `{summary['cluster_count']}`.",
        f"- Census verdict: `{summary['census_verdict']}`.",
        f"- Release fit run: `{summary['release_fit_run']}`.",
        "",
        "| failure_reason | rows |",
        "| --- | ---: |",
    ]
    for reason, n in summary["failure_reason_counts"].items():
        lines.append(f"| `{reason}` | {n} |")
    if summary.get("release"):
        rel = summary["release"]
        lines.extend([
            "",
            "## Release Fit v2.1",
            "",
            "| clusters | rows | point sigma_a | profile U95 | bootstrap U95 | U95 release | verdict |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | --- |",
            f"| {rel['n_clusters']} | {rel['n_rows']} | {fmt(rel['point_sigma_a_mps2'])} | "
            f"{fmt(rel['profile_u95_sigma_a_mps2'])} | {fmt(rel['cluster_bootstrap_u95_sigma_a_mps2'])} | "
            f"{fmt(rel['u95_release_sigma_a_mps2'])} | `{rel['verdict']}` |",
        ])
    else:
        lines.append("")
        lines.append("Stopped before release fitting because the expanded census stayed below six independent approaches.")
    lines.extend([
        "",
        "Artifacts: `eligibility_dirs.csv`, `replay_targets.csv`, `features_archive.csv`, "
        "`flight_meta.csv`, `expanded_census_clusters.csv`, `censored_approach_diagnostics.csv`, "
        "`censoring_ledger.csv`, `cluster_age_bin_counts.csv`, and release-fit CSVs when authorized.",
        "",
    ])
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def write_task_b_report(out_dir: Path, summary: dict, per_cluster: list[dict]) -> None:
    lines = [
        "# TASK B - Five-Cluster Diagnostic Suite",
        "",
        "DIAGNOSTIC ONLY: may falsify the repair; may not lift HOLD, declare a validated age, or release sigma_a.",
        "",
        f"- Selected clusters: `{summary['selected_cluster_count']}`.",
        f"- Missing legal-five ids: `{', '.join(summary['missing_legal_five']) if summary['missing_legal_five'] else 'none'}`.",
        f"- Sample rows: `{summary['sample_rows']}`.",
        f"- Mechanism regression slope/intercept: `{fmt(summary['mechanism_regression_slope'])}` / `{fmt(summary['mechanism_regression_intercept'])}`.",
        f"- R26-1 restamp verdict: `{summary['r26_1_restamp_verdict']}`.",
        "",
        "| cluster | auth | delta_latch | b0 old | b0 new | old-new | target -delta | error |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in per_cluster:
        lines.append(
            f"| `{row['cluster_id']}` | {fmt(row['auth_at_latch_median'])} | "
            f"{fmt(row['delta_latch_median_mps'])} | {fmt(row['b0_old_mps'])} | "
            f"{fmt(row['b0_new_mps'])} | {fmt(row['b0_old_minus_new_mps'])} | "
            f"{fmt(row['minus_delta_latch_median_mps'])} | {fmt(row['mechanism_error_mps'])} |"
        )
    lines.extend([
        "",
        "Artifacts are prefixed `DIAGNOSTIC_` and include selected clusters, anchor-policy samples, "
        "delta-latch mechanism table, b0 regime-invariance table, pseudo-floor diagnostics, "
        "R26-1 restamp rows, and command/admission old-vs-new comparison.",
        "",
    ])
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def run_task_a(params: ParamSet, out_dir: Path, eligibility_only: bool = False,
               max_targets: int | None = None) -> tuple[list[dict], list[dict], list[dict], list[dict], dict]:
    targets, eligibility = discover_targets(sample_frames=True)
    if max_targets is not None:
        targets = targets[:max_targets]
    write_csv(out_dir / "eligibility_dirs.csv", eligibility)
    write_csv(out_dir / "replay_targets.csv", targets)
    summary: dict[str, Any] = {
        "repo_head": git_head()[0],
        "fixture_dirs_enumerated": len(eligibility),
        "eligible_recordings": len(targets),
    }
    if eligibility_only:
        summary.update({
            "cluster_count": 0,
            "census_verdict": "ELIGIBILITY_ONLY",
            "release_fit_run": False,
            "failure_reason_counts": {},
        })
        with (out_dir / "summary.json").open("w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, sort_keys=True)
        write_task_a_report(out_dir, summary)
        return [], [], [], targets, summary

    features: list[dict] = []
    metas: list[dict] = []
    diagnostics: list[dict] = []
    clusters: list[dict] = []
    for i, target in enumerate(targets, start=1):
        print(f"[taskA] replay {i}/{len(targets)} {target['flight_id']} {target['fixture_dir']}", flush=True)
        try:
            rows, meta = run_video_replay_multi(params, target)
            attach_flight_signals(params, rows, target)
        except Exception as exc:  # keep the census complete
            meta = {
                "flight": target["label"],
                "flight_id": target["flight_id"],
                "fixture_dir": target.get("fixture_dir", ""),
                "era": target.get("era", ""),
                "recording_regime": target.get("recording_regime", ""),
                "replay_error": repr(exc),
            }
            metas.append(meta)
            diagnostics.append({
                "flight": target["label"],
                "flight_id": target["flight_id"],
                "fixture_dir": target.get("fixture_dir", ""),
                "era": target.get("era", ""),
                "recording_regime": target.get("recording_regime", ""),
                "approach_id": f"{target['flight_id']}:REPLAY_ERROR",
                "cluster_ok": False,
                "failure_reason": "REPLAY_ERROR",
                "notes": repr(exc),
            })
            continue
        metas.append(meta)
        features.extend(rows)
        diag, cls = approach_diagnostics_for_flight(rows, meta)
        diagnostics.extend(diag)
        clusters.extend(cls)

    write_csv(out_dir / "features_archive.csv", features)
    write_csv(out_dir / "flight_meta.csv", metas)
    write_csv(out_dir / "censored_approach_diagnostics.csv", diagnostics)
    write_csv(out_dir / "expanded_census_clusters.csv", clusters)
    reason_counts = Counter(str(r.get("failure_reason") or "") for r in diagnostics)
    write_csv(out_dir / "censoring_ledger.csv", [
        {"failure_reason": reason, "rows": count}
        for reason, count in sorted(reason_counts.items())
    ])
    write_csv(out_dir / "cluster_age_bin_counts.csv", age_bin_cluster_counts(clusters, features))

    summary.update({
        "cluster_count": len(clusters),
        "census_verdict": "PASS_GE_6" if len(clusters) >= MIN_RELEASE_CLUSTERS else "STOP_ARCHIVE_LT_6_APPROACHES",
        "release_fit_run": False,
        "failure_reason_counts": dict(sorted(reason_counts.items())),
    })

    if len(clusters) >= MIN_RELEASE_CLUSTERS:
        archive_fit.params = params
        samples, cluster_mech = build_forced_withhold_rows(features, clusters)
        write_csv(out_dir / "forced_withhold_samples.csv", samples)
        write_csv(out_dir / "cluster_mechanism.csv", cluster_mech)
        fit = fit_release(samples)
        boot = cluster_bootstrap(samples)
        loao = loao_sensitivity(samples)
        flight_loao = flight_loao_sensitivity(samples)
        reg = regime_rows(samples)
        cov, max_age, monotone = cluster_balanced_coverage(samples, fit)
        fallback = fallback_bound(samples, fit)
        ps = pseudo_samples(features, clusters)
        pfit = fit_release(ps) if ps else {}
        u95_release = max(float(fit["profile_u95_sigma_a_mps2"]), float(boot["cluster_bootstrap_u95_sigma_a_mps2"]))
        loao_push = any(str(r.get("pushes_over_gate")) == "True" or r.get("pushes_over_gate") is True for r in loao)
        flat = bool(fit["profile_nearly_flat"])
        if flat:
            verdict = "HOLD, PARAMETER-NOT-IDENTIFIED"
        elif loao_push:
            verdict = "HOLD, DATA-INSUFFICIENT"
        elif u95_release <= SIGMA_A_GATE:
            verdict = "RELEASE-READY (statistics side)"
        elif float(fit["sigma_a_mps2"]) <= SIGMA_A_GATE:
            verdict = "HOLD, DATA-INSUFFICIENT"
        else:
            verdict = "FAIL"
        release_row = {
            "n_flights": len({s["flight_id"] for s in samples}),
            "n_clusters": len({s["cluster_id"] for s in samples}),
            "n_rows": len(samples),
            "point_sigma_a_mps2": fit["sigma_a_mps2"],
            "profile_u95_sigma_a_mps2": fit["profile_u95_sigma_a_mps2"],
            "cluster_bootstrap_u95_sigma_a_mps2": boot["cluster_bootstrap_u95_sigma_a_mps2"],
            "u95_release_sigma_a_mps2": u95_release,
            "sigma_0_mps": fit["sigma_0_mps"],
            "pseudo_sigma_0_mps": pfit.get("sigma_0_mps", ""),
            "pseudo_sigma_a_mps2": pfit.get("sigma_a_mps2", ""),
            "profile_nearly_flat": fit["profile_nearly_flat"],
            "loao_pushes_over_gate": loao_push,
            "coverage_monotone_degrade": monotone,
            "max_validated_age": max_age,
            "verdict": verdict,
        }
        write_csv(out_dir / "release_fit.csv", [release_row])
        write_csv(out_dir / "mean_fit.csv", [{k: fit[k] for k in ["b0", "b1", "mean_fit_residual_rms_mps"]} | boot])
        write_csv(out_dir / "cluster_bootstrap.csv", [boot])
        write_csv(out_dir / "profile_likelihood.csv", [{k: fit[k] for k in [
            "profile_u95_sigma_a_mps2", "profile_threshold_nll", "profile_nearly_flat",
            "profile_loss_min", "profile_loss_max"]}])
        write_csv(out_dir / "loao_sensitivity.csv", loao)
        write_csv(out_dir / "flight_loao_sensitivity.csv", flight_loao)
        write_csv(out_dir / "command_regimes.csv", reg)
        write_csv(out_dir / "cluster_balanced_coverage.csv", cov)
        write_csv(out_dir / "fallback_monotone_bound.csv", fallback)
        write_csv(out_dir / "pseudo_samples.csv", ps)
        write_csv(out_dir / "pseudo_release_fit.csv", [pfit] if pfit else [])
        summary["release_fit_run"] = True
        summary["release"] = release_row

    with (out_dir / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
    write_task_a_report(out_dir, summary)
    return features, clusters, diagnostics, targets, summary


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def age_bin_cluster_counts(clusters: list[dict], features: list[dict]) -> list[dict]:
    rows = []
    for label, lo, hi in AGE_BINS:
        approach_ids = set()
        flights = set()
        count = 0
        for c in clusters:
            app_rows = [r for r in features if r.get("flight_id") == c["flight_id"]
                        and float(c["t_start_s"]) <= float(r["t_rel_s"]) <= float(c["t_end_s"])]
            full_rows = certified_full(app_rows)
            side_rows = certified_side(app_rows)
            for cut in full_rows:
                if fnum(cut.get("range_z_m")) is None or float(cut["range_z_m"]) > FULL_LEGAL_RANGE_M:
                    continue
                cut_s = float(cut["feature_ts_ns"]) / 1e9
                for side in side_rows:
                    age = float(side["feature_ts_ns"]) / 1e9 - cut_s
                    if lo <= age < hi:
                        count += 1
                        approach_ids.add(c["approach_id"])
                        flights.add(c["flight_id"])
        rows.append({
            "age_bin": label,
            "independent_approaches": len(approach_ids),
            "flights": len(flights),
            "side_after_full_rows": count,
        })
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eligibility-only", action="store_true")
    ap.add_argument("--task-a-only", action="store_true")
    ap.add_argument("--task-b-only", action="store_true")
    ap.add_argument("--max-targets", type=int, default=None)
    ap.add_argument("--from-task-a-dir", type=Path, default=None)
    args = ap.parse_args(argv)

    assert_mock_safe()
    head, head_short = git_head()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    params = apply_patches(ParamSet.load(ROOT / "config" / "params_default.json"), [])

    task_a_dir = ROOT / "tuning" / f"{TASK_A_PREFIX}-{head_short}-{stamp}"
    task_b_dir = ROOT / "tuning" / f"{TASK_B_PREFIX}-{head_short}-{stamp}"
    features: list[dict] = []
    clusters: list[dict] = []
    diagnostics: list[dict] = []
    targets: list[dict] = []
    if not args.task_b_only:
        task_a_dir.mkdir(parents=True, exist_ok=True)
        features, clusters, diagnostics, targets, summary_a = run_task_a(
            params, task_a_dir, eligibility_only=args.eligibility_only, max_targets=args.max_targets)
        print(f"[taskA] out={task_a_dir}")
        print(f"[taskA] clusters={summary_a.get('cluster_count')} verdict={summary_a.get('census_verdict')}")
    if args.eligibility_only or args.task_a_only:
        return 0

    if args.task_b_only and args.from_task_a_dir is not None:
        src = args.from_task_a_dir.resolve()
        features = read_csv(src / "features_archive.csv")
        clusters = read_csv(src / "expanded_census_clusters.csv")
        diagnostics = read_csv(src / "censored_approach_diagnostics.csv")
    elif args.task_b_only:
        # Task B still needs current replay rows for the known five.
        task_a_dir.mkdir(parents=True, exist_ok=True)
        features, clusters, diagnostics, targets, _summary_a = run_task_a(
            params, task_a_dir, eligibility_only=False, max_targets=args.max_targets)

    task_b_dir.mkdir(parents=True, exist_ok=True)
    summary_b = five_cluster_diagnostics(params, features, clusters, diagnostics, task_b_dir)
    print(f"[taskB] out={task_b_dir}")
    print(f"[taskB] selected={summary_b.get('selected_cluster_count')} samples={summary_b.get('sample_rows')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
