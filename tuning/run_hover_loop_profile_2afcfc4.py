"""Profile Windows mock-hover loop timing on the release-contract build.

Runs each condition in a fresh subprocess so AIGP_NOSLEEP is applied before
`aigp.core.scheduler` imports.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "tuning" / "hover-loop-profile-2afcfc4"

CASES = [
    ("default-250hz", 250, None),
    ("nosleep-250hz", 250, "1"),
    ("default-125hz", 125, None),
]


def pct(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    idx = min(len(sorted_values) - 1, max(0, int(round(q * (len(sorted_values) - 1)))))
    return sorted_values[idx]


def summarize(values: list[float]) -> dict[str, float]:
    if not values:
        return {"total_s": 0.0, "mean_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0}
    vals = sorted(values)
    total = sum(values)
    return {
        "total_s": total,
        "mean_ms": 1000.0 * total / len(values),
        "p50_ms": 1000.0 * pct(vals, 0.50),
        "p95_ms": 1000.0 * pct(vals, 0.95),
        "max_ms": 1000.0 * vals[-1],
    }


class LoopProfiler:
    def __init__(self) -> None:
        self.wait_s: list[float] = []
        self.work_s: list[float] = []
        self.entry_ns: list[int] = []
        self.return_ns: list[int] = []
        self._last_return_ns: int | None = None

    def wrap(self, cls) -> None:
        original = cls.wait_next_tick
        profiler = self

        def wrapped(loop_self):
            enter = time.perf_counter_ns()
            if profiler._last_return_ns is not None:
                profiler.work_s.append((enter - profiler._last_return_ns) / 1e9)
            dt = original(loop_self)
            leave = time.perf_counter_ns()
            profiler.entry_ns.append(enter)
            profiler.return_ns.append(leave)
            profiler.wait_s.append((leave - enter) / 1e9)
            profiler._last_return_ns = leave
            return dt

        cls.wait_next_tick = wrapped

    def as_dict(self) -> dict:
        first = self.entry_ns[0] if self.entry_ns else None
        last = self.return_ns[-1] if self.return_ns else None
        elapsed_s = ((last - first) / 1e9) if first is not None and last is not None else 0.0
        ticks = len(self.wait_s)
        wait = summarize(self.wait_s)
        work = summarize(self.work_s)
        measured_s = wait["total_s"] + work["total_s"]
        return {
            "ticks_profiled": ticks,
            "profile_elapsed_s": elapsed_s,
            "achieved_hz": ticks / elapsed_s if elapsed_s > 0 else 0.0,
            "wait": wait,
            "work": work,
            "wait_pct_of_measured": wait["total_s"] / measured_s if measured_s else 0.0,
            "work_pct_of_measured": work["total_s"] / measured_s if measured_s else 0.0,
        }


def run_one(case: str, control_hz: int) -> int:
    import numpy as np

    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT))

    from aigp.core import scheduler

    profiler = LoopProfiler()
    profiler.wrap(scheduler.RateLoop)

    from aigp.app import App, SimConfig
    from aigp.core.params import ParamSet
    from simtools.mock_sim import Gate, MockSim

    case_dir = OUT_DIR / case
    runtime_dir = case_dir / "runtime"
    case_dir.mkdir(parents=True, exist_ok=True)
    if runtime_dir.exists():
        shutil.rmtree(runtime_dir)

    cfg = SimConfig(
        mavlink_ip="127.0.0.1", mavlink_port=24650,
        heartbeat_timeout_s=10.0,
        vision_ip="127.0.0.1", vision_port=25700,
        control_hz=control_hz,
        planner_div=5,
        timesync_hz=10.0,
        log_dir=str(runtime_dir),
        record_vision=False,
    )
    sim = MockSim(
        mav_addr=("127.0.0.1", 24650),
        video_addr=("127.0.0.1", 25700),
        gates=[Gate(pos=np.array([50.0, 0.0, -1.5]), travel_yaw=0.0)],
    )
    app: App | None = None
    try:
        sim.start()
        app = App(cfg)
        app.connect()
        params = ParamSet.load("config/params_default.json").patch({
            "safety.imu_stale_s": 0.25,
            "planner.search.yaw_rate_rps": 0.0,
            "perception.detector.red_sat_min": 256,
        })
        result = app.fly(params, max_duration_s=60.0)
        app.mavlink.sim_reset()
        time.sleep(0.5)
    finally:
        if app is not None:
            app.close()
        sim.stop()

    summary = {
        "case": case,
        "control_hz": control_hz,
        "aigp_nosleep": os.environ.get("AIGP_NOSLEEP", ""),
        "result": {
            "aborted": result["aborted"],
            "abort_reason": result["abort_reason"],
            "gates_passed": result["gates_passed"],
            "env_hits": result["env_hits"],
            "gate_clips": result["gate_clips"],
            "loop_stats": result["loop_stats"],
        },
        "profile": profiler.as_dict(),
    }
    (case_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if runtime_dir.exists():
        shutil.rmtree(runtime_dir)
    print(json.dumps(summary, indent=2))
    return 0


def write_reports(rows: list[dict]) -> None:
    csv_path = OUT_DIR / "hover-loop-profile.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "case", "control_hz", "aigp_nosleep", "ticks", "achieved_hz",
                "overrun_frac", "max_late_us", "abort_reason", "env_hits",
                "gate_clips", "wait_mean_ms", "wait_p95_ms", "wait_total_s",
                "work_mean_ms", "work_p95_ms", "work_total_s",
                "wait_pct", "work_pct",
            ],
        )
        writer.writeheader()
        for row in rows:
            result = row["result"]
            loop = result["loop_stats"]
            profile = row["profile"]
            writer.writerow({
                "case": row["case"],
                "control_hz": row["control_hz"],
                "aigp_nosleep": row["aigp_nosleep"],
                "ticks": loop["ticks"],
                "achieved_hz": profile["achieved_hz"],
                "overrun_frac": loop["overrun_frac"],
                "max_late_us": loop["max_late_us"],
                "abort_reason": result["abort_reason"],
                "env_hits": result["env_hits"],
                "gate_clips": result["gate_clips"],
                "wait_mean_ms": profile["wait"]["mean_ms"],
                "wait_p95_ms": profile["wait"]["p95_ms"],
                "wait_total_s": profile["wait"]["total_s"],
                "work_mean_ms": profile["work"]["mean_ms"],
                "work_p95_ms": profile["work"]["p95_ms"],
                "work_total_s": profile["work"]["total_s"],
                "wait_pct": profile["wait_pct_of_measured"],
                "work_pct": profile["work_pct_of_measured"],
            })

    lines = [
        "# Hover Loop Profile - 2afcfc4",
        "",
        "Mock-only 60s stationary-hover runs: detection disabled and search yaw "
        "set to zero. Per-tick budget uses runtime wrapping around "
        "`RateLoop.wait_next_tick`: wait is time inside the scheduler call; work "
        "is time from scheduler return to the next scheduler entry.",
        "",
        "| Case | Target Hz | Achieved Hz | Ticks | Overrun frac | Max late us | Wait mean / p95 ms | Work mean / p95 ms | Result |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        result = row["result"]
        loop = result["loop_stats"]
        profile = row["profile"]
        lines.append(
            f"| `{row['case']}` | {row['control_hz']} | {profile['achieved_hz']:.2f} | "
            f"{loop['ticks']} | {loop['overrun_frac']:.4f} | {loop['max_late_us']} | "
            f"{profile['wait']['mean_ms']:.3f} / {profile['wait']['p95_ms']:.3f} | "
            f"{profile['work']['mean_ms']:.3f} / {profile['work']['p95_ms']:.3f} | "
            f"{result['abort_reason']}, env_hits={result['env_hits']}, clips={result['gate_clips']} |"
        )
    candidate = next((r for r in rows if r["case"] == "default-125hz"), None)
    lines.extend(["", "## Candidate Note", ""])
    if candidate is not None:
        loop = candidate["result"]["loop_stats"]
        stable = candidate["result"]["abort_reason"] == "max duration" \
            and candidate["result"]["env_hits"] == 0 \
            and candidate["result"]["gate_clips"] == 0
        if loop["overrun_frac"] < 0.05 and stable:
            lines.append("`control_hz=125` is a recommended-config candidate: near-zero overrun and stable hover in this mock probe.")
        else:
            lines.append("`control_hz=125` is not yet a clean recommended-config candidate from this probe.")
    (OUT_DIR / "hover-loop-profile.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_parent() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for case, hz, nosleep in CASES:
        env = os.environ.copy()
        if nosleep is None:
            env.pop("AIGP_NOSLEEP", None)
        else:
            env["AIGP_NOSLEEP"] = nosleep
        out_path = OUT_DIR / f"{case}.txt"
        proc = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--case", case, "--control-hz", str(hz)],
            cwd=str(ROOT),
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=180,
        )
        out_path.write_text(proc.stdout, encoding="utf-8")
        if proc.returncode != 0:
            raise RuntimeError(f"{case} failed rc={proc.returncode}; see {out_path}")
        rows.append(json.loads((OUT_DIR / case / "summary.json").read_text(encoding="utf-8")))
    write_reports(rows)
    (OUT_DIR / "hover-loop-profile.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case")
    ap.add_argument("--control-hz", type=int)
    args = ap.parse_args()
    if args.case:
        if args.control_hz is None:
            raise SystemExit("--control-hz is required with --case")
        return run_one(args.case, args.control_hz)
    return run_parent()


if __name__ == "__main__":
    raise SystemExit(main())
