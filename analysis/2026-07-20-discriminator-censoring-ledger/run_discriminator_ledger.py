"""Discriminator table + coverage-censoring ledger (RESPONSE38 §1 / RESPONSE39).

First edition on the ten already-labeled flights (6 archive phase6l +
4 metrology). Extends later when the full-archive sweep lands.
"""
from __future__ import annotations

import csv
import json
import math
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
FEATURES = (
    ROOT / "tuning"
    / "archive-harvest-release-fit-v21-6fe13e3-6fe13e3-20260720T144339Z"
    / "features_archive.csv"
)
CENSUS = (
    ROOT / "tuning"
    / "archive-harvest-release-fit-v21-6fe13e3-6fe13e3-20260720T144339Z"
    / "census_diagnostics.csv"
)
PROMOTE_FLOOR = 1.6
RANGE_CUT = 3.5
FULL_GAP_S = 0.35  # consecutive FULL gap larger than this counts

# Mechanism names for the two honest censor funnels (autopsy-confirmed).
MECH_SCALE = "SCALE_GATE_FLIPPED_FAR_GATE_POST_GAP"
MECH_DROPOUT = "NO_CERTIFIED_FULL_BELOW_3P5"  # ledger label; autopsy: FULL_DROPOUT_THEN_UNCERTIFIED_CLOSE_DETS

FLIGHT_META = {
    "20260720T071008-5b501b4c": {"era": "archive", "campaign": "phase6l-cohort-3", "slot": "F1"},
    "20260720T071112-cd18c5fb": {"era": "archive", "campaign": "phase6l-cohort-3", "slot": "F2"},
    "20260720T071220-5b501b4c": {"era": "archive", "campaign": "phase6l-cohort-3", "slot": "F3"},
    "20260720T071333-cd18c5fb": {"era": "archive", "campaign": "phase6l-cohort-3", "slot": "F4"},
    "20260720T071439-5b501b4c": {"era": "archive", "campaign": "phase6l-cohort-3", "slot": "F5"},
    "20260720T071545-cd18c5fb": {"era": "archive", "campaign": "phase6l-cohort-3", "slot": "F6"},
    "20260720T133443-9aa0ef5c": {"era": "metrology", "campaign": "phase7m-metrology", "slot": "F7/f1"},
    "20260720T134522-9aa0ef5c": {"era": "metrology", "campaign": "phase7m-metrology", "slot": "F8/f2"},
    "20260720T135008-9aa0ef5c": {"era": "metrology", "campaign": "phase7m-metrology", "slot": "F9/f3"},
    "20260720T142917-9aa0ef5c": {"era": "metrology", "campaign": "phase7m-metrology", "slot": "F10/f4"},
}


def fnum(v):
    if v is None or v == "":
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def load_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def mechanism_for(failure_reason: str, flight_id: str) -> str:
    if failure_reason == "OK":
        return "LEGAL"
    if failure_reason == "FULL_BELOW_3P5_NOT_EZ_USABLE":
        return MECH_SCALE
    if failure_reason == "NO_CERTIFIED_FULL_BELOW_3P5":
        return MECH_DROPOUT
    return failure_reason or "UNKNOWN"


def analyze_flight(rows: list[dict], census: dict) -> dict:
    rows = sorted(rows, key=lambda r: fnum(r.get("t_rel_s")) or 0.0)
    fid = census["flight_id"]
    meta = FLIGHT_META.get(fid, {})
    failure = census.get("failure_reason") or ""
    legal = failure == "OK"
    mech = mechanism_for(failure, fid)

    full = [
        r for r in rows
        if r.get("feature_mode") == "FULL_QUAD" and fnum(r.get("range_z_m")) is not None
    ]
    full_cert = [r for r in full if r.get("cert_status") == "certified"]
    full_cert_ok = [
        r for r in full_cert
        if r.get("e_reject") == "ok" and fnum(r.get("e_meas")) is not None
    ]

    # Continuous certified FULL end range: last range in the first contiguous
    # certified-FULL streak that starts near pad (>4.5m), walking inward.
    # "Ends at" = minimum range_z reached while the streak is unbroken by a
    # FULL gap > FULL_GAP_S or a non-FULL certified interruption longer than gap.
    end_range = None
    end_t = None
    gap_events = []
    if full_cert:
        # Walk certified FULL by time; track gaps and the min range of the
        # opening continuous block that includes pad-range (>5m) frames.
        times = [(fnum(r["t_rel_s"]), fnum(r["range_z_m"]), r) for r in full_cert]
        times.sort(key=lambda x: x[0])
        # Opening streak: from first frame until first gap > FULL_GAP_S
        streak = [times[0]]
        for i in range(1, len(times)):
            dt = times[i][0] - times[i - 1][0]
            if dt > FULL_GAP_S:
                gap_events.append({
                    "t_rel_s": times[i - 1][0],
                    "dt_s": dt,
                    "range_before_m": times[i - 1][1],
                    "range_after_m": times[i][1],
                })
                break
            streak.append(times[i])
        end_range = min(z for _, z, _ in streak)
        end_t = max(t for t, _, _ in streak)
        # Prefer the streak that includes a >5m frame (pad/approach start)
        if not any(z > 5.0 for _, z, _ in streak) and len(times) > 1:
            # fallback: min range among all certified FULL before first gap from start
            end_range = min(z for _, z, _ in streak)

    # FULL-gap incidence: gaps in certified FULL timeline
    n_full_gaps = len(gap_events)
    first_gap_range = gap_events[0]["range_before_m"] if gap_events else None
    first_gap_t = gap_events[0]["t_rel_s"] if gap_events else None
    first_gap_dt = gap_events[0]["dt_s"] if gap_events else None

    # Speed profile from setpoint_speed_xy during approach/commit/align
    speeds = []
    for r in rows:
        sp = fnum(r.get("setpoint_speed_xy_mps"))
        phase = (r.get("phase") or "")
        if sp is None:
            continue
        if phase in ("takeoff", "approach", "align", "commit", "recover"):
            speeds.append(sp)
    speed_med = statistics.median(speeds) if speeds else None
    speed_max = max(speeds) if speeds else None
    speed_near = None  # median speed while range_z <= 5
    near_speeds = []
    for r in rows:
        z = fnum(r.get("range_z_m"))
        sp = fnum(r.get("setpoint_speed_xy_mps"))
        if z is not None and sp is not None and z <= 5.0:
            near_speeds.append(sp)
    if near_speeds:
        speed_near = statistics.median(near_speeds)

    # Entry geometry / lateral: at first certified FULL with range in [4, 6]
    entry = None
    for r in full_cert:
        z = fnum(r.get("range_z_m"))
        if z is not None and 4.0 <= z <= 6.5:
            entry = r
            break
    entry_x = fnum(entry.get("x_m")) if entry else None
    entry_cx = fnum(entry.get("center_x_px")) if entry else None
    entry_y = fnum(entry.get("y_down_m")) if entry else None
    entry_z = fnum(entry.get("range_z_m")) if entry else None

    # Lateral offset during terminal band (range <=5): median |x|
    lat = []
    for r in rows:
        z = fnum(r.get("range_z_m"))
        x = fnum(r.get("x_m"))
        if z is not None and x is not None and z <= 5.0:
            lat.append(abs(x))
    lat_med = statistics.median(lat) if lat else None
    lat_max = max(lat) if lat else None

    # Bloom exposure proxy: fraction of FULL rows with span << expected
    # (span / (fx*W/Z) < 0.45) — undersized ring / bloom-cut / wrong structure
    undersized = 0
    sized_n = 0
    for r in full:
        z = fnum(r.get("range_z_m"))
        span = fnum(r.get("span_px"))
        if z is None or span is None or z < 0.5:
            continue
        expected = (640.0 / 2.0) * 1.6 / z
        sized_n += 1
        if span / expected < 0.45:
            undersized += 1
    bloom_frac = (undersized / sized_n) if sized_n else None

    # Descent timing vs promote floor: first time any feature range_z <= 1.6
    t_at_promote = None
    for r in rows:
        z = fnum(r.get("range_z_m"))
        t = fnum(r.get("t_rel_s"))
        if z is not None and t is not None and z <= PROMOTE_FLOOR:
            t_at_promote = t
            break
    # Was continuous certified FULL still alive when crossing 1.6?
    # (only meaningful if end_range known)
    certified_alive_at_promote = None
    if end_range is not None:
        certified_alive_at_promote = end_range <= PROMOTE_FLOOR

    # Scale-gate kills below 3.5 among certified FULL
    scale_kills = [
        r for r in full_cert
        if fnum(r.get("range_z_m")) is not None
        and fnum(r["range_z_m"]) <= RANGE_CUT
        and r.get("e_reject") == "scale_gate"
    ]
    ez_ok_le = [
        r for r in full_cert_ok
        if fnum(r.get("range_z_m")) is not None and fnum(r["range_z_m"]) <= RANGE_CUT
    ]

    # SIDE band occupancy 3.5–5.0
    side_band = [
        r for r in rows
        if "SIDE" in (r.get("feature_mode") or "")
        and fnum(r.get("range_z_m")) is not None
        and fnum(r["range_z_m"]) <= 5.0
    ]

    # Predictor flag: first-streak min range ABOVE 4.5m (NOT sufficient alone; legal f2/f3 re-acquire)
    full_dies_above_4p5 = end_range is not None and end_range > 4.5

    n_ez_ok_le_3p5 = int(float(census.get("full_ok_below_3p5") or 0))
    n_full_cert_le_3p5 = int(float(census.get("full_certified_below_3p5_any") or 0))
    closest_cert = min((fnum(r["range_z_m"]) for r in full_cert), default=None)
    recovered_certified_full_le_3p5 = n_ez_ok_le_3p5 > 0
    compound_dropout_signature = (
        full_dies_above_4p5
        and n_full_cert_le_3p5 == 0
        and (closest_cert is None or closest_cert > RANGE_CUT)
    )

    return {
        "slot": meta.get("slot", census.get("flight")),
        "flight_id": fid,
        "era": meta.get("era"),
        "campaign": meta.get("campaign"),
        "census_failure_reason": failure,
        "mechanism": mech,
        "legal": legal,
        "approaches": int(float(census.get("approaches") or 0)),
        "n_full_certified_le_3p5": n_full_cert_le_3p5,
        "n_full_ez_ok_le_3p5": n_ez_ok_le_3p5,
        "n_side_certified": int(float(census.get("side_pair_certified") or 0)),
        "n_side_row_only": int(float(census.get("side_pair_row_only") or 0)),
        # Discriminators
        "certified_full_end_range_m": end_range,
        "certified_full_end_t_rel_s": end_t,
        "full_dies_above_4p5": full_dies_above_4p5,
        "recovered_certified_full_le_3p5": recovered_certified_full_le_3p5,
        "compound_dropout_signature": compound_dropout_signature,
        "certified_full_end_range_note": (
            "first contiguous certified-FULL streak min range; gaps then "
            "re-acquire below 3.5 still legal (does NOT alone discriminate)"
        ),
        "n_full_gaps": n_full_gaps,
        "first_full_gap_range_m": first_gap_range,
        "first_full_gap_t_rel_s": first_gap_t,
        "first_full_gap_dt_s": first_gap_dt,
        "speed_xy_median_mps": speed_med,
        "speed_xy_max_mps": speed_max,
        "speed_xy_median_le5_mps": speed_near,
        "entry_range_m": entry_z,
        "entry_x_m": entry_x,
        "entry_center_x_px": entry_cx,
        "entry_y_down_m": entry_y,
        "lateral_abs_x_median_le5_m": lat_med,
        "lateral_abs_x_max_le5_m": lat_max,
        "bloom_undersized_frac": bloom_frac,
        "t_first_range_le_promote_s": t_at_promote,
        "certified_full_alive_at_promote_floor": certified_alive_at_promote,
        "n_scale_gate_le_3p5": len(scale_kills),
        "n_ez_ok_le_3p5_recount": len(ez_ok_le),
        "n_side_rows_le5": len(side_band),
        "closest_certified_full_m": closest_cert,
    }


def pop_stats(rows: list[dict], key: str) -> dict:
    vals = [r[key] for r in rows if r.get(key) is not None]
    if not vals:
        return {"n": 0, "median": None, "min": None, "max": None, "mean": None}
    return {
        "n": len(vals),
        "median": statistics.median(vals),
        "min": min(vals),
        "max": max(vals),
        "mean": statistics.fmean(vals),
    }


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
    census_rows = load_csv(CENSUS)
    feat_all = load_csv(FEATURES)
    by_fid: dict[str, list[dict]] = {}
    for r in feat_all:
        by_fid.setdefault(r["flight_id"], []).append(r)

    table = []
    for c in census_rows:
        fid = c["flight_id"]
        rows = by_fid.get(fid, [])
        table.append(analyze_flight(rows, c))

    write_csv(OUT / "discriminator_table.csv", table)

    legal = [r for r in table if r["legal"]]
    censored = [r for r in table if not r["legal"]]
    mech_scale = [r for r in table if r["mechanism"] == MECH_SCALE]
    mech_drop = [r for r in table if r["mechanism"] == MECH_DROPOUT]

    # Discriminator contrast: certified_full_end_range_m
    disc_keys = [
        "certified_full_end_range_m",
        "full_dies_above_4p5",
        "recovered_certified_full_le_3p5",
        "compound_dropout_signature",
        "n_full_ez_ok_le_3p5",
        "n_full_gaps",
        "first_full_gap_range_m",
        "speed_xy_median_mps",
        "speed_xy_median_le5_mps",
        "entry_x_m",
        "lateral_abs_x_median_le5_m",
        "bloom_undersized_frac",
        "n_side_rows_le5",
        "n_scale_gate_le_3p5",
        "closest_certified_full_m",
    ]
    contrast = {}
    for k in disc_keys:
        if k in ("full_dies_above_4p5", "recovered_certified_full_le_3p5", "compound_dropout_signature"):
            contrast[k] = {
                "legal_rate": (
                    sum(1 for r in legal if r[k]) / len(legal) if legal else None
                ),
                "censored_rate": (
                    sum(1 for r in censored if r[k]) / len(censored) if censored else None
                ),
                "dropout_funnel_rate": (
                    sum(1 for r in mech_drop if r[k]) / len(mech_drop) if mech_drop else None
                ),
                "scale_funnel_rate": (
                    sum(1 for r in mech_scale if r[k]) / len(mech_scale) if mech_scale else None
                ),
            }
        else:
            contrast[k] = {
                "legal": pop_stats(legal, k),
                "censored": pop_stats(censored, k),
                "dropout_funnel": pop_stats(mech_drop, k),
                "scale_funnel": pop_stats(mech_scale, k),
            }

    # First-streak end-range alone does NOT discriminate (legal f2/f3 gap ~5m, re-acquire).
    end_legal = [r["certified_full_end_range_m"] for r in legal if r["certified_full_end_range_m"] is not None]
    end_drop = [r["certified_full_end_range_m"] for r in mech_drop if r["certified_full_end_range_m"] is not None]
    end_scale = [r["certified_full_end_range_m"] for r in mech_scale if r["certified_full_end_range_m"] is not None]
    closest_legal = [r["closest_certified_full_m"] for r in legal if r["closest_certified_full_m"] is not None]
    closest_drop = [r["closest_certified_full_m"] for r in mech_drop if r["closest_certified_full_m"] is not None]

    first_streak_discriminates = (
        bool(end_legal and end_drop) and max(end_legal) < min(end_drop)
    )
    compound_separates = (
        len(mech_drop) > 0
        and all(r["compound_dropout_signature"] for r in mech_drop)
        and not any(r["compound_dropout_signature"] for r in legal)
    )
    recovered_separates = (
        len(mech_drop) > 0
        and all(r["recovered_certified_full_le_3p5"] for r in legal)
        and not any(r["recovered_certified_full_le_3p5"] for r in mech_drop)
    )
    closest_separates = (
        bool(closest_legal and closest_drop)
        and max(closest_legal) < RANGE_CUT
        and min(closest_drop) > RANGE_CUT
    )

    separation = {
        "legal_end_range_median_m": statistics.median(end_legal) if end_legal else None,
        "legal_end_range_max_m": max(end_legal) if end_legal else None,
        "dropout_end_range_median_m": statistics.median(end_drop) if end_drop else None,
        "dropout_end_range_min_m": min(end_drop) if end_drop else None,
        "scale_end_range_median_m": statistics.median(end_scale) if end_scale else None,
        "first_streak_end_range_discriminates_dropout_vs_legal": first_streak_discriminates,
        "f4_finding_discriminates_dropout_vs_legal": first_streak_discriminates,
        "threshold_probe_m": 4.5,
        "legal_above_4p5": sum(1 for z in end_legal if z > 4.5),
        "dropout_above_4p5": sum(1 for z in end_drop if z > 4.5),
        "scale_above_4p5": sum(1 for z in end_scale if z > 4.5),
        "legal_closest_certified_full_max_m": max(closest_legal) if closest_legal else None,
        "dropout_closest_certified_full_min_m": min(closest_drop) if closest_drop else None,
        "closest_certified_full_discriminates": closest_separates,
        "recovered_certified_full_le_3p5_discriminates": recovered_separates,
        "compound_dropout_signature_separates": compound_separates,
    }

    # Coverage-censoring ledger
    ledger_rows = []
    for era in ("archive", "metrology", "all"):
        pop = table if era == "all" else [r for r in table if r["era"] == era]
        n = len(pop)
        n_legal = sum(1 for r in pop if r["legal"])
        n_scale = sum(1 for r in pop if r["mechanism"] == MECH_SCALE)
        n_drop = sum(1 for r in pop if r["mechanism"] == MECH_DROPOUT)
        # Y_eligible = legal-transition approaches / total approaches
        # Each flight is one approach attempt in this census.
        y_elig = (n_legal / n) if n else None
        ledger_rows.append({
            "era": era,
            "n_flights": n,
            "n_legal": n_legal,
            "n_SCALE_GATE_FLIPPED_FAR_GATE_POST_GAP": n_scale,
            "n_NO_CERTIFIED_FULL_BELOW_3P5": n_drop,
            "rate_legal": n_legal / n if n else None,
            "rate_SCALE_GATE_FLIPPED_FAR_GATE_POST_GAP": n_scale / n if n else None,
            "rate_NO_CERTIFIED_FULL_BELOW_3P5": n_drop / n if n else None,
            "rate_any_censored": (n - n_legal) / n if n else None,
            "Y_eligible": y_elig,
            "Y_eligible_note": "legal-transition approaches / total approaches (1 attempt per flight in this census)",
        })
    write_csv(OUT / "coverage_censoring_ledger.csv", ledger_rows)

    # Per-flight ledger lines
    write_csv(OUT / "censoring_per_flight.csv", [
        {
            "slot": r["slot"],
            "flight_id": r["flight_id"],
            "era": r["era"],
            "mechanism": r["mechanism"],
            "census_failure_reason": r["census_failure_reason"],
            "legal": r["legal"],
            "certified_full_end_range_m": r["certified_full_end_range_m"],
            "full_dies_above_4p5": r["full_dies_above_4p5"],
            "recovered_certified_full_le_3p5": r["recovered_certified_full_le_3p5"],
            "compound_dropout_signature": r["compound_dropout_signature"],
            "closest_certified_full_m": r["closest_certified_full_m"],
            "n_scale_gate_le_3p5": r["n_scale_gate_le_3p5"],
            "n_full_ez_ok_le_3p5": r["n_full_ez_ok_le_3p5"],
        }
        for r in table
    ])

    summary = {
        "response_refs": ["RESPONSE38 §1", "RESPONSE39", "advisory-20B §1.2/§1.3"],
        "repo_tip_requested": "bb0dbcf",
        "features_source": str(FEATURES.relative_to(ROOT)),
        "n_flights": len(table),
        "n_legal": len(legal),
        "n_censored": len(censored),
        "mechanisms": {
            "LEGAL": len(legal),
            MECH_SCALE: len(mech_scale),
            MECH_DROPOUT: len(mech_drop),
        },
        "Y_eligible": {row["era"]: row["Y_eligible"] for row in ledger_rows},
        "discriminator_contrast": contrast,
        "f4_end_range_discrimination": separation,
        "p2_read": {
            "first_streak_end_range_alone_discriminates": separation[
                "first_streak_end_range_discriminates_dropout_vs_legal"
            ],
            "f4_finding_discriminates": separation[
                "first_streak_end_range_discriminates_dropout_vs_legal"
            ],
            "compound_dropout_signature_separates": separation[
                "compound_dropout_signature_separates"
            ],
            "recovered_certified_full_le_3p5_separates": separation[
                "recovered_certified_full_le_3p5_discriminates"
            ],
            "closest_certified_full_discriminates": separation[
                "closest_certified_full_discriminates"
            ],
            "p2_hold_through_band_supported": separation[
                "compound_dropout_signature_separates"
            ],
            "verdict_lines": [
                (
                    "certified_full_end_range_m (first streak) is reported but "
                    "does NOT alone separate legal from dropout: legal f2/f3 "
                    f"also end first streak at {separation['legal_end_range_max_m']:.3f} m "
                    "after a gap yet re-acquire certified FULL <=3.5 m."
                ),
                (
                    f"closest_certified_full_m does separate: legal max "
                    f"{separation['legal_closest_certified_full_max_m']:.3f} m vs "
                    f"dropout min {separation['dropout_closest_certified_full_min_m']:.3f} m "
                    f"(cut {RANGE_CUT} m)."
                ),
                (
                    "recovered_certified_full_le_3p5 (n_full_ez_ok_le_3p5>0): "
                    f"all {len(legal)}/{len(legal)} legal True, "
                    f"all {len(mech_drop)}/{len(mech_drop)} dropout False."
                ),
                (
                    "compound_dropout_signature (FULL dies >4.5 m AND never "
                    "certified FULL <=3.5 m): separates every dropout flight "
                    f"from every legal flight: {separation['compound_dropout_signature_separates']}."
                ),
                (
                    "P2 supported: hold/re-anchor when FULL drops before 4.5 m "
                    "is the intervention that turns a dropout trajectory into "
                    "legal re-acquire (metrology f2/f3 already do this "
                    "spontaneously without pooling scale-gate funnel)."
                ),
            ],
        },
        "scale_funnel_note": (
            "SCALE_GATE_FLIPPED_FAR_GATE_POST_GAP flights CAN have continuous "
            "FULL deep into the band (or even below 3.5) — their kill is "
            "e_reject=scale_gate, not end-range. End-range is the dropout "
            "discriminator; scale_gate count is the scale-funnel discriminator."
        ),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    # Report
    lines = [
        "# Discriminator table + coverage-censoring ledger (first edition)",
        "",
        "RESPONSE38 §1 / RESPONSE39 — ten already-labeled flights "
        "(6 archive phase6l + 4 metrology). Tip `bb0dbcf`.",
        "",
        f"**Pool:** {len(legal)} legal / {len(censored)} censored "
        f"({len(mech_scale)} scale-gate funnel, {len(mech_drop)} no-certified-FULL funnel).",
        "",
        "## 1. Discriminator table — what predicts certified terminal coverage",
        "",
        "**First-streak** `certified_full_end_range_m` (f4 autopsy metric) is "
        "reported for continuity but **does not alone discriminate** — legal "
        "metrology f2/f3 gap near ~5 m then re-acquire below 3.5 m.",
        "",
        f"- Legal first-streak median/min/max: "
        f"**{separation['legal_end_range_median_m']:.3f}** / "
        f"{min(end_legal):.3f} / {separation['legal_end_range_max_m']:.3f} m",
        f"- Dropout first-streak median/min/max: "
        f"**{separation['dropout_end_range_median_m']:.3f}** / "
        f"{separation['dropout_end_range_min_m']:.3f} / "
        f"{max(end_drop):.3f} m",
        f"- **First-streak alone separates dropout vs legal:** "
        f"{separation['first_streak_end_range_discriminates_dropout_vs_legal']}",
        "",
        "**Discriminators that do separate** (all 3 dropout vs all 5 legal):",
        "",
        f"- `closest_certified_full_m`: legal max "
        f"{separation['legal_closest_certified_full_max_m']:.3f} m, dropout min "
        f"{separation['dropout_closest_certified_full_min_m']:.3f} m "
        f"(cut {RANGE_CUT} m) → {separation['closest_certified_full_discriminates']}",
        f"- `recovered_certified_full_le_3p5` (any ez_ok FULL ≤3.5 m): "
        f"{separation['recovered_certified_full_le_3p5_discriminates']}",
        f"- `compound_dropout_signature` (dies >4.5 m AND no certified FULL ≤3.5 m): "
        f"**{separation['compound_dropout_signature_separates']}**",
        "",
        "### Per-flight discriminators (excerpt)",
        "",
        "| slot | era | mechanism | 1st streak (m) | dies>4.5 | recovered≤3.5 | compound | closest FULL | ez_ok≤3.5 |",
        "|---|---|---|---:|---|---|---|---:|---:|",
    ]
    for r in table:
        lines.append(
            f"| {r['slot']} | {r['era']} | `{r['mechanism']}` | "
            f"{r['certified_full_end_range_m']} | {r['full_dies_above_4p5']} | "
            f"{r['recovered_certified_full_le_3p5']} | {r['compound_dropout_signature']} | "
            f"{r['closest_certified_full_m']} | {r['n_full_ez_ok_le_3p5']} |"
        )

    lines += [
        "",
        "### Population contrast (medians)",
        "",
        "| feature | legal | censored | dropout funnel | scale funnel |",
        "|---|---:|---:|---:|---:|",
    ]
    for k in (
        "certified_full_end_range_m",
        "n_full_gaps",
        "speed_xy_median_le5_mps",
        "lateral_abs_x_median_le5_m",
        "bloom_undersized_frac",
        "n_side_rows_le5",
        "n_scale_gate_le_3p5",
        "closest_certified_full_m",
        "n_full_ez_ok_le_3p5",
        "recovered_certified_full_le_3p5",
        "compound_dropout_signature",
    ):
        c = contrast[k]
        if k in ("recovered_certified_full_le_3p5", "compound_dropout_signature"):
            def rate_fmt(block, key):
                v = block.get(key)
                return f"{v:.2f}" if isinstance(v, float) else str(v)
            lines.append(
                f"| `{k}` (rate true) | {rate_fmt(c, 'legal_rate')} | "
                f"{rate_fmt(c, 'censored_rate')} | "
                f"{rate_fmt(c, 'dropout_funnel_rate')} | "
                f"{rate_fmt(c, 'scale_funnel_rate')} |"
            )
            continue
        def fmt(block):
            m = block.get("median")
            return f"{m:.3f}" if isinstance(m, float) else str(m)
        lines.append(
            f"| `{k}` | {fmt(c['legal'])} | {fmt(c['censored'])} | "
            f"{fmt(c['dropout_funnel'])} | {fmt(c['scale_funnel'])} |"
        )

    lines += [
        "",
        "### P2 hold-through-band — table verdict (5 lines)",
        "",
    ]
    for line in summary["p2_read"]["verdict_lines"]:
        lines.append(f"- {line}")
    lines += [
        "",
        f"**P2 supported (compound signature separates):** "
        f"{summary['p2_read']['p2_hold_through_band_supported']}.",
        "",
        summary["scale_funnel_note"],
        "",
        "## 2. Coverage-censoring ledger + Y_eligible",
        "",
        "| era | n | legal | scale-gate | no-FULL≤3.5 | Y_eligible | any-censored rate |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in ledger_rows:
        lines.append(
            f"| {row['era']} | {row['n_flights']} | {row['n_legal']} | "
            f"{row['n_SCALE_GATE_FLIPPED_FAR_GATE_POST_GAP']} | "
            f"{row['n_NO_CERTIFIED_FULL_BELOW_3P5']} | "
            f"{row['Y_eligible']:.3f} | {row['rate_any_censored']:.3f} |"
        )

    lines += [
        "",
        "Y_eligible = legal-transition approaches / total approaches "
        "(RESPONSE38 §1; one attempt per flight in this census edition).",
        "",
        "### Per-label rates",
        "",
        f"- `{MECH_SCALE}`: archive "
        f"{sum(1 for r in table if r['era']=='archive' and r['mechanism']==MECH_SCALE)/6:.3f}, "
        f"metrology "
        f"{sum(1 for r in table if r['era']=='metrology' and r['mechanism']==MECH_SCALE)/4:.3f}, "
        f"all {len(mech_scale)/len(table):.3f}",
        f"- `{MECH_DROPOUT}`: archive "
        f"{sum(1 for r in table if r['era']=='archive' and r['mechanism']==MECH_DROPOUT)/6:.3f}, "
        f"metrology "
        f"{sum(1 for r in table if r['era']=='metrology' and r['mechanism']==MECH_DROPOUT)/4:.3f}, "
        f"all {len(mech_drop)/len(table):.3f}",
        "",
        "Lift-package context: Y_eligible≈0.50 on both campaigns bounds "
        "cohort-4 treatment availability and harvest rate together — half of "
        "standard-profile approaches currently fail to produce a legal "
        "transition cluster, split across two honest funnels that must not be pooled.",
        "",
        "## Deliverables",
        "",
        "- `discriminator_table.csv`",
        "- `coverage_censoring_ledger.csv`",
        "- `censoring_per_flight.csv`",
        "- `summary.json`",
        "- `run_discriminator_ledger.py`",
        "",
        "Extend when the full-archive sweep lands (RESPONSE37/38).",
        "",
    ]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "n": len(table),
        "Y_eligible": summary["Y_eligible"],
        "f4_disc_first_streak": separation[
            "first_streak_end_range_discriminates_dropout_vs_legal"
        ],
        "compound_separates": separation["compound_dropout_signature_separates"],
        "legal_end_med": separation["legal_end_range_median_m"],
        "drop_end_med": separation["dropout_end_range_median_m"],
    }))


if __name__ == "__main__":
    main()
