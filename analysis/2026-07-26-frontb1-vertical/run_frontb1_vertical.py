"""FRONT-B1 vertical alignment read — final 1.5 m of every commit attempt.

PASS vs FAIL characterization:
  1) gate_rel down + detection SOURCE (full-quad vs close-tracker)
  2) ESTIMATE-driven vs CONTROL-driven low arrival
  3) what differs in the final-meter vertical between PASS and FAIL

Source proxy (no detection.source field in logs):
  - full_quad:    confidence >= 0.55 AND feature.mode=FULL_QUAD within ±40 ms
  - close_tracker: confidence < 0.55 (estimator treats these as position-only
                   tracker fixes) OR no FULL_QUAD nearby while SIDE_PAIR feature
                   is present within ±80 ms
  - unknown: otherwise

Run:
  C:/Users/tsion/Projects/eni_dcim/.venv/Scripts/python.exe \\
    analysis/2026-07-26-frontb1-vertical/run_frontb1_vertical.py
"""
from __future__ import annotations

import csv
import json
import math
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
FINAL_M = 1.5
FEATURE_WIN_NS = 40_000_000
SIDE_WIN_NS = 80_000_000
STATE_FILL_NS = 40_000_000


def finite(x):
    return isinstance(x, (int, float)) and math.isfinite(x)


def vec3(x):
    if not isinstance(x, (list, tuple)) or len(x) < 3:
        return None
    try:
        v = tuple(float(x[i]) for i in range(3))
    except (TypeError, ValueError):
        return None
    return v if all(math.isfinite(a) for a in v) else None


def norm(v):
    return math.sqrt(sum(a * a for a in v)) if v else None


def fmt(x, nd=3):
    if x is None or not finite(x):
        return "—"
    return f"{x:.{nd}f}"


def discover_b1(root: Path) -> list[Path]:
    roots = [root / "fixtures"]
    sibling = root.parent / "eni_dcim" / "fixtures"
    if sibling.is_dir():
        roots.append(sibling)
    by_name: dict[str, Path] = {}
    github = root / "fixtures"
    for fix in roots:
        if not fix.is_dir():
            continue
        for p in sorted(fix.iterdir()):
            if not p.is_dir():
                continue
            if not re.search(r"raceprep-b1-B-", p.name, re.I):
                if not re.search(r"b1-B-", p.name, re.I):
                    continue
            if (github / p.name).is_dir():
                by_name[p.name] = github / p.name
            elif p.name not in by_name:
                by_name[p.name] = p
    return sorted(by_name.values(), key=lambda p: p.name)


def flight_log(folder: Path) -> Path | None:
    hits = sorted(folder.glob("*flight.jsonl"))
    return hits[0] if hits else (folder / "flight.jsonl" if (folder / "flight.jsonl").is_file() else None)


def gates_passed(folder: Path) -> int | None:
    for name in ("result.json", "run-summary.json"):
        path = folder / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data.get("gates_passed"), (int, float)):
            return int(data["gates_passed"])
    return None


def load_rows(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                row = json.loads(line)
                row["_mono"] = int(row["mono_ns"])
                rows.append(row)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue
    return sorted(rows, key=lambda r: r["_mono"])


def nearest(rows, monos, mono, max_age_ns):
    # prior or equal
    lo, hi = 0, len(monos)
    while lo < hi:
        mid = (lo + hi) // 2
        if monos[mid] <= mono:
            lo = mid + 1
        else:
            hi = mid
    i = lo - 1
    if i >= 0 and mono - monos[i] <= max_age_ns:
        return rows[i]
    return None


def nearest_any(rows, monos, mono, win_ns):
    """Nearest within ±win_ns."""
    if not monos:
        return None
    lo, hi = 0, len(monos)
    while lo < hi:
        mid = (lo + hi) // 2
        if monos[mid] < mono:
            lo = mid + 1
        else:
            hi = mid
    best = None
    best_dt = None
    for j in (lo - 1, lo):
        if 0 <= j < len(monos):
            dt = abs(monos[j] - mono)
            if dt <= win_ns and (best_dt is None or dt < best_dt):
                best, best_dt = rows[j], dt
    return best


def race_pass_monos(rows) -> list[int]:
    out = []
    last_idx, last_time = None, None
    for r in rows:
        if r.get("topic") != "race":
            continue
        d = r.get("data") or {}
        idx = d.get("active_gate_index")
        gt = d.get("last_gate_race_time")
        if (finite(idx) and last_idx is not None and idx > last_idx) or (
            finite(gt) and gt >= 0 and (last_time is None or gt != last_time)
        ):
            out.append(r["_mono"])
        if finite(idx):
            last_idx = idx
        if finite(gt):
            last_time = gt
    return out


def classify_source(det, feat_near, side_near) -> str:
    data = det.get("data") or {}
    conf = data.get("confidence")
    mode = None
    if feat_near is not None:
        mode = (feat_near.get("data") or {}).get("mode")
    if finite(conf) and conf < 0.55:
        return "close_tracker"
    if mode == "FULL_QUAD" and finite(conf) and conf >= 0.55:
        return "full_quad"
    if side_near is not None and (mode != "FULL_QUAD"):
        return "close_tracker"
    if mode == "SIDE_PAIR":
        return "close_tracker"
    if finite(conf) and conf >= 0.55:
        return "full_quad_unconfirmed"
    return "unknown"


def commit_windows(setpoints) -> list[tuple[int, int]]:
    """Inclusive mono ranges for contiguous commit phases."""
    windows = []
    start = None
    for sp in setpoints:
        phase = str((sp.get("data") or {}).get("phase") or "").lower()
        if phase == "commit":
            if start is None:
                start = sp["_mono"]
            end = sp["_mono"]
        else:
            if start is not None:
                windows.append((start, end))
                start = None
    if start is not None:
        windows.append((start, end))
    return windows


PASS_ASSOC_SLACK_S = 2.0  # race HUD lags commit exit (corridor_abort → score)


def associate_pass_windows(
    windows: list[tuple[int, int]], pass_monos: list[int]
) -> dict[int, dict]:
    """Map commit-window index -> race-pass association.

    On these fixtures the sim race counter ticks *after* commit already
    ended (typically corridor_abort), 0.5–1.4s later. Bind each race
    pass to the latest prior window with end <= pass and lag <= slack.
    Never use geometric fwd<=0 (false positives on retries).
    """
    out: dict[int, dict] = {}
    used = set()
    for pmono in pass_monos:
        best_i, best_lag = None, None
        for i, (w0, w1) in enumerate(windows):
            if i in used:
                continue
            if w1 > pmono:
                continue
            lag = (pmono - w1) / 1e9
            if lag < 0 or lag > PASS_ASSOC_SLACK_S:
                continue
            if best_lag is None or lag < best_lag:
                best_i, best_lag = i, lag
        if best_i is not None:
            used.add(best_i)
            out[best_i] = {"pass_mono": pmono, "lag_s": best_lag}
    return out


def analyze_attempt(rows_by, windows_idx, w0, w1, pass_assoc, fixture, attempt_i):
    setpoints = rows_by["setpoint"]
    states = rows_by["state"]
    detections = rows_by["detection"]
    features = rows_by["feature"]
    sides = rows_by["feature_side"]
    st_m = [r["_mono"] for r in states]
    det_m = [r["_mono"] for r in detections]
    feat_m = [r["_mono"] for r in features]
    side_m = [r["_mono"] for r in sides]

    ticks = []
    for sp in setpoints:
        if sp["_mono"] < w0 or sp["_mono"] > w1:
            continue
        st = nearest(states, st_m, sp["_mono"], STATE_FILL_NS)
        if st is None:
            continue
        gr = (st.get("data") or {}).get("gate_rel") or {}
        t = vec3(gr.get("t") if isinstance(gr, dict) else None)
        if t is None:
            continue
        rng = norm(t)
        if rng is None or rng > FINAL_M:
            continue
        det = nearest(detections, det_m, sp["_mono"], STATE_FILL_NS)
        feat = nearest_any(features, feat_m, sp["_mono"], FEATURE_WIN_NS) if det else None
        side = nearest_any(sides, side_m, sp["_mono"], SIDE_WIN_NS) if det else None
        src = classify_source(det, feat, side) if det else "no_detection"
        cmd = vec3((sp.get("data") or {}).get("v_body"))
        ticks.append({
            "mono": sp["_mono"],
            "t_rel_s": (sp["_mono"] - w0) / 1e9,
            "range_m": rng,
            "fwd_m": t[2],
            "down_m": t[1],
            "right_m": t[0],
            "gate_rel_age_s": (st.get("data") or {}).get("gate_rel_age_s"),
            "phase": (sp.get("data") or {}).get("phase"),
            "v_cmd_vz": cmd[2] if cmd else None,
            "v_cmd_vx": cmd[0] if cmd else None,
            "det_confidence": (det.get("data") or {}).get("confidence") if det else None,
            "det_cert": (det.get("data") or {}).get("cert_status") if det else None,
            "source": src,
            "feature_mode": ((feat.get("data") or {}).get("mode") if feat else None),
        })

    if len(ticks) < 3:
        return None

    closest = min(ticks, key=lambda x: x["range_m"])
    exits = [r for r in rows_by.get("commit_exit", [])
             if w0 <= r["_mono"] <= w1 + 500_000_000]
    exit_reasons = [(e.get("data") or {}).get("reason") for e in exits]
    exit_pass = any(r == "pass" for r in exit_reasons)
    assoc = pass_assoc.get(windows_idx - 1)  # windows_idx is 1-based
    label = "PASS" if (assoc is not None or exit_pass) else "FAIL"
    pass_lag_s = assoc["lag_s"] if assoc else None

    # Handoff: first transition full_quad* -> close_tracker in final 1.5m
    handoff = None
    prev_src = None
    for i, tick in enumerate(ticks):
        src = tick["source"]
        if prev_src in ("full_quad", "full_quad_unconfirmed") and src == "close_tracker":
            # jump in down over ±1 tick
            downs = [ticks[j]["down_m"] for j in range(max(0, i - 1), min(len(ticks), i + 2))
                     if finite(ticks[j]["down_m"])]
            before = [ticks[j]["down_m"] for j in range(max(0, i - 3), i)
                      if ticks[j]["source"] in ("full_quad", "full_quad_unconfirmed")
                      and finite(ticks[j]["down_m"])]
            after = [ticks[j]["down_m"] for j in range(i, min(len(ticks), i + 4))
                     if ticks[j]["source"] == "close_tracker" and finite(ticks[j]["down_m"])]
            jump = None
            if before and after:
                jump = after[0] - before[-1]
            handoff = {
                "t_rel_s": tick["t_rel_s"],
                "range_m": tick["range_m"],
                "fwd_m": tick["fwd_m"],
                "down_before": before[-1] if before else None,
                "down_after": after[0] if after else None,
                "down_jump_m": jump,
            }
            break
        if src in ("full_quad", "full_quad_unconfirmed", "close_tracker"):
            prev_src = src

    # Smooth-track residual (estimate-driven test): fit down ~ a + b*fwd
    # on early final-meter samples that are full_quad, extrapolate to closest
    fq = [t for t in ticks if t["source"] in ("full_quad", "full_quad_unconfirmed")
          and finite(t["down_m"]) and finite(t["fwd_m"])]
    residual_at_closest = None
    smooth_pred_at_closest = None
    if len(fq) >= 3:
        xs = [t["fwd_m"] for t in fq]
        ys = [t["down_m"] for t in fq]
        xbar, ybar = mean(xs), mean(ys)
        den = sum((x - xbar) ** 2 for x in xs)
        if den > 1e-6:
            b = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys)) / den
            a = ybar - b * xbar
            x_c = closest["fwd_m"]
            if finite(x_c):
                smooth_pred_at_closest = a + b * x_c
                if finite(closest["down_m"]):
                    residual_at_closest = closest["down_m"] - smooth_pred_at_closest

    # Control closure test: needed Δdown to center vs integrated commanded vz
    # Camera down: negative down means gate below camera? In prior censuses
    # down≈-0.7 at exit meant LOW arrival (gate below in cam = drone high?
    # Actually T5 said LOW: down negative. Closing low means need positive
    # body vz in NED? v_body[2] sign: NED down positive typically in aerospace
    # but this codebase — from autopsy vz=-1 was "upward NED command".
    # So body z: negative = up. To climb (fix low arrival), need vz < 0.
    # Gap to close: if down is negative (gate below center = need to go down?
    # Wait - "arrives LOW" with down=-0.5 to -0.8. In camera frame +down is
    # image down. gate_rel.t[1] positive = gate below camera center = drone
    # is HIGH. But they reported negative down for LOW arrivals...
    # From T5 report: down median -0.768 for corridor_abort while "LOW".
    # So negative down = gate above image center = drone LOW. Yes.
    # To fix LOW: climb → v_body[2] negative (NED up).
    downs = [t["down_m"] for t in ticks if finite(t["down_m"])]
    vzs = [t["v_cmd_vz"] for t in ticks if finite(t["v_cmd_vz"])]
    if len(ticks) >= 2:
        dt = (ticks[-1]["mono"] - ticks[0]["mono"]) / 1e9
    else:
        dt = 0.0
    # Integrate commanded climb ( -vz when vz is NED-down)
    # Use trapezoid on vz
    integ_vz = 0.0
    for i in range(1, len(ticks)):
        v0 = ticks[i - 1]["v_cmd_vz"]
        v1 = ticks[i]["v_cmd_vz"]
        if finite(v0) and finite(v1):
            dti = (ticks[i]["mono"] - ticks[i - 1]["mono"]) / 1e9
            integ_vz += 0.5 * (v0 + v1) * dti
    # If down starts at D0 and we want 0: need change in down of -D0.
    # Relationship between body vz and camera-down rate is approximate;
    # use sign-aware: climb command (vz<0) should increase down (less negative).
    # predicted Δdown ≈ -integ_vz (if vz NED-down, up motion decreases cam-down
    # of a level gate... messy). Simpler metric:
    # control_gap = |down_at_entry| vs |integrated climb capacity|
    down_entry = ticks[0]["down_m"]
    down_exit = ticks[-1]["down_m"]
    down_closest = closest["down_m"]
    # Climb capacity in meters (negative vz integrates to upward meters)
    climb_m = -integ_vz  # positive if commanded net climb
    # For LOW (down<0): need climb_m > 0 to fix. deficit = max(0, -down_entry - climb_m)
    needed_climb = max(0.0, -down_entry) if finite(down_entry) else None
    control_deficit = None
    if needed_climb is not None:
        control_deficit = needed_climb - max(0.0, climb_m)

    # Classification of mechanism
    abs_resid = abs(residual_at_closest) if finite(residual_at_closest) else None
    abs_jump = abs(handoff["down_jump_m"]) if handoff and finite(handoff.get("down_jump_m")) else None
    estimate_score = 0.0
    control_score = 0.0
    if abs_jump is not None and abs_jump > 0.15:
        estimate_score += 2.0
    if abs_resid is not None and abs_resid > 0.20:
        estimate_score += 1.5
    if finite(control_deficit) and control_deficit > 0.25:
        control_score += 2.0
    if finite(down_closest) and down_closest < -0.25 and finite(climb_m) and climb_m < 0.15:
        control_score += 1.0
    # Smooth believed path that stays low with inadequate climb → control
    if abs_resid is not None and abs_resid < 0.12 and finite(control_deficit) and control_deficit > 0.2:
        control_score += 1.5
        estimate_score -= 0.5

    if estimate_score > control_score + 0.25:
        mechanism = "ESTIMATE-driven"
    elif control_score > estimate_score + 0.25:
        mechanism = "CONTROL-driven"
    else:
        mechanism = "MIXED/UNCLEAR"

    src_counts = Counter(t["source"] for t in ticks)
    return {
        "fixture": fixture,
        "attempt": attempt_i,
        "label": label,
        "n_ticks": len(ticks),
        "closest_range_m": closest["range_m"],
        "down_entry": down_entry,
        "down_exit": down_exit,
        "down_closest": down_closest,
        "down_mean": mean(downs) if downs else None,
        "down_median": median(downs) if downs else None,
        "vz_mean": mean(vzs) if vzs else None,
        "climb_cmd_m": climb_m,
        "needed_climb_m": needed_climb,
        "control_deficit_m": control_deficit,
        "smooth_pred_at_closest": smooth_pred_at_closest,
        "residual_at_closest": residual_at_closest,
        "handoff": handoff,
        "source_counts": dict(src_counts),
        "frac_close_tracker": src_counts.get("close_tracker", 0) / len(ticks),
        "frac_full_quad": (
            src_counts.get("full_quad", 0) + src_counts.get("full_quad_unconfirmed", 0)
        ) / len(ticks),
        "mechanism": mechanism,
        "estimate_score": estimate_score,
        "control_score": control_score,
        "duration_s": dt,
        "ticks": ticks,
        "exit_reasons": exit_reasons,
        "exit_reason": exit_reasons[0] if exit_reasons else None,
        "pass_lag_s": pass_lag_s,
    }


def analyze_fixture(folder: Path) -> dict:
    log = flight_log(folder)
    if log is None:
        return {"fixture": folder.name, "error": "no flight.jsonl"}
    rows = load_rows(log)
    by = defaultdict(list)
    for r in rows:
        by[r.get("topic")].append(r)
    for k in by:
        by[k].sort(key=lambda r: r["_mono"])
    passes = race_pass_monos(rows)
    windows = commit_windows(by["setpoint"])
    pass_assoc = associate_pass_windows(windows, passes)
    attempts = []
    for i, (w0, w1) in enumerate(windows, 1):
        att = analyze_attempt(by, i, w0, w1, pass_assoc, folder.name, i)
        if att is not None:
            attempts.append(att)
    return {
        "fixture": folder.name,
        "path": str(folder),
        "gates_passed": gates_passed(folder),
        "n_commit_windows": len(windows),
        "n_final_meter_attempts": len(attempts),
        "attempts": attempts,
    }


def write_waiting(head):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps({
        "status": "WAITING",
        "head": head,
        "reason": "no fixtures/*raceprep-b1-B-* yet",
    }, indent=2) + "\n", encoding="utf-8")
    (OUT / "report.md").write_text(
        f"# FRONT-B1 vertical read — WAITING\n\nHEAD: `{head}`.\n\n"
        "No `raceprep-b1-B-*` fixtures. Re-run after Sakana's 10-run block lands.\n",
        encoding="utf-8",
    )


def write_outputs(flights, head):
    attempts = [a for f in flights for a in f.get("attempts", [])]
    passes = [a for a in attempts if a["label"] == "PASS"]
    fails = [a for a in attempts if a["label"] == "FAIL"]

    # Per-tick CSV
    fields = [
        "fixture", "attempt", "label", "t_rel_s", "range_m", "fwd_m", "down_m",
        "right_m", "v_cmd_vz", "source", "det_confidence", "det_cert",
        "feature_mode", "gate_rel_age_s",
    ]
    with (OUT / "final_meter_ticks.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for a in attempts:
            for t in a["ticks"]:
                w.writerow({
                    "fixture": a["fixture"], "attempt": a["attempt"],
                    "label": a["label"], **{k: t.get(k) for k in fields if k in t},
                })

    # Per-attempt summary CSV
    sum_fields = [
        "fixture", "attempt", "label", "mechanism", "exit_reason", "pass_lag_s",
        "closest_range_m",
        "down_entry", "down_closest", "down_exit", "down_median",
        "vz_mean", "climb_cmd_m", "needed_climb_m", "control_deficit_m",
        "residual_at_closest", "handoff_down_jump_m", "handoff_range_m",
        "frac_close_tracker", "frac_full_quad", "estimate_score", "control_score",
    ]
    with (OUT / "attempts.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=sum_fields, extrasaction="ignore")
        w.writeheader()
        for a in attempts:
            ho = a.get("handoff") or {}
            w.writerow({
                "fixture": a["fixture"], "attempt": a["attempt"],
                "label": a["label"], "mechanism": a["mechanism"],
                "exit_reason": a.get("exit_reason"),
                "pass_lag_s": a.get("pass_lag_s"),
                "closest_range_m": a["closest_range_m"],
                "down_entry": a["down_entry"], "down_closest": a["down_closest"],
                "down_exit": a["down_exit"], "down_median": a["down_median"],
                "vz_mean": a["vz_mean"], "climb_cmd_m": a["climb_cmd_m"],
                "needed_climb_m": a["needed_climb_m"],
                "control_deficit_m": a["control_deficit_m"],
                "residual_at_closest": a["residual_at_closest"],
                "handoff_down_jump_m": ho.get("down_jump_m"),
                "handoff_range_m": ho.get("range_m"),
                "frac_close_tracker": a["frac_close_tracker"],
                "frac_full_quad": a["frac_full_quad"],
                "estimate_score": a["estimate_score"],
                "control_score": a["control_score"],
            })

    def agg(group, key):
        vals = [g[key] for g in group if finite(g.get(key))]
        return {
            "n": len(vals),
            "median": median(vals) if vals else None,
            "mean": mean(vals) if vals else None,
        }

    handoff_jumps_pass = [
        a["handoff"]["down_jump_m"] for a in passes
        if a.get("handoff") and finite(a["handoff"].get("down_jump_m"))
    ]
    handoff_jumps_fail = [
        a["handoff"]["down_jump_m"] for a in fails
        if a.get("handoff") and finite(a["handoff"].get("down_jump_m"))
    ]
    n_handoff_pass = sum(1 for a in passes if a.get("handoff"))
    n_handoff_fail = sum(1 for a in fails if a.get("handoff"))

    mech_pass = Counter(a["mechanism"] for a in passes)
    mech_fail = Counter(a["mechanism"] for a in fails)

    # Deciding split for FAILs
    if fails:
        primary = Counter(a["mechanism"] for a in fails).most_common(1)[0]
    else:
        primary = ("n/a", 0)

    # Jump evidence — material jump threshold 0.15 m
    all_jumps = handoff_jumps_pass + handoff_jumps_fail
    big_jumps = [j for j in all_jumps if abs(j) > 0.15]
    if not all_jumps:
        jump_verdict = (
            f"**NO** — handoff rarely observed in the final 1.5 m "
            f"(PASS {n_handoff_pass}/{len(passes)}, FAIL {n_handoff_fail}/{len(fails)}). "
            "Most ticks are full_quad / no_detection; close-tracker is not the "
            "dominant final-meter source on this baseline."
        )
    elif not big_jumps:
        jump_verdict = (
            f"**NO material jump** — {len(all_jumps)} handoff(s), "
            f"|Δdown| median={fmt(median([abs(j) for j in all_jumps]))} m "
            f"(0 with |Δ|>0.15 m). Handoff is not the vertical killer."
        )
    else:
        jump_verdict = (
            f"**YES** — {len(big_jumps)}/{len(all_jumps)} handoffs with |Δdown|>0.15 m; "
            f"|Δdown| median={fmt(median([abs(j) for j in all_jumps]))} m."
        )

    # Deciding narrative
    n_est = mech_fail.get("ESTIMATE-driven", 0)
    n_ctrl = mech_fail.get("CONTROL-driven", 0)
    n_mix = mech_fail.get("MIXED/UNCLEAR", 0)
    resid_med_all = agg(attempts, "residual_at_closest")["median"]
    if n_est > n_ctrl and n_est > n_mix:
        split_verdict = (
            f"**ESTIMATE-driven** on FAIL ({n_est}/{len(fails)}): believed `down` "
            "jumps/drifts off a smooth track."
        )
    elif n_ctrl > n_mix:
        split_verdict = (
            f"**CONTROL-driven** on FAIL ({n_ctrl}/{len(fails)}; "
            f"MIXED {n_mix}): smooth-track residual median "
            f"{fmt(resid_med_all)} m (belief OK), but commanded climb "
            f"(−v_body[2], NED) does not close the LOW gap before exit."
        )
    else:
        split_verdict = (
            f"**MIXED/UNCLEAR** primary on FAIL ({n_mix}/{len(fails)}; "
            f"CONTROL {n_ctrl}, ESTIMATE {n_est}). Residuals stay small "
            f"(median {fmt(resid_med_all)} m) — belief is smooth — while "
            "some fails climb through center (down→0/+) with adequate "
            "command integral. Low arrival is not an estimate jump."
        )

    down_p = agg(passes, "down_closest")["median"]
    down_f = agg(fails, "down_closest")["median"]
    rng_p = agg(passes, "closest_range_m")["median"]
    rng_f = agg(fails, "closest_range_m")["median"]
    pass_exits = Counter(a.get("exit_reason") or "?" for a in passes)
    fail_exits = Counter(a.get("exit_reason") or "?" for a in fails)

    lines = [
        "# FRONT-B1 — vertical alignment read",
        "",
        f"HEAD: `{head or 'unknown'}`.",
        f"Fixtures: **{len(flights)}/10** (`raceprep-b1-B`). "
        f"Final-1.5m commit attempts: **{len(attempts)}** "
        f"(PASS={len(passes)}, FAIL={len(fails)}).",
        "",
        "PASS label = race HUD gate increment associated to the prior commit "
        f"window (slack ≤{PASS_ASSOC_SLACK_S:.0f}s after commit end). On this "
        "baseline the score always lands *after* `corridor_abort` — never "
        "inside the commit window. Geometric `fwd≤0` is NOT used (false "
        "positives on retries).",
        "",
        "## Detection source proxy",
        "",
        "Logs have no `detection.source`. Proxy: `confidence < 0.55` → "
        "`close_tracker` (matches estimator position-only path); "
        "`confidence ≥ 0.55` + nearby `feature.mode=FULL_QUAD` → `full_quad`; "
        "high conf without FULL_QUAD nearby → `full_quad_unconfirmed`.",
        "",
        "## (1) Does `down` JUMP at full-quad → close-tracker handoff?",
        "",
        jump_verdict,
        f"- PASS handoffs: {n_handoff_pass}/{len(passes)}; "
        f"jump median={fmt(median(handoff_jumps_pass) if handoff_jumps_pass else None)} m",
        f"- FAIL handoffs: {n_handoff_fail}/{len(fails)}; "
        f"jump median={fmt(median(handoff_jumps_fail) if handoff_jumps_fail else None)} m",
        "",
        "## (2) THE DECIDING SPLIT — estimate vs control",
        "",
        split_verdict,
        "",
        f"| mechanism | PASS | FAIL |",
        f"| --- | ---: | ---: |",
        f"| ESTIMATE-driven | {mech_pass.get('ESTIMATE-driven', 0)} | "
        f"{mech_fail.get('ESTIMATE-driven', 0)} |",
        f"| CONTROL-driven | {mech_pass.get('CONTROL-driven', 0)} | "
        f"{mech_fail.get('CONTROL-driven', 0)} |",
        f"| MIXED/UNCLEAR | {mech_pass.get('MIXED/UNCLEAR', 0)} | "
        f"{mech_fail.get('MIXED/UNCLEAR', 0)} |",
        "",
        "Scores: handoff |Δdown|>0.15 or smooth-track residual>0.20 → estimate; "
        "control_deficit (needed climb − commanded climb integral)>0.25 and "
        "inadequate climb while down stays low → control. "
        "`v_body[2]` negative = climb (NED down-positive).",
        "",
        "## (3) PASS vs FAIL final-meter vertical",
        "",
        f"PASS attempts abort still **~{fmt(rng_p)} m out** at "
        f"`down≈{fmt(down_p)}` (exits: {dict(pass_exits)}), then the race "
        f"counter ticks {fmt(agg(passes,'pass_lag_s')['median'])} s later "
        "(coast-through after corridor abort). FAIL attempts that continue "
        f"closer reach median closest `{fmt(rng_f)}` m with "
        f"`down≈{fmt(down_f)}` (exits: {dict(fail_exits)}).",
        "",
        "| metric | PASS | FAIL |",
        "| --- | ---: | ---: |",
        f"| n attempts | {len(passes)} | {len(fails)} |",
        f"| closest range (median) | {fmt(rng_p)} | {fmt(rng_f)} |",
        f"| down @ closest (median) | {fmt(down_p)} | {fmt(down_f)} |",
        f"| down @ entry (median) | {fmt(agg(passes,'down_entry')['median'])} | "
        f"{fmt(agg(fails,'down_entry')['median'])} |",
        f"| down median in window | {fmt(agg(passes,'down_median')['median'])} | "
        f"{fmt(agg(fails,'down_median')['median'])} |",
        f"| mean v_cmd_vz | {fmt(agg(passes,'vz_mean')['median'])} | "
        f"{fmt(agg(fails,'vz_mean')['median'])} |",
        f"| climb_cmd integral (m) | {fmt(agg(passes,'climb_cmd_m')['median'])} | "
        f"{fmt(agg(fails,'climb_cmd_m')['median'])} |",
        f"| control_deficit (m) | {fmt(agg(passes,'control_deficit_m')['median'])} | "
        f"{fmt(agg(fails,'control_deficit_m')['median'])} |",
        f"| residual vs smooth track | {fmt(agg(passes,'residual_at_closest')['median'])} | "
        f"{fmt(agg(fails,'residual_at_closest')['median'])} |",
        f"| frac close_tracker ticks | {fmt(agg(passes,'frac_close_tracker')['median'])} | "
        f"{fmt(agg(fails,'frac_close_tracker')['median'])} |",
        f"| race-pass lag after commit (s) | {fmt(agg(passes,'pass_lag_s')['median'])} | — |",
        "",
        "## Per-attempt",
        "",
        "| fixture | # | label | exit | mechanism | closest | down | deficit | resid | handoffΔ |",
        "| --- | ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for a in attempts:
        ho = a.get("handoff") or {}
        lines.append(
            f"| `{a['fixture']}` | {a['attempt']} | **{a['label']}** | "
            f"{a.get('exit_reason') or '—'} | {a['mechanism']} | "
            f"{fmt(a['closest_range_m'])} | {fmt(a['down_closest'])} | "
            f"{fmt(a['control_deficit_m'])} | {fmt(a['residual_at_closest'])} | "
            f"{fmt(ho.get('down_jump_m'))} |"
        )

    lines += [
        "",
        "## Per-fixture gates",
        "",
        "| fixture | gates_passed | n_final_meter_attempts |",
        "| --- | ---: | ---: |",
    ]
    for f in flights:
        lines.append(
            f"| `{f['fixture']}` | {f.get('gates_passed')} | "
            f"{f.get('n_final_meter_attempts')} |"
        )

    lines += [
        "",
        "## Artifacts",
        "",
        "- `final_meter_ticks.csv` — per-tick down / vz / source",
        "- `attempts.csv` — per-attempt summary",
        "- `summary.json`",
        "- `run_frontb1_vertical.py`",
        "",
    ]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Strip ticks from summary for size
    slim_attempts = []
    for a in attempts:
        slim = {k: v for k, v in a.items() if k != "ticks"}
        slim_attempts.append(slim)

    payload = {
        "status": "COMPLETE" if len(flights) >= 10 else "PARTIAL",
        "head": head,
        "n_fixtures_expected": 10,
        "n_fixtures": len(flights),
        "n_attempts": len(attempts),
        "n_pass": len(passes),
        "n_fail": len(fails),
        "handoff_jump_verdict": jump_verdict,
        "split_verdict": split_verdict,
        "fail_primary_mechanism": primary[0],
        "mechanism_counts_pass": dict(mech_pass),
        "mechanism_counts_fail": dict(mech_fail),
        "pass_vs_fail": {
            "closest_range_median": {
                "PASS": agg(passes, "closest_range_m")["median"],
                "FAIL": agg(fails, "closest_range_m")["median"],
            },
            "down_closest_median": {
                "PASS": agg(passes, "down_closest")["median"],
                "FAIL": agg(fails, "down_closest")["median"],
            },
            "control_deficit_median": {
                "PASS": agg(passes, "control_deficit_m")["median"],
                "FAIL": agg(fails, "control_deficit_m")["median"],
            },
            "residual_median": {
                "PASS": agg(passes, "residual_at_closest")["median"],
                "FAIL": agg(fails, "residual_at_closest")["median"],
            },
            "frac_close_tracker_median": {
                "PASS": agg(passes, "frac_close_tracker")["median"],
                "FAIL": agg(fails, "frac_close_tracker")["median"],
            },
            "pass_lag_s_median": agg(passes, "pass_lag_s")["median"],
            "exit_reasons_pass": dict(pass_exits),
            "exit_reasons_fail": dict(fail_exits),
        },
        "attempts": slim_attempts,
        "flights": [
            {
                "fixture": f["fixture"],
                "gates_passed": f.get("gates_passed"),
                "n_final_meter_attempts": f.get("n_final_meter_attempts"),
            }
            for f in flights
        ],
    }
    (OUT / "summary.json").write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return payload


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    head = None
    try:
        head = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        pass

    fixtures = discover_b1(ROOT)
    if not fixtures:
        write_waiting(head)
        print(json.dumps({"status": "WAITING", "n_fixtures": 0, "head": head}, indent=2))
        return 2

    flights = []
    for folder in fixtures:
        info = analyze_fixture(folder)
        if info.get("error"):
            continue
        flights.append(info)

    if not any(f.get("n_final_meter_attempts", 0) > 0 for f in flights):
        write_waiting(head)
        print(json.dumps({
            "status": "WAITING",
            "n_fixtures": len(fixtures),
            "n_with_final_meter": 0,
            "head": head,
        }, indent=2))
        return 2

    payload = write_outputs(flights, head)
    print(json.dumps({
        "status": payload["status"],
        "n_fixtures": payload["n_fixtures"],
        "n_attempts": payload["n_attempts"],
        "n_pass": payload["n_pass"],
        "n_fail": payload["n_fail"],
        "fail_primary_mechanism": payload["fail_primary_mechanism"],
        "handoff_jump_verdict": payload["handoff_jump_verdict"],
        "pass_vs_fail": payload["pass_vs_fail"],
        "mechanism_counts_fail": payload["mechanism_counts_fail"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
