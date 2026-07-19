"""Enable-gate evidence from phase6e F2 — V3 overlap, contact axis, FA=0.

Fixture lives in the sibling operator checkout (eni_dcim); deliverables
land under analysis/ in this repo.
"""
from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
FIX = Path(r"C:\Users\tsion\Projects\eni_dcim\fixtures\20260719T143556-phase6e-aim-tfv1")
FID = "20260719T143404-a76247fb"
LOG = FIX / f"{FID}-flight.jsonl"
SLICE = FIX / f"{FID}_takeoff_to_end.aigprec"
PARAMS = FIX / f"{FID}-params.json"

sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from aigp.core.messages import RelPose  # noqa: E402
from aigp.planning.approach import true_world_dz  # noqa: E402
from aigp.planning.vertical_terminal import (  # noqa: E402
    row_only_vertical_error,
    top_bar_vertical_error,
)

GATE_W = 1.6
GATE_H = 1.6
D_STAR_BAR = GATE_H / 2.0          # 0.80 — opening-center aim under top bar
D_STAR_BANNER = 0.15               # R4 provisional
FX = 320.0
FY = 320.0
CX = 320.0
CY = 180.0                         # 640x360
IMG_H = 360
IMG_W = 640

# User windows are t_from_first (log start).
WIN_V3 = (7.0, 8.0)
WIN_CONTACT = (8.12, 8.52)
CLIP_T = 7.97


def load_log(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def t0_first(rows: list[dict]) -> int:
    return int(rows[0]["mono_ns"])


def t_ff(row: dict, t0: int) -> float:
    return (int(row["mono_ns"]) - t0) / 1e9


def feature_oracle(y_top_px: float, span_px: float, mode: str,
                   depth_z: float | None) -> dict:
    """Pixel FEATURE -> e_z (+UP required displacement)."""
    y_norm = (CY - float(y_top_px)) / FY          # +UP
    span_norm = float(span_px) / FY
    out = {
        "y_top_px": float(y_top_px),
        "span_px": float(span_px),
        "y_norm": y_norm,
        "span_norm": span_norm,
        "mode": mode,
        "e_z_bar": None,
        "e_z_banner": None,
        "e_z_row_only_bar": None,
    }
    if span_norm > 1e-9 and mode == "BAR_FULL":
        out["e_z_bar"] = float(top_bar_vertical_error(
            y_norm, span_norm, GATE_W, D_STAR_BAR))
        out["e_z_banner"] = float(top_bar_vertical_error(
            y_norm, span_norm, GATE_W, D_STAR_BANNER))
    if depth_z is not None and depth_z > 0.05:
        out["e_z_row_only_bar"] = float(row_only_vertical_error(
            y_norm, float(depth_z), D_STAR_BAR))
    return out


def nearest_state(states: list[dict], t: float, max_dt: float = 0.08):
    if not states:
        return None
    best = min(states, key=lambda s: abs(s["t"] - t))
    return best if abs(best["t"] - t) <= max_dt else None


def believed_alt_error(st: dict, aim_up_m: float) -> dict:
    """Alt-hold error in +UP meters: + = vehicle needs to climb.

    Alt-hold nulls (world_dz - aim). world_dz + = gate BELOW vehicle (NED).
    When world_dz ≈ aim, believed is 'centered' on the aim point.
    e_believed_up = -(world_dz - aim)  matches TERM e_z sign.
    """
    gr = st.get("gate_rel")
    if gr is None:
        return {"e_believed_up": None, "world_dz": None, "aim": aim_up_m}
    t = np.asarray(gr["t"], float)
    q = np.asarray(st["q_att"], float)
    lr = float(st.get("level_roll", 0.0))
    lp = float(st.get("level_pitch", 0.0))
    # Near-gate aim taper (race_planner._aim_up): floor=0, aim*=dist/4
    dist = float(np.linalg.norm(t))
    aim = max(0.0, float(aim_up_m) * float(np.clip(dist / 4.0, 0.0, 1.0)))
    wdz = true_world_dz(RelPose(t=t, normal=np.asarray(gr.get("normal") or [0, 0, 1], float)),
                        q, lr, lp)
    e_up = -(wdz - aim)
    return {
        "e_believed_up": float(e_up),
        "world_dz": float(wdz),
        "aim": float(aim),
        "dist": dist,
        "age": float(st.get("gate_rel_age_s") or st.get("age_s") or 0.0),
        "t_cam": t.tolist(),
    }


def parse_states(rows: list[dict], t0: int) -> list[dict]:
    out = []
    for r in rows:
        if r.get("topic") != "state":
            continue
        d = r["data"]
        gr = d.get("gate_rel")
        if gr is None:
            continue
        age = d.get("gate_rel_age_s")
        if age is not None and not math.isfinite(float(age)):
            age = None
        out.append({
            "t": t_ff(r, t0),
            "gate_rel": gr,
            "q_att": d.get("q_att") or d.get("attitude") or [1, 0, 0, 0],
            "level_roll": d.get("level_roll", 0.0),
            "level_pitch": d.get("level_pitch", 0.0),
            "gate_rel_age_s": age,
            "gate_center_px": d.get("gate_center_px"),
        })
    return out


def parse_features(rows: list[dict], t0: int) -> list[dict]:
    out = []
    for r in rows:
        if r.get("topic") != "feature":
            continue
        d = r["data"]
        out.append({
            "t": t_ff(r, t0),
            "y_top_px": d["y_top_px"],
            "span_px": d["span_px"],
            "center_x_px": d["center_x_px"],
            "cert_status": d.get("cert_status"),
            "mode": d.get("mode", "BAR_FULL"),
        })
    return out


def parse_detections(rows: list[dict], t0: int) -> list[dict]:
    out = []
    for r in rows:
        if r.get("topic") != "detection":
            continue
        d = r["data"]
        rp = d.get("rel_pose") or {}
        tvec = d.get("t_vec") or rp.get("t")
        if tvec is None:
            continue
        tvec = list(map(float, tvec))
        corners = d.get("corners_px") or d.get("corners")
        center = d.get("center_px")
        out.append({
            "t": t_ff(r, t0),
            "t_vec": tvec,
            "R": float(np.linalg.norm(tvec)),
            "center_px": center,
            "corners": corners,
            "cert_status": d.get("cert_status"),
            "confidence": d.get("confidence"),
            "normal": d.get("normal") or rp.get("normal"),
        })
    return out


def parse_shadows(rows: list[dict], t0: int) -> list[dict]:
    out = []
    for r in rows:
        if r.get("topic") != "shadow":
            continue
        d = r["data"]
        out.append({
            "t": t_ff(r, t0),
            "owner": d.get("owner"),
            "up_legacy_mps": d.get("up_legacy_mps"),
            "adapter_delta_mps": d.get("adapter_delta_mps"),
            "adapter_ok": d.get("adapter_ok"),
        })
    return out


def parse_collisions(rows: list[dict], t0: int) -> list[dict]:
    out = []
    for r in rows:
        if r.get("topic") != "collision":
            continue
        d = r["data"]
        out.append({
            "t": t_ff(r, t0),
            "impulse": d.get("impulse"),
            "threat_level": d.get("threat_level"),
        })
    return out


def frame_ids_in_window(rows: list[dict], t0: int, lo: float, hi: float):
    fids = []
    for r in rows:
        if r.get("topic") != "frame":
            continue
        t = t_ff(r, t0)
        if lo <= t <= hi:
            fids.append(int(r["data"]["frame_id"]))
    return (min(fids), max(fids)) if fids else None


def contact_axis(dets: list[dict]) -> dict:
    """Post-crossing detections → which bar was hit (P-B predicts TOP).

    Heuristics (gate seen from behind/side after graze):
    - cam ty < 0 with center high in image (small y) ⇒ looking at UPPER
      structure (top bar / banner) ⇒ TOP contact consistent
    - cam ty > 0 / center near bottom ⇒ looking at lower ring ⇒ BOTTOM
    - |tx| >> |ty| with side-dominant center ⇒ lateral (LEFT/RIGHT)
    """
    rows = []
    votes = {"TOP": 0, "BOTTOM": 0, "LEFT": 0, "RIGHT": 0, "UNCLEAR": 0}
    for d in dets:
        tx, ty, tz = d["t_vec"]
        cx = cy = None
        if d.get("center_px"):
            cx, cy = float(d["center_px"][0]), float(d["center_px"][1])
        # Skip far-gate flickers
        if d["R"] > 8.0:
            label = "FAR_FLICKER"
        elif abs(tx) > abs(ty) + 0.25 and abs(tx) > 0.35:
            label = "RIGHT" if tx > 0 else "LEFT"
        elif ty < -0.15 or (cy is not None and cy < IMG_H * 0.40):
            label = "TOP"
        elif ty > 0.15 or (cy is not None and cy > IMG_H * 0.60):
            label = "BOTTOM"
        else:
            label = "UNCLEAR"
        if label in votes:
            votes[label] += 1
        rows.append({
            "t": d["t"], "R": d["R"], "t_vec": d["t_vec"],
            "center_px": d.get("center_px"), "cert": d.get("cert_status"),
            "label": label,
        })
    # majority among structural votes
    structural = {k: v for k, v in votes.items() if k != "UNCLEAR"}
    winner = max(structural, key=structural.get) if any(structural.values()) else "UNCLEAR"
    return {"votes": votes, "winner": winner, "rows": rows,
            "hypothesis_PB_top": winner == "TOP"}


def run_cert_suite(lo_fid: int, hi_fid: int) -> dict:
    py = Path(r"C:\Users\tsion\Projects\eni_dcim\.venv\Scripts\python.exe")
    if not py.exists():
        py = Path(sys.executable)
    cmd = [
        str(py), str(ROOT / "scripts" / "cert_suite.py"),
        "--slice", str(SLICE),
        "--log", str(LOG),
        "--window", f"{lo_fid}:{hi_fid}",
        "--params", str(PARAMS) if PARAMS.exists() else str(ROOT / "config" / "params_default.json"),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "fa0": proc.returncode == 0,
    }


def aim_up_from_params() -> float:
    if not PARAMS.exists():
        return 0.3
    p = json.loads(PARAMS.read_text(encoding="utf-8"))
    # nested or flat
    try:
        return float(p["planner"]["approach"]["aim_up_m"])
    except Exception:
        return float(p.get("planner.approach.aim_up_m", 0.3))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = load_log(LOG)
    t0 = t0_first(rows)
    aim0 = aim_up_from_params()
    states = parse_states(rows, t0)
    features = parse_features(rows, t0)
    dets = parse_detections(rows, t0)
    shadows = parse_shadows(rows, t0)
    collisions = parse_collisions(rows, t0)

    # --- V3 overlap band (7.0-8.0) ---
    feats_v3 = [f for f in features if WIN_V3[0] <= f["t"] < WIN_V3[1]]
    states_v3 = [s for s in states if WIN_V3[0] <= s["t"] < WIN_V3[1]]
    shadows_v3 = [s for s in shadows if WIN_V3[0] <= s["t"] < WIN_V3[1]]
    v3_series = []
    for f in feats_v3:
        st = nearest_state(states_v3, f["t"])
        depth = None
        bel = {"e_believed_up": None}
        if st is not None:
            depth = float(st["gate_rel"]["t"][2])
            bel = believed_alt_error(st, aim0)
        ora = feature_oracle(f["y_top_px"], f["span_px"], f["mode"], depth)
        delta = None
        if ora["e_z_bar"] is not None and bel.get("e_believed_up") is not None:
            delta = ora["e_z_bar"] - bel["e_believed_up"]
        v3_series.append({
            "t": f["t"],
            "cert_status": f["cert_status"],
            "mode": f["mode"],
            **{k: ora[k] for k in ("y_top_px", "span_px", "y_norm", "span_norm",
                                   "e_z_bar", "e_z_banner", "e_z_row_only_bar")},
            "e_believed_up": bel.get("e_believed_up"),
            "world_dz": bel.get("world_dz"),
            "aim": bel.get("aim"),
            "age": bel.get("age"),
            "dist": bel.get("dist"),
            "t_cam": bel.get("t_cam"),
            "delta_oracle_minus_believed": delta,
            "shadow_owner": None,
            "up_legacy_mps": None,
        })
        # attach nearest shadow
        sh = min(shadows_v3, key=lambda s: abs(s["t"] - f["t"])) if shadows_v3 else None
        if sh and abs(sh["t"] - f["t"]) < 0.05:
            v3_series[-1]["shadow_owner"] = sh["owner"]
            v3_series[-1]["up_legacy_mps"] = sh["up_legacy_mps"]

    # Also dense believed series (every state) for RMS in 1.5-3m if any
    believed_series = []
    for st in states_v3:
        bel = believed_alt_error(st, aim0)
        R = bel.get("dist")
        believed_series.append({"t": st["t"], **bel, "R": R})

    e_z_vals = [r["e_z_bar"] for r in v3_series if r["e_z_bar"] is not None]
    bel_vals = [r["e_believed_up"] for r in v3_series if r["e_believed_up"] is not None]
    deltas = [r["delta_oracle_minus_believed"] for r in v3_series
              if r["delta_oracle_minus_believed"] is not None]

    def _stats(xs):
        if not xs:
            return None
        a = np.asarray(xs, float)
        return {
            "n": int(a.size),
            "mean": float(a.mean()),
            "rms": float(np.sqrt(np.mean(a ** 2))),
            "median": float(np.median(a)),
            "min": float(a.min()),
            "max": float(a.max()),
        }

    # Overlap-band: features whose believed range is in 0.5-3m (terminal)
    # V3 release bar is RMS<=0.05m of (oracle - reference) in 1.5-3m;
    # here reference = believed alt-hold error (what flew).
    v3_verdict = {
        "n_features": len(feats_v3),
        "n_paired": len(deltas),
        "e_z_bar": _stats(e_z_vals),
        "e_believed_up": _stats(bel_vals),
        "delta_oracle_minus_believed": _stats(deltas),
        "would_term_descend": bool(e_z_vals) and float(np.median(e_z_vals)) < -0.15,
        "believed_near_centered": bool(bel_vals) and abs(float(np.median(bel_vals))) < 0.15,
        "high_bias_disagreement": None,
        "v3_rms_bar_0p05": None,
    }
    if deltas:
        med_d = float(np.median(deltas))
        # oracle more negative than believed ⇒ HIGH disagreement (TERM descend)
        v3_verdict["high_bias_disagreement"] = med_d < -0.20
        v3_verdict["v3_rms_bar_0p05"] = float(np.sqrt(np.mean(np.square(deltas)))) <= 0.05
        v3_verdict["median_delta_m"] = med_d

    # --- Contact axis ---
    dets_c = [d for d in dets if WIN_CONTACT[0] <= d["t"] <= WIN_CONTACT[1]]
    contact = contact_axis(dets_c)

    # Pre-clip geometry snapshot (believed vs detection)
    dets_pre = [d for d in dets if 7.85 <= d["t"] <= 7.98]
    closest_det = min(dets_pre, key=lambda d: d["R"]) if dets_pre else None
    st_clip = nearest_state(states, CLIP_T, max_dt=0.1)
    clip_snap = {
        "collisions": [c for c in collisions if 7.9 <= c["t"] <= 8.1],
        "closest_det_preclip": closest_det,
        "state_at_clip": None if st_clip is None else {
            "t": st_clip["t"],
            **believed_alt_error(st_clip, aim0),
        },
    }

    # --- FA=0 cert suite ---
    # Graze window: last ~0.5s of approach through recover (7.5-8.3)
    win_fids = frame_ids_in_window(rows, t0, 7.50, 8.30)
    cert = None
    if win_fids and SLICE.exists():
        cert = run_cert_suite(win_fids[0], win_fids[1])
    else:
        cert = {"fa0": None, "error": "missing slice or frame ids",
                "window_fids": win_fids}

    # Shadow owner histogram in V3 window
    from collections import Counter
    owner_hist = dict(Counter(s["owner"] for s in shadows_v3))

    summary = {
        "flight": FID,
        "fixture": str(FIX),
        "t0_mono_ns": t0,
        "aim_up_m_param": aim0,
        "d_star_bar": D_STAR_BAR,
        "d_star_banner": D_STAR_BANNER,
        "windows": {"v3": WIN_V3, "contact": WIN_CONTACT, "clip_t": CLIP_T},
        "v3": v3_verdict,
        "v3_series": v3_series,
        "believed_series_n": len(believed_series),
        "shadow_owner_hist_7_8": owner_hist,
        "contact": {
            "votes": contact["votes"],
            "winner": contact["winner"],
            "hypothesis_PB_top": contact["hypothesis_PB_top"],
            "n_dets": len(dets_c),
        },
        "contact_rows": contact["rows"],
        "clip_snap": clip_snap,
        "cert": {
            "window_fids": win_fids,
            "fa0": cert.get("fa0"),
            "returncode": cert.get("returncode"),
            "stdout": cert.get("stdout"),
            "stderr": (cert.get("stderr") or "")[:2000],
        },
        "enable_greens": {
            "V3_overlap_disagreement_documented": bool(v3_series),
            "V3_rms_le_0p05": v3_verdict.get("v3_rms_bar_0p05"),
            "FA0_graze": cert.get("fa0"),
            "A6_hb": "OTHER_TASK",
            "note": ("V3 release bar is RMS<=0.05m oracle-vs-reference in "
                     "1.5-3m; this flight's graze band is sub-2m FEATURE "
                     "samples — disagreement magnitude is the enable "
                     "evidence that TERM would have acted differently."),
        },
    }

    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    with (OUT / "v3_series.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "t", "cert_status", "mode", "y_top_px", "span_px", "y_norm",
            "span_norm", "e_z_bar", "e_z_banner", "e_z_row_only_bar",
            "e_believed_up", "world_dz", "aim", "age", "dist",
            "delta_oracle_minus_believed", "shadow_owner", "up_legacy_mps",
        ])
        w.writeheader()
        for r in v3_series:
            w.writerow({k: r.get(k) for k in w.fieldnames})

    with (OUT / "contact_dets.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "t", "R", "tx", "ty", "tz", "cx", "cy", "cert", "label",
        ])
        w.writeheader()
        for r in contact["rows"]:
            tx, ty, tz = r["t_vec"]
            cx = cy = ""
            if r.get("center_px"):
                cx, cy = r["center_px"][0], r["center_px"][1]
            w.writerow({
                "t": r["t"], "R": r["R"], "tx": tx, "ty": ty, "tz": tz,
                "cx": cx, "cy": cy, "cert": r.get("cert"), "label": r["label"],
            })

    report = render_report(summary)
    (OUT / "enable-gates-f2.md").write_text(report, encoding="utf-8")
    (ROOT / "analysis" / "2026-07-19-enable-gates-f2.md").write_text(report, encoding="utf-8")
    print(json.dumps({
        "v3": v3_verdict,
        "contact": summary["contact"],
        "fa0": cert.get("fa0"),
        "cert_stdout": (cert.get("stdout") or "")[:800],
    }, indent=2))
    return 0


def render_report(s: dict) -> str:
    v3 = s["v3"]
    c = s["contact"]
    cert = s["cert"]
    clip = s["clip_snap"]
    lines = []
    lines.append("# Enable-gate evidence — phase6e F2")
    lines.append("")
    lines.append(f"Flight `{s['flight']}` in fixture "
                 f"`20260719T143556-phase6e-aim-tfv1` (sibling checkout).")
    lines.append("Timebase: **t_from_first** (log start); takeoff ≈ 4.22 s; "
                 "gate clips at **t ≈ 7.97–7.98** (impulses 0.10 + 4.39).")
    lines.append("")
    lines.append("These are **two of the three enable greens** (V3 disagreement "
                 "evidence + FA=0). A6/`h_b` is a separate analyst task.")
    lines.append("")
    lines.append("## Clip snapshot")
    lines.append("")
    lines.append(f"- collisions: `{json.dumps(clip.get('collisions'))}`")
    cd = clip.get("closest_det_preclip")
    if cd:
        lines.append(
            f"- closest pre-clip detection: R={cd['R']:.3f} m at t={cd['t']:.3f}, "
            f"t_vec={cd['t_vec']}, center={cd.get('center_px')}"
        )
    sc = clip.get("state_at_clip")
    if sc:
        lines.append(
            f"- state @ clip: t={sc['t']:.3f}, world_dz={sc.get('world_dz')}, "
            f"aim={sc.get('aim')}, e_believed_up={sc.get('e_believed_up')}, "
            f"age={sc.get('age')}, t_cam={sc.get('t_cam')}"
        )
    lines.append("")
    lines.append("## 1. V3 overlap-band — oracle e_z vs believed alt-hold")
    lines.append("")
    lines.append("From logged `feature` (pixel top-bar + span) and paired "
                 "`state` in **t ∈ [7.0, 8.0)**:")
    lines.append("")
    lines.append(f"- FEATURE samples: **{v3.get('n_features')}** "
                 f"(paired with state: {v3.get('n_paired')})")
    lines.append(f"- d*_bar = {s['d_star_bar']} (opening center under top bar); "
                 f"d*_banner = {s['d_star_banner']} (provisional R4)")
    lines.append(f"- shadow owner hist: `{s.get('shadow_owner_hist_7_8')}`")
    lines.append("")
    lines.append("### Series")
    lines.append("")
    lines.append("| t | y_top_px | span_px | e_z_bar | e_z_banner | "
                 "e_believed_up | Δ(oracle−bel) | age | shadow |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for r in s["v3_series"]:
        def fmt(x):
            return "" if x is None else f"{x:.3f}"
        lines.append(
            f"| {r['t']:.3f} | {fmt(r.get('y_top_px'))} | {fmt(r.get('span_px'))} | "
            f"{fmt(r.get('e_z_bar'))} | {fmt(r.get('e_z_banner'))} | "
            f"{fmt(r.get('e_believed_up'))} | "
            f"{fmt(r.get('delta_oracle_minus_believed'))} | "
            f"{fmt(r.get('age'))} | {r.get('shadow_owner','')} |"
        )
    lines.append("")
    lines.append("### Stats")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps({
        "e_z_bar": v3.get("e_z_bar"),
        "e_believed_up": v3.get("e_believed_up"),
        "delta_oracle_minus_believed": v3.get("delta_oracle_minus_believed"),
        "would_term_descend": v3.get("would_term_descend"),
        "believed_near_centered": v3.get("believed_near_centered"),
        "high_bias_disagreement": v3.get("high_bias_disagreement"),
        "median_delta_m": v3.get("median_delta_m"),
        "v3_rms_le_0p05": v3.get("v3_rms_bar_0p05"),
    }, indent=2))
    lines.append("```")
    lines.append("")
    # Verdict paragraph
    if v3.get("would_term_descend") and v3.get("believed_near_centered"):
        lines.append(
            "**Verdict:** YES — the pixel-row oracle is **HIGH** "
            f"(median e_z_bar ≈ {v3['e_z_bar']['median']:.2f} m ⇒ TERM would "
            "command **descend**) while alt-hold believed near-centered "
            f"(median e_believed_up ≈ {v3['e_believed_up']['median']:.2f} m). "
            f"Median disagreement Δ ≈ {v3.get('median_delta_m')} m."
        )
    elif v3.get("high_bias_disagreement"):
        lines.append(
            "**Verdict:** oracle−believed median Δ is negative "
            f"({v3.get('median_delta_m')} m) — TERM would pull **down** relative "
            "to what alt-hold was doing."
        )
    else:
        lines.append(
            "**Verdict:** see stats — disagreement not cleanly in the "
            "~0.3 m HIGH direction on the paired FEATURE samples "
            "(or FEATURE count too small / cert=none)."
        )
    lines.append("")
    lines.append(
        "Note: all FEATURE `cert_status` values in this window are "
        "`none` — the side-pair certificate never armed, so live TERM "
        "ownership would NOT have captured even if enable were true. "
        "The oracle series is still the enable-gate *measurement* of "
        "what a healthy terminal feature would have said."
    )
    lines.append("")
    lines.append("V3 release bar (RMS ≤ 0.05 m in the 1.5–3 m overlap band) "
                 "is a tracker hygiene gate on healthy approaches; this "
                 "graze’s sub-2 m FEATURE band documents the **actuation "
                 "delta** alt-hold vs oracle, not a pass of that RMS bar "
                 f"(v3_rms_le_0p05={v3.get('v3_rms_bar_0p05')}).")
    lines.append("")
    lines.append("## 2. Axis of contact — post-crossing detections")
    lines.append("")
    lines.append(f"Window t ∈ [{WIN_CONTACT[0]}, {WIN_CONTACT[1]}] "
                 f"({c['n_dets']} detections).")
    lines.append("")
    lines.append(f"- votes: `{c['votes']}`")
    lines.append(f"- winner: **{c['winner']}**")
    lines.append(f"- P-B / top-bar hypothesis (predicts TOP): "
                 f"**{'CONFIRMED' if c['hypothesis_PB_top'] else 'NOT CONFIRMED'}**")
    lines.append("")
    lines.append("| t | R | t_vec | center_px | cert | label |")
    lines.append("|---:|---:|---|---|---|---|")
    for r in s["contact_rows"]:
        lines.append(
            f"| {r['t']:.3f} | {r['R']:.2f} | `{[round(x,3) for x in r['t_vec']]}` | "
            f"`{r.get('center_px')}` | {r.get('cert')} | {r['label']} |"
        )
    lines.append("")
    lines.append("## 3. FA=0 — certificate chain through the graze")
    lines.append("")
    lines.append(f"Command window frame ids: `{cert.get('window_fids')}` "
                 "(t_from_first 7.50–8.30, covers final approach + clip + "
                 "immediate recover).")
    lines.append("")
    lines.append(f"- exit code: `{cert.get('returncode')}`")
    lines.append(f"- **FA=0: {'PASS' if cert.get('fa0') else 'FAIL / BLOCKED'}**")
    lines.append("")
    lines.append("```")
    lines.append((cert.get("stdout") or "").rstrip() or "(no stdout)")
    lines.append("```")
    if cert.get("stderr"):
        lines.append("")
        lines.append("stderr (truncated):")
        lines.append("```")
        lines.append(cert["stderr"][:1500])
        lines.append("```")
    lines.append("")
    lines.append("## Enable-green scorecard")
    lines.append("")
    lines.append("| Gate | Status | Evidence |")
    lines.append("|---|---|---|")
    g = s["enable_greens"]
    fa = "GREEN" if g.get("FA0_graze") else ("RED" if g.get("FA0_graze") is False else "BLOCKED")
    v3s = ("DOCUMENTED disagreement"
           if g.get("V3_overlap_disagreement_documented") else "missing")
    lines.append(f"| V3 oracle-vs-believed (this flight) | {v3s} | "
                 f"Δ median={v3.get('median_delta_m')} m; "
                 f"TERM descend={v3.get('would_term_descend')} |")
    lines.append(f"| FA=0 suite (graze window) | **{fa}** | "
                 f"cert_suite window {cert.get('window_fids')} |")
    lines.append("| A6 / h_b | OTHER TASK | feeds the third green |")
    lines.append("")
    lines.append("## Deliverables")
    lines.append("")
    lines.append("- `enable-gates-f2.md` (this file)")
    lines.append("- `summary.json`, `v3_series.csv`, `contact_dets.csv`")
    lines.append("")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
