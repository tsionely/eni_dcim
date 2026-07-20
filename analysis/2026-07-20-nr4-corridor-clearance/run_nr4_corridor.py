"""P2 — N-R4 corridor clearance (inter-gate obstacle proxy).

Across post-pass → death segments, estimate lateral distance from the
frozen exit chord (and cyan ribbon, when slice exists) to nearest obstacle.

Obstacle proxy: hard env collisions after gate-1 pass. Lateral offset of
integrated body travel from the exit chord at collision time; also closest
gate_rel lateral (tx) while R in mid-range [3,12] m during inter-gate.

Outputs:
  analysis/2026-07-20-nr4-corridor-clearance/summary.json
  analysis/2026-07-20-nr4-corridor-clearance.md
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
MD_ROOT = ROOT / "analysis" / "2026-07-20-nr4-corridor-clearance.md"
sys.path.insert(0, str(ROOT / "src"))

from aigp.io.udp_tap import STREAM_VISION, read_recording  # noqa: E402
from aigp.io.vision_rx import ChunkAssembler  # noqa: E402

EXIT_WINDOW_S = 0.15
BANK_R = (3.0, 12.0)
HARD_IMPULSE = 1.5
FX_NOM = 320.0
D_CLEAR_PROVISIONAL = 0.9  # design default until data overrides
MARGIN_M = 0.4

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
        "label": "phase6i_200816",
        "fid": "20260719T200816-f170ead6",
        "fixture": "20260719T204430-phase6i-r-rate-ab",
        "slice": "20260719T200816-f170ead6_takeoff_to_end.aigprec",
    },
    {
        "label": "phase6i_201851",
        "fid": "20260719T201851-50f9dcc8",
        "fixture": "20260719T204430-phase6i-r-rate-ab",
        "slice": "20260719T201851-50f9dcc8_takeoff_to_end.aigprec",
    },
    {
        "label": "milestone_131137",
        "fid": "20260716T131137-2ca531c3",
        "fixture": "20260716T132549-phase3j-r2training-rerun",
        "slice": "20260716T131137-2ca531c3_r2j_rerun_slice_start.aigprec",
        "slice_note": "pad-only slice; cyan inter-gate skipped if no post-pass frames",
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


def resolve_log(fid: str, fixture: str) -> Path | None:
    for root in FIX_ROOTS:
        p = root / fixture / f"{fid}-flight.jsonl"
        if p.exists():
            return p
    for root in FIX_ROOTS + LOG_ROOTS:
        hits = list(root.glob(f"**/{fid}-flight.jsonl")) if root.exists() else []
        if hits:
            return hits[0]
        p = root / fid / "flight.jsonl"
        if p.exists():
            return p
    return None


def resolve_slice(fid: str, fixture: str, slice_name: str) -> Path | None:
    for root in FIX_ROOTS:
        p = root / fixture / slice_name
        if p.exists():
            return p
        hits = list(root.glob(f"**/{slice_name}")) if root.exists() else []
        if hits:
            return hits[0]
    return None


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


def bearing_deg(tx: float, tz: float) -> float:
    return float(np.degrees(np.arctan2(tx, max(tz, 1e-6))))


def ang_diff(a: float, b: float) -> float:
    return float((a - b + 180.0) % 360.0 - 180.0)


def parse_flight(path: Path) -> dict:
    rows = load_jsonl(path)
    t0 = int(rows[0]["mono_ns"])
    toff = takeoff_mono(rows)
    dets, states, setpoints, race, colls = [], [], [], [], []
    for r in rows:
        mono = int(r["mono_ns"])
        t_ff = (mono - toff) / 1e9
        t_rel = (mono - t0) / 1e9
        topic = r.get("topic")
        d = r.get("data") or {}
        if topic == "detection":
            rp = d.get("rel_pose") or {}
            tvec = d.get("t_vec") or rp.get("t")
            if tvec is None:
                continue
            tvec = list(map(float, tvec))
            R = float(np.linalg.norm(tvec))
            dets.append({
                "t_ff": t_ff, "t_rel": t_rel, "t_vec": tvec, "R": R,
                "bearing": bearing_deg(tvec[0], tvec[2]),
                "tx": tvec[0], "ty": tvec[1], "tz": tvec[2],
                "center_px": d.get("center_px"),
            })
        elif topic == "state":
            gr = d.get("gate_rel")
            states.append({
                "t_ff": t_ff, "t_rel": t_rel, "gate_rel": gr,
                "q": d.get("q_att"), "age": d.get("gate_rel_age_s"),
                "v_world": list(map(float, d.get("v_world") or [0, 0, 0])),
            })
        elif topic == "setpoint":
            setpoints.append({
                "t_ff": t_ff, "phase": d.get("phase"),
                "v_body": list(map(float, d.get("v_body") or [0, 0, 0])),
            })
        elif topic == "race":
            race.append({
                "t_ff": t_ff,
                "active_gate_index": d.get("active_gate_index"),
                "gates_passed": d.get("gates_passed"),
            })
        elif topic == "collision":
            colls.append({
                "t_ff": t_ff,
                "impulse": float(d.get("impulse") or 0.0),
                "threat_level": int(d.get("threat_level") or 0),
            })
    return {
        "dets": dets, "states": states, "setpoints": setpoints,
        "race": race, "collisions": colls, "t0": t0, "takeoff": toff,
    }


def find_pass_t(log: dict) -> tuple[float | None, str]:
    prev = None
    for r in log["race"]:
        idx = r.get("active_gate_index")
        if idx is not None and prev is not None and idx > prev:
            return r["t_ff"], "hud"
        if idx is not None:
            prev = idx
    prev_tz = None
    for s in log["states"]:
        gr = s.get("gate_rel")
        if gr is None:
            prev_tz = None
            continue
        tz = float(gr["t"][2])
        if prev_tz is not None and prev_tz * tz < 0 and abs(prev_tz) < 2.0:
            return s["t_ff"], "tz_signflip"
        prev_tz = tz
    return None, "none"


def find_death_t(log: dict, t_pass: float) -> tuple[float | None, dict | None]:
    hard = [c for c in log["collisions"]
            if c["t_ff"] >= t_pass - 0.05
            and (c["threat_level"] >= 2 or c["impulse"] >= HARD_IMPULSE)]
    if not hard:
        hard = [c for c in log["collisions"] if c["t_ff"] >= t_pass]
    if not hard:
        return None, None
    death = max(hard, key=lambda c: c["impulse"])
    return death["t_ff"], death


def frozen_exit(log: dict, t_pass: float) -> dict | None:
    travel = []
    for sp in log["setpoints"]:
        if t_pass - EXIT_WINDOW_S <= sp["t_ff"] <= t_pass and sp.get("v_body"):
            vx, vy = sp["v_body"][0], sp["v_body"][1]
            if vx > 0.5:
                travel.append(float(np.degrees(np.arctan2(vy, vx))))
    los = []
    for s in log["states"]:
        if t_pass - EXIT_WINDOW_S <= s["t_ff"] <= t_pass:
            gr = s.get("gate_rel")
            if gr is None:
                continue
            t = gr["t"]
            if float(t[2]) > 0.05:
                los.append(bearing_deg(float(t[0]), float(t[2])))
    if len(travel) >= 3:
        return {
            "bearing_deg": float(np.median(travel)),
            "source": "body_travel_median",
            "n": len(travel),
        }
    if los:
        return {
            "bearing_deg": float(np.median(los)),
            "source": "gate1_los_median",
            "n": len(los),
        }
    if travel:
        return {
            "bearing_deg": float(np.median(travel)),
            "source": "body_travel_sparse",
            "n": len(travel),
        }
    return None


def integrate_travel(setpoints: list[dict], t0: float, t1: float,
                     exit_bearing_deg: float) -> dict:
    """Integrate v_body from t0→t1; project onto exit chord (par) and lateral."""
    sps = [s for s in setpoints if t0 - 0.02 <= s["t_ff"] <= t1 + 0.02]
    sps = sorted(sps, key=lambda s: s["t_ff"])
    if len(sps) < 2:
        return {"s_par_m": None, "s_lat_m": None, "n": len(sps)}
    eb = math.radians(exit_bearing_deg)
    # body frame: x forward, y right. Exit unit in body at freeze:
    ex, ey = math.cos(eb), math.sin(eb)
    # lateral unit (right of exit): rotate +90°
    lx, ly = -ey, ex
    s_par = 0.0
    s_lat = 0.0
    for a, b in zip(sps[:-1], sps[1:]):
        dt = b["t_ff"] - a["t_ff"]
        if dt <= 0 or dt > 0.5:
            continue
        if not (t0 <= b["t_ff"] <= t1 or t0 <= a["t_ff"] <= t1):
            continue
        vx, vy = a["v_body"][0], a["v_body"][1]
        s_par += (vx * ex + vy * ey) * dt
        s_lat += (vx * lx + vy * ly) * dt
    return {"s_par_m": float(s_par), "s_lat_m": float(s_lat), "n": len(sps)}


def midrange_closest_tx(states: list[dict], t_pass: float,
                        t_end: float) -> dict | None:
    best = None
    for s in states:
        if not (t_pass <= s["t_ff"] <= t_end):
            continue
        gr = s.get("gate_rel")
        if gr is None:
            continue
        t = list(map(float, gr["t"]))
        R = float(np.linalg.norm(t))
        if not (BANK_R[0] <= R <= BANK_R[1]):
            continue
        tx = abs(t[0])
        if best is None or tx < best["abs_tx"]:
            best = {
                "t_ff": s["t_ff"], "R": R, "tx": t[0], "abs_tx": tx,
                "ty": t[1], "tz": t[2],
            }
    return best


def decode_intergate_frames(vision: Path, log: dict, t_pass: float,
                            t_end: float, stride: int = 3):
    """Decode slice frames overlapping inter-gate; map to t_ff via mono."""
    assembler = ChunkAssembler()
    seen = set()
    frames = []
    toff = log["takeoff"]
    for mono_ns, stream_id, data in read_recording(str(vision)):
        if stream_id != STREAM_VISION:
            continue
        done = assembler.feed(data)
        if not done:
            continue
        frame_id, sim_ns, jpeg = done
        if frame_id in seen:
            continue
        seen.add(frame_id)
        t_ff = (mono_ns - toff) / 1e9
        # slice mono may not match log; also try relative within recording later
        frames.append({
            "mono_ns": int(mono_ns), "frame_id": int(frame_id),
            "t_ff_raw": t_ff, "jpeg": jpeg,
        })
    if not frames:
        return []
    # Align: if raw t_ff never overlaps pass window, treat first frame as
    # near takeoff (slice starts at takeoff) using ordered index + log frames.
    raw_times = [f["t_ff_raw"] for f in frames]
    overlap = sum(1 for t in raw_times if t_pass - 1.0 <= t <= t_end + 1.0)
    out = []
    if overlap >= 5:
        for i, fr in enumerate(frames):
            if i % stride:
                continue
            t = fr["t_ff_raw"]
            if t_pass <= t <= t_end:
                img = cv2.imdecode(np.frombuffer(fr["jpeg"], np.uint8),
                                   cv2.IMREAD_COLOR)
                if img is not None:
                    out.append({"t_ff": t, "img": img,
                                "frame_id": fr["frame_id"]})
    else:
        # Assume slice spans takeoff→end with uniform-ish timing from log
        # Use mono relative to first slice packet mapped onto [0, t_end].
        m0 = frames[0]["mono_ns"]
        m1 = frames[-1]["mono_ns"]
        span = max((m1 - m0) / 1e9, 1e-3)
        for i, fr in enumerate(frames):
            if i % stride:
                continue
            t_ff = (fr["mono_ns"] - m0) / 1e9  # ≈ time since takeoff if slice starts there
            if t_pass <= t_ff <= t_end:
                img = cv2.imdecode(np.frombuffer(fr["jpeg"], np.uint8),
                                   cv2.IMREAD_COLOR)
                if img is not None:
                    out.append({"t_ff": t_ff, "img": img,
                                "frame_id": fr["frame_id"]})
    return out


def cyan_lateral_stats(frames, dets) -> dict:
    """Ribbon lateral offset from image center → rough meters via R_est."""
    if not frames:
        return {"n_frames": 0, "cyan_pct": None}
    offsets_px = []
    offsets_m = []
    cyan_n = 0
    for fr in frames:
        m = cyan_mask(fr["img"])
        ys, xs = np.where(m > 0)
        if len(ys) < 20:
            continue
        cyan_n += 1
        h, w = fr["img"].shape[:2]
        cx = float(np.mean(xs))
        off_px = cx - w / 2.0
        offsets_px.append(off_px)
        # nearest det R
        R = None
        best_dt = 1e9
        for d in dets:
            dt = abs(d["t_ff"] - fr["t_ff"])
            if dt < best_dt and BANK_R[0] <= d["R"] <= 20.0:
                best_dt = dt
                R = d["R"]
        if R is not None and best_dt < 0.25:
            # x_m ≈ (u - cx) * Z / fx
            offsets_m.append(off_px * R / FX_NOM)
    return {
        "n_frames": len(frames),
        "cyan_frames": cyan_n,
        "cyan_pct": 100.0 * cyan_n / len(frames) if frames else None,
        "lat_offset_px": {
            "median": float(np.median(offsets_px)) if offsets_px else None,
            "p90_abs": float(np.percentile(np.abs(offsets_px), 90))
            if offsets_px else None,
            "n": len(offsets_px),
        },
        "lat_offset_m_est": {
            "median": float(np.median(offsets_m)) if offsets_m else None,
            "p90_abs": float(np.percentile(np.abs(offsets_m), 90))
            if offsets_m else None,
            "n": len(offsets_m),
        },
    }


def analyze_one(meta: dict) -> dict:
    path = resolve_log(meta["fid"], meta["fixture"])
    if path is None:
        return {"label": meta["label"], "fid": meta["fid"], "error": "log_not_found"}
    log = parse_flight(path)
    t_pass, psrc = find_pass_t(log)
    if t_pass is None:
        return {"label": meta["label"], "fid": meta["fid"], "error": "no_pass",
                "path": str(path)}
    t_death, death = find_death_t(log, t_pass)
    t_end = t_death if t_death is not None else (
        log["setpoints"][-1]["t_ff"] if log["setpoints"] else t_pass + 20.0)
    exit_info = frozen_exit(log, t_pass)
    if exit_info is None:
        return {"label": meta["label"], "fid": meta["fid"], "error": "no_exit",
                "t_pass": t_pass, "path": str(path)}

    # Hard collisions in inter-gate
    hard = [c for c in log["collisions"]
            if c["t_ff"] >= t_pass - 0.05
            and (c["threat_level"] >= 2 or c["impulse"] >= HARD_IMPULSE)]
    coll_rows = []
    for c in hard:
        integ = integrate_travel(log["setpoints"], t_pass, c["t_ff"],
                                 exit_info["bearing_deg"])
        # also gate_rel at collision
        st = min(log["states"], key=lambda s: abs(s["t_ff"] - c["t_ff"])) \
            if log["states"] else None
        gr_tx = None
        gr_R = None
        if st and st.get("gate_rel") and abs(st["t_ff"] - c["t_ff"]) < 0.15:
            t = list(map(float, st["gate_rel"]["t"]))
            gr_tx = t[0]
            gr_R = float(np.linalg.norm(t))
        coll_rows.append({
            "t_ff": c["t_ff"],
            "impulse": c["impulse"],
            "threat_level": c["threat_level"],
            "s_par_m": integ["s_par_m"],
            "s_lat_m": integ["s_lat_m"],
            "abs_s_lat_m": (abs(integ["s_lat_m"])
                            if integ["s_lat_m"] is not None else None),
            "gate_rel_tx": gr_tx,
            "gate_rel_R": gr_R,
        })

    mid = midrange_closest_tx(log["states"], t_pass, t_end)

    # Cyan on slice if present
    cyan = {"n_frames": 0, "note": "no_slice"}
    sp = resolve_slice(meta["fid"], meta["fixture"], meta["slice"])
    if sp is not None and meta.get("slice_note") and "pad" in meta["slice_note"]:
        cyan = {"n_frames": 0, "note": meta["slice_note"], "path": str(sp)}
    elif sp is not None:
        try:
            frames = decode_intergate_frames(sp, log, t_pass, t_end, stride=4)
            cyan = cyan_lateral_stats(frames, log["dets"])
            cyan["path"] = str(sp)
            cyan["n_decoded_intergate"] = len(frames)
        except Exception as e:
            cyan = {"n_frames": 0, "error": str(e), "path": str(sp)}

    abs_lats = [c["abs_s_lat_m"] for c in coll_rows
                if c["abs_s_lat_m"] is not None]
    s_pars = [c["s_par_m"] for c in coll_rows if c["s_par_m"] is not None]

    return {
        "label": meta["label"],
        "fid": meta["fid"],
        "path": str(path),
        "t_pass_ff": t_pass,
        "pass_source": psrc,
        "t_death_ff": t_death,
        "death": death,
        "exit": exit_info,
        "hard_collisions": coll_rows,
        "min_abs_s_lat_at_hard_m": float(min(abs_lats)) if abs_lats else None,
        "min_s_par_at_hard_m": float(min(s_pars)) if s_pars else None,
        "midrange_closest_tx": mid,
        "cyan": cyan,
        "intergate_duration_s": float(t_end - t_pass),
    }


def aggregate(rows: list[dict]) -> dict:
    ok = [r for r in rows if "error" not in r]
    lats = [r["min_abs_s_lat_at_hard_m"] for r in ok
            if r.get("min_abs_s_lat_at_hard_m") is not None]
    pars = [r["min_s_par_at_hard_m"] for r in ok
            if r.get("min_s_par_at_hard_m") is not None]
    mid_tx = [r["midrange_closest_tx"]["abs_tx"] for r in ok
              if r.get("midrange_closest_tx")]
    cyan_p90 = []
    for r in ok:
        m = (r.get("cyan") or {}).get("lat_offset_m_est") or {}
        if m.get("p90_abs") is not None:
            cyan_p90.append(m["p90_abs"])

    # corridor_lower: free half-width proxy = min |s_lat| at hard hit
    # (obstacle encountered that far off the exit chord). If we only hit
    # far off-chord, corridor along the chord may be wider — treat as
    # LOWER bound on observed obstacle distance from chord.
    corridor_lower = float(min(lats)) if lats else None

    # d_clear provisional: keep 0.9 unless along-track death is closer
    # (structure immediately after pass). Use 25th percentile of s_par
    # as a soft check — if p25 < 0.9, recommend that.
    d_clear = D_CLEAR_PROVISIONAL
    d_clear_note = "design default 0.9 m"
    if pars:
        p25 = float(np.percentile(pars, 25))
        if p25 < d_clear:
            d_clear = max(0.5, p25)
            d_clear_note = f"lowered to p25(s_par@hard)={p25:.2f}"

    d_bridge_max = None
    bridge_kill = None
    if corridor_lower is not None:
        d_bridge_max = min(0.8, corridor_lower - d_clear - MARGIN_M)
        bridge_kill = d_bridge_max <= 0

    return {
        "n_flights_ok": len(ok),
        "n_with_hard_lat": len(lats),
        "corridor_lower_m": corridor_lower,
        "corridor_lower_source": "min_|s_lat|_at_hard_env_collision",
        "d_clear_provisional_m": d_clear,
        "d_clear_note": d_clear_note,
        "d_bridge_max_m": d_bridge_max,
        "d_bridge_kill": bridge_kill,
        "formula": "d_bridge_max = min(0.8, corridor_lower - d_clear - 0.4)",
        "s_par_at_hard_m": {
            "min": float(min(pars)) if pars else None,
            "median": float(np.median(pars)) if pars else None,
            "p25": float(np.percentile(pars, 25)) if pars else None,
        },
        "midrange_abs_tx_m": {
            "min": float(min(mid_tx)) if mid_tx else None,
            "median": float(np.median(mid_tx)) if mid_tx else None,
        },
        "cyan_lat_p90_abs_m": {
            "min": float(min(cyan_p90)) if cyan_p90 else None,
            "median": float(np.median(cyan_p90)) if cyan_p90 else None,
            "n": len(cyan_p90),
        },
    }


def write_md(summary: dict) -> str:
    agg = summary["aggregate"]
    lines = [
        "# N-R4 corridor clearance",
        "",
        "Inter-gate obstacle proxy from hard env collisions after gate-1 "
        "pass, relative to the frozen exit chord (body-travel bearing).",
        "",
        "## Verdict",
        "",
        f"- **corridor_lower**: `{agg.get('corridor_lower_m')}` m "
        f"({agg.get('corridor_lower_source')})",
        f"- **d_clear provisional**: `{agg.get('d_clear_provisional_m')}` m "
        f"— {agg.get('d_clear_note')}",
        f"- **d_bridge_max**: `{agg.get('d_bridge_max_m')}` m "
        f"(`{agg.get('formula')}`)",
        f"- **bridge kill (≤0)**: `{agg.get('d_bridge_kill')}`",
        "",
        "## Per flight",
        "",
        "| label | t_pass | t_death | exit° | |s_lat|@hard | s_par@hard | mid |tx| | cyan% |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in summary["flights"]:
        if r.get("error"):
            lines.append(
                f"| {r.get('label')} | — | — | — | ERR:{r['error']} | — | — | — |")
            continue
        hard = r.get("hard_collisions") or []
        lat = r.get("min_abs_s_lat_at_hard_m")
        par = r.get("min_s_par_at_hard_m")
        mid = r.get("midrange_closest_tx") or {}
        cyan = r.get("cyan") or {}
        death = r.get("t_death_ff")
        death_s = "—" if death is None else f"{death:.2f}"
        lat_s = "—" if lat is None else f"{lat:.2f}"
        par_s = "—" if par is None else f"{par:.2f}"
        mid_s = "—" if not mid else f"{mid['abs_tx']:.2f}"
        cp = cyan.get("cyan_pct")
        cyan_s = "—" if cp is None else f"{cp:.0f}"
        lines.append(
            f"| {r['label']} | {r['t_pass_ff']:.2f} | {death_s} | "
            f"{r['exit']['bearing_deg']:+.1f} | {lat_s} | {par_s} | "
            f"{mid_s} | {cyan_s} |"
        )
    lines += [
        "",
        "## Method",
        "",
        "1. HUD pass → freeze exit bearing = median body-travel atan2(vy,vx) "
        "over final 0.15 s (forward vx>0.5).",
        "2. Integrate v_body from pass→collision; project onto exit unit "
        "(s_par) and right-of-exit (s_lat).",
        "3. Hard collision: threat_level≥2 or impulse≥1.5.",
        "4. Mid-range lock: min |gate_rel.tx| while R∈[3,12] m post-pass.",
        "5. Cyan: HSV (90,120,120)–(98,255,255) on takeoff→end slice; "
        "lateral px→m via R_est/fx.",
        "",
        f"Generated by `{OUT.name}/run_nr4_corridor.py`.",
        "",
    ]
    return "\n".join(lines)


def main():
    rows = [analyze_one(m) for m in FLIGHTS]
    summary = {
        "ask": "N-R4 corridor clearance",
        "flights": rows,
        "aggregate": aggregate(rows),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8")
    md = write_md(summary)
    (OUT / "report.md").write_text(md, encoding="utf-8")
    MD_ROOT.write_text(md, encoding="utf-8")
    agg = summary["aggregate"]
    print("N-R4 done")
    print("corridor_lower", agg.get("corridor_lower_m"))
    print("d_clear", agg.get("d_clear_provisional_m"))
    print("d_bridge_max", agg.get("d_bridge_max_m"),
          "kill", agg.get("d_bridge_kill"))
    for r in rows:
        if r.get("error"):
            print("ERR", r["label"], r["error"])
        else:
            print(r["label"], "pass", round(r["t_pass_ff"], 2),
                  "death", r.get("t_death_ff"),
                  "lat", r.get("min_abs_s_lat_at_hard_m"),
                  "par", r.get("min_s_par_at_hard_m"))


if __name__ == "__main__":
    main()
