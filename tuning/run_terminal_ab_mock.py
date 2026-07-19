from __future__ import annotations

import argparse
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
from aigp.core.params import ParamSet  # noqa: E402
from aigp.learning.flight_log import iter_log  # noqa: E402
from simtools.mock_sim import Gate, MockSim  # noqa: E402


LOCK_PATH = Path("C:/Temp/eni_dcim_sim.lock")
RUN_STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
HEAD = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
HEAD_SHORT = HEAD[:7]
OUT_DIR = ROOT / "tuning" / f"terminal-ab-{HEAD_SHORT}-{RUN_STAMP}"
RUNTIME_DIR = ROOT / "tuning" / "runtime-logs" / f"terminal-ab-{HEAD_SHORT}-{RUN_STAMP}"


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


def summarize_term_status(log_dir: str, terminal_enabled: bool) -> tuple[dict, list[str]]:
    counts = {
        "term_rows": 0,
        "engaged_rows": 0,
        "ready_rows": 0,
        "owner_term_rows": 0,
        "applied_rows": 0,
        "engaged_not_ready_rows": 0,
        "applied_while_not_engaged_rows": 0,
        "applied_while_not_ready_rows": 0,
    }
    e_values: list[float] = []
    anomalies: list[str] = []
    flight_dir = Path(log_dir)
    if not flight_dir.exists():
        return counts, ["missing log_dir"]
    for rec in iter_log(flight_dir):
        if rec.get("topic") != "term_status":
            continue
        data = rec.get("data", {})
        counts["term_rows"] += 1
        engaged = bool(data.get("engaged"))
        ready = bool(data.get("ready"))
        applied = data.get("v_bz_applied") is not None
        owner_term = data.get("owner") == "term"
        if engaged:
            counts["engaged_rows"] += 1
        if ready:
            counts["ready_rows"] += 1
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
    if e_values:
        counts["e_z_min"] = min(e_values)
        counts["e_z_max"] = max(e_values)
    else:
        counts["e_z_min"] = ""
        counts["e_z_max"] = ""
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
    return {
        "runs": total,
        "passes": passes,
        "pass_rate": passes / total if total else 0.0,
        "finished": finished,
        "finish_rate": finished / total if total else 0.0,
        "term_anomaly_runs": anomalies,
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
        "| Arm | Patches | Passes | Runs | Pass rate | Finished | Terminal anomaly runs |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for label, patches in ARMS:
        summary = summaries[label]
        patch_text = " ".join(f"--patch {k}={v}" for k, v in patches.items())
        lines.append(
            f"| `{label}` | `{patch_text}` | {summary['passes']} | "
            f"{summary['runs']} | {summary['pass_rate']:.1%} | "
            f"{summary['finished']} | {summary['term_anomaly_runs']} |"
        )
    lines.extend([
        "",
        "## Term Status Notes",
        "",
        "| Arm | Run | Gates | Finished | term rows | engaged | ready | owner=term | applied | anomalies |",
        "|---|---:|---:|---|---:|---:|---:|---:|---:|---|",
    ])
    for row in rows:
        lines.append(
            f"| `{row['arm']}` | {row['idx']} | {row['gates_passed']} | "
            f"{row['finished']} | {row['term_rows']} | {row['engaged_rows']} | "
            f"{row['ready_rows']} | {row['owner_term_rows']} | "
            f"{row['applied_rows']} | {row['term_anomalies']} |"
        )
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=10)
    args = parser.parse_args(argv)
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
