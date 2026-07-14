"""Flight kinematics plots + markdown findings from operator flight.jsonl logs."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aigp.telemetry.plots import load_topic, plot_flight  # noqa: E402

LOGS = Path(r"C:\Users\tsion\Projects\eni_dcim_phase1\logs")
OUT = ROOT / "analysis" / "kinematics"
REPORT = ROOT / "analysis" / "20260714-flight-kinematics.md"


def imu_stats(imu_recs: list[dict]) -> dict:
    if not imu_recs:
        return {}
    accel = np.array([r["data"]["accel"] for r in imu_recs], dtype=np.float64)
    gyro = np.array([r["data"]["gyro"] for r in imu_recs], dtype=np.float64)
    return {
        "accel_mean": accel.mean(axis=0).tolist(),
        "accel_std": accel.std(axis=0).tolist(),
        "accel_norm_mean": float(np.linalg.norm(accel, axis=1).mean()),
        "accel_norm_std": float(np.linalg.norm(accel, axis=1).std()),
        "gyro_mean": gyro.mean(axis=0).tolist(),
        "gyro_std": gyro.std(axis=0).tolist(),
        "gyro_norm_p95": float(np.percentile(np.linalg.norm(gyro, axis=1), 95)),
    }


def plot_imu(imu_recs: list[dict], out_path: Path) -> None:
    if not imu_recs:
        return
    t0 = imu_recs[0]["mono_ns"]
    t = np.array([(r["mono_ns"] - t0) / 1e9 for r in imu_recs])
    accel = np.array([r["data"]["accel"] for r in imu_recs])
    gyro = np.array([r["data"]["gyro"] for r in imu_recs])
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    for i, lab in enumerate(["ax", "ay", "az"]):
        axes[0].plot(t, accel[:, i], label=lab, linewidth=0.8)
    axes[0].set_ylabel("accel [m/s^2]")
    axes[0].legend(fontsize=8)
    for i, lab in enumerate(["gx", "gy", "gz"]):
        axes[1].plot(t, gyro[:, i], label=lab, linewidth=0.8)
    axes[1].set_ylabel("gyro [rad/s]")
    axes[1].set_xlabel("time [s]")
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def analyze_flight(flight_dir: Path) -> dict:
    fl = flight_dir / "flight.jsonl"
    out_dir = OUT / flight_dir.name
    out_dir.mkdir(parents=True, exist_ok=True)
    plot_flight(fl, out_dir / "flight.png")
    imu = load_topic(fl, "imu")
    plot_imu(imu, out_dir / "imu.png")
    fsm = load_topic(fl, "fsm")
    det = load_topic(fl, "detection")
    setpoints = load_topic(fl, "setpoint")
    states = load_topic(fl, "state")
    result = {}
    result_path = flight_dir / "result.json"
    if result_path.exists():
        result = json.loads(result_path.read_text(encoding="utf-8"))

    # setpoint phase timeline
    phases = []
    prev = None
    t0 = None
    for r in setpoints:
        if t0 is None:
            t0 = r["mono_ns"]
        ph = r["data"].get("phase")
        if ph != prev:
            phases.append({"t_s": round((r["mono_ns"] - t0) / 1e9, 3), "phase": ph})
            prev = ph

    dists = []
    for r in det:
        pose = r["data"].get("rel_pose")
        if pose and pose.get("t"):
            tt = pose["t"]
            dists.append(math.sqrt(tt[0] ** 2 + tt[1] ** 2 + tt[2] ** 2))

    return {
        "flight_id": flight_dir.name,
        "result": result,
        "imu": imu_stats(imu),
        "fsm": [{"t_s": (r["mono_ns"] - (fsm[0]["mono_ns"] if fsm else 0)) / 1e9,
                 "src": r["data"].get("src"), "dst": r["data"].get("dst")} for r in fsm],
        "setpoint_phases": phases,
        "n_detections": len(det),
        "n_states": len(states),
        "min_gate_m": min(dists) if dists else None,
        "median_gate_m": float(np.median(dists)) if dists else None,
        "plots": [
            str((out_dir / "flight.png").relative_to(ROOT)).replace("\\", "/"),
            str((out_dir / "imu.png").relative_to(ROOT)).replace("\\", "/"),
        ],
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    reports = []
    for d in sorted(LOGS.iterdir()):
        if not (d / "flight.jsonl").exists():
            continue
        # Skip empty vision early probe with no frames if desired — keep all
        print(f"kinematics {d.name}", flush=True)
        reports.append(analyze_flight(d))

    (OUT / "summary.json").write_text(json.dumps(reports, indent=2), encoding="utf-8")

    lines = [
        "# Flight kinematics report",
        "",
        "Generated from operator `logs/*/flight.jsonl` using `aigp.telemetry.plots`.",
        "Plots live under `analysis/kinematics/<flight_id>/`.",
        "",
    ]
    for r in reports:
        lines.append(f"## `{r['flight_id']}`")
        lines.append("")
        res = r.get("result") or {}
        lines.append(
            f"- result: aborted={res.get('aborted')} reason=`{res.get('abort_reason')}` "
            f"gates={res.get('gates_passed')} dur={res.get('duration_s')}"
        )
        imu = r.get("imu") or {}
        if imu:
            lines.append(
                f"- IMU |a| mean±std: {imu['accel_norm_mean']:.2f}±{imu['accel_norm_std']:.2f} m/s²; "
                f"gyro p95 |ω|={imu['gyro_norm_p95']:.2f} rad/s"
            )
            lines.append(
                f"- accel_std xyz: {[round(x, 3) for x in imu['accel_std']]}; "
                f"gyro_std xyz: {[round(x, 3) for x in imu['gyro_std']]}"
            )
        lines.append(f"- detections in log: {r['n_detections']}; "
                     f"min/median gate dist: {r['min_gate_m']}/{r['median_gate_m']} m")
        lines.append("- FSM:")
        for ev in r["fsm"]:
            lines.append(f"  - t={ev['t_s']:.3f}s {ev['src']} -> {ev['dst']}")
        if r["setpoint_phases"]:
            lines.append("- setpoint phases:")
            for p in r["setpoint_phases"][:30]:
                lines.append(f"  - t={p['t_s']}s `{p['phase']}`")
        lines.append("- plots:")
        for p in r["plots"]:
            lines.append(f"  - `{p}`")
        # Findings
        findings = []
        if imu and imu.get("gyro_norm_p95", 0) > 2.0:
            findings.append("high angular rates (tumble/aggressive motion)")
        if imu and imu.get("accel_norm_std", 0) < 0.05 and imu.get("gyro_norm_p95", 0) < 0.05:
            findings.append("near-frozen IMU (parked/menu-like)")
        if res.get("abort_reason") == "stale channels: frame":
            findings.append("aborted on stale vision channel")
        if (r["n_detections"] or 0) < 500 and (res.get("duration_s") or 0) > 30:
            findings.append("sparse detections during long flight (attitude away from gates)")
        if findings:
            lines.append("- findings: " + "; ".join(findings))
        lines.append("")

    lines += [
        "## Cross-flight takeaways",
        "",
        "- Flights that enter TAKEOFF before the scheduled race start show high |ω| and sparse detections — consistent with early-start DSQ + tumble.",
        "- Parked/race-waiting flights (`20260713T202513`, `20260714T041536`) keep high detection counts and modest IMU motion.",
        "- Closest logged approach so far: phase2b `20260714T072732` at ~3.97 m (still gates_passed=0).",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {REPORT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
