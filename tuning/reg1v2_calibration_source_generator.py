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

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from aigp.planning.vertical_terminal import robust_slope

REG1_COMMIT = "e73ca90"
SOURCE_GENERATOR_PATH = "tuning/reg1v2_calibration_source_generator.py"
DT_S = 0.02
DT_NS = 20_000_000
STEP_FLOOR_MPS = 0.35
PRE_WINDOW_TICKS = 10
PRE_STABILITY_MPS = 0.05
POST_TRANSITION_MPS = 0.05
POST_CAP_TICKS = 50
RATE_MAX_GAP_S = 0.12
RATE_LAST_SAMPLE_CAP = 12
RATE_MIN_SAMPLES = 4
MIN_VALID_ROWS = 8
NULL_TIE_REL_TOL = 1e-9
G_VALUES = [round(i * 0.05, 2) for i in range(31)]
TAU_VALUES = [round(i * 0.02, 2) for i in range(1, 61)]
L_VALUES = list(range(26))
PRIMARY_FIT_DIRECTION = "down"
PACKET_SCOPES = {"SYNTHETIC_DIAGNOSTIC", "REG2_CALIBRATION_CANDIDATE", "VOID"}
CERT_TRUE_TEXT = {"True", "true", "1"}
CERT_FALSE_TEXT = {"False", "false", "0"}
TRACE_FIELDS = (
    "planner_phase",
    "term_owner_state",
    "arbiter_vertical_source",
    "adapter_input_v_body_z",
    "post_limit_command_v_body_z",
    "clip_status",
)
TRACE_VALUE_SETS = {
    "planner_phase": {"CAL_SYNTH", "POSITION", "COMMIT", "ALIGN", "LEGACY", "TRACK"},
    "term_owner_state": {"LEGACY", "TERM", "COMMON_ARM", "SIDE", "FULL"},
    "arbiter_vertical_source": {"setpoint.v_body[2]", "TERM", "LEGACY", "COMMON_ARM"},
    "clip_status": {"not_clipped", "clipped", "CLIPPED", "none"},
}


class CalibrationSourceError(RuntimeError):
    pass


class RowsScoredCommonMismatch(CalibrationSourceError):
    code = "ROWS_SCORED_COMMON_MISMATCH"


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
    pre_level_mps: float | None
    post_level_mps: float | None
    pre_mean_mps: float | None
    post_ticks: list[int]
    rows: list[dict[str, object]]
    exclusion_reason: str = ""
    metadata: dict[str, object] | None = None


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


def parse_certified_full(value: object) -> tuple[bool | None, str]:
    if isinstance(value, bool):
        return value, "VALID"
    if value is None:
        return None, "ABSENT_CERTIFICATION"
    text = str(value)
    if text in CERT_TRUE_TEXT:
        return True, "VALID"
    if text in CERT_FALSE_TEXT:
        return False, "VALID"
    return None, "ABSENT_CERTIFICATION"


def canonical_feature_ts_ns(row: Mapping[str, object]) -> tuple[int | None, str]:
    raw = row.get("feature_ts_ns")
    if raw is None or str(raw) == "":
        return None, "ABSENT_FEATURE_TS_NS"
    try:
        value = int(str(raw))
    except (TypeError, ValueError):
        return None, "ABSENT_FEATURE_TS_NS"
    return value, "VALID"


def _row_alignment_ledger(row: Mapping[str, object], feature_ts_ns: int | None) -> dict[str, object]:
    tick_raw = row.get("tick")
    ts = _num(row.get("ts_s"))
    ledger: dict[str, object] = {
        "alignment_status": "VALID",
        "alignment_reason": "",
        "nearest_tick": None,
        "tick_mismatch": None,
        "tick_mismatch_ns": None,
    }
    if feature_ts_ns is None:
        ledger["alignment_status"] = "ABSENT"
        ledger["alignment_reason"] = "ABSENT_FEATURE_TS_NS"
        return ledger
    nearest_tick = int(round(feature_ts_ns / DT_NS))
    ledger["nearest_tick"] = nearest_tick
    if tick_raw is not None and str(tick_raw) != "":
        try:
            tick = int(tick_raw)
        except (TypeError, ValueError):
            ledger["alignment_status"] = "MISMATCH"
            ledger["alignment_reason"] = "INVALID_TICK"
            return ledger
        mismatch = tick - nearest_tick
        ledger["tick_mismatch"] = mismatch
        ledger["tick_mismatch_ns"] = mismatch * DT_NS
        if abs(mismatch) > 1:
            ledger["alignment_status"] = "MISMATCH"
            ledger["alignment_reason"] = "FEATURE_CONTROL_TICK_MISMATCH_GT_1"
    elif ts is not None:
        mismatch_ns = int(round(ts * 1_000_000_000)) - feature_ts_ns
        ledger["tick_mismatch_ns"] = mismatch_ns
        if abs(mismatch_ns) > DT_NS:
            ledger["alignment_status"] = "MISMATCH"
            ledger["alignment_reason"] = "FEATURE_CONTROL_TIME_MISMATCH_GT_1_TICK"
    return ledger


def _immutable_exposure_key(row: Mapping[str, object], feature_ts_ns: int | None) -> tuple[str, str] | None:
    if feature_ts_ns is None:
        return None
    flight_id = str(row.get("flight_id", ""))
    return (flight_id, str(feature_ts_ns))


def normalize_rows_with_metadata(rows: Sequence[Mapping[str, object]]) -> tuple[list[dict[str, object]], dict[str, object]]:
    out: list[dict[str, object]] = []
    discarded: list[dict[str, object]] = []
    mismatch_ledger: list[dict[str, object]] = []
    absent_feature_rows: list[dict[str, object]] = []
    absent_cert_rows: list[dict[str, object]] = []
    seen_exposures: set[tuple[str, str]] = set()
    for index, row in enumerate(rows):
        new = dict(row)
        tick_raw = new.get("tick")
        if tick_raw is None:
            tick_raw = index
        new["tick"] = int(tick_raw)
        if _num(new.get("ts_s")) is None:
            new["ts_s"] = new["tick"] * DT_S
        feature_ts_ns, feature_status = canonical_feature_ts_ns(new)
        new["feature_ts_status"] = feature_status
        new["feature_ts_absent_reason"] = "" if feature_status == "VALID" else feature_status
        if feature_ts_ns is not None:
            new["feature_ts_ns"] = feature_ts_ns
        else:
            new.pop("feature_ts_ns", None)
            absent_feature_rows.append({"row_key": new.get("row_key", f"input_{index:06d}"), "reason": feature_status})
        cert_value, cert_status = parse_certified_full(new.get("certified_full"))
        new["certified_full_parsed"] = cert_value
        new["certification_status"] = "CERTIFIED_TRUE" if cert_value is True else "CERTIFIED_FALSE" if cert_value is False else cert_status
        new["certification_absent_reason"] = "" if cert_status == "VALID" else cert_status
        if cert_value is None:
            absent_cert_rows.append({"row_key": new.get("row_key", f"input_{index:06d}"), "reason": cert_status, "raw": new.get("certified_full")})
        alignment = _row_alignment_ledger(new, feature_ts_ns)
        new.update(alignment)
        if alignment["alignment_status"] == "MISMATCH":
            mismatch_ledger.append({"row_key": new.get("row_key", f"input_{index:06d}"), **alignment})
        exposure_key = _immutable_exposure_key(new, feature_ts_ns)
        if exposure_key is not None and exposure_key in seen_exposures:
            discarded.append({
                "discarded_row_key": new.get("row_key", f"input_{index:06d}"),
                "feature_ts_ns": feature_ts_ns,
                "reason": "DUPLICATE_EXPOSURE_FIRST_WINS",
            })
            continue
        if exposure_key is not None:
            seen_exposures.add(exposure_key)
        if _num(new.get("v_ref_up_mps")) is None:
            v_body_z = _num(new.get("setpoint_v_body_z"))
            level_pitch = _num(new.get("level_pitch"))
            level_roll = _num(new.get("level_roll"))
            if v_body_z is not None and level_pitch is not None and level_roll is not None:
                new["v_ref_up_mps"] = world_up_from_body_z(v_body_z, level_pitch, level_roll)
        if not new.get("row_key"):
            new["row_key"] = f"tick_{new['tick']:06d}"
        out.append(new)
    meta = {
        "discarded_rebroadcasts": discarded,
        "discarded_rebroadcast_count": len(discarded),
        "mismatch_ledger": mismatch_ledger,
        "mismatch_count": len(mismatch_ledger),
        "absent_feature_ts_rows": absent_feature_rows,
        "absent_certification_rows": absent_cert_rows,
    }
    return sorted(out, key=lambda r: int(r["tick"])), meta


def normalize_rows(rows: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    return normalize_rows_with_metadata(rows)[0]


def _certified_history(rows: Sequence[Mapping[str, object]], anchor_ts_s: float) -> list[tuple[float, float]]:
    history: list[tuple[float, int, float]] = []
    for order, row in enumerate(rows):
        cert_value = row.get("certified_full_parsed")
        if cert_value is None and "certified_full_parsed" not in row:
            cert_value, _status = parse_certified_full(row.get("certified_full"))
        if cert_value is not True:
            continue
        feature_ts_ns, feature_status = canonical_feature_ts_ns(row)
        if feature_status != "VALID":
            continue
        ts = _num(row.get("ts_s"))
        e_meas = _num(row.get("e_meas_m"))
        if ts is None or e_meas is None:
            continue
        if ts <= anchor_ts_s:
            history.append((ts, order, e_meas))
    history.sort(key=lambda row: (row[0], row[1]))
    deduped: list[tuple[float, float]] = []
    for ts, _order, e_meas in history:
        if deduped and ts <= deduped[-1][0]:
            continue
        deduped.append((ts, e_meas))
    return deduped


def _fresh_tail(history: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
    if len(history) < 2:
        return list(history)
    i = len(history) - 1
    while i > 0 and history[i][0] - history[i - 1][0] <= RATE_MAX_GAP_S:
        i -= 1
    return list(history[i:])


def reconstruct_v_full_raw(rows: Sequence[Mapping[str, object]], anchor_ts_s: float) -> tuple[float | None, str, dict[str, object]]:
    history = _certified_history(rows, anchor_ts_s)
    fresh_tail = _fresh_tail(history)
    recent = fresh_tail[-RATE_LAST_SAMPLE_CAP:]
    xs = [ts for ts, _ in recent]
    ys = [e for _, e in recent]
    span = (max(xs) - min(xs)) if xs else 0.0
    meta = {
        "history_samples": len(history),
        "fresh_tail_samples": len(fresh_tail),
        "recent_samples": len(recent),
        "fresh_tail_span_s": span,
        "max_gap_s": RATE_MAX_GAP_S,
        "last_sample_cap": RATE_LAST_SAMPLE_CAP,
    }
    if len(xs) < RATE_MIN_SAMPLES:
        return None, "ABSENT_RESPONSE", meta
    slope = robust_slope(xs, ys)
    if slope is None:
        return None, "ABSENT_RESPONSE", meta
    return -slope, "VALID", meta


def _trace_for_row(row: Mapping[str, object]) -> dict[str, object]:
    missing = [field for field in TRACE_FIELDS if field not in row]
    blank = [field for field in TRACE_FIELDS if field in row and str(row.get(field, "")) == ""]
    untyped: list[str] = []
    for field in ("adapter_input_v_body_z", "post_limit_command_v_body_z"):
        if field in row and str(row.get(field, "")) != "" and _num(row.get(field)) is None:
            untyped.append(field)
    for field, values in TRACE_VALUE_SETS.items():
        if field in row and str(row.get(field, "")) != "" and str(row.get(field)) not in values:
            untyped.append(field)
    complete = not missing and not blank and not untyped
    return {
        "trace_complete": complete,
        "missing_trace_fields": ";".join(missing),
        "blank_trace_fields": ";".join(blank),
        "untyped_trace_fields": ";".join(sorted(set(untyped))),
        **{field: row.get(field, "") for field in TRACE_FIELDS},
    }


def detect_step_windows(rows_in: Sequence[Mapping[str, object]], sentinel_keys: Iterable[str] = ()) -> list[StepWindow]:
    rows, input_meta = normalize_rows_with_metadata(rows_in)
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
            pre_mean = None
        else:
            pre_refs = [_num(r.get("v_ref_up_mps")) for r in pre_rows if r is not None]
            if any(v is None for v in pre_refs) or any(abs(float(v) - prev_ref) >= PRE_STABILITY_MPS for v in pre_refs if v is not None):
                reason = "ABSENT_INPUT"
                pre_mean = None
            else:
                pre_mean = statistics.fmean(float(v) for v in pre_refs if v is not None) if pre_refs else None
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
            feature_ts_ns, feature_status = canonical_feature_ts_ns(src)
            event_rows.append({
                "event_id": f"step_{seq:02d}",
                "row_key": event_key,
                "tick": int(src["tick"]),
                "relative_tick": int(src["tick"]) - tick,
                "ts_s": float(src["ts_s"]),
                "feature_ts_ns": feature_ts_ns,
                "feature_ts_status": feature_status,
                "feature_ts_absent_reason": src.get("feature_ts_absent_reason", "" if feature_status == "VALID" else feature_status),
                "certified_full_parsed": src.get("certified_full_parsed"),
                "certification_status": src.get("certification_status", ""),
                "certification_absent_reason": src.get("certification_absent_reason", ""),
                "alignment_status": src.get("alignment_status", ""),
                "alignment_reason": src.get("alignment_reason", ""),
                "nearest_tick": src.get("nearest_tick"),
                "tick_mismatch": src.get("tick_mismatch"),
                "tick_mismatch_ns": src.get("tick_mismatch_ns"),
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
            pre_level_mps=float(prev_ref) if prev_ref is not None else None,
            post_level_mps=float(post_ref) if post_ref is not None else None,
            pre_mean_mps=float(pre_mean) if pre_mean is not None else None,
            post_ticks=post_ticks,
            rows=event_rows,
            exclusion_reason=reason,
            metadata={
                "pre_mean_absent_reason": "ABSENT_INPUT" if pre_mean is None else "",
                **input_meta,
            },
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
    if window.pre_mean_mps is None or window.post_level_mps is None:
        return {}
    refs = _refs_by_tick(window)
    v_hat = candidate.g * float(window.pre_mean_mps)
    preds: dict[int, float] = {}
    for tick in window.post_ticks:
        ref_tick = tick - candidate.lag_ticks
        if ref_tick < window.tick:
            ref = float(window.pre_mean_mps)
        else:
            ref = refs.get(ref_tick, float(window.post_level_mps))
        v_hat = v_hat + (DT_S / candidate.tau_s) * (candidate.g * ref - v_hat)
        preds[tick] = v_hat
    return preds


def candidate_score(windows: Sequence[StepWindow], candidate: Candidate, fit_directions: set[str] | None = None) -> dict[str, object]:
    scoring_rows = 0
    post_lag_rows = 0
    sse = 0.0
    max_post_lag_horizon_s = 0.0
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
            meas = _num(row.get("v_meas_mps"))
            pred = preds.get(int(row["tick"]))
            if meas is None or pred is None:
                continue
            scoring_rows += 1
            if rel_tick >= candidate.lag_ticks:
                post_lag_rows += 1
                max_post_lag_horizon_s = max(max_post_lag_horizon_s, (rel_tick - candidate.lag_ticks) * DT_S)
            sse += (meas - pred) ** 2
    eligible = post_lag_rows >= MIN_VALID_ROWS and max_post_lag_horizon_s >= candidate.tau_s
    if eligible:
        failing_rule = ""
    elif post_lag_rows < MIN_VALID_ROWS:
        failing_rule = "INSUFFICIENT_POST_LAG_ROWS"
    else:
        failing_rule = "HORIZON_LT_TAU"
    return {
        "g": candidate.g,
        "tau_s": candidate.tau_s,
        "L_ticks": candidate.lag_ticks,
        "rows_used": scoring_rows,
        "scoring_rows": scoring_rows,
        "rows_scored_common": scoring_rows,
        "post_lag_rows": post_lag_rows,
        "max_horizon_s": max_post_lag_horizon_s,
        "max_post_lag_horizon_s": max_post_lag_horizon_s,
        "sse": sse,
        "mse": (sse / scoring_rows) if scoring_rows else None,
        "rms_mps": math.sqrt(sse / scoring_rows) if scoring_rows else None,
        "eligible": eligible,
        "candidate_type": "ELIGIBLE" if eligible else "UNIDENTIFIABLE",
        "failing_rule": failing_rule,
        "ineligible_reason": failing_rule,
    }


def _score_key(row: Mapping[str, object]) -> tuple[float, float, int]:
    return (float(row["g"]), float(row["tau_s"]), int(row["L_ticks"]))


def _candidate_neighbor_keys(row: Mapping[str, object]) -> list[tuple[str, tuple[float, float, int]]]:
    g, tau, lag = _score_key(row)
    return [
        ("g_minus", (round(g - 0.05, 2), tau, lag)),
        ("g_plus", (round(g + 0.05, 2), tau, lag)),
        ("tau_minus", (g, round(tau - 0.02, 2), lag)),
        ("tau_plus", (g, round(tau + 0.02, 2), lag)),
        ("L_minus", (g, tau, lag - 1)),
        ("L_plus", (g, tau, lag + 1)),
    ]


def local_open_face(best: Mapping[str, object], score_rows: Sequence[Mapping[str, object]]) -> tuple[bool, list[dict[str, object]]]:
    by_key = {_score_key(row): row for row in score_rows}
    checks: list[dict[str, object]] = []
    open_face = False
    for face, key in _candidate_neighbor_keys(best):
        g, tau, lag = key
        in_domain = g in G_VALUES and tau in TAU_VALUES and lag in L_VALUES
        neighbor = by_key.get(key)
        eligible = bool(neighbor and neighbor.get("eligible"))
        reason = ""
        if not in_domain:
            reason = "OUTSIDE_DOMAIN"
            open_face = True
        elif not eligible:
            reason = str(neighbor.get("ineligible_reason", "INELIGIBLE_NEIGHBOR")) if neighbor else "MISSING_NEIGHBOR"
            open_face = True
        checks.append({
            "face": face,
            "g": g,
            "tau_s": tau,
            "L_ticks": lag,
            "in_domain": in_domain,
            "eligible": eligible,
            "open_reason": reason,
        })
    return open_face, checks


def _strictly_better_loss(lhs: float, rhs: float) -> bool:
    if lhs >= rhs:
        return False
    denom = max(abs(lhs), abs(rhs), 1e-300)
    return (rhs - lhs) / denom > NULL_TIE_REL_TOL


def _losses_tied(lhs: float, rhs: float) -> bool:
    denom = max(abs(lhs), abs(rhs), 1e-300)
    return abs(lhs - rhs) / denom <= NULL_TIE_REL_TOL


def assert_rows_scored_common(score_rows: Sequence[Mapping[str, object]]) -> int:
    common_counts = {int(row["rows_scored_common"]) for row in score_rows}
    if len(common_counts) > 1:
        raise RowsScoredCommonMismatch(f"ROWS_SCORED_COMMON_MISMATCH: {sorted(common_counts)}")
    return next(iter(common_counts)) if common_counts else 0


def fit_response_model(windows: Sequence[StepWindow], fit_directions: set[str] | None = None) -> dict[str, object]:
    detected = sorted({w.direction for w in windows})
    usable = [w for w in windows if not w.exclusion_reason and (fit_directions is None or w.direction in fit_directions)]
    score_rows = [candidate_score(usable, cand, fit_directions) for cand in candidate_grid()]
    rows_scored_common = assert_rows_scored_common(score_rows)
    eligible = [row for row in score_rows if row["eligible"]]
    null_scores = [row for row in score_rows if row["eligible"] and float(row["g"]) == 0.0]
    null_best = min(null_scores, key=lambda r: float(r["sse"])) if null_scores else None
    positive = [row for row in eligible if float(row["g"]) > 0.0]
    positive_best = min(positive, key=lambda r: float(r["sse"])) if positive else None
    global_best = min(eligible, key=lambda r: float(r["sse"])) if eligible else None
    global_minimizers = [row for row in eligible if global_best is not None and _losses_tied(float(row["sse"]), float(global_best["sse"]))]
    positive_global_minimizers = [row for row in global_minimizers if float(row["g"]) > 0.0]
    distinct_positive_global_minimizers = sorted({_score_key(row) for row in positive_global_minimizers})
    prediction_equivalence_status = (
        "SINGLE_MINIMIZER"
        if len(distinct_positive_global_minimizers) <= 1
        else "NOT_EVALUATED_NO_PREREG_EQUIVALENCE"
    )
    null_strictly_better = (
        null_best is not None
        and all(_strictly_better_loss(float(null_best["sse"]), float(row["sse"])) for row in positive)
        and not positive_global_minimizers
    )
    null_tied_positive = (
        null_best is not None
        and any(_losses_tied(float(null_best["sse"]), float(row["sse"])) for row in positive)
    )
    open_face = False
    open_face_checks: list[dict[str, object]] = []
    if not usable or not eligible:
        status = "UNCALIBRATABLE"
        best = None
    elif null_strictly_better:
        status = "NULL_CALIBRATED"
        best = null_best
    elif positive_best is not None:
        best = positive_best
        open_face, open_face_checks = local_open_face(best, score_rows)
        if len(distinct_positive_global_minimizers) > 1:
            status = "NOT_IDENTIFIED"
        elif null_tied_positive:
            status = "NOT_IDENTIFIED"
        elif open_face:
            status = "NOT_IDENTIFIED"
        else:
            status = "CALIBRATED"
    else:
        status = "NULL_CALIBRATED"
        best = null_best
    return {
        "calibration_status": status,
        "best": best,
        "null_model_score": null_best,
        "null_tie_rel_tol": NULL_TIE_REL_TOL,
        "null_strictly_better_than_positive": null_strictly_better,
        "null_tied_positive": null_tied_positive,
        "global_minimizer_count": len(global_minimizers),
        "global_minimizer_coordinates": [
            {"g": g, "tau_s": tau, "L_ticks": lag}
            for g, tau, lag in sorted({_score_key(row) for row in global_minimizers})
        ],
        "positive_global_minimizer_count": len(distinct_positive_global_minimizers),
        "prediction_equivalence_status": prediction_equivalence_status,
        "local_open_face": open_face,
        "local_open_face_checks": open_face_checks,
        "detected_directions": detected,
        "fit_directions": sorted(fit_directions) if fit_directions else detected,
        "candidate_count": len(score_rows),
        "rows_scored_common": rows_scored_common,
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
        "metadata": window.metadata or {},
    }


def read_csv_rows(path: Path) -> list[dict[str, object]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def read_sentinel_keys(path: Path) -> list[str]:
    rows = read_csv_rows(path)
    keys: list[str] = []
    for row in rows:
        key = row.get("row_key")
        if not key and row.get("flight_id") and row.get("frame_id") and row.get("feature_ts_ns"):
            key = f"{row['flight_id']}|frame={row['frame_id']}|feature_ts_ns={row['feature_ts_ns']}"
        if key:
            keys.append(str(key))
    return keys


def input_digest_rows(paths: Sequence[str]) -> list[dict[str, str]]:
    rows = []
    for value in paths:
        if value.startswith("synthetic://"):
            digest = sha256_bytes(value.encode("utf-8"))
        else:
            digest = sha256_file(Path(value))
        rows.append({"path": value, "sha256": digest})
    return rows


def source_bytes_commit(repo: Path) -> str:
    return git(repo, ["log", "-n", "1", "--format=%H", "--", SOURCE_GENERATOR_PATH])


def provenance_packet(repo: Path, input_paths: Sequence[str], exact_command: str, *, artifact_commit: str | None = None) -> dict[str, object]:
    execution_tip = git(repo, ["rev-parse", "HEAD"])
    if not is_ancestor(repo, REG1_COMMIT, execution_tip):
        raise CalibrationSourceError(f"REG-1 commit {REG1_COMMIT} is not an ancestor of {execution_tip}")
    source_commit = source_bytes_commit(repo)
    if not is_ancestor(repo, REG1_COMMIT, source_commit):
        raise CalibrationSourceError(f"REG-1 commit {REG1_COMMIT} is not an ancestor of source commit {source_commit}")
    if not is_ancestor(repo, source_commit, execution_tip):
        raise CalibrationSourceError(f"source commit {source_commit} is not an ancestor of execution tip {execution_tip}")
    return {
        "source_generator_path": SOURCE_GENERATOR_PATH,
        "source_generator_commit": source_commit,
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
    packet = provenance_packet(repo, ["synthetic://reg1v23-detector-dry-run"], "python tuning/reg1v2_calibration_source_generator.py --synthetic-dry-run")
    return {
        "artifact": "REG1V23_CALIBRATION_SOURCE_SYNTHETIC_DRY_RUN",
        "diagnostic_token": "DIAGNOSTIC",
        "packet_scope": "SYNTHETIC_DIAGNOSTIC",
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
    parser = argparse.ArgumentParser(description="REG-1v2.3 calibration source generator")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--synthetic-dry-run", action="store_true")
    parser.add_argument("--input-csv")
    parser.add_argument("--sentinel-keys-csv")
    parser.add_argument("--sentinel-keys-digest")
    parser.add_argument("--sentinel-keys-commit")
    parser.add_argument("--out-dir")
    parser.add_argument("--direction", choices=["up", "down"])
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    if args.synthetic_dry_run:
        print(json.dumps(synthetic_dry_run(repo), indent=2, sort_keys=True))
        return 0
    if not args.input_csv or not args.out_dir:
        parser.error("--input-csv and --out-dir are required outside --synthetic-dry-run")
    if args.direction != PRIMARY_FIT_DIRECTION:
        raise CalibrationSourceError(f"DIRECTION_REFUSED: explicit --direction {PRIMARY_FIT_DIRECTION} is required")
    if not args.sentinel_keys_csv or not args.sentinel_keys_digest or not args.sentinel_keys_commit:
        raise CalibrationSourceError("SENTINEL_BINDING_MISSING: --sentinel-keys-csv, --sentinel-keys-digest, and --sentinel-keys-commit are required")
    input_path = Path(args.input_csv).resolve()
    rows = read_csv_rows(input_path)
    input_paths = [str(input_path)]
    sentinel_path = Path(args.sentinel_keys_csv).resolve()
    actual_sentinel_digest = sha256_file(sentinel_path)
    if actual_sentinel_digest != args.sentinel_keys_digest:
        raise CalibrationSourceError("SENTINEL_DIGEST_MISMATCH")
    git(repo, ["cat-file", "-e", f"{args.sentinel_keys_commit}^{{commit}}"])
    sentinel_keys = read_sentinel_keys(sentinel_path)
    input_paths.append(str(sentinel_path))
    windows = detect_step_windows(rows, sentinel_keys=sentinel_keys)
    calibration_keys = sorted({str(row["row_key"]) for window in windows for row in window.rows})
    sentinel_key_set = sorted({str(key) for key in sentinel_keys})
    sentinel_intersection = sorted(set(calibration_keys).intersection(sentinel_key_set))
    if sentinel_intersection:
        raise CalibrationSourceError(f"SENTINEL_OVERLAP: {sentinel_intersection}")
    fit_dirs = {args.direction}
    fit = fit_response_model(windows, fit_dirs)
    packet = {
        "artifact": "REG1V23_CALIBRATION_PACKET",
        "diagnostic_token": "DIAGNOSTIC",
        "packet_scope": "REG2_CALIBRATION_CANDIDATE",
        "fit_summary": {k: v for k, v in fit.items() if k not in {"score_rows"}},
        "calibration_key_set": calibration_keys,
        "sentinel_key_count": len(sentinel_keys),
        "sentinel_key_set": sentinel_key_set,
        "sentinel_key_intersection": sentinel_intersection,
        "sentinel_keys_digest": actual_sentinel_digest,
        "sentinel_keys_commit": args.sentinel_keys_commit,
        "direction": args.direction,
        "primary_fit_direction": PRIMARY_FIT_DIRECTION,
        "provenance": provenance_packet(repo, input_paths, " ".join(sys.argv if argv is None else [sys.argv[0], *argv])),
    }
    write_packet(Path(args.out_dir), packet, fit["score_rows"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
