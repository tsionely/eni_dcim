"""P6 — N-R2 extended R1 cyan ribbon on inter-gate segments.

For try15, try39, milestone (if available): after gate-1 pass → death,
measure cyan availability % and longest absent gap (seconds).
A7 height rider: cyan mean row vs attitude-compensated horizon.

Cyan HSV from analysis/2026-07-17-advisory4/run_advisory4.py.

Outputs:
  analysis/2026-07-20-nr2-ribbon-intergate/summary.json
  analysis/2026-07-20-nr2-ribbon-intergate.md
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
MD_ROOT = ROOT / "analysis" / "2026-07-20-nr2-ribbon-intergate.md"
sys.path.insert(0, str(ROOT / "src"))

from aigp.io.udp_tap import STREAM_VISION, read_recording  # noqa: E402
from aigp.io.vision_rx import ChunkAssembler  # noqa: E402

IMG_H = 360
HARD_IMPULSE = 1.5
MIN_CYAN_PX = 20

FLIGHTS = [
    {
        "label": "try15",
        "fid": "20260719T160537-f170ead6",
        "fixture": "20260719T164956-phase6h-first-enable",
        "slice": "20260719T160537-f170ead6_takeoff_to_end.aigprec",
    },
    {
        "label": "try39",
        "fid": "20260719T163649-f170ead6",
        "fixture": "20260719T164956-phase6h-first-enable",
        "slice": "20260719T163649-f170ead6_takeoff_to_end.aigprec",
    },
    {
        "label": "milestone_131137",
        "fid": "20260716T131137-2ca531c3",
        "fixture": "20260716T132549-phase3j-r2training-rerun",
        "slice": "20260716T131137-2ca531c3_r2j_rerun_slice_start.aigprec",
        "full_vision_roots": [
            Path(r"C:\Users\tsion\Projects\eni_dcim_phase1\logs\20260716T131137-2ca531c3\vision.aigprec"),
            Path(r"C:\Users\tsion\Projects\eni_dcim\logs\20260716T131137-2ca531c3\vision.aigprec"),
        ],
        "slice_is_pad": True,
    },
]

FIX_ROOTS = [
    ROOT / "fixtures",
    Path(r"C:\Users\tsion\Projects\eni_dcim\fixtures"),
]
LOG_ROOTS = [
    Path(r"C:\Users\tsion\Projects\eni_dcim\logs"),
    Path(r"C:\Users\tsion\Projects\eni_dcim_phase1\logs"),
]


def cyan_mask(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, (90, 120, 120), (98, 255, 255))


def pitch_from_q(q) -> float | None:
    if not q or len(q) < 4:
        return None
    w, x, y, z = (float(v) for v in q[:4])
    sinp = max(-1.0, min(1.0, 2 * (w * y - z * x)))
    return math.asin(sinp)


def horizon_row(pitch_rad: float, h: int = IMG_H) -> float:
    horiz = 180.0 + 320.0 * math.tan(math.radians(11.0) + pitch_rad)
    return float(np.clip(horiz, 0, h - 1))


def resolve_log(fid: str, fixture: str) -> Path | None:
    for root in FIX_ROOTS:
        p = root / fixture / f"{fid}-flight.jsonl"
        if p.exists():
            return p
    for root in FIX_ROOTS + LOG_ROOTS:
        if not root.exists():
            continue
        hits = list(root.glob(f"**/{fid}-flight.jsonl"))
        if hits:
            return hits[0]
        p = root / fid / "flight.jsonl"
        if p.exists():
            return p
    return None


def resolve_vision(meta: dict) -> tuple[Path | None, str]:
    # Prefer full vision for milestone inter-gate; else committed slice
    for p in meta.get("full_vision_roots") or []:
        if p.exists():
            return p, "full_vision"
    for root in FIX_ROOTS:
        p = root / meta["fixture"] / meta["slice"]
        if p.exists():
            note = "pad_slice" if meta.get("slice_is_pad") else "takeoff_to_end"
            return p, note
    return None, "missing"


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def takeoff_mono(rows: list[dict]) -> int:
    for r in rows:
        if r.get("topic") == "fsm":
            d = r["data"]
            if d.get("dst") == "TAKEOFF" or "GO" in str(d.get("reason", "")).upper():
                return int(r["mono_ns"])
    for r in rows:
        if r.get("topic") == "setpoint" and r["data"].get("phase") == "takeoff":
            return int(r["mono_ns"])
    return int(rows[0]["mono_ns"])


def parse_flight(path: Path) -> dict:
    rows = load_jsonl(path)
    t0 = int(rows[0]["mono_ns"])
    toff = takeoff_mono(rows)
    states, race, colls, frames_meta = [], [], [], []
    for r in rows:
        mono = int(r["mono_ns"])
        t_ff = (mono - toff) / 1e9
        topic = r.get("topic")
        d = r.get("data") or {}
        if topic == "state":
            states.append({
                "t_ff": t_ff, "mono_ns": mono,
                "q": d.get("q_att"),
                "gate_rel": d.get("gate_rel"),
            })
        elif topic == "race":
            race.append({
                "t_ff": t_ff,
                "active_gate_index": d.get("active_gate_index"),
            })
        elif topic == "collision":
            colls.append({
                "t_ff": t_ff,
                "impulse": float(d.get("impulse") or 0.0),
                "threat_level": int(d.get("threat_level") or 0),
            })
        elif topic == "frame":
            frames_meta.append({"t_ff": t_ff, "mono_ns": mono})
    return {
        "states": states, "race": race, "collisions": colls,
        "frames_meta": frames_meta, "t0": t0, "takeoff": toff,
    }


def find_pass_t(log: dict) -> float | None:
    prev = None
    for r in log["race"]:
        idx = r.get("active_gate_index")
        if idx is not None and prev is not None and idx > prev:
            return r["t_ff"]
        if idx is not None:
            prev = idx
    return None


def find_death_t(log: dict, t_pass: float) -> float | None:
    hard = [c for c in log["collisions"]
            if c["t_ff"] >= t_pass - 0.05
            and (c["threat_level"] >= 2 or c["impulse"] >= HARD_IMPULSE)]
    if not hard:
        hard = [c for c in log["collisions"] if c["t_ff"] >= t_pass]
    if not hard:
        return None
    return max(hard, key=lambda c: c["impulse"])["t_ff"]


def nearest_pitch(states, t_ff: float) -> float:
    pitch = 0.0
    best = 1e9
    for s in states:
        dt = abs(s["t_ff"] - t_ff)
        if dt < best and s.get("q"):
            best = dt
            p = pitch_from_q(s["q"])
            if p is not None:
                pitch = p
    return pitch


def decode_window(vision: Path, log: dict, t_pass: float, t_end: float,
                  stride: int = 2, max_frames: int = 400):
    """Yield inter-gate frames with t_ff.

    Strategy:
      1) Prefer mono_ns − takeoff mapping when it overlaps the window.
      2) Else map slice mono span onto [0, t_end] (takeoff→end slices).
      3) For huge full recordings, skip packets outside a mono window
         estimated from log frame topics.
    """
    assembler = ChunkAssembler()
    seen = set()
    raw = []
    toff = log["takeoff"]

    # Optional mono gate from log frames to avoid decoding whole 500MB
    mono_lo = mono_hi = None
    if log["frames_meta"]:
        fm = [f for f in log["frames_meta"] if t_pass <= f["t_ff"] <= t_end]
        if fm:
            mono_lo = fm[0]["mono_ns"] - int(0.5e9)
            mono_hi = fm[-1]["mono_ns"] + int(0.5e9)

    for mono_ns, stream_id, data in read_recording(str(vision)):
        if stream_id != STREAM_VISION:
            continue
        if mono_lo is not None and (mono_ns < mono_lo or mono_ns > mono_hi):
            continue
        done = assembler.feed(data)
        if not done:
            continue
        frame_id, sim_ns, jpeg = done
        if frame_id in seen:
            continue
        seen.add(frame_id)
        raw.append({
            "mono_ns": int(mono_ns), "frame_id": int(frame_id),
            "t_ff_raw": (mono_ns - toff) / 1e9, "jpeg": jpeg,
        })
        if len(raw) >= max_frames * stride * 3 and mono_lo is not None:
            break

    if not raw:
        return [], "no_frames"

    overlap = sum(1 for f in raw if t_pass <= f["t_ff_raw"] <= t_end)
    frames = []
    mode = "mono_takeoff"
    if overlap >= 5:
        for i, fr in enumerate(raw):
            if i % stride:
                continue
            t = fr["t_ff_raw"]
            if t_pass <= t <= t_end:
                img = cv2.imdecode(np.frombuffer(fr["jpeg"], np.uint8),
                                   cv2.IMREAD_COLOR)
                if img is not None:
                    frames.append({"t_ff": t, "img": img,
                                   "frame_id": fr["frame_id"]})
    else:
        mode = "slice_remap"
        m0 = raw[0]["mono_ns"]
        for i, fr in enumerate(raw):
            if i % stride:
                continue
            t = (fr["mono_ns"] - m0) / 1e9
            if t_pass <= t <= t_end:
                img = cv2.imdecode(np.frombuffer(fr["jpeg"], np.uint8),
                                   cv2.IMREAD_COLOR)
                if img is not None:
                    frames.append({"t_ff": t, "img": img,
                                   "frame_id": fr["frame_id"]})
    # Cap
    if len(frames) > max_frames:
        step = max(1, len(frames) // max_frames)
        frames = frames[::step][:max_frames]
    return frames, mode


def ribbon_stats(frames, states) -> dict:
    if not frames:
        return {
            "n_frames": 0, "cyan_pct": None, "longest_absent_gap_s": None,
        }
    flags = []  # (t_ff, cyan_bool, mean_y, horiz, offset)
    for fr in frames:
        m = cyan_mask(fr["img"])
        ys, xs = np.where(m > 0)
        pitch = nearest_pitch(states, fr["t_ff"])
        h = fr["img"].shape[0]
        horiz = horizon_row(pitch, h)
        if len(ys) < MIN_CYAN_PX:
            flags.append((fr["t_ff"], False, None, horiz, None, pitch))
            continue
        mean_y = float(np.mean(ys))
        off = mean_y - horiz
        flags.append((fr["t_ff"], True, mean_y, horiz, off, pitch))

    n = len(flags)
    cyan_n = sum(1 for f in flags if f[1])
    # Longest absent gap: max dt between consecutive cyan=True, or
    # from window edges
    times = sorted(f[0] for f in flags)
    cyan_times = sorted(f[0] for f in flags if f[1])
    longest_gap = 0.0
    if not cyan_times:
        longest_gap = times[-1] - times[0] if len(times) >= 2 else 0.0
    else:
        edges = [times[0]] + cyan_times + [times[-1]]
        for a, b in zip(edges[:-1], edges[1:]):
            longest_gap = max(longest_gap, b - a)

    offsets = [f[4] for f in flags if f[4] is not None]
    mean_rows = [f[2] for f in flags if f[2] is not None]
    horizs = [f[3] for f in flags if f[1]]
    above = sum(1 for f in flags if f[1] and f[2] is not None and f[2] < f[3])

    return {
        "n_frames": n,
        "cyan_frames": cyan_n,
        "cyan_pct": 100.0 * cyan_n / n if n else None,
        "longest_absent_gap_s": float(longest_gap),
        "a7_height": {
            "cyan_mean_row": float(np.mean(mean_rows)) if mean_rows else None,
            "horizon_mean_row": float(np.mean(horizs)) if horizs else None,
            "offset_px_mean": float(np.mean(offsets)) if offsets else None,
            "offset_px_median": float(np.median(offsets)) if offsets else None,
            "offset_px_std": float(np.std(offsets)) if offsets else None,
            "frac_above_horizon": (above / cyan_n) if cyan_n else None,
            "note": "offset = cyan_mean_row - horizon; <0 ⇒ cyan above horizon",
        },
        "t_span_s": float(times[-1] - times[0]) if len(times) >= 2 else 0.0,
    }


def analyze_one(meta: dict) -> dict:
    path = resolve_log(meta["fid"], meta["fixture"])
    if path is None:
        return {"label": meta["label"], "fid": meta["fid"], "error": "log_not_found"}
    log = parse_flight(path)
    t_pass = find_pass_t(log)
    if t_pass is None:
        return {"label": meta["label"], "fid": meta["fid"], "error": "no_pass",
                "path": str(path)}
    t_death = find_death_t(log, t_pass)
    t_end = t_death if t_death is not None else t_pass + 15.0

    vision, vsrc = resolve_vision(meta)
    if vision is None:
        return {
            "label": meta["label"], "fid": meta["fid"],
            "t_pass_ff": t_pass, "t_death_ff": t_death,
            "error": "no_vision", "path": str(path),
        }

    # Skip pad-only slice for milestone if we somehow didn't get full vision
    if meta.get("slice_is_pad") and vsrc == "pad_slice":
        return {
            "label": meta["label"], "fid": meta["fid"],
            "t_pass_ff": t_pass, "t_death_ff": t_death,
            "error": "pad_slice_only_no_intergate_video",
            "vision": str(vision),
        }

    frames, mode = decode_window(vision, log, t_pass, t_end,
                                 stride=3 if vsrc == "full_vision" else 2,
                                 max_frames=350)
    stats = ribbon_stats(frames, log["states"])
    return {
        "label": meta["label"],
        "fid": meta["fid"],
        "path": str(path),
        "vision": str(vision),
        "vision_source": vsrc,
        "decode_mode": mode,
        "t_pass_ff": t_pass,
        "t_death_ff": t_death,
        "intergate_duration_s": float(t_end - t_pass),
        "ribbon": stats,
    }


def write_md(summary: dict) -> str:
    lines = [
        "# N-R2 extended R1 — cyan ribbon inter-gate",
        "",
        "Cyan availability and longest absent gap on post-pass → death "
        "segments; A7 height rider vs attitude-compensated horizon.",
        "",
        "## Per flight",
        "",
        "| flight | t_pass | t_death | n_frames | cyan% | longest gap (s) | "
        "cyan row | horizon | offset px | above horiz frac |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in summary["flights"]:
        if r.get("error"):
            lines.append(
                f"| {r['label']} | {r.get('t_pass_ff', '—')} | "
                f"{r.get('t_death_ff', '—')} | ERR: {r['error']} | | | | | | |"
            )
            continue
        rb = r["ribbon"]
        a7 = rb.get("a7_height") or {}
        death = r["t_death_ff"]
        death_s = "—" if death is None else f"{death:.2f}"
        lines.append(
            f"| {r['label']} | {r['t_pass_ff']:.2f} | {death_s} | "
            f"{rb.get('n_frames')} | "
            f"{_pct(rb.get('cyan_pct'))} | "
            f"{_f(rb.get('longest_absent_gap_s'))} | "
            f"{_f(a7.get('cyan_mean_row'))} | "
            f"{_f(a7.get('horizon_mean_row'))} | "
            f"{_f(a7.get('offset_px_median'))} | "
            f"{_f(a7.get('frac_above_horizon'))} |"
        )
    agg = summary.get("aggregate") or {}
    lines += [
        "",
        "## Aggregate",
        "",
        f"- mean cyan%: `{agg.get('mean_cyan_pct')}`",
        f"- max longest-gap: `{agg.get('max_longest_gap_s')}` s",
        f"- mean offset_px (median per flight): `{agg.get('mean_offset_px')}`",
        "",
        "## Method",
        "",
        "1. Inter-gate window = HUD pass → hard env death.",
        "2. Cyan HSV `(90,120,120)–(98,255,255)` (advisory4).",
        "3. Availability = fraction of decoded frames with ≥20 cyan pixels.",
        "4. Longest absent gap = max time between cyan-present samples "
        "(including window edges).",
        "5. A7: horizon = `180 + 320·tan(11°+pitch)`; "
        "offset = cyan_mean_row − horizon (<0 ⇒ above).",
        "",
        f"Generated by `{OUT.name}/run_nr2_ribbon.py`.",
        "",
    ]
    return "\n".join(lines)


def _f(v) -> str:
    if v is None:
        return "—"
    return f"{v:.2f}"


def _pct(v) -> str:
    if v is None:
        return "—"
    return f"{v:.1f}"


def aggregate(rows: list[dict]) -> dict:
    ok = [r for r in rows if "error" not in r and r.get("ribbon")]
    pcts = [r["ribbon"]["cyan_pct"] for r in ok
            if r["ribbon"].get("cyan_pct") is not None]
    gaps = [r["ribbon"]["longest_absent_gap_s"] for r in ok
            if r["ribbon"].get("longest_absent_gap_s") is not None]
    offs = []
    for r in ok:
        a7 = r["ribbon"].get("a7_height") or {}
        if a7.get("offset_px_median") is not None:
            offs.append(a7["offset_px_median"])
    return {
        "n_ok": len(ok),
        "mean_cyan_pct": float(np.mean(pcts)) if pcts else None,
        "max_longest_gap_s": float(max(gaps)) if gaps else None,
        "mean_offset_px": float(np.mean(offs)) if offs else None,
    }


def main():
    rows = [analyze_one(m) for m in FLIGHTS]
    summary = {
        "ask": "N-R2 extended R1 ribbon inter-gate",
        "flights": rows,
        "aggregate": aggregate(rows),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8")
    md = write_md(summary)
    (OUT / "report.md").write_text(md, encoding="utf-8")
    MD_ROOT.write_text(md, encoding="utf-8")
    print("N-R2 done")
    print("aggregate", summary["aggregate"])
    for r in rows:
        if r.get("error"):
            print("ERR", r["label"], r["error"])
        else:
            rb = r["ribbon"]
            print(r["label"], "cyan%", rb.get("cyan_pct"),
                  "gap", rb.get("longest_absent_gap_s"),
                  "n", rb.get("n_frames"))


if __name__ == "__main__":
    main()
