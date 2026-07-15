from __future__ import annotations

import csv
import json
import math
import shutil
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
from aigp.learning.campaign import Campaign
from aigp.learning.metrics import score_flight
from aigp.learning.optimizers import CEM
from aigp.learning.results_db import ResultsDB
from simtools.mock_sim import Gate, MockSim

RUN_ID = "2026-07-15-rebaseline-5ec57ee"
OUT_DIR = ROOT / "tuning" / "campaigns" / RUN_ID
RUNTIME_DIR = ROOT / "tuning" / "runtime-logs" / RUN_ID
CAMPAIGN_DIR = OUT_DIR / "campaign-cem"
VERIFY_DIR = OUT_DIR / "verification"
FLAKE_DIR = OUT_DIR / "flake-hunt-single-gate"

MAV_BASE = 28550
VIDEO_BASE = 29600

TUNE_BOUNDS = {
    "planner.approach.aim_up_m": (0.1, 0.6),
    "planner.commit.distance_m": (1.5, 3.5),
    "planner.commit.duration_s": (1.0, 2.0),
    "estimation.vision_vel_blend": (0.1, 0.3),
    "control.att_rate.vz_p": (0.5, 1.2),
    "control.att_rate.vz_i": (0.2, 0.7),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_cfg(label: str, mav_port: int, vision_port: int) -> SimConfig:
    return SimConfig(
        mavlink_ip="127.0.0.1",
        mavlink_port=mav_port,
        heartbeat_timeout_s=20.0,
        vision_ip="127.0.0.1",
        vision_port=vision_port,
        control_hz=250,
        planner_div=5,
        timesync_hz=10.0,
        log_dir=str(RUNTIME_DIR / label),
        save_frames_every_n=0,
        record_vision=False,
    )


@contextmanager
def mock_session(label: str, port_offset: int = 0, gates: list[Gate] | None = None,
                 **mock_kwargs):
    cfg = make_cfg(label, MAV_BASE + port_offset, VIDEO_BASE + port_offset)
    sim = MockSim(
        mav_addr=("127.0.0.1", cfg.mavlink_port),
        video_addr=("127.0.0.1", cfg.vision_port),
        gates=gates,
        **mock_kwargs,
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


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def copy_db(src: Path, dest: Path) -> None:
    if src.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def flight_row(label: str, idx: int, params: ParamSet, result: dict,
               score: float | None = None, error: str = "") -> dict:
    row = {
        "label": label,
        "idx": idx,
        "flight_id": result.get("flight_id", ""),
        "gates_passed": result.get("gates_passed", 0),
        "finished": bool(result.get("finished", False)),
        "aborted": bool(result.get("aborted", False)),
        "abort_reason": result.get("abort_reason", ""),
        "duration_s": result.get("duration_s", ""),
        "lap_time_s": result.get("lap_time_s", ""),
        "gate_clips": result.get("gate_clips", 0),
        "env_hits": result.get("env_hits", 0),
        "score": score if score is not None else "",
        "param_hash": params.hash,
        "log_dir": result.get("log_dir", ""),
        "error": error,
    }
    return row


def summarize_rows(rows: list[dict]) -> dict:
    n = len(rows)
    if n == 0:
        return {"flights": 0}
    gates = [int(r.get("gates_passed") or 0) for r in rows]
    scores = [float(r["score"]) for r in rows if r.get("score") not in ("", None)]
    return {
        "flights": n,
        "total_gates": sum(gates),
        "min_gates": min(gates),
        "max_gates": max(gates),
        "gate_pass_rate": sum(1 for g in gates if g >= 1) / n,
        "finish_rate": sum(1 for r in rows if str(r.get("finished")) == "True") / n,
        "abort_rate": sum(1 for r in rows if str(r.get("aborted")) == "True") / n,
        "best_score": max(scores) if scores else None,
        "avg_score": sum(scores) / len(scores) if scores else None,
    }


def last_fsm_signature(log_dir: str) -> str:
    if not log_dir:
        return "no-log-dir"
    path = Path(log_dir) / "flight.jsonl"
    if not path.exists():
        return "no-flight-jsonl"
    last = "no-fsm"
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                item = json.loads(line)
                if item.get("topic") == "fsm":
                    payload = item.get("data", item)
                    last = json.dumps(payload, sort_keys=True)
    except Exception as exc:  # noqa: BLE001 - diagnostic helper only
        return f"fsm-read-error:{type(exc).__name__}:{exc}"
    return last


def run_campaign(base_params: ParamSet) -> tuple[dict[str, float], list[dict]]:
    CAMPAIGN_DIR.mkdir(parents=True, exist_ok=True)
    db_path = CAMPAIGN_DIR / "results.sqlite"
    db = ResultsDB(db_path)
    logs: list[str] = []
    optimizer = CEM(TUNE_BOUNDS, seed=20260715)
    campaign_id = f"rebaseline-cem-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
    with mock_session("campaign-cem", port_offset=0) as app:
        campaign = Campaign(
            campaign_id,
            base_params,
            optimizer,
            db,
            fly_fn=lambda p: app.reset_and_fly(p, settle_s=1.0, max_duration_s=45.0),
            log_fn=lambda s: (logs.append(s), print(s, flush=True)),
        )
        best = campaign.run(40)
    db.close()
    rows = []
    db_read = ResultsDB(db_path)
    for i, row in enumerate(db_read.flights(campaign_id), start=1):
        rows.append({
            "idx": i,
            "flight_id": row["flight_id"],
            "gates_passed": row["gates_passed"],
            "finished": bool(row["finished"]),
            "aborted": bool(row["aborted"]),
            "abort_reason": row["abort_reason"],
            "gate_clips": row["gate_clips"],
            "env_hits": row["env_hits"],
            "score": row["score"],
            "param_hash": row["param_hash"],
        })
    db_read.close()
    (CAMPAIGN_DIR / "run-output.txt").write_text("\n".join(logs) + "\n", encoding="utf-8")
    write_csv(CAMPAIGN_DIR / "flights.csv", rows)
    best_params = best[0] if best is not None else {}
    (CAMPAIGN_DIR / "best-params.json").write_text(
        json.dumps(best_params, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return best_params, rows


def verify(label: str, params: ParamSet, n: int, port_offset: int) -> list[dict]:
    rows: list[dict] = []
    with mock_session(f"verify-{label}", port_offset=port_offset) as app:
        for idx in range(1, n + 1):
            try:
                result = app.reset_and_fly(params, settle_s=1.0, max_duration_s=45.0)
                score = score_flight(result, params)
                row = flight_row(label, idx, params, result, score)
            except Exception as exc:  # noqa: BLE001 - record flake signature
                row = flight_row(label, idx, params, {}, None,
                                 f"{type(exc).__name__}: {exc}")
            rows.append(row)
            print(f"[verify {label}] {idx}/{n} gates={row['gates_passed']} "
                  f"finished={row['finished']} aborted={row['aborted']} "
                  f"error={row['error']}", flush=True)
    write_csv(VERIFY_DIR / f"{label}.csv", rows)
    return rows


def flake_hunt(base_params: ParamSet) -> list[dict]:
    gates = [Gate(pos=np.array([7.0, 0.0, -1.5]), travel_yaw=0.0,
                  width=1.6, height=1.6)]
    params = base_params.patch({
        "safety.imu_stale_s": 0.25,
        "planner.takeoff.duration_s": 1.6,
        "planner.approach.speed_far_mps": 2.0,
        "safety.flight_timeout_s": 30.0,
    })
    rows: list[dict] = []
    with mock_session(
        "flake-single-gate",
        port_offset=20,
        gates=gates,
        image_size=(320, 180),
        video_hz=20.0,
    ) as app:
        for idx in range(1, 31):
            try:
                result = app.reset_and_fly(params, settle_s=1.0, max_duration_s=30.0)
                score = score_flight(result, params)
                row = flight_row("single_gate", idx, params, result, score)
                row["last_fsm"] = last_fsm_signature(result.get("log_dir", ""))
                failed = int(row["gates_passed"]) < 1 or not bool(row["finished"])
                row["failure_signature"] = "" if not failed else (
                    f"gates={row['gates_passed']} finished={row['finished']} "
                    f"aborted={row['aborted']} abort={row['abort_reason']} "
                    f"last_fsm={row['last_fsm']}"
                )
            except Exception as exc:  # noqa: BLE001 - record flake signature
                row = flight_row("single_gate", idx, params, {}, None,
                                 f"{type(exc).__name__}: {exc}")
                row["last_fsm"] = "exception"
                row["failure_signature"] = row["error"]
            rows.append(row)
            print(f"[flake single_gate] {idx}/30 gates={row['gates_passed']} "
                  f"finished={row['finished']} error={row['error']}", flush=True)
    write_csv(FLAKE_DIR / "single_gate_30.csv", rows)
    return rows


def write_summary(base_params: ParamSet, best_params: dict[str, float],
                  campaign_rows: list[dict], default_rows: list[dict],
                  best_rows: list[dict], flake_rows: list[dict]) -> None:
    campaign_summary = summarize_rows(campaign_rows)
    default_summary = summarize_rows(default_rows)
    best_summary = summarize_rows(best_rows)
    flake_summary = summarize_rows(flake_rows)
    failures = [r for r in flake_rows if r.get("failure_signature")]
    throttle_down = [r for r in failures if "THROTTLE_DOWN" in r.get("failure_signature", "")]
    patch = " ".join(f"--patch {k}={v}" for k, v in best_params.items())

    lines = [
        f"# Re-Baseline Mock Campaign - {RUN_ID}",
        "",
        "Role: QA & MOCK-TUNER.",
        "",
        f"Commit: `{current_commit()}`.",
        "Scope: mock only. No real simulator was launched, reset, clicked, or commanded.",
        "",
        "## Bounds",
        "",
        "```json",
        json.dumps(TUNE_BOUNDS, indent=2, sort_keys=True),
        "```",
        "",
        "## 40-Flight CEM Campaign",
        "",
        summary_bullets(campaign_summary),
        "",
        "Best parameters:",
        "",
        "```json",
        json.dumps(best_params, indent=2, sort_keys=True),
        "```",
        "",
        "Sakana patch starting point:",
        "",
        "```powershell",
        patch,
        "```",
        "",
        "## Verification: Default vs Best",
        "",
        "Default params, 20 flights:",
        summary_bullets(default_summary),
        "",
        "Best params, 20 flights:",
        summary_bullets(best_summary),
        "",
        "## 30x Single-Gate Flake Hunt",
        "",
        summary_bullets(flake_summary),
        "",
        f"Failures: `{len(failures)}/30`.",
        f"Timeout-in-THROTTLE_DOWN signatures: `{len(throttle_down)}`.",
        "",
        "Failure signatures are in `flake-hunt-single-gate/single_gate_30.csv`.",
    ]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT_DIR / "sakana-next-patch.txt").write_text(patch + "\n", encoding="utf-8")
    metadata = {
        "run_id": RUN_ID,
        "commit": current_commit(),
        "bounds": TUNE_BOUNDS,
        "best_params": best_params,
        "campaign_summary": campaign_summary,
        "default_verify_summary": default_summary,
        "best_verify_summary": best_summary,
        "flake_summary": flake_summary,
        "flake_failures": len(failures),
        "timeout_in_throttle_down": len(throttle_down),
        "base_param_hash": base_params.hash,
    }
    (OUT_DIR / "summary.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def summary_bullets(summary: dict) -> str:
    return "\n".join([
        f"- Flights: {summary.get('flights', 0)}",
        f"- Total gates: {summary.get('total_gates', 0)}",
        f"- Gates min/max: {summary.get('min_gates', 0)}/{summary.get('max_gates', 0)}",
        f"- Gate-pass rate: {summary.get('gate_pass_rate', 0.0):.1%}",
        f"- Finish rate: {summary.get('finish_rate', 0.0):.1%}",
        f"- Abort rate: {summary.get('abort_rate', 0.0):.1%}",
        f"- Best score: {summary.get('best_score')}",
        f"- Avg score: {summary.get('avg_score')}",
    ])


def current_commit() -> str:
    import subprocess

    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    base_params = ParamSet.load(ROOT / "config" / "params_default.json")
    print(f"[rebaseline] commit={current_commit()}", flush=True)
    best_params, campaign_rows = run_campaign(base_params)
    best = base_params.patch(best_params)
    default_rows = verify("default", base_params, 20, port_offset=10)
    best_rows = verify("best", best, 20, port_offset=12)
    flake_rows = flake_hunt(base_params)
    write_summary(base_params, best_params, campaign_rows, default_rows, best_rows, flake_rows)
    print(f"[rebaseline] summary={OUT_DIR / 'summary.md'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
