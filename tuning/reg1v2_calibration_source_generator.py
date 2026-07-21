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

GOVERNING_REG1_COMMIT = "ca1c161cf1b31b8f21ba4e47a5a0ec9951fe1976"
REG1_COMMIT = GOVERNING_REG1_COMMIT
SOURCE_GENERATOR_PATH = "tuning/reg1v2_calibration_source_generator.py"
CANONICAL_SCORING_KEY_SCHEMA = "reg1v25_support_key_json_array_v1"
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
SSE_ABS_FLOOR = 1e-18
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


class ScoringSupportMismatch(CalibrationSourceError):
    code = "SCORING_SUPPORT_SHA256_MISMATCH"


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


def _causal_floor_control_tick(feature_ts_ns: int, control_ticks: set[int]) -> int | None:
    floor_tick = feature_ts_ns // DT_NS
    candidates = [tick for tick in control_ticks if tick <= floor_tick]
    return max(candidates) if candidates else None


def _row_alignment_ledger(row: Mapping[str, object], feature_ts_ns: int | None, control_ticks: set[int]) -> dict[str, object]:
    original_tick = int(row["tick"])
    ledger: dict[str, object] = {
        "alignment_status": "VALID",
        "alignment_reason": "",
        "causal_floor_tick": None,
        "assigned_control_tick": None,
        "control_tick_original": original_tick,
        "tick_mismatch_ns": None,
        "abs_tick_mismatch_ns": None,
    }
    if feature_ts_ns is None:
        ledger["alignment_status"] = "ABSENT"
        ledger["alignment_reason"] = "ABSENT_FEATURE_TS_NS"
        return ledger
    assigned_tick = _causal_floor_control_tick(feature_ts_ns, control_ticks)
    ledger["causal_floor_tick"] = assigned_tick
    ledger["assigned_control_tick"] = assigned_tick
    if assigned_tick is None:
        ledger["alignment_status"] = "OFF_WINDOW"
        ledger["alignment_reason"] = "OFF_WINDOW"
        return ledger
    mismatch_ns = feature_ts_ns - assigned_tick * DT_NS
    ledger["tick_mismatch_ns"] = mismatch_ns
    ledger["abs_tick_mismatch_ns"] = abs(mismatch_ns)
    if mismatch_ns < 0 or mismatch_ns > DT_NS:
        ledger["alignment_status"] = "OFF_WINDOW"
        ledger["alignment_reason"] = "OFF_WINDOW"
    return ledger


def exposure_key_components(row: Mapping[str, object], feature_ts_ns: int | None) -> tuple[tuple[str, int] | None, list[str]]:
    missing: list[str] = []
    flight_id = row.get("flight_id")
    if flight_id is None or str(flight_id) == "":
        missing.append("flight_id")
    if feature_ts_ns is None:
        missing.append("feature_ts_ns")
    if missing:
        return None, missing
    return (str(flight_id), int(feature_ts_ns)), []


def format_exposure_key(key: tuple[str, int]) -> str:
    flight_id, feature_ts_ns = key
    return f"{flight_id}|feature_ts_ns={feature_ts_ns}"


def _payload_for_identity(row: Mapping[str, object]) -> dict[str, object]:
    fields = (
        "frame_id",
        "e_meas_m",
        "v_ref_up_mps",
        "setpoint_v_body_z",
        "level_pitch",
        "level_roll",
        "certified_full",
        *TRACE_FIELDS,
    )
    return {field: row.get(field, None) for field in fields}


def _payload_sha256(row: Mapping[str, object]) -> str:
    return sha256_bytes(json.dumps(_payload_for_identity(row), sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"))


def normalize_rows_with_metadata(rows: Sequence[Mapping[str, object]]) -> tuple[list[dict[str, object]], dict[str, object]]:
    raw_control_ticks: set[int] = set()
    prepared: list[dict[str, object]] = []
    absent_feature_rows: list[dict[str, object]] = []
    absent_cert_rows: list[dict[str, object]] = []
    for index, row in enumerate(rows):
        tick_raw = row.get("tick")
        raw_control_ticks.add(int(tick_raw) if tick_raw is not None and str(tick_raw) != "" else index)
        new = dict(row)
        new["_file_order"] = index
        new["tick"] = int(tick_raw) if tick_raw is not None and str(tick_raw) != "" else index
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
        exposure_key, missing_components = exposure_key_components(new, feature_ts_ns)
        new["exposure_key_tuple"] = exposure_key
        new["exposure_key_missing_components"] = ";".join(missing_components)
        new["payload_sha256"] = _payload_sha256(new)
        prepared.append(new)

    excluded: list[dict[str, object]] = []
    discarded: list[dict[str, object]] = []
    mismatch_ledger: list[dict[str, object]] = []
    primary_groups: dict[tuple[str, int], list[dict[str, object]]] = {}
    frame_groups: dict[tuple[str, str], set[int]] = {}
    for row in prepared:
        exposure_key = row.get("exposure_key_tuple")
        if exposure_key is None:
            excluded.append({
                "row_key": row.get("row_key", f"input_{row['_file_order']:06d}"),
                "reason": "ABSENT_EXPOSURE_KEY",
                "missing_components": row["exposure_key_missing_components"],
            })
            continue
        primary_groups.setdefault(exposure_key, []).append(row)
        frame_id = row.get("frame_id")
        if frame_id is not None and str(frame_id) != "":
            frame_groups.setdefault((str(row.get("flight_id", "")), str(frame_id)), set()).add(int(row["feature_ts_ns"]))

    conflicting_primary = {
        key for key, group in primary_groups.items()
        if len({str(row["payload_sha256"]) for row in group}) > 1
    }
    conflicting_frame_ids = {
        frame_key for frame_key, ts_values in frame_groups.items() if len(ts_values) > 1
    }
    frame_conflict_rows = {
        id(row)
        for row in prepared
        if row.get("frame_id") is not None
        and (str(row.get("flight_id", "")), str(row.get("frame_id"))) in conflicting_frame_ids
    }
    retained_primary: set[tuple[str, int]] = set()
    out: list[dict[str, object]] = []
    for row in prepared:
        exposure_key = row.get("exposure_key_tuple")
        if exposure_key is None:
            continue
        exposure_key_text = format_exposure_key(exposure_key)
        row["exposure_key"] = exposure_key_text
        if exposure_key in conflicting_primary:
            excluded.append({
                "row_key": row.get("row_key", f"input_{row['_file_order']:06d}"),
                "exposure_key": exposure_key_text,
                "reason": "EXPOSURE_PAYLOAD_CONFLICT",
            })
            continue
        if id(row) in frame_conflict_rows:
            excluded.append({
                "row_key": row.get("row_key", f"input_{row['_file_order']:06d}"),
                "exposure_key": exposure_key_text,
                "reason": "FRAME_ID_COLLISION",
            })
            continue
        if exposure_key in retained_primary:
            discarded.append({
                "discarded_row_key": row.get("row_key", f"input_{row['_file_order']:06d}"),
                "exposure_key": exposure_key_text,
                "feature_ts_ns": int(row["feature_ts_ns"]),
                "reason": "DUPLICATE_EXPOSURE_FIRST_WINS",
            })
            continue
        retained_primary.add(exposure_key)
        alignment = _row_alignment_ledger(row, int(row["feature_ts_ns"]), raw_control_ticks)
        row.update(alignment)
        if alignment["alignment_status"] in {"MISMATCH", "OFF_WINDOW"} or alignment.get("tick_mismatch_ns") not in {None, 0}:
            mismatch_ledger.append({"row_key": row.get("row_key", f"input_{row['_file_order']:06d}"), **alignment})
        if alignment["alignment_status"] == "OFF_WINDOW":
            excluded.append({
                "row_key": row.get("row_key", f"input_{row['_file_order']:06d}"),
                "exposure_key": exposure_key_text,
                "reason": "OFF_WINDOW",
            })
            continue
        row["assigned_control_tick"] = int(alignment["assigned_control_tick"])
        row["tick"] = int(alignment["assigned_control_tick"])
        row["ts_s"] = row["tick"] * DT_S
        if _num(row.get("v_ref_up_mps")) is None:
            v_body_z = _num(row.get("setpoint_v_body_z"))
            level_pitch = _num(row.get("level_pitch"))
            level_roll = _num(row.get("level_roll"))
            if v_body_z is not None and level_pitch is not None and level_roll is not None:
                row["v_ref_up_mps"] = world_up_from_body_z(v_body_z, level_pitch, level_roll)
        if not row.get("row_key"):
            row["row_key"] = f"tick_{row['tick']:06d}"
        row.pop("_file_order", None)
        row.pop("exposure_key_tuple", None)
        out.append(row)
    meta = {
        "discarded_rebroadcasts": discarded,
        "discarded_rebroadcast_count": len(discarded),
        "excluded_exposure_rows": excluded,
        "excluded_exposure_count": len(excluded),
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
    rows_norm, normalization_meta = normalize_rows_with_metadata(rows)
    history = _certified_history(rows_norm, anchor_ts_s)
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
        "normalization": normalization_meta,
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
    by_tick: dict[int, dict[str, object]] = {}
    for row in rows:
        tick = int(row["tick"])
        if tick not in by_tick:
            by_tick[tick] = row
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
            row_key = str(src.get("row_key"))
            relative_tick = int(src["tick"]) - tick
            sentinel_event_key = serialize_scoring_key((
                f"step_{seq:02d}",
                str(src["flight_id"]),
                int(src["feature_ts_ns"]),
                int(src["assigned_control_tick"]),
            ))
            if sentinel_event_key in sentinel_set:
                reason = "SENTINEL_DISJOINT"
            v_meas, response_status, response_meta = reconstruct_v_full_raw(rows, float(src["ts_s"]))
            trace = _trace_for_row(src)
            feature_ts_ns, feature_status = canonical_feature_ts_ns(src)
            event_rows.append({
                "event_id": f"step_{seq:02d}",
                "row_key": row_key,
                "flight_id": src.get("flight_id"),
                "frame_id": src.get("frame_id"),
                "tick": int(src["tick"]),
                "assigned_control_tick": int(src["assigned_control_tick"]),
                "relative_tick": relative_tick,
                "ts_s": float(src["ts_s"]),
                "feature_ts_ns": feature_ts_ns,
                "exposure_key": src.get("exposure_key", ""),
                "feature_ts_status": feature_status,
                "feature_ts_absent_reason": src.get("feature_ts_absent_reason", "" if feature_status == "VALID" else feature_status),
                "certified_full_parsed": src.get("certified_full_parsed"),
                "certification_status": src.get("certification_status", ""),
                "certification_absent_reason": src.get("certification_absent_reason", ""),
                "alignment_status": src.get("alignment_status", ""),
                "alignment_reason": src.get("alignment_reason", ""),
                "causal_floor_tick": src.get("causal_floor_tick"),
                "control_tick_original": src.get("control_tick_original"),
                "tick_mismatch_ns": src.get("tick_mismatch_ns"),
                "abs_tick_mismatch_ns": src.get("abs_tick_mismatch_ns"),
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


def candidate_score(
    windows: Sequence[StepWindow],
    candidate: Candidate,
    fit_directions: set[str] | None = None,
    *,
    support_count: int | None = None,
    support_sha256: str | None = None,
) -> dict[str, object]:
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
    if support_count is None or support_sha256 is None:
        ledger = support_ledger(windows, fit_directions)
        keys = support_keys_from_ledger(ledger)
        support_count = len(keys)
        support_sha256 = scoring_support_sha256_from_keys(keys)
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
        "rows_scored_common": support_count,
        "scoring_support_sha256": support_sha256,
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


def scoring_key_tuple(window: StepWindow, row: Mapping[str, object]) -> tuple[str, str, int, int]:
    return (
        str(window.event_id),
        str(row["flight_id"]),
        int(row["feature_ts_ns"]),
        int(row["assigned_control_tick"]),
    )


def serialize_scoring_key(key: tuple[str, str, int, int]) -> str:
    return json.dumps([key[0], key[1], key[2], key[3]], separators=(",", ":"), ensure_ascii=False)


def scoring_event_key(window: StepWindow, row: Mapping[str, object]) -> str:
    return serialize_scoring_key(scoring_key_tuple(window, row))


def scoring_support_bytes(keys: Sequence[tuple[str, str, int, int]]) -> bytes:
    records = [serialize_scoring_key(key) for key in sorted(keys)]
    payload = "".join(f"{record}\n" for record in records)
    return payload.encode("utf-8")


def scoring_support_sha256_from_keys(keys: Sequence[tuple[str, str, int, int]]) -> str:
    payload = scoring_support_bytes(keys)
    return sha256_bytes(payload)


def support_ledger(windows: Sequence[StepWindow], fit_directions: set[str] | None = None) -> list[dict[str, object]]:
    ledger: list[dict[str, object]] = []
    for window in windows:
        window_excluded = bool(window.exclusion_reason)
        direction_excluded = fit_directions is not None and window.direction not in fit_directions
        for row in window.rows:
            response_valid = row.get("response_status") == "VALID"
            trace_valid = bool(row.get("trace_complete"))
            included = not window_excluded and not direction_excluded and response_valid and trace_valid
            reason = ""
            if window_excluded:
                reason = window.exclusion_reason
            elif direction_excluded:
                reason = "OFF_SUPPORT_DIRECTION"
            elif not response_valid:
                reason = str(row.get("response_status", "ABSENT_RESPONSE"))
            elif not trace_valid:
                reason = "INCOMPLETE_TRACE"
            key = scoring_key_tuple(window, row)
            ledger.append({
                "window_id": window.event_id,
                "event_key": serialize_scoring_key(key),
                "flight_id": key[1],
                "feature_ts_ns": row.get("feature_ts_ns"),
                "assigned_control_tick": row.get("assigned_control_tick"),
                "relative_tick": row.get("relative_tick"),
                "response_validity_state": row.get("response_status"),
                "trace_validity_state": "VALID" if trace_valid else "INCOMPLETE",
                "included_in_objective": included,
                "exclusion_reason": reason,
            })
    return ledger


def support_keys_from_ledger(ledger: Sequence[Mapping[str, object]]) -> list[tuple[str, str, int, int]]:
    return [
        (str(row["window_id"]), str(row["flight_id"]), int(row["feature_ts_ns"]), int(row["assigned_control_tick"]))
        for row in ledger
        if row.get("included_in_objective")
    ]


def duplicate_scoring_key_count(keys: Sequence[tuple[str, str, int, int]]) -> int:
    return len(keys) - len(set(keys))


def assert_rows_scored_common(score_rows: Sequence[Mapping[str, object]]) -> int:
    common_counts = {int(row["rows_scored_common"]) for row in score_rows}
    if len(common_counts) > 1:
        raise RowsScoredCommonMismatch(f"ROWS_SCORED_COMMON_MISMATCH: {sorted(common_counts)}")
    support_hashes = {str(row["scoring_support_sha256"]) for row in score_rows}
    if len(support_hashes) > 1:
        raise ScoringSupportMismatch(f"SCORING_SUPPORT_SHA256_MISMATCH: {sorted(support_hashes)}")
    return next(iter(common_counts)) if common_counts else 0


def fit_response_model(windows: Sequence[StepWindow], fit_directions: set[str] | None = None) -> dict[str, object]:
    detected = sorted({w.direction for w in windows})
    usable = [w for w in windows if not w.exclusion_reason and (fit_directions is None or w.direction in fit_directions)]
    ledger = support_ledger(windows, fit_directions)
    ledger_support_keys = support_keys_from_ledger(ledger)
    dup_key_count = duplicate_scoring_key_count(ledger_support_keys)
    if dup_key_count:
        raise ScoringSupportMismatch(f"DUPLICATE_SCORING_KEY_COUNT: {dup_key_count}")
    ledger_support_sha256 = scoring_support_sha256_from_keys(ledger_support_keys)
    score_rows = [
        candidate_score(
            usable,
            cand,
            fit_directions,
            support_count=len(ledger_support_keys),
            support_sha256=ledger_support_sha256,
        )
        for cand in candidate_grid()
    ]
    rows_scored_common = assert_rows_scored_common(score_rows)
    scoring_support_sha256_values = {str(row["scoring_support_sha256"]) for row in score_rows}
    scoring_support_sha256 = next(iter(scoring_support_sha256_values)) if scoring_support_sha256_values else scoring_support_sha256_from_keys([])
    if scoring_support_sha256 != ledger_support_sha256:
        raise ScoringSupportMismatch(f"SCORING_SUPPORT_SHA256_MISMATCH_LEDGER: score={scoring_support_sha256} ledger={ledger_support_sha256}")
    eligible = [row for row in score_rows if row["eligible"]]
    null_scores = [row for row in score_rows if float(row["g"]) == 0.0]
    null_best = min(null_scores, key=lambda r: float(r["sse"])) if null_scores else None
    positive = [row for row in eligible if float(row["g"]) > 0.0]
    positive_best = min(positive, key=lambda r: float(r["sse"])) if positive else None
    null_loss = float(null_best["sse"]) if null_best is not None else None
    best_positive_loss = float(positive_best["sse"]) if positive_best is not None else None
    null_positive_gap = (best_positive_loss - null_loss) if best_positive_loss is not None and null_loss is not None else None
    null_tie_epsilon = (
        NULL_TIE_REL_TOL * max(best_positive_loss, null_loss, SSE_ABS_FLOOR)
        if best_positive_loss is not None and null_loss is not None
        else None
    )
    if best_positive_loss is None:
        null_tie_rule_result = "NO_POSITIVE_ELIGIBLE"
    elif null_positive_gap is not None and null_tie_epsilon is not None and null_positive_gap > null_tie_epsilon:
        null_tie_rule_result = "NULL_BETTER"
    elif null_positive_gap is not None and null_tie_epsilon is not None and abs(null_positive_gap) <= null_tie_epsilon:
        null_tie_rule_result = "TIE"
    else:
        null_tie_rule_result = "POSITIVE_BETTER"
    compared_losses = []
    if best_positive_loss is not None:
        compared_losses.append(best_positive_loss)
    if null_loss is not None:
        compared_losses.append(null_loss)
    global_loss = min(compared_losses) if compared_losses else None
    null_global_minimizer = null_best is not None and global_loss is not None and _losses_tied(float(null_best["sse"]), global_loss)
    positive_global_minimizers = [row for row in positive if global_loss is not None and _losses_tied(float(row["sse"]), global_loss)]
    distinct_positive_global_minimizers = sorted({_score_key(row) for row in positive_global_minimizers})
    global_minimizer_coordinates: list[dict[str, object]] = []
    if null_global_minimizer:
        global_minimizer_coordinates.append({"g": 0.0, "tau_s": None, "L_ticks": None, "class": "NULL_MANIFOLD"})
    global_minimizer_coordinates.extend(
        {"g": g, "tau_s": tau, "L_ticks": lag, "class": "POSITIVE_G"}
        for g, tau, lag in distinct_positive_global_minimizers
    )
    prediction_equivalence_status = (
        "SINGLE_MINIMIZER"
        if len(distinct_positive_global_minimizers) <= 1
        else "NOT_EVALUATED_NO_PREREG_EQUIVALENCE"
    )
    null_strictly_better = null_tie_rule_result in {"NULL_BETTER", "NO_POSITIVE_ELIGIBLE"} and null_best is not None and not positive_global_minimizers
    null_tied_positive = null_tie_rule_result == "TIE"
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
    model_class = "NULL_CONTRIBUTION" if status == "NULL_CALIBRATED" else "POSITIVE_GAIN" if status == "CALIBRATED" else "NOT_APPLICABLE"
    reg2_branch = {
        "model_class": model_class,
        "g": 0.0 if model_class == "NULL_CONTRIBUTION" else (float(best["g"]) if best else None),
        "tau_s": "NOT_APPLICABLE" if model_class == "NULL_CONTRIBUTION" else (float(best["tau_s"]) if best else None),
        "L_ticks": "NOT_APPLICABLE" if model_class == "NULL_CONTRIBUTION" else (int(best["L_ticks"]) if best else None),
        "profile_box": "NOT_APPLICABLE_NULL_CLASS" if model_class == "NULL_CONTRIBUTION" else ("PENDING_PROFILE_BOX" if model_class == "POSITIVE_GAIN" else None),
        "null_loss": null_loss,
        "best_positive_loss": best_positive_loss,
        "null_to_positive_loss_gap": null_positive_gap,
        "positive_global_minimizer_count": len(distinct_positive_global_minimizers),
        "null_tie_rule_result": null_tie_rule_result,
    }
    return {
        "calibration_status": status,
        "best": best,
        "null_model_score": null_best,
        "null_tie_rel_tol": NULL_TIE_REL_TOL,
        "sse_abs_floor": SSE_ABS_FLOOR,
        "null_loss": null_loss,
        "best_positive_loss": best_positive_loss,
        "null_to_positive_loss_gap": null_positive_gap,
        "null_tie_epsilon": null_tie_epsilon,
        "null_tie_rule_result": null_tie_rule_result,
        "reg2_branch": reg2_branch,
        "model_class": model_class,
        "null_strictly_better_than_positive": null_strictly_better,
        "null_tied_positive": null_tied_positive,
        "global_minimizer_count": len(global_minimizer_coordinates),
        "global_minimizer_coordinates": global_minimizer_coordinates,
        "positive_global_minimizer_count": len(distinct_positive_global_minimizers),
        "null_manifold_collapsed": True,
        "prediction_equivalence_status": prediction_equivalence_status,
        "local_open_face": open_face,
        "local_open_face_checks": open_face_checks,
        "detected_directions": detected,
        "fit_directions": sorted(fit_directions) if fit_directions else detected,
        "candidate_count": len(score_rows),
        "rows_scored_common": rows_scored_common,
        "scoring_support_sha256": scoring_support_sha256,
        "duplicate_scoring_key_count": dup_key_count,
        "calibration_key_schema": CANONICAL_SCORING_KEY_SCHEMA,
        "support_ledger": ledger,
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
        key = row.get("event_key") or row.get("row_key")
        if not key and row.get("window_id") and row.get("flight_id") and row.get("feature_ts_ns") and row.get("assigned_control_tick"):
            key = serialize_scoring_key((
                str(row["window_id"]),
                str(row["flight_id"]),
                int(str(row["feature_ts_ns"])),
                int(str(row["assigned_control_tick"])),
            ))
        if key:
            keys.append(str(key))
    return keys


def _repo_relative_path(repo: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError as exc:
        raise CalibrationSourceError("SENTINEL_PATH_OUTSIDE_REPO") from exc


def verify_sentinel_binding(
    repo: Path,
    *,
    artifact_path: Path,
    artifact_sha256: str,
    criterion_commit: str,
    evidence_commit: str,
    reviewed_tip: str,
    key_schema: str,
) -> dict[str, object]:
    if not all([str(artifact_path), artifact_sha256, criterion_commit, evidence_commit, reviewed_tip, key_schema]):
        raise CalibrationSourceError("SENTINEL_BINDING_MISSING")
    if key_schema != CANONICAL_SCORING_KEY_SCHEMA:
        raise CalibrationSourceError("SENTINEL_SCHEMA_MISMATCH")
    execution_tip = git(repo, ["rev-parse", "HEAD"])
    rel_path = _repo_relative_path(repo, artifact_path)
    for label, commit in {
        "sentinel_criterion_commit": criterion_commit,
        "sentinel_evidence_commit": evidence_commit,
        "sentinel_reviewed_tip": reviewed_tip,
    }.items():
        try:
            git(repo, ["cat-file", "-e", f"{commit}^{{commit}}"])
        except subprocess.CalledProcessError as exc:
            raise CalibrationSourceError(f"SENTINEL_UNRESOLVABLE_{label}") from exc
    if (
        not is_ancestor(repo, criterion_commit, evidence_commit)
        or not is_ancestor(repo, evidence_commit, reviewed_tip)
        or not is_ancestor(repo, reviewed_tip, execution_tip)
    ):
        raise CalibrationSourceError("SENTINEL_ANCESTRY_MISMATCH")
    try:
        evidence_digest = committed_byte_digest(repo, evidence_commit, rel_path)
        reviewed_digest = committed_byte_digest(repo, reviewed_tip, rel_path)
        tip_digest = committed_byte_digest(repo, execution_tip, rel_path)
    except subprocess.CalledProcessError as exc:
        raise CalibrationSourceError("SENTINEL_ARTIFACT_UNRESOLVABLE") from exc
    if evidence_digest != artifact_sha256:
        raise CalibrationSourceError("SENTINEL_EVIDENCE_DIGEST_MISMATCH")
    if reviewed_digest != artifact_sha256:
        raise CalibrationSourceError("SENTINEL_REVIEWED_DIGEST_MISMATCH")
    if tip_digest != artifact_sha256:
        raise CalibrationSourceError("SENTINEL_TIP_DIGEST_MISMATCH")
    keys = read_sentinel_keys(artifact_path)
    return {
        "sentinel_artifact_path": rel_path,
        "sentinel_artifact_sha256": artifact_sha256,
        "sentinel_criterion_commit": criterion_commit,
        "sentinel_evidence_commit": evidence_commit,
        "sentinel_reviewed_tip": reviewed_tip,
        "sentinel_key_schema": key_schema,
        "sentinel_key_count": len(keys),
        "sentinel_keys": sorted(keys),
        "sentinel_verification": {
            "ancestry": "PASS",
            "digest_at_evidence": "PASS",
            "digest_at_reviewed_tip": "PASS",
            "digest_at_tip": "PASS",
            "schema_equality": "PASS",
        },
    }


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
    if not is_ancestor(repo, GOVERNING_REG1_COMMIT, execution_tip):
        raise CalibrationSourceError(f"GOVERNING_REG1_COMMIT {GOVERNING_REG1_COMMIT} is not an ancestor of {execution_tip}")
    source_commit = source_bytes_commit(repo)
    if not is_ancestor(repo, GOVERNING_REG1_COMMIT, source_commit):
        raise CalibrationSourceError(f"GOVERNING_REG1_COMMIT {GOVERNING_REG1_COMMIT} is not an ancestor of source commit {source_commit}")
    if not is_ancestor(repo, source_commit, execution_tip):
        raise CalibrationSourceError(f"source commit {source_commit} is not an ancestor of execution tip {execution_tip}")
    source_sha_at_source = committed_byte_digest(repo, source_commit, SOURCE_GENERATOR_PATH)
    source_sha_at_tip = committed_byte_digest(repo, execution_tip, SOURCE_GENERATOR_PATH)
    if source_sha_at_source != source_sha_at_tip:
        raise CalibrationSourceError("SOURCE_GENERATOR_SHA256_MISMATCH")
    return {
        "source_generator_path": SOURCE_GENERATOR_PATH,
        "source_generator_commit": source_commit,
        "source_generator_sha256_at_source_commit": source_sha_at_source,
        "source_generator_sha256_at_execution_tip": source_sha_at_tip,
        "execution_tip": execution_tip,
        "artifact_commit": artifact_commit,
        "governing_reg1_commit": GOVERNING_REG1_COMMIT,
        "reg1_commit": GOVERNING_REG1_COMMIT,
        "input_digests": input_digest_rows(input_paths),
        "exact_command": exact_command,
        "prior_viewed_output": {
            "prior_viewed_artifact_path": "tuning/a091-response-model-calibration-reg1v22-aaa1c17-20260721T113736Z/summary.json",
            "prior_viewed_artifact_sha256": "b7e7f66bc307a0f0b68f6938b78ae55719ee43f648164019dbaada46ad3553f1",
            "prior_viewed_evidence_commit_full": "b42103962f2ee8445f3d2cd51897006b1da97714",
            "prior_viewed_attestation_commit_full": "044153b55cb543b5141b910e8893c65ce92fa36b",
            "prior_viewed_removal_commit_full": "2fa8e9d8059f5031b211e7cf28742b0bfe535d4b",
            "disposition": "VOID_PRE_V2.3",
            "prior_disposition": "VOID_PRE_V2.3",
            "prior_board_effect": "NONE",
            "result_viewed": True,
            "prior_calibration_status": "NULL_CALIBRATED",
            "prior_g": 0.0,
            "prior_tau": 0.02,
            "prior_L": 0,
            "prior_rms": 0.0,
            "prior_scoring_rows": 51,
            "prior_fit_directions": ["DOWN", "UP"],
            "effect_on_current_status": "none",
            "void_reasons": [
                "generator predates v2.3",
                "UP direction included",
                "real-run contracts incomplete",
                "provenance rules incomplete"
            ],
        },
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
            "flight_id": "synthetic",
            "frame_id": f"syn_frame_{tick:04d}",
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
    packet = provenance_packet(repo, ["synthetic://reg1v25-detector-dry-run"], "python tuning/reg1v2_calibration_source_generator.py --synthetic-dry-run")
    return {
        "artifact": "REG1V25_CALIBRATION_SOURCE_SYNTHETIC_DRY_RUN",
        "diagnostic_token": "DIAGNOSTIC",
        "packet_scope": "SYNTHETIC_DIAGNOSTIC",
        "detector": [window_to_dict(w) for w in windows],
        "fit_summary": {k: v for k, v in fit.items() if k not in {"score_rows"}},
        "grid": {"g_count": len(G_VALUES), "tau_count": len(TAU_VALUES), "L_count": len(L_VALUES), "candidate_count": len(G_VALUES) * len(TAU_VALUES) * len(L_VALUES)},
        "provenance": packet,
    }


def write_packet(
    out_dir: Path,
    packet: Mapping[str, object],
    score_rows: Sequence[Mapping[str, object]] | None = None,
    ledger_rows: Sequence[Mapping[str, object]] | None = None,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=False)
    packet_out = dict(packet)
    if ledger_rows is not None:
        ledger_path = out_dir / "support_ledger.csv"
        with ledger_path.open("w", newline="", encoding="utf-8") as f:
            fieldnames = list(ledger_rows[0].keys()) if ledger_rows else ["empty"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(ledger_rows)
        packet_out["support_ledger_path"] = str(ledger_path)
        packet_out["support_ledger_sha256"] = sha256_file(ledger_path)
    (out_dir / "summary.json").write_text(json.dumps(packet_out, indent=2, sort_keys=True), encoding="utf-8")
    if score_rows is not None:
        with (out_dir / "candidate_scores.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(score_rows[0].keys()) if score_rows else ["empty"])
            writer.writeheader()
            writer.writerows(score_rows)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="REG-1v2.5 calibration source generator")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--synthetic-dry-run", action="store_true")
    parser.add_argument("--input-csv")
    parser.add_argument("--sentinel-artifact-path", "--sentinel-keys-csv", dest="sentinel_artifact_path")
    parser.add_argument("--sentinel-artifact-sha256", "--sentinel-keys-digest", dest="sentinel_artifact_sha256")
    parser.add_argument("--sentinel-criterion-commit")
    parser.add_argument("--sentinel-evidence-commit", "--sentinel-keys-commit", dest="sentinel_evidence_commit")
    parser.add_argument("--sentinel-reviewed-tip")
    parser.add_argument("--sentinel-key-schema")
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
    if not all([
        args.sentinel_artifact_path,
        args.sentinel_artifact_sha256,
        args.sentinel_criterion_commit,
        args.sentinel_evidence_commit,
        args.sentinel_reviewed_tip,
        args.sentinel_key_schema,
    ]):
        raise CalibrationSourceError("SENTINEL_BINDING_MISSING")
    input_path = Path(args.input_csv).resolve()
    rows = read_csv_rows(input_path)
    input_paths = [str(input_path)]
    sentinel_path = Path(args.sentinel_artifact_path).resolve()
    sentinel_binding = verify_sentinel_binding(
        repo,
        artifact_path=sentinel_path,
        artifact_sha256=str(args.sentinel_artifact_sha256),
        criterion_commit=str(args.sentinel_criterion_commit),
        evidence_commit=str(args.sentinel_evidence_commit),
        reviewed_tip=str(args.sentinel_reviewed_tip),
        key_schema=str(args.sentinel_key_schema),
    )
    sentinel_keys = list(sentinel_binding["sentinel_keys"])
    input_paths.append(str(sentinel_path))
    windows = detect_step_windows(rows, sentinel_keys=sentinel_keys)
    calibration_keys = sorted({scoring_event_key(window, row) for window in windows for row in window.rows})
    sentinel_key_set = sorted({str(key) for key in sentinel_keys})
    sentinel_intersection = sorted(set(calibration_keys).intersection(sentinel_key_set))
    if sentinel_intersection:
        raise CalibrationSourceError(f"SENTINEL_OVERLAP: {sentinel_intersection}")
    fit_dirs = {args.direction}
    fit = fit_response_model(windows, fit_dirs)
    packet = {
        "artifact": "REG1V25_CALIBRATION_PACKET",
        "diagnostic_token": "DIAGNOSTIC",
        "packet_scope": "REG2_CALIBRATION_CANDIDATE",
        "fit_summary": {k: v for k, v in fit.items() if k not in {"score_rows", "support_ledger"}},
        "calibration_key_set": calibration_keys,
        "calibration_key_count": len(calibration_keys),
        "intersection_count": len(sentinel_intersection),
        "intersection_keys": sentinel_intersection,
        **{k: v for k, v in sentinel_binding.items() if k != "sentinel_keys"},
        "sentinel_key_set": sentinel_key_set,
        "direction": args.direction,
        "primary_fit_direction": PRIMARY_FIT_DIRECTION,
        "provenance": provenance_packet(repo, input_paths, " ".join(sys.argv if argv is None else [sys.argv[0], *argv])),
    }
    write_packet(Path(args.out_dir), packet, fit["score_rows"], fit["support_ledger"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
