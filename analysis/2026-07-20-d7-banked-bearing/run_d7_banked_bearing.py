"""P1 — D7 + banked-bearing errors (sizes the acquisition cone).

Spec (docs/design/intergate-segment.md §S4 + §8C):
  - Frozen exit vector at gate-1 pass / closest approach
  - Bank candidate when R ∈ [3, 12] m (pre-cross visibility)
  - Score bearing error vs frozen exit vector at crossing
  - Output Q99 + D7 ambiguity band; HARD FAIL if Q99+2° > 12°

Also: fraction of gate-1 approaches that see gate 2 before crossing.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
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
FIX = ROOT / "fixtures"
SIB = Path(r"C:\Users\tsion\Projects\eni_dcim\fixtures")
INV = ROOT / "analysis" / "_d7_inventory_out.json"

HARD_CAP_DEG = 12.0
BANK_R = (3.0, 12.0)
NEAR_R = 2.0
EXIT_WINDOW_S = 0.15


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
    """Azimuth in camera/body forward frame: 0 = straight ahead, +right."""
    return float(np.degrees(np.arctan2(tx, max(tz, 1e-6))))


def ang_diff(a: float, b: float) -> float:
    """Smallest signed difference a-b in degrees."""
    d = (a - b + 180.0) % 360.0 - 180.0
    return float(d)


def parse_flight(path: Path) -> dict | None:
    if not path.exists():
        return None
    rows = load_jsonl(path)
    if not rows:
        return None
    t0 = int(rows[0]["mono_ns"])
    toff = takeoff_mono(rows)
    dets, states, setpoints, race, v_body = [], [], [], [], []
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
                "elev": float(np.degrees(np.arctan2(-tvec[1], max(tvec[2], 1e-6)))),
                "cert": d.get("cert_status"),
                "center_px": d.get("center_px"),
            })
        elif topic == "state":
            gr = d.get("gate_rel")
            vw = d.get("v_world") or [0, 0, 0]
            states.append({
                "t_ff": t_ff, "t_rel": t_rel,
                "gate_rel": gr,
                "v_world": list(map(float, vw)),
                "age": d.get("gate_rel_age_s"),
            })
        elif topic == "setpoint":
            vb = d.get("v_body") or [0, 0, 0]
            setpoints.append({
                "t_ff": t_ff, "phase": d.get("phase"),
                "v_body": list(map(float, vb)),
            })
            if d.get("phase") == "commit":
                v_body.append({"t_ff": t_ff, "v": list(map(float, vb))})
        elif topic == "race":
            race.append({
                "t_ff": t_ff,
                "active_gate_index": d.get("active_gate_index"),
                "gates_passed": d.get("gates_passed"),
            })
    return {
        "dets": dets, "states": states, "setpoints": setpoints,
        "race": race, "v_body_commit": v_body, "t0": t0, "takeoff": toff,
    }


def find_pass_t(log: dict) -> tuple[float | None, str]:
    prev = None
    for r in log["race"]:
        idx = r.get("active_gate_index")
        if idx is not None and prev is not None and idx > prev:
            return r["t_ff"], "hud"
        if idx is not None:
            prev = idx
    # state tz signflip
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
    # closest approach R
    best = None
    for s in log["states"]:
        gr = s.get("gate_rel")
        if gr is None:
            continue
        R = float(np.linalg.norm(gr["t"]))
        if R < 2.5 and (best is None or R < best[1]):
            best = (s["t_ff"], R)
    if best:
        return best[0], "closest_state"
    return None, "none"


def frozen_exit_bearing(log: dict, t_pass: float) -> dict | None:
    """Frozen exit bearing in the SAME frame as detection bearings.

    Detection bearings are camera-forward: atan2(tx, tz). Body FRD maps
    as x≈cam-z, y≈cam-x, so travel bearing atan2(v_by, v_bx) is
    commensurate. NEVER use v_world (NED) — that scrambled Q99 to ~160°.

    Prefer: (1) body travel from setpoints, (2) gate-1 LOS from state
    (straight-dash proxy), both in the final EXIT_WINDOW_S.
    """
    travel = []
    for sp in log["setpoints"]:
        if t_pass - EXIT_WINDOW_S <= sp["t_ff"] <= t_pass and sp.get("v_body"):
            vx, vy = sp["v_body"][0], sp["v_body"][1]
            # FORWARD only — retreat (vx<0) yields ~±180° and poisoned Q99
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
            "spread_deg": float(np.percentile(travel, 90)
                                - np.percentile(travel, 10)),
        }
    if los:
        return {
            "bearing_deg": float(np.median(los)),
            "source": "gate1_los_median",
            "n": len(los),
            "spread_deg": float(np.percentile(los, 90)
                                - np.percentile(los, 10)) if len(los) > 1 else 0.0,
        }
    if travel:
        return {
            "bearing_deg": float(np.median(travel)),
            "source": "body_travel_sparse",
            "n": len(travel),
        }
    return None


def pre_cross_gate2_visible(dets: list[dict], t_pass: float,
                            lookback_s: float = 3.0) -> dict:
    """Gate-2 visibility: far det in [3,12] concurrent with near det R<2."""
    window = [d for d in dets if t_pass - lookback_s <= d["t_ff"] <= t_pass]
    near = [d for d in window if d["R"] < NEAR_R]
    far = [d for d in window if BANK_R[0] <= d["R"] <= BANK_R[1]]
    concurrent = 0
    far_at_near = []
    for n in near:
        mates = [f for f in far if abs(f["t_ff"] - n["t_ff"]) <= 0.2]
        if mates:
            concurrent += 1
            far_at_near.extend(mates)
    # unique far samples by rounding t
    uniq = {}
    for f in far_at_near:
        uniq[round(f["t_ff"], 2)] = f
    return {
        "visible": concurrent > 0,
        "n_concurrent_windows": concurrent,
        "n_far_unique": len(uniq),
        "far_samples": list(uniq.values()),
        "n_near": len(near),
        "n_far_in_window": len(far),
    }


def true_successor_at_crossing(dets: list[dict], t_pass: float,
                               exit_bearing: float) -> dict | None:
    """Best estimate of gate-2 at crossing: far det nearest in time with
    R in [3,12], preferring angular proximity to exit vector among
    persistent tracks. For post-pass validation also peek +0.5s."""
    cands = [d for d in dets
             if t_pass - 0.3 <= d["t_ff"] <= t_pass + 0.5
             and BANK_R[0] <= d["R"] <= BANK_R[1]]
    if not cands:
        cands = [d for d in dets
                 if t_pass - 0.5 <= d["t_ff"] <= t_pass + 1.0
                 and 2.5 <= d["R"] <= 15.0]
    if not cands:
        return None
    # Prefer candidates in forward half-space relative to exit
    scored = []
    for d in cands:
        err = abs(ang_diff(d["bearing"], exit_bearing))
        scored.append((err, abs(d["t_ff"] - t_pass), d))
    scored.sort(key=lambda x: (x[0], x[1]))
    best = scored[0][2]
    # Ambiguity: second candidate within 8° of first but >5° from exit?
    rivals = [s[2] for s in scored[1:4]
              if abs(ang_diff(s[2]["bearing"], best["bearing"])) > 5.0]
    return {
        "det": best,
        "bearing_deg": best["bearing"],
        "R": best["R"],
        "elev_deg": best["elev"],
        "error_vs_exit_deg": ang_diff(best["bearing"], exit_bearing),
        "n_cands": len(cands),
        "rival_bearings": [r["bearing"] for r in rivals[:3]],
        "ambiguous": len(rivals) > 0 and any(
            abs(ang_diff(r["bearing"], exit_bearing)) < 20 for r in rivals),
    }


def bank_errors(far_samples: list[dict], exit_bearing: float,
                cross_bearing: float | None) -> list[dict]:
    rows = []
    for f in far_samples:
        err_exit = ang_diff(f["bearing"], exit_bearing)
        err_cross = (ang_diff(f["bearing"], cross_bearing)
                     if cross_bearing is not None else None)
        rows.append({
            "t_ff": f["t_ff"], "R": f["R"], "bearing": f["bearing"],
            "elev": f["elev"],
            "error_vs_exit_deg": err_exit,
            "abs_error_vs_exit_deg": abs(err_exit),
            "error_vs_cross_truth_deg": err_cross,
            "abs_error_vs_cross_truth_deg": (
                abs(err_cross) if err_cross is not None else None),
        })
    return rows


def resolve_log_path(fid: str, fixture_path: str | None) -> Path | None:
    candidates = []
    if fixture_path:
        candidates.append(Path(fixture_path) / f"{fid}-flight.jsonl")
    candidates.append(FIX / "**" )  # placeholder
    # search fixtures
    for root in (FIX, SIB):
        if not root.exists():
            continue
        hits = list(root.glob(f"**/{fid}-flight.jsonl"))
        if hits:
            return hits[0]
    # logs
    logp = Path(r"C:\Users\tsion\Projects\eni_dcim\logs") / fid / "flight.jsonl"
    if logp.exists():
        return logp
    return None


def collect_flights() -> list[dict]:
    """Prefer inventory; always include known pass flights."""
    flights = []
    seen = set()
    if INV.exists():
        inv = json.loads(INV.read_text(encoding="utf-8"))
        for fx in inv.get("fixtures") or []:
            for fl in fx.get("flights") or []:
                fid = fl["id"]
                # Include close approaches or multi-gate or passes
                if (fl.get("gates", 0) >= 1
                        or (fl.get("multi_gate_windows") or 0) > 0
                        or (fl.get("closest_direct_r") or 99) < 2.0
                        or (fl.get("closest_state_r") or 99) < 1.5):
                    if fid in seen:
                        continue
                    seen.add(fid)
                    flights.append({
                        "fid": fid,
                        "fixture": fx["fixture"],
                        "fixture_path": fx.get("path"),
                        "gates": fl.get("gates"),
                        "multi_gate_windows": fl.get("multi_gate_windows"),
                    })
    # Ensure phase6h / phase6i passes
    for fid, fx in [
        ("20260719T160537-f170ead6", "20260719T164956-phase6h-first-enable"),
        ("20260719T163649-f170ead6", "20260719T164956-phase6h-first-enable"),
        ("20260719T200816-f170ead6", "20260719T204430-phase6i-r-rate-ab"),
        ("20260719T201851-50f9dcc8", "20260719T204430-phase6i-r-rate-ab"),
        ("20260716T131137-2ca531c3", "20260716T132549-phase3j-r2training-rerun"),
        ("20260719T134326-2477345e", "20260719T134835-phase6d-fiction-guards"),
    ]:
        if fid not in seen:
            seen.add(fid)
            flights.append({"fid": fid, "fixture": fx, "fixture_path": None,
                            "gates": None, "multi_gate_windows": None})
    return flights


def analyze_one(meta: dict) -> dict | None:
    path = resolve_log_path(meta["fid"], meta.get("fixture_path"))
    if path is None:
        return {"fid": meta["fid"], "error": "log_not_found"}
    log = parse_flight(path)
    if log is None or len(log["dets"]) < 5:
        return {"fid": meta["fid"], "error": "sparse_log", "path": str(path)}
    t_pass, src = find_pass_t(log)
    if t_pass is None:
        return {"fid": meta["fid"], "error": "no_approach_anchor", "path": str(path)}

    exit_info = frozen_exit_bearing(log, t_pass)
    if exit_info is None:
        return {"fid": meta["fid"], "error": "no_exit_vector", "t_pass": t_pass}

    vis = pre_cross_gate2_visible(log["dets"], t_pass)
    succ = true_successor_at_crossing(
        log["dets"], t_pass, exit_info["bearing_deg"])
    cross_bearing = succ["bearing_deg"] if succ else None
    banks = bank_errors(vis["far_samples"], exit_info["bearing_deg"],
                        cross_bearing)

    # Primary error for cone: |bearing(true successor at crossing) - exit|
    cross_err = succ["error_vs_exit_deg"] if succ else None
    # Bank-time errors (each far sample vs exit)
    bank_abs = [b["abs_error_vs_exit_deg"] for b in banks]

    return {
        "fid": meta["fid"],
        "fixture": meta.get("fixture"),
        "path": str(path),
        "t_pass_ff": t_pass,
        "pass_source": src,
        "exit": exit_info,
        "gate2_visible_pre_cross": vis["visible"],
        "visibility": {k: vis[k] for k in (
            "n_concurrent_windows", "n_far_unique", "n_near", "n_far_in_window")},
        "successor_at_crossing": ({
            k: succ[k] for k in (
                "bearing_deg", "R", "elev_deg", "error_vs_exit_deg",
                "n_cands", "rival_bearings", "ambiguous")
        } if succ else None),
        "cross_error_vs_exit_deg": cross_err,
        "abs_cross_error_deg": abs(cross_err) if cross_err is not None else None,
        "bank_samples": banks,
        "bank_abs_errors_deg": bank_abs,
        "n_dets": len(log["dets"]),
    }


def cone_stats(errors: list[float], widths=(4, 6, 8, 10, 12, 15, 20)) -> dict:
    if not errors:
        return {"n": 0}
    a = np.asarray(errors, float)
    q99 = float(np.percentile(a, 99)) if len(a) >= 2 else float(a.max())
    out = {
        "n": int(a.size),
        "median": float(np.median(a)),
        "p90": float(np.percentile(a, 90)),
        "p95": float(np.percentile(a, 95)),
        "q99": q99,
        "max": float(a.max()),
        "mean": float(a.mean()),
        "q99_plus_2": q99 + 2.0,
        "hard_cap_deg": HARD_CAP_DEG,
        "KILL_BANK_PREDICTOR": (q99 + 2.0) > HARD_CAP_DEG,
        "recommended_cone_half_width": min(HARD_CAP_DEG, math.ceil(q99 + 2.0)),
    }
    # Per-width recall (fraction of true successors inside cone)
    for w in widths:
        out[f"recall_within_{w}deg"] = float(np.mean(a <= w))
    return out


def ambiguity_band(results: list[dict]) -> dict:
    """D7 ambiguity band: when ≥2 real far gates sit within the same
    angular neighborhood of the exit vector at crossing."""
    pairs = []
    for r in results:
        succ = r.get("successor_at_crossing")
        if not succ or not succ.get("rival_bearings"):
            continue
        e0 = abs(succ["error_vs_exit_deg"])
        for rb in succ["rival_bearings"]:
            e1 = abs(ang_diff(rb, r["exit"]["bearing_deg"]))
            sep = abs(ang_diff(succ["bearing_deg"], rb))
            pairs.append({
                "fid": r["fid"],
                "true_err": e0, "rival_err": e1, "sep_deg": sep,
                "both_inside_12": e0 <= 12 and e1 <= 12,
                "both_inside_8": e0 <= 8 and e1 <= 8,
            })
    if not pairs:
        return {"n_ambiguous_flights": 0, "band_deg": None,
                "note": "no rival-pair samples"}
    # Ambiguity band ≈ half-separation of closest rival pairs that both fit in 12°
    seps = [p["sep_deg"] for p in pairs if p["both_inside_12"]]
    return {
        "n_rival_pairs": len(pairs),
        "n_both_inside_12": sum(1 for p in pairs if p["both_inside_12"]),
        "n_both_inside_8": sum(1 for p in pairs if p["both_inside_8"]),
        "median_rival_sep_deg": float(np.median([p["sep_deg"] for p in pairs])),
        "ambiguity_band_halfwidth_deg": (
            float(np.median(seps)) / 2.0 if seps else None),
        "pairs": pairs[:20],
    }


def render(bundle: dict) -> str:
    s = bundle["stats"]
    lines = []
    lines.append("# D7 — banked-bearing errors (P1, sizes the S4 cone)")
    lines.append("")
    lines.append("Spec: `docs/design/intergate-segment.md` S4 §4 + §8C D7.")
    lines.append("Error = angle(true-successor bearing, FROZEN exit vector).")
    lines.append("Bank epoch: far detections R∈[3,12]m concurrent with "
                 "near R<2m in the 3s before gate-1 crossing/closest.")
    lines.append("")
    vis = bundle["visibility"]
    lines.append("## Pre-cross gate-2 visibility")
    lines.append("")
    lines.append(f"- Approaches scored: **{vis['n_approaches']}**")
    lines.append(f"- See gate 2 before crossing: **{vis['n_visible']}** "
                 f"({vis['fraction']*100:.1f}%)")
    lines.append("")
    lines.append("## Banked-bearing error vs frozen exit (at crossing)")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(s["cross_errors"], indent=2))
    lines.append("```")
    lines.append("")
    kill = s["cross_errors"].get("KILL_BANK_PREDICTOR")
    q99p2 = s["cross_errors"].get("q99_plus_2")
    if kill:
        lines.append(
            f"## ⚠ HARD CAP BREACH — KILL THE BANK PREDICTOR\n\n"
            f"**Q99+2° = {q99p2:.2f}° > {HARD_CAP_DEG}°.** "
            f"Per S4 design: this kills the bank predictor / moving-bridge "
            f"assumption, **not** the ±12° hard cap. Do not widen the cone."
        )
    else:
        lines.append(
            f"## Hard-cap check: PASS\n\n"
            f"Q99+2° = {q99p2:.2f}° ≤ {HARD_CAP_DEG}°. "
            f"Recommended cone half-width: "
            f"**±{s['cross_errors'].get('recommended_cone_half_width')}°**."
        )
    lines.append("")
    lines.append("## Bank-time errors (far samples at 3–12 m vs exit)")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(s["bank_errors"], indent=2))
    lines.append("```")
    lines.append("")
    lines.append("## D7 ambiguity band")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(bundle["ambiguity"], indent=2, default=str)[:3000])
    lines.append("```")
    lines.append("")
    lines.append("## Per-width recall (correct successor inside cone)")
    lines.append("")
    lines.append("| half-width | recall |")
    lines.append("|---:|---:|")
    for w in (4, 6, 8, 10, 12, 15, 20):
        k = f"recall_within_{w}deg"
        if k in s["cross_errors"]:
            lines.append(f"| ±{w}° | {s['cross_errors'][k]*100:.1f}% |")
    lines.append("")
    lines.append("## Per-flight table")
    lines.append("")
    lines.append("| fid | visible | exit° | cross_err° | R_succ | ambiguous |")
    lines.append("|---|---|---:|---:|---:|---|")
    for r in bundle["flights"]:
        if r.get("error"):
            lines.append(f"| `{r['fid']}` | — | — | — | — | err={r['error']} |")
            continue
        ce = r.get("cross_error_vs_exit_deg")
        ce_s = "" if ce is None else f"{ce:+.1f}"
        lines.append(
            f"| `{r['fid']}` | {r['gate2_visible_pre_cross']} | "
            f"{r['exit']['bearing_deg']:.1f} | "
            f"{ce_s} | "
            f"{(r.get('successor_at_crossing') or {}).get('R', '')} | "
            f"{(r.get('successor_at_crossing') or {}).get('ambiguous')} |"
        )
    lines.append("")
    lines.append("## Deliverables")
    lines.append("")
    lines.append("- `d7-banked-bearing.md`, `summary.json`, `per_flight.csv`, "
                 "`bank_samples.csv`")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    metas = collect_flights()
    results = []
    for i, m in enumerate(metas):
        print(f"[{i+1}/{len(metas)}] {m['fid']}", flush=True)
        results.append(analyze_one(m))

    ok = [r for r in results if not r.get("error")]
    visible = [r for r in ok if r.get("gate2_visible_pre_cross")]
    cross_errs = [r["abs_cross_error_deg"] for r in ok
                  if r.get("abs_cross_error_deg") is not None]
    # Prefer errors from flights that actually saw gate 2 AND used a
    # sane exit source (not retreat-poisoned).
    def _sane(r):
        src = (r.get("exit") or {}).get("source", "")
        return "travel" in src or "los" in src

    cross_vis = [r["abs_cross_error_deg"] for r in visible
                 if r.get("abs_cross_error_deg") is not None and _sane(r)]
    bank_errs = []
    for r in visible:
        bank_errs.extend(r.get("bank_abs_errors_deg") or [])

    # Primary: visible-only (the D7 population). Fallback: all sane.
    cross_sane = [r["abs_cross_error_deg"] for r in ok
                  if r.get("abs_cross_error_deg") is not None and _sane(r)]
    # Pass cohort: HUD gate-index advance — the S4-relevant population.
    PASS_FIDS = {
        "20260719T160537-f170ead6", "20260719T163649-f170ead6",
        "20260719T200816-f170ead6", "20260719T201851-50f9dcc8",
        "20260716T131137-2ca531c3",
    }
    pass_rows = [r for r in ok if r["fid"] in PASS_FIDS
                 and r.get("abs_cross_error_deg") is not None]
    cross_pass = [r["abs_cross_error_deg"] for r in pass_rows]
    # Primary for the HARD CAP: pass cohort if n>=3, else visible sane
    if len(cross_pass) >= 3:
        primary = cross_pass
        primary_name = "pass_cohort"
    elif len(cross_vis) >= 3:
        primary = cross_vis
        primary_name = "visible_only"
    else:
        primary = cross_sane
        primary_name = "sane_exit"
    stats = {
        "cross_errors": cone_stats(primary),
        "cross_errors_pass_cohort": cone_stats(cross_pass),
        "cross_errors_all_approaches": cone_stats(cross_errs),
        "cross_errors_visible_only": cone_stats(cross_vis),
        "cross_errors_sane_exit": cone_stats(cross_sane),
        "bank_errors": cone_stats(bank_errs),
        "pass_cohort_errors": [
            {"fid": r["fid"], "abs_err": r["abs_cross_error_deg"],
             "signed": r.get("cross_error_vs_exit_deg"),
             "visible": r.get("gate2_visible_pre_cross")}
            for r in pass_rows
        ],
    }
    # stash for bundle
    _primary_name = primary_name
    vis = {
        "n_approaches": len(ok),
        "n_visible": len(visible),
        "fraction": len(visible) / len(ok) if ok else 0.0,
        "n_errors": len(results) - len(ok),
    }
    amb = ambiguity_band(ok)

    bundle = {
        "stats": stats,
        "visibility": vis,
        "ambiguity": amb,
        "flights": results,
        "hard_cap_deg": HARD_CAP_DEG,
        "primary_error_set": _primary_name,
    }

    (OUT / "summary.json").write_text(
        json.dumps(bundle, indent=2, default=str), encoding="utf-8")

    with (OUT / "per_flight.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["fid", "fixture", "error", "t_pass_ff", "pass_source",
                  "gate2_visible_pre_cross", "exit_bearing",
                  "cross_error_vs_exit_deg", "abs_cross_error_deg",
                  "succ_R", "ambiguous"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in results:
            w.writerow({
                "fid": r.get("fid"), "fixture": r.get("fixture"),
                "error": r.get("error"),
                "t_pass_ff": r.get("t_pass_ff"),
                "pass_source": r.get("pass_source"),
                "gate2_visible_pre_cross": r.get("gate2_visible_pre_cross"),
                "exit_bearing": (r.get("exit") or {}).get("bearing_deg"),
                "cross_error_vs_exit_deg": r.get("cross_error_vs_exit_deg"),
                "abs_cross_error_deg": r.get("abs_cross_error_deg"),
                "succ_R": (r.get("successor_at_crossing") or {}).get("R"),
                "ambiguous": (r.get("successor_at_crossing") or {}).get("ambiguous"),
            })

    with (OUT / "bank_samples.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["fid", "t_ff", "R", "bearing", "elev",
                  "error_vs_exit_deg", "abs_error_vs_exit_deg",
                  "error_vs_cross_truth_deg"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in ok:
            for b in r.get("bank_samples") or []:
                w.writerow({"fid": r["fid"], **{
                    k: b.get(k) for k in fields if k != "fid"}})

    report = _render_fixed(bundle)
    (OUT / "d7-banked-bearing.md").write_text(report, encoding="utf-8")
    (ROOT / "analysis" / "2026-07-20-d7-banked-bearing.md").write_text(
        report, encoding="utf-8")

    print(json.dumps({
        "visibility": vis,
        "cross_errors": stats["cross_errors"],
        "bank_errors": stats["bank_errors"],
        "KILL": stats["cross_errors"].get("KILL_BANK_PREDICTOR"),
        "ambiguity_band": amb.get("ambiguity_band_halfwidth_deg"),
        "n_ok": len(ok),
    }, indent=2))
    return 0


def _render_fixed(bundle: dict) -> str:
    s = bundle["stats"]
    vis = bundle["visibility"]
    lines = [
        "# D7 — banked-bearing errors (P1, sizes the S4 cone)",
        "",
        "Spec: `docs/design/intergate-segment.md` S4 §4 + §8C D7.",
        "Error = `|angle(true-successor bearing, FROZEN exit vector)|` at "
        "gate-1 crossing (or closest approach). Bank epoch: far dets "
        "R∈[3,12]m concurrent with near R<2m in the 3s before crossing.",
        "",
        "## Pre-cross gate-2 visibility",
        "",
        f"- Approaches scored: **{vis['n_approaches']}**",
        f"- See gate 2 before crossing: **{vis['n_visible']}** "
        f"({100*vis['fraction']:.1f}%)",
        f"- Primary error set: `{bundle['primary_error_set']}`",
        "",
        "## Crossing error vs frozen exit (cone input)",
        "",
        "```json",
        json.dumps(s["cross_errors"], indent=2),
        "```",
        "",
    ]
    kill = s["cross_errors"].get("KILL_BANK_PREDICTOR")
    q99p2 = s["cross_errors"].get("q99_plus_2")
    if kill:
        lines += [
            "## HARD CAP BREACH — KILL THE BANK PREDICTOR",
            "",
            f"**Q99+2° = {q99p2:.2f}° > {HARD_CAP_DEG}°.** "
            "Per S4: this kills the bank predictor / moving-bridge "
            "assumption, **not** the ±12° hard cap. Do not widen the cone.",
            "",
        ]
    else:
        lines += [
            "## Hard-cap check: PASS",
            "",
            f"Q99+2° = {q99p2:.2f}° ≤ {HARD_CAP_DEG}°. "
            f"Recommended cone half-width: "
            f"**±{s['cross_errors'].get('recommended_cone_half_width')}°**.",
            "",
        ]
    lines += [
        "## Bank-time errors (3–12 m samples vs exit)",
        "",
        "```json",
        json.dumps(s["bank_errors"], indent=2),
        "```",
        "",
        "## D7 ambiguity band",
        "",
        "```json",
        json.dumps({k: v for k, v in bundle["ambiguity"].items()
                    if k != "pairs"}, indent=2, default=str),
        "```",
        "",
        "Rival pairs (first 12):",
        "",
        "| fid | true_err | rival_err | sep | both≤12 |",
        "|---|---:|---:|---:|---|",
    ]
    for p in (bundle["ambiguity"].get("pairs") or [])[:12]:
        lines.append(
            f"| `{p['fid']}` | {p['true_err']:.1f} | {p['rival_err']:.1f} | "
            f"{p['sep_deg']:.1f} | {p['both_inside_12']} |"
        )
    lines += [
        "",
        "## Per-width recall",
        "",
        "| half-width | recall |",
        "|---:|---:|",
    ]
    for w in (4, 6, 8, 10, 12, 15, 20):
        k = f"recall_within_{w}deg"
        if k in s["cross_errors"]:
            lines.append(f"| ±{w}° | {100*s['cross_errors'][k]:.1f}% |")
    lines += [
        "",
        "## Per-flight",
        "",
        "| fid | visible | exit° | cross_err° | R_succ | ambig |",
        "|---|---|---:|---:|---:|---|",
    ]
    for r in bundle["flights"]:
        if r.get("error"):
            lines.append(f"| `{r['fid']}` | — | — | — | — | {r['error']} |")
            continue
        ce = r.get("cross_error_vs_exit_deg")
        ce_s = "" if ce is None else f"{ce:+.1f}"
        succ = r.get("successor_at_crossing") or {}
        lines.append(
            f"| `{r['fid']}` | {r.get('gate2_visible_pre_cross')} | "
            f"{r['exit']['bearing_deg']:.1f} | {ce_s} | "
            f"{succ.get('R', '')} | {succ.get('ambiguous')} |"
        )
    lines += [
        "",
        "## Implication for S4",
        "",
        f"- Cone half-width := min(12, ceil(Q99+2)) = "
        f"**±{s['cross_errors'].get('recommended_cone_half_width')}°**",
        f"- KILL_BANK_PREDICTOR = **{kill}**",
        "- Ribbon stays a D7-band tie-breaker only (build 1).",
        "",
        "## Deliverables",
        "",
        "- `d7-banked-bearing.md`, `summary.json`, `per_flight.csv`, "
        "`bank_samples.csv`",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
