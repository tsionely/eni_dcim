"""P1 — A8 re-extraction, CONTACT-INSTANT states only (RESPONSE16 §2).

Spec compliance:
  - Use the state sample nearest the collision mono (contact instant).
  - REJECT any sample whose state range disagrees with contact geometry
    (far belief, stale age, or |R_state − R_det| disagreement when a
    near detection exists).
  - Do NOT substitute detection-pose true_dz for the state (that was
    the prior rider's repair path; this pass is state-only).
  - Report n, both tails of (0.8 − true_dz) and of clearance deficit.
  - Cross-check against the mock collision model (reachable in-repo).

Chain remains HELD on h=0.62 until a contact-grade extraction lands.
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
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "analysis" / "2026-07-20-a8-half-extent"))

from aigp.core.messages import RelPose  # noqa: E402
from aigp.planning.approach import true_world_dz  # noqa: E402
from run_a8_half_extent import (  # noqa: E402
    OPENING_HALF_H, GRAZE_IMPULSE, TRY39_CLIP_TIMES,
    resolve_log, parse_flight, select_grazes, nearest,
)

# Contact geometry: a graze at the frame must see near-plane range.
# Opening half 0.8; clip annulus in mock goes out to 1.5× → ~1.2 m
# off-axis. Along-track, contact is near the plane → R typically <~2 m.
R_CONTACT_MAX = 2.0
AGE_MAX = 0.20
DT_STATE_MAX = 0.08
# If a near detection exists, state R must agree within this fraction/abs
R_AGREE_ABS = 0.75
R_AGREE_FRAC = 0.40

# Broaden search beyond the original 11 — still only graze-band contacts
FLIGHTS = [
    {
        "label": "phase6d_F1",
        "fid": "20260719T134326-2477345e",
        "fixture": "20260719T134835-phase6d-fiction-guards",
        "select": "all_graze",
    },
    {
        "label": "try39_clip_pair",
        "fid": "20260719T163649-f170ead6",
        "fixture": "20260719T164956-phase6h-first-enable",
        "select": "try39_pair",
    },
    {
        "label": "phase6c_F3",
        "fid": "20260719T121637-f186c83e",
        "fixture": "20260719T121704-phase6c-true-vertical",
        "select": "all_graze",
    },
    {
        "label": "phase6h_try15",
        "fid": "20260719T162247-f170ead6",
        "fixture": "20260719T164956-phase6h-first-enable",
        "select": "all_graze",
    },
    {
        "label": "phase6j_F4",
        "fid": "20260720T053745-5cebc2b2",
        "fixture": "20260720T054037-phase6j-block-a-cohort-2",
        "select": "all_graze",
    },
]


def scatter(vals: list[float]) -> dict:
    if not vals:
        return {"n": 0}
    a = np.asarray(vals, float)
    return {
        "n": int(len(a)),
        "min": float(a.min()),
        "max": float(a.max()),
        "mean": float(a.mean()),
        "std": float(a.std()),
        "median": float(np.median(a)),
        "p10": float(np.percentile(a, 10)),
        "p90": float(np.percentile(a, 90)),
        "values": [float(x) for x in a],
    }


def state_true_dz(st: dict) -> tuple[float | None, float | None, float | None]:
    """Return (true_dz, R, tz) from contact-instant state only."""
    gr = st.get("gate_rel")
    if not gr or gr.get("t") is None:
        return None, None, None
    t = list(map(float, gr["t"]))
    R = float(np.linalg.norm(t))
    nrm = gr.get("normal") or [0, 0, 1]
    tw = float(true_world_dz(
        RelPose(t=np.asarray(t, float), normal=np.asarray(nrm, float)),
        np.asarray(st["q_att"], float),
        float(st["level_roll"]), float(st["level_pitch"])))
    return tw, R, float(t[2])


def contact_geometry_ok(R_state: float | None, age: float | None,
                        dt: float | None, R_det: float | None) -> tuple[bool, str]:
    if R_state is None:
        return False, "REJECT_no_state_gate"
    if not math.isfinite(R_state) or R_state > R_CONTACT_MAX:
        return False, "REJECT_state_R_vs_contact_geom"
    if age is not None and (not math.isfinite(age) or age > AGE_MAX):
        return False, "REJECT_stale_state"
    if dt is not None and dt > DT_STATE_MAX:
        return False, "REJECT_state_too_far_from_collision_t"
    if R_det is not None and R_det <= R_CONTACT_MAX:
        # State must agree with near detection at contact
        tol = max(R_AGREE_ABS, R_AGREE_FRAC * max(R_det, R_state))
        if abs(R_state - R_det) > tol:
            return False, "REJECT_state_R_disagrees_with_det"
    return True, "ACCEPT_contact_instant_state"


def analyze_flight(meta: dict) -> dict:
    path = resolve_log(meta["fid"], meta["fixture"])
    if path is None:
        return {"label": meta["label"], "fid": meta["fid"], "error": "log_not_found"}
    log = parse_flight(path)
    grazes = select_grazes(meta, log["collisions"])
    rows = []
    for g in grazes:
        st = nearest(log["states"], g["t_ff"], max_dt=0.15)
        det = nearest([d for d in log["dets"] if d.get("R") and d["R"] < 4.0],
                      g["t_ff"], max_dt=0.2)
        if st is None:
            rows.append({
                "t_ff": g["t_ff"], "impulse": g["impulse"],
                "accepted": False, "reason": "REJECT_no_state",
            })
            continue
        tw, R_state, tz = state_true_dz(st)
        age = st.get("age")
        if isinstance(age, (int, float)):
            age = float(age)
        else:
            age = None
        dt = abs(st["t_ff"] - g["t_ff"])
        R_det = det["R"] if det else None
        ok, reason = contact_geometry_ok(R_state, age, dt, R_det)
        proxy = None if tw is None else (OPENING_HALF_H - tw)
        deficit = None if proxy is None else max(0.0, -proxy)
        # Tail label: HIGH contact (vehicle high / gate below) vs LOW
        tail = None
        if tw is not None:
            tail = "HIGH" if tw >= 0 else "LOW"
        rows.append({
            "flight": meta["label"],
            "fid": meta["fid"],
            "t_ff": g["t_ff"],
            "impulse": g["impulse"],
            "threat_level": g["threat_level"],
            "accepted": ok and tw is not None,
            "reason": reason if ok else reason,
            "true_dz": tw if ok else None,
            "true_dz_raw": tw,
            "proxy_0p8_minus_true_dz": proxy if ok else None,
            "clearance_deficit": deficit if ok else None,
            "tail": tail if ok else None,
            "R_state": R_state,
            "tz_state": tz,
            "R_det": R_det,
            "age": age,
            "dt_state": dt,
        })
    return {
        "label": meta["label"],
        "fid": meta["fid"],
        "path": str(path),
        "n_grazes": len(grazes),
        "contacts": rows,
    }


def sim_collision_crosscheck() -> dict:
    """Mock model: point-mass vs opening; clip annulus 1.0–1.5 × half-size.

    At first clip onset for a point mass, |vert| ≈ opening_half →
    true_dz ≈ ±d* and clearance deficit ≈ 0 ⇒ implied h_drone ≈ 0.
    Real-sim grazes with deficit > 0 would measure body extent beyond
    the point-mass idealization.
    """
    # GATE_GEOM opening half = 0.8; mock Gate default height=1.4 → 0.7
    d_star = 0.80
    mock_default_half = 1.4 / 2.0
    return {
        "reachable": True,
        "path": "simtools/mock_sim.py::_check_gate_crossing",
        "model": "point-mass drone (no airframe half-extent constant)",
        "pass_band": "|vert| <= half_h",
        "clip_band": "half_h < |vert| <= 1.5*half_h (collision_id=1001)",
        "GATE_GEOM_d_star": d_star,
        "mock_default_half_h": mock_default_half,
        "implied_h_drone_at_clip_onset_point_mass": 0.0,
        "note": (
            "Point-mass first-clip predicts deficit≈0 (true_dz≈±half_h). "
            "A measured contact-instant max(deficit)>0 is the real airframe "
            "half-extent above that idealization. Absence of accepted "
            "HIGH-tail deficits is consistent with the mock (h=0), and "
            "does NOT support published h=0.62."
        ),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    flights = [analyze_flight(m) for m in FLIGHTS]
    all_rows = []
    for f in flights:
        all_rows.extend(f.get("contacts") or [])

    accepted = [r for r in all_rows if r.get("accepted")]
    rejected = [r for r in all_rows if not r.get("accepted")]
    reasons: dict[str, int] = {}
    for r in rejected:
        k = r.get("reason") or "?"
        reasons[k] = reasons.get(k, 0) + 1

    proxies = [r["proxy_0p8_minus_true_dz"] for r in accepted
               if r.get("proxy_0p8_minus_true_dz") is not None]
    deficits = [r["clearance_deficit"] for r in accepted
                if r.get("clearance_deficit") is not None]
    high = [r for r in accepted if r.get("tail") == "HIGH"]
    low = [r for r in accepted if r.get("tail") == "LOW"]
    high_def = [r["clearance_deficit"] for r in high
                if r.get("clearance_deficit") is not None]
    low_proxy = [r["proxy_0p8_minus_true_dz"] for r in low
                 if r.get("proxy_0p8_minus_true_dz") is not None]

    h_drone = float(max(deficits)) if deficits else None
    # Both tails of (0.8 − true_dz): min = HIGH-side (can be negative),
    # max = LOW-side (large positive).
    proxy_scatter = scatter(proxies)
    deficit_scatter = scatter(deficits)

    sim = sim_collision_crosscheck()
    held = {
        "h_drone_held": 0.62,
        "C_contact_held": 0.18,
        "cmd_clamp_held": 0.10,
        "status": "HELD — chain does not tighten or loosen on this extraction",
    }

    usable = h_drone is not None and len(accepted) >= 3 and max(deficits or [0]) > 0.05
    verdict = {
        "n_grazes_scanned": len(all_rows),
        "n_accepted_contact_instant": len(accepted),
        "n_rejected": len(rejected),
        "rejection_reasons": reasons,
        "n_HIGH_tail": len(high),
        "n_LOW_tail": len(low),
        "proxy_0p8_minus_true_dz": proxy_scatter,
        "both_tails_proxy": {
            "LOW_tail_max_proxy": float(max(low_proxy)) if low_proxy else None,
            "HIGH_tail_min_proxy": float(min(
                [r["proxy_0p8_minus_true_dz"] for r in high
                 if r.get("proxy_0p8_minus_true_dz") is not None]
            )) if high else None,
            "note": "LOW tail → large +(0.8−dz); HIGH tail → small/negative proxy",
        },
        "clearance_deficit": deficit_scatter,
        "both_tails_deficit": {
            "HIGH_tail_max_deficit": float(max(high_def)) if high_def else 0.0,
            "LOW_tail_deficit_should_be_zero": (
                float(max([r["clearance_deficit"] for r in low] or [0.0]))
            ),
        },
        "h_drone_contact_instant_m": h_drone if deficits else None,
        "contact_grade_usable": usable,
        "chain": held,
        "sim_crosscheck": sim,
        "ruling_input": (
            "If n_accepted==0 or HIGH-tail max deficit≈0: published 0.62 "
            "remains UNSUPPORTED; keep HELD. If contact-grade h lands with "
            "n>=3 HIGH-tail samples, re-derive C_contact = 0.80 − h."
        ),
    }

    summary = {
        "ask": "A8 re-extraction — contact-instant states only (RESPONSE16)",
        "verdict": verdict,
        "flights": flights,
    }
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8")

    lines = [
        "# A8 re-extraction — contact-instant states only",
        "",
        "## Verdict",
        "",
        f"- **n scanned / accepted / rejected**: "
        f"{verdict['n_grazes_scanned']} / "
        f"{verdict['n_accepted_contact_instant']} / "
        f"{verdict['n_rejected']}",
        f"- **Rejection reasons**: `{reasons}`",
        f"- **Tails**: HIGH n=`{len(high)}`, LOW n=`{len(low)}`",
        f"- **(0.8−true_dz) both tails**: "
        f"min=`{proxy_scatter.get('min')}`, max=`{proxy_scatter.get('max')}`, "
        f"mean=`{proxy_scatter.get('mean')}`, std=`{proxy_scatter.get('std')}` "
        f"(n={proxy_scatter.get('n')})",
        f"- **Clearance deficit both tails**: "
        f"HIGH max=`{verdict['both_tails_deficit']['HIGH_tail_max_deficit']}`, "
        f"LOW max=`{verdict['both_tails_deficit']['LOW_tail_deficit_should_be_zero']}`",
        f"- **h_drone (contact-instant)**: `{verdict['h_drone_contact_instant_m']}`",
        f"- **Contact-grade usable**: `{usable}`",
        f"- **Chain**: **HELD** at h=0.62 / C_contact=0.18 / cmd_clamp=0.10 "
        f"(does not tighten or loosen on this pass)",
        "",
        "### Sim collision-model cross-check",
        "",
        f"- Reachable: `{sim['path']}` — {sim['model']}",
        f"- Pass: `{sim['pass_band']}`; clip: `{sim['clip_band']}`",
        f"- GATE_GEOM d*={sim['GATE_GEOM_d_star']}; "
        f"mock default half_h={sim['mock_default_half_h']}",
        f"- Implied point-mass h_drone at clip onset: "
        f"**{sim['implied_h_drone_at_clip_onset_point_mass']}**",
        f"- {sim['note']}",
        "",
        "## Accepted contacts",
        "",
        "| flight | t_ff | impulse | true_dz | 0.8−dz | deficit | tail | R_state | R_det | age |",
        "|---|---:|---:|---:|---:|---:|---|---:|---:|---:|",
    ]
    for r in accepted:
        lines.append(
            f"| {r['flight']} | {r['t_ff']:.3f} | {r['impulse']:.3f} | "
            f"{r['true_dz']:.3f} | {r['proxy_0p8_minus_true_dz']:.3f} | "
            f"{r['clearance_deficit']:.3f} | {r['tail']} | "
            f"{r['R_state']:.2f} | "
            f"{r['R_det'] if r['R_det'] is not None else float('nan'):.2f} | "
            f"{r['age'] if r['age'] is not None else float('nan'):.3f} |"
        )
    if not accepted:
        lines.append("| — | | | | | | no contact-instant accepts | | | |")

    lines += [
        "",
        "## Rejected (sample)",
        "",
        "| flight | t_ff | impulse | reason | R_state | R_det | age |",
        "|---|---:|---:|---|---:|---:|---:|",
    ]
    for r in rejected[:25]:
        lines.append(
            f"| {r.get('flight', '')} | {r.get('t_ff', float('nan')):.3f} | "
            f"{r.get('impulse', float('nan')):.3f} | {r.get('reason')} | "
            f"{r.get('R_state') if r.get('R_state') is not None else float('nan'):.2f} | "
            f"{r.get('R_det') if r.get('R_det') is not None else float('nan'):.2f} | "
            f"{r.get('age') if r.get('age') is not None else float('nan'):.3f} |"
        )

    lines += [
        "",
        "## Method",
        "",
        "1. Graze band: threat≥1, impulse ∈ [0.02, 1.2] "
        "(try39 keeps the 4.035/4.042 pair).",
        "2. Nearest **state** within 0.15 s of collision — true_world_dz from "
        "state.gate_rel only (no detection substitution).",
        f"3. Accept iff R_state ≤ {R_CONTACT_MAX} m, age ≤ {AGE_MAX} s, "
        f"|Δt| ≤ {DT_STATE_MAX} s, and if a near det exists "
        f"|R_state−R_det| ≤ max({R_AGREE_ABS}, {R_AGREE_FRAC}·R).",
        "4. Both tails: HIGH (true_dz≥0) vs LOW (true_dz<0); "
        "h_drone := max(clearance_deficit) on accepted.",
        "5. Sim cross-check: mock point-mass clip annulus "
        "(simtools/mock_sim.py).",
        "",
        f"Generated by `{OUT.name}/run_a8_contact_instant.py`.",
    ]
    text = "\n".join(lines)
    (OUT / "report.md").write_text(text, encoding="utf-8")
    (ROOT / "analysis" / "2026-07-20-a8-contact-instant.md").write_text(
        text, encoding="utf-8")
    print(json.dumps(verdict, indent=2, default=str))


if __name__ == "__main__":
    main()
