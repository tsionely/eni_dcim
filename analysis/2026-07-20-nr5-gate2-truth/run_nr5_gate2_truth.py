"""P3 — N-R5 gate-2 truth labels at gate-1 crossing (+ try39 near-pass).

For death fixtures try15/try39, try39 geometric near-pass (R≈0.42), and
phase6i passes: at gate-1 HUD crossing record true bearing/range/height of
the best gate-2 candidate (far det R∈[3,12] m, angularly nearest to exit,
or first persistent post-pass lock).

Outputs table for B1/A1 kill tests.
  analysis/2026-07-20-nr5-gate2-truth/summary.json
  analysis/2026-07-20-nr5-gate2-truth.md
"""
from __future__ import annotations

import json
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
MD_ROOT = ROOT / "analysis" / "2026-07-20-nr5-gate2-truth.md"
sys.path.insert(0, str(ROOT / "src"))

EXIT_WINDOW_S = 0.15
BANK_R = (3.0, 12.0)
NEAR_PASS_R = 0.42
NEAR_PASS_TOL = 0.15

FLIGHTS = [
    {
        "label": "try15_death",
        "fid": "20260719T160537-f170ead6",
        "fixture": "20260719T164956-phase6h-first-enable",
        "role": "chase_death",
    },
    {
        "label": "try39_death",
        "fid": "20260719T163649-f170ead6",
        "fixture": "20260719T164956-phase6h-first-enable",
        "role": "chase_death_plus_nearpass",
        "label_nearpass": True,
    },
    {
        "label": "phase6i_200816",
        "fid": "20260719T200816-f170ead6",
        "fixture": "20260719T204430-phase6i-r-rate-ab",
        "role": "pass",
    },
    {
        "label": "phase6i_201851",
        "fid": "20260719T201851-50f9dcc8",
        "fixture": "20260719T204430-phase6i-r-rate-ab",
        "role": "pass",
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


def elev_deg(ty: float, tz: float) -> float:
    return float(np.degrees(np.arctan2(-ty, max(tz, 1e-6))))


def ang_diff(a: float, b: float) -> float:
    return float((a - b + 180.0) % 360.0 - 180.0)


def parse_flight(path: Path) -> dict:
    rows = load_jsonl(path)
    t0 = int(rows[0]["mono_ns"])
    toff = takeoff_mono(rows)
    dets, states, setpoints, race = [], [], [], []
    for r in rows:
        mono = int(r["mono_ns"])
        t_ff = (mono - toff) / 1e9
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
                "t_ff": t_ff, "t_vec": tvec, "R": R,
                "bearing": bearing_deg(tvec[0], tvec[2]),
                "elev": elev_deg(tvec[1], tvec[2]),
                "height_ty": tvec[1],
                "cert": d.get("cert_status"),
                "center_px": d.get("center_px"),
            })
        elif topic == "state":
            gr = d.get("gate_rel")
            states.append({"t_ff": t_ff, "gate_rel": gr, "age": d.get("gate_rel_age_s")})
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
    return {
        "dets": dets, "states": states, "setpoints": setpoints,
        "race": race, "t0": t0, "takeoff": toff,
    }


def find_pass_t(log: dict) -> tuple[float | None, str]:
    prev = None
    for r in log["race"]:
        idx = r.get("active_gate_index")
        if idx is not None and prev is not None and idx > prev:
            return r["t_ff"], "hud"
        if idx is not None:
            prev = idx
    return None, "none"


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
        return {"bearing_deg": float(np.median(travel)), "source": "body_travel_median"}
    if los:
        return {"bearing_deg": float(np.median(los)), "source": "gate1_los_median"}
    if travel:
        return {"bearing_deg": float(np.median(travel)), "source": "body_travel_sparse"}
    return None


def best_gate2_at_crossing(dets: list[dict], t_pass: float,
                           exit_bearing: float) -> dict | None:
    """Far det R∈[3,12] nearest in angle to exit; window around crossing."""
    cands = [d for d in dets
             if t_pass - 0.3 <= d["t_ff"] <= t_pass + 0.5
             and BANK_R[0] <= d["R"] <= BANK_R[1]]
    source = "far_det_near_crossing"
    if not cands:
        cands = [d for d in dets
                 if t_pass - 0.5 <= d["t_ff"] <= t_pass + 1.0
                 and 2.5 <= d["R"] <= 15.0]
        source = "relaxed_2.5_15"
    if not cands:
        return None
    scored = sorted(
        cands,
        key=lambda d: (abs(ang_diff(d["bearing"], exit_bearing)),
                       abs(d["t_ff"] - t_pass)),
    )
    best = scored[0]
    rivals = [d for d in scored[1:5]
              if abs(ang_diff(d["bearing"], best["bearing"])) > 5.0]
    return {
        "source": source,
        "t_ff": best["t_ff"],
        "bearing_deg": best["bearing"],
        "R_m": best["R"],
        "elev_deg": best["elev"],
        "height_ty_m": best["height_ty"],
        "error_vs_exit_deg": ang_diff(best["bearing"], exit_bearing),
        "n_cands": len(cands),
        "rival_bearings_deg": [r["bearing"] for r in rivals[:3]],
        "center_px": best.get("center_px"),
        "cert": best.get("cert"),
    }


def first_persistent_postpass_lock(states: list[dict], t_pass: float,
                                   exit_bearing: float,
                                   persist_s: float = 0.25) -> dict | None:
    """First post-pass state lock with R∈[3,12] held ≥persist_s."""
    window = [s for s in states
              if t_pass < s["t_ff"] <= t_pass + 3.0 and s.get("gate_rel")]
    if not window:
        return None
    # find contiguous stretches
    best = None
    i = 0
    while i < len(window):
        s0 = window[i]
        t = list(map(float, s0["gate_rel"]["t"]))
        R = float(np.linalg.norm(t))
        if not (BANK_R[0] <= R <= BANK_R[1]):
            i += 1
            continue
        j = i
        while j + 1 < len(window):
            s1 = window[j + 1]
            t1 = list(map(float, s1["gate_rel"]["t"]))
            R1 = float(np.linalg.norm(t1))
            if abs(R1 - R) > 4.0:
                break
            if not (2.5 <= R1 <= 15.0):
                break
            j += 1
        dur = window[j]["t_ff"] - s0["t_ff"]
        if dur >= persist_s:
            brg = bearing_deg(t[0], t[2])
            cand = {
                "source": "postpass_persistent_state",
                "t_ff": s0["t_ff"],
                "bearing_deg": brg,
                "R_m": R,
                "elev_deg": elev_deg(t[1], t[2]),
                "height_ty_m": t[1],
                "error_vs_exit_deg": ang_diff(brg, exit_bearing),
                "persist_s": dur,
                "age": s0.get("age"),
            }
            if best is None or s0["t_ff"] < best["t_ff"]:
                best = cand
            break
        i = j + 1
    return best


def try39_nearpass(states: list[dict], t_pass: float) -> dict | None:
    """Label geometric near-pass of gate 2 when state R≈0.42 post-pass."""
    best = None
    for s in states:
        if s["t_ff"] < t_pass:
            continue
        gr = s.get("gate_rel")
        if gr is None:
            continue
        t = list(map(float, gr["t"]))
        R = float(np.linalg.norm(t))
        if abs(R - NEAR_PASS_R) > NEAR_PASS_TOL + 0.35:
            continue
        score = abs(R - NEAR_PASS_R)
        if best is None or score < best["_score"]:
            best = {
                "_score": score,
                "t_ff": s["t_ff"],
                "R_m": R,
                "bearing_deg": bearing_deg(t[0], t[2]),
                "elev_deg": elev_deg(t[1], t[2]),
                "height_ty_m": t[1],
                "tx": t[0], "ty": t[1], "tz": t[2],
                "age": s.get("age"),
                "note": "geometric_term_nearpass_gate2",
            }
    # Prefer the global post-pass minimum R if closer to 0.42 narrative
    min_r = None
    for s in states:
        if s["t_ff"] < t_pass:
            continue
        gr = s.get("gate_rel")
        if gr is None:
            continue
        t = list(map(float, gr["t"]))
        R = float(np.linalg.norm(t))
        if R < 1.5 and (min_r is None or R < min_r["R_m"]):
            min_r = {
                "t_ff": s["t_ff"], "R_m": R,
                "bearing_deg": bearing_deg(t[0], t[2]),
                "elev_deg": elev_deg(t[1], t[2]),
                "height_ty_m": t[1],
                "tx": t[0], "ty": t[1], "tz": t[2],
                "age": s.get("age"),
                "note": "postpass_min_state_R",
            }
    if best is not None:
        best.pop("_score", None)
        best["also_min_R"] = min_r
        return best
    return min_r


def analyze_one(meta: dict) -> dict:
    path = resolve_log(meta["fid"], meta["fixture"])
    if path is None:
        return {"label": meta["label"], "fid": meta["fid"], "error": "log_not_found"}
    log = parse_flight(path)
    t_pass, psrc = find_pass_t(log)
    if t_pass is None:
        return {"label": meta["label"], "fid": meta["fid"], "error": "no_hud_pass",
                "path": str(path)}
    exit_info = frozen_exit(log, t_pass)
    if exit_info is None:
        return {"label": meta["label"], "fid": meta["fid"], "error": "no_exit",
                "t_pass": t_pass}
    g2 = best_gate2_at_crossing(log["dets"], t_pass, exit_info["bearing_deg"])
    persist = first_persistent_postpass_lock(
        log["states"], t_pass, exit_info["bearing_deg"])
    # Prefer crossing far-det; fall back to persistent lock
    truth = g2 if g2 is not None else persist
    truth_source = (g2 or {}).get("source") if g2 else (
        persist.get("source") if persist else None)

    nearpass = None
    if meta.get("label_nearpass"):
        nearpass = try39_nearpass(log["states"], t_pass)

    # B1/A1 kill-test row
    kill_row = {
        "flight": meta["label"],
        "fid": meta["fid"],
        "t_pass_ff": t_pass,
        "exit_bearing_deg": exit_info["bearing_deg"],
        "gate2_bearing_deg": truth["bearing_deg"] if truth else None,
        "gate2_R_m": truth["R_m"] if truth else None,
        "gate2_elev_deg": truth["elev_deg"] if truth else None,
        "gate2_height_ty_m": truth["height_ty_m"] if truth else None,
        "err_vs_exit_deg": truth["error_vs_exit_deg"] if truth else None,
        "label_source": truth_source,
        # A1: a -20°/17m hop must be rejected — record whether truth is in tube
        "in_bearing_cone_pm12": (
            abs(truth["error_vs_exit_deg"]) <= 12.0 if truth else None),
        "in_range_tube_3_12": (
            BANK_R[0] <= truth["R_m"] <= BANK_R[1] if truth else None),
    }

    return {
        "label": meta["label"],
        "fid": meta["fid"],
        "role": meta["role"],
        "path": str(path),
        "t_pass_ff": t_pass,
        "pass_source": psrc,
        "exit": exit_info,
        "gate2_at_crossing": g2,
        "postpass_persistent_lock": persist,
        "truth_used": truth,
        "kill_test_row": kill_row,
        "try39_nearpass_gate2": nearpass,
    }


def write_md(summary: dict) -> str:
    lines = [
        "# N-R5 gate-2 truth labels",
        "",
        "Truth labels at gate-1 HUD crossing for B1 (successor selection) "
        "and A1 (acquisition tube) kill tests.",
        "",
        "## B1 / A1 table",
        "",
        "| flight | t_pass | exit° | g2 bearing° | g2 R | elev° | ty (height) | "
        "err vs exit° | in ±12° | in [3,12] | source |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for r in summary["flights"]:
        if r.get("error"):
            lines.append(f"| {r['label']} | — | — | ERR: {r['error']} | | | | | | | |")
            continue
        k = r["kill_test_row"]
        lines.append(
            f"| {k['flight']} | {k['t_pass_ff']:.2f} | "
            f"{k['exit_bearing_deg']:+.1f} | "
            f"{_fmt(k['gate2_bearing_deg'], '+.1f')} | "
            f"{_fmt(k['gate2_R_m'], '.2f')} | "
            f"{_fmt(k['gate2_elev_deg'], '+.1f')} | "
            f"{_fmt(k['gate2_height_ty_m'], '+.2f')} | "
            f"{_fmt(k['err_vs_exit_deg'], '+.1f')} | "
            f"{k['in_bearing_cone_pm12']} | {k['in_range_tube_3_12']} | "
            f"{k['label_source']} |"
        )
    lines += ["", "## try39 near-pass (R≈0.42)", ""]
    np_ = None
    for r in summary["flights"]:
        if r.get("try39_nearpass_gate2"):
            np_ = r["try39_nearpass_gate2"]
            break
    if np_ is None:
        lines.append("No near-pass label found.")
    else:
        lines.append(
            f"- t_ff=`{np_['t_ff']:.3f}`  R=`{np_['R_m']:.3f}` m  "
            f"bearing=`{np_['bearing_deg']:+.1f}`°  "
            f"elev=`{np_['elev_deg']:+.1f}`°  ty=`{np_['height_ty_m']:+.3f}`  "
            f"note=`{np_.get('note')}`"
        )
        if np_.get("also_min_R"):
            m = np_["also_min_R"]
            lines.append(
                f"- also post-pass min R: t_ff=`{m['t_ff']:.3f}` "
                f"R=`{m['R_m']:.3f}` bearing=`{m['bearing_deg']:+.1f}`°"
            )
    lines += [
        "",
        "## Method",
        "",
        "1. Gate-1 pass = HUD active_gate_index increment.",
        "2. Exit bearing = median body-travel over final 0.15 s.",
        "3. Gate-2 truth = far detection R∈[3,12] in [t_pass−0.3, +0.5], "
        "angularly nearest to exit; else first persistent post-pass state lock.",
        "4. try39 near-pass = state R closest to 0.42 after pass.",
        "",
        f"Generated by `{OUT.name}/run_nr5_gate2_truth.py`.",
        "",
    ]
    return "\n".join(lines)


def _fmt(v, spec: str) -> str:
    if v is None:
        return "—"
    return format(v, spec)


def main():
    rows = [analyze_one(m) for m in FLIGHTS]
    kill_table = [r["kill_test_row"] for r in rows if r.get("kill_test_row")]
    summary = {
        "ask": "N-R5 gate-2 truth labels",
        "flights": rows,
        "kill_test_table": kill_table,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8")
    md = write_md(summary)
    (OUT / "report.md").write_text(md, encoding="utf-8")
    MD_ROOT.write_text(md, encoding="utf-8")
    print("N-R5 done")
    for k in kill_table:
        print(k["flight"], "exit", k["exit_bearing_deg"],
              "g2", k["gate2_bearing_deg"], "R", k["gate2_R_m"],
              "err", k["err_vs_exit_deg"])
    for r in rows:
        if r.get("try39_nearpass_gate2"):
            np_ = r["try39_nearpass_gate2"]
            print("try39 nearpass", "t", np_["t_ff"], "R", np_["R_m"])


if __name__ == "__main__":
    main()
