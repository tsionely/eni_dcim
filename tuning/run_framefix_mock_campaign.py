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
from aigp.learning.metrics import score_flight  # noqa: E402
from aigp.learning.optimizers import CEM  # noqa: E402
from aigp.learning.results_db import ResultsDB  # noqa: E402
from simtools.mock_sim import MockSim  # noqa: E402


LOCK_PATH = Path("C:/Temp/eni_dcim_sim.lock")
RUN_STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
HEAD_SHORT = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
OUT_DIR = ROOT / "tuning" / "campaigns" / f"2026-07-19-framefix-{HEAD_SHORT}-{RUN_STAMP}"
RUNTIME_DIR = ROOT / "tuning" / "runtime-logs" / f"framefix-{HEAD_SHORT}-{RUN_STAMP}"

BOUNDS = {
    "planner.align.max_dz_m": (0.3, 0.8),
    "planner.commit.abort_min_dist_m": (0.8, 1.5),
    "planner.approach.reacquire_max_m": (6.0, 12.0),
    "control.att_rate.vel_p": (0.15, 0.6),
    "control.att_rate.vel_i": (0.02, 0.3),
    "control.att_rate.vz_p": (0.4, 1.5),
    "control.att_rate.vz_i": (0.1, 0.8),
    "control.att_rate.tilt_max_rad": (0.2, 0.6),
    "control.att_rate.hover_thrust": (0.35, 0.65),
}


def git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


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
        raise RuntimeError("SIM guard blocked mock campaign: " + "; ".join(details))


def make_cfg(label: str, port_offset: int) -> SimConfig:
    return SimConfig(
        mavlink_ip="127.0.0.1",
        mavlink_port=33550 + port_offset,
        heartbeat_timeout_s=20.0,
        vision_ip="127.0.0.1",
        vision_port=34600 + port_offset,
        control_hz=250,
        planner_div=5,
        timesync_hz=10.0,
        log_dir=str(RUNTIME_DIR / label),
        save_frames_every_n=0,
        record_vision=False,
    )


@contextmanager
def mock_session(label: str, seed: int, port_offset: int) -> Iterator[App]:
    assert_mock_safe()
    cfg = make_cfg(label, port_offset)
    sim = MockSim(
        mav_addr=("127.0.0.1", cfg.mavlink_port),
        video_addr=("127.0.0.1", cfg.vision_port),
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


def summarize(rows: list[dict]) -> dict:
    total = len(rows)
    if not total:
        return {"flights": 0}
    gates = [int(r.get("gates_passed") or 0) for r in rows]
    scores = [float(r["score"]) for r in rows if r.get("score") not in ("", None)]
    def truthy(value: object) -> bool:
        return value is True or str(value).lower() == "true"

    return {
        "flights": total,
        "passes_ge_1": sum(1 for g in gates if g >= 1),
        "pass_rate_ge_1": sum(1 for g in gates if g >= 1) / total,
        "total_gates": sum(gates),
        "max_gates": max(gates),
        "finished": sum(1 for r in rows if truthy(r.get("finished"))),
        "finish_rate": sum(1 for r in rows if truthy(r.get("finished"))) / total,
        "aborted": sum(1 for r in rows if truthy(r.get("aborted"))),
        "stale_imu": sum(1 for r in rows if truthy(r.get("stale_imu"))),
        "best_score": max(scores) if scores else None,
        "avg_score": sum(scores) / len(scores) if scores else None,
    }


def row_for(seed: int, idx: int, params: ParamSet, overrides: dict[str, float],
            result: dict, score: float, best_so_far: float) -> dict:
    abort_reason = str(result.get("abort_reason", ""))
    return {
        "seed": seed,
        "idx": idx,
        "flight_id": result.get("flight_id", ""),
        "gates_passed": result.get("gates_passed", 0),
        "finished": bool(result.get("finished", False)),
        "aborted": bool(result.get("aborted", False)),
        "abort_reason": abort_reason,
        "stale_imu": "stale channels: imu" in abort_reason,
        "duration_s": result.get("duration_s", ""),
        "lap_time_s": result.get("lap_time_s", ""),
        "gate_clips": result.get("gate_clips", 0),
        "env_hits": result.get("env_hits", 0),
        "overrun_frac": result.get("loop_stats", {}).get("overrun_frac", ""),
        "score": score,
        "best_so_far": best_so_far,
        "param_hash": params.hash,
        "log_dir": result.get("log_dir", ""),
        **{f"param.{k}": v for k, v in overrides.items()},
    }


def run_seed(seed: int, flights: int, base_params: ParamSet, seed_index: int) -> tuple[list[dict], dict, float]:
    seed_dir = OUT_DIR / f"seed-{seed}"
    db = ResultsDB(seed_dir / "results.sqlite")
    optimizer = CEM(BOUNDS, seed=seed)
    campaign_id = f"framefix-cem-seed-{seed}"
    db.record_campaign(campaign_id, "CEM", list(BOUNDS.keys()), datetime.now(timezone.utc).isoformat())
    rows: list[dict] = []
    best_score = float("-inf")
    with mock_session(f"seed-{seed}", seed=seed, port_offset=seed_index * 20) as app:
        for idx in range(1, flights + 1):
            assert_mock_safe()
            overrides = optimizer.ask()
            params = base_params.patch(overrides)
            started_at = datetime.now(timezone.utc).isoformat()
            try:
                result = app.reset_and_fly(params, settle_s=1.0, max_duration_s=45.0)
                score = score_flight(result, params)
            except Exception as exc:  # noqa: BLE001 - campaign diagnostics
                result = {
                    "aborted": True,
                    "abort_reason": f"{type(exc).__name__}: {exc}",
                    "gates_passed": 0,
                    "duration_s": 45.0,
                    "gate_clips": 0,
                    "env_hits": 0,
                    "loop_stats": {},
                }
                score = -999.0
            optimizer.tell(overrides, score)
            best_score = max(best_score, score)
            db.record_flight(
                result.get("flight_id", f"{campaign_id}-{idx:03d}"),
                started_at,
                params,
                result,
                score,
                campaign_id=campaign_id,
            )
            row = row_for(seed, idx, params, overrides, result, score, best_score)
            rows.append(row)
            print(
                f"[campaign seed={seed}] {idx}/{flights} score={score:.1f} "
                f"best={best_score:.1f} gates={row['gates_passed']} "
                f"abort={row['aborted']} reason={str(row['abort_reason'])[:80]}",
                flush=True,
            )
    db.close()
    best = optimizer.best
    best_params = best[0] if best is not None else {}
    best_score_value = float(best[1]) if best is not None else float("-inf")
    write_csv(seed_dir / "flights.csv", rows)
    write_csv(seed_dir / "score_progression.csv", [
        {"idx": r["idx"], "score": r["score"], "best_so_far": r["best_so_far"],
         "gates_passed": r["gates_passed"], "finished": r["finished"]}
        for r in rows
    ])
    (seed_dir / "best-params.json").write_text(
        json.dumps({"seed": seed, "score": best_score_value, "params": best_params},
                   indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return rows, best_params, best_score_value


def patch_line(params: dict[str, float]) -> str:
    return " ".join(f"--patch {key}={value}" for key, value in params.items())


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_completed_seed(seed: int, flights: int) -> tuple[list[dict], dict[str, float], float] | None:
    seed_dir = OUT_DIR / f"seed-{seed}"
    flights_csv = seed_dir / "flights.csv"
    best_json = seed_dir / "best-params.json"
    if not flights_csv.exists() or not best_json.exists():
        return None
    rows = read_csv(flights_csv)
    if len(rows) < flights:
        return None
    best = json.loads(best_json.read_text(encoding="utf-8"))
    return rows, dict(best.get("params", {})), float(best.get("score", float("-inf")))


def write_report(seeds: list[int], flights: int, rows: list[dict], best: dict,
                 best_score: float, seed_summaries: list[dict]) -> None:
    overall = summarize(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Frame-Fix Mock CEM Campaign",
        "",
        "Role: QA & MOCK-TUNER.",
        "Scope: mock only. No real simulator was launched, reset, clicked, or commanded.",
        f"Commit: `{git_sha()}`.",
        f"Seeds: `{', '.join(str(s) for s in seeds)}`.",
        f"Flights per seed: `{flights}`.",
        f"Total flights: `{len(rows)}`.",
        "Mode: normal 250Hz mock, no `--low-load`.",
        "",
        "## Campaign Bounds",
        "",
        "Bounds were supplied by this campaign runner under `tuning/`; no project config file was edited.",
        "",
        "```json",
        json.dumps(BOUNDS, indent=2, sort_keys=True),
        "```",
        "",
        "## Overall Result",
        "",
        f"- Flights: `{overall['flights']}`",
        f"- Gate >=1 pass rate: `{overall['passes_ge_1']}/{overall['flights']}` (`{overall['pass_rate_ge_1']:.1%}`)",
        f"- Total gates: `{overall['total_gates']}`",
        f"- Max gates in one flight: `{overall['max_gates']}`",
        f"- Finished: `{overall['finished']}/{overall['flights']}` (`{overall['finish_rate']:.1%}`)",
        f"- Aborted: `{overall['aborted']}/{overall['flights']}`",
        f"- Stale-IMU aborts: `{overall['stale_imu']}`",
        f"- Best score: `{overall['best_score']}`",
        f"- Average score: `{overall['avg_score']}`",
        "",
        "## Per-Seed Summary",
        "",
        "| Seed | Flights | >=1 gate | Pass rate | Max gates | Finished | Best score |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for summary in seed_summaries:
        lines.append(
            f"| {summary['seed']} | {summary['flights']} | {summary['passes_ge_1']} | "
            f"{summary['pass_rate_ge_1']:.1%} | {summary['max_gates']} | "
            f"{summary['finished']} | {summary['best_score']} |"
        )
    lines.extend([
        "",
        "## Best Parameters",
        "",
        f"Best score: `{best_score}`.",
        "",
        "```json",
        json.dumps(best, indent=2, sort_keys=True),
        "```",
        "",
        "Sakana patch starting point:",
        "",
        "```powershell",
        patch_line(best),
        "```",
        "",
        "## Artifacts",
        "",
        "- `all-flights.csv`: every flight, score, gate count, abort reason, and params.",
        "- `seed-*/score_progression.csv`: per-seed score progression.",
        "- `campaign-config.json`: seed list, flight count, and bounds used.",
    ])
    (OUT_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT_DIR / "sakana-next-patch.txt").write_text(patch_line(best) + "\n", encoding="utf-8")
    (OUT_DIR / "summary.json").write_text(
        json.dumps({
            "commit": git_sha(),
            "seeds": seeds,
            "flights_per_seed": flights,
            "bounds": BOUNDS,
            "overall": overall,
            "per_seed": seed_summaries,
            "best_score": best_score,
            "best_params": best,
            "sakana_patch": patch_line(best),
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    global OUT_DIR, RUNTIME_DIR
    parser = argparse.ArgumentParser()
    parser.add_argument("--flights", type=int, default=40)
    parser.add_argument("--seeds", default="20260719,20260720")
    parser.add_argument("--out-dir", default=None,
                        help="Existing tuning/campaigns directory to resume into")
    parser.add_argument("--resume", action="store_true",
                        help="Skip seeds whose flights.csv already has the requested flight count")
    args = parser.parse_args(argv)
    seeds = [int(item.strip()) for item in args.seeds.split(",") if item.strip()]
    if args.out_dir:
        OUT_DIR = (ROOT / args.out_dir).resolve() if not Path(args.out_dir).is_absolute() else Path(args.out_dir)
        RUNTIME_DIR = ROOT / "tuning" / "runtime-logs" / OUT_DIR.name

    assert_mock_safe()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    campaign_config = {
        "commit": git_sha(),
        "optimizer": "cem",
        "flights_per_seed": args.flights,
        "seeds": seeds,
        "bounds": BOUNDS,
        "base_param_patches": {"safety.imu_stale_s": 0.25},
    }
    (OUT_DIR / "campaign-config.json").write_text(
        json.dumps(campaign_config, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    base_params = ParamSet.load(ROOT / "config" / "params_default.json").patch(
        {"safety.imu_stale_s": 0.25})
    all_rows: list[dict] = []
    seed_summaries: list[dict] = []
    best_params: dict[str, float] = {}
    best_score = float("-inf")
    for seed_index, seed in enumerate(seeds):
        completed = load_completed_seed(seed, args.flights) if args.resume else None
        if completed is not None:
            rows, params, score = completed
            print(f"[campaign seed={seed}] resume: using existing {len(rows)} rows", flush=True)
        else:
            rows, params, score = run_seed(seed, args.flights, base_params, seed_index)
        all_rows.extend(rows)
        summary = summarize(rows)
        summary["seed"] = seed
        seed_summaries.append(summary)
        if score > best_score:
            best_score = score
            best_params = params
    write_csv(OUT_DIR / "all-flights.csv", all_rows)
    write_report(seeds, args.flights, all_rows, best_params, best_score, seed_summaries)
    print(f"[campaign] report={OUT_DIR / 'summary.md'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
