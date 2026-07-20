"""RESPONSE48 amended three-task diagnostic round.

CSV-only: no simulator launch. Produces archaeology-first wrong-sign
disclosure, corrected event-support re-score, shadow residual split
diagnostics, and era/applicability ledger artifacts.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tuning"))

from archive_harvest_release_fit_v21 import SIGMA_A_GATE  # noqa: E402
from run_l1_perception_replay import assert_mock_safe  # noqa: E402
from run_shadow_residual_diagnostics import (  # noqa: E402
    cluster_balanced_coverage,
    cluster_bootstrap_fast,
    fnum,
    fit_mean_values,
    fit_release_fast,
    flight_loao_sensitivity_fast,
    loao_sensitivity_fast,
    shadow_samples,
)


TASK_A_DIR = ROOT / "tuning" / "taskA-full-archive-retro-census-bb0dbcf-20260720T165623Z"
TASK_B_DIR = ROOT / "tuning" / "taskB-five-cluster-DIAGNOSTIC-bb0dbcf-20260720T183318Z"
OUT_PREFIX = "response48-amended-DIAGNOSTIC"
WRONG_SIGN_CRITERION = ROOT / "docs" / "criteria" / "wrong_sign_rescore_equivalence.md"
SHADOW_CRITERION = ROOT / "docs" / "criteria" / "shadow_fit_decision_structure.md"
DISCOVERY_OVERLAP_IDS = {
    "20260720T071112-cd18c5fb",
    "20260720T071333-cd18c5fb",
    "20260720T135008-9aa0ef5c",
}
OFF_TARGET_DISCOVERY_IDS = {
    "20260720T071545-cd18c5fb",
    "20260720T134522-9aa0ef5c",
}
NEEDED_DEADBAND = 0.02
LEGACY_E_DEADBAND = 0.03
LEGACY_PRODUCT_EPS = -1e-6
STEP_THRESHOLD_MPS = 0.08
CORRIDOR_M = 0.30


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def git_head() -> tuple[str, str]:
    head = git("rev-parse", "HEAD")
    return head, head[:7]


def last_commit_for(path: Path) -> str:
    return git("log", "-1", "--format=%H", "--", str(path.relative_to(ROOT)))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    keys: list[str] = list(fieldnames or [])
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def era_family(era: str) -> str:
    for prefix in ["phase3", "phase4", "phase5", "phase6", "phase7"]:
        if era.startswith(prefix):
            return prefix
    return era or "unknown"


def mean_or_blank(values: list[float]) -> float | str:
    return statistics.fmean(values) if values else ""


def sign_violation(cmd: float | None, needed_e: float | None,
                   cmd_deadband: float = NEEDED_DEADBAND,
                   e_deadband: float = NEEDED_DEADBAND) -> bool:
    if cmd is None or needed_e is None:
        return False
    if abs(cmd) <= cmd_deadband or abs(needed_e) <= e_deadband:
        return False
    return cmd * needed_e < 0.0


def opposition_to_velocity(cmd: float | None, velocity: float | None,
                           cmd_deadband: float = NEEDED_DEADBAND,
                           v_deadband: float = NEEDED_DEADBAND) -> bool:
    if cmd is None or velocity is None:
        return False
    if abs(cmd) <= cmd_deadband or abs(velocity) <= v_deadband:
        return False
    return cmd * velocity < 0.0


def legacy_wrong_sign(row: dict[str, str]) -> bool:
    cmd = fnum(row.get("terminal_vz_up_mps"))
    ez = fnum(row.get("e_meas"))
    return (
        cmd is not None and ez is not None
        and abs(ez) > LEGACY_E_DEADBAND
        and cmd * ez < LEGACY_PRODUCT_EPS
    )


def select_event_rows(trace_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in trace_rows:
        grouped[(row.get("flight_id", ""), row.get("trial", ""), row.get("mono_ns", ""))].append(row)
    selected = []
    for key in sorted(grouped):
        group = grouped[key]
        fed = [r for r in group if truthy(r.get("fed"))]
        chosen = fed[0] if fed else group[0]
        chosen = dict(chosen)
        chosen["_trace_duplicate_count"] = str(len(group))
        chosen["_selected_fed_row"] = str(bool(fed))
        selected.append(chosen)
    return selected


def archaeology_and_rescore(task_b_dir: Path, out_dir: Path) -> dict[str, Any]:
    rows = read_csv(task_b_dir / "DIAGNOSTIC_r26_1_anchor_trial_rows.csv")
    restamp = read_csv(task_b_dir / "DIAGNOSTIC_r26_1_restamp_verdict.csv")[0]
    term_rows = [r for r in rows if r.get("shadow_owner") == "term"]
    term_side_rows = [
        r for r in term_rows
        if r.get("active_source") == "SIDE_PAIR"
        and fnum(r.get("shadow_vz_cmd_new_mps")) is not None
    ]
    event_rows = select_event_rows(term_side_rows)

    lineage_raw = git(
        "log", "--reverse", "--format=%H%x09%h%x09%s",
        "-G", "wrong_sign|wrong_sign_command_rows|terminal_vz_up_mps",
        "--", "tuning/run_archive_retro_census_and_diagnostics.py",
    )
    lineage_rows = []
    for line in lineage_raw.splitlines():
        parts = line.split("\t", 2)
        if len(parts) == 3:
            lineage_rows.append({
                "commit": parts[0],
                "short": parts[1],
                "subject": parts[2],
            })
    write_csv(out_dir / "01_wrong_sign_harness_lineage.csv", lineage_rows)

    legacy_flagged = []
    for idx, row in enumerate(term_rows):
        if legacy_wrong_sign(row):
            legacy_flagged.append({
                "term_row_index": idx,
                "flight_id": row.get("flight_id", ""),
                "trial": row.get("trial", ""),
                "frame_id": row.get("frame_id", ""),
                "mono_ns": row.get("mono_ns", ""),
                "fed": row.get("fed", ""),
                "active_source": row.get("active_source", ""),
                "terminal_vz_up_mps": row.get("terminal_vz_up_mps", ""),
                "e_meas": row.get("e_meas", ""),
                "applied_e_z": row.get("applied_e_z", ""),
                "truth_vz_up_mps": row.get("truth_vz_up_mps", ""),
                "legacy_formula": (
                    "shadow_owner=='term'; cmd=terminal_vz_up_mps; "
                    "ez=e_meas; abs(ez)>0.03; cmd*ez<-1e-6"
                ),
            })
    write_csv(out_dir / "01_wrong_sign_legacy_28_rows.csv", legacy_flagged)

    mask_rows = [
        {
            "layer": "all_trace_rows",
            "rows": len(rows),
            "unique_events": len({(r.get("flight_id"), r.get("trial"), r.get("mono_ns")) for r in rows}),
            "selection": "all DIAGNOSTIC_r26_1_anchor_trial_rows rows",
        },
        {
            "layer": "legacy_term_rows",
            "rows": len(term_rows),
            "unique_events": len({(r.get("flight_id"), r.get("trial"), r.get("mono_ns")) for r in term_rows}),
            "selection": "shadow_owner == 'term'",
        },
        {
            "layer": "legacy_28_formula_rows",
            "rows": len(legacy_flagged),
            "unique_events": len({(r.get("flight_id"), r.get("trial"), r.get("mono_ns")) for r in legacy_flagged}),
            "selection": "legacy formula positive over legacy_term_rows",
        },
        {
            "layer": "traceability_term_side_with_new_command",
            "rows": len(term_side_rows),
            "unique_events": len({(r.get("flight_id"), r.get("trial"), r.get("mono_ns")) for r in term_side_rows}),
            "selection": "shadow_owner == 'term', active_source == SIDE_PAIR, shadow_vz_cmd_new_mps populated",
        },
        {
            "layer": "command_event_support",
            "rows": len(event_rows),
            "unique_events": len({(r.get("flight_id"), r.get("trial"), r.get("mono_ns")) for r in event_rows}),
            "selection": "unique (flight_id, trial, mono_ns); fed=True row selected when duplicated",
        },
        {
            "layer": "sign_evaluable_events",
            "rows": sum(
                1 for r in event_rows
                if abs(fnum(r.get("shadow_vz_cmd_new_mps")) or 0.0) > NEEDED_DEADBAND
            ),
            "unique_events": sum(
                1 for r in event_rows
                if abs(fnum(r.get("shadow_vz_cmd_new_mps")) or 0.0) > NEEDED_DEADBAND
            ),
            "selection": "command events with abs(new_cmd)>0.02",
        },
        {
            "layer": "zero_neutral_on_support",
            "rows": sum(
                1 for r in event_rows
                if fnum(r.get("shadow_vz_cmd_new_mps")) is not None
                and abs(fnum(r.get("shadow_vz_cmd_new_mps")) or 0.0) <= NEEDED_DEADBAND
            ),
            "unique_events": sum(
                1 for r in event_rows
                if fnum(r.get("shadow_vz_cmd_new_mps")) is not None
                and abs(fnum(r.get("shadow_vz_cmd_new_mps")) or 0.0) <= NEEDED_DEADBAND
            ),
            "selection": "numeric zero/neutral commands remain on support and score as nonviolations",
        },
    ]
    write_csv(out_dir / "01_wrong_sign_mask_accounting.csv", mask_rows)

    paired_rows = []
    off_support_rows = []
    prev_old_cmd = None
    prev_new_cmd = None
    old_step = 0
    new_step = 0
    for idx, row in enumerate(event_rows, start=1):
        old_cmd = fnum(row.get("shadow_vz_cmd_old_mps"))
        new_cmd = fnum(row.get("shadow_vz_cmd_new_mps"))
        needed = fnum(row.get("applied_e_z"))
        velocity = fnum(row.get("truth_vz_up_mps"))
        reasons = []
        if old_cmd is None:
            reasons.append("old_cmd_absent")
        if new_cmd is None:
            reasons.append("new_cmd_absent")
        if needed is None:
            reasons.append("needed_correction_absent")
        if prev_old_cmd is not None and old_cmd is not None and abs(old_cmd - prev_old_cmd) > STEP_THRESHOLD_MPS:
            old_step += 1
        if prev_new_cmd is not None and new_cmd is not None and abs(new_cmd - prev_new_cmd) > STEP_THRESHOLD_MPS:
            new_step += 1
        if old_cmd is not None:
            prev_old_cmd = old_cmd
        if new_cmd is not None:
            prev_new_cmd = new_cmd
        rec = {
            "event_index": idx,
            "flight_id": row.get("flight_id", ""),
            "trial": row.get("trial", ""),
            "mono_ns": row.get("mono_ns", ""),
            "frame_id": row.get("frame_id", ""),
            "fed": row.get("fed", ""),
            "trace_duplicate_count": row.get("_trace_duplicate_count", ""),
            "selected_fed_row": row.get("_selected_fed_row", ""),
            "range_z_m": row.get("range_z_m", ""),
            "needed_correction_col": "applied_e_z",
            "needed_correction_m": needed if needed is not None else "",
            "old_cmd_col": "shadow_vz_cmd_old_mps",
            "old_cmd_mps": old_cmd if old_cmd is not None else "",
            "new_cmd_col": "shadow_vz_cmd_new_mps",
            "new_cmd_mps": new_cmd if new_cmd is not None else "",
            "command_deadband_mps": NEEDED_DEADBAND,
            "needed_deadband_m": NEEDED_DEADBAND,
            "old_wrong_sign_needed": sign_violation(old_cmd, needed),
            "new_wrong_sign_needed": sign_violation(new_cmd, needed),
            "new_excess_violation": (
                sign_violation(new_cmd, needed)
                and not sign_violation(old_cmd, needed)
            ),
            "zero_neutral_event": (
                new_cmd is not None and abs(new_cmd) <= NEEDED_DEADBAND
            ),
            "sign_evaluable_event": (
                new_cmd is not None and needed is not None
                and abs(new_cmd) > NEEDED_DEADBAND
                and abs(needed) > NEEDED_DEADBAND
            ),
            "velocity_reference_col": "truth_vz_up_mps",
            "velocity_reference_mps": velocity if velocity is not None else "",
            "old_opposition_to_velocity_rate": opposition_to_velocity(old_cmd, velocity),
            "new_opposition_to_velocity_rate": opposition_to_velocity(new_cmd, velocity),
            "support_status": "paired_common_support" if not reasons else "off_support",
            "off_support_reason": ";".join(reasons),
        }
        if reasons:
            off_support_rows.append(rec)
        else:
            paired_rows.append(rec)
    write_csv(out_dir / "01_wrong_sign_paired_common_support_events.csv", paired_rows)
    write_csv(
        out_dir / "01_wrong_sign_off_support_events.csv",
        off_support_rows,
        fieldnames=list(paired_rows[0].keys()) if paired_rows else None,
    )

    approach_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in paired_rows:
        approach_groups[(str(row["flight_id"]), str(row["trial"]))].append(row)
    approach_rows = []
    for (fid, trial), group in sorted(approach_groups.items()):
        old_v = sum(1 for r in group if r["old_wrong_sign_needed"])
        new_v = sum(1 for r in group if r["new_wrong_sign_needed"])
        excess = sum(1 for r in group if r["new_excess_violation"])
        old_opp = sum(1 for r in group if r["old_opposition_to_velocity_rate"])
        new_opp = sum(1 for r in group if r["new_opposition_to_velocity_rate"])
        approach_rows.append({
            "flight_id": fid,
            "trial": trial,
            "paired_command_events": len(group),
            "sign_evaluable_events": sum(1 for r in group if r["sign_evaluable_event"]),
            "zero_neutral_events_on_support": sum(1 for r in group if r["zero_neutral_event"]),
            "old_wrong_sign_needed": old_v,
            "new_wrong_sign_needed": new_v,
            "new_excess_wrong_sign_events": excess,
            "equivalence_margin": 0,
            "wrong_sign_clause_result": "PASS" if excess == 0 and new_v == 0 else "FAIL_CLOSED",
            "old_opposition_to_velocity_events": old_opp,
            "new_opposition_to_velocity_events": new_opp,
            "opposition_to_velocity_rate_delta": (
                (new_opp / len(group)) - (old_opp / len(group)) if group else ""
            ),
            "opposition_to_velocity_note": "telemetry descriptor only; no pass/fail semantics",
        })
    write_csv(out_dir / "01_wrong_sign_approach_level_rescore.csv", approach_rows)

    definitions = [
        {
            "definition": "legacy_harness_raw_e_meas_trace_rows",
            "path": "old_actual_applied",
            "rows": len(term_rows),
            "events": len({(r.get("flight_id"), r.get("trial"), r.get("mono_ns")) for r in term_rows}),
            "violations": len(legacy_flagged),
            "status": "INVALID_TEST_WRONG_SUPPORT_AND_MASK",
            "formula": "terminal_vz_up_mps vs e_meas; abs(e_meas)>0.03; trace rows as units",
        },
        {
            "definition": "registered_needed_correction_event_support",
            "path": "old_policy_forecast",
            "rows": len(paired_rows),
            "events": len(paired_rows),
            "violations": sum(1 for r in paired_rows if r["old_wrong_sign_needed"]),
            "status": "PASS" if not any(r["old_wrong_sign_needed"] for r in paired_rows) else "FAIL",
            "formula": "shadow_vz_cmd_old_mps vs applied_e_z; abs both >0.02; event support",
        },
        {
            "definition": "registered_needed_correction_event_support",
            "path": "new_shadow_forecast",
            "rows": len(paired_rows),
            "events": len(paired_rows),
            "violations": sum(1 for r in paired_rows if r["new_wrong_sign_needed"]),
            "status": "PASS" if not any(r["new_wrong_sign_needed"] for r in paired_rows) else "FAIL_CLOSED",
            "formula": "shadow_vz_cmd_new_mps vs applied_e_z; abs both >0.02; event support",
        },
        {
            "definition": "opposition_to_velocity_rate",
            "path": "old_policy_forecast",
            "rows": len(paired_rows),
            "events": len(paired_rows),
            "violations": sum(1 for r in paired_rows if r["old_opposition_to_velocity_rate"]),
            "status": "TELEMETRY_ONLY",
            "formula": "shadow_vz_cmd_old_mps vs truth_vz_up_mps; descriptor only",
        },
        {
            "definition": "opposition_to_velocity_rate",
            "path": "new_shadow_forecast",
            "rows": len(paired_rows),
            "events": len(paired_rows),
            "violations": sum(1 for r in paired_rows if r["new_opposition_to_velocity_rate"]),
            "status": "TELEMETRY_ONLY",
            "formula": "shadow_vz_cmd_new_mps vs truth_vz_up_mps; descriptor only",
        },
    ]
    write_csv(out_dir / "01_wrong_sign_definition_scorecard.csv", definitions)

    historical = historical_zero_green_rescore(out_dir)

    first_lineage = lineage_rows[0]["commit"] if lineage_rows else ""
    archaeology_md = [
        "# WRONG-SIGN ARCHAEOLOGY",
        "",
        "Scope: DIAGNOSTIC, CSV-only, archaeology before re-score.",
        "",
        "## Ancestor Harness",
        "",
        f"- First harness-lineage hit: `{first_lineage}`.",
        "- The historical restamp count came from `tuning/run_archive_retro_census_and_diagnostics.py`.",
        "- Formula reconstructed from the ancestor harness:",
        "",
        "```python",
        "term_rows = [r for r in all_rows if r.get('shadow_owner') == TERM_OWNER]",
        "cmd = fnum(row.get('terminal_vz_up_mps'))",
        "ez = fnum(row.get('e_meas'))",
        "if cmd is not None and ez is not None and abs(ez) > 0.03 and cmd * ez < -1e-6:",
        "    wrong_sign += 1",
        "```",
        "",
        "This did not encode command-vs-velocity directly. It is still marked `INVALID_TEST_WRONG_SUPPORT_AND_MASK` because it used trace rows as units, raw `e_meas`, the old 0.03 e deadband, and no old/new paired event support.",
        "",
        "## Count Reconstruction",
        "",
        f"- Legacy term rows: `{len(term_rows)}`.",
        f"- Legacy formula positives: `{len(legacy_flagged)}`.",
        f"- Traceability term/SIDE rows with new command populated: `{len(term_side_rows)}`.",
        f"- Unique command events after `(flight_id, trial, mono_ns)` dedupe and `fed=True` selection: `{len(event_rows)}`.",
        f"- Sign-evaluable events after 0.02 command deadband: `{sum(1 for r in event_rows if abs(fnum(r.get('shadow_vz_cmd_new_mps')) or 0.0) > NEEDED_DEADBAND)}`.",
        f"- Zero/neutral command events on support: `{sum(1 for r in event_rows if fnum(r.get('shadow_vz_cmd_new_mps')) is not None and abs(fnum(r.get('shadow_vz_cmd_new_mps')) or 0.0) <= NEEDED_DEADBAND)}`.",
        "",
        "The apparent `16 -> 13` contraction is a trace-row to sign-evaluable-row contraction, not a support loss: three trace rows carry numeric zero/neutral commands. After event dedupe, they are two zero-command events that remain on support and score as nonviolations.",
        "",
        "## Corrected Criterion",
        "",
        f"- Criterion file: `{WRONG_SIGN_CRITERION.relative_to(ROOT)}`.",
        f"- Criterion commit: `{last_commit_for(WRONG_SIGN_CRITERION)}`.",
        f"- Corrected wrong-sign clause result on paired common support: `{approach_rows[0]['wrong_sign_clause_result'] if approach_rows else 'NO_SUPPORT'}`.",
        f"- Historical zero-wrong-sign artifacts re-scored: `{historical['artifacts']}`.",
        "",
    ]
    (out_dir / "01_wrong_sign_archaeology.md").write_text("\n".join(archaeology_md), encoding="utf-8")

    base_liveness = (
        int(restamp.get("legal_trial_count") or 0) > 0
        and int(restamp.get("owner_term_side_rows") or 0) > 0
        and int(restamp.get("side_shadow_capture_rows") or 0) > 0
        and (fnum(restamp.get("max_admission_score")) or 999.0) <= CORRIDOR_M
        and int(restamp.get("phase_changed_rows") or 0) == 0
    )
    return {
        "legacy_wrong_sign_rows": len(legacy_flagged),
        "legacy_status": "INVALID_TEST_WRONG_SUPPORT_AND_MASK",
        "trace_term_side_rows": len(term_side_rows),
        "command_event_support": len(event_rows),
        "sign_evaluable_events": sum(
            1 for r in event_rows
            if abs(fnum(r.get("shadow_vz_cmd_new_mps")) or 0.0) > NEEDED_DEADBAND
        ),
        "zero_neutral_events": sum(
            1 for r in event_rows
            if fnum(r.get("shadow_vz_cmd_new_mps")) is not None
            and abs(fnum(r.get("shadow_vz_cmd_new_mps")) or 0.0) <= NEEDED_DEADBAND
        ),
        "paired_common_support_events": len(paired_rows),
        "new_excess_wrong_sign_events": sum(1 for r in paired_rows if r["new_excess_violation"]),
        "base_liveness_pass": base_liveness,
        "old_event_step_beyond_slew": old_step,
        "new_event_step_beyond_slew": new_step,
        "historical_zero_green_artifacts_rescored": historical["artifacts"],
    }


def historical_zero_green_rescore(out_dir: Path) -> dict[str, int]:
    artifact_rows = []
    event_rows = []
    for summary in sorted((ROOT / "tuning").glob("terminal-ab-*/summary.md")):
        text = summary.read_text(encoding="utf-8", errors="ignore")
        if "wrong-sign rows 0" not in text:
            continue
        run_dir = summary.parent
        term_dir = run_dir / "term_status_live"
        if not term_dir.exists():
            continue
        total_events = 0
        sign_events = 0
        violations = 0
        opp_vel = 0
        for csv_path in sorted(term_dir.glob("*.csv")):
            rows = read_csv(csv_path)
            for row in rows:
                if row.get("owner") != "term":
                    continue
                # TermStatus carries both the semantic vertical/up command
                # (`vz_up`) and the body-z adapter channel (`v_bz_applied`).
                # The registered criterion is sign(command) vs sign(e), so
                # use the world/up command; body-z remains telemetry.
                cmd = fnum(row.get("vz_up"))
                e = fnum(row.get("e_z"))
                vel = fnum(row.get("truth_vz_up_mps"))
                if cmd is None or e is None:
                    continue
                total_events += 1
                sign_eval = abs(cmd) > NEEDED_DEADBAND and abs(e) > NEEDED_DEADBAND
                if sign_eval:
                    sign_events += 1
                bad = sign_violation(cmd, e)
                if bad:
                    violations += 1
                ov = opposition_to_velocity(cmd, vel)
                if ov:
                    opp_vel += 1
                event_rows.append({
                    "artifact": run_dir.name,
                    "term_status_csv": str(csv_path.relative_to(ROOT)),
                    "row": row.get("row", ""),
                    "ts_ns": row.get("ts_ns", ""),
                    "cmd_col": "vz_up",
                    "cmd_mps": cmd,
                    "needed_e_col": "e_z",
                    "needed_e_m": e,
                    "registered_wrong_sign": bad,
                    "body_z_adapter_v_bz_applied": row.get("v_bz_applied", ""),
                    "opposition_to_velocity_rate": ov,
                })
        artifact_rows.append({
            "artifact": run_dir.name,
            "historical_summary_claim": "wrong-sign rows 0",
            "registered_definition": "sign(command) vs sign(e_z), deadband 0.02",
            "command_events": total_events,
            "sign_evaluable_events": sign_events,
            "registered_wrong_sign_events": violations,
            "opposition_to_velocity_events": opp_vel,
            "rescore_status": "PASS" if violations == 0 else "FAIL_REVIEW",
        })
    write_csv(out_dir / "01_historical_zero_wrong_sign_green_rescore.csv", artifact_rows)
    write_csv(out_dir / "01_historical_zero_wrong_sign_green_event_rows.csv", event_rows)
    return {"artifacts": len(artifact_rows), "events": len(event_rows)}


def target_set_for_sample(row: dict[str, Any]) -> str:
    fid = str(row.get("flight_id", ""))
    if fid in DISCOVERY_OVERLAP_IDS:
        return "discovery_overlap_3"
    return "confirmatory_20"


def fit_rows_for_set(samples: list[dict[str, Any]], set_name: str) -> list[dict[str, Any]]:
    if set_name == "pooled_23":
        return list(samples)
    if set_name == "discovery_overlap_3":
        return [r for r in samples if r.get("flight_id") in DISCOVERY_OVERLAP_IDS]
    if set_name == "confirmatory_20":
        return [r for r in samples if r.get("flight_id") not in DISCOVERY_OVERLAP_IDS]
    if set_name == "legacy_discovery_appendix_4_analyzable":
        return [
            r for r in samples
            if r.get("flight_id") in DISCOVERY_OVERLAP_IDS
            or r.get("flight_id") in OFF_TARGET_DISCOVERY_IDS
        ]
    raise ValueError(set_name)


def annotate_samples(samples: list[dict[str, Any]], policy: str) -> list[dict[str, Any]]:
    out = []
    for row in samples:
        rec = dict(row)
        rec["anchor_policy"] = policy
        rec["target_set"] = target_set_for_sample(rec)
        out.append(rec)
    return out


def fit_set(policy: str, set_name: str, rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    fit = fit_release_fast(rows)
    boot = cluster_bootstrap_fast(rows) if len({r["cluster_id"] for r in rows}) >= 2 else {
        "cluster_bootstrap_n": 0,
        "cluster_bootstrap_u95_sigma_a_mps2": "",
    }
    loao = loao_sensitivity_fast(rows) if len({r["cluster_id"] for r in rows}) >= 2 else []
    coverage, max_age, monotone = cluster_balanced_coverage(rows, fit)
    u95_vals = [
        fnum(fit.get("profile_u95_sigma_a_mps2")),
        fnum(boot.get("cluster_bootstrap_u95_sigma_a_mps2")),
    ]
    u95 = max(v for v in u95_vals if v is not None)
    summary = {
        "diagnostic_only": True,
        "target_set": set_name,
        "anchor_policy": policy,
        "n_clusters": len({r["cluster_id"] for r in rows}),
        "n_flights": len({r["flight_id"] for r in rows}),
        "n_rows": len(rows),
        "point_sigma_a_mps2": fit["sigma_a_mps2"],
        "profile_u95_sigma_a_mps2": fit["profile_u95_sigma_a_mps2"],
        "cluster_bootstrap_u95_sigma_a_mps2": boot.get("cluster_bootstrap_u95_sigma_a_mps2", ""),
        "u95_conservative_mps2": u95,
        "sigma_0_mps": fit["sigma_0_mps"],
        "profile_nearly_flat": fit["profile_nearly_flat"],
        "max_validated_age": max_age,
        "coverage_monotone_degrade": monotone,
        "gate_0p35_push": u95 > SIGMA_A_GATE,
    }
    for row in loao:
        row["target_set"] = set_name
        row["anchor_policy"] = policy
    for row in coverage:
        row["target_set"] = set_name
        row["anchor_policy"] = policy
    return summary, [boot], loao, coverage


def cluster_regime_labels(samples: list[dict[str, Any]]) -> dict[str, str]:
    by_cluster: dict[str, set[str]] = defaultdict(set)
    for row in samples:
        if row.get("command_regime"):
            by_cluster[str(row["cluster_id"])].add(str(row["command_regime"]))
    return {cid: ";".join(sorted(vals)) for cid, vals in by_cluster.items()}


def shadow_fit_diagnostics(task_a_dir: Path, out_dir: Path) -> dict[str, Any]:
    old_base = read_csv(task_a_dir / "forced_withhold_samples.csv")
    clusters = read_csv(task_a_dir / "expanded_census_clusters.csv")
    old_samples = annotate_samples([dict(r) for r in old_base], "old_attenuated_anchor")
    new_samples = annotate_samples(shadow_samples(old_base), "shadow_unattenuated_anchor")
    for row in old_samples:
        row["r_v_old_mps"] = row.get("r_v_mps", "")
    for row in new_samples:
        row["r_v_new_mps"] = row.get("r_v_mps", "")

    write_csv(out_dir / "02_shadow_forced_withhold_samples.csv", new_samples)

    set_names = [
        "discovery_overlap_3",
        "confirmatory_20",
        "pooled_23",
        "legacy_discovery_appendix_4_analyzable",
    ]
    release_rows = []
    boot_rows = []
    loao_rows = []
    coverage_rows = []
    for set_name in set_names:
        for policy, samples in [
            ("old_attenuated_anchor", old_samples),
            ("shadow_unattenuated_anchor", new_samples),
        ]:
            rows = fit_rows_for_set(samples, set_name)
            if not rows:
                continue
            print(f"fit {set_name} {policy} clusters={len({r['cluster_id'] for r in rows})}", flush=True)
            rel, boot, loao, coverage = fit_set(policy, set_name, rows)
            release_rows.append(rel)
            for row in boot:
                row["target_set"] = set_name
                row["anchor_policy"] = policy
                boot_rows.append(row)
            loao_rows.extend(loao)
            coverage_rows.extend(coverage)
    write_csv(out_dir / "02_shadow_old_vs_new_release_fit_by_set.csv", release_rows)
    write_csv(out_dir / "02_shadow_old_vs_new_cluster_bootstrap_by_set.csv", boot_rows)
    write_csv(out_dir / "02_shadow_old_vs_new_loao_by_set.csv", loao_rows)
    write_csv(out_dir / "02_shadow_old_vs_new_balanced_coverage_by_set.csv", coverage_rows)

    meta = {row["cluster_id"]: row for row in clusters}
    old_by: dict[str, list[dict[str, Any]]] = defaultdict(list)
    new_by: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in old_samples:
        old_by[row["cluster_id"]].append(row)
    for row in new_samples:
        new_by[row["cluster_id"]].append(row)
    regimes = cluster_regime_labels(old_samples)
    b0_rows = []
    for cid in sorted(meta):
        old_group = old_by[cid]
        new_group = new_by[cid]
        old_b0, old_b1 = fit_mean_values(old_group)
        new_b0, new_b1 = fit_mean_values(new_group)
        auths = [fnum(r.get("auth_at_latch")) for r in old_group]
        vl = [fnum(r.get("v_latch_true_mps")) for r in old_group]
        auth_vals = [v for v in auths if v is not None]
        vl_vals = [v for v in vl if v is not None]
        fid = meta[cid].get("flight_id", "")
        target_set = "discovery_overlap_3" if fid in DISCOVERY_OVERLAP_IDS else "confirmatory_20"
        b0_rows.append({
            "diagnostic_only": True,
            "cluster_id": cid,
            "flight_id": fid,
            "target_set": target_set,
            "legacy_discovery_listed": fid in DISCOVERY_OVERLAP_IDS or fid in OFF_TARGET_DISCOVERY_IDS,
            "fixture_dir": meta[cid].get("fixture_dir", ""),
            "era": meta[cid].get("era", ""),
            "recording_regime": meta[cid].get("recording_regime", ""),
            "regime_labels": regimes.get(cid, ""),
            "n_rows": len(new_group),
            "auth_at_latch_median": statistics.median(auth_vals) if auth_vals else "",
            "v_latch_median_mps": statistics.median(vl_vals) if vl_vals else "",
            "predicted_offset_mps": mean_or_blank([
                fnum(r.get("predicted_b0_from_auth_mps")) for r in old_group
                if fnum(r.get("predicted_b0_from_auth_mps")) is not None
            ]),
            "b0_old_mps": old_b0 if old_b0 is not None else "",
            "b1_old_mps_per_s": old_b1 if old_b1 is not None else "",
            "b0_new_mps": new_b0 if new_b0 is not None else "",
            "b1_new_mps_per_s": new_b1 if new_b1 is not None else "",
            "remainder_mps": new_b0 if new_b0 is not None else "",
            "old_minus_new_b0_mps": old_b0 - new_b0 if old_b0 is not None and new_b0 is not None else "",
        })
    write_csv(out_dir / "02_shadow_b0_new_per_cluster_split.csv", b0_rows)

    mechanism_rows = []
    for label, ids in [
        ("discovery_overlap_3", DISCOVERY_OVERLAP_IDS),
        ("confirmatory_20", {r["flight_id"] for r in clusters if r["flight_id"] not in DISCOVERY_OVERLAP_IDS}),
        ("pooled_23", {r["flight_id"] for r in clusters}),
        ("legacy_discovery_appendix_5_listed", DISCOVERY_OVERLAP_IDS | OFF_TARGET_DISCOVERY_IDS),
    ]:
        group = [r for r in b0_rows if r["flight_id"] in ids]
        mechanism_rows.append({
            "target_set": label,
            "approaches_listed": len(ids),
            "approaches_analyzable": len(group),
            "b0_new_abs_max_mps": max([abs(float(r["b0_new_mps"])) for r in group if fnum(r.get("b0_new_mps")) is not None], default=""),
            "b0_new_median_mps": statistics.median([float(r["b0_new_mps"]) for r in group if fnum(r.get("b0_new_mps")) is not None]) if group else "",
            "note": "mechanism evidence counted in approaches, never rows",
        })
    write_csv(out_dir / "02_shadow_mechanism_evidence_counts.csv", mechanism_rows)

    mapping_rows = mapping_walk(task_a_dir)
    write_csv(out_dir / "02_directory_recording_approach_cluster_mapping_walk.csv", mapping_rows)
    mapping_counts = mapping_walk_counts(task_a_dir, mapping_rows)
    write_csv(out_dir / "02_directory_recording_approach_cluster_mapping_counts.csv", [mapping_counts])

    return {
        "pooled_shadow": next(r for r in release_rows if r["target_set"] == "pooled_23" and r["anchor_policy"] == "shadow_unattenuated_anchor"),
        "pooled_old": next(r for r in release_rows if r["target_set"] == "pooled_23" and r["anchor_policy"] == "old_attenuated_anchor"),
        "discovery_overlap_approaches": 3,
        "confirmatory_approaches": 20,
        "pooled_approaches": 23,
        "mapping_rows": len(mapping_rows),
        "mapping_counts": mapping_counts,
    }


def mapping_walk(task_a_dir: Path) -> list[dict[str, Any]]:
    dirs = read_csv(task_a_dir / "eligibility_dirs.csv")
    targets = read_csv(task_a_dir / "replay_targets.csv")
    diagnostics = read_csv(task_a_dir / "censored_approach_diagnostics.csv")
    clusters = read_csv(task_a_dir / "expanded_census_clusters.csv")
    targets_by_fid = {r["flight_id"]: r for r in targets}
    clusters_by_approach = {r["approach_id"]: r for r in clusters}
    rows = []
    for d in dirs:
        dir_targets = [t for t in targets if t.get("fixture_path") == d.get("dir")]
        dir_approaches = [a for a in diagnostics if a.get("fixture_dir") == Path(d.get("dir", "")).name]
        if not dir_targets:
            rows.append({
                "fixture_dir": d.get("dir", ""),
                "era": d.get("era", ""),
                "frames": d.get("frames?", ""),
                "imu": d.get("IMU?", ""),
                "recording_label": "",
                "flight_id": "",
                "recording": "",
                "approach_id": "",
                "cluster_id": "",
                "cluster_ok": False,
                "failure_reason": "NO_ELIGIBLE_RECORDING",
                "notes": d.get("notes", ""),
            })
            continue
        for app in dir_approaches:
            target = targets_by_fid.get(app.get("flight_id", ""), {})
            cluster = clusters_by_approach.get(app.get("approach_id", ""), {})
            rows.append({
                "fixture_dir": d.get("dir", ""),
                "era": d.get("era", ""),
                "frames": d.get("frames?", ""),
                "imu": d.get("IMU?", ""),
                "recording_label": target.get("label", app.get("flight", "")),
                "flight_id": app.get("flight_id", ""),
                "recording": target.get("recording", ""),
                "log": target.get("log", ""),
                "physical_approach": app.get("approach_id", ""),
                "cluster_id": cluster.get("cluster_id", ""),
                "cluster_ok": app.get("cluster_ok", ""),
                "failure_reason": app.get("failure_reason", ""),
                "recording_regime": app.get("recording_regime", ""),
                "provenance": cluster.get("provenance", ""),
            })
    return rows


def mapping_walk_counts(task_a_dir: Path, mapping_rows: list[dict[str, Any]]) -> dict[str, Any]:
    dirs = read_csv(task_a_dir / "eligibility_dirs.csv")
    targets = read_csv(task_a_dir / "replay_targets.csv")
    diagnostics = read_csv(task_a_dir / "censored_approach_diagnostics.csv")
    clusters = read_csv(task_a_dir / "expanded_census_clusters.csv")
    return {
        "fixture_dirs_enumerated": len(dirs),
        "eligible_recordings": len(targets),
        "physical_approaches_examined": len(diagnostics),
        "legal_clusters": len(clusters),
        "mapping_walk_rows": len(mapping_rows),
        "no_eligible_recording_rows": sum(1 for r in mapping_rows if r.get("failure_reason") == "NO_ELIGIBLE_RECORDING"),
        "censored_or_legal_approach_rows": sum(1 for r in mapping_rows if r.get("failure_reason") != "NO_ELIGIBLE_RECORDING"),
        "walk": "61 fixture dirs -> 115 eligible recordings -> 178 physical approaches -> 23 legal clusters",
    }


def funnel_applicability(row: dict[str, str]) -> tuple[str, str]:
    era = row.get("era", "")
    reason = row.get("failure_reason", "")
    if reason == "OK":
        return "current-gate", "legal approach under current predicate"
    if era.startswith("phase3") or era.startswith("phase4"):
        return "era-structural", "pre-terminal/current-side era; funnel not transported as cohort-4 prior"
    if reason in {"NO_CLOSE_FEATURE_EPOCH_LE4P5", "NO_PARALLEL_SIDE_PRODUCTION"}:
        return "era-behavioral", "historical behavior/guards partly cured; descriptive only"
    if reason in {"FULL_BELOW_3P5_NOT_EZ_USABLE", "NO_LEGAL_FULL_RATE_ANCHOR", "NO_LEGAL_SIDE_MAINTENANCE_INTERVAL", "NO_CERTIFIED_FULL_BELOW_3P5"}:
        return "current-gate", "current replay gate/funnel remains applicable to cohort availability accounting"
    return "current-gate", "default current-gate classification; inspect row notes"


def ledger(task_a_dir: Path, out_dir: Path) -> dict[str, Any]:
    rows = read_csv(task_a_dir / "censored_approach_diagnostics.csv")
    detailed = []
    for row in rows:
        y = truthy(row.get("cluster_ok")) or row.get("failure_reason") == "OK"
        full_close_any = fnum(row.get("full_certified_below_3p5_any")) or 0.0
        full_dies_gt4p5 = row.get("failure_reason") == "NO_CLOSE_FEATURE_EPOCH_LE4P5"
        never_recert = full_close_any == 0.0
        signature = full_dies_gt4p5 and never_recert
        applicability, note = funnel_applicability(row)
        detailed.append({
            "flight": row.get("flight", ""),
            "flight_id": row.get("flight_id", ""),
            "approach_id": row.get("approach_id", ""),
            "fixture_dir": row.get("fixture_dir", ""),
            "era": row.get("era", ""),
            "era_family": era_family(row.get("era", "")),
            "recording_regime": row.get("recording_regime", ""),
            "failure_reason": row.get("failure_reason", ""),
            "Y_eligible": y,
            "funnel_applicability": applicability,
            "funnel_applicability_note": note,
            "frozen_compound_signature_positive": signature,
            "full_dies_gt4p5_proxy": full_dies_gt4p5,
            "never_recertifies_le3p5": never_recert,
            "definition": "RESPONSE42/44 frozen: FULL dies >4.5m AND never re-certifies <=3.5m; no threshold moved",
        })
    write_csv(out_dir / "03_ledger_approach_rows_with_applicability.csv", detailed)

    era_rows = []
    for era in sorted({r["era"] for r in detailed}):
        group = [r for r in detailed if r["era"] == era]
        y_count = sum(1 for r in group if r["Y_eligible"])
        counts = Counter(r["funnel_applicability"] for r in group)
        era_rows.append({
            "era": era,
            "era_family": era_family(era),
            "approaches": len(group),
            "Y_eligible": y_count,
            "Y_ineligible": len(group) - y_count,
            "Y_eligible_rate": y_count / len(group) if group else "",
            "era_structural": counts.get("era-structural", 0),
            "era_behavioral": counts.get("era-behavioral", 0),
            "current_gate": counts.get("current-gate", 0),
            "cohort4_prior_eligible_denominator": counts.get("current-gate", 0),
            "cohort4_prior_eligible_n": sum(1 for r in group if r["Y_eligible"] and r["funnel_applicability"] == "current-gate"),
        })
    write_csv(out_dir / "03_Y_eligible_by_era_with_applicability.csv", era_rows)

    sig_rows = []
    for app in ["era-structural", "era-behavioral", "current-gate", "all"]:
        scope = detailed if app == "all" else [r for r in detailed if r["funnel_applicability"] == app]
        for signature in [False, True]:
            for y in [False, True]:
                group = [
                    r for r in scope
                    if r["frozen_compound_signature_positive"] == signature
                    and r["Y_eligible"] == y
                ]
                sig_rows.append({
                    "funnel_applicability": app,
                    "frozen_compound_signature_positive": signature,
                    "Y_eligible": y,
                    "approaches": len(group),
                    "eras": ";".join(sorted({r["era"] for r in group})),
                })
    write_csv(out_dir / "03_frozen_compound_signature_2x2_with_applicability.csv", sig_rows)
    return {
        "approaches": len(detailed),
        "Y_eligible": sum(1 for r in detailed if r["Y_eligible"]),
        "current_gate_approaches": sum(1 for r in detailed if r["funnel_applicability"] == "current-gate"),
        "current_gate_Y_eligible": sum(1 for r in detailed if r["Y_eligible"] and r["funnel_applicability"] == "current-gate"),
        "signature_positive": sum(1 for r in detailed if r["frozen_compound_signature_positive"]),
    }


def run(args: argparse.Namespace) -> Path:
    assert_mock_safe()
    head, short = git_head()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ROOT / "tuning" / f"{OUT_PREFIX}-{short}-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=False)

    task_a = args.task_a_dir.resolve()
    task_b = args.task_b_dir.resolve()
    wrong = archaeology_and_rescore(task_b, out_dir)
    shadow = shadow_fit_diagnostics(task_a, out_dir)
    led = ledger(task_a, out_dir)

    summary = {
        "repo_head": head,
        "diagnostic_only": True,
        "wrong_sign_criterion_commit": last_commit_for(WRONG_SIGN_CRITERION),
        "shadow_fit_criterion_commit": last_commit_for(SHADOW_CRITERION),
        "wrong_sign": wrong,
        "shadow": shadow,
        "ledger": led,
        "source_artifacts": {
            "task_a": str(task_a.relative_to(ROOT)),
            "task_b": str(task_b.relative_to(ROOT)),
        },
    }
    write_json(out_dir / "summary.json", summary)
    lines = [
        "# RESPONSE48 Amended Three-Task Round",
        "",
        "Scope: DIAGNOSTIC, CSV-only; no FlightSim/DCGame launch.",
        f"Repo HEAD / generator commit: `{head}`.",
        "",
        "## 1. Wrong-Sign Archaeology First",
        "",
        f"- Legacy 28 reconstruction: `{wrong['legacy_wrong_sign_rows']}` rows.",
        f"- Historical legacy status: `{wrong['legacy_status']}`.",
        f"- Trace term/SIDE rows with new command populated: `{wrong['trace_term_side_rows']}`.",
        f"- Command-event support: `{wrong['command_event_support']}` events.",
        f"- Sign-evaluable events: `{wrong['sign_evaluable_events']}`.",
        f"- Zero/neutral events on support: `{wrong['zero_neutral_events']}`.",
        f"- New excess wrong-sign events on paired common support: `{wrong['new_excess_wrong_sign_events']}`.",
        f"- Historical zero-wrong-sign artifacts re-scored: `{wrong['historical_zero_green_artifacts_rescored']}`.",
        "",
        "## 2. Shadow Residual v2.1 Fit",
        "",
        f"- Pooled old U95: `{shadow['pooled_old']['u95_conservative_mps2']}`.",
        f"- Pooled shadow U95: `{shadow['pooled_shadow']['u95_conservative_mps2']}`.",
        f"- Split counts: discovery overlap `{shadow['discovery_overlap_approaches']}`, confirmatory `{shadow['confirmatory_approaches']}`, pooled `{shadow['pooled_approaches']}`.",
        "",
        "## 3. Ledger",
        "",
        f"- Approaches: `{led['approaches']}`.",
        f"- Y_eligible: `{led['Y_eligible']}`.",
        f"- Current-gate approaches: `{led['current_gate_approaches']}`.",
        f"- Current-gate Y_eligible: `{led['current_gate_Y_eligible']}`.",
        f"- Frozen compound-signature positives: `{led['signature_positive']}`.",
        "",
        "Primary artifacts are prefixed `01_`, `02_`, and `03_` in this directory.",
        "",
    ]
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(out_dir)
    return out_dir


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task-a-dir", type=Path, default=TASK_A_DIR)
    ap.add_argument("--task-b-dir", type=Path, default=TASK_B_DIR)
    args = ap.parse_args(argv)
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
