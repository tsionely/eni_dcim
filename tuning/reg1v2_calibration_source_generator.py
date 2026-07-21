"""REG-1v2 calibration source generator for Contract B.

This source file is intentionally committed before any A091 calibration packet
is allowed to exist. The current task may run only synthetic dry-runs; real A091
execution is a later instruction after this file is an ancestor.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
from typing import Iterable, Mapping, Sequence

REG1_COMMIT = "139a4d1"
SOURCE_GENERATOR_PATH = "tuning/reg1v2_calibration_source_generator.py"
DT_S = 0.02
STEP_FLOOR_MPS = 0.35
PRE_WINDOW_TICKS = 10
PRE_STABILITY_MPS = 0.05
POST_TRANSITION_MPS = 0.05
POST_CAP_TICKS = 50
RATE_HISTORY_S = 0.50
RATE_MIN_SAMPLES = 4
RATE_MIN_SPAN_S = 0.15
MIN_VALID_ROWS = 8
G_VALUES = [round(i * 0.05, 2) for i in range(31)]
TAU_VALUES = [round(i * 0.02, 2) for i in range(1, 61)]
L_VALUES = list(range(26))
TRACE_FIELDS = (
    "planner_phase",
    "term_owner_state",
    "arbiter_vertical_source",
    "adapter_input_v_body_z",
    "post_limit_command_v_body_z",
    "clip_status",
)


class CalibrationSourceError(RuntimeError):
    pass


@dataclass(frozen=True)
class Candidate:
    g: float
    tau_s: float
    lag_ticks: int


@dataclass(frozen=True)
class StepWindow:
    event_id: str
    tick: int
    direction: str
    pre_level_mps: float
    post_level_mps: float
    pre_mean_mps: float
    post_ticks: list[int]
    rows: list[dict[str, object]]
    exclusion_reason: str = ""


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


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git(repo: Path, args: Sequence[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def git_bytes(repo: Path, args: Sequence[str]) -> bytes:
    return subprocess.check_output(["git", *args], cwd=repo)


def is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", ancestor, descendant], cwd=repo).returncode == 0


def committed_byte_digest(repo: Path, reviewed_tip: str, rel_path: str) -> str:
    return sha256_bytes(git_bytes(repo, ["show", f"{reviewed_tip}:{rel_path}"]))


def world_up_from_body_z(v_body_z: float, level_pitch: float, level_roll: float) -> float:
    return -float(v_body_z) * math.cos(float(level_pitch)) * math.cos(float(level_roll))


def theil_sen_slope(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    slopes: list[float] = []
    for i, xi in enumerate(xs):
        for j in range(i + 1, len(xs)):
            dx = xs[j] - xi
            if dx != 0.0:
                slopes.append((ys[j] - ys[i]) / dx)
    if not slopes:
        return None
    return float(statistics.median(slopes))


def normalize_rows(rows: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for index, row in enumerate(rows):
        new = dict(row)
        tick_raw = new.get("tick")
        if tick_raw is None:
            tick_raw = index
        new["tick"] = int(tick_raw)
        if _num(new.get("ts_s")) is None:
            new["ts_s"] = new["tick"] * DT_S
        if _num(new.get("v_ref_up_mps")) is None:
            v_body_z = _num(new.get("setpoint_v_body_z"))
            level_pitch = _num(new.get("level_pitch"))
            level_roll = _num(new.get("level_roll"))
            if v_body_z is not None and level_pitch is not None and level_roll is not None:
                new["v_ref_up_mps"] = world_up_from_body_z(v_body_z, level_pitch, level_roll)
        if not new.get("row_key"):
            new["row_key"] = f"tick_{new['tick']:06d}"
        if not new.get("feature_ts_ns"):
            new["feature_ts_ns"] = int(round(float(new["ts_s"]) * 1_000_000_000))
        out.append(new)
    return sorted(out, key=lambda r: int(r["tick"]))


def _certified_history(rows: Sequence[Mapping[str, object]], anchor_ts_s: float) -> tuple[list[float], list[float]]:
    start = anchor_ts_s - RATE_HISTORY_S
    history: list[tuple[float, float]] = []
    for row in rows:
        if not bool(row.get("certified_full", True)):
            continue
        ts = _num(row.get("ts_s"))
        e_meas = _num(row.get("e_meas_m"))
        if ts is None or e_meas is None:
            continue
        if start <= ts <= anchor_ts_s:
            history.append((ts, e_meas))
    history.sort()
    return [x for x, _ in history], [y for _, y in history]


def reconstruct_v_full_raw(rows: Sequence[Mapping[str, object]], anchor_ts_s: float) -> tuple[float | None, str, dict[str, object]]:
    xs, ys = _certified_history(rows, anchor_ts_s)
    span = (max(xs) - min(xs)) if xs else 0.0
    meta = {"history_samples": len(xs), "history_span_s": span}
    if len(xs) < RATE_MIN_SAMPLES or span < RATE_MIN_SPAN_S:
        return None, "ABSENT_RESPONSE", meta
    slope = theil_sen_slope(xs, ys)
    if slope is None:
        return None, "ABSENT_RESPONSE", meta
    return -slope, "VALID", meta


def _trace_for_row(row: Mapping[str, object]) -> dict[str, object]:
    missing = [field for field in TRACE_FIELDS if field not in row]
    return {
        "trace_complete": not missing,
        "missing_trace_fields": ";".join(missing),
        **{field: row.get(field, "") for field in TRACE_FIELDS},
    }


def detect_step_windows(rows_in: Sequence[Mapping[str, object]], sentinel_keys: Iterable[str] = ()) -> list[StepWindow]:
    rows = normalize_rows(rows_in)
    by_tick = {int(r["tick"]): r for r in rows}
    sentinel_set = {str(k) for k in sentinel_keys}
    raw_step_indices: list[int] = []
    for i in range(1, len(rows)):
        prev_ref = _num(rows[i - 1].get("v_ref_up_mps"))
        ref = _num(rows[i].get("v_ref_up_mps"))
        if prev_ref is None or ref is None:
            continue
        if abs(ref - prev_ref) >= STEP_FLOOR_MPS:
            raw_step_indices.append(i)
    merged_indices = [idx for idx in raw_step_indices if idx - 1 not in raw_step_indices]
    windows: list[StepWindow] = []
    for seq, idx in enumerate(merged_indices, start=1):
        row = rows[idx]
        tick = int(row["tick"])
        pre_ticks = list(range(tick - PRE_WINDOW_TICKS, tick))
        pre_rows = [by_tick.get(t) for t in pre_ticks]
        prev_ref = _num(rows[idx - 1].get("v_ref_up_mps"))
        post_ref = _num(row.get("v_ref_up_mps"))
        reason = ""
        if any(r is None for r in pre_rows) or prev_ref is None or post_ref is None:
            reason = "ABSENT_INPUT"
            pre_mean = 0.0
        else:
            pre_refs = [_num(r.get("v_ref_up_mps")) for r in pre_rows if r is not None]
            if any(v is None for v in pre_refs) or any(abs(float(v) - prev_ref) >= PRE_STABILITY_MPS for v in pre_refs if v is not None):
                reason = "ABSENT_INPUT"
            pre_mean = statistics.fmean(float(v) for v in pre_refs if v is not None) if pre_refs else 0.0
        end_tick = tick + POST_CAP_TICKS - 1
        for later in rows[idx + 1:]:
            later_ref = _num(later.get("v_ref_up_mps"))
            if later_ref is None:
                reason = reason or "ABSENT_INPUT"
                continue
            if abs(later_ref - post_ref) >= POST_TRANSITION_MPS:
                end_tick = min(end_tick, int(later["tick"]) - 1)
                break
        post_ticks = [t for t in range(tick, end_tick + 1) if t in by_tick]
        event_rows: list[dict[str, object]] = []
        for t in post_ticks:
            src = by_tick[t]
            event_key = str(src.get("row_key"))
            if event_key in sentinel_set:
                reason = "SENTINEL_DISJOINT"
            v_meas, response_status, response_meta = reconstruct_v_full_raw(rows, float(src["ts_s"]))
            trace = _trace_for_row(src)
            event_rows.append({
                "event_id": f"step_{seq:02d}",
                "row_key": event_key,
                "tick": int(src["tick"]),
                "relative_tick": int(src["tick"]) - tick,
                "ts_s": float(src["ts_s"]),
                "feature_ts_ns": int(src["feature_ts_ns"]),
                "v_ref_up_mps": _num(src.get("v_ref_up_mps")),
                "v_meas_mps": v_meas,
                "response_status": response_status,
                **response_meta,
                **trace,
            })
        valid_count = sum(1 for r in event_rows if r["response_status"] == "VALID" and r["trace_complete"])
        if not reason and valid_count < MIN_VALID_ROWS:
            reason = "INSUFFICIENT_ROWS"
        direction = "up" if post_ref is not None and prev_ref is not None and post_ref > prev_ref else "down"
        windows.append(StepWindow(
            event_id=f"step_{seq:02d}",
            tick=tick,
            direction=direction,
            pre_level_mps=float(prev_ref or 0.0),
            post_level_mps=float(post_ref or 0.0),
            pre_mean_mps=float(pre_mean),
            post_ticks=post_ticks,
            rows=event_rows,
            exclusion_reason=reason,
        ))
    return windows


def candidate_grid() -> Iterable[Candidate]:
    for lag in L_VALUES:
        for tau in TAU_VALUES:
            for g in G_VALUES:
                yield Candidate(g=g, tau_s=tau, lag_ticks=lag)


def _refs_by_tick(window: StepWindow) -> dict[int, float]:
    return {int(r["tick"]): float(r["v_ref_up_mps"]) for r in window.rows if _num(r.get("v_ref_up_mps")) is not None}


def predict_window(window: StepWindow, candidate: Candidate) -> dict[int, float]:
    refs = _refs_by_tick(window)
    v_hat = candidate.g * window.pre_mean_mps
    preds: dict[int, float] = {}
    for tick in window.post_ticks:
        ref_tick = tick - candidate.lag_ticks
        if ref_tick < window.tick:
            ref = window.pre_mean_mps
        else:
            ref = refs.get(ref_tick, window.post_level_mps)
        v_hat = v_hat + (DT_S / candidate.tau_s) * (candidate.g * ref - v_hat)
        preds[tick] = v_hat
    return preds


def candidate_score(windows: Sequence[StepWindow], candidate: Candidate, fit_directions: set[str] | None = None) -> dict[str, object]:
    rows_used = 0
    sse = 0.0
    max_horizon_s = 0.0
    for window in windows:
        if window.exclusion_reason:
            continue
        if fit_directions is not None and window.direction not in fit_directions:
            continue
        preds = predict_window(window, candidate)
        for row in window.rows:
            if row["response_status"] != "VALID" or not row["trace_complete"]:
                continue
            rel_tick = int(row["relative_tick"])
            if rel_tick < candidate.lag_ticks:
                continue
            meas = _num(row.get("v_meas_mps"))
            pred = preds.get(int(row["tick"]))
            if meas is None or pred is None:
                continue
            rows_used += 1
            max_horizon_s = max(max_horizon_s, rel_tick * DT_S)
            sse += (meas - pred) ** 2
    eligible = rows_used >= MIN_VALID_ROWS and max_horizon_s >= candidate.tau_s
    return {
        "g": candidate.g,
        "tau_s": candidate.tau_s,
        "L_ticks": candidate.lag_ticks,
        "rows_used": rows_used,
        "max_horizon_s": max_horizon_s,
        "sse": sse,
        "mse": (sse / rows_used) if rows_used else None,
        "rms_mps": math.sqrt(sse / rows_used) if rows_used else None,
        "eligible": eligible,
        "ineligible_reason": "" if eligible else ("INSUFFICIENT_ROWS" if rows_used < MIN_VALID_ROWS else "HORIZON_LT_TAU"),
    }


def _open_face(best: Mapping[str, object], eligible_scores: Sequence[Mapping[str, object]]) -> bool:
    if float(best["g"]) == 0.0:
        return False
    if float(best["g"]) in {min(G_VALUES), max(G_VALUES)}:
        return True
    if float(best["tau_s"]) in {min(TAU_VALUES), max(TAU_VALUES)}:
        return True
    if int(best["L_ticks"]) in {min(L_VALUES), max(L_VALUES)}:
        return True
    eligible_taus = {float(s["tau_s"]) for s in eligible_scores}
    eligible_lags = {int(s["L_ticks"]) for s in eligible_scores}
    if float(best["tau_s"]) == max(eligible_taus):
        return True
    if int(best["L_ticks"]) == max(eligible_lags):
        return True
    return False


def fit_response_model(windows: Sequence[StepWindow], fit_directions: set[str] | None = None) -> dict[str, object]:
    detected = sorted({w.direction for w in windows})
    usable = [w for w in windows if not w.exclusion_reason and (fit_directions is None or w.direction in fit_directions)]
    score_rows = [candidate_score(usable, cand, fit_directions) for cand in candidate_grid()]
    eligible = [row for row in score_rows if row["eligible"]]
    null_scores = [row for row in score_rows if row["eligible"] and float(row["g"]) == 0.0]
    null_best = min(null_scores, key=lambda r: float(r["sse"])) if null_scores else None
    if not usable or not eligible:
        status = "UNCALIBRATABLE"
        best = None
    else:
        best = eligible[0]
        for row in eligible[1:]:
            if float(row["sse"]) < float(best["sse"]):
                best = row
        if float(best["g"]) == 0.0:
            status = "NULL_CALIBRATED"
        elif _open_face(best, eligible):
            status = "NOT_IDENTIFIED"
        else:
            status = "CALIBRATED"
    return {
        "calibration_status": status,
        "best": best,
        "null_model_score": null_best,
        "detected_directions": detected,
        "fit_directions": sorted(fit_directions) if fit_directions else detected,
        "candidate_count": len(score_rows),
        "eligible_count": len(eligible),
        "score_rows": score_rows,
        "window_count": len(windows),
        "usable_window_count": len(usable),
        "windows": [window_to_dict(w) for w in windows],
    }


def window_to_dict(window: StepWindow) -> dict[str, object]:
    return {
        "event_id": window.event_id,
        "tick": window.tick,
        "direction": window.direction,
        "pre_level_mps": window.pre_level_mps,
        "post_level_mps": window.post_level_mps,
        "pre_mean_mps": window.pre_mean_mps,
        "post_tick_count": len(window.post_ticks),
        "valid_rows": sum(1 for r in window.rows if r["response_status"] == "VALID" and r["trace_complete"]),
        "exclusion_reason": window.exclusion_reason,
    }


def read_csv_rows(path: Path) -> list[dict[str, object]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def input_digest_rows(paths: Sequence[str]) -> list[dict[str, str]]:
    rows = []
    for value in paths:
        if value.startswith("synthetic://"):
            digest = sha256_bytes(value.encode("utf-8"))
        else:
            digest = sha256_file(Path(value))
        rows.append({"path": value, "sha256": digest})
    return rows


def provenance_packet(repo: Path, input_paths: Sequence[str], exact_command: str, *, artifact_commit: str | None = None) -> dict[str, object]:
    execution_tip = git(repo, ["rev-parse", "HEAD"])
    if not is_ancestor(repo, REG1_COMMIT, execution_tip):
        raise CalibrationSourceError(f"REG-1 commit {REG1_COMMIT} is not an ancestor of {execution_tip}")
    return {
        "source_generator_path": SOURCE_GENERATOR_PATH,
        "source_generator_commit": execution_tip,
        "execution_tip": execution_tip,
        "artifact_commit": artifact_commit,
        "reg1_commit": REG1_COMMIT,
        "input_digests": input_digest_rows(input_paths),
        "exact_command": exact_command,
        "attestation_policy": "artifact_manifest digests must be computed from committed bytes in a child attestation commit",
    }


def committed_attestation_rows(repo: Path, reviewed_tip: str, paths: Sequence[str]) -> list[dict[str, str]]:
    return [
        {"path": path, "reviewed_tip": reviewed_tip, "sha256_committed_bytes": committed_byte_digest(repo, reviewed_tip, path)}
        for path in paths
    ]


def synthetic_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    e0 = 2.0
    e_slope = -0.25
    for tick in range(115):
        if tick < 20:
            v_ref = 0.0
        elif tick < 50:
            v_ref = 0.50
        else:
            v_ref = -0.10
        ts = tick * DT_S
        rows.append({
            "row_key": f"syn_{tick:04d}",
            "tick": tick,
            "ts_s": ts,
            "feature_ts_ns": int(round(ts * 1_000_000_000)),
            "v_ref_up_mps": v_ref,
            "e_meas_m": e0 + e_slope * ts,
            "certified_full": True,
            "planner_phase": "CAL_SYNTH",
            "term_owner_state": "LEGACY",
            "arbiter_vertical_source": "setpoint.v_body[2]",
            "adapter_input_v_body_z": -v_ref,
            "post_limit_command_v_body_z": -v_ref,
            "clip_status": "not_clipped",
        })
    return rows


def synthetic_null_rows() -> list[dict[str, object]]:
    rows = synthetic_rows()
    for row in rows:
        row["e_meas_m"] = 1.25
    return rows


def synthetic_dry_run(repo: Path) -> dict[str, object]:
    rows = synthetic_rows()
    windows = detect_step_windows(rows)
    fit = fit_response_model(windows)
    packet = provenance_packet(repo, ["synthetic://reg1v2-detector-dry-run"], "python tuning/reg1v2_calibration_source_generator.py --synthetic-dry-run")
    return {
        "artifact": "REG1V2_CALIBRATION_SOURCE_SYNTHETIC_DRY_RUN",
        "diagnostic_only": True,
        "detector": [window_to_dict(w) for w in windows],
        "fit_summary": {k: v for k, v in fit.items() if k not in {"score_rows"}},
        "grid": {"g_count": len(G_VALUES), "tau_count": len(TAU_VALUES), "L_count": len(L_VALUES), "candidate_count": len(G_VALUES) * len(TAU_VALUES) * len(L_VALUES)},
        "provenance": packet,
    }


def write_packet(out_dir: Path, packet: Mapping[str, object], score_rows: Sequence[Mapping[str, object]] | None = None) -> None:
    out_dir.mkdir(parents=True, exist_ok=False)
    (out_dir / "summary.json").write_text(json.dumps(packet, indent=2, sort_keys=True), encoding="utf-8")
    if score_rows is not None:
        with (out_dir / "candidate_scores.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(score_rows[0].keys()) if score_rows else ["empty"])
            writer.writeheader()
            writer.writerows(score_rows)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="REG-1v2 calibration source generator")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--synthetic-dry-run", action="store_true")
    parser.add_argument("--input-csv")
    parser.add_argument("--out-dir")
    parser.add_argument("--fit-direction", choices=["up", "down", "both"], default="both")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    if args.synthetic_dry_run:
        print(json.dumps(synthetic_dry_run(repo), indent=2, sort_keys=True))
        return 0
    if not args.input_csv or not args.out_dir:
        parser.error("--input-csv and --out-dir are required outside --synthetic-dry-run")
    input_path = Path(args.input_csv).resolve()
    rows = read_csv_rows(input_path)
    windows = detect_step_windows(rows)
    fit_dirs = None if args.fit_direction == "both" else {args.fit_direction}
    fit = fit_response_model(windows, fit_dirs)
    packet = {
        "artifact": "REG1V2_CALIBRATION_PACKET",
        "diagnostic_only": True,
        "fit_summary": {k: v for k, v in fit.items() if k not in {"score_rows"}},
        "provenance": provenance_packet(repo, [str(input_path)], " ".join(sys.argv)),
    }
    write_packet(Path(args.out_dir), packet, fit["score_rows"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
