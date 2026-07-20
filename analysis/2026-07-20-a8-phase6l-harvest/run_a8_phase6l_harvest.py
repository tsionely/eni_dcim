"""P1 — A8 CONTACT HARVEST from phase6l (RESPONSE18 §4).

Flights: F2 (071112) 11 gate clips + F4/F6 singles.
Pipeline:
  - event-grouping (cluster collisions within EVENT_GAP_S)
  - first-touch rule (one sample per trajectory/event)
  - contact-instant accept (state R/age; det agree when present)
  - per-tail h_up / h_down
  - provenance ledger
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
sys.path.insert(0, str(ROOT / "analysis" / "2026-07-20-a8-contact-instant"))

from aigp.core.messages import RelPose  # noqa: E402
from aigp.planning.approach import true_world_dz  # noqa: E402
from run_a8_half_extent import (  # noqa: E402
    OPENING_HALF_H, GRAZE_IMPULSE, resolve_log, parse_flight, nearest,
)
from run_a8_contact_instant import (  # noqa: E402
    R_CONTACT_MAX, AGE_MAX, DT_STATE_MAX, R_AGREE_ABS, R_AGREE_FRAC,
    contact_geometry_ok, state_true_dz, scatter, sim_collision_crosscheck,
)

EVENT_GAP_S = 0.05  # micro-clip cluster; 0.15 wrongly merged F2's 0.125s gap
FIX = "20260720T071602-phase6l-cohort-3"

FLIGHTS = [
    {"label": "phase6l_F2", "fid": "20260720T071112-cd18c5fb",
     "fixture": FIX, "note": "11 gate clips, clip-budget abort"},
    {"label": "phase6l_F4", "fid": "20260720T071333-cd18c5fb",
     "fixture": FIX, "note": "live single(s)"},
    {"label": "phase6l_F6", "fid": "20260720T071545-cd18c5fb",
     "fixture": FIX, "note": "live single(s)"},
]


def group_events(collisions: list[dict]) -> list[list[dict]]:
    """Cluster collisions into contact events by time proximity."""
    if not collisions:
        return []
    ordered = sorted(collisions, key=lambda c: c["t_ff"])
    groups = [[ordered[0]]]
    for c in ordered[1:]:
        if c["t_ff"] - groups[-1][-1]["t_ff"] <= EVENT_GAP_S:
            groups[-1].append(c)
        else:
            groups.append([c])
    return groups


def first_touch(group: list[dict]) -> dict:
    """Earliest collision in the event (first-touch rule)."""
    return min(group, key=lambda c: c["t_ff"])


def h_up_down(true_dz: float) -> dict:
    """Per-tail half-extents at contact (opening half d*=0.8).

    HIGH (true_dz>=0): top-bar geometry → h_up = max(0, d* − true_dz)
    LOW  (true_dz<0):  bottom-bar → h_down = max(0, d* + true_dz)
    """
    if true_dz >= 0:
        return {
            "tail": "HIGH",
            "h_up": max(0.0, OPENING_HALF_H - true_dz),
            "h_down": None,
            "clearance_deficit_high": max(0.0, true_dz - OPENING_HALF_H),
        }
    return {
        "tail": "LOW",
        "h_up": None,
        "h_down": max(0.0, OPENING_HALF_H + true_dz),
        "clearance_deficit_high": 0.0,
    }


def score_touch(c: dict, log: dict, meta: dict, event_id: int,
                n_in_event: int) -> dict:
    st = nearest(log["states"], c["t_ff"], max_dt=0.15)
    det = nearest([d for d in log["dets"] if d.get("R") and d["R"] < 4.0],
                  c["t_ff"], max_dt=0.2)
    base = {
        "flight": meta["label"],
        "fid": meta["fid"],
        "event_id": event_id,
        "n_in_event": n_in_event,
        "t_ff": c["t_ff"],
        "impulse": c["impulse"],
        "threat_level": c["threat_level"],
        "first_touch": True,
    }
    if st is None:
        return {**base, "accepted": False, "reason": "REJECT_no_state",
                "provenance": "no_state"}
    tw, R_state, tz = state_true_dz(st)
    age = st.get("age")
    age = float(age) if isinstance(age, (int, float)) else None
    dt = abs(st["t_ff"] - c["t_ff"])
    R_det = det["R"] if det else None
    ok, reason = contact_geometry_ok(R_state, age, dt, R_det)

    # Fresh vision at the plane: if state lacks gate_rel but a near
    # det exists with FRESH attitude-bearing state, allow det+att.
    provenance = "state_gate_rel"
    age_ok = age is not None and math.isfinite(age) and age <= AGE_MAX
    if (not ok or tw is None) and det is not None and det["R"] <= R_CONTACT_MAX:
        if st is not None and age_ok and dt <= DT_STATE_MAX:
            if R_state is None or R_state > R_CONTACT_MAX:
                nrm = det.get("normal") or [0, 0, 1]
                tw_det = float(true_world_dz(
                    RelPose(t=np.asarray(det["t_vec"], float),
                            normal=np.asarray(nrm, float)),
                    np.asarray(st["q_att"], float),
                    float(st["level_roll"]), float(st["level_pitch"])))
                tw, R_state, tz = tw_det, det["R"], float(det["t_vec"][2])
                ok, reason = True, "ACCEPT_det_plus_att_plane"
                provenance = "det_plus_att"

    tails = h_up_down(tw) if (ok and tw is not None) else {}
    proxy = None if tw is None else (OPENING_HALF_H - tw)
    return {
        **base,
        "accepted": bool(ok and tw is not None),
        "reason": reason,
        "provenance": provenance,
        "true_dz": tw if ok else None,
        "true_dz_raw": tw,
        "proxy_0p8_minus_true_dz": proxy if ok else None,
        "R_state": R_state,
        "tz_state": tz,
        "R_det": R_det,
        "age": age,
        "dt_state": dt,
        **tails,
    }


def analyze_flight(meta: dict) -> dict:
    path = resolve_log(meta["fid"], meta["fixture"])
    if path is None:
        return {"label": meta["label"], "error": "log_not_found"}
    log = parse_flight(path)
    # All threat>=1 in graze band OR slightly wider for clip budget
    colls = [c for c in log["collisions"]
             if c["threat_level"] >= 1
             and 0.02 <= c["impulse"] <= 3.0]
    # Prefer graze band for envelope; keep ledger of all first-touches
    groups = group_events(colls)
    ledger = []
    micro_fresh = []  # all graze-band collisions with fresh state (consistency)
    for i, g in enumerate(groups):
        touch = first_touch(g)
        scored = score_touch(touch, log, meta, i, len(g))
        if not scored["accepted"]:
            for alt in sorted(g, key=lambda c: c["t_ff"])[1:]:
                alt_s = score_touch(alt, log, meta, i, len(g))
                if alt_s["accepted"]:
                    alt_s["first_touch"] = False
                    alt_s["first_touch_fallback"] = True
                    alt_s["original_first_t_ff"] = touch["t_ff"]
                    scored = alt_s
                    break
        scored["in_graze_band"] = (
            GRAZE_IMPULSE[0] <= scored["impulse"] <= GRAZE_IMPULSE[1])
        ledger.append(scored)
        # Micro-contact census: every collision in group with fresh state
        for c in g:
            if not (GRAZE_IMPULSE[0] <= c["impulse"] <= GRAZE_IMPULSE[1]):
                continue
            m = score_touch(c, log, meta, i, len(g))
            m["first_touch"] = abs(c["t_ff"] - touch["t_ff"]) < 1e-6
            if m.get("accepted") and m.get("R_state") is not None:
                micro_fresh.append(m)
    return {
        "label": meta["label"],
        "fid": meta["fid"],
        "note": meta["note"],
        "path": str(path),
        "n_collisions": len(colls),
        "n_events": len(groups),
        "ledger": ledger,
        "micro_fresh_contacts": micro_fresh,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    flights = [analyze_flight(m) for m in FLIGHTS]
    ledger = []
    micros = []
    for f in flights:
        ledger.extend(f.get("ledger") or [])
        micros.extend(f.get("micro_fresh_contacts") or [])

    accepted = [r for r in ledger if r.get("accepted") and r.get("in_graze_band")]
    accepted_all = [r for r in ledger if r.get("accepted")]
    sample = accepted if accepted else accepted_all

    high = [r for r in sample if r.get("tail") == "HIGH"]
    low = [r for r in sample if r.get("tail") == "LOW"]
    h_ups = [r["h_up"] for r in high if r.get("h_up") is not None]
    h_downs = [r["h_down"] for r in low if r.get("h_down") is not None]
    # Micro-consistency (same trajectory, all fresh graze clips)
    micro_h_downs = [r["h_down"] for r in micros
                     if r.get("tail") == "LOW" and r.get("h_down") is not None]
    micro_h_ups = [r["h_up"] for r in micros
                   if r.get("tail") == "HIGH" and r.get("h_up") is not None]
    h_up = float(max(h_ups)) if h_ups else None
    h_down = float(max(h_downs)) if h_downs else None
    extents = [x for x in [h_up, h_down] if x is not None]
    h_drone = float(max(extents)) if extents else None

    proxies = [r["proxy_0p8_minus_true_dz"] for r in sample
               if r.get("proxy_0p8_minus_true_dz") is not None]
    reasons: dict[str, int] = {}
    for r in ledger:
        if not r.get("accepted"):
            k = r.get("reason") or "?"
            reasons[k] = reasons.get(k, 0) + 1

    usable = (
        h_drone is not None
        and len(sample) >= 3
        and (h_up is not None or h_down is not None)
    )
    unfreeze = bool(usable and h_drone is not None and h_drone > 0.05)

    sim = sim_collision_crosscheck()
    verdict = {
        "n_events": len(ledger),
        "n_accepted_graze": len(accepted),
        "n_accepted_any_impulse": len(accepted_all),
        "sample_used": "graze_band" if accepted else "all_accepted_impulse",
        "n_sample": len(sample),
        "n_HIGH": len(high),
        "n_LOW": len(low),
        "h_up_m": h_up,
        "h_down_m": h_down,
        "h_drone_m": h_drone,
        "h_up_scatter": scatter(h_ups),
        "h_down_scatter": scatter(h_downs),
        "proxy_scatter": scatter(proxies),
        "micro_fresh_n": len(micros),
        "micro_h_up_scatter": scatter(micro_h_ups),
        "micro_h_down_scatter": scatter(micro_h_downs),
        "rejection_reasons": reasons,
        "contact_grade_usable": usable,
        "envelope_unfreeze_candidate": unfreeze,
        "chain": {
            "held_h": 0.62,
            "held_C_contact": 0.18,
            "if_unfreeze_C_contact": (
                None if h_drone is None else 0.80 - h_drone),
            "status": (
                "UNFREEZE CANDIDATE — re-derive from harvest h_drone"
                if unfreeze else
                "HELD — first-touch n<3 or h≈0; see micro-fresh for consistency"
            ),
        },
        "sim_crosscheck": sim,
    }

    summary = {"ask": "A8 phase6l contact harvest", "verdict": verdict,
               "flights": flights, "ledger": ledger}
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8")
    (OUT / "provenance_ledger.csv").write_text(
        "flight,event_id,t_ff,impulse,threat,accepted,reason,provenance,"
        "true_dz,tail,h_up,h_down,R_state,R_det,age,first_touch,in_graze\n"
        + "\n".join(
            f"{r.get('flight')},{r.get('event_id')},{r.get('t_ff')},"
            f"{r.get('impulse')},{r.get('threat_level')},{r.get('accepted')},"
            f"{r.get('reason')},{r.get('provenance')},{r.get('true_dz')},"
            f"{r.get('tail')},{r.get('h_up')},{r.get('h_down')},"
            f"{r.get('R_state')},{r.get('R_det')},{r.get('age')},"
            f"{r.get('first_touch')},{r.get('in_graze_band')}"
            for r in ledger
        ),
        encoding="utf-8")

    lines = [
        "# A8 contact harvest — phase6l F2/F4/F6",
        "",
        "## Verdict",
        "",
        f"- **Events (first-touch)**: {verdict['n_events']}; "
        f"accepted graze `{len(accepted)}` / any-impulse `{len(accepted_all)}`",
        f"- **Sample**: `{verdict['sample_used']}` n=`{len(sample)}` "
        f"(HIGH `{len(high)}` / LOW `{len(low)}`)",
        f"- **h_up / h_down / h_drone**: "
        f"`{h_up}` / `{h_down}` / `{h_drone}`",
        f"- **Contact-grade usable**: `{usable}`; "
        f"**unfreeze candidate**: `{unfreeze}`",
        f"- **Chain**: {verdict['chain']['status']}",
        f"- **Micro-fresh clips** (consistency, not first-touch n): "
        f"n=`{verdict['micro_fresh_n']}`, "
        f"h_down scatter max=`{(verdict['micro_h_down_scatter'] or {}).get('max')}`, "
        f"h_up max=`{(verdict['micro_h_up_scatter'] or {}).get('max')}`",
        f"- **Rejects**: `{reasons}`",
        "",
        "### Sim cross-check",
        "",
        f"- Mock is point-mass (implied h≈0) — real-sim harvest only. "
        f"{sim['note']}",
        "",
        "## Provenance ledger (first-touch per event)",
        "",
        "| flight | evt | t_ff | imp | thr | ok | prov | true_dz | tail | h_up | h_down | R | age |",
        "|---|---:|---:|---:|---:|:---:|---|---:|---|---:|---:|---:|---:|",
    ]
    for r in ledger:
        lines.append(
            f"| {r.get('flight')} | {r.get('event_id')} | "
            f"{r.get('t_ff', float('nan')):.3f} | "
            f"{r.get('impulse', float('nan')):.3f} | {r.get('threat_level')} | "
            f"{'Y' if r.get('accepted') else 'n'} | {r.get('provenance')} | "
            f"{r.get('true_dz') if r.get('true_dz') is not None else float('nan'):.3f} | "
            f"{r.get('tail') or '—'} | "
            f"{r.get('h_up') if r.get('h_up') is not None else float('nan'):.3f} | "
            f"{r.get('h_down') if r.get('h_down') is not None else float('nan'):.3f} | "
            f"{r.get('R_state') if r.get('R_state') is not None else float('nan'):.2f} | "
            f"{r.get('age') if r.get('age') is not None else float('nan'):.3f} |"
        )
    lines += [
        "",
        "## Method",
        "",
        f"1. Event-group collisions within {EVENT_GAP_S}s.",
        "2. First-touch = earliest in group (fallback to first admissible).",
        f"3. Contact-instant: R≤{R_CONTACT_MAX}, age≤{AGE_MAX}, "
        f"|Δt|≤{DT_STATE_MAX}; det+att allowed only if state gate_rel absent/far.",
        "4. h_up = max(0, 0.8−true_dz) on HIGH; "
        "h_down = max(0, 0.8+true_dz) on LOW; h_drone = max(h_up, h_down).",
        "5. Provenance ledger CSV alongside this report.",
        "",
        f"Generated by `{OUT.name}/run_a8_phase6l_harvest.py`.",
    ]
    text = "\n".join(lines)
    (OUT / "report.md").write_text(text, encoding="utf-8")
    (ROOT / "analysis" / "2026-07-20-a8-phase6l-harvest.md").write_text(
        text, encoding="utf-8")
    print(json.dumps(verdict, indent=2, default=str))


if __name__ == "__main__":
    main()
