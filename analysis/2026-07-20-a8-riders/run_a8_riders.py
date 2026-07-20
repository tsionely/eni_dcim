"""P2 — A8 verification riders (advisory-10).

1. Confirm each of the 11 graze true_dz values are AT CONTACT
   (near-range pose), not aim/believed from a drifted/far lock.
2. Publish MAX + scatter of (0.8 − true_dz); if 0.62 was a mean,
   the MAX governs the chain.
3. Extract LATERAL half-extent from side-clip events (and note
   sim-model gap if no side clips exist).
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

from aigp.core.messages import RelPose  # noqa: E402
from aigp.estimation.attitude_filter import level_quat, quat_multiply, quat_rotate  # noqa: E402
from aigp.perception.camera import cam_to_body  # noqa: E402
from aigp.planning.approach import true_world_dz  # noqa: E402

# Reuse the original A8 sample set
sys.path.insert(0, str(ROOT / "analysis" / "2026-07-20-a8-half-extent"))
from run_a8_half_extent import (  # noqa: E402
    FLIGHTS, OPENING_HALF_H, GRAZE_IMPULSE,
    resolve_log, parse_flight, select_grazes, nearest, contact_row,
)

OPENING_HALF_W = 0.8  # square opening; lateral half-extent of OPENING
CONTACT_R_MAX = 2.5   # pose used for true_dz must be near-contact
AGE_MAX = 0.25        # state age at contact must be fresh


def true_world_dxyz(rel: RelPose, q_att, level_roll, level_pitch) -> np.ndarray:
    """Levelled gate vector (same frame as true_world_dz); +z = gate below."""
    q_true = quat_multiply(level_quat(level_roll, level_pitch),
                           np.asarray(q_att, float))
    return quat_rotate(q_true, cam_to_body(np.asarray(rel.t, float)))


def classify_contact_source(c: dict, st, det) -> dict:
    """Is true_dz from a contact-range pose or a drifted/aim/far belief?"""
    R_state = c.get("R_state")
    R_det = c.get("R_det")
    age = st.get("age") if st else None
    dt = c.get("dt_state")

    state_near = (R_state is not None and R_state <= CONTACT_R_MAX
                  and (age is None or age <= AGE_MAX))
    det_near = R_det is not None and R_det <= CONTACT_R_MAX

    if state_near:
        source = "state_fresh_near"
        valid = True
    elif det_near and st is not None:
        source = "det_near_plus_att"
        valid = True
    elif R_state is not None and R_state > CONTACT_R_MAX:
        source = "REJECT_far_state_belief"
        valid = False
    elif age is not None and age > AGE_MAX and not det_near:
        source = "REJECT_stale_state"
        valid = False
    else:
        source = "REJECT_no_near_pose"
        valid = False

    return {
        "source": source,
        "valid_at_contact": valid,
        "age_at_state": age,
        "R_state": R_state,
        "R_det": R_det,
        "dt_state": dt,
    }


def recompute_true_dz_prefer_contact(c_raw, st, det) -> float | None:
    """Prefer near detection pose + attitude; else fresh near state."""
    if st is None:
        return None
    q = np.asarray(st["q_att"], float)
    roll, pitch = st["level_roll"], st["level_pitch"]

    def dz_from(tvec, nrm):
        return float(true_world_dz(
            RelPose(t=np.asarray(tvec, float),
                    normal=np.asarray(nrm if nrm is not None else [0, 0, 1], float)),
            q, roll, pitch))

    R_state = None
    if st.get("gate_rel"):
        t = list(map(float, st["gate_rel"]["t"]))
        R_state = float(np.linalg.norm(t))
        age = st.get("age")
        if R_state <= CONTACT_R_MAX and (age is None or age <= AGE_MAX):
            nrm = st["gate_rel"].get("normal") or [0, 0, 1]
            return dz_from(t, nrm)

    if det is not None and det["R"] <= CONTACT_R_MAX:
        return dz_from(det["t_vec"], det.get("normal"))

    # Last resort: original (may be far) — caller tags invalid
    if st.get("gate_rel"):
        t = list(map(float, st["gate_rel"]["t"]))
        nrm = st["gate_rel"].get("normal") or [0, 0, 1]
        return dz_from(t, nrm)
    return None


def analyze_vertical_riders() -> dict:
    contacts_out = []
    for meta in FLIGHTS:
        path = resolve_log(meta["fid"], meta["fixture"])
        if path is None:
            contacts_out.append({"label": meta["label"], "error": "missing"})
            continue
        log = parse_flight(path)
        # enrich states with age (already there)
        grazes = select_grazes(meta, log["collisions"])
        for g in grazes:
            st = nearest(log["states"], g["t_ff"], max_dt=0.15)
            det = nearest([d for d in log["dets"] if d["R"] < 4.0],
                          g["t_ff"], max_dt=0.2)
            if det is None:
                det = nearest(log["dets"], g["t_ff"], max_dt=0.2)
            base = contact_row(g, log["states"], log["dets"])
            tag = classify_contact_source(base, st, det)
            tw_contact = recompute_true_dz_prefer_contact(base, st, det)
            proxy = None if tw_contact is None else (OPENING_HALF_H - tw_contact)
            deficit = None if proxy is None else max(0.0, -proxy)
            contacts_out.append({
                "flight": meta["label"],
                "fid": meta["fid"],
                "t_ff": g["t_ff"],
                "impulse": g["impulse"],
                "threat_level": g["threat_level"],
                "true_dz_original": base.get("true_world_dz"),
                "true_dz_at_contact": tw_contact if tag["valid_at_contact"] else None,
                "true_dz_raw_recompute": tw_contact,
                "proxy_0p8_minus_true_dz": proxy if tag["valid_at_contact"] else None,
                "proxy_raw": proxy,
                "clearance_deficit": deficit if tag["valid_at_contact"] else None,
                "clearance_deficit_raw": deficit,
                **tag,
                "ty_state": base.get("ty_state"),
                "ty_det": base.get("ty_det"),
            })
    return contacts_out


def scatter_stats(vals):
    if not vals:
        return {"n": 0}
    a = np.asarray(vals, float)
    return {
        "n": int(len(a)),
        "max": float(a.max()),
        "min": float(a.min()),
        "mean": float(a.mean()),
        "std": float(a.std()),
        "median": float(np.median(a)),
        "p10": float(np.percentile(a, 10)),
        "p90": float(np.percentile(a, 90)),
        "values": [float(x) for x in a],
    }


def find_side_clips() -> dict:
    """Scan known clip-rich flights for lateral (side-bar) grazes."""
    # Broaden search: phase6d F1, try39, phase6j F4 (2 gate_clips),
    # phase6h all attempts with clips.
    candidates = [
        ("phase6d_F1", "20260719T134326-2477345e",
         "20260719T134835-phase6d-fiction-guards"),
        ("try39", "20260719T163649-f170ead6",
         "20260719T164956-phase6h-first-enable"),
        ("phase6j_F4", "20260720T053745-5cebc2b2",
         "20260720T054037-phase6j-block-a-cohort-2"),
        ("phase6c_F3", "20260719T121637-f186c83e",
         "20260719T121704-phase6c-true-vertical"),
        ("phase6h_try15", "20260719T162247-f170ead6",
         "20260719T164956-phase6h-first-enable"),
    ]
    side_events = []
    for label, fid, fixture in candidates:
        path = resolve_log(fid, fixture)
        if path is None:
            continue
        log = parse_flight(path)
        grazes = [c for c in log["collisions"]
                  if c["threat_level"] >= 1
                  and GRAZE_IMPULSE[0] <= c["impulse"] <= GRAZE_IMPULSE[1]]
        # Also include slightly harder clips up to impulse 2.5 for sides
        clips = [c for c in log["collisions"]
                 if c["threat_level"] >= 1
                 and 0.02 <= c["impulse"] <= 2.5]
        for g in clips:
            st = nearest(log["states"], g["t_ff"], max_dt=0.12)
            det = nearest([d for d in log["dets"] if d["R"] and d["R"] < 3.0],
                          g["t_ff"], max_dt=0.2)
            if st is None or not st.get("gate_rel"):
                continue
            t = list(map(float, st["gate_rel"]["t"]))
            R = float(np.linalg.norm(t))
            if R > 3.0:
                # try det
                if det is None:
                    continue
                t = det["t_vec"]
                R = det["R"]
                nrm = det.get("normal") or [0, 0, 1]
            else:
                nrm = st["gate_rel"].get("normal") or [0, 0, 1]
            rel = RelPose(t=np.asarray(t, float),
                          normal=np.asarray(nrm, float))
            tl = true_world_dxyz(rel, st["q_att"], st["level_roll"], st["level_pitch"])
            # NED levelled: [0]=north/fwd-ish, [1]=east/lateral, [2]=down
            dx, dz = float(tl[1]), float(tl[2])
            # Side-clip heuristic: |lateral| dominates |vertical|
            side_score = abs(dx) - abs(dz)
            is_side = abs(dx) >= 0.35 and abs(dx) >= abs(dz) * 0.9
            if not is_side and not (abs(dx) > 0.5 and abs(dz) < 0.4):
                continue
            proxy_lat = OPENING_HALF_W - abs(dx)
            deficit_lat = max(0.0, -proxy_lat)
            side_events.append({
                "flight": label,
                "fid": fid,
                "t_ff": g["t_ff"],
                "impulse": g["impulse"],
                "R": R,
                "true_dx": dx,
                "true_dz": dz,
                "side_score": side_score,
                "proxy_0p8_minus_abs_dx": proxy_lat,
                "lateral_clearance_deficit": deficit_lat,
                "center_px": (det or {}).get("center_px") if det else None,
            })
    deficits = [e["lateral_clearance_deficit"] for e in side_events]
    proxies = [e["proxy_0p8_minus_abs_dx"] for e in side_events]
    w_drone = float(max(deficits)) if deficits else None
    # Mock crossing uses gate half-size only — no airframe radius.
    return {
        "n_side_events": len(side_events),
        "events": side_events,
        "proxy_0p8_minus_abs_dx": scatter_stats(proxies),
        "w_drone_m": w_drone,
        "w_drone_formula": "max(0, max(|true_dy|-0.8)) at side-classified grazes",
        "sim_collision_model": (
            "mock_sim._check_gate_crossing uses gate half_w/half_h only — "
            "no drone lateral half-extent constant in repo; "
            "real-sim side clips are the measurement path"
        ),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    contacts = analyze_vertical_riders()
    valid = [c for c in contacts if c.get("valid_at_contact")
             and c.get("proxy_0p8_minus_true_dz") is not None]
    raw = [c for c in contacts if c.get("proxy_raw") is not None]
    invalid = [c for c in contacts if c.get("valid_at_contact") is False]

    proxy_valid = scatter_stats([c["proxy_0p8_minus_true_dz"] for c in valid])
    deficits_valid = [c["clearance_deficit"] for c in valid
                      if c.get("clearance_deficit") is not None]
    deficits_raw = [c["clearance_deficit_raw"] for c in raw
                    if c.get("clearance_deficit_raw") is not None]
    h_valid = float(max(deficits_valid)) if deficits_valid else 0.0
    h_raw = float(max(deficits_raw)) if deficits_raw else 0.0

    # Original published series of (0.8 - true_dz_original)
    proxy_orig_series = []
    deficit_orig_series = []
    for c in contacts:
        if c.get("true_dz_original") is not None:
            p = OPENING_HALF_H - c["true_dz_original"]
            proxy_orig_series.append(p)
            deficit_orig_series.append(max(0.0, -p))
    proxy_orig = scatter_stats(proxy_orig_series)
    max_deficit_orig = float(max(deficit_orig_series)) if deficit_orig_series else 0.0
    # Flag contacts whose ORIGINAL true_dz came from far state (even if repaired)
    n_orig_far = sum(
        1 for c in contacts
        if c.get("R_state") is not None and c["R_state"] > CONTACT_R_MAX
    )
    published_h = 0.62
    mean_proxy_orig = proxy_orig.get("mean")
    identity = {
        "published_h_drone": published_h,
        "is_mean_of_0p8_minus_true_dz": (
            mean_proxy_orig is not None
            and abs(mean_proxy_orig - published_h) < 0.05
        ),
        "is_max_clearance_deficit_of_original": abs(max_deficit_orig - published_h) < 0.02,
        "original_proxy_scatter": proxy_orig,
        "original_max_deficit": max_deficit_orig,
        "n_original_from_far_state": n_orig_far,
        "ruling": (
            f"Published 0.62 ≈ mean(0.8−true_dz)={mean_proxy_orig} AND ≈ "
            f"max(deficit)={max_deficit_orig} from the ORIGINAL series. "
            f"Advisory-8B: clamp from the MAX of (0.8−true_dz) "
            f"(MAX={proxy_orig.get('max')}) — but that statistic mixes LOW "
            f"grazes (large positive proxy) with HIGH grazes; physical "
            f"vertical half-extent is max(deficit)=max(0, true_dz−0.8). "
            f"{n_orig_far} of 11 original true_dz samples used R_state>"
            f"{CONTACT_R_MAX}m (far belief). Contact-valid repair drops "
            f"those HIGH outliers → h_drone_contact_valid may be 0 — "
            f"published 0.62 is then UNSUPPORTED at contact geometry."
        ),
    }

    lateral = find_side_clips()

    summary = {
        "ask": "A8 verification riders (advisory-10)",
        "n_contacts_total": len(contacts),
        "n_valid_at_contact": len(valid),
        "n_rejected_source": len(invalid),
        "rejection_reasons": {},
        "identity_of_0p62": identity,
        "contact_valid_proxy_0p8_minus_true_dz": proxy_valid,
        "h_drone_contact_valid_m": h_valid,
        "h_drone_raw_recompute_m": h_raw,
        "chain_implication": {
            "C_contact_from_published": 0.80 - 0.62,
            "C_contact_from_contact_valid_h": (
                None if not deficits_valid else 0.80 - h_valid
            ),
            "if_max_proxy_governed_wrongly": proxy_orig.get("max"),
            "note": (
                "Clearance is worst-case: h_drone = max deficit among "
                "CONTACT-valid grazes; MAX of (0.8-dz) is a different "
                "statistic (includes low-side grazes) and must NOT be "
                "read as h_drone."
            ),
        },
        "contacts": contacts,
        "lateral": lateral,
    }
    for c in invalid:
        k = c.get("source", "?")
        summary["rejection_reasons"][k] = summary["rejection_reasons"].get(k, 0) + 1

    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8")

    lines = [
        "# A8 verification riders (advisory-10)",
        "",
        "## Verdict",
        "",
        f"- **Published h=0.62 identity**: "
        f"coincides with mean(0.8−dz)=`{mean_proxy_orig}` "
        f"{'YES' if identity['is_mean_of_0p8_minus_true_dz'] else 'no'}; "
        f"also coincides with max(deficit_original)=`{max_deficit_orig}` "
        f"{'YES' if identity['is_max_clearance_deficit_of_original'] else 'no'}; "
        f"MAX(0.8−dz)=`{proxy_orig.get('max')}` — if that governed as h, "
        f"C_contact would go negative. "
        f"{n_orig_far}/11 original samples used far-state belief (R>{CONTACT_R_MAX}).",
        f"- **Original 11-sample (0.8−true_dz)**: "
        f"MAX=`{proxy_orig.get('max')}`, mean=`{proxy_orig.get('mean')}`, "
        f"std=`{proxy_orig.get('std')}`, median=`{proxy_orig.get('median')}` "
        f"(n={proxy_orig.get('n')}).",
        f"- **Contact-valid subset**: {len(valid)}/{len(contacts)} "
        f"(rejected {len(invalid)}: `{summary['rejection_reasons']}`).",
        f"- **h_drone (contact-valid)**: `{h_valid}` m; "
        f"raw/unfiltered recompute `{h_raw}` m.",
        f"- **Lateral half-extent**: n_side_events=`{lateral['n_side_events']}`, "
        f"w_drone=`{lateral.get('w_drone_m')}` — {lateral['sim_collision_model']}.",
        "",
        "### Chain",
        "",
        f"- C_contact from published 0.62: `{0.80-0.62}` m",
        f"- C_contact from contact-valid h: "
        f"`{summary['chain_implication']['C_contact_from_contact_valid_h']}`",
        "",
        "## Per-contact audit",
        "",
        "| flight | t_ff | impulse | orig_dz | contact_dz | 0.8−dz | valid | source | R_state | R_det | age |",
        "|---|---:|---:|---:|---:|---:|:---:|---|---:|---:|---:|",
    ]
    for c in contacts:
        if c.get("error"):
            lines.append(f"| {c.get('flight')} | | | | | | | {c['error']} | | | |")
            continue
        lines.append(
            f"| {c['flight']} | {c['t_ff']:.3f} | {c['impulse']:.3f} | "
            f"{c.get('true_dz_original') if c.get('true_dz_original') is not None else float('nan'):.3f} | "
            f"{c.get('true_dz_at_contact') if c.get('true_dz_at_contact') is not None else float('nan'):.3f} | "
            f"{c.get('proxy_0p8_minus_true_dz') if c.get('proxy_0p8_minus_true_dz') is not None else float('nan'):.3f} | "
            f"{'Y' if c.get('valid_at_contact') else 'n'} | {c.get('source')} | "
            f"{c.get('R_state') if c.get('R_state') is not None else float('nan'):.2f} | "
            f"{c.get('R_det') if c.get('R_det') is not None else float('nan'):.2f} | "
            f"{c.get('age_at_state') if c.get('age_at_state') is not None else float('nan'):.3f} |"
        )
    lines += [
        "",
        "## Lateral side-clip events",
        "",
        "| flight | t_ff | impulse | R | true_dx | true_dz | 0.8−|dx| | lat_deficit |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for e in lateral.get("events") or []:
        lines.append(
            f"| {e['flight']} | {e['t_ff']:.3f} | {e['impulse']:.3f} | "
            f"{e['R']:.2f} | {e['true_dx']:.3f} | {e['true_dz']:.3f} | "
            f"{e['proxy_0p8_minus_abs_dx']:.3f} | "
            f"{e['lateral_clearance_deficit']:.3f} |"
        )
    if not lateral.get("events"):
        lines.append("| — | | | | | | | no side-classified grazes |")
    lines += [
        "",
        "## Method",
        "",
        "1. Same 11 graze sample as P4 A8 (phase6d F1 + try39 pair).",
        f"2. Contact-valid iff pose R ≤ {CONTACT_R_MAX} m and (state age ≤ {AGE_MAX} s or near det).",
        "3. Prefer fresh near state; else near detection + attitude for true_world_dz.",
        "4. Scatter = max/mean/std/median/p10/p90 of (0.8 − true_dz).",
        "5. Side-clip: |true_dx| ≥ 0.35 and |dx| ≳ |dz| on graze/clip impulses.",
        "",
        f"Generated by `{OUT.name}/run_a8_riders.py`.",
    ]
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")
    (ROOT / "analysis" / "2026-07-20-a8-riders.md").write_text(
        "\n".join(lines), encoding="utf-8")
    print(json.dumps({
        "n_valid": len(valid),
        "n_rejected": len(invalid),
        "identity": identity,
        "h_valid": h_valid,
        "proxy_valid": proxy_valid,
        "lateral_n": lateral["n_side_events"],
        "w_drone": lateral.get("w_drone_m"),
    }, indent=2, default=str))


if __name__ == "__main__":
    main()
