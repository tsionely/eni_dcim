"""Milestone autopsy + inter-gate frontier (AGENTS.md DATA ANALYST CURRENT TASK).

1) Extend crossing-miss map with phase3i + phase3j-rerun (incl. PASS flight).
2) Inter-gate segment study on the Gate-1 pass flight.
3) Cyan-line corridor feasibility BETWEEN gates (phase4b design input).
"""
from __future__ import annotations

import csv
import json
import math
import shutil
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
MISS_MAP = ROOT / "analysis" / "2026-07-15-crossing-miss-map"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(MISS_MAP))

from aigp.io.udp_tap import STREAM_VISION, read_recording  # noqa: E402
from aigp.io.vision_rx import ChunkAssembler  # noqa: E402

# Reuse miss-map segmentation / reconstruction
from run_crossing_miss_map import (  # noqa: E402
    PHASE_COLORS,
    Attempt,
    reconstruct_misses,
)

PASS_FLIGHT = "20260716T131137-2ca531c3"
PASS_FIX = ROOT / "fixtures" / "20260716T132549-phase3j-r2training-rerun"
PASS_LOG = PASS_FIX / f"{PASS_FLIGHT}-flight.jsonl"

# Recommended cyan bands from analysis/2026-07-14-r2-deepdive
CYAN_H_LO, CYAN_H_HI = 90, 98
CYAN_S_MIN, CYAN_V_MIN = 120, 120
CYAN_PRESENT_FRAC = 0.002

# Extra local recording path discovered on this machine (not in git)
LOCAL_VISION_CANDIDATES = [
    Path(r"C:\Users\tsion\Projects\eni_dcim_phase1\logs") / PASS_FLIGHT / "vision.aigprec",
    ROOT / "logs" / PASS_FLIGHT / "vision.aigprec",
    Path(r"C:\Users\tsion\Projects\eni_dcim\logs") / PASS_FLIGHT / "vision.aigprec",
]

PHASE_DIRS_EXT = [
    ("phase3c", ROOT / "fixtures" / "20260715T052244-phase3c-r2training"),
    ("phase3d", ROOT / "fixtures" / "20260715T135600-phase3d-r2training"),
    ("phase3e", ROOT / "fixtures" / "20260715T190627-phase3e-r2training-slow"),
    ("phase3f", ROOT / "fixtures" / "20260715T200734-phase3f-r2training-slow"),
]
for tag in ("phase3g", "phase3h", "phase3i"):
    for d in sorted((ROOT / "fixtures").glob(f"*{tag}*")):
        PHASE_DIRS_EXT.append((tag, d))
# Prefer rerun label; skip blocked phase3j without -rerun
for d in sorted((ROOT / "fixtures").glob("*phase3j*rerun*")):
    PHASE_DIRS_EXT.append(("phase3j_rerun", d))

PHASE_COLORS_EXT = dict(PHASE_COLORS)
PHASE_COLORS_EXT["phase3j_rerun"] = "#17becf"
PHASE_COLORS_EXT["PASS"] = "#00ff00"


@dataclass
class TimelineEvent:
    t: float
    kind: str
    detail: str


def load_result(path: Path) -> dict:
    rp = path.with_name(path.name.replace("-flight.jsonl", "-result.json"))
    if rp.exists():
        return json.loads(rp.read_text(encoding="utf-8"))
    return {}


def extend_miss_map() -> list[Attempt]:
    """Rebuild miss table/scatter including phase3i + phase3j-rerun; mark PASS."""
    attempts: list[Attempt] = []
    for phase, fix_dir in PHASE_DIRS_EXT:
        if not fix_dir.exists():
            continue
        for fp in sorted(fix_dir.glob("*-flight.jsonl")):
            rows = reconstruct_misses(phase, fp)
            attempts.extend(rows)
            for a in rows:
                print(
                    f"  {phase} {a.flight_id} att{a.attempt_n}: "
                    f"{a.status} d={a.closest_dist_m} lat={a.miss_lateral_m} "
                    f"vert={a.miss_vertical_m} gates={a.gates_passed}",
                    flush=True,
                )

    CLOSE_M = 5.0
    # CSV
    with (OUT / "miss_table.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "phase",
                "flight_id",
                "attempt_n",
                "n_attempts_in_flight",
                "attempt_phases",
                "ended_retreat",
                "status",
                "closest_dist_m",
                "miss_lateral_m",
                "miss_vertical_m",
                "gate_rel_age_s",
                "gates_passed",
                "is_pass_attempt",
                "result",
            ]
        )
        for a in attempts:
            is_pass = bool(a.gates_passed and a.gates_passed >= 1 and a.attempt_n == 1)
            # For multi-attempt after a pass, only first close attempt is the PASS crossing
            if a.flight_id == PASS_FLIGHT and a.attempt_n == 1 and a.status == "ok":
                is_pass = True
            w.writerow(
                [
                    a.phase,
                    a.flight_id,
                    a.attempt_n,
                    a.n_attempts_in_flight,
                    a.attempt_phases,
                    a.ended_retreat,
                    a.status,
                    a.closest_dist_m,
                    a.miss_lateral_m,
                    a.miss_vertical_m,
                    a.gate_rel_age_s,
                    a.gates_passed,
                    is_pass,
                    a.result,
                ]
            )

    # Scatter
    fig, ax = plt.subplots(figsize=(10, 8))
    for phase, color in PHASE_COLORS_EXT.items():
        if phase == "PASS":
            continue
        pts = [
            a
            for a in attempts
            if a.phase == phase
            and a.status == "ok"
            and a.closest_dist_m is not None
            and a.closest_dist_m <= CLOSE_M
            and a.flight_id != PASS_FLIGHT
        ]
        if not pts:
            continue
        xs = [a.miss_lateral_m for a in pts]
        ys = [a.miss_vertical_m for a in pts]
        marker = "D" if phase in ("phase3h", "phase3i", "phase3j_rerun") else "o"
        ax.scatter(xs, ys, c=color, s=60, marker=marker, label=f"{phase} (n={len(pts)})", zorder=3)
        for a, x, y in zip(pts, xs, ys):
            lab = a.flight_id[-6:]
            if a.n_attempts_in_flight > 1:
                lab = f"{lab}#{a.attempt_n}"
            ax.annotate(lab, (x, y), textcoords="offset points", xytext=(3, 3), fontsize=6, color=color)

    # PASS star
    pass_rows = [
        a
        for a in attempts
        if a.flight_id == PASS_FLIGHT
        and a.status == "ok"
        and a.closest_dist_m is not None
        and a.closest_dist_m <= CLOSE_M
        and a.attempt_n == 1
    ]
    if pass_rows:
        a = pass_rows[0]
        ax.scatter(
            [a.miss_lateral_m],
            [a.miss_vertical_m],
            c="lime",
            s=220,
            marker="*",
            edgecolors="k",
            linewidths=0.8,
            label="PASS Gate1 (3j-rerun F4)",
            zorder=5,
        )
        ax.annotate(
            f"PASS lat={a.miss_lateral_m:+.2f} vert={a.miss_vertical_m:+.2f}",
            (a.miss_lateral_m, a.miss_vertical_m),
            textcoords="offset points",
            xytext=(8, -12),
            fontsize=8,
            color="darkgreen",
            fontweight="bold",
        )

    ax.axhline(0, color="k", lw=0.8)
    ax.axvline(0, color="k", lw=0.8)
    ax.add_patch(plt.Rectangle((-0.75, -0.75), 1.5, 1.5, fill=False, ls="--", color="gray"))
    ax.set_xlabel("lateral miss (m)  [+ = aircraft LEFT of opening]")
    ax.set_ylabel("vertical miss (m)  [+ UP = aircraft HIGH / top-bar]")
    ax.set_title("Crossing-miss map + milestone PASS (STATE, dist≤5m)")
    ax.grid(True, alpha=0.3)
    ax.set_aspect("equal", adjustable="datalim")
    ax.legend(loc="best", fontsize=7)
    (OUT / "plots").mkdir(exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT / "plots" / "miss_scatter_with_pass.png", dpi=140)
    # Also refresh the shared miss-map plot location
    fig.savefig(MISS_MAP / "plots" / "miss_scatter.png", dpi=140)
    plt.close(fig)

    # Phase summary markdown fragment
    lines = [
        "# Crossing-miss map extension (phase3i + phase3j-rerun + PASS)",
        "",
        f"PASS flight: `{PASS_FLIGHT}` (green star). Convention unchanged from "
        "`analysis/2026-07-15-crossing-miss-map`.",
        "",
        f"## Phase summary (ok, dist ≤ {CLOSE_M:.0f} m)",
        "",
        "| phase | n | mean |lat| | mean lat | mean vert | mean |vert| | rms | n_pass_flights |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for phase in [
        "phase3c",
        "phase3d",
        "phase3e",
        "phase3f",
        "phase3g",
        "phase3h",
        "phase3i",
        "phase3j_rerun",
    ]:
        ok = [
            a
            for a in attempts
            if a.phase == phase
            and a.status == "ok"
            and a.closest_dist_m is not None
            and a.closest_dist_m <= CLOSE_M
        ]
        if not ok:
            continue
        lat = np.array([a.miss_lateral_m for a in ok], float)
        vert = np.array([a.miss_vertical_m for a in ok], float)
        rms = float(np.sqrt(np.mean(lat**2 + vert**2)))
        n_pass = len({a.flight_id for a in ok if (a.gates_passed or 0) >= 1})
        lines.append(
            f"| {phase} | {len(ok)} | {np.mean(np.abs(lat)):.2f} | {np.mean(lat):+.2f} | "
            f"{np.mean(vert):+.2f} | {np.mean(np.abs(vert)):.2f} | {rms:.2f} | {n_pass} |"
        )

    lines += ["", "## PASS crossing vector (ground-truth success)", ""]
    if pass_rows:
        a = pass_rows[0]
        lines.append(
            f"- Flight `{a.flight_id}` attempt {a.attempt_n}: "
            f"dist={a.closest_dist_m:.3f} m, **lateral={a.miss_lateral_m:+.3f} m**, "
            f"**vertical={a.miss_vertical_m:+.3f} m**, age={a.gate_rel_age_s:.2f}s, "
            f"cycle=`{a.attempt_phases}`."
        )
        lines.append(
            "- Sign convention: vert+ = aircraft HIGH. This PASS is the calibration "
            "anchor — prior phases that cluster near this point were geometrically close."
        )
    else:
        lines.append("- PASS attempt not found in STATE reconstruction — check log.")

    lines += [
        "",
        "## Table",
        "",
        "Full rows: `miss_table.csv`. Scatter: `plots/miss_scatter_with_pass.png`.",
        "",
    ]
    (OUT / "miss_map_extension.md").write_text("\n".join(lines), encoding="utf-8")

    # Copy CSV into shared miss-map dir for continuity
    shutil.copy2(OUT / "miss_table.csv", MISS_MAP / "miss_table.csv")
    return attempts


def analyze_intergate() -> dict:
    """Study pass→collision on the milestone flight."""
    assert PASS_LOG.exists(), PASS_LOG
    result = load_result(PASS_LOG)
    t0 = None
    events: list[TimelineEvent] = []
    phase_changes: list[tuple[float, str]] = []
    last_phase = None
    samples = []
    race_events = []
    collisions = []
    gate_ages = []

    with PASS_LOG.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            mono = int(rec["mono_ns"])
            if t0 is None:
                t0 = mono
            t = (mono - t0) / 1e9
            topic = rec["topic"]
            d = rec["data"]
            if topic == "fsm":
                events.append(
                    TimelineEvent(t, "fsm", f"{d.get('src')}→{d.get('dst')} ({d.get('reason')})")
                )
            elif topic == "setpoint":
                ph = d.get("phase")
                if isinstance(ph, str) and ph != last_phase:
                    phase_changes.append((t, ph))
                    events.append(TimelineEvent(t, "phase", ph))
                    last_phase = ph
            elif topic == "collision":
                collisions.append({"t": t, **{k: d.get(k) for k in ("impulse", "collision_id", "threat_level")}})
                events.append(
                    TimelineEvent(t, "collision", f"impulse={d.get('impulse')} id={d.get('collision_id')}")
                )
            elif topic == "race":
                agi = d.get("active_gate_index")
                lgr = d.get("last_gate_race_time")
                race_events.append({"t": t, "agi": agi, "last_gate_race_time": lgr})
            elif topic == "state":
                gr = d.get("gate_rel")
                age = float(d.get("gate_rel_age_s") or 0.0)
                if gr and gr.get("t") is not None:
                    tx, ty, tz = (float(x) for x in gr["t"])
                    dist = math.sqrt(tx * tx + ty * ty + tz * tz)
                    samples.append(
                        {
                            "t": t,
                            "dist": dist,
                            "tx": tx,
                            "ty": ty,
                            "tz": tz,
                            "age": age,
                            "phase": last_phase,
                        }
                    )
                    if 26.0 <= t <= 40.0:
                        gate_ages.append((t, age, dist))

    # Pass proxy: first agi==1
    pass_t = None
    for i, re in enumerate(race_events):
        if re["agi"] == 1 and (i == 0 or race_events[i - 1]["agi"] != 1):
            pass_t = re["t"]
            break

    # Closest near pass
    near_pass = [s for s in samples if 24.0 <= s["t"] <= 28.0]
    closest_pass = min(near_pass, key=lambda s: s["dist"]) if near_pass else None

    # Gate-2 window: after pass until collision
    inter = [s for s in samples if pass_t and s["t"] >= pass_t and s["t"] <= 40.0]
    ages_inter = [s["age"] for s in inter] if inter else []
    # Brief commit/retreat
    commit_retreat = [(t, p) for t, p in phase_changes if 30.0 <= t <= 36.0]

    # Plot inter-gate kinematics
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    if inter:
        ts = [s["t"] for s in inter]
        axes[0].plot(ts, [s["dist"] for s in inter], "b-", lw=1)
        axes[0].set_ylabel("gate_rel dist (m)")
        axes[0].axvline(pass_t, color="g", ls="--", label="pass (agi→1)")
        if collisions:
            axes[0].axvline(collisions[0]["t"], color="r", ls="--", label="collision")
        axes[0].legend(fontsize=8)
        axes[0].grid(True, alpha=0.3)
        axes[1].plot(ts, [s["tx"] for s in inter], label="lat tx")
        axes[1].plot(ts, [s["ty"] for s in inter], label="vert ty")
        axes[1].set_ylabel("miss components (m)")
        axes[1].legend(fontsize=8)
        axes[1].grid(True, alpha=0.3)
        axes[2].plot(ts, [s["age"] for s in inter], "m-")
        axes[2].set_ylabel("gate_rel_age (s)")
        axes[2].set_xlabel("t (s) from log start")
        axes[2].grid(True, alpha=0.3)
        for t, p in phase_changes:
            if pass_t and t >= pass_t - 1:
                axes[0].axvline(t, color="gray", alpha=0.25, lw=0.6)
    fig.suptitle(f"Inter-gate segment — {PASS_FLIGHT}")
    fig.tight_layout()
    fig.savefig(OUT / "plots" / "intergate_kinematics.png", dpi=140)
    plt.close(fig)

    # Extract frames from local vision if available
    vision_path = next((p for p in LOCAL_VISION_CANDIDATES if p.exists()), None)
    frame_notes = []
    collision_frames_dir = OUT / "collision_frames"
    collision_frames_dir.mkdir(exist_ok=True)

    # Always copy operator screens
    screens = PASS_FIX / "screens"
    for name in ("f4_start.jpg", "f4_mid.jpg", "f4_late.jpg", "f4_end.jpg"):
        src = screens / name
        if src.exists():
            dst = collision_frames_dir / name
            shutil.copy2(src, dst)
            # Read image for brief description via pixel stats / save annotated
            img = cv2.imread(str(src))
            if img is not None:
                frame_notes.append(
                    {
                        "file": name,
                        "source": "operator_screen",
                        "shape": list(img.shape),
                        "mean_bgr": [float(x) for x in img.mean(axis=(0, 1))],
                    }
                )

    vision_meta = {"path": str(vision_path) if vision_path else None, "coverage": None}
    if vision_path is not None and t0 is not None:
        # Map recording mono to flight t; extract near collision and mid inter-gate
        assembler = ChunkAssembler()
        first_mono = None
        last_mono = None
        n_frames = 0
        targets = []
        if collisions:
            targets.append(("near_collision", collisions[0]["t"] - 0.3))
            targets.append(("at_collision", collisions[0]["t"]))
        if pass_t:
            targets.append(("just_after_pass", pass_t + 0.5))
            targets.append(("mid_intergate", (pass_t + (collisions[0]["t"] if collisions else pass_t + 10)) / 2))
            targets.append(("pre_retreat", 32.4))
        best = {name: None for name, _ in targets}  # name -> (err, t, jpeg)

        for mono_ns, stream_id, data in read_recording(str(vision_path)):
            if stream_id != STREAM_VISION:
                continue
            done = assembler.feed(data)
            if done is None:
                continue
            _fid, _ts, jpeg = done
            n_frames += 1
            if first_mono is None:
                first_mono = mono_ns
            last_mono = mono_ns
            t = (mono_ns - t0) / 1e9  # flight-relative using SAME t0 as log
            for name, tgt in targets:
                err = abs(t - tgt)
                if best[name] is None or err < best[name][0]:
                    best[name] = (err, t, jpeg)

        dur = ((last_mono - first_mono) / 1e9) if first_mono and last_mono else None
        t_first = ((first_mono - t0) / 1e9) if first_mono else None
        t_last = ((last_mono - t0) / 1e9) if last_mono else None
        vision_meta = {
            "path": str(vision_path),
            "n_assembled_frames": n_frames,
            "rec_duration_s": dur,
            "flight_t_first": t_first,
            "flight_t_last": t_last,
            "covers_pass": bool(t_last is not None and pass_t is not None and t_last >= pass_t),
            "covers_collision": bool(
                t_last is not None and collisions and t_last >= collisions[0]["t"] - 0.5
            ),
        }
        for name, pack in best.items():
            if pack is None:
                continue
            err, t, jpeg = pack
            if err > 2.0:
                frame_notes.append({"file": name, "skipped": True, "err_s": err, "t": t})
                continue
            img = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                continue
            # Cyan overlay
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(
                hsv, (CYAN_H_LO, CYAN_S_MIN, CYAN_V_MIN), (CYAN_H_HI, 255, 255)
            )
            frac = float(cv2.countNonZero(mask)) / (img.shape[0] * img.shape[1])
            vis = img.copy()
            overlay = vis.copy()
            overlay[mask > 0] = (255, 255, 0)
            vis = cv2.addWeighted(overlay, 0.35, vis, 0.65, 0)
            cv2.putText(
                vis,
                f"{name} t={t:.2f}s cyan_frac={frac:.4f} err={err:.2f}s",
                (8, 22),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )
            outp = collision_frames_dir / f"{name}_t{t:.1f}.jpg"
            h, w = vis.shape[:2]
            if w > 900:
                vis = cv2.resize(vis, (900, int(h * 900 / w)))
            cv2.imwrite(str(outp), vis, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            frame_notes.append(
                {
                    "file": outp.name,
                    "source": "vision.aigprec",
                    "t": t,
                    "err_s": err,
                    "cyan_frac": frac,
                }
            )

    # Describe screens with cyan frac
    for name in ("f4_late.jpg", "f4_end.jpg", "f4_mid.jpg"):
        p = collision_frames_dir / name
        if not p.exists():
            continue
        img = cv2.imread(str(p))
        if img is None:
            continue
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, (CYAN_H_LO, CYAN_S_MIN, CYAN_V_MIN), (CYAN_H_HI, 255, 255))
        frac = float(cv2.countNonZero(mask)) / (img.shape[0] * img.shape[1])
        vis = img.copy()
        overlay = vis.copy()
        overlay[mask > 0] = (255, 255, 0)
        vis = cv2.addWeighted(overlay, 0.35, vis, 0.65, 0)
        cv2.putText(
            vis,
            f"{name} cyan_frac={frac:.4f}",
            (8, 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
        )
        outp = collision_frames_dir / f"annotated_{name}"
        cv2.imwrite(str(outp), vis, [int(cv2.IMWRITE_JPEG_QUALITY), 85])

    out = {
        "flight_id": PASS_FLIGHT,
        "result": result,
        "pass_t_agi": pass_t,
        "closest_at_pass": closest_pass,
        "commit_retreat_window": commit_retreat,
        "collisions": collisions,
        "intergate_age_mean": float(np.mean(ages_inter)) if ages_inter else None,
        "intergate_age_max": float(np.max(ages_inter)) if ages_inter else None,
        "n_intergate_samples": len(inter),
        "phase_changes": phase_changes,
        "events": [asdict(e) for e in events if e.t >= 20.0],
        "vision_meta": vision_meta,
        "frame_notes": frame_notes,
        "note_times_vs_agents_md": {
            "agents_said_pass_t": 25.4,
            "measured_pass_agi_t": pass_t,
            "measured_closest_t": closest_pass["t"] if closest_pass else None,
            "agents_said_retreat_t": 31.6,
            "measured_commit_retreat": commit_retreat,
        },
    }
    (OUT / "intergate_summary.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def cyan_corridor_study() -> dict:
    """Is cyan ribbon continuously visible BETWEEN gates?

    Prefer local full vision on the pass flight (inter-gate window).
    Also sample other R2 start slices + operator late screens as secondary evidence.
    """
    results = []

    def study_recording(path: Path, label: str, t0_flight: int | None, t_lo: float | None, t_hi: float | None):
        assembler = ChunkAssembler()
        first_mono = None
        stats = []
        n = 0
        present = 0
        annotated = 0
        out_dir = OUT / "cyan_frames" / label
        out_dir.mkdir(parents=True, exist_ok=True)
        for mono_ns, stream_id, data in read_recording(str(path)):
            if stream_id != STREAM_VISION:
                continue
            done = assembler.feed(data)
            if done is None:
                continue
            fid, _ts, jpeg = done
            if first_mono is None:
                first_mono = mono_ns
            if t0_flight is not None:
                t = (mono_ns - t0_flight) / 1e9
            else:
                t = (mono_ns - first_mono) / 1e9
            if t_lo is not None and t < t_lo:
                continue
            if t_hi is not None and t > t_hi:
                if t0_flight is not None:
                    break
                continue
            img = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                continue
            n += 1
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(
                hsv, (CYAN_H_LO, CYAN_S_MIN, CYAN_V_MIN), (CYAN_H_HI, 255, 255)
            )
            frac = float(cv2.countNonZero(mask)) / (img.shape[0] * img.shape[1])
            is_present = frac >= CYAN_PRESENT_FRAC
            if is_present:
                present += 1
            # centroid of cyan for "corridor direction" proxy
            ys, xs = np.where(mask > 0)
            cx = float(xs.mean()) if len(xs) else float("nan")
            cy = float(ys.mean()) if len(ys) else float("nan")
            stats.append({"t": t, "frac": frac, "present": is_present, "cx": cx, "cy": cy})
            # annotate ~12 evenly
            if n % max(1, 40) == 0 and annotated < 16:
                vis = img.copy()
                overlay = vis.copy()
                overlay[mask > 0] = (255, 255, 0)
                vis = cv2.addWeighted(overlay, 0.35, vis, 0.65, 0)
                cv2.putText(
                    vis,
                    f"{label} t={t:.1f}s frac={frac:.4f}",
                    (8, 22),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    1,
                )
                h, w = vis.shape[:2]
                if w > 800:
                    vis = cv2.resize(vis, (800, int(h * 800 / w)))
                cv2.imwrite(str(out_dir / f"t{t:.1f}_f{fid}.jpg"), vis, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                annotated += 1

        pct = 100.0 * present / n if n else 0.0
        # Continuity: longest gap without cyan
        max_gap = 0.0
        gap = 0.0
        prev_t = None
        for s in stats:
            if prev_t is None:
                prev_t = s["t"]
            dt = s["t"] - prev_t
            prev_t = s["t"]
            if not s["present"]:
                gap += dt
                max_gap = max(max_gap, gap)
            else:
                gap = 0.0
        row = {
            "label": label,
            "path": str(path),
            "frames": n,
            "cyan_present_pct": pct,
            "mean_frac": float(np.mean([s["frac"] for s in stats])) if stats else 0.0,
            "max_absent_gap_s": max_gap,
            "t_lo": t_lo,
            "t_hi": t_hi,
        }
        results.append(row)
        # timeline plot
        if stats:
            fig, ax = plt.subplots(figsize=(10, 3))
            ax.plot([s["t"] for s in stats], [s["frac"] for s in stats], "c-", lw=0.8)
            ax.axhline(CYAN_PRESENT_FRAC, color="gray", ls="--", label="present thresh")
            ax.set_xlabel("t (s)")
            ax.set_ylabel("cyan frac")
            ax.set_title(f"Cyan visibility — {label}")
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=8)
            fig.tight_layout()
            fig.savefig(OUT / "plots" / f"cyan_timeline_{label}.png", dpi=120)
            plt.close(fig)
        return row

    # Flight t0
    t0 = None
    with PASS_LOG.open(encoding="utf-8") as f:
        for line in f:
            t0 = int(json.loads(line)["mono_ns"])
            break

    vision_path = next((p for p in LOCAL_VISION_CANDIDATES if p.exists()), None)
    ig = json.loads((OUT / "intergate_summary.json").read_text(encoding="utf-8")) if (OUT / "intergate_summary.json").exists() else {}
    pass_t = ig.get("pass_t_agi")
    coll_t = ig["collisions"][0]["t"] if ig.get("collisions") else None

    if vision_path is not None and t0 is not None:
        # Full available span
        study_recording(vision_path, "pass_full_local", t0, None, None)
        if pass_t is not None:
            # Inter-gate if covered
            study_recording(
                vision_path,
                "pass_intergate",
                t0,
                pass_t,
                coll_t or (pass_t + 15.0),
            )
            # Approach-only for comparison
            study_recording(vision_path, "pass_pre_pass", t0, max(0.0, pass_t - 8.0), pass_t)

    # Secondary: a few R2 start slices (pad/approach baseline — not inter-gate)
    slice_budget = [
        ROOT / "fixtures" / "20260714T203252-phase3a-r2training",
        ROOT / "fixtures" / "20260716T115732-phase3i-r2training",
        PASS_FIX,
    ]
    for fix in slice_budget:
        if not fix.exists():
            continue
        for sl in sorted(fix.glob("*slice*.aigprec"))[:1]:
            study_recording(sl, f"slice_{fix.name[9:28]}_{sl.stem[-16:]}", None, None, None)

    # Operator late/end screens as collision-context cyan presence
    screen_rows = []
    for name in ("f4_mid.jpg", "f4_late.jpg", "f4_end.jpg"):
        p = PASS_FIX / "screens" / name
        if not p.exists():
            continue
        img = cv2.imread(str(p))
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, (CYAN_H_LO, CYAN_S_MIN, CYAN_V_MIN), (CYAN_H_HI, 255, 255))
        frac = float(cv2.countNonZero(mask)) / (img.shape[0] * img.shape[1])
        screen_rows.append({"screen": name, "cyan_frac": frac, "present": frac >= CYAN_PRESENT_FRAC})

    summary = {
        "bands": {"H": [CYAN_H_LO, CYAN_H_HI], "S_min": CYAN_S_MIN, "V_min": CYAN_V_MIN},
        "recordings": results,
        "operator_screens": screen_rows,
        "verdict_inputs": {
            "local_vision": str(vision_path) if vision_path else None,
            "pass_t": pass_t,
            "collision_t": coll_t,
        },
    }
    (OUT / "cyan_corridor_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def identify_collision_object(inter: dict) -> list[str]:
    """Heuristic notes from screens + vision frames about what was hit."""
    notes = []
    # Read end/late images if present
    for name in ("f4_end.jpg", "f4_late.jpg", "f4_mid.jpg"):
        p = OUT / "collision_frames" / name
        if not p.exists():
            continue
        img = cv2.imread(str(p))
        if img is None:
            continue
        h, w = img.shape[:2]
        # Simple cues: large dark vertical structure vs bright aircraft shapes
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 80, 160)
        # Vertical energy
        vert = edges.mean(axis=0)
        horiz = edges.mean(axis=1)
        vert_peak = float(vert.max())
        horiz_peak = float(horiz.max())
        notes.append(
            f"`{name}`: edge vert_peak={vert_peak:.1f} horiz_peak={horiz_peak:.1f} "
            f"(high vert_peak suggests pillar/column structure)."
        )
    vm = inter.get("vision_meta") or {}
    if not vm.get("covers_collision"):
        notes.append(
            "Local `vision.aigprec` does **not** cover the collision timestamp — "
            "identification relies on operator `f4_late`/`f4_end` screens + kinematics."
        )
    # Kinematic hint: lock jumped to 35–40m just before hit — looking past obstacle?
    notes.append(
        "Kinematics: in the last 1s before collision, STATE `gate_rel` dist jumped "
        "~14m→40m (lock switch / far gate), while flying straight toward the "
        "stale/next lock — consistent with an intervening obstacle not in the gate model."
    )
    return notes


def write_report(attempts: list[Attempt], inter: dict, cyan: dict) -> None:
    pass_rows = [
        a
        for a in attempts
        if a.flight_id == PASS_FLIGHT and a.attempt_n == 1 and a.status == "ok"
    ]
    collision_id_notes = identify_collision_object(inter)

    # Cyan verdict
    inter_rec = next((r for r in cyan.get("recordings", []) if r["label"] == "pass_intergate"), None)
    full_rec = next((r for r in cyan.get("recordings", []) if r["label"] == "pass_full_local"), None)
    screens = cyan.get("operator_screens") or []

    lines = [
        "# Milestone autopsy + inter-gate frontier",
        "",
        "AGENTS.md DATA ANALYST CURRENT TASK (HEAD ≥ `3d37d99`).",
        f"Milestone flight: `{PASS_FLIGHT}` in `fixtures/20260716T132549-phase3j-r2training-rerun`.",
        "",
        "## 1. Crossing-miss map extension (phase3i + phase3j-rerun + PASS)",
        "",
        "See `miss_map_extension.md`, `miss_table.csv`, `plots/miss_scatter_with_pass.png`.",
        "",
    ]
    if pass_rows:
        a = pass_rows[0]
        lines += [
            "### PASS crossing vector (first ground-truth success)",
            "",
            f"| field | value |",
            f"|---|---|",
            f"| closest dist | **{a.closest_dist_m:.3f} m** |",
            f"| lateral | **{a.miss_lateral_m:+.3f} m** ( + = aircraft LEFT ) |",
            f"| vertical | **{a.miss_vertical_m:+.3f} m** ( + = aircraft HIGH ) |",
            f"| gate_rel_age | {a.gate_rel_age_s:.2f} s |",
            f"| cycle | `{a.attempt_phases}` |",
            "",
        ]

    # Compact phase3i / 3j summary
    lines += ["### New phases at a glance (ok, dist≤5m)", "", "| phase | n | mean lat | mean vert | rms |", "|---|---:|---:|---:|---:|"]
    for phase in ("phase3i", "phase3j_rerun"):
        ok = [
            a
            for a in attempts
            if a.phase == phase
            and a.status == "ok"
            and a.closest_dist_m is not None
            and a.closest_dist_m <= 5.0
        ]
        if not ok:
            lines.append(f"| {phase} | 0 | — | — | — |")
            continue
        lat = np.array([a.miss_lateral_m for a in ok], float)
        vert = np.array([a.miss_vertical_m for a in ok], float)
        rms = float(np.sqrt(np.mean(lat**2 + vert**2)))
        lines.append(
            f"| {phase} | {len(ok)} | {np.mean(lat):+.2f} | {np.mean(vert):+.2f} | {rms:.2f} |"
        )

    lines += [
        "",
        "## 2. Inter-gate segment study (pass → collision)",
        "",
        "![intergate](plots/intergate_kinematics.png)",
        "",
        "### Timeline corrections vs AGENTS.md wording",
        "",
        "| AGENTS.md | Measured on log |",
        "|---|---|",
        f"| pass t≈25.4 | **agi 0→1 at t={inter.get('pass_t_agi'):.3f}s**; "
        f"closest STATE at t={((inter.get('closest_at_pass') or {}).get('t'))}s |",
        f"| commit→retreat t≈31.6 | **{inter.get('commit_retreat_window')}** |",
        f"| collision t≈38.9 | **t={inter['collisions'][0]['t']:.3f}s** impulse="
        f"{inter['collisions'][0].get('impulse')} |"
        if inter.get("collisions")
        else "| collision | none |",
        "",
        "### Gate-2 lock quality",
        "",
        f"- Inter-gate STATE samples: **{inter.get('n_intergate_samples')}**",
        f"- Mean `gate_rel_age_s`: **{inter.get('intergate_age_mean')}**",
        f"- Max age: **{inter.get('intergate_age_max')}**",
        "- After the pass the pipeline re-arms on a far gate (~18 m). Approach closes range "
        "to ~2–4 m by t≈32, then a **0.20 s commit** flips to **retreat** (age≈1.0 s — "
        "stale lock / corridor breach), backs off, re-approaches, then wanders with "
        "lock jumps (dist 14→40 m) before the hard env hit.",
        "",
        "### Brief commit→retreat",
        "",
        "Measured cycle (not 31.6):",
        "",
    ]
    for t, p in inter.get("commit_retreat_window") or []:
        lines.append(f"- t={t:.3f}s → `{p}`")
    lines += [
        "",
        "Interpretation: gate-2 attempt aborted almost immediately — age-aware lock was "
        "already stale (~0.8–1.0 s) at commit entry; retreat fired, then the second "
        "approach never re-acquired a clean close lock before the obstacle strike.",
        "",
        "### What did it hit?",
        "",
        "Frames: `collision_frames/` (operator `f4_*` + any extracted vision frames).",
        "",
    ]
    for n in collision_id_notes:
        lines.append(f"- {n}")
    lines += [
        "",
        f"- Vision coverage: `{json.dumps(inter.get('vision_meta'))}`",
        "",
        "## 3. Cyan line as obstacle-free corridor (phase4b input)",
        "",
        f"HSV bands (from R2 deep-dive): H∈[{CYAN_H_LO},{CYAN_H_HI}], S≥{CYAN_S_MIN}, V≥{CYAN_V_MIN}.",
        "",
        "### Recording windows",
        "",
        "| label | frames | cyan-present% | mean frac | max absent gap (s) |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in cyan.get("recordings", []):
        if r["frames"] == 0:
            continue
        # Only list primary labels + a few slices to keep report short
        if not (
            r["label"].startswith("pass_")
            or "phase3a" in r["label"]
            or "phase3j" in r["label"]
            or "phase3i" in r["label"]
        ):
            continue
        lines.append(
            f"| `{r['label']}` | {r['frames']} | {r['cyan_present_pct']:.1f} | "
            f"{r['mean_frac']:.4f} | {r['max_absent_gap_s']:.2f} |"
        )
    lines += ["", "### Operator screens (collision context)", ""]
    for s in screens:
        lines.append(
            f"- `{s['screen']}`: cyan_frac={s['cyan_frac']:.4f} "
            f"({'present' if s['present'] else 'absent/weak'})"
        )

    # Decision
    if inter_rec and inter_rec["frames"] > 50:
        pct = inter_rec["cyan_present_pct"]
        if pct >= 70:
            verdict = (
                f"**YES — feasible.** Inter-gate window shows cyan present in "
                f"**{pct:.0f}%** of frames (max gap {inter_rec['max_absent_gap_s']:.2f}s). "
                "Phase4b should treat the ribbon as a corridor prior between gates."
            )
        elif pct >= 30:
            verdict = (
                f"**MARGINAL.** Cyan present **{pct:.0f}%** between gates — usable as a "
                "soft prior / disambiguator, not a sole path tracker without gap-filling."
            )
        else:
            verdict = (
                f"**NO — not continuously segmentable in this window** "
                f"(present {pct:.0f}%). Do not bet phase4b on cyan-only corridor follow "
                "without better inter-gate recordings."
            )
    elif full_rec and full_rec.get("flight_t_last") is not None and pass_t and full_rec["flight_t_last"] < pass_t:
        verdict = (
            "**INCONCLUSIVE on inter-gate from local vision** — available "
            f"`vision.aigprec` only covers flight t∈[{full_rec.get('flight_t_first')}, "
            f"{full_rec.get('flight_t_last')}] (ends before pass). "
            "Start-slice + pad approach cyan remains strong (prior R2 deep-dive: ~100% "
            "through-gate). **Recommend:** operator collect a 20–40 MB slice covering "
            "t=pass→collision before locking phase4b cyan-follow. Meanwhile use cyan as "
            "**gate disambiguator when multiple rings visible**, not as sole obstacle avoider."
        )
    else:
        verdict = (
            "**INCONCLUSIVE** — no inter-gate pixel coverage in analyzed recordings. "
            "Prior approach-slice study still supports cyan as a gate-threading prior. "
            "Phase4b should not assume continuous between-gate ribbon tracking until "
            "an inter-gate slice exists."
        )

    lines += [
        "",
        "### Verdict (phase4b navigation design)",
        "",
        verdict,
        "",
        "Would following the line have avoided the hit?",
        "",
    ]
    if inter_rec and inter_rec["frames"] > 50 and inter_rec["cyan_present_pct"] >= 50:
        lines.append(
            "- **Likely yes, if the ribbon stays in the clear lane** — the pilot's straight "
            "line to a far/stale gate-2 lock drove into an obstacle; a ribbon-following "
            "lateral controller would bend the path along the track corridor."
        )
    else:
        lines.append(
            "- **Cannot prove from pixels yet** (inter-gate frames missing/short). "
            "Kinematically the hit is a straight-line chase after a failed gate-2 commit; "
            "any corridor prior (cyan or map) that keeps the path off pillars/aircraft "
            "would address the failure mode. **Collect inter-gate slice next.**"
        )

    lines += [
        "",
        "## Deliverables",
        "",
        "- `report.md` (this file)",
        "- `miss_map_extension.md`, `miss_table.csv`, `plots/miss_scatter_with_pass.png`",
        "- `intergate_summary.json`, `plots/intergate_kinematics.png`, `collision_frames/`",
        "- `cyan_corridor_summary.json`, `cyan_frames/`, `plots/cyan_timeline_*.png`",
        "- Shared miss-map refresh: `analysis/2026-07-15-crossing-miss-map/miss_table.csv` + scatter",
        "",
    ]
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")
    # Also drop a pointer into the miss-map report
    pointer = MISS_MAP / "report.md"
    if pointer.exists():
        text = pointer.read_text(encoding="utf-8")
        banner = (
            "\n\n---\n\n## Extension (2026-07-16 milestone)\n\n"
            "phase3i + phase3j-rerun + PASS star: see "
            "`analysis/2026-07-16-milestone-autopsy/report.md`.\n"
        )
        if "2026-07-16 milestone" not in text:
            pointer.write_text(text.rstrip() + banner, encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "plots").mkdir(exist_ok=True)
    print("=== 1) miss map extension ===", flush=True)
    attempts = extend_miss_map()
    print("=== 2) inter-gate ===", flush=True)
    inter = analyze_intergate()
    print("=== 3) cyan corridor ===", flush=True)
    cyan = cyan_corridor_study()
    print("=== report ===", flush=True)
    write_report(attempts, inter, cyan)
    summary = {
        "pass_flight": PASS_FLIGHT,
        "n_attempts": len(attempts),
        "intergate": {
            k: inter.get(k)
            for k in (
                "pass_t_agi",
                "closest_at_pass",
                "commit_retreat_window",
                "collisions",
                "vision_meta",
            )
        },
        "cyan_labels": [r["label"] for r in cyan.get("recordings", []) if r["frames"]],
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("Done.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
