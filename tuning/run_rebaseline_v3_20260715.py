from __future__ import annotations

import argparse
import csv
import ctypes
import json
import os
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from aigp.app import App, SimConfig
from aigp.core.params import ParamSet
from aigp.learning.metrics import score_flight
from aigp.learning.optimizers import CEM
from aigp.learning.results_db import ResultsDB
from simtools.mock_sim import Gate, MockSim

RUN_LABEL = "rebaseline-v4"
RUN_ID = os.environ.get("ENI_REBASELINE_RUN_ID", "2026-07-16-rebaseline-v4-44f5f74")
OUT_DIR = ROOT / "tuning" / "campaigns" / RUN_ID
RUNTIME_DIR = ROOT / "tuning" / "runtime-logs" / RUN_ID
LOCK_PATH = Path("C:/Temp/eni_dcim_sim.lock")
MAV_BASE = 30550
VIDEO_BASE = 31600
LOW_LOAD = False

TUNE_BOUNDS = {
    "planner.approach.aim_up_m": (0.1, 0.6),
    "planner.commit.distance_m": (1.5, 3.5),
    "planner.commit.duration_s": (1.0, 2.0),
    "estimation.vision_vel_blend": (0.1, 0.3),
    "control.att_rate.vz_p": (0.5, 1.2),
    "control.att_rate.vz_i": (0.2, 0.7),
}

BEFORE_CI = {
    "commit": "f5e88659a26056a7f692412004e30fac498dc276",
    "ci_overrun_frac": 0.7431254191817572,
    "hover_probe_overrun_frac": 0.7468099395567495,
    "heartbeat_timeouts": 2,
    "pytest_summary": "3 failed, 69 passed, 1 xfailed, 2 warnings in 49.60s",
    "campaign_guard": "guard-aborted: normal attempt 1 stale-IMU 18.2%, then SIM LOCK appeared",
}


def commit_hash() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def flight_sim_processes() -> list[str]:
    rows: list[str] = []
    for image in ("FlightSim.exe", "DCGame.exe"):
        proc = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {image}", "/FO", "CSV", "/NH"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        text = proc.stdout.strip()
        if text and "No tasks are running" not in text:
            rows.extend(line for line in text.splitlines() if line.strip())
    return rows


def assert_clean_sim_guard() -> None:
    procs = flight_sim_processes()
    lock_exists = LOCK_PATH.exists()
    if procs or lock_exists:
        details = []
        if procs:
            details.append("processes=" + " | ".join(procs))
        if lock_exists:
            details.append(f"lock={LOCK_PATH.read_text(errors='replace').strip()}")
        raise RuntimeError("sim guard blocked run: " + "; ".join(details))


def filetime_to_int(ft) -> int:
    return (ft.dwHighDateTime << 32) | ft.dwLowDateTime


def cpu_percent_sample(interval_s: float = 0.25) -> float | None:
    class FILETIME(ctypes.Structure):
        _fields_ = [
            ("dwLowDateTime", ctypes.c_ulong),
            ("dwHighDateTime", ctypes.c_ulong),
        ]

    get_times = ctypes.windll.kernel32.GetSystemTimes

    def sample() -> tuple[int, int, int] | None:
        idle, kernel, user = FILETIME(), FILETIME(), FILETIME()
        if not get_times(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
            return None
        return filetime_to_int(idle), filetime_to_int(kernel), filetime_to_int(user)

    first = sample()
    if first is None:
        return None
    time.sleep(interval_s)
    second = sample()
    if second is None:
        return None
    idle_delta = second[0] - first[0]
    total_delta = (second[1] - first[1]) + (second[2] - first[2])
    if total_delta <= 0:
        return None
    return max(0.0, min(100.0, 100.0 * (1.0 - idle_delta / total_delta)))


def cpu_row(phase: str, batch: str) -> dict:
    return {
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "phase": phase,
        "batch": batch,
        "cpu_total_pct": cpu_percent_sample(),
        "lock_exists": LOCK_PATH.exists(),
        "flightsim_processes": " | ".join(flight_sim_processes()),
    }


def make_cfg(label: str, port_offset: int) -> SimConfig:
    control_hz = 125 if LOW_LOAD else 250
    return SimConfig(
        mavlink_ip="127.0.0.1",
        mavlink_port=MAV_BASE + port_offset,
        heartbeat_timeout_s=20.0,
        vision_ip="127.0.0.1",
        vision_port=VIDEO_BASE + port_offset,
        control_hz=control_hz,
        planner_div=5,
        timesync_hz=10.0,
        log_dir=str(RUNTIME_DIR / label),
        save_frames_every_n=0,
        record_vision=False,
    )


@contextmanager
def mock_session(label: str, port_offset: int, gates: list[Gate] | None = None, **sim_kwargs):
    assert_clean_sim_guard()
    cfg = make_cfg(label, port_offset)
    sim = MockSim(
        mav_addr=("127.0.0.1", cfg.mavlink_port),
        video_addr=("127.0.0.1", cfg.vision_port),
        gates=gates,
        **sim_kwargs,
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


def low_load_mock_opts() -> dict:
    if not LOW_LOAD:
        return {}
    return {
        "video_hz": 12.0,
        "imu_hz": 100.0,
        "physics_hz": 125.0,
        "image_size": (320, 180),
    }


def measure_hover_overrun(base_params: ParamSet) -> dict:
    assert_clean_sim_guard()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    gates = [Gate(pos=np.array([50.0, 0.0, -1.5]), travel_yaw=0.0)]
    with mock_session("hover-overrun", port_offset=80, gates=gates,
                      **low_load_mock_opts()) as app:
        params = base_params.patch({
            "safety.imu_stale_s": 0.25,
            "planner.search.yaw_rate_rps": 0.4,
            "perception.detector.red_sat_min": 256,
        })
        result = app.fly(params, max_duration_s=6.0)
    loop_stats = result.get("loop_stats", {})
    row = {
        "commit": commit_hash(),
        "flight_id": result.get("flight_id", ""),
        "aborted": result.get("aborted", False),
        "abort_reason": result.get("abort_reason", ""),
        "gates_passed": result.get("gates_passed", 0),
        "env_hits": result.get("env_hits", 0),
        "gate_clips": result.get("gate_clips", 0),
        "ticks": loop_stats.get("ticks"),
        "overrun_frac": loop_stats.get("overrun_frac"),
        "log_dir": result.get("log_dir", ""),
    }
    (OUT_DIR / "hover-overrun-after.json").write_text(
        json.dumps(row, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[hover-overrun] overrun_frac={row['overrun_frac']} "
          f"ticks={row['ticks']} abort={row['abort_reason']}", flush=True)
    return row


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def flight_row(idx: int, label: str, params: ParamSet, result: dict,
               score: float | None = None, attempt: int = 1, error: str = "") -> dict:
    abort_reason = result.get("abort_reason", "")
    return {
        "attempt": attempt,
        "label": label,
        "idx": idx,
        "flight_id": result.get("flight_id", ""),
        "gates_passed": result.get("gates_passed", 0),
        "finished": bool(result.get("finished", False)),
        "aborted": bool(result.get("aborted", False)),
        "abort_reason": abort_reason,
        "stale_imu": "stale channels: imu" in str(abort_reason),
        "duration_s": result.get("duration_s", ""),
        "lap_time_s": result.get("lap_time_s", ""),
        "gate_clips": result.get("gate_clips", 0),
        "env_hits": result.get("env_hits", 0),
        "score": score if score is not None else "",
        "param_hash": params.hash,
        "log_dir": result.get("log_dir", ""),
        "error": error,
    }


def summarize(rows: list[dict]) -> dict:
    total = len(rows)
    if total == 0:
        return {"flights": 0}
    gates = [int(r.get("gates_passed") or 0) for r in rows]
    scores = [float(r["score"]) for r in rows if r.get("score") not in ("", None)]
    stale = sum(1 for r in rows if str(r.get("stale_imu")) == "True" or r.get("stale_imu") is True)
    return {
        "flights": total,
        "total_gates": sum(gates),
        "max_gates": max(gates),
        "gate_pass_rate": sum(1 for g in gates if g >= 1) / total,
        "finish_rate": sum(1 for r in rows if r.get("finished") is True or str(r.get("finished")) == "True") / total,
        "abort_rate": sum(1 for r in rows if r.get("aborted") is True or str(r.get("aborted")) == "True") / total,
        "stale_imu": stale,
        "stale_imu_rate": stale / total,
        "best_score": max(scores) if scores else None,
        "avg_score": sum(scores) / len(scores) if scores else None,
    }


def run_campaign_attempt(attempt: int, base_params: ParamSet) -> tuple[bool, dict[str, float], list[dict], list[dict]]:
    rows: list[dict] = []
    cpu_rows: list[dict] = [cpu_row("campaign", f"attempt-{attempt}-start")]
    db_path = OUT_DIR / f"campaign-cem-attempt-{attempt}" / "results.sqlite"
    db = ResultsDB(db_path)
    optimizer = CEM(TUNE_BOUNDS, seed=20260715 + attempt)
    db.record_campaign(
        f"{RUN_LABEL}-cem-attempt-{attempt}",
        "CEM",
        list(TUNE_BOUNDS.keys()),
        datetime.now(timezone.utc).isoformat(),
    )
    with mock_session(f"campaign-attempt-{attempt}", port_offset=attempt,
                      **low_load_mock_opts()) as app:
        for idx in range(1, 41):
            assert_clean_sim_guard()
            if idx == 1 or (idx - 1) % 10 == 0:
                cpu_rows.append(cpu_row("campaign", f"attempt-{attempt}-before-{idx:02d}"))
            overrides = optimizer.ask()
            params = base_params.patch(overrides)
            started_at = datetime.now(timezone.utc).isoformat()
            try:
                result = app.reset_and_fly(params, settle_s=1.0, max_duration_s=45.0)
                score = score_flight(result, params)
                optimizer.tell(overrides, score)
                db.record_flight(
                    result.get("flight_id", f"attempt-{attempt}-{idx:03d}"),
                    started_at,
                    params,
                    result,
                    score,
                    campaign_id=f"{RUN_LABEL}-cem-attempt-{attempt}",
                )
                row = flight_row(idx, "campaign", params, result, score, attempt)
            except Exception as exc:  # noqa: BLE001 - measurement diagnostics
                row = flight_row(idx, "campaign", params, {}, None, attempt,
                                 f"{type(exc).__name__}: {exc}")
            rows.append(row)
            stale_rate = summarize(rows)["stale_imu_rate"]
            print(
                f"[campaign attempt {attempt}] {idx}/40 gates={row['gates_passed']} "
                f"finished={row['finished']} stale_imu={row['stale_imu']} "
                f"stale_rate={stale_rate:.1%}",
                flush=True,
            )
            if idx >= 10 and stale_rate > 0.10:
                print(f"[campaign attempt {attempt}] aborting contaminated measurement: "
                      f"stale_imu_rate={stale_rate:.1%}", flush=True)
                break
    db.close()
    cpu_rows.append(cpu_row("campaign", f"attempt-{attempt}-end"))
    attempt_dir = OUT_DIR / f"campaign-cem-attempt-{attempt}"
    write_csv(attempt_dir / "flights.csv", rows)
    write_csv(attempt_dir / "cpu.csv", cpu_rows)
    best = optimizer.best
    best_params = best[0] if best is not None else {}
    (attempt_dir / "best-params.json").write_text(
        json.dumps(best_params, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    valid = len(rows) == 40 and summarize(rows)["stale_imu_rate"] <= 0.10
    return valid, best_params, rows, cpu_rows


def run_campaign(base_params: ParamSet) -> tuple[dict[str, float], list[dict], list[dict], int, bool]:
    all_cpu: list[dict] = []
    for attempt in range(1, 4):
        valid, best_params, rows, cpu_rows = run_campaign_attempt(attempt, base_params)
        all_cpu.extend(cpu_rows)
        if valid:
            return best_params, rows, all_cpu, attempt, True
    return best_params, rows, all_cpu, 3, False


def verify(label: str, params: ParamSet, n: int, port_offset: int) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    cpu_rows = [cpu_row("verify", f"{label}-start")]
    with mock_session(f"verify-{label}", port_offset=port_offset,
                      **low_load_mock_opts()) as app:
        for idx in range(1, n + 1):
            assert_clean_sim_guard()
            if idx == 1 or (idx - 1) % 10 == 0:
                cpu_rows.append(cpu_row("verify", f"{label}-before-{idx:02d}"))
            try:
                result = app.reset_and_fly(params, settle_s=1.0, max_duration_s=45.0)
                score = score_flight(result, params)
                row = flight_row(idx, label, params, result, score)
            except Exception as exc:  # noqa: BLE001 - measurement diagnostics
                row = flight_row(idx, label, params, {}, None, error=f"{type(exc).__name__}: {exc}")
            rows.append(row)
            print(f"[verify {label}] {idx}/{n} gates={row['gates_passed']} "
                  f"finished={row['finished']} stale_imu={row['stale_imu']}", flush=True)
    cpu_rows.append(cpu_row("verify", f"{label}-end"))
    write_csv(OUT_DIR / "verification" / f"{label}.csv", rows)
    write_csv(OUT_DIR / "verification" / f"{label}-cpu.csv", cpu_rows)
    return rows, cpu_rows


def bullets(summary: dict) -> str:
    return "\n".join([
        f"- Flights: {summary.get('flights', 0)}",
        f"- Total gates: {summary.get('total_gates', 0)}",
        f"- Max gates: {summary.get('max_gates', 0)}",
        f"- Gate-pass rate: {summary.get('gate_pass_rate', 0.0):.1%}",
        f"- Finish rate: {summary.get('finish_rate', 0.0):.1%}",
        f"- Abort rate: {summary.get('abort_rate', 0.0):.1%}",
        f"- Stale-IMU: {summary.get('stale_imu', 0)} ({summary.get('stale_imu_rate', 0.0):.1%})",
        f"- Best score: {summary.get('best_score')}",
        f"- Avg score: {summary.get('avg_score')}",
    ])


def write_summary(best_params: dict[str, float], campaign_rows: list[dict],
                  default_rows: list[dict], best_rows: list[dict],
                  cpu_rows: list[dict], attempt: int, valid_campaign: bool,
                  hover_after: dict) -> None:
    campaign_summary = summarize(campaign_rows)
    default_summary = summarize(default_rows)
    best_summary = summarize(best_rows)
    p0_default_zero = default_summary.get("finish_rate") == 0.0
    patch = " ".join(f"--patch {k}={v}" for k, v in best_params.items())
    patch_text = patch if valid_campaign else (
        "# NO VALID SAKANA PATCH: all campaign attempts exceeded the "
        "stale-IMU contamination guard."
    )
    best_heading = (
        "Best parameters:"
        if valid_campaign
        else "Best parameters from rejected contaminated attempt:"
    )
    lines = [
        f"# Re-Baseline v4 Mock Campaign - {RUN_ID}",
        "",
        "Role: QA & MOCK-TUNER.",
        "",
        f"Commit: `{commit_hash()}`.",
        "Pre-run requirement: clean machine, no `FlightSim`/`DCGame`, no sim lock.",
        "Scope: mock only. No real simulator was launched, reset, clicked, or commanded.",
        f"Mode: `{'low-load' if LOW_LOAD else 'normal'}`.",
        "",
        "## Windows Timer Fix Quantification",
        "",
        f"- Before commit: `{BEFORE_CI['commit']}`.",
        f"- Before CI hover `overrun_frac`: `{BEFORE_CI['ci_overrun_frac']}`.",
        f"- Before standalone hover probe `overrun_frac`: `{BEFORE_CI['hover_probe_overrun_frac']}`.",
        f"- Before heartbeat timeouts in Windows CI: `{BEFORE_CI['heartbeat_timeouts']}`.",
        f"- Before pytest summary: `{BEFORE_CI['pytest_summary']}`.",
        f"- After commit: `{commit_hash()}`.",
        f"- After hover `overrun_frac`: `{hover_after.get('overrun_frac')}`.",
        f"- After hover ticks: `{hover_after.get('ticks')}`.",
        f"- After hover abort reason: `{hover_after.get('abort_reason')}`.",
        "",
        "## Guard",
        "",
        f"- Campaign attempt used: `{attempt}`.",
        f"- Campaign valid under stale-IMU <=10% rule: `{valid_campaign}`.",
        f"- Default 0% finish P0 finding: `{p0_default_zero}`.",
        "",
        "## Bounds",
        "",
        "```json",
        json.dumps(TUNE_BOUNDS, indent=2, sort_keys=True),
        "```",
        "",
        "## 40-Flight CEM Campaign",
        "",
        bullets(campaign_summary),
        "",
        best_heading,
        "",
        "```json",
        json.dumps(best_params, indent=2, sort_keys=True),
        "```",
        "",
        "Sakana patch starting point:",
        "",
        "```powershell",
        patch_text,
        "```",
        "",
        "## Verification: Default vs Best",
        "",
        "Default params, 20 flights:",
        bullets(default_summary),
        "",
        "Best params, 20 flights:",
        bullets(best_summary),
        "",
        "## CPU Samples",
        "",
        "CPU samples are recorded in `cpu.csv` and per-verification CPU CSVs.",
    ]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT_DIR / "sakana-next-patch.txt").write_text(patch_text + "\n", encoding="utf-8")
    write_csv(OUT_DIR / "cpu.csv", cpu_rows)
    (OUT_DIR / "summary.json").write_text(
        json.dumps({
            "run_id": RUN_ID,
            "commit": commit_hash(),
            "bounds": TUNE_BOUNDS,
            "campaign_attempt": attempt,
            "valid_campaign": valid_campaign,
            "mode": "low-load" if LOW_LOAD else "normal",
            "before_ci": BEFORE_CI,
            "hover_overrun_after": hover_after,
            "best_params": best_params,
            "sakana_patch": patch if valid_campaign else None,
            "campaign_summary": campaign_summary,
            "default_summary": default_summary,
            "best_summary": best_summary,
            "default_zero_finish_p0": p0_default_zero,
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    global LOW_LOAD
    parser = argparse.ArgumentParser()
    parser.add_argument("--low-load", action="store_true",
                        help="Use reduced-fidelity mock settings for busy Windows machines")
    args = parser.parse_args(argv)
    LOW_LOAD = bool(args.low_load)

    assert_clean_sim_guard()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    base_params = ParamSet.load(ROOT / "config" / "params_default.json").patch(
        {"safety.imu_stale_s": 0.25})
    print(f"[{RUN_LABEL}] commit={commit_hash()} mode={'low-load' if LOW_LOAD else 'normal'}", flush=True)
    hover_after = measure_hover_overrun(base_params)
    best_params, campaign_rows, cpu_rows, attempt, valid_campaign = run_campaign(base_params)
    best = base_params.patch(best_params) if best_params else base_params
    default_rows, default_cpu = verify("default", base_params, 20, port_offset=20)
    best_rows, best_cpu = verify("best", best, 20, port_offset=22)
    cpu_rows.extend(default_cpu)
    cpu_rows.extend(best_cpu)
    write_summary(best_params, campaign_rows, default_rows, best_rows,
                  cpu_rows, attempt, valid_campaign, hover_after)
    print(f"[{RUN_LABEL}] summary={OUT_DIR / 'summary.md'}", flush=True)
    return 0 if valid_campaign else 2


if __name__ == "__main__":
    raise SystemExit(main())
