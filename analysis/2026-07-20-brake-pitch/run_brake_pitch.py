"""P3 — Brake-pitch columns on loss-frame table (cohorts 1–3).

Add {pitch_att at loss, gate bbox bottom row, exit border} and adjudicate
whether nose-up/brake pitch correlates with bottom-edge exit in the
3–4.5 m loss band (R_drop: bottom-exit @ 3.7 m for 6°, 4.5 m for 8° at
honest 11.2° camera elevation).
"""
from __future__ import annotations

import csv
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
    COHORT1, COHORT2, load_flight, find_vision_death, analyze_one,
    first_commit_window, fov_class, IMG_H, IMG_W,
)

# Cohort 3 = phase6l Block-B / endpoints set
COHORT3 = {
    "label": "cohort3_phase6l",
    "fixture": ROOT / "fixtures" / "20260720T071602-phase6l-cohort-3",
    "flights": [
        {"slot": 1, "arm": "control", "fid": "20260720T071008-5b501b4c"},
        {"slot": 2, "arm": "live", "fid": "20260720T071112-cd18c5fb"},
        {"slot": 3, "arm": "control", "fid": "20260720T071220-5b501b4c"},
        {"slot": 4, "arm": "live", "fid": "20260720T071333-cd18c5fb"},
        {"slot": 5, "arm": "control", "fid": "20260720T071439-5b501b4c"},
        {"slot": 6, "arm": "live", "fid": "20260720T071545-cd18c5fb"},
    ],
}

CAM_ELEV_DEG = 11.2
# R_drop predictions (think-tank): bottom exit range vs additional nose-up
R_DROP = {6.0: 3.7, 8.0: 4.5}
LOSS_BAND = (3.0, 4.5)


def quat_pitch_deg(q) -> float:
    w, x, y, z = map(float, q)
    sinp = max(-1.0, min(1.0, 2 * (w * y - z * x)))
    return math.asin(sinp) * 180 / math.pi


def bbox_bottom_row(corners) -> float | None:
    if corners is None:
        return None
    pts = np.asarray(corners, float).reshape(-1, 2)
    if pts.size == 0:
        return None
    return float(pts[:, 1].max())


def exit_border(touches: list[str]) -> str:
    has_b = "bottom" in touches or "near_bottom" in touches
    has_s = any(t in touches for t in
                ("left", "right", "near_left", "near_right"))
    if has_b and not has_s:
        return "bottom"
    if has_s and not has_b:
        return "side"
    if has_b and has_s:
        return "bottom+side"
    return "none"


def nearest_state(states, t):
    if not states:
        return None
    return min(states, key=lambda s: abs(s["t_ff"] - t))


def enrich_flight(cohort_label: str, fixture: Path, meta: dict) -> dict:
    out = analyze_one(meta, fixture, do_frames=False)
    if out.get("error"):
        return {**meta, "cohort": cohort_label, "error": out["error"]}

    path = fixture / f"{meta['fid']}-flight.jsonl"
    if not path.exists():
        alt = (Path(r"C:\Users\tsion\Projects\eni_dcim") / "fixtures"
               / fixture.name / path.name)
        path = alt if alt.exists() else path
    log = load_flight(path)

    vd = out.get("vision_death") or {}
    loss_t = vd.get("loss_t_ff")
    last = vd.get("last_near_detection") or {}
    fov = vd.get("fov_at_last_near") or {}
    touches = list(fov.get("touches") or [])
    if not touches and last.get("corners_px") is not None:
        fov = fov_class(last.get("corners_px"), last.get("center_px"))
        touches = list(fov.get("touches") or [])

    # Pitch from q_att (level_pitch is frozen rest calibration −17.8°)
    t_ref = loss_t if loss_t is not None else last.get("t_ff")
    pitch = roll = None
    toff = log["takeoff"]
    best_dt = 1e9
    for r in log["rows"]:
        if r.get("topic") != "state" or t_ref is None:
            continue
        t_ff = (int(r["mono_ns"]) - toff) / 1e9
        dt = abs(t_ff - t_ref)
        if dt >= best_dt:
            continue
        q = (r.get("data") or {}).get("q_att")
        if not q:
            continue
        best_dt = dt
        pitch = quat_pitch_deg(q)
        w, x, y, z = map(float, q)
        sinr = 2 * (w * x + y * z)
        cosr = 1 - 2 * (x * x + y * y)
        roll = math.atan2(sinr, cosr) * 180 / math.pi

    st_loss = vd.get("state_at_loss") or {}
    R_loss = st_loss.get("R_believed")
    R_last = last.get("R")
    R_band = R_last if R_last is not None else R_loss
    bottom_row = bbox_bottom_row(last.get("corners_px"))
    if bottom_row is None and last.get("center_px"):
        bottom_row = float(last["center_px"][1])

    border = exit_border(touches)
    in_band = (R_band is not None and LOSS_BAND[0] <= R_band <= LOSS_BAND[1])
    # Brake nose-up: q_att pitch >= 3° (queued fix θ≤3–4°)
    brake_like = pitch is not None and pitch >= 3.0
    r_drop_pred = None
    if pitch is not None:
        if pitch >= 8.0:
            r_drop_pred = R_DROP[8.0]
        elif pitch >= 6.0:
            r_drop_pred = R_DROP[6.0]
        elif pitch >= 3.0:
            r_drop_pred = R_DROP[6.0]

    return {
        "cohort": cohort_label,
        "slot": meta["slot"],
        "arm": meta["arm"],
        "fid": meta["fid"],
        "loss_mode": out.get("loss_mode") or vd.get("loss_mode"),
        "loss_t_ff": loss_t,
        "R_last_near": R_last,
        "R_believed_at_loss": R_loss,
        "R_for_band": R_band,
        "in_3_4p5_band": in_band,
        "pitch_att_deg": pitch,
        "roll_att_deg": roll,
        "bbox_bottom_row": bottom_row,
        "exit_border": border,
        "fov_touches": touches,
        "brake_like_pitch_ge3": brake_like,
        "r_drop_pred_m": r_drop_pred,
        "vision_died_no_reacq": out.get("vision_died_no_reacq"),
        "center_px": last.get("center_px"),
    }


def adjudicate(rows: list[dict]) -> dict:
    band = [r for r in rows if r.get("in_3_4p5_band")
            and r.get("pitch_att_deg") is not None
            and r.get("exit_border")]
    if not band:
        return {
            "verdict": "FILE_CLOSES — insufficient 3–4.5m rows with pitch+border",
            "n_band": 0,
            "pitch_adjudicates": False,
            "queued_fix": False,
        }

    bottom = [r for r in band if "bottom" in (r.get("exit_border") or "")]
    side = [r for r in band if r.get("exit_border") == "side"]
    none = [r for r in band if r.get("exit_border") == "none"]

    pitch_bottom = [r["pitch_att_deg"] for r in bottom]
    pitch_other = [r["pitch_att_deg"] for r in band if r not in bottom]

    mean_b = float(np.mean(pitch_bottom)) if pitch_bottom else None
    mean_o = float(np.mean(pitch_other)) if pitch_other else None

    # Correlation test: bottom-exit rows should show higher nose-up pitch
    # AND R near R_drop prediction when pitch≥6.
    n_brake_bottom = sum(1 for r in bottom if r.get("brake_like_pitch_ge3"))
    n_brake_nonbottom = sum(
        1 for r in band if r not in bottom and r.get("brake_like_pitch_ge3"))

    # Adjudicate: pitch "adjudicates" if (a) bottom exits are enriched for
    # brake-like pitch vs non-bottom, AND (b) at least half of bottom exits
    # in-band have pitch≥3.
    enriched = (
        n_brake_bottom >= 1
        and (not pitch_other or (mean_b is not None and mean_o is not None
                                 and mean_b > mean_o + 1.0))
    )
    frac_brake_among_bottom = (
        n_brake_bottom / len(bottom) if bottom else 0.0
    )
    # Also check: many bottom exits at low pitch ⇒ FOV geometry not brake
    low_pitch_bottom = sum(1 for r in bottom if r["pitch_att_deg"] < 3.0)

    if not bottom:
        verdict = ("FILE_CLOSES — no bottom-edge exits in 3–4.5m band; "
                   "brake-pitch hypothesis has no support from this table")
        adj = False
    elif frac_brake_among_bottom >= 0.5 and enriched:
        verdict = ("PITCH_ADJUDICATES — nose-up/brake pitch enriched on "
                   "bottom-edge exits in 3–4.5m; queued fix "
                   "(decel by 5–6m, θ≤3–4° through commit) is next build")
        adj = True
    elif low_pitch_bottom >= max(1, len(bottom) // 2):
        verdict = ("FILE_CLOSES — bottom-edge exits occur without brake "
                   "nose-up (pitch<3° majority); FOV/geometry dominates; "
                   "queued brake-pitch fix not justified by this table")
        adj = False
    else:
        verdict = ("FILE_CLOSES — mixed/weak pitch↔bottom correlation; "
                   "does not clear the bar for the queued planner fix")
        adj = False

    return {
        "verdict": verdict,
        "pitch_adjudicates": adj,
        "queued_fix": adj,
        "n_band": len(band),
        "n_bottom": len(bottom),
        "n_side": len(side),
        "n_none": len(none),
        "mean_pitch_bottom": mean_b,
        "mean_pitch_nonbottom": mean_o,
        "n_brake_bottom": n_brake_bottom,
        "n_brake_nonbottom": n_brake_nonbottom,
        "frac_brake_among_bottom": frac_brake_among_bottom,
        "r_drop_ref": R_DROP,
        "cam_elev_deg": CAM_ELEV_DEG,
    }


def main() -> None:
    cohorts = [
        ("cohort1", COHORT1),
        ("cohort2", COHORT2),
        ("cohort3", COHORT3),
    ]
    rows = []
    for label, co in cohorts:
        for meta in co["flights"]:
            print(f"… {label} {meta['fid']}", flush=True)
            rows.append(enrich_flight(label, co["fixture"], meta))

    adj = adjudicate(rows)
    summary = {
        "ask": "brake-pitch columns on loss-frame table (cohorts 1–3)",
        "cam_elev_deg": CAM_ELEV_DEG,
        "r_drop_predictions_m": R_DROP,
        "loss_band_m": LOSS_BAND,
        "adjudication": adj,
        "rows": rows,
    }
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8")

    fields = [
        "cohort", "slot", "arm", "fid", "loss_mode", "loss_t_ff",
        "R_last_near", "R_believed_at_loss", "in_3_4p5_band",
        "pitch_att_deg", "bbox_bottom_row", "exit_border",
        "brake_like_pitch_ge3", "r_drop_pred_m",
    ]
    with (OUT / "loss_frame_brake_pitch.csv").open(
            "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

    lines = [
        "# Brake-pitch adjudication (cohorts 1–3)",
        "",
        f"**Verdict:** {adj['verdict']}",
        "",
        f"- pitch_adjudicates: **{adj['pitch_adjudicates']}**",
        f"- queued fix (decel 5–6m, θ≤3–4°): **{adj['queued_fix']}**",
        f"- n in 3–4.5m band with pitch+border: {adj['n_band']} "
        f"(bottom={adj['n_bottom']}, side={adj['n_side']}, none={adj['n_none']})",
        f"- mean pitch bottom vs other: "
        f"{adj.get('mean_pitch_bottom')} vs {adj.get('mean_pitch_nonbottom')}",
        "",
        f"R_drop ref (cam elev {CAM_ELEV_DEG}°): "
        f"6°→{R_DROP[6.0]}m, 8°→{R_DROP[8.0]}m.",
        "",
        "## Loss-frame table",
        "",
        "| cohort | slot | arm | R_near | pitch° | bbox_bottom | exit | brake≥3° | mode |",
        "|--------|-----:|-----|-------:|-------:|------------:|:----:|:--------:|------|",
    ]
    for r in rows:
        if r.get("error"):
            lines.append(
                f"| {r.get('cohort')} | {r.get('slot')} | {r.get('arm')} | "
                f"— | — | — | — | — | ERR |"
            )
            continue
        lines.append(
            f"| {r['cohort']} | {r['slot']} | {r['arm']} | "
            f"{(r.get('R_last_near') or float('nan')):.2f} | "
            f"{(r.get('pitch_att_deg') or float('nan')):.1f} | "
            f"{(r.get('bbox_bottom_row') or float('nan')):.0f} | "
            f"{r.get('exit_border')} | {r.get('brake_like_pitch_ge3')} | "
            f"{r.get('loss_mode')} |"
        )
    lines += [
        "",
        "Pitch is from `q_att` (live attitude). Logged `level_pitch` is "
        "the frozen rest calibration (−17.8°) and is **not** used.",
        "",
        "## Deliverables",
        "",
        "- `loss_frame_brake_pitch.csv`, `summary.json`, this report",
    ]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(adj, indent=2))


if __name__ == "__main__":
    main()
