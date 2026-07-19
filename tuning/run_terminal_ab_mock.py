from __future__ import annotations

import argparse
import bisect
import csv
import json
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from aigp.app import App, SimConfig  # noqa: E402
from aigp.core.messages import RelPose  # noqa: E402
from aigp.core.params import ParamSet  # noqa: E402
from aigp.learning.flight_log import iter_log  # noqa: E402
from aigp.planning.approach import true_world_dz  # noqa: E402
from simtools.mock_sim import Gate, MockSim  # noqa: E402


LOCK_PATH = Path("C:/Temp/eni_dcim_sim.lock")
RUN_STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
HEAD = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
HEAD_SHORT = HEAD[:7]
OUT_DIR = ROOT / "tuning" / f"terminal-ab-f10b35c-{HEAD_SHORT}-{RUN_STAMP}"
RUNTIME_DIR = ROOT / "tuning" / "runtime-logs" / f"terminal-ab-f10b35c-{HEAD_SHORT}-{RUN_STAMP}"


ARMS = [
    ("control_speed1p8", {
        "planner.commit.speed_mps": 1.8,
    }),
    ("terminal_speed1p8", {
        "planner.commit.speed_mps": 1.8,
        "planner.terminal.enable": True,
    }),
]


def flight_sim_processes() -> list[str]:
    rows: list[str] = []
    for image in ("FlightSim.exe", "DCGame.exe"):
        proc = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {image}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
        )
        text = proc.stdout.strip()
        if text and "No tasks are running" not in text:
            rows.extend(line for line in text.splitlines() if line.strip())
    return rows


def assert_mock_safe() -> None:
    details: list[str] = []
    if LOCK_PATH.exists():
        details.append(f"lock={LOCK_PATH.read_text(errors='replace').strip()}")
    procs = flight_sim_processes()
    if procs:
        details.append("processes=" + " | ".join(procs))
    if details:
        raise RuntimeError("SIM guard blocked terminal A/B: " + "; ".join(details))


def make_cfg(label: str, port_offset: int) -> SimConfig:
    return SimConfig(
        mavlink_ip="127.0.0.1",
        mavlink_port=36550 + port_offset,
        heartbeat_timeout_s=20.0,
        vision_ip="127.0.0.1",
        vision_port=37600 + port_offset,
        control_hz=250,
        planner_div=5,
        timesync_hz=10.0,
        log_dir=str(RUNTIME_DIR / label),
        save_frames_every_n=0,
        record_vision=False,
    )


@contextmanager
def mock_session(label: str, port_offset: int, seed: int) -> Iterator[App]:
    assert_mock_safe()
    cfg = make_cfg(label, port_offset)
    gate = Gate(pos=np.array([7.0, 0.0, -1.5]), travel_yaw=0.0,
                width=1.6, height=1.6)
    sim = MockSim(
        mav_addr=("127.0.0.1", cfg.mavlink_port),
        video_addr=("127.0.0.1", cfg.vision_port),
        gates=[gate],
        image_size=(320, 180),
        video_hz=20.0,
        seed=seed,
    )
    app = App(cfg)
    sim.start()
    time.sleep(0.5)
    try:
        app.connect()
        yield app
    finally:
        app.close()
        sim.stop()
        time.sleep(0.5)


def _f(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt(value, digits: int = 3) -> str:
    value = _f(value)
    return "" if value is None else f"{value:.{digits}f}"


def _fmt_na(value, digits: int = 3) -> str:
    text = _fmt(value, digits)
    return text if text else "n/a"


def _fmt_m(value, digits: int = 3) -> str:
    text = _fmt(value, digits)
    return f"{text}m" if text else "n/a"


def _sign(value: float, eps: float = 0.02) -> int:
    if value > eps:
        return 1
    if value < -eps:
        return -1
    return 0


def _state_from_data(data: dict) -> dict | None:
    gr = data.get("gate_rel")
    if not gr or gr.get("t") is None:
        return None
    try:
        t = np.asarray(gr["t"], dtype=np.float64)
        normal = np.asarray(gr.get("normal", [0.0, 0.0, -1.0]), dtype=np.float64)
        q_att = np.asarray(data.get("q_att"), dtype=np.float64)
        level_roll = float(data.get("level_roll", 0.0))
        level_pitch = float(data.get("level_pitch", 0.0))
    except (TypeError, ValueError):
        return None
    if t.shape != (3,) or q_att.shape != (4,) or not np.isfinite(t).all():
        return None
    rel = RelPose(t=t, normal=normal)
    try:
        true_dz = true_world_dz(rel, q_att, level_roll, level_pitch)
    except Exception:
        true_dz = float("nan")
    center = data.get("gate_center_px") or [None, None]
    return {
        "ts_ns": int(data.get("ts_ns", 0)),
        "range_m": float(t[2]),
        "lateral_m": float(t[0]),
        "camera_y_down_m": float(t[1]),
        "true_dz_m": float(true_dz),
        "gate_age_s": _f(data.get("gate_rel_age_s")),
        "center_x_px": _f(center[0]) if len(center) > 0 else None,
        "center_y_px": _f(center[1]) if len(center) > 1 else None,
    }


def _nearest_state(states: list[dict], ts_ns: int) -> dict | None:
    if not states:
        return None
    ts_values = [s["ts_ns"] for s in states]
    idx = bisect.bisect_left(ts_values, ts_ns)
    candidates = []
    if idx < len(states):
        candidates.append(states[idx])
    if idx:
        candidates.append(states[idx - 1])
    return min(candidates, key=lambda s: abs(s["ts_ns"] - ts_ns)) if candidates else None


def _mean(values: list[float]) -> float | None:
    vals = [float(v) for v in values if np.isfinite(v)]
    return float(np.mean(vals)) if vals else None


def _std(values: list[float]) -> float | None:
    vals = [float(v) for v in values if np.isfinite(v)]
    return float(np.std(vals, ddof=0)) if vals else None


def summarize_term_status(log_dir: str, terminal_enabled: bool) -> tuple[dict, list[str]]:
    counts = {
        "term_rows": 0,
        "engaged_rows": 0,
        "ready_rows": 0,
        "engaged_ready_rows": 0,
        "owner_term_rows": 0,
        "applied_rows": 0,
        "engaged_not_ready_rows": 0,
        "applied_while_not_engaged_rows": 0,
        "applied_while_not_ready_rows": 0,
        "owner_transitions": 0,
        "owner_drop_while_engaged_ready": 0,
        "applied_sign_mismatch_rows": 0,
        "applied_sign_flip_rows": 0,
        "ready_drop_after_applied_rows": 0,
        "feature_rows": 0,
        "unique_feature_ts": 0,
        "feature_certified_rows": 0,
        "feature_probation_rows": 0,
        "feature_none_rows": 0,
        "detection_certified_rows": 0,
        "detection_probation_rows": 0,
        "detection_none_rows": 0,
    }
    e_values: list[float] = []
    vz_values: list[float] = []
    vbz_values: list[float] = []
    states: list[dict] = []
    term_records: list[tuple[dict, dict | None]] = []
    feature_ts: set[int] = set()
    anomalies: list[str] = []
    flight_dir = Path(log_dir)
    if not flight_dir.exists():
        return counts, ["missing log_dir"]
    for rec in iter_log(flight_dir):
        topic = rec.get("topic")
        data = rec.get("data", {})
        if topic == "state":
            state = _state_from_data(data)
            if state is not None:
                states.append(state)
            continue
        if topic == "feature":
            counts["feature_rows"] += 1
            cert = data.get("cert_status", "none")
            if cert == "certified":
                counts["feature_certified_rows"] += 1
            elif cert == "probation":
                counts["feature_probation_rows"] += 1
            else:
                counts["feature_none_rows"] += 1
            ts = data.get("ts_ns")
            if ts is not None:
                feature_ts.add(int(ts))
            continue
        if topic == "detection":
            cert = data.get("cert_status", "none")
            if cert == "certified":
                counts["detection_certified_rows"] += 1
            elif cert == "probation":
                counts["detection_probation_rows"] += 1
            else:
                counts["detection_none_rows"] += 1
            continue
        if topic != "term_status":
            continue
        state = _nearest_state(states, int(data.get("ts_ns", 0)))
        term_records.append((data, state))
        counts["term_rows"] += 1
        engaged = bool(data.get("engaged"))
        ready = bool(data.get("ready"))
        applied = data.get("v_bz_applied") is not None
        owner_term = data.get("owner") == "term"
        if engaged:
            counts["engaged_rows"] += 1
        if ready:
            counts["ready_rows"] += 1
        if engaged and ready:
            counts["engaged_ready_rows"] += 1
        if owner_term:
            counts["owner_term_rows"] += 1
        if applied:
            counts["applied_rows"] += 1
        if engaged and not ready:
            counts["engaged_not_ready_rows"] += 1
        if applied and not engaged:
            counts["applied_while_not_engaged_rows"] += 1
        if applied and not ready:
            counts["applied_while_not_ready_rows"] += 1
        if data.get("e_z") is not None:
            e_values.append(float(data["e_z"]))
        if data.get("vz_up") is not None:
            vz_values.append(float(data["vz_up"]))
        if data.get("v_bz_applied") is not None:
            vbz_values.append(float(data["v_bz_applied"]))
    counts["unique_feature_ts"] = len(feature_ts)
    states.sort(key=lambda s: s["ts_ns"])
    closest = min(states, key=lambda s: abs(s["range_m"])) if states else None
    if closest is not None:
        counts["closest_range_m"] = closest["range_m"]
        counts["closest_lateral_m"] = closest["lateral_m"]
        counts["closest_true_dz_m"] = closest["true_dz_m"]
        counts["closest_center_x_px"] = closest["center_x_px"]
        counts["closest_center_y_px"] = closest["center_y_px"]
    else:
        counts["closest_range_m"] = ""
        counts["closest_lateral_m"] = ""
        counts["closest_true_dz_m"] = ""
        counts["closest_center_x_px"] = ""
        counts["closest_center_y_px"] = ""

    prev_owner = None
    prev_applied_sign = 0
    saw_applied = False
    saw_ready_after_applied = False
    ready_seen = False
    first_ready_idx = None
    first_owner_idx = None
    first_applied_idx = None
    ranges_by_flag: dict[str, list[float]] = {
        "engaged": [], "ready": [], "engaged_ready": [], "owner": [], "applied": []
    }
    for idx, (data, state) in enumerate(term_records):
        owner = data.get("owner", "")
        engaged = bool(data.get("engaged"))
        ready = bool(data.get("ready"))
        owner_term = owner == "term"
        e_z = _f(data.get("e_z"))
        vz_up = _f(data.get("vz_up"))
        v_bz = _f(data.get("v_bz_applied"))
        if prev_owner is not None and owner != prev_owner:
            counts["owner_transitions"] += 1
            if prev_owner == "term" and engaged and ready:
                counts["owner_drop_while_engaged_ready"] += 1
        prev_owner = owner
        if ready and first_ready_idx is None:
            first_ready_idx = idx
        if owner_term and first_owner_idx is None:
            first_owner_idx = idx
        if v_bz is not None and first_applied_idx is None:
            first_applied_idx = idx
        if saw_applied and not ready and saw_ready_after_applied:
            counts["ready_drop_after_applied_rows"] += 1
        if ready and saw_applied:
            saw_ready_after_applied = True
        if state is not None:
            if engaged:
                ranges_by_flag["engaged"].append(state["range_m"])
            if ready:
                ranges_by_flag["ready"].append(state["range_m"])
            if engaged and ready:
                ranges_by_flag["engaged_ready"].append(state["range_m"])
            if owner_term:
                ranges_by_flag["owner"].append(state["range_m"])
            if v_bz is not None:
                ranges_by_flag["applied"].append(state["range_m"])
        if e_z is not None and v_bz is not None:
            # e_z is +up; body z is down-positive, so the expected sign is opposite.
            if _sign(e_z) and _sign(v_bz) and _sign(e_z) == _sign(v_bz):
                counts["applied_sign_mismatch_rows"] += 1
        if e_z is not None and vz_up is not None:
            if _sign(e_z) and _sign(vz_up) and _sign(e_z) != _sign(vz_up):
                counts["vz_up_sign_mismatch_rows"] = (
                    int(counts.get("vz_up_sign_mismatch_rows", 0)) + 1)
        if v_bz is not None:
            sign = _sign(v_bz)
            if prev_applied_sign and sign and sign != prev_applied_sign:
                counts["applied_sign_flip_rows"] += 1
            if sign:
                prev_applied_sign = sign
            saw_applied = True
        if ready:
            ready_seen = True
    counts.setdefault("vz_up_sign_mismatch_rows", 0)
    for key, values in ranges_by_flag.items():
        counts[f"first_{key}_range_m"] = values[0] if values else ""
        counts[f"min_{key}_range_m"] = min(values) if values else ""
        counts[f"max_{key}_range_m"] = max(values) if values else ""
    if first_ready_idx is not None and first_owner_idx is not None:
        counts["ready_to_owner_delay_rows"] = max(0, first_owner_idx - first_ready_idx)
    else:
        counts["ready_to_owner_delay_rows"] = ""
    if first_ready_idx is not None and first_applied_idx is not None:
        counts["ready_to_applied_delay_rows"] = max(0, first_applied_idx - first_ready_idx)
    else:
        counts["ready_to_applied_delay_rows"] = ""
    if first_owner_idx is not None and first_applied_idx is not None:
        counts["owner_to_applied_delay_rows"] = max(0, first_applied_idx - first_owner_idx)
    else:
        counts["owner_to_applied_delay_rows"] = ""
    if e_values:
        counts["e_z_min"] = min(e_values)
        counts["e_z_max"] = max(e_values)
    else:
        counts["e_z_min"] = ""
        counts["e_z_max"] = ""
    if vz_values:
        counts["vz_up_min"] = min(vz_values)
        counts["vz_up_max"] = max(vz_values)
    else:
        counts["vz_up_min"] = ""
        counts["vz_up_max"] = ""
    if vbz_values:
        counts["v_bz_min"] = min(vbz_values)
        counts["v_bz_max"] = max(vbz_values)
        counts["v_bz_max_step"] = max(
            [abs(vbz_values[i] - vbz_values[i - 1]) for i in range(1, len(vbz_values))]
            or [0.0]
        )
    else:
        counts["v_bz_min"] = ""
        counts["v_bz_max"] = ""
        counts["v_bz_max_step"] = ""
    if terminal_enabled and counts["term_rows"] == 0:
        anomalies.append("terminal enabled but no term_status rows")
    if not terminal_enabled and counts["term_rows"] != 0:
        anomalies.append("terminal disabled but term_status rows exist")
    if counts["applied_while_not_engaged_rows"]:
        anomalies.append("v_bz_applied while not engaged")
    if counts["applied_while_not_ready_rows"]:
        anomalies.append("v_bz_applied while oracle not ready")
    if terminal_enabled and counts["engaged_rows"] and counts["ready_rows"] == 0:
        anomalies.append("engaged but oracle never ready")
    if (terminal_enabled and counts["engaged_ready_rows"]
            and counts["owner_term_rows"] == 0):
        anomalies.append("engaged+ready but owner never term")
    elif (terminal_enabled and counts["ready_rows"]
          and counts["owner_term_rows"] == 0):
        anomalies.append("ready and engagement never overlapped")
    if terminal_enabled and counts["owner_term_rows"] and counts["applied_rows"] == 0:
        anomalies.append("owner term but no applied body-z")
    if counts["applied_sign_mismatch_rows"]:
        anomalies.append("wrong-sign v_bz_applied vs e_z")
    if counts["vz_up_sign_mismatch_rows"]:
        anomalies.append("wrong-sign vz_up vs e_z")
    if counts["owner_drop_while_engaged_ready"]:
        anomalies.append("owner drop while engaged+ready")
    if counts["applied_sign_flip_rows"]:
        anomalies.append("v_bz sign flip jitter")
    if counts["ready_drop_after_applied_rows"]:
        anomalies.append("readiness drop after applied")
    return counts, anomalies


def write_csv(path: Path, rows: list[dict]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def arm_summary(rows: list[dict]) -> dict:
    total = len(rows)
    passes = sum(1 for r in rows if int(r.get("gates_passed") or 0) >= 1)
    finished = sum(1 for r in rows if r.get("finished") is True)
    anomalies = sum(1 for r in rows if r.get("term_anomalies"))
    lateral = [_f(r.get("closest_lateral_m")) for r in rows]
    dz = [_f(r.get("closest_true_dz_m")) for r in rows]
    closest_range = [_f(r.get("closest_range_m")) for r in rows]
    lateral_vals = [v for v in lateral if v is not None]
    dz_vals = [v for v in dz if v is not None]
    range_vals = [v for v in closest_range if v is not None]
    return {
        "runs": total,
        "passes": passes,
        "pass_rate": passes / total if total else 0.0,
        "finished": finished,
        "finish_rate": finished / total if total else 0.0,
        "term_anomaly_runs": anomalies,
        "closest_range_mean_m": _mean(range_vals),
        "closest_lateral_mean_m": _mean(lateral_vals),
        "closest_lateral_std_m": _std(lateral_vals),
        "closest_true_dz_mean_m": _mean(dz_vals),
        "closest_true_dz_std_m": _std(dz_vals),
    }


def run_arm(label: str, patches: dict, runs: int, arm_index: int) -> list[dict]:
    rows: list[dict] = []
    params = ParamSet.load(ROOT / "config" / "params_default.json").patch({
        "safety.imu_stale_s": 0.25,
        **patches,
    })
    terminal_enabled = bool(patches.get("planner.terminal.enable", False))
    with mock_session(label, port_offset=arm_index * 20, seed=20260719 + arm_index) as app:
        for idx in range(1, runs + 1):
            assert_mock_safe()
            result = app.reset_and_fly(params, settle_s=1.0, max_duration_s=45.0)
            term_counts, anomalies = summarize_term_status(result.get("log_dir", ""),
                                                           terminal_enabled)
            row = {
                "arm": label,
                "idx": idx,
                "flight_id": result.get("flight_id", ""),
                "gates_passed": result.get("gates_passed", 0),
                "finished": bool(result.get("finished", False)),
                "aborted": bool(result.get("aborted", False)),
                "abort_reason": result.get("abort_reason", ""),
                "duration_s": result.get("duration_s", ""),
                "gate_clips": result.get("gate_clips", 0),
                "env_hits": result.get("env_hits", 0),
                "overrun_frac": result.get("loop_stats", {}).get("overrun_frac", ""),
                "log_dir": result.get("log_dir", ""),
                "term_anomalies": "; ".join(anomalies),
                **term_counts,
            }
            rows.append(row)
            print(
                f"[terminal-ab {label}] {idx}/{runs} "
                f"gates={row['gates_passed']} finished={row['finished']} "
                f"term_rows={row['term_rows']} anomalies={row['term_anomalies']}",
                flush=True,
            )
    return rows


def write_report(rows: list[dict], summaries: dict[str, dict]) -> None:
    lines = [
        "# Terminal A/B Mock",
        "",
        "Role: QA & MOCK-TUNER.",
        "Scope: mock only. No real simulator was launched, reset, clicked, or commanded.",
        f"Commit: `{HEAD}`.",
        "Base harness patch: `safety.imu_stale_s=0.25`.",
        "",
        "## Arms",
        "",
        "| Arm | Patches | Passes | Runs | Pass rate | Finished | Terminal anomaly runs | closest R mean | lateral mean/std | true dz mean/std |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label, patches in ARMS:
        summary = summaries[label]
        patch_text = " ".join(f"--patch {k}={v}" for k, v in patches.items())
        lines.append(
            f"| `{label}` | `{patch_text}` | {summary['passes']} | "
            f"{summary['runs']} | {summary['pass_rate']:.1%} | "
            f"{summary['finished']} | {summary['term_anomaly_runs']} | "
            f"{_fmt(summary['closest_range_mean_m'])} | "
            f"{_fmt(summary['closest_lateral_mean_m'])}/{_fmt(summary['closest_lateral_std_m'])} | "
            f"{_fmt(summary['closest_true_dz_mean_m'])}/{_fmt(summary['closest_true_dz_std_m'])} |"
        )
    lines.extend([
        "",
        "## Term Status Notes",
        "",
        "| Arm | Run | Gates | Finished | term rows | engaged | ready | engaged+ready | owner=term | applied | first owner R | first applied R | e_z min/max | v_bz min/max | sign bad | owner transitions | closest y/dz | anomalies |",
        "|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ])
    for row in rows:
        lines.append(
            f"| `{row['arm']}` | {row['idx']} | {row['gates_passed']} | "
            f"{row['finished']} | {row['term_rows']} | {row['engaged_rows']} | "
            f"{row['ready_rows']} | {row.get('engaged_ready_rows', '')} | "
            f"{row['owner_term_rows']} | "
            f"{row['applied_rows']} | {_fmt(row.get('first_owner_range_m'))} | "
            f"{_fmt(row.get('first_applied_range_m'))} | "
            f"{_fmt(row.get('e_z_min'))}/{_fmt(row.get('e_z_max'))} | "
            f"{_fmt(row.get('v_bz_min'))}/{_fmt(row.get('v_bz_max'))} | "
            f"{row.get('applied_sign_mismatch_rows', '')} | "
            f"{row.get('owner_transitions', '')} | "
            f"{_fmt(row.get('closest_lateral_m'))}/{_fmt(row.get('closest_true_dz_m'))} | "
            f"{row['term_anomalies']} |"
        )
    lines.extend([
        "",
        "## Gatekeeping Answers",
        "",
    ])
    for label, _patches in ARMS:
        arm_rows = [r for r in rows if r["arm"] == label]
        engaged_ready_ranges = [_f(r.get("first_engaged_ready_range_m"))
                                for r in arm_rows]
        owner_ranges = [_f(r.get("first_owner_range_m")) for r in arm_rows]
        applied_ranges = [_f(r.get("first_applied_range_m")) for r in arm_rows]
        engaged_ready_ranges = [v for v in engaged_ready_ranges if v is not None]
        owner_ranges = [v for v in owner_ranges if v is not None]
        applied_ranges = [v for v in applied_ranges if v is not None]
        sign_bad = sum(int(r.get("applied_sign_mismatch_rows") or 0) for r in arm_rows)
        chatter = sum(1 for r in arm_rows if int(r.get("owner_drop_while_engaged_ready") or 0)
                      or int(r.get("owner_transitions") or 0) > 2)
        jitter = sum(1 for r in arm_rows if int(r.get("applied_sign_flip_rows") or 0))
        ready_transient = sum(
            1 for r in arm_rows
            if int(r.get("applied_while_not_ready_rows") or 0)
            or int(r.get("ready_drop_after_applied_rows") or 0)
        )
        certified_feature_runs = sum(
            1 for r in arm_rows if int(r.get("feature_certified_rows") or 0)
        )
        engaged_ready_no_owner = sum(
            1 for r in arm_rows
            if int(r.get("engaged_ready_rows") or 0)
            and not int(r.get("owner_term_rows") or 0)
        )
        lines.append(
            f"- `{label}`: engaged+ready runs {len(engaged_ready_ranges)}/{len(arm_rows)} "
            f"(first range mean {_fmt_m(_mean(engaged_ready_ranges))}); "
            f"owner=term runs {len(owner_ranges)}/{len(arm_rows)} "
            f"(first range mean {_fmt_m(_mean(owner_ranges))}, "
            f"min {_fmt_m(min(owner_ranges) if owner_ranges else None)}); "
            f"v_bz_applied runs {len(applied_ranges)}/{len(arm_rows)} "
            f"(first range mean {_fmt_m(_mean(applied_ranges))}); "
            f"wrong-sign rows {sign_bad}; owner-chatter runs {chatter}; "
            f"jitter runs {jitter}; readiness-transient runs {ready_transient}; "
            f"certified-feature runs {certified_feature_runs}/{len(arm_rows)}; "
            f"engaged+ready/no-owner runs {engaged_ready_no_owner}/{len(arm_rows)}."
        )
    live_rows = [r for r in rows if r["arm"] == "terminal_speed1p8"]
    live_owner_rows = sum(int(r.get("owner_term_rows") or 0) for r in live_rows)
    live_applied_rows = sum(int(r.get("applied_rows") or 0) for r in live_rows)
    live_engaged_ready = sum(1 for r in live_rows
                             if int(r.get("engaged_ready_rows") or 0))
    verdict = ("NO-GO for live terminal arms: the mock live arm never actuated."
               if live_rows and (live_owner_rows == 0 or live_applied_rows == 0)
               else "GO from mock terminal authority wiring.")
    lines.extend([
        "",
        "## Verdict",
        "",
        verdict,
        "",
        f"Live arm summary: owner=term rows `{live_owner_rows}`, "
        f"v_bz_applied rows `{live_applied_rows}`, "
        f"runs with engaged+ready `{live_engaged_ready}/{len(live_rows)}`.",
    ])
    lines.extend([
        "",
        "Artifacts: `runs.csv`, `runs.json`, and per-flight logs under "
        f"`{RUNTIME_DIR.relative_to(ROOT)}`.",
    ])
    (OUT_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT_DIR / "summary.json").write_text(
        json.dumps({"commit": HEAD, "arms": ARMS, "summaries": summaries,
                    "rows": rows}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def rebuild_existing(out_dir: Path) -> None:
    global OUT_DIR, RUNTIME_DIR
    OUT_DIR = out_dir.resolve()
    rows = json.loads((OUT_DIR / "runs.json").read_text(encoding="utf-8"))
    log_dirs = [Path(r.get("log_dir", "")) for r in rows if r.get("log_dir")]
    if log_dirs:
        RUNTIME_DIR = log_dirs[0].resolve().parents[1]
    rebuilt: list[dict] = []
    for row in rows:
        terminal_enabled = row.get("arm") == "terminal_speed1p8"
        term_counts, anomalies = summarize_term_status(row.get("log_dir", ""),
                                                       terminal_enabled)
        keep = {k: v for k, v in row.items()
                if k not in term_counts and k != "term_anomalies"}
        rebuilt.append({
            **keep,
            "term_anomalies": "; ".join(anomalies),
            **term_counts,
        })
    summaries = {}
    for label, _patches in ARMS:
        summaries[label] = arm_summary([r for r in rebuilt if r["arm"] == label])
    write_csv(OUT_DIR / "runs.csv", rebuilt)
    (OUT_DIR / "runs.json").write_text(
        json.dumps(rebuilt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(rebuilt, summaries)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--rebuild-from", type=Path)
    args = parser.parse_args(argv)
    if args.rebuild_from:
        rebuild_existing(args.rebuild_from)
        print(f"[terminal-ab] rebuilt report={OUT_DIR / 'summary.md'}", flush=True)
        return 0
    assert_mock_safe()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    summaries: dict[str, dict] = {}
    for arm_index, (label, patches) in enumerate(ARMS):
        arm_rows = run_arm(label, patches, args.runs, arm_index)
        rows.extend(arm_rows)
        summaries[label] = arm_summary(arm_rows)
    write_csv(OUT_DIR / "runs.csv", rows)
    (OUT_DIR / "runs.json").write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n",
                                        encoding="utf-8")
    write_report(rows, summaries)
    print(f"[terminal-ab] report={OUT_DIR / 'summary.md'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
