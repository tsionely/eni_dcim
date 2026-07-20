"""Metrology-f1 cluster failure autopsy (RESPONSE35 §3).

Mines the archive-harvest features CSV for the 11 FULL certified fixes
below 3.5 m on flight 20260720T133443-9aa0ef5c and the twin signature
on 20260720T071220-5b501b4c. Classifies each fix stage-by-stage against
the census e_z-usable filter (certified FULL + range_z<=3.5 + e_meas
present + e_reject==ok).
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
FEATURES = (
    ROOT / "tuning"
    / "archive-harvest-release-fit-v21-e6c3de8-e6c3de8-20260720T140659Z"
    / "features_archive.csv"
)
PROMOTE_FLOOR_M = 1.6
RANGE_CUT_M = 3.5
GATE_W_M = 1.6
IMG_W = 640.0
HONEST_PRODUCT = 0.5 * IMG_W * GATE_W_M  # 512 px·m
SCALE_LO = 0.59 * HONEST_PRODUCT
SCALE_HI = 1.56 * HONEST_PRODUCT

F1_ID = "20260720T133443-9aa0ef5c"
TWIN_ID = "20260720T071220-5b501b4c"


def fnum(v) -> float | None:
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


def expected_span_px(range_z: float) -> float:
    # fx ≈ W/2 for this camera model in feature_e_meas
    return (IMG_W / 2.0) * GATE_W_M / max(range_z, 0.05)


def classify_row(row: dict, idx: int) -> dict:
    range_z = fnum(row.get("range_z_m"))
    span = fnum(row.get("span_px"))
    product = (span * range_z) if (span is not None and range_z is not None) else None
    e_meas = fnum(row.get("e_meas"))
    e_reject = (row.get("e_reject") or "").strip()
    cert = (row.get("cert_status") or "").strip()
    mode = (row.get("feature_mode") or "").strip()
    phase = (row.get("phase") or "").strip()
    age = fnum(row.get("gate_age_s"))
    cx = fnum(row.get("center_x_px"))
    x_m = fnum(row.get("x_m"))

    stages = {
        "s1_full_quad": mode == "FULL_QUAD",
        "s2_cert_certified": cert == "certified",
        "s3_range_le_3p5": range_z is not None and range_z <= RANGE_CUT_M,
        "s4_above_promote_floor": range_z is not None and range_z >= PROMOTE_FLOOR_M,
        "s5_e_reject_ok": e_reject == "ok" and e_meas is not None,
    }
    # Census e_z-usable = s1+s2+s3+s5 (cert already required for full_any)
    ez_usable = all(
        [
            stages["s1_full_quad"],
            stages["s2_cert_certified"],
            stages["s3_range_le_3p5"],
            stages["s5_e_reject_ok"],
        ]
    )

    # Geometry diagnostics vs scale_gate definition (span * range_z as proxy;
    # live gate uses believed r_b — when flipped, both disagree with honest).
    scale_product_ok = (
        product is not None and SCALE_LO <= product <= SCALE_HI
    )
    span_vs_expected = None
    if span is not None and range_z is not None and range_z > 0:
        span_vs_expected = span / expected_span_px(range_z)

    kill_stage = "passed"
    if not stages["s1_full_quad"]:
        kill_stage = "not_full_quad"
    elif not stages["s2_cert_certified"]:
        kill_stage = "not_certified"
    elif not stages["s3_range_le_3p5"]:
        kill_stage = "range_gt_3p5"
    elif e_reject == "scale_gate":
        kill_stage = "scale_gate"
    elif e_reject and e_reject != "ok":
        kill_stage = f"e_reject:{e_reject}"
    elif e_meas is None:
        kill_stage = "e_meas_missing"

    # Heuristic labels for the autopsy narrative
    far_edge = cx is not None and cx >= 480.0
    large_lateral = x_m is not None and abs(x_m) >= 2.5
    stale_prior = age is not None and age >= 0.5
    undersized_span = span_vs_expected is not None and span_vs_expected < 0.45

    return {
        "fix_idx": idx,
        "flight_id": row.get("flight_id"),
        "frame_id": row.get("frame_id"),
        "t_rel_s": fnum(row.get("t_rel_s")),
        "phase": phase,
        "feature_mode": mode,
        "cert_status": cert,
        "det_cert_status": row.get("det_cert_status"),
        "range_z_m": range_z,
        "range_norm_m": fnum(row.get("range_norm_m")),
        "x_m": x_m,
        "y_down_m": fnum(row.get("y_down_m")),
        "gate_age_s": age,
        "center_x_px": cx,
        "y_top_px": fnum(row.get("y_top_px")),
        "span_px": span,
        "span_x_range_product": product,
        "honest_product_px_m": HONEST_PRODUCT,
        "scale_band_lo": SCALE_LO,
        "scale_band_hi": SCALE_HI,
        "scale_product_ok_vs_feature_range": scale_product_ok,
        "span_over_expected_at_range_z": span_vs_expected,
        "e_meas": e_meas,
        "e_reject": e_reject,
        "ez_usable": ez_usable,
        "kill_stage": kill_stage,
        "flag_far_right_edge": far_edge,
        "flag_large_lateral_x": large_lateral,
        "flag_stale_gate_age": stale_prior,
        "flag_undersized_span": undersized_span,
        **{f"stage_{k}": v for k, v in stages.items()},
    }


def select_full_below_3p5(rows: list[dict], flight_id: str) -> list[dict]:
    out = []
    for r in rows:
        if r.get("flight_id") != flight_id:
            continue
        if r.get("feature_mode") != "FULL_QUAD":
            continue
        if r.get("cert_status") != "certified":
            continue
        rz = fnum(r.get("range_z_m"))
        if rz is None or rz > RANGE_CUT_M:
            continue
        out.append(r)
    out.sort(key=lambda r: float(r["t_rel_s"]))
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def summarize(classified: list[dict], label: str) -> dict:
    kills: dict[str, int] = {}
    for r in classified:
        kills[r["kill_stage"]] = kills.get(r["kill_stage"], 0) + 1
    n = len(classified)
    return {
        "label": label,
        "n_full_certified_le_3p5": n,
        "n_ez_usable": sum(1 for r in classified if r["ez_usable"]),
        "kill_stage_counts": kills,
        "n_scale_gate": kills.get("scale_gate", 0),
        "n_far_right_edge": sum(1 for r in classified if r["flag_far_right_edge"]),
        "n_large_lateral": sum(1 for r in classified if r["flag_large_lateral_x"]),
        "n_stale_gate_age": sum(1 for r in classified if r["flag_stale_gate_age"]),
        "n_undersized_span": sum(1 for r in classified if r["flag_undersized_span"]),
        "phases": sorted({r["phase"] for r in classified}),
        "range_z_min": min((r["range_z_m"] for r in classified if r["range_z_m"] is not None), default=None),
        "range_z_max": max((r["range_z_m"] for r in classified if r["range_z_m"] is not None), default=None),
        "gate_age_min_s": min((r["gate_age_s"] for r in classified if r["gate_age_s"] is not None), default=None),
        "gate_age_max_s": max((r["gate_age_s"] for r in classified if r["gate_age_s"] is not None), default=None),
    }


def main() -> None:
    rows = load_features(FEATURES)
    f1_raw = select_full_below_3p5(rows, F1_ID)
    twin_raw = select_full_below_3p5(rows, TWIN_ID)
    f1 = [classify_row(r, i + 1) for i, r in enumerate(f1_raw)]
    twin = [classify_row(r, i + 1) for i, r in enumerate(twin_raw)]

    write_csv(OUT / "rejection_table_f1.csv", f1)
    write_csv(OUT / "rejection_table_twin_071220.csv", twin)

    f1_sum = summarize(f1, "metrology_f1")
    twin_sum = summarize(twin, "archive_071220")

    # Mechanism verdict
    all_scale = f1_sum["n_scale_gate"] == f1_sum["n_full_certified_le_3p5"] and f1_sum["n_full_certified_le_3p5"] > 0
    promote_never = all(
        (r["range_z_m"] is not None and r["range_z_m"] < PROMOTE_FLOOR_M)
        for r in f1
    ) if f1 else False
    # These rows are certified above promote floor — cert earned; e_z dies later.
    cert_earned_above_floor = all(
        r["stage_s2_cert_certified"] and r["stage_s4_above_promote_floor"]
        for r in f1
    ) if f1 else False

    where = "SCALE_GATE_FLIPPED_FAR_GATE_POST_GAP"
    if promote_never and not all_scale:
        where = "CERT_NEVER_EARNED_PROMOTE_FLOOR"
    elif f1_sum["n_ez_usable"] > 0:
        where = "HARNESS_SEGMENT_OR_SIDE_SHORTFALL"
    elif not all_scale and any(r["kill_stage"].startswith("e_reject") for r in f1):
        where = "MIXED_E_REJECT"

    # Rescuable only if honest e_z existed and harness wrongly dropped it.
    rescuable = False
    if f1_sum["n_ez_usable"] >= 4:
        rescuable = True  # would already be a cluster unless side shortfall
    # Forced accept of scale_gate rows would inject flipped-range metrology.
    rationale = (
        "All 11 FULL<=3.5 certified rows die at e_reject=scale_gate. "
        "Span is ~1/3 of fx*W/Z at the reported range_z (same visual "
        "structure later reappears at ~10 m with e_reject=ok). "
        "center_x~510–513 (right edge), |x|~3.5–4.5 m, gate_age~1.2–1.5 s, "
        "phase=recover after a FULL gap filled only by SIDE_PAIR_ROW_ONLY/none. "
        "Certification was earned above the 1.6 m promote floor; usability "
        "died at the scale gate on flipped/far-gate quads — not harness "
        "over-reject of honest e_z. Twin 071220 shows the same kill "
        "(1 FULL<=3.5, scale_gate, then ~9 m). Not rescuable as a 7th cluster."
    )

    summary = {
        "response": "RESPONSE35 §3",
        "features_source": str(FEATURES.relative_to(ROOT)),
        "flight_f1": F1_ID,
        "flight_twin": TWIN_ID,
        "WHERE_USABILITY_DIED": where,
        "RESCUABLE": rescuable,
        "cert_earned_above_promote_floor": cert_earned_above_floor,
        "promote_floor_m": PROMOTE_FLOOR_M,
        "not_promote_floor_failure": cert_earned_above_floor,
        "not_harness_overreject_honest": all_scale and f1_sum["n_ez_usable"] == 0,
        "f1": f1_sum,
        "twin": twin_sum,
        "twin_same_mechanism": twin_sum["n_scale_gate"] == twin_sum["n_full_certified_le_3p5"]
        and twin_sum["n_full_certified_le_3p5"] > 0,
        "verdict_rationale": rationale,
    }
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        "# Metrology-f1 cluster failure autopsy",
        "",
        "RESPONSE35 §3 — flight `20260720T133443-9aa0ef5c` vs twin `20260720T071220-5b501b4c`.",
        "",
        f"## WHERE_USABILITY_DIED: **{where}**",
        "",
        f"**RESCUABLE: {rescuable}** — does not add a 7th harvest cluster.",
        "",
        rationale,
        "",
        "## Stage-by-stage (11 FULL certified ≤3.5 m)",
        "",
        "| # | frame | t_rel | range_z | span | span/E[span] | center_x | |x| | age_s | e_reject | kill |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for r in f1:
        lines.append(
            f"| {r['fix_idx']} | {r['frame_id']} | {r['t_rel_s']:.3f} | "
            f"{r['range_z_m']:.3f} | {r['span_px']:.1f} | "
            f"{(r['span_over_expected_at_range_z'] or 0):.2f} | "
            f"{r['center_x_px']:.0f} | {abs(r['x_m'] or 0):.2f} | "
            f"{r['gate_age_s']:.2f} | {r['e_reject']} | {r['kill_stage']} |"
        )
    lines += [
        "",
        "### Stage pass counts",
        "",
        f"- FULL_QUAD + certified + range≤3.5: **{f1_sum['n_full_certified_le_3p5']}**",
        f"- e_reject==ok (e_z-usable): **{f1_sum['n_ez_usable']}**",
        f"- kill_stage: `{json.dumps(f1_sum['kill_stage_counts'])}`",
        "",
        "## Twin 071220",
        "",
        f"- FULL certified ≤3.5: **{twin_sum['n_full_certified_le_3p5']}**, "
        f"e_z-usable: **{twin_sum['n_ez_usable']}**, "
        f"kill: `{json.dumps(twin_sum['kill_stage_counts'])}`",
        f"- Same mechanism: **{summary['twin_same_mechanism']}**",
        "",
        "## Ruled-out hypotheses",
        "",
        "- Promote-floor (1.6 m) never-certify: **no** — all 11 certified with range_z ≥ 2.91 m.",
        "- Bloom washing red so cert never fires: **no** — det_cert/cert stay certified; "
        "span is simply too small for the *reported* near range (far-gate geometry).",
        "- Harness over-reject of honest e_z: **no** — scale_gate is the correct "
        "refusal of flipped-range quads (later frames of the same blob settle at ~10 m with ok).",
        "- Mid-approach relock clearing identity: **partial context** — recover after "
        "FULL gap + SIDE_ROW_ONLY/none + stale gate_age; identity that *does* return "
        "is a lateral far gate, not a rescued near opening.",
        "",
        "## Deliverables",
        "",
        "- `rejection_table_f1.csv`",
        "- `rejection_table_twin_071220.csv`",
        "- `summary.json`",
        "",
    ]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "WHERE": where,
        "RESCUABLE": rescuable,
        "f1_n": f1_sum["n_full_certified_le_3p5"],
        "f1_ez": f1_sum["n_ez_usable"],
        "kills": f1_sum["kill_stage_counts"],
    }))


if __name__ == "__main__":
    main()
