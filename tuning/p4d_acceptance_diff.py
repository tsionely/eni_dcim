"""P4(d) row-level FULL acceptance diff for F4.

QA & MOCK-TUNER scope: recorded F4 replay/CSV only. No real simulator launch.
The lost row set is taken from the existing hold-lift P4 artifact, then this
script replays F4 with instrumentation to classify each lost FULL row.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import subprocess
import sys
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
    feature_e_meas,
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


P4_DIR = ROOT / "tuning" / "hold-lift-p4-3b554f3-3942837-20260720T115546Z"


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def percentile(values: list[float], pct: float) -> float | str:
    vals = sorted(v for v in values if math.isfinite(v))
    if not vals:
        return ""
    if len(vals) == 1:
        return vals[0]
    pos = pct / 100.0 * (len(vals) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return vals[lo]
    frac = pos - lo
    return vals[lo] * (1.0 - frac) + vals[hi] * frac


def existing_p4_sets() -> tuple[set[int], set[int], list[int]]:
    rows = read_csv(P4_DIR / "p4_feature_rows.csv")
    detector = {
        int(r["frame_id"])
        for r in rows
        if r["flight"] == "F4"
        and r["arm"] == "detector_only"
        and r["feature_mode"] == "FULL_QUAD"
    }
    parallel = {
        int(r["frame_id"])
        for r in rows
        if r["flight"] == "F4"
        and r["arm"] == "parallel_tracker"
        and r["feature_mode"] == "FULL_QUAD"
    }
    return detector, parallel, sorted(detector - parallel)


def source_commit(ref: str) -> tuple[str, str, list[str]]:
    sha = subprocess.check_output(["git", "rev-parse", ref], cwd=ROOT, text=True).strip()
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", f"{ref}..HEAD", "--", ".", ":!tuning"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    return sha, sha[:7], changed


def f4_target() -> dict:
    return next(t for t in TARGETS if t["label"] == "F4")


def run_trace(params: ParamSet, target: dict, arm: str) -> tuple[dict, list[dict], list[dict]]:
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
    parallel_below_m = float(params.get("perception.close_tracker.parallel_below_m", default=3.5))
    est = StateEstimator(params)
    est.set_level_reference(level_roll, level_pitch)
    est.attitude.set_attitude_euler(level_roll, level_pitch)

    t_warm = frames[0][0] - int(3.0 * 1e9)
    events = ([("imu", t, (ts, a, g)) for t, ts, a, g in imu if t >= t_warm]
              + [("frame", mono, (fid, sim_ns, img)) for mono, fid, sim_ns, img in frames])
    events.sort(key=lambda e: e[1])
    t0 = events[0][1]

    trace = []
    relocks = []
    full_fixes = 0
    accepted_full = 0
    feature_full = 0
    side_rows = 0
    last_full_mono = None
    side_armed = False
    center_hint = None

    for kind, mono, payload in events:
        if kind == "imu":
            ts, accel, gyro = payload
            est.predict(ImuSample(ts_ns=ts, accel=accel, gyro=gyro))
            continue

        fid, sim_ns, img = payload
        phase = phase_at(phases, mono)
        state_before = est.state
        prior_z = gate_range_z(state_before) if state_before.gate_rel is not None \
            and state_before.gate_rel_age_s < 1.0 else None
        prior_norm = (
            float(np.linalg.norm(state_before.gate_rel.t))
            if state_before.gate_rel is not None and state_before.gate_rel_age_s < 1.0
            else None
        )
        tracker_status_before = (
            tracker.certificate.status_at(int(sim_ns)) if tracker is not None else ""
        )
        frame = CameraFrame(frame_id=int(fid), ts_ns=int(sim_ns), image=img)
        det = detector.detect(frame, prior_z)
        center_hint = None
        emitted = []

        if det is not None and det.rel_pose is not None:
            full_fixes += 1
            anchored = False
            rejection_stage = ""
            mismatch_m = ""
            mismatch_frac = ""
            threshold_m = ""
            r_fix_norm = float(np.linalg.norm(det.rel_pose.t))
            r_fix_z = float(det.rel_pose.t[2])
            if det.confidence >= 0.55:
                last_full_mono = mono
            if det.cert_status != "certified":
                rejection_stage = "certificate_status"
            else:
                if prior_z is None:
                    anchored = True
                else:
                    mismatch_m = abs(r_fix_norm - float(prior_z))
                    threshold_m = 0.4 * float(prior_z)
                    mismatch_frac = mismatch_m / max(float(prior_z), 1e-9)
                    if mismatch_m <= threshold_m:
                        anchored = True
                    else:
                        rejection_stage = "other_prediction_inconsistent_relock"
                        if tracker is not None:
                            tracker.certificate.on_relock_or_collision()
                            relock_row = {
                                "arm": arm,
                                "frame_id": int(fid),
                                "mono_ns": int(mono),
                                "feature_ts_ns": int(det.ts_ns),
                                "t_rel_s": (int(mono) - t0) / 1e9,
                                "phase": phase,
                                "prior_z_m": prior_z if prior_z is not None else "",
                                "prior_norm_m": prior_norm if prior_norm is not None else "",
                                "det_range_norm_m": r_fix_norm,
                                "det_z_m": r_fix_z,
                                "range_mismatch_m": mismatch_m,
                                "range_mismatch_frac": mismatch_frac,
                                "mismatch_threshold_m": threshold_m,
                                "tracker_status_before": tracker_status_before,
                            }
                            relocks.append(relock_row)
                            side_armed = False
            if anchored:
                accepted_full += 1
            est.update_vision(det)
            feat = feature_from_full(det) if anchored else None
            e_meas, e_reject = feature_e_meas(params, est.state, feat) if feat is not None else ("", "")
            if anchored and feat is None:
                rejection_stage = "other_no_full_feature"
            elif anchored and e_reject not in ("", "ok"):
                rejection_stage = "scale_gate" if e_reject == "scale_gate" else f"feature_{e_reject}"
            elif anchored:
                rejection_stage = "accepted"
                feature_full += 1
                emitted.append(("FULL_QUAD", "detector"))
            if (tracker is not None and anchored and tracker.enabled
                    and det.rel_pose is not None and float(det.rel_pose.t[2]) <= parallel_below_m):
                side_armed = True
                prior_pose = state_before.gate_rel if state_before.gate_rel is not None else det.rel_pose
                tracked_side = tracker.track(frame, prior_pose, center_hint_px=det.center_px)
                if tracked_side is not None and tracker.last_feature is not None:
                    side_rows += 1
                    emitted.append(("SIDE_PAIR", "tracker_parallel"))

            tracker_status_after = (
                tracker.certificate.status_at(int(sim_ns)) if tracker is not None else ""
            )
            trace.append({
                "arm": arm,
                "frame_id": int(fid),
                "mono_ns": int(mono),
                "feature_ts_ns": int(det.ts_ns),
                "t_rel_s": (int(mono) - t0) / 1e9,
                "phase": phase,
                "raw_full_fix": True,
                "det_cert_status": det.cert_status,
                "det_confidence": det.confidence,
                "det_range_norm_m": r_fix_norm,
                "det_z_m": r_fix_z,
                "prior_z_m": prior_z if prior_z is not None else "",
                "prior_norm_m": prior_norm if prior_norm is not None else "",
                "prior_age_s": state_before.gate_rel_age_s if state_before.gate_rel is not None else "",
                "range_mismatch_m": mismatch_m,
                "range_mismatch_frac": mismatch_frac,
                "mismatch_threshold_m": threshold_m,
                "accepted_full": anchored,
                "full_feature_accepted": rejection_stage == "accepted",
                "e_meas": e_meas,
                "e_reject": e_reject,
                "parallel_acceptance_stage": rejection_stage,
                "tracker_status_before": tracker_status_before,
                "tracker_status_after": tracker_status_after,
                "emitted_modes": ",".join(m for m, _ in emitted),
            })
        elif det is not None:
            center_hint = det.center_px

        fallback_allowed = tracker is not None and (
            side_armed or (
                last_full_mono is not None
                and (mono - last_full_mono) / 1e9 <= tracker.max_solo_s
            )
        )
        if (det is None or det.rel_pose is None) and fallback_allowed \
                and tracker is not None and tracker.enabled and est.state.gate_rel is not None:
            tracked = tracker.track(frame, est.state.gate_rel, center_hint_px=center_hint)
            if tracked is not None:
                est.update_vision(tracked)
                if tracker.last_feature is not None:
                    side_rows += 1

    meta = {
        "flight": target["label"],
        "flight_id": target["flight_id"],
        "arm": arm,
        "unique_exposures": len(frames),
        "raw_full_fixes": full_fixes,
        "accepted_full": accepted_full,
        "full_feature_rows": feature_full,
        "side_rows": side_rows,
        "relock_events": len(relocks),
    }
    return meta, trace, relocks


def classify_lost_rows(lost: list[int], parallel_trace: list[dict],
                       relocks: list[dict]) -> list[dict]:
    by_frame = {int(r["frame_id"]): r for r in parallel_trace}
    relocks_sorted = sorted(relocks, key=lambda r: int(r["frame_id"]))
    rows = []
    for fid in lost:
        tr = by_frame.get(fid)
        before = [r for r in relocks_sorted if int(r["frame_id"]) < fid]
        before_or_same = [r for r in relocks_sorted if int(r["frame_id"]) <= fid]
        last = before_or_same[-1] if before_or_same else None
        if tr is None:
            rows.append({
                "frame_id": fid,
                "status": "missing_raw_fix_in_parallel_trace",
            })
            continue
        relock_stage = tr["parallel_acceptance_stage"] == "other_prediction_inconsistent_relock"
        unique_contradictory_before = len({int(r["frame_id"]) for r in before})
        unique_contradictory_at_or_before = len({int(r["frame_id"]) for r in before_or_same})
        rows.append({
            "frame_id": fid,
            "feature_ts_ns": tr["feature_ts_ns"],
            "mono_ns": tr["mono_ns"],
            "t_rel_s": tr["t_rel_s"],
            "phase": tr["phase"],
            "range_norm_m": tr["det_range_norm_m"],
            "range_z_m": tr["det_z_m"],
            "parallel_acceptance_stage": tr["parallel_acceptance_stage"],
            "det_cert_status": tr["det_cert_status"],
            "e_reject": tr["e_reject"],
            "tracker_prediction_inconsistent_relock_this_row": relock_stage,
            "tracker_prediction_inconsistent_relock_preceded": bool(before),
            "tracker_prediction_inconsistent_relock_at_or_before": bool(before_or_same),
            "relock_frame_id": last["frame_id"] if last else "",
            "relock_range_mismatch_m": last["range_mismatch_m"] if last else "",
            "relock_range_mismatch_frac": last["range_mismatch_frac"] if last else "",
            "relock_prior_z_m": last["prior_z_m"] if last else "",
            "relock_prior_norm_m": last["prior_norm_m"] if last else "",
            "relock_det_range_norm_m": last["det_range_norm_m"] if last else "",
            "unique_contradictory_exposures_before": unique_contradictory_before,
            "unique_contradictory_exposures_at_or_before": unique_contradictory_at_or_before,
        })
    return rows


def verdict(diff_rows: list[dict]) -> tuple[str, str]:
    lost = [r for r in diff_rows if r.get("parallel_acceptance_stage")]
    if not lost:
        return "UNKNOWN", "No lost rows were classified."
    relock_rows = [
        r for r in lost
        if r.get("parallel_acceptance_stage") == "other_prediction_inconsistent_relock"
    ]
    if len(relock_rows) == len(lost):
        max_before = max(int(r["unique_contradictory_exposures_before"]) for r in relock_rows)
        far_identity = []
        for row in relock_rows:
            det = fnum(row.get("relock_det_range_norm_m"))
            prior = fnum(row.get("relock_prior_z_m"))
            mismatch = fnum(row.get("relock_range_mismatch_m"))
            if det is None or prior is None or mismatch is None:
                continue
            if det >= 2.5 and mismatch >= max(1.0, 2.0 * abs(prior)):
                far_identity.append(row)
        if max_before < 2:
            return (
                "FALSE RELOCK",
                "All lost rows are rejected by prediction-inconsistent relock; the first lost row has no preceding contradictory exposure, so the 8-row loss is a primary-channel liveness regression candidate.",
            )
        if max_before >= 3 and len(far_identity) >= len(relock_rows) - 1:
            return (
                "HONEST RELOCK",
                "All lost rows are relock-rejected after many prior contradictory exposures, and the rejected detector ranges jump far outside the live primary lock. This prices the certificate boundary rather than showing a primary-channel liveness regression.",
            )
        return (
            "HONEST RELOCK CANDIDATE",
            "Rows are relock-rejected after multiple prior contradictory exposures; needs identity-change corroboration.",
        )
    return (
        "MIXED",
        "Lost rows have mixed rejection stages; see p4d_lost_full_diff.csv.",
    )


def write_report(out_dir: Path, summary: dict) -> None:
    lines = [
        "# P4(d) F4 Acceptance Diff",
        "",
        "Scope: recorded F4 replay/CSV only; no simulator launched.",
        f"Repo HEAD: `{summary['repo_head']}`.",
        f"Source P4 artifact: `{summary['p4_source']}`.",
        f"Source ref: `{summary['source_ref']}` -> `{summary['source_sha']}`.",
        "",
        "## Reproduction",
        "",
        "| Arm | raw FULL fixes | accepted FULL | side rows | relock events |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in summary["arm_meta"]:
        lines.append(
            f"| `{row['arm']}` | {row['raw_full_fixes']} | {row['accepted_full']} | "
            f"{row['side_rows']} | {row['relock_events']} |"
        )
    lines.extend([
        "",
        f"Existing P4 lost frame ids: `{summary['lost_frame_ids']}`.",
        "",
        "## Lost Rows",
        "",
        "| frame | ts_ns | range | stage | relock at/before | mismatch | prior z | relock det range | contrad before | contrad at/before |",
        "|---:|---:|---:|---|---|---:|---:|---:|---:|---:|",
    ])
    for row in summary["diff_rows"]:
        lines.append(
            f"| {row['frame_id']} | {row.get('feature_ts_ns', '')} | "
            f"{fmt(row.get('range_norm_m'))} | `{row.get('parallel_acceptance_stage', '')}` | "
            f"`{row.get('tracker_prediction_inconsistent_relock_at_or_before', '')}` | "
            f"{fmt(row.get('relock_range_mismatch_m'))} | {fmt(row.get('relock_prior_z_m'))} | "
            f"{fmt(row.get('relock_det_range_norm_m'))} | "
            f"{row.get('unique_contradictory_exposures_before', '')} | "
            f"{row.get('unique_contradictory_exposures_at_or_before', '')} |"
        )
    lines.extend([
        "",
        "## Verdict",
        "",
        f"`{summary['verdict']}`: {summary['verdict_note']}",
        "",
        f"F4 cluster quarantine: `{summary['f4_cluster_quarantine']}`.",
        "",
        "Artifacts: `p4d_lost_full_diff.csv`, `p4d_parallel_trace.csv`, "
        "`p4d_detector_trace.csv`, `p4d_relock_events.csv`, "
        "`p4d_arm_meta.csv`, `summary.json`, and `summary.md`.",
    ])
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-ref", default="876b570")
    args = parser.parse_args(argv)

    assert_mock_safe()
    repo_head, repo_short = git_head()
    source_sha, source_short, source_delta = source_commit(args.source_ref)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ROOT / "tuning" / f"p4d-f4-acceptance-diff-{source_short}-{repo_short}-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    params = apply_patches(ParamSet.load(ROOT / "config" / "params_default.json"), [])
    target = f4_target()
    old_detector, old_parallel, lost = existing_p4_sets()
    det_meta, det_trace, det_relocks = run_trace(params, target, "detector_only")
    par_meta, par_trace, par_relocks = run_trace(params, target, "parallel_tracker")
    diff_rows = classify_lost_rows(lost, par_trace, par_relocks)
    label, note = verdict(diff_rows)
    summary = {
        "repo_head": repo_head,
        "source_ref": args.source_ref,
        "source_sha": source_sha,
        "non_tuning_delta_from_source": source_delta,
        "p4_source": str(P4_DIR.relative_to(ROOT)),
        "existing_detector_only_full_rows": len(old_detector),
        "existing_parallel_full_rows": len(old_parallel),
        "lost_frame_ids": lost,
        "arm_meta": [det_meta, par_meta],
        "diff_rows": diff_rows,
        "verdict": label,
        "verdict_note": note,
        "f4_cluster_quarantine": "CLEARED" if label == "HONEST RELOCK" else "KEEP_QUARANTINED",
    }
    write_csv(out_dir / "p4d_detector_trace.csv", det_trace)
    write_csv(out_dir / "p4d_parallel_trace.csv", par_trace)
    write_csv(out_dir / "p4d_relock_events.csv", par_relocks)
    write_csv(out_dir / "p4d_lost_full_diff.csv", diff_rows)
    write_csv(out_dir / "p4d_arm_meta.csv", [det_meta, par_meta])
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(out_dir, summary)
    print(f"[p4d] report={out_dir / 'summary.md'}")
    print(f"[p4d] verdict={label} lost={len(diff_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
