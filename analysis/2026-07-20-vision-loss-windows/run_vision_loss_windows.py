"""P2 — Vision-loss definitional check on phase6l.

F2/F4 show fresh px inside 1m yet 'vision past 3m' = fail.
Quantify loss-then-recover windows per flight:
  loss onset range, gap length, recovery range.
Also report vz std (expect 0.05–0.14 — damper killed the oscillator).
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

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "analysis" / "2026-07-20-vision-death-3m"))

from run_vision_death_3m import (  # noqa: E402
    load_flight, first_commit_window, analyze_one, BLIND_BUDGET_S,
    NEAR_R_MAX, FRAME_MARGIN, IMG_W, IMG_H,
)

FIX = ROOT / "fixtures" / "20260720T071602-phase6l-cohort-3"
FLIGHTS = [
    {"slot": 1, "arm": "control", "fid": "20260720T071008-5b501b4c"},
    {"slot": 2, "arm": "live", "fid": "20260720T071112-cd18c5fb"},
    {"slot": 3, "arm": "control", "fid": "20260720T071220-5b501b4c"},
    {"slot": 4, "arm": "live", "fid": "20260720T071333-cd18c5fb"},
    {"slot": 5, "arm": "control", "fid": "20260720T071439-5b501b4c"},
    {"slot": 6, "arm": "live", "fid": "20260720T071545-cd18c5fb"},
]

AGE_LOSS = 0.25
AGE_RECOVER = 0.10


def in_frame(center) -> bool:
    if not center:
        return False
    u, v = float(center[0]), float(center[1])
    return (FRAME_MARGIN <= u <= IMG_W - FRAME_MARGIN
            and FRAME_MARGIN <= v <= IMG_H - FRAME_MARGIN)


def loss_recover_windows(log: dict) -> list[dict]:
    """Find age-loss then recover episodes during/after first commit."""
    c0, c1 = first_commit_window(log["setpoints"])
    if c0 is None:
        return []
    states = [s for s in log["states"] if s["t_ff"] >= c0 - 0.1]
    windows = []
    loss_start = None
    loss_R = None
    loss_center = None
    for s in states:
        age = s["age"]
        bad = age is None or not math.isfinite(age) or age >= AGE_LOSS
        good = (age is not None and math.isfinite(age) and age <= AGE_RECOVER
                and s["R"] is not None and s["R"] < NEAR_R_MAX)
        if bad and loss_start is None:
            loss_start = s["t_ff"]
            loss_R = s["R"]
            loss_center = s.get("center_px")
        elif good and loss_start is not None:
            gap = s["t_ff"] - loss_start
            windows.append({
                "loss_t_ff": loss_start,
                "loss_onset_R": loss_R,
                "loss_center_px": loss_center,
                "loss_in_frame": in_frame(loss_center),
                "recover_t_ff": s["t_ff"],
                "recover_R": s["R"],
                "recover_center_px": s.get("center_px"),
                "gap_s": gap,
                "during_first_commit": (
                    c1 is None or loss_start <= (c1 + 0.5)),
            })
            loss_start = None
            loss_R = None
            loss_center = None
    # Unrecovered loss
    if loss_start is not None:
        windows.append({
            "loss_t_ff": loss_start,
            "loss_onset_R": loss_R,
            "loss_center_px": loss_center,
            "loss_in_frame": in_frame(loss_center),
            "recover_t_ff": None,
            "recover_R": None,
            "recover_center_px": None,
            "gap_s": None,
            "unrecovered": True,
            "during_first_commit": True,
        })
    return windows


def fresh_px_inside_1m(log: dict) -> dict:
    """Any certified/probation det with R<1 and age-fresh state nearby?"""
    hits = []
    for d in log["dets"]:
        if d["R"] is None or d["R"] >= 1.0:
            continue
        if d.get("cert") not in ("certified", "probation"):
            continue
        # nearest state age
        st = min(log["states"], key=lambda s: abs(s["t_ff"] - d["t_ff"]),
                 default=None)
        if st is None:
            continue
        age = st["age"]
        fresh = age is not None and math.isfinite(age) and age < 0.2
        if fresh and in_frame(d.get("center_px")):
            hits.append({
                "t_ff": d["t_ff"], "R": d["R"],
                "center_px": d.get("center_px"), "cert": d.get("cert"),
                "age": age,
            })
    return {
        "n_fresh_px_inside_1m": len(hits),
        "min_R": float(min(h["R"] for h in hits)) if hits else None,
        "samples": hits[:8],
    }


def vz_stats_commit(log: dict) -> dict:
    c0, c1 = first_commit_window(log["setpoints"])
    if c0 is None:
        return {"std": None}
    vz = []
    for s in log["states"]:
        if s["t_ff"] < c0:
            continue
        if c1 is not None and s["t_ff"] > c1:
            break
        if s.get("v_world"):
            vz.append(s["v_world"][2])
    if not vz:
        return {"std": None, "n": 0}
    a = np.asarray(vz, float)
    return {
        "n": len(a),
        "std": float(a.std()),
        "mean": float(a.mean()),
        "ptp": float(a.max() - a.min()),
        "damper_band_0p05_0p14": bool(0.05 <= a.std() <= 0.14),
    }


def endpoint_past_3m(log: dict) -> dict:
    """Replicate phase6l endpoint definition for comparison."""
    c0, c1 = first_commit_window(log["setpoints"])
    near = [d for d in log["dets"]
            if d["R"] is not None and d["R"] < 8
            and c0 is not None and c0 - 0.05 <= d["t_ff"] <= (c1 or c0 + 8)
            and d.get("cert") in ("certified", "probation")]
    det_min = min(near, key=lambda d: d["R"]) if near else None
    max_age = 0.0
    inf = False
    if c0 is not None:
        for s in log["states"]:
            if not (c0 <= s["t_ff"] <= (c1 or c0 + 8)):
                continue
            a = s["age"]
            if a is None or not math.isfinite(a) or a > 1e6:
                inf = True
                max_age = float("inf")
            else:
                max_age = max(max_age, a)
    blind = inf or max_age >= BLIND_BUDGET_S
    closest_R = det_min["R"] if det_min else None
    survived = bool(
        closest_R is not None and closest_R < 3.0 and not blind
        and det_min is not None and in_frame(det_min.get("center_px"))
    )
    return {
        "closest_R": closest_R,
        "blind": blind,
        "max_age": None if not math.isfinite(max_age) else max_age,
        "survived_past_3m_endpoint": survived,
        "why_fail": (
            None if survived else
            ("no_near_det" if closest_R is None else
             "blind_budget" if blind else
             "closest_R_ge_3" if closest_R >= 3.0 else
             "out_of_frame")
        ),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for meta in FLIGHTS:
        path = FIX / f"{meta['fid']}-flight.jsonl"
        if not path.exists():
            rows.append({**meta, "error": "missing"})
            continue
        log = load_flight(path)
        wins = loss_recover_windows(log)
        px = fresh_px_inside_1m(log)
        vz = vz_stats_commit(log)
        ep = endpoint_past_3m(log)
        vd = analyze_one(meta, FIX, do_frames=False)
        # Residual FOV driver: losses where onset center near edge
        fov_losses = [w for w in wins
                      if w.get("loss_center_px") and not w.get("loss_in_frame")]
        rows.append({
            **meta,
            "endpoint": ep,
            "fresh_px_lt_1m": px,
            "vz_commit": vz,
            "n_loss_recover_windows": len(wins),
            "windows": wins,
            "n_fov_edge_losses": len(fov_losses),
            "vision_died_analyzer": vd.get("vision_died_no_reacq"),
            "loss_mode": vd.get("loss_mode"),
            "definitional_tension": bool(
                px["n_fresh_px_inside_1m"] > 0
                and not ep["survived_past_3m_endpoint"]
            ),
        })

    summary = {
        "ask": "vision-loss definitional check — phase6l",
        "flights": rows,
        "note": (
            "Endpoint 'past 3m' requires closest det R<3 AND not blind "
            "in the WHOLE first commit. Fresh px inside 1m can coexist "
            "with a prior loss window (age≥0.25 then recover) — that is "
            "loss-then-recover, not continuous survival."
        ),
    }
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8")

    lines = [
        "# Vision-loss definitional check — phase6l",
        "",
        "## Verdict",
        "",
        summary["note"],
        "",
        "| slot | arm | past_3m | why_fail | fresh&lt;1m | min_R&lt;1 | "
        "n_L→R | fov_edge_losses | vz_std | vision_death |",
        "|---:|---|:---:|---|---:|---:|---:|---:|---:|:---:|",
    ]
    for r in rows:
        if r.get("error"):
            lines.append(f"| {r.get('slot')} | {r.get('arm')} | ERR | | | | | | | |")
            continue
        ep = r["endpoint"]
        px = r["fresh_px_lt_1m"]
        vz = r["vz_commit"]
        lines.append(
            f"| {r['slot']} | {r['arm']} | "
            f"{'Y' if ep['survived_past_3m_endpoint'] else 'n'} | "
            f"{ep.get('why_fail') or '—'} | "
            f"{px['n_fresh_px_inside_1m']} | "
            f"{px['min_R'] if px['min_R'] is not None else float('nan'):.2f} | "
            f"{r['n_loss_recover_windows']} | {r['n_fov_edge_losses']} | "
            f"{vz['std'] if vz['std'] is not None else float('nan'):.3f} | "
            f"{'Y' if r['vision_died_analyzer'] else 'n'} |"
        )

    lines += ["", "## Loss→recover windows", ""]
    for r in rows:
        if r.get("error"):
            continue
        lines.append(f"### F{r['slot']} `{r['fid']}` ({r['arm']})")
        lines.append("")
        if not r["windows"]:
            lines.append("- (none)")
            lines.append("")
            continue
        lines.append(
            "| loss_t | onset_R | gap_s | recover_R | in_frame_at_loss | unrecovered |"
        )
        lines.append("|---:|---:|---:|---:|:---:|:---:|")
        for w in r["windows"]:
            lines.append(
                f"| {w['loss_t_ff']:.2f} | "
                f"{w['loss_onset_R'] if w.get('loss_onset_R') is not None else float('nan'):.2f} | "
                f"{w['gap_s'] if w.get('gap_s') is not None else float('nan'):.2f} | "
                f"{w['recover_R'] if w.get('recover_R') is not None else float('nan'):.2f} | "
                f"{'Y' if w.get('loss_in_frame') else 'n'} | "
                f"{'Y' if w.get('unrecovered') else 'n'} |"
            )
        lines.append("")

    lines += [
        "## Method",
        "",
        f"Loss = age≥{AGE_LOSS}s; recover = age≤{AGE_RECOVER}s with R<{NEAR_R_MAX}.",
        "Endpoint past_3m = min certified/probation det R<3 in first commit "
        "AND max_age < blind budget 0.6s (whole commit).",
        "vz_std over commit v_world[2] — damper band 0.05–0.14.",
        "",
        f"Generated by `{OUT.name}/run_vision_loss_windows.py`.",
    ]
    text = "\n".join(lines)
    (OUT / "report.md").write_text(text, encoding="utf-8")
    (ROOT / "analysis" / "2026-07-20-vision-loss-windows.md").write_text(
        text, encoding="utf-8")
    print(json.dumps({
        "n_flights": len(rows),
        "definitional_tensions": [
            {"fid": r["fid"], "fresh_lt_1m": r["fresh_px_lt_1m"]["n_fresh_px_inside_1m"],
             "past_3m": r["endpoint"]["survived_past_3m_endpoint"],
             "why": r["endpoint"]["why_fail"],
             "n_windows": r["n_loss_recover_windows"],
             "vz_std": r["vz_commit"]["std"]}
            for r in rows if not r.get("error") and r.get("definitional_tension")
        ],
        "vz_stds": {r["fid"]: r["vz_commit"]["std"]
                    for r in rows if not r.get("error")},
    }, indent=2, default=str))


if __name__ == "__main__":
    main()
