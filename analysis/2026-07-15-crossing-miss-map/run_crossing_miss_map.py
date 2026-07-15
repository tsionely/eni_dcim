"""Crossing-miss map across phase3c/3d/3e/3f (+3g if present).

From STATE gate_rel (lock-accepted / dead-reckoned), NOT raw detections.
Miss vector at closest approach: lateral = cam tx (body y), vertical = cam ty
(body z, down+). Positive vertical => aircraft HIGH / top-bar.
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from aigp.io.udp_tap import STREAM_VISION, read_recording  # noqa: E402
from aigp.io.vision_rx import ChunkAssembler  # noqa: E402

PHASE_DIRS = [
    ("phase3c", ROOT / "fixtures" / "20260715T052244-phase3c-r2training"),
    ("phase3d", ROOT / "fixtures" / "20260715T135600-phase3d-r2training"),
    ("phase3e", ROOT / "fixtures" / "20260715T190627-phase3e-r2training-slow"),
    ("phase3f", ROOT / "fixtures" / "20260715T200734-phase3f-r2training-slow"),
]
# Optional 3g
for d in sorted((ROOT / "fixtures").glob("*phase3g*")):
    PHASE_DIRS.append(("phase3g", d))

PHASE_COLORS = {
    "phase3c": "#d62728",
    "phase3d": "#ff7f0e",
    "phase3e": "#2ca02c",
    "phase3f": "#1f77b4",
    "phase3g": "#9467bd",
}


@dataclass
class Attempt:
    phase: str
    flight_id: str
    status: str
    n_states_with_gate: int
    closest_dist_m: float | None
    miss_lateral_m: float | None  # + = opening right of aircraft = aircraft LEFT of opening
    miss_vertical_m: float | None  # + = opening below aircraft = aircraft HIGH
    t_closest_s: float | None
    gate_rel_age_s: float | None
    result: str | None
    gates_passed: int | None


def load_result(path: Path) -> dict:
    rp = path.with_name(path.name.replace("-flight.jsonl", "-result.json"))
    if rp.exists():
        return json.loads(rp.read_text(encoding="utf-8"))
    return {}


def reconstruct_miss(phase: str, path: Path) -> Attempt:
    flight_id = path.stem.replace("-flight", "")
    result = load_result(path)
    t0 = None
    best = None  # (dist, t, tx, ty, tz, age)
    n_gate = 0
    with path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec["topic"] != "state":
                continue
            mono = int(rec["mono_ns"])
            if t0 is None:
                t0 = mono
            t = (mono - t0) / 1e9
            d = rec["data"]
            gr = d.get("gate_rel")
            if not gr or gr.get("t") is None:
                continue
            n_gate += 1
            tx, ty, tz = (float(x) for x in gr["t"])
            dist = math.sqrt(tx * tx + ty * ty + tz * tz)
            age = float(d.get("gate_rel_age_s") or 0.0)
            # Closest approach; break ties toward fresher lock
            if best is None or dist < best[0] - 1e-6 or (
                abs(dist - best[0]) < 0.05 and age < best[5]
            ):
                best = (dist, t, tx, ty, tz, age)

    if best is None:
        return Attempt(
            phase=phase,
            flight_id=flight_id,
            status="no_gate_rel",
            n_states_with_gate=0,
            closest_dist_m=None,
            miss_lateral_m=None,
            miss_vertical_m=None,
            t_closest_s=None,
            gate_rel_age_s=None,
            result=result.get("abort_reason") or result.get("status"),
            gates_passed=result.get("gates_passed"),
        )

    dist, t, tx, ty, tz, age = best
    return Attempt(
        phase=phase,
        flight_id=flight_id,
        status="ok",
        n_states_with_gate=n_gate,
        closest_dist_m=dist,
        miss_lateral_m=tx,  # cam x / body y
        miss_vertical_m=ty,  # cam y / body z (down+)
        t_closest_s=t,
        gate_rel_age_s=age,
        result=result.get("abort_reason") or ("finished" if result.get("finished") else None),
        gates_passed=int(result.get("gates_passed") or 0),
    )


def find_pnp_outliers(phase: str, path: Path, dist_lo=2.0, dist_hi=4.5, min_abs_ty=2.0, min_dty=0.8):
    """Find close-range detections with huge |ty| or large consecutive Δty."""
    t0 = None
    dets = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec["topic"] != "detection" or not rec["data"].get("rel_pose"):
                continue
            mono = int(rec["mono_ns"])
            if t0 is None:
                t0 = mono
            t = (mono - t0) / 1e9
            d = rec["data"]
            tx, ty, tz = (float(x) for x in d["rel_pose"]["t"])
            dist = math.sqrt(tx * tx + ty * ty + tz * tz)
            dets.append(
                {
                    "t": t,
                    "dist": dist,
                    "tx": tx,
                    "ty": ty,
                    "tz": tz,
                    "center": d.get("center_px"),
                    "corners": d.get("corners_px"),
                    "conf": d.get("confidence"),
                    "ts_ns": d.get("ts_ns"),
                }
            )

    outliers = []
    for i, det in enumerate(dets):
        if not (dist_lo <= det["dist"] <= dist_hi):
            continue
        reason = None
        dty = None
        if abs(det["ty"]) >= min_abs_ty:
            reason = f"|ty|={abs(det['ty']):.2f}m at {det['dist']:.2f}m"
        if i > 0:
            prev = dets[i - 1]
            dt = det["t"] - prev["t"]
            if 0 < dt < 0.4 and dist_lo <= prev["dist"] <= dist_hi:
                dty = abs(det["ty"] - prev["ty"])
                if dty >= min_dty:
                    reason = (reason + "; " if reason else "") + f"Δty={dty:.2f}m"
        if reason:
            outliers.append({**det, "reason": reason, "dty": dty, "phase": phase, "flight_id": path.stem.replace("-flight", "")})
    # Dedupe near-in-time
    outliers.sort(key=lambda o: abs(o["ty"]), reverse=True)
    kept = []
    for o in outliers:
        if any(abs(o["t"] - k["t"]) < 0.15 and o["flight_id"] == k["flight_id"] for k in kept):
            continue
        kept.append(o)
        if len(kept) >= 12:
            break
    return kept


def extract_frame_near_t(slice_path: Path, target_t_s: float, t0_mono: int | None = None):
    """Decode the assembled frame closest to target relative time in the slice."""
    if not slice_path.exists():
        return None, None
    assembler = ChunkAssembler()
    best = None
    first_mono = None
    for mono_ns, stream_id, data in read_recording(str(slice_path)):
        if stream_id != STREAM_VISION:
            continue
        done = assembler.feed(data)
        if done is None:
            continue
        frame_id, ts_ns, jpeg = done
        if first_mono is None:
            first_mono = mono_ns
        t = (mono_ns - first_mono) / 1e9
        err = abs(t - target_t_s)
        if best is None or err < best[0]:
            best = (err, t, frame_id, jpeg)
        if t > target_t_s + 2.0 and best is not None and best[0] < 0.5:
            break
    if best is None:
        return None, None
    img = cv2.imdecode(np.frombuffer(best[3], dtype=np.uint8), cv2.IMREAD_COLOR)
    return img, {"t_slice": best[1], "err": best[0], "frame_id": best[2]}


def annotate_and_save(img, out_path: Path, title: str, corners=None, center=None):
    if img is None:
        return False
    vis = img.copy()
    if corners is not None:
        pts = np.asarray(corners, dtype=np.int32).reshape(-1, 2)
        cv2.polylines(vis, [pts], True, (0, 255, 255), 2)
    if center is not None:
        cv2.circle(vis, (int(center[0]), int(center[1])), 6, (0, 0, 255), -1)
    cv2.putText(vis, title[:80], (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
    h, w = vis.shape[:2]
    if w > 800:
        scale = 800 / w
        vis = cv2.resize(vis, (800, int(h * scale)), interpolation=cv2.INTER_AREA)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), vis, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    return True


def find_slice_for_flight(fix_dir: Path, flight_id: str) -> Path | None:
    # Common patterns: {id}_r2*_slice_start.aigprec
    cands = list(fix_dir.glob(f"{flight_id}*.aigprec"))
    if cands:
        return cands[0]
    # phase3d F4 reused older id
    cands = list(fix_dir.glob("*slice*.aigprec"))
    return cands[0] if len(cands) == 1 else None


def write_dashboard(attempts: list[Attempt], outliers: list[dict], autopsy_notes: list[str]):
    lines = [
        "# Crossing-miss map (phase3c–3f convergence dashboard)",
        "",
        "Generated by `analysis/2026-07-15-crossing-miss-map/run_crossing_miss_map.py`.",
        "Miss vectors from **STATE `gate_rel`** (lock-accepted / dead-reckoned), "
        "**not** raw detections (which include lock-rejected fixes).",
        "",
        "Convention at closest approach:",
        "- **lateral_m** = cam `t_x` (body y): + = opening RIGHT of aircraft = aircraft LEFT of opening",
        "- **vertical_m** = cam `t_y` (body z, down+): + = opening BELOW aircraft = aircraft HIGH / top-bar",
        "",
        "## Miss table (every R2 attempt)",
        "",
        "| phase | flight | status | closest dist (m) | lateral (m) | vertical (m) | age (s) | gates | result |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for a in attempts:
        if a.status != "ok":
            lines.append(
                f"| {a.phase} | `{a.flight_id}` | {a.status} | — | — | — | — | "
                f"{a.gates_passed if a.gates_passed is not None else '—'} | {a.result or '—'} |"
            )
            continue
        lines.append(
            f"| {a.phase} | `{a.flight_id}` | ok | {a.closest_dist_m:.2f} | "
            f"{a.miss_lateral_m:+.2f} | {a.miss_vertical_m:+.2f} | "
            f"{a.gate_rel_age_s:.2f} | {a.gates_passed} | {a.result or '—'} |"
        )

    # Phase summaries
    lines += ["", "## Phase summary (ok attempts only)", ""]
    lines.append("| phase | n | mean |lat| | mean lat | mean vert | mean |vert| | rms miss |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for phase in ["phase3c", "phase3d", "phase3e", "phase3f", "phase3g"]:
        ok = [a for a in attempts if a.phase == phase and a.status == "ok"]
        if not ok:
            continue
        lat = np.array([a.miss_lateral_m for a in ok], float)
        vert = np.array([a.miss_vertical_m for a in ok], float)
        rms = float(np.sqrt(np.mean(lat**2 + vert**2)))
        lines.append(
            f"| {phase} | {len(ok)} | {np.mean(np.abs(lat)):.2f} | {np.mean(lat):+.2f} | "
            f"{np.mean(vert):+.2f} | {np.mean(np.abs(vert)):.2f} | {rms:.2f} |"
        )

    lines += [
        "",
        "## Scatter",
        "",
        "![miss scatter](plots/miss_scatter.png)",
        "",
        "Origin = gate opening center. Points = STATE closest approach. "
        "Ideal pass sits near (0,0). Right/up in the plot = aircraft LEFT / HIGH.",
        "",
        "## Close-range PnP outlier autopsy (2–4.5 m)",
        "",
        "Raw detections (for autopsy only). Looking for |ty|≥2 m or consecutive Δty≥0.8 m.",
        "",
    ]
    if not outliers:
        lines.append("No outliers matched the thresholds in the scanned flights.")
    else:
        lines.append("| phase | flight | t (s) | dist (m) | ty (m) | Δty | reason | frame |")
        lines.append("|---|---|---:|---:|---:|---:|---|---|")
        for o in outliers:
            frame = o.get("frame_file") or "—"
            dty = f"{o['dty']:.2f}" if o.get("dty") is not None else "—"
            lines.append(
                f"| {o['phase']} | `{o['flight_id']}` | {o['t']:.2f} | {o['dist']:.2f} | "
                f"{o['ty']:+.2f} | {dty} | {o['reason']} | {frame} |"
            )
    lines += ["", "### What the detector saw", ""]
    for note in autopsy_notes:
        lines.append(f"- {note}")
    if not autopsy_notes:
        lines.append("- (no annotated frames extracted)")

    lines += [
        "",
        "## Reading the convergence",
        "",
        "- **phase3c→3d** (mount_pitch=29): vertical should shrink if altitude phantom died.",
        "- **phase3e** (slow): both axes may shrink via phantom starvation.",
        "- **phase3f** (cross-track): lateral |mean| should drop vs 3e.",
        "- **phase3g** (altitude hold): vertical residual is the target if present.",
        "",
        "## Deliverables",
        "",
        "- `report.md`, `summary.json`, `miss_table.csv`",
        "- `plots/miss_scatter.png`",
        "- `pnp_outliers/` annotated frames",
        "",
    ]
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")


def plot_scatter(attempts: list[Attempt]):
    fig, ax = plt.subplots(figsize=(8.5, 7))
    for phase, color in PHASE_COLORS.items():
        pts = [a for a in attempts if a.phase == phase and a.status == "ok"]
        if not pts:
            continue
        xs = [a.miss_lateral_m for a in pts]
        ys = [a.miss_vertical_m for a in pts]  # plot up = aircraft high visually? 
        # User-facing: vertical axis "up on plot = aircraft HIGH" => use -ty so high is up
        # Wait: ty+ = high aircraft. Plot y = -ty would put high DOWN. Use plot y = -ty for image-like?
        # Plot y = miss_vertical_m so +UP = aircraft HIGH.
        ys = [a.miss_vertical_m for a in pts]
        ax.scatter(xs, ys, c=color, s=70, label=f"{phase} (n={len(pts)})", zorder=3)
        for a, x, y in zip(pts, xs, ys):
            ax.annotate(a.flight_id[-6:], (x, y), textcoords="offset points", xytext=(4, 4), fontsize=7, color=color)
    ax.axhline(0, color="k", lw=0.8)
    ax.axvline(0, color="k", lw=0.8)
    # Opening size reference (~1.5m half-width / half-height typical)
    ax.add_patch(plt.Rectangle((-0.75, -0.75), 1.5, 1.5, fill=False, ls="--", color="gray", label="~opening ±0.75m"))
    ax.set_xlabel("lateral miss (m)  [+ = aircraft LEFT of opening]")
    ax.set_ylabel("vertical miss (m)  [+ UP = aircraft HIGH / top-bar]")
    ax.set_title("R2 crossing-miss map (STATE gate_rel closest approach)")
    ax.grid(True, alpha=0.3)
    ax.set_aspect("equal", adjustable="datalim")
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    (OUT / "plots").mkdir(exist_ok=True)
    fig.savefig(OUT / "plots" / "miss_scatter.png", dpi=140)
    plt.close(fig)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "plots").mkdir(exist_ok=True)
    (OUT / "pnp_outliers").mkdir(exist_ok=True)

    attempts: list[Attempt] = []
    all_outliers: list[dict] = []
    autopsy_notes: list[str] = []

    for phase, fix_dir in PHASE_DIRS:
        if not fix_dir.exists():
            print(f"skip missing {fix_dir}", flush=True)
            continue
        flights = sorted(fix_dir.glob("*-flight.jsonl"))
        print(f"{phase}: {len(flights)} flights in {fix_dir.name}", flush=True)
        for fp in flights:
            a = reconstruct_miss(phase, fp)
            attempts.append(a)
            print(
                f"  {a.flight_id}: {a.status} dist={a.closest_dist_m} "
                f"lat={a.miss_lateral_m} vert={a.miss_vertical_m}",
                flush=True,
            )
            # PnP autopsy focus on phase3f (and others that have big outliers)
            outs = find_pnp_outliers(phase, fp)
            for o in outs:
                o["fix_dir"] = str(fix_dir)
            all_outliers.extend(outs)

    # Prefer phase3f outliers for frame extraction; fall back to largest |ty|
    all_outliers.sort(key=lambda o: abs(o["ty"]), reverse=True)
    # Keep diverse top set
    selected = []
    for o in all_outliers:
        if len(selected) >= 8:
            break
        if any(o["flight_id"] == s["flight_id"] and abs(o["t"] - s["t"]) < 0.3 for s in selected):
            continue
        selected.append(o)

    for i, o in enumerate(selected):
        fix_dir = Path(o["fix_dir"])
        slice_path = find_slice_for_flight(fix_dir, o["flight_id"])
        # Slice relative time may not match full log time — try matching by scanning
        # detections near o['t'] is from full log; slices are usually start windows.
        # Heuristic: many slices are from flight start; use o['t'] directly.
        fname = f"{o['phase']}_{o['flight_id'][-6:]}_t{o['t']:.1f}_ty{o['ty']:+.1f}.jpg"
        out_img = OUT / "pnp_outliers" / fname
        img = None
        meta = None
        if slice_path is not None:
            img, meta = extract_frame_near_t(slice_path, o["t"])
            # If slice is start-only and t is late, err will be large — still save best
        title = f"{o['phase']} {o['flight_id'][-8:]} t={o['t']:.1f}s d={o['dist']:.1f} ty={o['ty']:+.2f}"
        ok = annotate_and_save(img, out_img, title, corners=o.get("corners"), center=o.get("center"))
        if ok and meta is not None:
            o["frame_file"] = f"pnp_outliers/{fname}"
            note = (
                f"`{fname}`: {o['reason']}; center={o.get('center')}; "
                f"slice_t≈{meta['t_slice']:.2f}s (err {meta['err']:.2f}s). "
            )
            # Heuristic visual class from geometry
            if o.get("center"):
                cx, cy = o["center"]
                if cy < 100:
                    note += "Center high in frame (sky/ceiling / looking up). "
                if cx < 80 or cx > 560:
                    note += "Center near left/right edge (partial / off-axis). "
            if abs(o["ty"]) > 3.0 and o["dist"] < 5.0:
                note += "Likely wrong-quad / far gate / banner (ty≫plausible at this range). "
            autopsy_notes.append(note)
        else:
            autopsy_notes.append(
                f"{o['phase']} `{o['flight_id']}` t={o['t']:.1f}: {o['reason']} — "
                f"no matching slice frame extracted."
            )

    plot_scatter(attempts)
    write_dashboard(attempts, selected, autopsy_notes)

    # CSV
    import csv

    with (OUT / "miss_table.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "phase",
                "flight_id",
                "status",
                "closest_dist_m",
                "miss_lateral_m",
                "miss_vertical_m",
                "gate_rel_age_s",
                "gates_passed",
                "result",
            ]
        )
        for a in attempts:
            w.writerow(
                [
                    a.phase,
                    a.flight_id,
                    a.status,
                    a.closest_dist_m,
                    a.miss_lateral_m,
                    a.miss_vertical_m,
                    a.gate_rel_age_s,
                    a.gates_passed,
                    a.result,
                ]
            )

    summary = {
        "attempts": [a.__dict__ for a in attempts],
        "pnp_outliers": [
            {k: v for k, v in o.items() if k not in ("corners", "fix_dir")} for o in selected
        ],
        "autopsy_notes": autopsy_notes,
        "phase3g_present": any(p == "phase3g" for p, _ in PHASE_DIRS if _.exists()),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote report + {len(attempts)} attempts, {len(selected)} outliers", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
