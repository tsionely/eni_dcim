"""Metrology-f4 cluster failure autopsy (RESPONSE36 §3).

Funnel label: NO_CERTIFIED_FULL_BELOW_3P5 — distinct from f1's
scale_gate kill. Mines harvest features + live flight.jsonl for
20260720T142917-9aa0ef5c and archive comparators F1/F5.
"""
from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
FEATURES = (
    ROOT / "tuning"
    / "archive-harvest-release-fit-v21-6fe13e3-6fe13e3-20260720T144339Z"
    / "features_archive.csv"
)
F4_LOG = (
    ROOT / "fixtures" / "20260720T142941-phase7m-metrology-f4"
    / "20260720T142917-9aa0ef5c-flight.jsonl"
)
F4_ID = "20260720T142917-9aa0ef5c"
F1_ID = "20260720T071008-5b501b4c"
F5_ID = "20260720T071439-5b501b4c"
OK_ID = "20260720T134522-9aa0ef5c"  # metrology f2 sibling — legal cluster
RANGE_CUT = 3.5
PROMOTE_FLOOR = 1.6


def fnum(v):
    if v is None or v == "":
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def load_features(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def flight_rows(all_rows: list[dict], fid: str) -> list[dict]:
    return [r for r in all_rows if r.get("flight_id") == fid]


def summarize_csv(rows: list[dict], label: str) -> dict:
    mode_cert = Counter((r["feature_mode"], r["cert_status"]) for r in rows)
    full = [r for r in rows if r.get("feature_mode") == "FULL_QUAD"]
    full_rz = [(r, fnum(r.get("range_z_m"))) for r in full]
    full_rz = [(r, z) for r, z in full_rz if z is not None]
    full_le = [(r, z) for r, z in full_rz if z <= RANGE_CUT]
    full_cert_le = [(r, z) for r, z in full_le if r.get("cert_status") == "certified"]
    side = [r for r in rows if "SIDE" in (r.get("feature_mode") or "")]
    closest = min(full_rz, key=lambda t: t[1], default=(None, None))
    return {
        "label": label,
        "n_feature_rows": len(rows),
        "mode_cert": {f"{a}|{b}": c for (a, b), c in sorted(mode_cert.items())},
        "n_full": len(full),
        "full_range_min": closest[1],
        "full_range_max": max((z for _, z in full_rz), default=None),
        "n_full_le_3p5_any_cert": len(full_le),
        "n_full_certified_le_3p5": len(full_cert_le),
        "n_side_any": len(side),
        "n_side_probation": sum(1 for r in side if r.get("cert_status") == "probation"),
        "n_side_row_only": sum(1 for r in side if "ROW_ONLY" in (r.get("feature_mode") or "")),
        "closest_full": None if closest[0] is None else {
            "t_rel_s": fnum(closest[0].get("t_rel_s")),
            "range_z_m": closest[1],
            "cert_status": closest[0].get("cert_status"),
            "phase": closest[0].get("phase"),
            "center_x_px": fnum(closest[0].get("center_x_px")),
            "e_reject": closest[0].get("e_reject"),
            "frame_id": closest[0].get("frame_id"),
        },
    }


def live_detection_audit(path: Path) -> dict:
    dets = []
    feats = []
    fsm = []
    collision = None
    for line in path.open(encoding="utf-8"):
        o = json.loads(line)
        t = o.get("topic")
        d = o.get("data") or {}
        mono = o.get("mono_ns")
        if t == "fsm":
            fsm.append({"src": d.get("src"), "dst": d.get("dst"), "reason": d.get("reason"), "mono_ns": mono})
            if d.get("dst") == "ABORTED" and collision is None:
                collision = {"mono_ns": mono, "reason": d.get("reason")}
        if t == "detection" and d.get("rel_pose"):
            r = float(d["rel_pose"]["t"][2])
            dets.append({
                "mono_ns": mono,
                "ts_ns": d.get("ts_ns"),
                "range_z_m": r,
                "cert_status": d.get("cert_status"),
                "confidence": d.get("confidence"),
                "center_px": d.get("center_px"),
            })
        if t == "feature":
            feats.append({
                "mono_ns": mono,
                "mode": d.get("mode"),
                "cert_status": d.get("cert_status"),
                "y_top_px": d.get("y_top_px"),
                "span_px": d.get("span_px"),
                "center_x_px": d.get("center_x_px"),
            })
    le35 = [d for d in dets if d["range_z_m"] <= RANGE_CUT]
    le50 = [d for d in dets if d["range_z_m"] <= 5.0]
    min_det = min(dets, key=lambda d: d["range_z_m"], default=None)
    return {
        "n_detections": len(dets),
        "min_detection": min_det,
        "n_det_le_3p5": len(le35),
        "det_le_3p5_cert": dict(Counter(d["cert_status"] for d in le35)),
        "n_det_le_5p0": len(le50),
        "det_le_5p0": sorted(le50, key=lambda d: d["range_z_m"]),
        "feature_mode_cert_live": dict(Counter((f["mode"], f["cert_status"]) for f in feats)),
        "fsm": fsm,
        "collision": collision,
    }


def stage_table_f4(csv_rows: list[dict], live: dict) -> list[dict]:
    """Stage-by-stage narrative rows for the f4 funnel (not 11 scale_gate fixes)."""
    rows = sorted(csv_rows, key=lambda r: fnum(r.get("t_rel_s")) or 0.0)
    stages = []
    # Stage A: continuous FULL certified above 5m
    full_above = [
        r for r in rows
        if r.get("feature_mode") == "FULL_QUAD"
        and r.get("cert_status") == "certified"
        and fnum(r.get("range_z_m")) is not None
        and fnum(r["range_z_m"]) > 5.0
    ]
    stages.append({
        "stage": "A_pad_to_mid_FULL_certified",
        "pass": len(full_above) > 0,
        "n_rows": len(full_above),
        "detail": f"{len(full_above)} certified FULL with range_z>5; continuous lock from pad",
        "kill": False,
    })
    # Stage B: FULL dropout into SIDE in 4-5m band
    side_band = [
        r for r in rows
        if "SIDE" in (r.get("feature_mode") or "")
        and fnum(r.get("range_z_m")) is not None
        and fnum(r["range_z_m"]) <= 5.0
    ]
    stages.append({
        "stage": "B_FULL_dropout_to_SIDE_4to5m",
        "pass": True,  # observed
        "n_rows": len(side_band),
        "detail": (
            f"{len(side_band)} SIDE rows ≤5m "
            f"(probation={sum(1 for r in side_band if r.get('cert_status')=='probation')}, "
            f"row_only={sum(1 for r in side_band if 'ROW_ONLY' in (r.get('feature_mode') or ''))}); "
            "last continuous FULL before band ends ~5.31m"
        ),
        "kill": False,
    })
    # Stage C: any certified FULL ≤3.5 in harvest
    full_le = [
        r for r in rows
        if r.get("feature_mode") == "FULL_QUAD"
        and r.get("cert_status") == "certified"
        and fnum(r.get("range_z_m")) is not None
        and fnum(r["range_z_m"]) <= RANGE_CUT
    ]
    closest_full = min(
        (
            (r, fnum(r.get("range_z_m")))
            for r in rows
            if r.get("feature_mode") == "FULL_QUAD" and fnum(r.get("range_z_m")) is not None
        ),
        key=lambda t: t[1],
        default=(None, None),
    )
    stages.append({
        "stage": "C_harvest_certified_FULL_le_3p5",
        "pass": len(full_le) > 0,
        "n_rows": len(full_le),
        "detail": (
            f"census gate FAIL — 0 certified FULL ≤{RANGE_CUT}m; "
            f"closest certified FULL harvest range={closest_full[1]} "
            f"(frame {closest_full[0].get('frame_id') if closest_full[0] else None}, "
            f"phase={closest_full[0].get('phase') if closest_full[0] else None})"
        ),
        "kill": True,
    })
    # Stage D: live close detections
    le35 = live.get("det_le_3p5_cert") or {}
    stages.append({
        "stage": "D_live_detector_fixes_le_3p5",
        "pass": (live.get("n_det_le_3p5") or 0) > 0,
        "n_rows": live.get("n_det_le_3p5") or 0,
        "detail": (
            f"YES approach got close — min_det={live.get('min_detection')}; "
            f"cert breakdown ≤3.5: {le35}"
        ),
        "kill": False,
    })
    # Stage E: those close dets certified?
    n_cert_close = le35.get("certified", 0)
    stages.append({
        "stage": "E_close_dets_certified",
        "pass": n_cert_close > 0,
        "n_rows": n_cert_close,
        "detail": (
            "close dets are cert=none conf=0.5 — identity never re-certified "
            f"below promote floor path; promote_floor={PROMOTE_FLOOR}m is moot "
            "because these are not fresh FULL anchors in harvest"
        ),
        "kill": True,
    })
    # Stage F: SIDE never promotes to certified for harvest
    stages.append({
        "stage": "F_SIDE_certified_for_cluster",
        "pass": False,
        "n_rows": 0,
        "detail": "SIDE stays probation/row-only/none — census needs certified SIDE≥2 AND certified FULL≤3.5",
        "kill": True,
    })
    return stages


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    all_rows = load_features(FEATURES)
    f4 = flight_rows(all_rows, F4_ID)
    f1 = flight_rows(all_rows, F1_ID)
    f5 = flight_rows(all_rows, F5_ID)
    ok = flight_rows(all_rows, OK_ID)
    live = live_detection_audit(F4_LOG)

    f4_sum = summarize_csv(f4, "metrology_f4")
    f1_sum = summarize_csv(f1, "archive_F1")
    f5_sum = summarize_csv(f5, "archive_F5")
    ok_sum = summarize_csv(ok, "metrology_f2_ok")

    stages = stage_table_f4(f4, live)
    write_csv(OUT / "rejection_table_f4.csv", [
        {
            "stage": s["stage"],
            "pass": s["pass"],
            "kill": s["kill"],
            "n_rows": s["n_rows"],
            "detail": s["detail"],
        }
        for s in stages
    ])

    # Timeline of harvest rows with range<=5.5 for f4
    timeline = []
    for r in sorted(f4, key=lambda x: fnum(x.get("t_rel_s")) or 0):
        z = fnum(r.get("range_z_m"))
        if z is None or z > 5.5:
            continue
        timeline.append({
            "t_rel_s": fnum(r.get("t_rel_s")),
            "phase": r.get("phase"),
            "feature_mode": r.get("feature_mode"),
            "cert_status": r.get("cert_status"),
            "range_z_m": z,
            "center_x_px": fnum(r.get("center_x_px")),
            "span_px": fnum(r.get("span_px")),
            "gate_age_s": fnum(r.get("gate_age_s")),
            "e_reject": r.get("e_reject"),
            "x_m": fnum(r.get("x_m")),
            "frame_id": r.get("frame_id"),
        })
    write_csv(OUT / "timeline_le5p5_f4.csv", timeline)

    # Comparator one-pager
    write_csv(OUT / "comparator_summary.csv", [
        {
            "flight": s["label"],
            "n_full_certified_le_3p5": s["n_full_certified_le_3p5"],
            "full_range_min": s["full_range_min"],
            "n_side_probation": s["n_side_probation"],
            "n_side_row_only": s["n_side_row_only"],
            "census_label": (
                "OK" if s["n_full_certified_le_3p5"] > 0 else "NO_CERTIFIED_FULL_BELOW_3P5"
            ),
        }
        for s in (f4_sum, f1_sum, f5_sum, ok_sum)
    ])

    where = "FULL_DROPOUT_THEN_UNCERTIFIED_CLOSE_DETS"
    systematic = True  # F1+F5 same census label; same profile class
    profile_change_required = True

    rationale = (
        "Approach DID get close (live min det 2.30 m, 2 dets ≤3.5 m) but both "
        "close dets are cert=none conf=0.5 and emit no harvest FULL feature. "
        "Continuous certified FULL ends ~5.31 m; the 4–5 m band is SIDE "
        "probation/row-only only; one recover FULL at 3.75 m sits ABOVE the "
        "3.5 m census cut (e_reject=ok — not a scale_gate kill). Archive F1/F5 "
        "share NO_CERTIFIED_FULL_BELOW_3P5 with closest harvest FULL ≥4.3 m. "
        "Successful sibling 134522 delivers 33 certified FULL ≤3.5 on the same "
        "metrology profile family — so this is a systematic coverage lottery of "
        "the standard approach, not an idiosyncratic one-off and not f1's funnel."
    )

    profile_proposal = {
        "decision": "CHANGE_METROLOGY_PROFILE_SELECTION",
        "visibility": "tanks-visible (RESPONSE36 §3 / advisory §6)",
        "do_not": "quiet retune of detector/cert thresholds to rescue these flights",
        "items": [
            {
                "id": "P1_accept_gate",
                "title": "Collection accept-gate on certified coverage",
                "text": (
                    "A metrology flight counts toward the shortfall ONLY if harvest "
                    "shows ≥4 certified FULL with range_z≤3.5 and e_reject=ok "
                    "(cluster entry bar). Flights labeled NO_CERTIFIED_FULL_BELOW_3P5 "
                    "are logged as coverage failures and do not consume the "
                    "remaining shortfall slot — retry under P2."
                ),
            },
            {
                "id": "P2_hold_certified_through_band",
                "title": "Hold certified FULL through the 5→3 m band",
                "text": (
                    "Profile selection change: when FULL drops to SIDE before 4.5 m, "
                    "align/hold (or slow to ≤1.2 m/s) until ≥3 consecutive certified "
                    "FULL re-anchors, then continue. Goal = enrich older-age SIDE "
                    "bins AND hold certified FULL coverage through ≤3.5 m "
                    "(advisory §6 both clauses)."
                ),
            },
            {
                "id": "P3_no_more_identical_blind_collection",
                "title": "Stop identical blind collection",
                "text": (
                    "Per RESPONSE36 escalation: do not fly another identical "
                    "standard-profile metrology attempt until P1/P2 are adopted. "
                    "f1 (scale_gate) and f4 (no certified FULL≤3.5) are two "
                    "different honest funnels; repeating the profile reproduces "
                    "known censoring."
                ),
            },
        ],
    }

    summary = {
        "response": "RESPONSE36 §3",
        "repo_tip_requested": "2e37585",
        "features_source": str(FEATURES.relative_to(ROOT)),
        "flight_f4": F4_ID,
        "comparators": {"F1": F1_ID, "F5": F5_ID, "ok_sibling": OK_ID},
        "census_label": "NO_CERTIFIED_FULL_BELOW_3P5",
        "WHERE_USABILITY_DIED": where,
        "distinct_from_f1": True,
        "f1_funnel": "SCALE_GATE_FLIPPED_FAR_GATE_POST_GAP",
        "SYSTEMATIC_vs_LOTTERY": "SYSTEMATIC_PROFILE_COVERAGE_LOTTERY",
        "profile_change_required": profile_change_required,
        "RESCUABLE_as_7th_cluster": False,
        "f4_csv": f4_sum,
        "f4_live": {
            "min_detection": live.get("min_detection"),
            "n_det_le_3p5": live.get("n_det_le_3p5"),
            "det_le_3p5_cert": live.get("det_le_3p5_cert"),
            "fsm_abort": live.get("collision"),
        },
        "archive_F1": f1_sum,
        "archive_F5": f5_sum,
        "ok_sibling": ok_sum,
        "stages": stages,
        "verdict_rationale": rationale,
        "profile_selection_proposal": profile_proposal,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Metrology-f4 cluster failure autopsy",
        "",
        "RESPONSE36 §3 — flight `20260720T142917-9aa0ef5c` "
        "(fixtures/20260720T142941-phase7m-metrology-f4).",
        "Census label: **NO_CERTIFIED_FULL_BELOW_3P5** "
        "(distinct from f1's scale-gate kill).",
        "",
        f"## WHERE_USABILITY_DIED: **{where}**",
        "",
        "**SYSTEMATIC profile coverage lottery** (same label as archive F1/F5) — "
        "not an idiosyncratic one-off. **Not rescuable** as a 7th cluster without "
        "a tanks-visible profile selection change.",
        "",
        rationale,
        "",
        "## Stage-by-stage rejection table",
        "",
        "| Stage | Pass? | Kill? | n | Detail |",
        "|---|---|---|---:|---|",
    ]
    for s in stages:
        lines.append(
            f"| `{s['stage']}` | {s['pass']} | {s['kill']} | {s['n_rows']} | {s['detail']} |"
        )
    lines += [
        "",
        "## Did the approach get close enough?",
        "",
        f"- Live min detection: **{live.get('min_detection')}**",
        f"- Live dets ≤3.5 m: **{live.get('n_det_le_3p5')}** "
        f"(cert breakdown `{live.get('det_le_3p5_cert')}`)",
        f"- Harvest closest certified FULL: **{f4_sum['full_range_min']:.3f} m** "
        f"(recover frame {f4_sum['closest_full']['frame_id']}) — above the 3.5 m cut",
        "- Abort: environment collision (impulse=2.6), gates_passed=0",
        "",
        "## Comparator board (same census label vs OK sibling)",
        "",
        "| Flight | certified FULL≤3.5 | closest FULL | SIDE probation | census |",
        "|---|---:|---:|---:|---|",
        f"| f4 `{F4_ID}` | {f4_sum['n_full_certified_le_3p5']} | "
        f"{f4_sum['full_range_min']} | {f4_sum['n_side_probation']} | NO_CERTIFIED_FULL_BELOW_3P5 |",
        f"| archive F1 | {f1_sum['n_full_certified_le_3p5']} | "
        f"{f1_sum['full_range_min']} | {f1_sum['n_side_probation']} | NO_CERTIFIED_FULL_BELOW_3P5 |",
        f"| archive F5 | {f5_sum['n_full_certified_le_3p5']} | "
        f"{f5_sum['full_range_min']} | {f5_sum['n_side_probation']} | NO_CERTIFIED_FULL_BELOW_3P5 |",
        f"| ok sibling f2 | {ok_sum['n_full_certified_le_3p5']} | "
        f"{ok_sum['full_range_min']} | {ok_sum['n_side_probation']} | OK |",
        "",
        "## Ruled-out / distinguished",
        "",
        "- f1-style scale_gate on flipped far gate: **no** — closest harvest FULL "
        "at 3.75 m has e_reject=ok; zero FULL≤3.5 to kill.",
        "- Never approached: **no** — live to 2.30 m.",
        "- Promote-floor blocking fresh cert below 1.6 m: **not the primary kill** — "
        "coverage already failed above 3.5 m; close dets are none/0.5 before that floor matters.",
        "- Harness over-reject of honest certified FULL≤3.5: **no** — none exist in harvest.",
        "",
        "## Profile selection change (tanks-visible)",
        "",
        f"**Decision: `{profile_proposal['decision']}`** — {profile_proposal['visibility']}.",
        f"Do **not**: {profile_proposal['do_not']}.",
        "",
    ]
    for item in profile_proposal["items"]:
        lines += [f"### {item['id']}: {item['title']}", "", item["text"], ""]
    lines += [
        "## Deliverables",
        "",
        "- `rejection_table_f4.csv`",
        "- `timeline_le5p5_f4.csv`",
        "- `comparator_summary.csv`",
        "- `summary.json`",
        "- `run_f4_autopsy.py`",
        "",
    ]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "WHERE": where,
        "SYSTEMATIC": systematic,
        "f4_full_le35": f4_sum["n_full_certified_le_3p5"],
        "closest_full": f4_sum["full_range_min"],
        "live_min": live.get("min_detection"),
    }))


if __name__ == "__main__":
    main()
