"""Build the A091 REG-1v2.2 calibration packet.

Replay/CSV only. This script prepares the A091 input table from the archived
flight log plus the current feature archive, then delegates scoring to the
committed REG-1v2 calibration source generator.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tuning.reg1v2_calibration_source_generator import (
    TRACE_FIELDS,
    candidate_grid,
    candidate_score,
    detect_step_windows,
    fit_response_model,
    git,
    input_digest_rows,
    predict_window,
    provenance_packet,
    read_csv_rows,
    read_sentinel_keys,
    reconstruct_v_full_raw,
    sha256_file,
    window_to_dict,
    world_up_from_body_z,
)

FLIGHT_ID = "20260719T201851-50f9dcc8"
DEFAULT_FEATURES = Path("tuning/taskA-full-archive-retro-census-bb0dbcf-20260720T165623Z/features_archive.csv")
DEFAULT_FORCED = Path("tuning/taskA-full-archive-retro-census-bb0dbcf-20260720T165623Z/forced_withhold_samples.csv")
DEFAULT_FLIGHT_LOG = Path("fixtures/20260719T204430-phase6i-r-rate-ab/20260719T201851-50f9dcc8-flight.jsonl")
DT_NS = 20_000_000


def _num(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        value_f = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value_f):
        return None
    return value_f


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _latest_at(index: Sequence[tuple[int, Mapping[str, object]]], mono_ns: int) -> Mapping[str, object] | None:
    monos = [m for m, _ in index]
    pos = bisect.bisect_right(monos, mono_ns) - 1
    if pos < 0:
        return None
    return index[pos][1]


def _state_levels(state: Mapping[str, object] | None, fallback_pitch: float, fallback_roll: float) -> tuple[float, float]:
    if state is None:
        return fallback_pitch, fallback_roll
    data = state.get("data", {})
    if not isinstance(data, Mapping):
        return fallback_pitch, fallback_roll
    pitch = _num(data.get("level_pitch"))
    roll = _num(data.get("level_roll"))
    return (
        fallback_pitch if pitch is None else float(pitch),
        fallback_roll if roll is None else float(roll),
    )


def _write_csv(path: Path, rows: Sequence[Mapping[str, object]], fieldnames: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fields: list[str] = []
        for row in rows:
            for key in row.keys():
                if key not in fields:
                    fields.append(key)
        fieldnames = fields or ["empty"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_input(repo: Path, input_dir: Path, features_path: Path, flight_log_path: Path, forced_path: Path) -> dict[str, object]:
    input_dir.mkdir(parents=True, exist_ok=True)
    log_rows = _read_jsonl(repo / flight_log_path)
    setpoints = [(int(r["mono_ns"]), r) for r in log_rows if r.get("topic") == "setpoint"]
    states = [(int(r["mono_ns"]), r) for r in log_rows if r.get("topic") == "state"]
    terms = [(int(r["mono_ns"]), r) for r in log_rows if r.get("topic") == "term_status"]
    shadows = [(int(r["mono_ns"]), r) for r in log_rows if r.get("topic") == "shadow"]
    if not setpoints:
        raise RuntimeError("A091 flight log has no setpoint rows")
    setpoints.sort(key=lambda x: x[0])
    states.sort(key=lambda x: x[0])
    terms.sort(key=lambda x: x[0])
    shadows.sort(key=lambda x: x[0])

    feature_rows_all = [
        row for row in read_csv_rows(repo / features_path)
        if row.get("flight_id") == FLIGHT_ID and row.get("topic") == "feature"
    ]
    if not feature_rows_all:
        raise RuntimeError("A091 feature rows not found in features archive")
    fallback_pitch = float(feature_rows_all[0].get("level_pitch_rad") or 0.0)
    fallback_roll = float(feature_rows_all[0].get("level_roll_rad") or 0.0)
    base_mono = setpoints[0][0]

    rows_by_tick: dict[int, dict[str, object]] = {}
    setpoint_by_tick: dict[int, Mapping[str, object]] = {}
    for mono_ns, record in setpoints:
        tick = int(round((mono_ns - base_mono) / DT_NS))
        data = record.get("data", {})
        if not isinstance(data, Mapping):
            continue
        v_body = data.get("v_body", [None, None, None])
        v_body_z = _num(v_body[2] if isinstance(v_body, list) and len(v_body) >= 3 else None)
        state = _latest_at(states, mono_ns)
        level_pitch, level_roll = _state_levels(state, fallback_pitch, fallback_roll)
        v_ref = None if v_body_z is None else world_up_from_body_z(v_body_z, level_pitch, level_roll)
        row = {
            "row_key": f"{FLIGHT_ID}|setpoint_tick={tick:06d}",
            "flight_id": FLIGHT_ID,
            "tick": tick,
            "ts_s": tick * 0.02,
            "feature_ts_ns": int(round(tick * 0.02 * 1_000_000_000)),
            "mono_ns": mono_ns,
            "v_ref_up_mps": v_ref if v_ref is not None else "",
            "setpoint_v_body_z": v_body_z if v_body_z is not None else "",
            "level_pitch": level_pitch,
            "level_roll": level_roll,
            "certified_full": False,
            "row_kind": "setpoint_grid",
        }
        rows_by_tick[tick] = row
        setpoint_by_tick[tick] = record

    feature_rows_all.sort(key=lambda r: int(r["mono_ns"]))
    merged_features = 0
    for feature in feature_rows_all:
        mono_ns = int(feature["mono_ns"])
        tick = int(round((mono_ns - base_mono) / DT_NS))
        setpoint = _latest_at(setpoints, mono_ns)
        state = _latest_at(states, mono_ns)
        term = _latest_at(terms, mono_ns)
        shadow = _latest_at(shadows, mono_ns)
        level_pitch, level_roll = _state_levels(state, fallback_pitch, fallback_roll)
        setpoint_data = setpoint.get("data", {}) if setpoint is not None else {}
        if not isinstance(setpoint_data, Mapping):
            setpoint_data = {}
        v_body = setpoint_data.get("v_body", [None, None, None])
        v_body_z = _num(v_body[2] if isinstance(v_body, list) and len(v_body) >= 3 else None)
        v_ref = None if v_body_z is None else world_up_from_body_z(v_body_z, level_pitch, level_roll)
        existing = rows_by_tick.get(tick)
        existing_is_feature = existing is not None and existing.get("row_kind") == "feature_exposure"
        certified_full = (
            feature.get("feature_mode") == "FULL_QUAD"
            and feature.get("cert_status") == "certified"
            and feature.get("det_cert_status") == "certified"
        )
        if existing_is_feature and not certified_full:
            continue
        term_data = term.get("data", {}) if term is not None else {}
        shadow_data = shadow.get("data", {}) if shadow is not None else {}
        if not isinstance(term_data, Mapping):
            term_data = {}
        if not isinstance(shadow_data, Mapping):
            shadow_data = {}
        row = {
            "row_key": f"{FLIGHT_ID}|frame={feature['frame_id']}|feature_ts_ns={feature['feature_ts_ns']}",
            "flight_id": FLIGHT_ID,
            "frame_id": feature["frame_id"],
            "tick": tick,
            "ts_s": (mono_ns - base_mono) / 1_000_000_000.0,
            "feature_ts_ns": feature["feature_ts_ns"],
            "mono_ns": mono_ns,
            "tick_grid_mono_ns": base_mono + tick * DT_NS,
            "tick_mismatch_ns": mono_ns - (base_mono + tick * DT_NS),
            "v_ref_up_mps": v_ref if v_ref is not None else "",
            "setpoint_v_body_z": v_body_z if v_body_z is not None else "",
            "e_meas_m": feature.get("e_meas", ""),
            "certified_full": certified_full,
            "row_kind": "feature_exposure",
            "feature_mode": feature.get("feature_mode", ""),
            "cert_status": feature.get("cert_status", ""),
            "det_cert_status": feature.get("det_cert_status", ""),
            "range_z_m": feature.get("range_z_m", ""),
            "level_pitch": level_pitch,
            "level_roll": level_roll,
            "planner_phase": setpoint_data.get("phase", feature.get("phase", "")),
            "term_owner_state": term_data.get("owner", "UNKNOWN"),
            "arbiter_vertical_source": "setpoint.v_body[2]->world_up",
            "adapter_input_v_body_z": v_body_z if v_body_z is not None else "",
            "post_limit_command_v_body_z": v_body_z if v_body_z is not None else "",
            "clip_status": "logged_setpoint",
            "shadow_owner": shadow_data.get("owner", ""),
            "shadow_up_legacy_mps": shadow_data.get("up_legacy_mps", ""),
            "term_ready": term_data.get("ready", ""),
            "term_engaged": term_data.get("engaged", ""),
        }
        rows_by_tick[tick] = row
        merged_features += 1

    input_rows = [rows_by_tick[tick] for tick in sorted(rows_by_tick)]
    input_csv = input_dir / "a091_reg1v22_input.csv"
    _write_csv(input_csv, input_rows)

    forced_rows = [
        dict(row) for row in read_csv_rows(repo / forced_path)
        if row.get("flight_id") == FLIGHT_ID
    ]
    for row in forced_rows:
        if not row.get("row_key") and row.get("flight_id") and row.get("frame_id") and row.get("feature_ts_ns"):
            row["row_key"] = f"{row['flight_id']}|frame={row['frame_id']}|feature_ts_ns={row['feature_ts_ns']}"
    sentinel_csv = input_dir / "a091_sentinel_interval_keys.csv"
    _write_csv(sentinel_csv, forced_rows)

    summary = {
        "flight_id": FLIGHT_ID,
        "base_setpoint_mono_ns": base_mono,
        "input_rows": len(input_rows),
        "feature_rows_in_archive": len(feature_rows_all),
        "feature_rows_merged_to_tick_grid": merged_features,
        "sentinel_rows": len(forced_rows),
        "features_path": str(features_path),
        "flight_log_path": str(flight_log_path),
        "forced_withhold_path": str(forced_path),
        "frame_transform_derivation": "setpoint.v_body[2] is body-z positive down; world-up commanded reference is v_ref_up = -v_body_z * cos(level_pitch) * cos(level_roll).",
        "zero_none_law": "0.0 is retained as a value; absent fields stay absent and become typed ABSENT/OFF_SUPPORT rows, never implicit zero.",
    }
    (input_dir / "input_build_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return {"input_csv": input_csv, "sentinel_csv": sentinel_csv, "summary": summary}


def _usable_windows(windows, fit_dirs: set[str] | None) -> list[object]:
    return [
        w for w in windows
        if not w.exclusion_reason and (fit_dirs is None or w.direction in fit_dirs)
    ]


def _profile_rows(score_rows: Sequence[Mapping[str, object]], best: Mapping[str, object] | None) -> list[Mapping[str, object]]:
    if best is None or best.get("rms_mps") is None:
        return []
    best_rms = float(best["rms_mps"])
    limit = best_rms * 1.10
    return [
        row for row in score_rows
        if row.get("eligible") and row.get("rms_mps") is not None and float(row["rms_mps"]) <= limit
    ]


def write_calibration_artifact(repo: Path, out_dir: Path, input_csv: Path, sentinel_csv: Path, exact_command: str) -> dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=False)
    rows = read_csv_rows(input_csv)
    sentinel_keys = read_sentinel_keys(sentinel_csv)
    windows = detect_step_windows(rows, sentinel_keys=sentinel_keys)
    fit = fit_response_model(windows)
    score_rows = fit["score_rows"]
    fit_summary = {k: v for k, v in fit.items() if k != "score_rows"}
    usable = _usable_windows(windows, None)
    best = fit.get("best")
    profile = _profile_rows(score_rows, best)

    _write_csv(out_dir / "candidate_windows.csv", [window_to_dict(w) for w in windows])
    _write_csv(out_dir / "grid_candidate_scores.csv", score_rows)
    _write_csv(out_dir / "profile_box_candidates.csv", profile)

    interval_rows: list[dict[str, object]] = []
    input_validity_rows: list[dict[str, object]] = []
    excluded_rows: list[dict[str, object]] = []
    for window in windows:
        for row in window.rows:
            record = {
                "event_id": window.event_id,
                "window_exclusion_reason": window.exclusion_reason,
                **row,
                "direction": window.direction,
            }
            input_validity_rows.append(record)
            valid = row["response_status"] == "VALID" and row["trace_complete"] and not window.exclusion_reason
            if valid:
                interval_rows.append(record)
            else:
                excluded_rows.append(record)
    _write_csv(out_dir / "calibration_interval_keys.csv", interval_rows)
    _write_csv(out_dir / "input_validity_rows.csv", input_validity_rows)
    _write_csv(out_dir / "excluded_response_rows.csv", excluded_rows)

    prediction_rows: list[dict[str, object]] = []
    if best is not None:
        from tuning.reg1v2_calibration_source_generator import Candidate

        candidate = Candidate(g=float(best["g"]), tau_s=float(best["tau_s"]), lag_ticks=int(best["L_ticks"]))
        for window in usable:
            preds = predict_window(window, candidate)
            for row in window.rows:
                if row["response_status"] != "VALID" or not row["trace_complete"]:
                    continue
                pred = preds.get(int(row["tick"]))
                meas = _num(row.get("v_meas_mps"))
                prediction_rows.append({
                    "event_id": window.event_id,
                    "row_key": row["row_key"],
                    "tick": row["tick"],
                    "relative_tick": row["relative_tick"],
                    "v_ref_up_mps": row["v_ref_up_mps"],
                    "v_meas_mps": meas,
                    "v_pred_mps": pred,
                    "residual_mps": None if meas is None or pred is None else meas - pred,
                    "g": best["g"],
                    "tau_s": best["tau_s"],
                    "L_ticks": best["L_ticks"],
                })
    _write_csv(out_dir / "best_fit_row_predictions.csv", prediction_rows)

    reconstruction_rows: list[dict[str, object]] = []
    for row in rows:
        if row.get("row_kind") != "feature_exposure":
            continue
        rate, status, meta = reconstruct_v_full_raw(rows, float(row["ts_s"]))
        reconstruction_rows.append({
            "row_key": row["row_key"],
            "frame_id": row.get("frame_id", ""),
            "feature_ts_ns": row["feature_ts_ns"],
            "tick": row["tick"],
            "ts_s": row["ts_s"],
            "certified_full": row.get("certified_full"),
            "v_full_raw_mps": rate,
            "response_status": status,
            **meta,
        })
    _write_csv(out_dir / "v_full_raw_reconstruction_check.csv", reconstruction_rows)

    head_short = git(repo, ["rev-parse", "--short", "HEAD"])
    for src, name in (
        (Path(f"C:/Temp/eni_post_reg2_fixtures_{head_short}.txt"), "preflight_post_reg2_fixture_transcript.txt"),
        (Path(f"C:/Temp/eni_reg1v22_source_fixtures_{head_short}.txt"), "preflight_reg1v22_source_fixture_transcript.txt"),
    ):
        if src.exists():
            shutil.copyfile(src, out_dir / name)

    profile_box = {}
    if profile:
        for key in ("g", "tau_s", "L_ticks"):
            vals = sorted({float(row[key]) for row in profile})
            profile_box[key] = {"min": min(vals), "max": max(vals), "count_distinct": len(vals)}

    summary = {
        "artifact": "A091_RESPONSE_MODEL_CALIBRATION_REG1V22",
        "diagnostic_only": True,
        "flight_id": FLIGHT_ID,
        "criterion_ancestor_required": "ee0bb6a",
        "execution_tip": git(repo, ["rev-parse", "HEAD"]),
        "calibration_status": fit["calibration_status"],
        "best": best,
        "null_model_score": fit.get("null_model_score"),
        "fit_summary": fit_summary,
        "profile_candidate_count": len(profile),
        "profile_box_within_10_percent_rms": profile_box,
        "calibration_rows": len(interval_rows),
        "sentinel_unique_rows": len(sentinel_keys),
        "calibration_sentinel_overlap_rows": len({r["row_key"] for r in interval_rows}.intersection(set(sentinel_keys))),
        "source_input_csv": str(input_csv),
        "source_sentinel_keys": str(sentinel_csv),
        "input_digests": input_digest_rows([str(input_csv), str(sentinel_csv)]),
        "provenance": provenance_packet(repo, [str(input_csv), str(sentinel_csv)], exact_command),
        "frame_transform_derivation": "setpoint.v_body[2] is body-z positive down; world-up commanded reference is v_ref_up = -v_body_z * cos(level_pitch) * cos(level_roll).",
        "zero_none_law": "0.0 is retained as an observed value; None/absent fields are typed and never merged with zero.",
        "reg2_note": "REG-2 is not written by this artifact; numeric binding remains a follow-up criterion commit.",
        "no_sim_scope": "Replay/CSV only; no FlightSim/DCGame launch.",
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "# A091 REG-1v2.2 Calibration Packet",
        "",
        f"- execution_tip: `{summary['execution_tip']}`",
        f"- calibration_status: `{summary['calibration_status']}`",
        f"- calibration_rows: `{summary['calibration_rows']}`",
        f"- sentinel_rows: `{summary['sentinel_unique_rows']}`",
        f"- calibration_sentinel_overlap_rows: `{summary['calibration_sentinel_overlap_rows']}`",
        f"- profile_candidate_count: `{summary['profile_candidate_count']}`",
        "",
        "This packet is DIAGNOSTIC evidence only. REG-2 remains pending and no intervention/judge run was executed.",
    ]
    if best is not None:
        lines.insert(4, f"- best: `g={best['g']}, tau={best['tau_s']}, L={best['L_ticks']}, rms={best['rms_mps']}`")
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build A091 REG-1v2.2 calibration packet")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--features", default=str(DEFAULT_FEATURES))
    parser.add_argument("--flight-log", default=str(DEFAULT_FLIGHT_LOG))
    parser.add_argument("--forced-withhold", default=str(DEFAULT_FORCED))
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    input_dir = Path(args.input_dir)
    out_dir = Path(args.out_dir)
    built = build_input(repo, input_dir, Path(args.features), Path(args.flight_log), Path(args.forced_withhold))
    exact_command = " ".join(sys.argv)
    summary = write_calibration_artifact(repo, out_dir, built["input_csv"], built["sentinel_csv"], exact_command)
    print(json.dumps({
        "artifact": summary["artifact"],
        "out_dir": str(out_dir),
        "input_csv": str(built["input_csv"]),
        "calibration_status": summary["calibration_status"],
        "best": summary["best"],
        "calibration_rows": summary["calibration_rows"],
        "sentinel_overlap": summary["calibration_sentinel_overlap_rows"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
