"""R26 anchor-run replay on commit 7657559.

QA & MOCK-TUNER scope: recorded-video replay and synthetic oracle micro-replays
only. Writes artifacts under tuning/.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import subprocess
import sys
from bisect import bisect_right
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tuning"))

from aigp.core.params import ParamSet  # noqa: E402
from aigp.estimation.attitude_filter import quat_rotate  # noqa: E402
from aigp.planning.approach import level_quat  # noqa: E402
from aigp.planning.vertical_owner import (  # noqa: E402
    TERM_OWNER,
    TerminalOracle,
    VerticalOwnerArbiter,
    slew_up_velocity,
)
from aigp.planning.vertical_terminal import (  # noqa: E402
    compute_terminal_guidance,
    crossing_error,
    crossing_sigma,
)
from run_l1_perception_replay import (  # noqa: E402
    TARGETS,
    assert_mock_safe,
    fnum,
    fmt,
    git_head,
    read_jsonl,
    run_video_replay,
    write_csv,
)


DEFAULT_SOURCE_REF = "3b554f3"
SIDE_SIGMA_E_FLOOR_M = 0.038
FULL_SIGMA_E_M = 0.05
FULL_SIGMA_V_MPS = 0.10
TAIL_S = 0.50
CORRIDOR_M = 0.30


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


def apply_patches(params: ParamSet, patches: list[str]) -> ParamSet:
    overrides = {}
    for item in patches:
        key, sep, raw = item.partition("=")
        if not sep:
            raise SystemExit(f"--patch needs KEY=VALUE, got: {item}")
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            value = raw
        overrides[key.strip()] = value
    return params.patch(overrides) if overrides else params


def load_setpoint_signals(log_path: Path) -> list[tuple[int, float, float | None]]:
    out = []
    for rec in read_jsonl(log_path):
        if rec.get("topic") != "setpoint":
            continue
        data = rec.get("data", {})
        v = data.get("v_body") or data.get("vel_body") or data.get("velocity_body")
        speed = None
        body_z = None
        if isinstance(v, list) and len(v) >= 2:
            speed = math.hypot(float(v[0]), float(v[1]))
            if len(v) >= 3:
                body_z = float(v[2])
        if speed is None:
            speed = fnum(data.get("speed_mps"))
        if speed is not None:
            out.append((int(rec.get("mono_ns", 0)), float(speed), body_z))
    out.sort()
    return out


def setpoint_speed_at(samples: list[tuple[int, float, float | None]],
                      mono_ns: int, default: float | None = None) -> float | None:
    if not samples:
        return default
    idx = bisect_right([s[0] for s in samples], mono_ns) - 1
    if idx < 0:
        return default
    return samples[idx][1]


def setpoint_vz_up_at(samples: list[tuple[int, float, float | None]],
                      mono_ns: int, level_roll: float,
                      level_pitch: float) -> float | None:
    if not samples:
        return None
    idx = bisect_right([s[0] for s in samples], mono_ns) - 1
    if idx < 0:
        return None
    body_z = samples[idx][2]
    if body_z is None:
        return None
    cos_tilt = float(np.cos(level_pitch) * np.cos(level_roll))
    return -float(body_z) * cos_tilt


def load_truth_vz(log_path: Path) -> list[tuple[int, float]]:
    out = []
    for rec in read_jsonl(log_path):
        if rec.get("topic") != "state":
            continue
        data = rec.get("data", {})
        v = data.get("v_world")
        if not isinstance(v, list) or len(v) < 3:
            continue
        q_lvl = level_quat(
            float(data.get("level_roll", 0.0)),
            float(data.get("level_pitch", 0.0)),
        )
        v_level = quat_rotate(q_lvl, np.asarray(v, dtype=np.float64))
        out.append((int(rec.get("mono_ns", 0)), -float(v_level[2])))
    out.sort()
    return out


def at_or_before(samples: list[tuple[int, float]], mono_ns: int,
                 default: float | None = None) -> float | None:
    if not samples:
        return default
    idx = bisect_right([s[0] for s in samples], mono_ns) - 1
    if idx < 0:
        return default
    return samples[idx][1]


def attach_flight_signals(params: ParamSet, rows: list[dict], target: dict) -> None:
    log_path = ROOT / target["log"]
    setpoints = load_setpoint_signals(log_path)
    truth_vz = load_truth_vz(log_path)
    default_speed = float(params.get("planner.commit.speed_mps", default=2.5))
    for row in rows:
        mono = int(row["mono_ns"])
        row["setpoint_speed_xy_mps"] = setpoint_speed_at(setpoints, mono, default_speed)
        row["setpoint_vz_up_mps"] = setpoint_vz_up_at(
            setpoints,
            mono,
            float(row.get("level_roll_rad") or 0.0),
            float(row.get("level_pitch_rad") or 0.0),
        )
        row["truth_vz_up_mps"] = at_or_before(truth_vz, mono, None)


def exact_pairs(rows: list[dict]) -> list[dict]:
    full = {
        (r["flight"], str(r["feature_ts_ns"])): r
        for r in rows
        if r.get("feature_mode") == "FULL_QUAD"
        and r.get("cert_status") == "certified"
        and fnum(r.get("e_meas")) is not None
    }
    pairs = []
    for row in rows:
        if (row.get("feature_mode") != "SIDE_PAIR"
                or row.get("cert_status") != "certified"
                or fnum(row.get("e_meas")) is None):
            continue
        frow = full.get((row["flight"], str(row["feature_ts_ns"])))
        if frow is None:
            continue
        pairs.append({
            "flight": row["flight"],
            "frame_id": row["frame_id"],
            "feature_ts_ns": row["feature_ts_ns"],
            "t_rel_s": row["t_rel_s"],
            "range_z_m": row.get("range_z_m", ""),
            "side_e_z": row["e_meas"],
            "full_e_z": frow["e_meas"],
            "residual_e_m": float(row["e_meas"]) - float(frow["e_meas"]),
        })
    return pairs


def rms(values: list[float]) -> float | None:
    vals = [v for v in values if math.isfinite(v)]
    if not vals:
        return None
    return math.sqrt(statistics.fmean([v * v for v in vals]))


def rms_centered(values: list[float]) -> float | None:
    vals = [v for v in values if math.isfinite(v)]
    if len(vals) < 2:
        return None
    mean = statistics.fmean(vals)
    return math.sqrt(statistics.fmean([(v - mean) ** 2 for v in vals]))


def percentile(values: list[float], pct: float) -> float | None:
    vals = sorted(v for v in values if math.isfinite(v))
    if not vals:
        return None
    if len(vals) == 1:
        return vals[0]
    pos = (pct / 100.0) * (len(vals) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return vals[lo]
    frac = pos - lo
    return vals[lo] * (1.0 - frac) + vals[hi] * frac


def terminal_tail_s(params: ParamSet) -> float:
    abort_min = float(params.get("planner.commit.abort_min_dist_m", default=0.8))
    speed = float(params.get("planner.commit.speed_mps", default=2.5))
    coverage = float(params.get("planner.terminal.coverage_tail_p95_s", default=0.50))
    return max(0.45, abort_min / max(speed, 0.1), coverage)


def rate_source_of(oracle: TerminalOracle) -> str:
    if oracle.active_source == "SIDE_PAIR":
        return "FULL_RATE_ANCHOR" if oracle.rate_anchor_valid else "ANCHOR_INVALID"
    return "FULL_QUAD"


def rate_anchor_age(oracle: TerminalOracle, now_s: float) -> float:
    if oracle.rate_anchor_ts is None:
        return 0.0
    return float(oracle.anchor_age_s(now_s))


def rate_anchor_age_frozen(oracle: TerminalOracle) -> float:
    if oracle.rate_anchor_ts is None:
        return 0.0
    return float(oracle.anchor_age_s())


def rate_anchor_elapsed(oracle: TerminalOracle, ts_s: float) -> float:
    if oracle.rate_anchor_ts is None:
        return 0.0
    return max(0.0, float(ts_s) - float(oracle.rate_anchor_ts))


def anchor_hold_rate(oracle: TerminalOracle, prev_vz_up: float | None) -> tuple[float | None, float, float | str]:
    anchor_v = fnum(oracle.rate_anchor_v)
    if anchor_v is None or not oracle.rate_anchor_valid:
        return None, 0.0, oracle.anchor_applied_ref if oracle.anchor_applied_ref is not None else ""
    if oracle.anchor_applied_ref is None:
        ref = oracle.applied_at(oracle.rate_anchor_ts) if hasattr(oracle, "applied_at") else None
        if ref is None and prev_vz_up is not None:
            ref = float(prev_vz_up)
        oracle.anchor_applied_ref = ref
    ff = (
        float(prev_vz_up) - float(oracle.anchor_applied_ref)
        if prev_vz_up is not None and oracle.anchor_applied_ref is not None
        else 0.0
    )
    return anchor_v + ff, ff, oracle.anchor_applied_ref if oracle.anchor_applied_ref is not None else ""


def terminal_command_update(
    params: ParamSet,
    oracle: TerminalOracle,
    row: dict,
    e_z_eff: float,
    prev_vz_up: float | None,
    dt: float,
    prev_phase: str | None = None,
) -> dict:
    speed = max(float(row.get("setpoint_speed_xy_mps") or 0.0),
                float(params.get("planner.commit.speed_mps", default=2.5)),
                0.5)
    r = max(float(row.get("range_z_m") or 0.0), 0.05)
    tau_s = r / speed
    vz_max = float(params.get("planner.terminal.vz_max_mps", default=0.6))
    az_max = float(params.get("planner.terminal.az_max_mps2", default=2.0))
    margin = float(params.get("planner.terminal.margin_m", default=0.55))
    cmd_clamp = float(params.get("planner.terminal.cmd_clamp_m", default=0.10))
    logged_applied_vz_up = fnum(row.get("setpoint_vz_up_mps"))
    maintenance_score = ""
    maintenance_score_ok = ""
    runtime_hold_authorized = ""
    age = rate_anchor_age(oracle, float(row["feature_ts_ns"]) / 1e9)
    if oracle.active_source == "SIDE_PAIR":
        applied_now = logged_applied_vz_up if logged_applied_vz_up is not None else prev_vz_up
        if hasattr(oracle, "note_applied"):
            oracle.note_applied(float(row["feature_ts_ns"]) / 1e9,
                                float(applied_now) if applied_now is not None else 0.0)
        sig_e, _ = oracle.sigmas()
        h_m = min(tau_s, terminal_tail_s(params), TAIL_S)
        sigma_a_ceiling = 0.35
        sv_maint = math.sqrt(0.10 ** 2 + (age * sigma_a_ceiling) ** 2)
        maintenance_score = 2.0 * math.sqrt(float(sig_e) ** 2 + (h_m * sv_maint) ** 2) + 0.06
        maintenance_score_ok = maintenance_score <= CORRIDOR_M
        runtime_hold_authorized = bool(
            oracle.rate_anchor_valid and age <= tau_s + 0.5 and maintenance_score_ok
        )
        if runtime_hold_authorized:
            # The recorded replay is counterfactual for the terminal owner, so
            # use the actually logged vertical command as the applied-command
            # feed-forward term when it is available.
            rate_hold, ff, applied_ref = anchor_hold_rate(oracle, applied_now)
            v_z_up = float(rate_hold or 0.0)
        else:
            rate_hold, ff, applied_ref = None, 0.0, oracle.anchor_applied_ref or ""
            v_z_up = 0.0
    else:
        vz = oracle.v_z_visual()
        v_z_up = vz * oracle.rate_authority() if vz is not None else 0.0
        rate_hold, ff, applied_ref = None, 0.0, ""

    guidance = compute_terminal_guidance(
        e_z=float(np.clip(e_z_eff, -cmd_clamp, cmd_clamp)),
        sigma_e=0.10,
        v_z=v_z_up,
        sigma_v=0.15,
        tau_s=tau_s,
        margin_m=margin,
        prev_phase=prev_phase,
        vz_max=vz_max,
        az_max=az_max,
    )
    vz_goal = (
        prev_vz_up if guidance["vz_cmd"] is None and prev_vz_up is not None
        else 0.0 if guidance["vz_cmd"] is None
        else float(guidance["vz_cmd"])
    )
    vz_applied = slew_up_velocity(
        prev_vz_up if prev_vz_up is not None else vz_goal,
        vz_goal,
        dt,
        az_max,
        az_max,
    )
    return {
        "rate_hold_corrected_mps": rate_hold if rate_hold is not None else "",
        "rate_feed_forward_mps": ff,
        "anchor_applied_ref_mps": applied_ref,
        "logged_applied_vz_up_mps": logged_applied_vz_up if logged_applied_vz_up is not None else "",
        "maintenance_score": maintenance_score,
        "maintenance_score_ok": maintenance_score_ok,
        "runtime_hold_authorized": runtime_hold_authorized,
        "terminal_phase": guidance["phase"],
        "terminal_tau_eff_s": guidance["tau_eff"],
        "terminal_e_cross_m": guidance["e_cross"],
        "terminal_sigma_cross_m": guidance["sigma_cross"],
        "terminal_safe": guidance["safe"],
        "terminal_rate_input_mps": v_z_up,
        "terminal_vz_up_mps": vz_applied,
        "terminal_vz_goal_mps": vz_goal,
    }


def admission_metrics(params: ParamSet, oracle: TerminalOracle, row: dict,
                      side_sigma_e_m: float,
                      side_vz_override: float | None = None) -> dict:
    if not oracle.ready():
        return {
            "admission_score": "",
            "admission_sigma": "",
            "admission_e_cross_m": "",
            "admission_vz_vis_mps": "",
            "admission_h_tail_s": "",
        }
    e_now = fnum(row.get("e_meas"))
    if e_now is None and getattr(oracle, "_hist", None):
        e_now = float(oracle._hist[-1][1])
    if e_now is None:
        return {
            "admission_score": "",
            "admission_sigma": "",
            "admission_e_cross_m": "",
            "admission_vz_vis_mps": "",
            "admission_h_tail_s": "",
        }
    speed = max(float(row.get("setpoint_speed_xy_mps") or 0.0),
                float(params.get("planner.commit.speed_mps", default=2.5)),
                0.5)
    r = max(float(row.get("range_z_m") or 0.0), 0.05)
    h_tail = min(r / speed, terminal_tail_s(params), TAIL_S)
    if oracle.active_source == "SIDE_PAIR":
        vz_vis = (
            float(side_vz_override)
            if side_vz_override is not None
            else float(oracle.rate_anchor_v or 0.0)
            if oracle.rate_anchor_valid
            else 0.0
        )
        sig_e, sig_v = side_sigma_e_m, FULL_SIGMA_V_MPS
    else:
        vz = oracle.v_z_visual()
        vz_vis = 0.0 if vz is None else float(vz) * oracle.rate_authority()
        sig_e, sig_v = FULL_SIGMA_E_M, FULL_SIGMA_V_MPS
    e_cross = crossing_error(float(e_now), vz_vis, h_tail)
    sigma = crossing_sigma(sig_e, vz_vis, sig_v, h_tail)
    return {
        "admission_score": abs(e_cross) + 2.0 * sigma + 0.06,
        "admission_sigma": sigma,
        "admission_e_cross_m": e_cross,
        "admission_vz_vis_mps": vz_vis,
        "admission_h_tail_s": h_tail,
    }


def replay_anchor_trial(params: ParamSet, rows: list[dict], label: str,
                        drop_full_after_ts_ns: int | None,
                        side_sigma_e_m: float) -> tuple[list[dict], list[dict]]:
    oracle = TerminalOracle()
    arbiter = VerticalOwnerArbiter()
    timeline = []
    transitions = []
    prev_source = oracle.active_source
    last_t = None
    transition_id = 0
    vz_max = float(params.get("planner.terminal.vz_max_mps", default=0.6))
    term_vz_up: float | None = None
    term_phase: str | None = None

    for row in rows:
        if not row.get("commit"):
            continue
        full_dropped = (
            drop_full_after_ts_ns is not None
            and row.get("feature_mode") == "FULL_QUAD"
            and int(row["feature_ts_ns"]) >= int(drop_full_after_ts_ns)
        )
        e_raw = fnum(row.get("e_meas")) if not full_dropped else None
        source_valid = (
            e_raw is not None
            and row.get("cert_status") == "certified"
            and row.get("feature_mode") in ("FULL_QUAD", "SIDE_PAIR")
        )
        active_sample = False
        ts_s = float(row["feature_ts_ns"]) / 1e9
        if source_valid:
            active_sample = oracle.observe(ts_s, float(e_raw),
                                           source=row["feature_mode"])
        if oracle.active_source != prev_source:
            transition_id += 1
            transitions.append({
                "trial": label,
                "transition_id": transition_id,
                "flight": row["flight"],
                "t_rel_s": row["t_rel_s"],
                "range_z_m": row.get("range_z_m", ""),
                "from_source": prev_source,
                "to_source": oracle.active_source,
                "rate_source": rate_source_of(oracle),
                "rate_anchor_age_s": rate_anchor_age(oracle, ts_s),
                "rate_anchor_age_frozen_s": rate_anchor_age_frozen(oracle),
                "rate_anchor_elapsed_s": rate_anchor_elapsed(oracle, ts_s),
                "rate_anchor_valid": oracle.rate_anchor_valid,
                "rate_anchor_v_mps": oracle.rate_anchor_v if oracle.rate_anchor_v is not None else "",
            })
            prev_source = oracle.active_source

        decision_row = dict(row)
        if not active_sample:
            decision_row["e_meas"] = ""
        metrics = admission_metrics(params, oracle, decision_row, side_sigma_e_m)
        score = fnum(metrics.get("admission_score"))
        first_capture_ok = (
            source_valid
            and row.get("topic") == "feature"
            and row.get("feature_mode") == "FULL_QUAD"
            and oracle.ready()
            and oracle.active_source == "FULL_QUAD"
            and score is not None
            and score <= CORRIDOR_M
        )
        maintain_ok = arbiter.owner == TERM_OWNER and source_valid
        capture_certified = first_capture_ok or maintain_ok
        if row.get("topic") == "feature":
            arbiter.note_exposure(source_valid)
        owner = arbiter.tick(
            commit_active=True,
            same_gate=True,
            certified=capture_certified,
            feature_age_s=float(row.get("gate_age_s") or 0.0),
            phase="position",
        )
        dt = 0.02 if last_t is None else max(float(row["t_rel_s"]) - last_t, 1e-3)
        applied_e_z = ""
        if owner == TERM_OWNER:
            applied = oracle.update(float(e_raw) if active_sample else None,
                                    dt=dt, vz_max=vz_max)
            applied_e_z = applied if applied is not None else ""
            command_info = terminal_command_update(
                params,
                oracle,
                row,
                float(applied) if applied is not None else 0.0,
                term_vz_up,
                dt,
                term_phase,
            )
            term_phase = str(command_info["terminal_phase"] or term_phase or "")
            term_vz_up = fnum(command_info["terminal_vz_up_mps"])
            if oracle.active_source == "SIDE_PAIR":
                metrics = admission_metrics(
                    params,
                    oracle,
                    decision_row,
                    side_sigma_e_m,
                    fnum(command_info["rate_hold_corrected_mps"]),
                )
                score = fnum(metrics.get("admission_score"))
        else:
            command_info = {
                "rate_hold_corrected_mps": "",
                "rate_feed_forward_mps": "",
                "anchor_applied_ref_mps": "",
                "logged_applied_vz_up_mps": row.get("setpoint_vz_up_mps", ""),
                "maintenance_score": "",
                "maintenance_score_ok": "",
                "runtime_hold_authorized": "",
                "terminal_phase": "",
                "terminal_tau_eff_s": "",
                "terminal_e_cross_m": "",
                "terminal_sigma_cross_m": "",
                "terminal_safe": "",
                "terminal_rate_input_mps": "",
                "terminal_vz_up_mps": "",
                "terminal_vz_goal_mps": "",
            }
        truth_v = fnum(row.get("truth_vz_up_mps"))
        anchor_v = fnum(oracle.rate_anchor_v)
        rate_hold = fnum(command_info.get("rate_hold_corrected_mps"))
        age = rate_anchor_age(oracle, ts_s)
        frozen_age = rate_anchor_age_frozen(oracle)
        elapsed_age = rate_anchor_elapsed(oracle, ts_s)
        rate_error_anchor_only = (
            truth_v - anchor_v
            if truth_v is not None and anchor_v is not None and age > 1e-6
            else ""
        )
        rate_error = (
            truth_v - rate_hold
            if truth_v is not None and rate_hold is not None and age > 1e-6
            else ""
        )
        sigma_a_sample = (
            float(rate_error) / age
            if fnum(rate_error) is not None and age > 1e-6
            else ""
        )
        sigma_a_anchor_only_sample = (
            float(rate_error_anchor_only) / age
            if fnum(rate_error_anchor_only) is not None and age > 1e-6
            else ""
        )
        shadow_capture = (
            owner == TERM_OWNER
            and source_valid
            and score is not None
            and score <= CORRIDOR_M
            and oracle.active_source in ("FULL_QUAD", "SIDE_PAIR")
        )
        timeline.append({
            **row,
            "trial": label,
            "drop_full_after_ts_ns": drop_full_after_ts_ns or "",
            "full_dropped": full_dropped,
            "fed": not full_dropped,
            "source_valid": source_valid,
            "active_sample": active_sample,
            "observer_ready": oracle.ready(),
            "active_source": oracle.active_source,
            "shadow_owner": owner,
            "shadow_capture": shadow_capture,
            "phase": "position",
            "phase_changed": False,
            "admission_score": metrics["admission_score"],
            "admission_sigma": metrics["admission_sigma"],
            "admission_e_cross_m": metrics["admission_e_cross_m"],
            "admission_vz_vis_mps": metrics["admission_vz_vis_mps"],
            "admission_h_tail_s": metrics["admission_h_tail_s"],
            "rate_source": rate_source_of(oracle),
            "rate_anchor_age_s": age,
            "rate_anchor_age_frozen_s": frozen_age,
            "rate_anchor_elapsed_s": elapsed_age,
            "rate_anchor_valid": oracle.rate_anchor_valid,
            "rate_anchor_v_mps": oracle.rate_anchor_v if oracle.rate_anchor_v is not None else "",
            **command_info,
            "truth_vz_up_mps": row.get("truth_vz_up_mps", ""),
            "rate_error_anchor_only_mps": rate_error_anchor_only,
            "sigma_a_anchor_only_sample_mps2": sigma_a_anchor_only_sample,
            "rate_error_mps": rate_error,
            "sigma_a_sample_mps2": sigma_a_sample,
            "applied_e_z": applied_e_z,
            "transition_id": transition_id if transition_id else "",
        })
        last_t = float(row["t_rel_s"])
    return timeline, transitions


def summarize_trial(timeline: list[dict], transitions: list[dict]) -> dict:
    captures = [r for r in timeline if r.get("shadow_capture")]
    side_term = [
        r for r in timeline
        if r.get("shadow_owner") == TERM_OWNER and r.get("active_source") == "SIDE_PAIR"
    ]
    side_scored = [r for r in side_term if fnum(r.get("admission_score")) is not None]
    return {
        "trial": timeline[0]["trial"] if timeline else "",
        "drop_full_after_ts_ns": timeline[0].get("drop_full_after_ts_ns", "") if timeline else "",
        "rows": len(timeline),
        "capture_rows": len(captures),
        "first_capture_range_m": captures[0].get("range_z_m", "") if captures else "",
        "first_capture_source": captures[0].get("active_source", "") if captures else "",
        "owner_term_rows": sum(1 for r in timeline if r.get("shadow_owner") == TERM_OWNER),
        "owner_term_side_rows": len(side_term),
        "side_shadow_capture_rows": sum(1 for r in side_term if r.get("shadow_capture")),
        "side_admission_max": max([float(r["admission_score"]) for r in side_scored]) if side_scored else "",
        "side_min_range_m": min([float(r["range_z_m"]) for r in side_term
                                 if fnum(r.get("range_z_m")) is not None],
                                default=""),
        "transition_count": len(transitions),
        "full_to_side_count": sum(
            1 for t in transitions
            if t["from_source"] == "FULL_QUAD" and t["to_source"] == "SIDE_PAIR"
        ),
        "rate_source_complete": all("rate_source" in r and "rate_anchor_age_s" in r
                                    for r in timeline),
        "phase_changed_rows": sum(1 for r in timeline if r.get("phase_changed")),
    }


def age_bin(age: float | None) -> str:
    if age is None:
        return "unknown"
    if age < 0.10:
        return "lt0p10"
    if age < 0.20:
        return "0p10-0p20"
    if age < 0.30:
        return "0p20-0p30"
    if age < 0.50:
        return "0p30-0p50"
    return "gte0p50"


def summarize_sigma_a(rows: list[dict]) -> list[dict]:
    groups = ["all", "0p10-0p20", "0p20-0p30", "0p30-0p50", "gte0p50"]
    out = []
    for label in groups:
        group = []
        for row in rows:
            sample = fnum(row.get("sigma_a_sample_mps2"))
            age = fnum(row.get("rate_anchor_age_s"))
            if sample is None or age is None or age < 0.10:
                continue
            if label != "all" and age_bin(age) != label:
                continue
            group.append(row)
        samples = [float(r["sigma_a_sample_mps2"]) for r in group]
        anchor_samples = [
            float(r["sigma_a_anchor_only_sample_mps2"]) for r in group
            if fnum(r.get("sigma_a_anchor_only_sample_mps2")) is not None
        ]
        ages = [float(r["rate_anchor_age_s"]) for r in group]
        errors = [float(r["rate_error_mps"]) for r in group]
        anchor_errors = [
            float(r["rate_error_anchor_only_mps"]) for r in group
            if fnum(r.get("rate_error_anchor_only_mps")) is not None
        ]
        out.append({
            "age_bin": label,
            "n": len(group),
            "age_min_s": min(ages) if ages else "",
            "age_max_s": max(ages) if ages else "",
            "age_median_s": statistics.median(ages) if ages else "",
            "rate_error_bias_mps": statistics.fmean(errors) if errors else "",
            "rate_error_rms_mps": rms(errors) if errors else "",
            "rate_error_anchor_only_rms_mps": rms(anchor_errors) if anchor_errors else "",
            "sigma_a_rms_mps2": rms(samples) if samples else "",
            "sigma_a_centered_mps2": rms_centered(samples) if len(samples) >= 2 else "",
            "sigma_a_anchor_only_rms_mps2": rms(anchor_samples) if anchor_samples else "",
        })
    return out


def summarize_sigma_regimes(rows: list[dict]) -> list[dict]:
    out = []
    for label in ["switch_adjacent", "maintenance"]:
        group = [r for r in rows if r.get("sigma_regime") == label]
        samples = [
            float(r["sigma_a_sample_mps2"]) for r in group
            if fnum(r.get("sigma_a_sample_mps2")) is not None
        ]
        ages = [
            float(r["rate_anchor_age_s"]) for r in group
            if fnum(r.get("rate_anchor_age_s")) is not None
        ]
        errors = [
            float(r["rate_error_mps"]) for r in group
            if fnum(r.get("rate_error_mps")) is not None
        ]
        out.append({
            "regime": label,
            "n": len(group),
            "age_min_s": min(ages) if ages else "",
            "age_max_s": max(ages) if ages else "",
            "rate_error_rms_mps": rms(errors) if errors else "",
            "sigma_a_rms_mps2": rms(samples) if samples else "",
            "sigma_a_centered_mps2": rms_centered(samples) if len(samples) >= 2 else "",
        })
    return out


def percentile_envelope(rows: list[dict]) -> list[dict]:
    out = []
    groups = [("all", rows)]
    groups.extend((r["regime"], [row for row in rows if row.get("sigma_regime") == r["regime"]])
                  for r in [{"regime": "switch_adjacent"}, {"regime": "maintenance"}])
    for label, group in groups:
        samples = [
            abs(float(r["sigma_a_sample_mps2"])) for r in group
            if fnum(r.get("sigma_a_sample_mps2")) is not None
        ]
        out.append({
            "group": label,
            "n": len(samples),
            "p50_abs_sigma_a_mps2": percentile(samples, 50) if samples else "",
            "p80_abs_sigma_a_mps2": percentile(samples, 80) if samples else "",
            "p90_abs_sigma_a_mps2": percentile(samples, 90) if samples else "",
            "p95_abs_sigma_a_mps2": percentile(samples, 95) if samples else "",
            "p99_abs_sigma_a_mps2": percentile(samples, 99) if samples else "",
            "max_abs_sigma_a_mps2": max(samples) if samples else "",
        })
    return out


def heldout_age_coverage(rows: list[dict]) -> list[dict]:
    specs = [
        ("0p10-0p20", 0.10, 0.20),
        ("0p20-0p30", 0.20, 0.30),
        ("0p30-0p50", 0.30, 0.50),
        ("gte0p50", 0.50, float("inf")),
    ]
    out = []
    for label, lo, hi in specs:
        group = []
        for row in rows:
            age = fnum(row.get("rate_anchor_age_s"))
            sample = fnum(row.get("sigma_a_sample_mps2"))
            if age is None or sample is None or age < lo or age >= hi:
                continue
            group.append(row)
        train = [r for r in group if int(float(r.get("frame_id", 0))) % 2 == 0]
        held = [r for r in group if int(float(r.get("frame_id", 0))) % 2 != 0]
        train_abs = [abs(float(r["sigma_a_sample_mps2"])) for r in train]
        fit = percentile(train_abs, 95) if train_abs else None
        held_abs = [abs(float(r["sigma_a_sample_mps2"])) for r in held]
        covered = [v for v in held_abs if fit is not None and v <= fit]
        floor = floor_for_sigma_a(fit) if fit is not None else ""
        ages = [float(r["rate_anchor_age_s"]) for r in group]
        out.append({
            "age_bin": label,
            "age_min_s": min(ages) if ages else "",
            "age_max_s": max(ages) if ages else "",
            "train_n": len(train),
            "heldout_n": len(held),
            "fit_p95_abs_sigma_a_mps2": fit if fit is not None else "",
            "heldout_coverage_frac": (len(covered) / len(held_abs)) if held_abs and fit is not None else "",
            "heldout_max_abs_sigma_a_mps2": max(held_abs) if held_abs else "",
            "floor_m": floor,
            "corridor_pass": (floor <= CORRIDOR_M) if fnum(floor) is not None else "",
        })
    return out


def summarize_age_distribution(trial_rows: list[dict], transitions: list[dict]) -> dict:
    transition_ages = [
        float(t["rate_anchor_age_s"]) for t in transitions
        if fnum(t.get("rate_anchor_age_s")) is not None
        and t.get("to_source") == "SIDE_PAIR"
    ]
    side_rows = [
        r for r in trial_rows
        if r.get("shadow_owner") == TERM_OWNER and r.get("active_source") == "SIDE_PAIR"
    ]
    side_ages = [
        float(r["rate_anchor_age_s"]) for r in side_rows
        if fnum(r.get("rate_anchor_age_s")) is not None
    ]
    damping_ages = [
        float(r["rate_anchor_age_s"]) for r in side_rows
        if r.get("terminal_phase") in ("damping", "freeze")
        and fnum(r.get("rate_anchor_age_s")) is not None
    ]
    scores = [
        float(r["maintenance_score"]) for r in side_rows
        if fnum(r.get("maintenance_score")) is not None
    ]
    authorized = [
        r for r in side_rows
        if str(r.get("runtime_hold_authorized")).lower() == "true"
        or r.get("runtime_hold_authorized") is True
    ]
    authorized_ages = [
        float(r["rate_anchor_age_s"]) for r in authorized
        if fnum(r.get("rate_anchor_age_s")) is not None
    ]
    return {
        "transition_age_n": len(transition_ages),
        "transition_age_min_s": min(transition_ages) if transition_ages else "",
        "transition_age_median_s": statistics.median(transition_ages) if transition_ages else "",
        "transition_age_max_s": max(transition_ages) if transition_ages else "",
        "maintain_age_n": len(side_ages),
        "maintain_age_max_s": max(side_ages) if side_ages else "",
        "authorized_age_max_s": max(authorized_ages) if authorized_ages else "",
        "damping_onset_age_s": min(damping_ages) if damping_ages else "",
        "worst_continuous_score": max(scores) if scores else "",
        "score_p95": percentile(scores, 95) if scores else "",
    }


def floor_for_sigma_a(sigma_a: float, age_s: float = TAIL_S) -> float:
    sig_v = math.sqrt(FULL_SIGMA_V_MPS ** 2 + (sigma_a * min(age_s, TAIL_S)) ** 2)
    return 2.0 * math.sqrt(SIDE_SIGMA_E_FLOOR_M ** 2 + (TAIL_S * sig_v) ** 2) + 0.06


def floor_table(measured_sigma_a: float | None) -> list[dict]:
    rows = []
    values = [0.0, 0.10, 0.20, 0.30, 0.35, 0.40, 0.50, 1.00, 2.00, 3.00]
    if measured_sigma_a is not None and all(abs(measured_sigma_a - v) > 1e-9 for v in values):
        values.append(float(measured_sigma_a))
    values = sorted(values)
    for sigma_a in values:
        floor = floor_for_sigma_a(sigma_a)
        rows.append({
            "sigma_a_mps2": sigma_a,
            "floor_m": floor,
            "corridor_pass": floor <= CORRIDOR_M,
            "measured_lands_here": (
                measured_sigma_a is not None
                and abs(sigma_a - measured_sigma_a) < 1e-9
            ),
        })
    return rows


def anchor_age_sweep(measured_sigma_a: float | None, max_used_age: float | None) -> list[dict]:
    rows = []
    sigma_a = float(measured_sigma_a or 0.0)
    for age in [0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.75, 1.00]:
        sig_v = math.sqrt(FULL_SIGMA_V_MPS ** 2 + (sigma_a * min(age, TAIL_S)) ** 2)
        floor = 2.0 * math.sqrt(SIDE_SIGMA_E_FLOOR_M ** 2 + (TAIL_S * sig_v) ** 2) + 0.06
        rows.append({
            "anchor_age_s": age,
            "sigma_a_mps2": sigma_a,
            "sigma_v_mps": sig_v,
            "floor_m": floor,
            "corridor_pass": floor <= CORRIDOR_M,
            "observed_age_used": (
                max_used_age is not None and age <= float(max_used_age) + 1e-9
            ),
        })
    return rows


def feed_oracle_row(rows: list[dict], scenario: str, oracle: TerminalOracle,
                    ts: float, e: float, source: str) -> None:
    active = oracle.observe(ts, e, source=source)
    rows.append({
        "scenario": scenario,
        "ts_s": ts,
        "source": source,
        "e_meas": e,
        "active_sample": active,
        "active_source": oracle.active_source,
        "rate_source": rate_source_of(oracle),
        "rate_anchor_age_s": rate_anchor_age(oracle, ts),
        "rate_anchor_age_frozen_s": rate_anchor_age_frozen(oracle),
        "rate_anchor_elapsed_s": rate_anchor_elapsed(oracle, ts),
        "rate_anchor_valid": oracle.rate_anchor_valid,
        "rate_anchor_v_mps": oracle.rate_anchor_v if oracle.rate_anchor_v is not None else "",
        "anchor_breaches": getattr(oracle, "_anchor_breaches", ""),
    })


def seeded_anchor_oracle(applied_fn) -> TerminalOracle:
    g = TerminalOracle()
    slope = -0.10
    for i in range(8):
        ts = i * 0.04
        if hasattr(g, "note_applied"):
            g.note_applied(ts, applied_fn(ts))
        g.observe(ts, 0.30 + slope * ts, source="FULL_QUAD")
        g.observe(ts, 0.34 + slope * ts, source="SIDE_PAIR")
    for i in range(8, 14):
        ts = i * 0.04
        if hasattr(g, "note_applied"):
            g.note_applied(ts, applied_fn(ts))
        g.observe(ts, 0.34 + slope * ts, source="SIDE_PAIR")
    return g


def command_change_fixtures() -> list[dict]:
    cases = [
        ("constant", lambda _t: 0.10, 0.10, 0.0),
        ("step_up_after_anchor", lambda t: 0.00 if t <= 0.28 else 0.30, 0.30, 0.30),
        ("step_down_after_anchor", lambda t: 0.00 if t <= 0.28 else -0.20, -0.20, -0.20),
        (
            "triangular_return",
            lambda t: 0.00 if t <= 0.32 else 0.40 if t <= 0.44 else 0.00,
            0.00,
            0.0,
        ),
    ]
    rows = []
    for name, applied_fn, applied_now, expected_ff in cases:
        g = seeded_anchor_oracle(applied_fn)
        now_s = 0.56
        if hasattr(g, "note_applied"):
            g.note_applied(now_s, applied_now)
        rate_hold, ff, applied_ref = anchor_hold_rate(g, applied_now)
        anchor_ref_lookup = (
            g.applied_at(g.rate_anchor_ts)
            if hasattr(g, "applied_at") and g.rate_anchor_ts is not None
            else ""
        )
        rows.append({
            "scenario": name,
            "active_source": g.active_source,
            "rate_anchor_valid": g.rate_anchor_valid,
            "rate_anchor_ts_s": g.rate_anchor_ts if g.rate_anchor_ts is not None else "",
            "rate_anchor_age_s": rate_anchor_age(g, now_s),
            "rate_anchor_v_mps": g.rate_anchor_v if g.rate_anchor_v is not None else "",
            "applied_at_anchor_lookup_mps": anchor_ref_lookup,
            "anchor_applied_ref_mps": applied_ref,
            "applied_now_mps": applied_now,
            "expected_feed_forward_mps": expected_ff,
            "measured_feed_forward_mps": ff,
            "hold_rate_mps": rate_hold if rate_hold is not None else "",
            "verdict": "PASS" if abs(float(ff) - float(expected_ff)) <= 1e-9 else "FAIL",
        })
    return rows


def micro_replays() -> tuple[list[dict], list[dict]]:
    rows = []
    summary = []

    g = TerminalOracle()
    slope = -0.10
    before = None
    for i in range(8):
        ts = i * 0.04
        feed_oracle_row(rows, "R26-4-side-offset", g, ts, 0.30 + slope * ts, "FULL_QUAD")
        feed_oracle_row(rows, "R26-4-side-offset", g, ts, 0.38 + slope * ts, "SIDE_PAIR")
    for i in range(8, 14):
        if i == 8:
            before = g.rate_anchor_v
        feed_oracle_row(rows, "R26-4-side-offset", g, i * 0.04,
                        0.38 + slope * i * 0.04, "SIDE_PAIR")
    summary.append({
        "scenario": "R26-4-side-offset",
        "verdict": "PASS" if g.active_source == "SIDE_PAIR"
        and g.rate_anchor_valid
        and g.rate_anchor_v is not None
        and abs(g.rate_anchor_v - (before if before is not None else g.rate_anchor_v)) < 1e-9
        else "FAIL",
        "final_active_source": g.active_source,
        "final_rate_source": rate_source_of(g),
        "final_rate_anchor_age_s": rate_anchor_age(g, 13 * 0.04),
        "final_rate_anchor_age_frozen_s": rate_anchor_age_frozen(g),
        "final_rate_anchor_valid": g.rate_anchor_valid,
        "final_rate_anchor_v_mps": g.rate_anchor_v if g.rate_anchor_v is not None else "",
    })

    g = TerminalOracle()
    for i in range(8):
        ts = i * 0.04
        feed_oracle_row(rows, "R26-5-contradiction", g, ts, 0.30 - 0.10 * ts, "FULL_QUAD")
        feed_oracle_row(rows, "R26-5-contradiction", g, ts, 0.34 - 0.10 * ts, "SIDE_PAIR")
    for i in range(8, 12):
        feed_oracle_row(rows, "R26-5-contradiction", g, i * 0.04,
                        0.34 - 0.10 * i * 0.04, "SIDE_PAIR")
    valid_before = g.rate_anchor_valid
    t0 = 12 * 0.04
    for k in range(3):
        ts = t0 + k * 0.04
        feed_oracle_row(rows, "R26-5-contradiction", g, ts,
                        0.34 - 0.10 * t0 + 0.6 * (ts - t0 + 0.5),
                        "SIDE_PAIR")
    summary.append({
        "scenario": "R26-5-contradiction",
        "verdict": "PASS" if valid_before and not g.rate_anchor_valid else "FAIL",
        "final_active_source": g.active_source,
        "final_rate_source": rate_source_of(g),
        "final_rate_anchor_age_s": rate_anchor_age(g, t0 + 2 * 0.04),
        "final_rate_anchor_age_frozen_s": rate_anchor_age_frozen(g),
        "final_rate_anchor_valid": g.rate_anchor_valid,
        "final_rate_anchor_v_mps": g.rate_anchor_v if g.rate_anchor_v is not None else "",
    })

    g = TerminalOracle()
    for i in range(8):
        ts = i * 0.04
        feed_oracle_row(rows, "R26-6-full-return", g, ts, 0.30 - 0.08 * ts, "FULL_QUAD")
        feed_oracle_row(rows, "R26-6-full-return", g, ts, 0.34 - 0.08 * ts, "SIDE_PAIR")
    for i in range(8, 12):
        feed_oracle_row(rows, "R26-6-full-return", g, i * 0.04,
                        0.34 - 0.08 * i * 0.04, "SIDE_PAIR")
    side_seen = g.active_source == "SIDE_PAIR"
    ref = g.e_z if g.e_z is not None else 0.30
    for k in range(3):
        ts = 12 * 0.04 + k * 0.04
        feed_oracle_row(rows, "R26-6-full-return", g, ts, ref - 0.08 * k * 0.04,
                        "FULL_QUAD")
    summary.append({
        "scenario": "R26-6-full-return",
        "verdict": "PASS" if side_seen and g.active_source == "FULL_QUAD"
        and not g.rate_anchor_valid
        else "FAIL",
        "final_active_source": g.active_source,
        "final_rate_source": rate_source_of(g),
        "final_rate_anchor_age_s": rate_anchor_age(g, 12 * 0.04 + 2 * 0.04),
        "final_rate_anchor_age_frozen_s": rate_anchor_age_frozen(g),
        "final_rate_anchor_valid": g.rate_anchor_valid,
        "final_rate_anchor_v_mps": g.rate_anchor_v if g.rate_anchor_v is not None else "",
    })
    return rows, summary


def write_report(out_dir: Path, summary: dict) -> None:
    lines = [
        "# R26 Anchor Run",
        "",
        "Role: QA & MOCK-TUNER.",
        "Scope: recorded-video replay plus synthetic oracle micro-replays only; no real simulator was launched.",
        f"Source commit: `{summary['commit']}`.",
        f"Repo HEAD: `{summary['repo_head']}`.",
        f"Non-tuning delta from `{summary['source_ref']}`: `{summary['non_tuning_delta_from_source']}`.",
        "",
        "## R26-1 Liveness",
        "",
        "| Trial | Drop frame | First capture R | TERM/SIDE rows | Side captures | Side max score | Min side R | Transitions | Verdict |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in summary["trial_summary"]:
        if not str(row["trial"]).startswith("anchor_drop_"):
            continue
        verdict = "PASS" if row["owner_term_side_rows"] > 0 \
            and row["side_shadow_capture_rows"] > 0 \
            and fnum(row["side_admission_max"]) is not None \
            and float(row["side_admission_max"]) <= CORRIDOR_M \
            and row["phase_changed_rows"] == 0 else "FAIL"
        lines.append(
            f"| `{row['trial']}` | {row.get('candidate_frame_id', '')} | "
            f"{fmt(row['first_capture_range_m'])} | {row['owner_term_side_rows']} | "
            f"{row['side_shadow_capture_rows']} | {fmt(row['side_admission_max'])} | "
            f"{fmt(row['side_min_range_m'])} | {row['full_to_side_count']} | `{verdict}` |"
        )
    lines.extend([
        "",
        f"Overall R26-1 verdict: `{summary['r26_1_verdict']}`.",
        "",
        "## R26-2/3 Sigma-a",
        "",
        "| Anchor age bin | n | age range | corrected err RMS | corrected sigma_a RMS | anchor-only sigma_a RMS | centered |",
        "|---|---:|---|---:|---:|---:|---:|",
    ])
    for row in summary["sigma_a_summary"]:
        lines.append(
            f"| `{row['age_bin']}` | {row['n']} | "
            f"{fmt(row['age_min_s'])}-{fmt(row['age_max_s'])} | "
            f"{fmt(row['rate_error_rms_mps'])} | {fmt(row['sigma_a_rms_mps2'])} | "
            f"{fmt(row['sigma_a_anchor_only_rms_mps2'])} | "
            f"{fmt(row['sigma_a_centered_mps2'])} |"
        )
    lines.extend([
        "",
        "### Percentile Envelope",
        "",
        "| Group | n | p50 | p80 | p90 | p95 | p99 | max |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for row in summary["sigma_percentile_envelope"]:
        lines.append(
            f"| `{row['group']}` | {row['n']} | "
            f"{fmt(row['p50_abs_sigma_a_mps2'])} | "
            f"{fmt(row['p80_abs_sigma_a_mps2'])} | "
            f"{fmt(row['p90_abs_sigma_a_mps2'])} | "
            f"{fmt(row['p95_abs_sigma_a_mps2'])} | "
            f"{fmt(row['p99_abs_sigma_a_mps2'])} | "
            f"{fmt(row['max_abs_sigma_a_mps2'])} |"
        )
    lines.extend([
        "",
        "### Regime Split",
        "",
        "| Regime | n | age range | corrected err RMS | sigma_a RMS | centered |",
        "|---|---:|---|---:|---:|---:|",
    ])
    for row in summary["sigma_regime_summary"]:
        lines.append(
            f"| `{row['regime']}` | {row['n']} | "
            f"{fmt(row['age_min_s'])}-{fmt(row['age_max_s'])} | "
            f"{fmt(row['rate_error_rms_mps'])} | "
            f"{fmt(row['sigma_a_rms_mps2'])} | "
            f"{fmt(row['sigma_a_centered_mps2'])} |"
        )
    lines.extend([
        "",
        "| sigma_a | floor | pass corridor | measured lands here |",
        "|---:|---:|---|---|",
    ])
    for row in summary["floor_table"]:
        lines.append(
            f"| {fmt(row['sigma_a_mps2'])} | {fmt(row['floor_m'])} | "
            f"`{row['corridor_pass']}` | `{row['measured_lands_here']}` |"
        )
    lines.extend([
        "",
        f"Overall R26-2/3 verdict: `{summary['r26_23_verdict']}`.",
        "",
        "### Anchor-Age Sweep",
        "",
        "| Age | sigma_v | floor | corridor pass | observed age used |",
        "|---:|---:|---:|---|---|",
    ])
    for row in summary["anchor_age_sweep"]:
        lines.append(
            f"| {fmt(row['anchor_age_s'])} | {fmt(row['sigma_v_mps'])} | "
            f"{fmt(row['floor_m'])} | `{row['corridor_pass']}` | "
            f"`{row['observed_age_used']}` |"
        )
    lines.extend([
        "",
        "### Held-Out Coverage",
        "",
        "| Age bin | train n | heldout n | fit p95 sigma_a | heldout coverage | floor | corridor pass |",
        "|---|---:|---:|---:|---:|---:|---|",
    ])
    for row in summary["heldout_age_coverage"]:
        lines.append(
            f"| `{row['age_bin']}` | {row['train_n']} | {row['heldout_n']} | "
            f"{fmt(row['fit_p95_abs_sigma_a_mps2'])} | "
            f"{fmt(row['heldout_coverage_frac'])} | {fmt(row['floor_m'])} | "
            f"`{row['corridor_pass']}` |"
        )
    age = summary["age_distribution"]
    lines.extend([
        "",
        "### Age Distributions",
        "",
        f"- Anchor age at transition: n={age['transition_age_n']}, "
        f"min/median/max={fmt(age['transition_age_min_s'])}/"
        f"{fmt(age['transition_age_median_s'])}/{fmt(age['transition_age_max_s'])}.",
        f"- Max age while maintaining: `{fmt(age['maintain_age_max_s'])}` "
        f"(authorized max `{fmt(age['authorized_age_max_s'])}`).",
        f"- Age at damping onset: `{fmt(age['damping_onset_age_s'])}`.",
        f"- Worst continuous score: `{fmt(age['worst_continuous_score'])}` "
        f"(p95 `{fmt(age['score_p95'])}`).",
        "",
        "## R26-4/5/6 Replays",
        "",
        "| Scenario | Verdict | Final source | Final rate source | Final now-age | Final frozen-age | Anchor valid |",
        "|---|---|---|---|---:|---:|---|",
    ])
    for row in summary["micro_summary"]:
        lines.append(
            f"| `{row['scenario']}` | `{row['verdict']}` | "
            f"`{row['final_active_source']}` | `{row['final_rate_source']}` | "
            f"{fmt(row['final_rate_anchor_age_s'])} | "
            f"{fmt(row['final_rate_anchor_age_frozen_s'])} | "
            f"`{row['final_rate_anchor_valid']}` |"
        )
    lines.extend([
        "",
        "## R26-3 Command-Change Fixtures",
        "",
        "| Scenario | applied at anchor | applied now | expected ff | measured ff | verdict |",
        "|---|---:|---:|---:|---:|---|",
    ])
    for row in summary["command_change_fixtures"]:
        lines.append(
            f"| `{row['scenario']}` | {fmt(row['applied_at_anchor_lookup_mps'])} | "
            f"{fmt(row['applied_now_mps'])} | {fmt(row['expected_feed_forward_mps'])} | "
            f"{fmt(row['measured_feed_forward_mps'])} | `{row['verdict']}` |"
        )
    lines.extend([
        "",
        f"Telemetry coverage: `{summary['rate_telemetry_complete']}` "
        "for rate_source/rate_anchor_age_s in every generated term row.",
        f"Anchor-age telemetry note: now-based `rate_anchor_age_s` range "
        f"{fmt(summary['now_anchor_age_min_s'])}-{fmt(summary['now_anchor_age_max_s'])}; "
        f"frozen/no-now diagnostic range "
        f"{fmt(summary['frozen_anchor_age_min_s'])}-{fmt(summary['frozen_anchor_age_max_s'])}; "
        f"elapsed anchor age range "
        f"{fmt(summary['elapsed_anchor_age_min_s'])}-{fmt(summary['elapsed_anchor_age_max_s'])}; "
        f"now-based advances `{summary['now_anchor_age_advances_flag']}`; "
        f"frozen/no-now static `{summary['frozen_no_now_static_flag']}`.",
        f"Feed-forward corrected sigma_a: `{fmt(summary['measured_sigma_a_mps2'])}`; "
        f"anchor-only comparison: `{fmt(summary['measured_anchor_only_sigma_a_mps2'])}`.",
        f"Applied-command audit: logged applied vz range "
        f"{fmt(summary['logged_applied_vz_min_mps'])}-{fmt(summary['logged_applied_vz_max_mps'])}; "
        f"feed-forward range "
        f"{fmt(summary['feed_forward_min_mps'])}-{fmt(summary['feed_forward_max_mps'])} "
        f"(RMS `{fmt(summary['feed_forward_rms_mps'])}`).",
        "",
        "Artifacts: `features_f2.csv`, `anchor_trial_rows.csv`, "
        "`anchor_trial_summary.csv`, `anchor_transitions.csv`, "
        "`sigma_a_rows.csv`, `sigma_a_summary.csv`, `sigma_regime_summary.csv`, "
        "`sigma_percentile_envelope.csv`, `heldout_age_coverage.csv`, "
        "`age_distribution.csv`, `anchor_age_sweep.csv`, `floor_table.csv`, "
        "`r26_command_change_fixtures.csv`, `r26_micro_rows.csv`, "
        "`r26_micro_summary.csv`, and `summary.json`.",
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
    out_dir = ROOT / "tuning" / f"hold-lift-r26-{src_short}-{head_short}-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    params = apply_patches(ParamSet.load(ROOT / "config" / "params_default.json"), [])
    target = next(t for t in TARGETS if t["label"] == "F2")
    rows, meta = run_video_replay(params, target)
    attach_flight_signals(params, rows, target)
    write_csv(out_dir / "features_f2.csv", rows)

    pairs = exact_pairs(rows)
    side_sigma_e = rms_centered([float(p["residual_e_m"]) for p in pairs])
    side_sigma_e = max(SIDE_SIGMA_E_FLOOR_M, float(side_sigma_e or SIDE_SIGMA_E_FLOOR_M))

    baseline_rows, baseline_transitions = replay_anchor_trial(
        params, rows, "baseline_no_drop", None, side_sigma_e)
    baseline_summary = summarize_trial(baseline_rows, baseline_transitions)
    captures = [r for r in baseline_rows if r.get("shadow_capture")
                and r.get("active_source") == "FULL_QUAD"]
    if not captures:
        raise RuntimeError("F2 baseline did not first-capture FULL")
    first_capture_ts = int(captures[0]["feature_ts_ns"])
    first_capture_range = float(captures[0]["range_z_m"])

    candidates = []
    for pair in pairs:
        ts = int(pair["feature_ts_ns"])
        rng = fnum(pair.get("range_z_m"))
        if ts > first_capture_ts and rng is not None and rng <= first_capture_range:
            candidates.append(pair)

    all_trial_rows = list(baseline_rows)
    all_transitions = list(baseline_transitions)
    trial_summary = [baseline_summary]
    for pair in candidates:
        label = f"anchor_drop_frame_{pair['frame_id']}"
        trial_rows, transitions = replay_anchor_trial(
            params, rows, label, int(pair["feature_ts_ns"]), side_sigma_e)
        for tr in trial_rows:
            tr["candidate_frame_id"] = pair["frame_id"]
            tr["candidate_range_z_m"] = pair["range_z_m"]
        for tr in transitions:
            tr["candidate_frame_id"] = pair["frame_id"]
            tr["candidate_range_z_m"] = pair["range_z_m"]
        summary_row = summarize_trial(trial_rows, transitions)
        summary_row["candidate_frame_id"] = pair["frame_id"]
        summary_row["candidate_range_z_m"] = pair["range_z_m"]
        all_trial_rows.extend(trial_rows)
        all_transitions.extend(transitions)
        trial_summary.append(summary_row)

    write_csv(out_dir / "anchor_trial_rows.csv", all_trial_rows)
    write_csv(out_dir / "anchor_transitions.csv", all_transitions)
    write_csv(out_dir / "anchor_trial_summary.csv", trial_summary)

    legal_trials = [
        r for r in trial_summary
        if str(r["trial"]).startswith("anchor_drop_") and r["full_to_side_count"] > 0
    ]
    r26_1_pass = bool(legal_trials) and all(
        r["owner_term_side_rows"] > 0
        and r["side_shadow_capture_rows"] > 0
        and fnum(r["side_admission_max"]) is not None
        and float(r["side_admission_max"]) <= CORRIDOR_M
        and r["phase_changed_rows"] == 0
        for r in legal_trials
    )

    sigma_a_rows = [
        r for r in all_trial_rows
        if str(r.get("trial", "")).startswith("anchor_drop_")
        and r.get("shadow_owner") == TERM_OWNER
        and r.get("active_source") == "SIDE_PAIR"
        and fnum(r.get("sigma_a_sample_mps2")) is not None
        and fnum(r.get("rate_anchor_age_s")) is not None
        and float(r["rate_anchor_age_s"]) >= 0.10
    ]
    for row in sigma_a_rows:
        age = fnum(row.get("rate_anchor_age_s"))
        row["sigma_regime"] = (
            "switch_adjacent"
            if age is not None and age < 0.20
            else "maintenance"
        )
    write_csv(out_dir / "sigma_a_rows.csv", sigma_a_rows)
    sigma_a_summary = summarize_sigma_a(sigma_a_rows)
    sigma_regime_summary = summarize_sigma_regimes(sigma_a_rows)
    sigma_percentile = percentile_envelope(sigma_a_rows)
    heldout_coverage = heldout_age_coverage(sigma_a_rows)
    age_distribution = summarize_age_distribution(all_trial_rows, all_transitions)
    code_ages = [float(r["rate_anchor_age_s"]) for r in sigma_a_rows
                 if fnum(r.get("rate_anchor_age_s")) is not None]
    frozen_ages = [float(r["rate_anchor_age_frozen_s"]) for r in sigma_a_rows
                   if fnum(r.get("rate_anchor_age_frozen_s")) is not None]
    elapsed_ages = [float(r["rate_anchor_elapsed_s"]) for r in sigma_a_rows
                    if fnum(r.get("rate_anchor_elapsed_s")) is not None]
    feed_forwards = [float(r["rate_feed_forward_mps"]) for r in sigma_a_rows
                     if fnum(r.get("rate_feed_forward_mps")) is not None]
    logged_applied_vz = [float(r["logged_applied_vz_up_mps"]) for r in sigma_a_rows
                         if fnum(r.get("logged_applied_vz_up_mps")) is not None]
    measured_sigma_a = next(
        (fnum(r["sigma_a_rms_mps2"]) for r in sigma_a_summary if r["age_bin"] == "all"),
        None,
    )
    measured_anchor_only_sigma_a = next(
        (
            fnum(r["sigma_a_anchor_only_rms_mps2"])
            for r in sigma_a_summary
            if r["age_bin"] == "all"
        ),
        None,
    )
    floors = floor_table(measured_sigma_a)
    age_sweep = anchor_age_sweep(measured_sigma_a, max(code_ages) if code_ages else None)
    write_csv(out_dir / "sigma_a_summary.csv", sigma_a_summary)
    write_csv(out_dir / "sigma_regime_summary.csv", sigma_regime_summary)
    write_csv(out_dir / "sigma_percentile_envelope.csv", sigma_percentile)
    write_csv(out_dir / "heldout_age_coverage.csv", heldout_coverage)
    write_csv(out_dir / "age_distribution.csv", [age_distribution])
    write_csv(out_dir / "anchor_age_sweep.csv", age_sweep)
    write_csv(out_dir / "floor_table.csv", floors)
    r26_23_pass = measured_sigma_a is not None and measured_sigma_a < 0.35

    micro_rows, micro_summary = micro_replays()
    command_fixtures = command_change_fixtures()
    write_csv(out_dir / "r26_micro_rows.csv", micro_rows)
    write_csv(out_dir / "r26_micro_summary.csv", micro_summary)
    write_csv(out_dir / "r26_command_change_fixtures.csv", command_fixtures)

    rate_telemetry_complete = (
        all("rate_source" in r and "rate_anchor_age_s" in r for r in all_trial_rows)
        and all("rate_source" in r and "rate_anchor_age_s" in r for r in micro_rows)
    )
    summary = {
        "source_ref": args.source_ref,
        "commit": src_head,
        "repo_head": head,
        "non_tuning_delta_from_source": source_delta,
        "flight_meta": meta,
        "exact_pair_count": len(pairs),
        "side_sigma_e_m": side_sigma_e,
        "first_capture_range_m": first_capture_range,
        "first_capture_ts_ns": first_capture_ts,
        "candidate_count": len(candidates),
        "legal_trial_count": len(legal_trials),
        "trial_summary": trial_summary,
        "r26_1_verdict": "PASS" if r26_1_pass else "FAIL",
        "sigma_a_summary": sigma_a_summary,
        "sigma_regime_summary": sigma_regime_summary,
        "sigma_percentile_envelope": sigma_percentile,
        "heldout_age_coverage": heldout_coverage,
        "age_distribution": age_distribution,
        "measured_sigma_a_mps2": measured_sigma_a,
        "measured_anchor_only_sigma_a_mps2": measured_anchor_only_sigma_a,
        "anchor_age_sweep": age_sweep,
        "floor_table": floors,
        "r26_23_verdict": "PASS" if r26_23_pass else "FAIL",
        "micro_summary": micro_summary,
        "command_change_fixtures": command_fixtures,
        "r26_3_verdict": "PASS" if all(r["verdict"] == "PASS" for r in command_fixtures) else "FAIL",
        "r26_456_verdict": "PASS" if all(r["verdict"] == "PASS" for r in micro_summary) else "FAIL",
        "rate_telemetry_complete": rate_telemetry_complete,
        "now_anchor_age_min_s": min(code_ages) if code_ages else "",
        "now_anchor_age_max_s": max(code_ages) if code_ages else "",
        "frozen_anchor_age_min_s": min(frozen_ages) if frozen_ages else "",
        "frozen_anchor_age_max_s": max(frozen_ages) if frozen_ages else "",
        "code_anchor_age_min_s": min(code_ages) if code_ages else "",
        "code_anchor_age_max_s": max(code_ages) if code_ages else "",
        "elapsed_anchor_age_min_s": min(elapsed_ages) if elapsed_ages else "",
        "elapsed_anchor_age_max_s": max(elapsed_ages) if elapsed_ages else "",
        "logged_applied_vz_min_mps": min(logged_applied_vz) if logged_applied_vz else "",
        "logged_applied_vz_max_mps": max(logged_applied_vz) if logged_applied_vz else "",
        "feed_forward_min_mps": min(feed_forwards) if feed_forwards else "",
        "feed_forward_max_mps": max(feed_forwards) if feed_forwards else "",
        "feed_forward_rms_mps": rms(feed_forwards) if feed_forwards else "",
        "now_anchor_age_advances_flag": (
            bool(code_ages) and max(code_ages) - min(code_ages) > 0.10
        ),
        "frozen_no_now_static_flag": (
            bool(frozen_ages and code_ages)
            and max(frozen_ages) - min(frozen_ages) < 1e-6
            and max(code_ages) - min(code_ages) > 0.10
        ),
        "anchor_age_frozen_flag": (
            bool(code_ages and elapsed_ages)
            and max(code_ages) - min(code_ages) < 1e-6
            and max(elapsed_ages) - min(elapsed_ages) > 0.10
        ),
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(out_dir, summary)
    print(f"[anchor-r26] report={out_dir / 'summary.md'}", flush=True)
    print(
        f"[anchor-r26] R26-1={summary['r26_1_verdict']} "
        f"R26-2/3={summary['r26_23_verdict']} "
        f"R26-4/5/6={summary['r26_456_verdict']}",
        flush=True,
    )
    return 0 if (r26_1_pass and r26_23_pass and summary["r26_456_verdict"] == "PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
