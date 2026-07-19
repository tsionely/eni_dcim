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


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from aigp.app import App, SimConfig  # noqa: E402
from aigp.core.params import ParamSet  # noqa: E402
from aigp.learning.flight_log import iter_log  # noqa: E402
from aigp.learning.metrics import score_flight  # noqa: E402
from aigp.learning.optimizers import CEM  # noqa: E402
from aigp.learning.results_db import ResultsDB  # noqa: E402
from simtools.mock_sim import MockSim  # noqa: E402


LOCK_PATH = Path("C:/Temp/eni_dcim_sim.lock")
RUN_STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
HEAD = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
HEAD_SHORT = HEAD[:7]
OUT_DIR = ROOT / "tuning" / "campaigns" / f"2026-07-19-terminal-{HEAD_SHORT}-{RUN_STAMP}"
RUNTIME_DIR = ROOT / "tuning" / "runtime-logs" / f"terminal-campaign-{HEAD_SHORT}-{RUN_STAMP}"


BASE_PATCH = {
    "safety.imu_stale_s": 0.25,
    "planner.commit.speed_mps": 1.8,
    "planner.terminal.enable": True,
}

BOUNDS = {
    "planner.terminal.margin_m": (0.4, 0.7),
    "planner.terminal.engage_range_m": (2.0, 3.5),
    "planner.align.max_dz_m": (0.3, 0.8),
    "control.att_rate.vel_p": (0.15, 0.6),
    "control.att_rate.vel_i": (0.02, 0.3),
    "control.att_rate.vz_p": (0.4, 1.5),
    "control.att_rate.vz_i": (0.1, 0.8),
    "control.att_rate.tilt_max_rad": (0.2, 0.6),
    "control.att_rate.hover_thrust": (0.35, 0.65),
}


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
        raise RuntimeError("SIM guard blocked terminal campaign: " + "; ".join(details))


def make_cfg() -> SimConfig:
    return SimConfig(
        mavlink_ip="127.0.0.1",
        mavlink_port=38550,
        heartbeat_timeout_s=20.0,
        vision_ip="127.0.0.1",
        vision_port=39600,
        control_hz=250,
        planner_div=5,
        timesync_hz=10.0,
        log_dir=str(RUNTIME_DIR),
        save_frames_every_n=0,
        record_vision=False,
    )


@contextmanager
def mock_session(seed: int) -> Iterator[App]:
    assert_mock_safe()
    cfg = make_cfg()
    sim = MockSim(
        mav_addr=("127.0.0.1", cfg.mavlink_port),
        video_addr=("127.0.0.1", cfg.vision_port),
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


def term_counts(log_dir: str) -> dict:
    counts = {
        "term_rows": 0,
        "engaged_rows": 0,
        "ready_rows": 0,
        "owner_term_rows": 0,
        "applied_rows": 0,
        "applied_while_not_ready_rows": 0,
    }
    path = Path(log_dir)
    if not path.exists():
        return counts
    for rec in iter_log(path):
        if rec.get("topic") != "term_status":
            continue
        data = rec.get("data", {})
        counts["term_rows"] += 1
        ready = bool(data.get("ready"))
        if data.get("engaged"):
            counts["engaged_rows"] += 1
        if ready:
            counts["ready_rows"] += 1
        if data.get("owner") == "term":
            counts["owner_term_rows"] += 1
        applied = data.get("v_bz_applied") is not None
        if applied:
            counts["applied_rows"] += 1
        if applied and not ready:
            counts["applied_while_not_ready_rows"] += 1
    return counts


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


def summarize(rows: list[dict]) -> dict:
    total = len(rows)
    if total == 0:
        return {"flights": 0}
    gates = [int(r.get("gates_passed") or 0) for r in rows]
    scores = [float(r["score"]) for r in rows if r.get("score") not in ("", None)]
    return {
        "flights": total,
        "passes_ge_1": sum(1 for g in gates if g >= 1),
        "pass_rate_ge_1": sum(1 for g in gates if g >= 1) / total,
        "total_gates": sum(gates),
        "max_gates": max(gates),
        "finished": sum(1 for r in rows if r.get("finished") is True),
        "finish_rate": sum(1 for r in rows if r.get("finished") is True) / total,
        "aborted": sum(1 for r in rows if r.get("aborted") is True),
        "best_score": max(scores) if scores else None,
        "avg_score": sum(scores) / len(scores) if scores else None,
        "term_anomaly_rows": sum(1 for r in rows
                                 if int(r.get("applied_while_not_ready_rows") or 0) > 0),
    }


def patch_line(best: dict[str, float]) -> str:
    merged = {**BASE_PATCH, **best}
    return " ".join(f"--patch {key}={json.dumps(value)}" for key, value in merged.items())


def run_campaign(flights: int, seed: int) -> tuple[list[dict], dict[str, float], float]:
    base_params = ParamSet.load(ROOT / "config" / "params_default.json").patch(BASE_PATCH)
    optimizer = CEM(BOUNDS, seed=seed)
    db = ResultsDB(OUT_DIR / "results.sqlite")
    campaign_id = f"terminal-cem-{RUN_STAMP}"
    db.record_campaign(campaign_id, "CEM", list(BOUNDS.keys()),
                       datetime.now(timezone.utc).isoformat())
    rows: list[dict] = []
    best_so_far = float("-inf")
    with mock_session(seed=seed) as app:
        for idx in range(1, flights + 1):
            assert_mock_safe()
            overrides = optimizer.ask()
            params = base_params.patch(overrides)
            started_at = datetime.now(timezone.utc).isoformat()
            try:
                result = app.reset_and_fly(params, settle_s=1.0, max_duration_s=60.0)
                score = score_flight(result, params)
            except Exception as exc:  # noqa: BLE001 - campaign diagnostics
                result = {
                    "aborted": True,
                    "abort_reason": f"{type(exc).__name__}: {exc}",
                    "gates_passed": 0,
                    "duration_s": 60.0,
                    "gate_clips": 0,
                    "env_hits": 0,
                    "loop_stats": {},
                }
                score = -999.0
            optimizer.tell(overrides, score)
            best_so_far = max(best_so_far, score)
            db.record_flight(
                result.get("flight_id", f"{campaign_id}-{idx:03d}"),
                started_at, params, result, score, campaign_id=campaign_id,
            )
            tcounts = term_counts(result.get("log_dir", ""))
            row = {
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
                "overrun_frac": result.get("loop_stats", {}).get("overrun_frac", ""),
                "score": score,
                "best_so_far": best_so_far,
                "param_hash": params.hash,
                "log_dir": result.get("log_dir", ""),
                **tcounts,
                **{f"param.{key}": value for key, value in overrides.items()},
            }
            rows.append(row)
            print(
                f"[terminal-campaign] {idx}/{flights} score={score:.1f} "
                f"best={best_so_far:.1f} gates={row['gates_passed']} "
                f"finished={row['finished']} term_applied={row['applied_rows']}",
                flush=True,
            )
    db.close()
    best = optimizer.best
    return rows, (best[0] if best else {}), (float(best[1]) if best else float("-inf"))


def write_report(rows: list[dict], best_params: dict[str, float], best_score: float,
                 seed: int) -> None:
    summary = summarize(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Terminal CEM Mock Campaign",
        "",
        "Role: QA & MOCK-TUNER.",
        "Scope: mock only. No real simulator was launched, reset, clicked, or commanded.",
        f"Commit: `{HEAD}`.",
        f"Seed: `{seed}`.",
        f"Flights: `{len(rows)}`.",
        "",
        "## Base Patch",
        "",
        "```json",
        json.dumps(BASE_PATCH, indent=2, sort_keys=True),
        "```",
        "",
        "## Bounds",
        "",
        "```json",
        json.dumps(BOUNDS, indent=2, sort_keys=True),
        "```",
        "",
        "## Result",
        "",
        f"- Flights: `{summary['flights']}`",
        f"- Gate >=1 pass rate: `{summary['passes_ge_1']}/{summary['flights']}` (`{summary['pass_rate_ge_1']:.1%}`)",
        f"- Total gates: `{summary['total_gates']}`",
        f"- Max gates: `{summary['max_gates']}`",
        f"- Finished: `{summary['finished']}/{summary['flights']}` (`{summary['finish_rate']:.1%}`)",
        f"- Aborted: `{summary['aborted']}/{summary['flights']}`",
        f"- Best score: `{summary['best_score']}`",
        f"- Average score: `{summary['avg_score']}`",
        f"- Flights with terminal applied while not ready: `{summary['term_anomaly_rows']}`",
        "",
        "## Best Parameters",
        "",
        f"Best score: `{best_score}`.",
        "",
        "```json",
        json.dumps(best_params, indent=2, sort_keys=True),
        "```",
        "",
        "Sakana patch starting point:",
        "",
        "```powershell",
        patch_line(best_params),
        "```",
        "",
        "Artifacts: `all-flights.csv`, `score_progression.csv`, `results.sqlite`, "
        "and per-flight logs under `tuning/runtime-logs/`.",
    ]
    (OUT_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT_DIR / "summary.json").write_text(
        json.dumps({"commit": HEAD, "seed": seed, "base_patch": BASE_PATCH,
                    "bounds": BOUNDS, "summary": summary,
                    "best_score": best_score, "best_params": best_params,
                    "sakana_patch": patch_line(best_params)},
                   indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (OUT_DIR / "sakana-next-patch.txt").write_text(patch_line(best_params) + "\n",
                                                    encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--flights", type=int, default=40)
    parser.add_argument("--seed", type=int, default=20260719)
    args = parser.parse_args(argv)
    assert_mock_safe()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "campaign-config.json").write_text(
        json.dumps({"commit": HEAD, "seed": args.seed, "flights": args.flights,
                    "base_patch": BASE_PATCH, "bounds": BOUNDS},
                   indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    rows, best_params, best_score = run_campaign(args.flights, args.seed)
    write_csv(OUT_DIR / "all-flights.csv", rows)
    write_csv(OUT_DIR / "score_progression.csv", [
        {"idx": row["idx"], "score": row["score"],
         "best_so_far": row["best_so_far"],
         "gates_passed": row["gates_passed"],
         "finished": row["finished"]}
        for row in rows
    ])
    write_report(rows, best_params, best_score, args.seed)
    print(f"[terminal-campaign] report={OUT_DIR / 'summary.md'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
