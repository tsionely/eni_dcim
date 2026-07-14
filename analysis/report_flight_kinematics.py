"""DATA ANALYST: flight kinematics reports from flight.jsonl logs.

Writes plots + markdown under analysis/ only.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aigp.telemetry.plots import load_topic, plot_flight  # noqa: E402


def discover_flight_logs(roots: list[Path]) -> list[Path]:
    found: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*flight.jsonl"):
            if p.stat().st_size > 10_000:
                found.append(p.resolve())
    # Prefer operator logs/ over fixture copies of same stem+size
    uniq: dict[str, Path] = {}
    for p in found:
        key = f"{p.name}:{p.stat().st_size}"
        prev = uniq.get(key)
        if prev is None:
            uniq[key] = p
            continue
        score = int("logs" in str(p).lower()) + int("fixtures" not in str(p).lower())
        prev_score = int("logs" in str(prev).lower()) + int("fixtures" not in str(prev).lower())
        if score >= prev_score:
            uniq[key] = p
    return sorted(uniq.values(), key=lambda p: p.stat().st_mtime)


def summarize_log(path: Path) -> dict:
    topics = Counter()
    imu_gyro = []
    imu_accel = []
    fsm_trans = []
    detections = 0
    setpoints = Counter()
    race_events = []
    t0 = None
    t_last = None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            topics[rec["topic"]] += 1
            mono = rec.get("mono_ns")
            if mono is not None:
                if t0 is None:
                    t0 = mono
                t_last = mono
            data = rec.get("data") or {}
            if rec["topic"] == "imu":
                g = data.get("gyro")
                a = data.get("accel")
                if g:
                    imu_gyro.append(g)
                if a:
                    imu_accel.append(a)
            elif rec["topic"] == "fsm":
                fsm_trans.append(
                    {
                        "t_s": None if t0 is None else (mono - t0) / 1e9,
                        "src": data.get("src"),
                        "dst": data.get("dst"),
                    }
                )
            elif rec["topic"] == "detection":
                detections += 1
            elif rec["topic"] == "setpoint":
                setpoints[data.get("phase", "?")] += 1
            elif rec["topic"] == "race":
                race_events.append(
                    {
                        "t_s": None if t0 is None else (mono - t0) / 1e9,
                        "started": data.get("race_start_boot_time_ms", -1) >= 0
                        if "race_start_boot_time_ms" in data
                        else data.get("started"),
                        "active_gate": data.get("active_gate_index"),
                        "boot_ms": data.get("sim_boot_time_ms"),
                        "start_ms": data.get("race_start_boot_time_ms"),
                    }
                )

    out: dict = {
        "path": str(path),
        "size_mb": round(path.stat().st_size / 1e6, 2),
        "topics": dict(topics),
        "duration_s": None if t0 is None or t_last is None else (t_last - t0) / 1e9,
        "detections": detections,
        "setpoint_phases": dict(setpoints),
        "fsm_transitions": fsm_trans[:50],
        "fsm_transition_count": len(fsm_trans),
    }
    if imu_gyro:
        g = np.asarray(imu_gyro, dtype=np.float64)
        out["imu_gyro_mean"] = g.mean(axis=0).tolist()
        out["imu_gyro_std"] = g.std(axis=0).tolist()
        out["imu_gyro_max_abs"] = np.abs(g).max(axis=0).tolist()
    if imu_accel:
        a = np.asarray(imu_accel, dtype=np.float64)
        out["imu_accel_mean"] = a.mean(axis=0).tolist()
        out["imu_accel_std"] = a.std(axis=0).tolist()
    # Race GO moment: first time start_ms becomes non-negative / changes
    go_t = None
    prev_start = None
    for ev in race_events:
        sm = ev.get("start_ms")
        if sm is None:
            continue
        if prev_start is None:
            prev_start = sm
        if sm >= 0 and (prev_start is None or prev_start < 0 or sm != prev_start):
            if go_t is None and sm >= 0:
                go_t = ev["t_s"]
        prev_start = sm
    out["approx_race_go_t_s"] = go_t
    out["race_samples"] = len(race_events)
    return out


def plot_imu(path: Path, out_path: Path) -> None:
    imu = load_topic(path, "imu")
    if not imu:
        return
    t0 = imu[0]["mono_ns"]
    ts = [(r["mono_ns"] - t0) / 1e9 for r in imu]
    gyro = np.asarray([r["data"]["gyro"] for r in imu], dtype=np.float64)
    accel = np.asarray([r["data"]["accel"] for r in imu], dtype=np.float64)
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    for i, lab in enumerate(["x", "y", "z"]):
        axes[0].plot(ts, gyro[:, i], label=f"gyro_{lab}", linewidth=0.8)
        axes[1].plot(ts, accel[:, i], label=f"accel_{lab}", linewidth=0.8)
    axes[0].set_ylabel("gyro [rad/s]")
    axes[0].legend(fontsize=8, loc="upper right")
    axes[1].set_ylabel("accel [m/s^2]")
    axes[1].set_xlabel("time [s]")
    axes[1].legend(fontsize=8, loc="upper right")
    fig.suptitle(path.name)
    fig.tight_layout()
    fig.savefig(out_path, dpi=110)
    plt.close(fig)


def write_md(summaries: list[dict], out_md: Path) -> None:
    lines = [
        "# Flight kinematics reports",
        "",
        "DATA ANALYST standing task #3. Source logs from operator checkout / fixtures.",
        "",
        "## Overview",
        "",
        "| log | MB | duration [s] | detections | FSM transitions | approx GO [s] | gyro std |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for s in summaries:
        gstd = "—"
        if "imu_gyro_std" in s:
            g = s["imu_gyro_std"]
            gstd = f"[{g[0]:.4f},{g[1]:.4f},{g[2]:.4f}]"
        go = f"{s['approx_race_go_t_s']:.2f}" if s.get("approx_race_go_t_s") is not None else "—"
        dur = f"{s['duration_s']:.1f}" if s.get("duration_s") is not None else "—"
        lines.append(
            f"| `{Path(s['path']).parent.name}/{Path(s['path']).name}` | {s['size_mb']} | "
            f"{dur} | {s.get('detections', 0)} | {s.get('fsm_transition_count', 0)} | "
            f"{go} | `{gstd}` |"
        )

    lines += ["", "## Per-flight findings", ""]
    for s in summaries:
        name = Path(s["path"]).name
        lines.append(f"### `{name}`")
        lines.append(f"- path: `{s['path']}`")
        lines.append(f"- topics: `{json.dumps(s.get('topics', {}))}`")
        lines.append(f"- setpoint phases: `{json.dumps(s.get('setpoint_phases', {}))}`")
        if "imu_gyro_mean" in s:
            lines.append(
                f"- IMU gyro mean={s['imu_gyro_mean']}, std={s['imu_gyro_std']}, "
                f"max_abs={s['imu_gyro_max_abs']}"
            )
            # Motion heuristic: parked ~0 std; flying has larger rates
            gstd = s["imu_gyro_std"]
            motion = "likely MOVING" if max(gstd) > 0.05 else "likely PARKED/idle (near-zero gyro std)"
            lines.append(f"- motion heuristic: **{motion}**")
        if "imu_accel_mean" in s:
            lines.append(f"- IMU accel mean={s['imu_accel_mean']}, std={s['imu_accel_std']}")
        if s.get("fsm_transitions"):
            lines.append("- FSM timeline (first transitions):")
            for tr in s["fsm_transitions"][:20]:
                lines.append(f"  - t={tr['t_s']:.2f}s: {tr['src']} → {tr['dst']}")
        lines.append("")

    lines += [
        "## Artifacts",
        "",
        "- Standard setpoint/state/detection/FSM plots: `analysis/plots/*-flight.png`",
        "- IMU plots: `analysis/plots/*-imu.png`",
        "- Machine-readable: `analysis/flight_kinematics_metrics.json`",
        "",
    ]
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--logs-root",
        action="append",
        default=[],
        help="Root(s) with flight.jsonl (repeatable)",
    )
    parser.add_argument("--out-dir", default=str(ROOT / "analysis"))
    args = parser.parse_args()

    roots = [Path(p) for p in args.logs_root] if args.logs_root else [
        Path(r"C:\Users\tsion\Projects\eni_dcim_phase1\logs"),
        ROOT / "fixtures",
    ]
    logs = discover_flight_logs(roots)
    print(f"Found {len(logs)} flight logs", flush=True)
    out_dir = Path(args.out_dir)
    plots = out_dir / "plots"
    plots.mkdir(parents=True, exist_ok=True)

    summaries = []
    for path in logs:
        print(f"  -> {path}", flush=True)
        summary = summarize_log(path)
        summaries.append(summary)
        stem = path.parent.name if path.parent.name else path.stem
        plot_flight(path, plots / f"{stem}-flight.png")
        plot_imu(path, plots / f"{stem}-imu.png")

    (out_dir / "flight_kinematics_metrics.json").write_text(
        json.dumps(summaries, indent=2), encoding="utf-8"
    )
    write_md(summaries, out_dir / "20260714-flight-kinematics.md")
    print(f"Wrote {out_dir / '20260714-flight-kinematics.md'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
