"""Post-flight analysis figures from a flight.jsonl log."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load_topic(log_path: str | Path, topic: str) -> list[dict]:
    records = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec["topic"] == topic:
                records.append(rec)
    return records


def plot_flight(log_path: str | Path, out_path: str | Path) -> None:
    """Standard post-flight figure: setpoints, velocity estimate, detections,
    FSM timeline."""
    log_path = Path(log_path)
    setpoints = load_topic(log_path, "setpoint")
    states = load_topic(log_path, "state")
    detections = load_topic(log_path, "detection")
    fsm = load_topic(log_path, "fsm")

    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    t0 = None

    def t_of(rec):
        nonlocal t0
        if t0 is None:
            t0 = rec["mono_ns"]
        return (rec["mono_ns"] - t0) / 1e9

    if setpoints:
        ts = [t_of(r) for r in setpoints]
        for i, label in enumerate(["vx", "vy", "vz"]):
            axes[0].plot(ts, [r["data"]["v_body"][i] for r in setpoints], label=f"cmd {label}")
    if states:
        ts = [t_of(r) for r in states]
        for i, label in enumerate(["vx", "vy", "vz"]):
            axes[0].plot(ts, [r["data"]["v_world"][i] for r in states],
                         linestyle="--", label=f"est {label}")
    axes[0].set_ylabel("velocity [m/s]")
    axes[0].legend(loc="upper right", fontsize=8)

    if detections:
        ts = [t_of(r) for r in detections]
        dists = [
            (sum(v * v for v in r["data"]["rel_pose"]["t"]) ** 0.5)
            if r["data"].get("rel_pose") else None
            for r in detections
        ]
        axes[1].plot([t for t, d in zip(ts, dists) if d is not None],
                     [d for d in dists if d is not None], ".", markersize=3)
    axes[1].set_ylabel("gate distance [m]")

    for rec in fsm:
        t = t_of(rec)
        axes[2].axvline(t, color="gray", alpha=0.5)
        axes[2].text(t, 0.5, rec["data"]["dst"], rotation=90, fontsize=7)
    axes[2].set_ylabel("FSM")
    axes[2].set_xlabel("time [s]")

    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
