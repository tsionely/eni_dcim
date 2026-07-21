"""Valid-plant stream intervention rerun for RESPONSE58.

CSV/log replay only. This script never launches FlightSim/DCGame.

It fixes the stream defect from run_second_mechanism_update.py by reading
the logged setpoint body-z stream from each archived flight.jsonl and
converting it to world-up with the adapter equation:

    v_up = -v_bz * cos(level_pitch) * cos(level_roll)

The committed criterion requires a plant-stream validity pre-check before
the intervention judge. A non-positive per-era correlation with the oracle
reference motion marks the input INVALID-INPUT and stops before judge/decomp.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import math
import statistics
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "tuning" / "ordered-round-A-G-DIAGNOSTIC-de19d88-20260720T220957Z"
FEATURES_ARCHIVE = ROOT / "tuning" / "taskA-full-archive-retro-census-bb0dbcf-20260720T165623Z" / "features_archive.csv"
OUT_PREFIX = "valid-plant-intervention-DIAGNOSTIC"
LOCK_PATH = Path("C:/Temp/eni_dcim_sim.lock")

CRITERION = ROOT / "docs" / "criteria" / "second_mechanism_refutation_thresholds.md"
RESPONSE58 = ROOT / "docs" / "thinktank" / "RESPONSE58.md"

COMPUTATION_COMMIT = "de19d881ce8fa0ddc27dd71d7306d0d366c43e90"
CHECKPOINT_EVIDENCE_COMMIT = "c19602f384bc30b0a53d649238b429f9085b6b8f"
NEAR_ZERO_RMS_MPS = 0.05
LARGE_B1_MPS2 = 0.35
AUTH_FULL = 0.999

CHECKPOINT_FILES = [
    SOURCE_DIR / "02_shadow_forced_withhold_samples.csv",
    SOURCE_DIR / "02_shadow_b0_new_per_cluster_split.csv",
    SOURCE_DIR / "summary.json",
    FEATURES_ARCHIVE,
]


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def is_ancestor(older: str, newer: str) -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", older, newer],
        cwd=ROOT,
        capture_output=True,
    ).returncode == 0


def last_commit_for(path: Path) -> str:
    return git("log", "-1", "--format=%H", "--", path.relative_to(ROOT).as_posix())


def assert_csv_safe() -> None:
    if LOCK_PATH.exists():
        raise SystemExit(f"SIM lock exists; refusing CSV generation: {LOCK_PATH}")
    try:
        out = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-Process FlightSim,DCGame -ErrorAction SilentlyContinue | "
                "Select-Object -ExpandProperty Id",
            ],
            text=True,
        )
    except subprocess.CalledProcessError:
        out = ""
    if out.strip():
        raise SystemExit(f"FlightSim/DCGame process visible; refusing CSV generation: {out.strip()}")


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
        writer = csv.DictWriter(f, fieldnames=keys, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def write_json(path: Path, data: Any) -> None:
    write_text(path, json.dumps(data, indent=2, sort_keys=True) + "\n")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def fnum(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def mean(values: list[float]) -> float | str:
    return statistics.fmean(values) if values else ""


def rms(values: list[float]) -> float | str:
    return math.sqrt(statistics.fmean([v * v for v in values])) if values else ""


def median(values: list[float]) -> float | str:
    return statistics.median(values) if values else ""


def corr(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2 or len(ys) < 2:
        return None
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 1e-18 or vy <= 1e-18:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(vx * vy)


def linreg(xs: list[float], ys: list[float]) -> tuple[float | str, float | str]:
    if len(xs) < 2 or len(ys) < 2:
        return "", ""
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    den = sum((x - mx) ** 2 for x in xs)
    if den <= 0:
        return my, ""
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
    return my - slope * mx, slope


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_setpoints(log_path: Path) -> list[dict[str, Any]]:
    rows = []
    for rec in read_jsonl(log_path):
        if rec.get("topic") != "setpoint":
            continue
        data = rec.get("data", {})
        field = ""
        v = None
        for name in ("v_body", "vel_body", "velocity_body"):
            if isinstance(data.get(name), list):
                field = name
                v = data[name]
                break
        if not isinstance(v, list) or len(v) < 3:
            continue
        rows.append({
            "mono_ns": int(rec.get("mono_ns", 0)),
            "phase": data.get("phase", ""),
            "field_name": field,
            "v_body_z": float(v[2]),
        })
    rows.sort(key=lambda r: int(r["mono_ns"]))
    return rows


def setpoint_at(setpoints: list[dict[str, Any]], mono_ns: int) -> dict[str, Any] | None:
    monos = [int(r["mono_ns"]) for r in setpoints]
    idx = bisect.bisect_right(monos, mono_ns) - 1
    if idx < 0:
        return None
    return setpoints[idx]


def convert_body_z_to_world_up(v_bz: float, level_pitch: float, level_roll: float) -> float:
    return -float(v_bz) * math.cos(float(level_pitch)) * math.cos(float(level_roll))


def load_features() -> dict[tuple[str, str, str], dict[str, str]]:
    out = {}
    for row in read_csv(FEATURES_ARCHIVE):
        out[(row["flight_id"], row["frame_id"], row["feature_ts_ns"])] = row
    return out


def flight_log_path(row: dict[str, str]) -> Path:
    return ROOT / "fixtures" / row["fixture_dir"] / f"{row['flight_id']}-flight.jsonl"


def build_input_manifest(out_dir: Path, samples: list[dict[str, str]]) -> dict[str, Any]:
    paths = [p for p in CHECKPOINT_FILES]
    for p in sorted({flight_log_path(r) for r in samples}):
        paths.append(p)
    rows = []
    for path in paths:
        rel = path.relative_to(ROOT).as_posix()
        rows.append({
            "path": rel,
            "sha256": sha256_file(path),
            "role": "checkpoint_or_flight_log",
        })
    out = out_dir / "checkpoint_input_manifest.json"
    write_json(out, rows)
    return {
        "input_manifest_path": out.relative_to(ROOT).as_posix(),
        "input_manifest_sha256": sha256_file(out),
        "input_count": len(rows),
    }


def packet(head: str, out_dir: Path, samples: list[dict[str, str]]) -> dict[str, Any]:
    inputs = build_input_manifest(out_dir, samples)
    return {
        "creation_time_utc": datetime.now(timezone.utc).isoformat(),
        "computation_commit": COMPUTATION_COMMIT,
        "checkpoint_evidence_commit": CHECKPOINT_EVIDENCE_COMMIT,
        "report_generator_commit": head,
        "criterion_commit": last_commit_for(CRITERION),
        "response58_commit": last_commit_for(RESPONSE58),
        "source_checkpoint_dir": SOURCE_DIR.relative_to(ROOT).as_posix(),
        "features_archive": FEATURES_ARCHIVE.relative_to(ROOT).as_posix(),
        "plant_signal": "flight.jsonl setpoint.<v_body|vel_body|velocity_body>[2] converted to world-up",
        "plant_formula": "v_up = -v_bz * cos(level_pitch) * cos(level_roll)",
        "before_formula": "r_before = v_ref_oracle_mps - v_latch_true_mps",
        "after_formula": "r_after = v_ref_oracle_mps - (v_latch_true_mps + logged_setpoint_vz_up_mps)",
        **inputs,
    }


def meta(p: dict[str, Any]) -> dict[str, Any]:
    return {
        "diagnostic_only": True,
        "computation_commit": p["computation_commit"],
        "checkpoint_evidence_commit": p["checkpoint_evidence_commit"],
        "report_generator_commit": p["report_generator_commit"],
        "criterion_commit": p["criterion_commit"],
        "response58_commit": p["response58_commit"],
        "creation_time_utc": p["creation_time_utc"],
        "source_checkpoint_dir": p["source_checkpoint_dir"],
        "input_manifest_path": p["input_manifest_path"],
        "input_manifest_sha256": p["input_manifest_sha256"],
    }


def enrich_samples(samples: list[dict[str, str]], features: dict[tuple[str, str, str], dict[str, str]],
                   p: dict[str, Any]) -> list[dict[str, Any]]:
    setpoint_cache: dict[Path, list[dict[str, Any]]] = {}
    rows = []
    for row in samples:
        feature = features[(row["flight_id"], row["frame_id"], row["feature_ts_ns"])]
        log_path = flight_log_path(row)
        if log_path not in setpoint_cache:
            setpoint_cache[log_path] = load_setpoints(log_path)
        setpoints = setpoint_cache[log_path]
        mono_ns = int(feature["mono_ns"])
        sp = setpoint_at(setpoints, mono_ns)
        if sp is None:
            raise SystemExit(f"no setpoint at/before mono_ns={mono_ns} for {log_path}")
        level_pitch = float(feature.get("level_pitch_rad") or 0.0)
        level_roll = float(feature.get("level_roll_rad") or 0.0)
        logged_vz_up = convert_body_z_to_world_up(float(sp["v_body_z"]), level_pitch, level_roll)
        feature_vz_up = fnum(feature.get("setpoint_vz_up_mps"))
        v_ref = fnum(row.get("v_ref_oracle_mps"))
        v_latch = fnum(row.get("v_latch_true_mps"))
        r_before = v_ref - v_latch if v_ref is not None and v_latch is not None else ""
        r_after = v_ref - (v_latch + logged_vz_up) if v_ref is not None and v_latch is not None else ""
        rows.append({
            **row,
            "era": feature.get("era", ""),
            "recording_regime": feature.get("recording_regime", ""),
            "mono_ns": mono_ns,
            "flight_log_path": log_path.relative_to(ROOT).as_posix(),
            "setpoint_field_name": sp["field_name"],
            "setpoint_phase": sp["phase"],
            "setpoint_mono_ns": sp["mono_ns"],
            "setpoint_age_s": (mono_ns - int(sp["mono_ns"])) / 1e9,
            "logged_setpoint_v_body_z_mps": sp["v_body_z"],
            "level_pitch_rad": level_pitch,
            "level_roll_rad": level_roll,
            "logged_setpoint_vz_up_mps": logged_vz_up,
            "features_archive_setpoint_vz_up_mps": feature_vz_up if feature_vz_up is not None else "",
            "features_archive_setpoint_diff_mps": (
                logged_vz_up - feature_vz_up if feature_vz_up is not None else ""
            ),
            "truth_vz_up_mps": feature.get("truth_vz_up_mps", ""),
            "plant_stream_derivation": p["plant_formula"],
            "r_before_mps": r_before,
            "r_after_valid_plant_mps": r_after,
            "before_formula": p["before_formula"],
            "after_formula": p["after_formula"],
        })
    return rows


def validity_precheck(p: dict[str, Any], rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    grouped: dict[tuple[str, str], dict[tuple[str, str, str], dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        exposure_key = (row["flight_id"], row["frame_id"], row["feature_ts_ns"])
        grouped[(row.get("era", ""), row.get("recording_regime", ""))][exposure_key] = row
    out = []
    invalid = False
    for (era, regime), exposure_map in sorted(grouped.items()):
        uniq = list(exposure_map.values())
        plant = [fnum(r.get("logged_setpoint_vz_up_mps")) for r in uniq]
        oracle = [fnum(r.get("v_ref_oracle_mps")) for r in uniq]
        truth = [fnum(r.get("truth_vz_up_mps")) for r in uniq]
        plant_oracle = [(x, y) for x, y in zip(plant, oracle) if x is not None and y is not None]
        plant_truth = [(x, y) for x, y in zip(plant, truth) if x is not None and y is not None]
        c_oracle = corr([x for x, _ in plant_oracle], [y for _, y in plant_oracle])
        c_truth = corr([x for x, _ in plant_truth], [y for _, y in plant_truth])
        if c_oracle is None:
            status = "NOT_EVALUABLE_ZERO_VARIANCE_OR_N_LT_2"
        elif c_oracle > 0.0:
            status = "PASS_POSITIVE"
        else:
            status = "INVALID_INPUT_NON_POSITIVE"
            invalid = True
        out.append({
            **meta(p),
            "scope": "era_recording_regime_unique_exposures",
            "era": era,
            "recording_regime": regime,
            "unique_exposures": len(uniq),
            "plant_field_source": "flight.jsonl setpoint stream",
            "plant_world_up_formula": p["plant_formula"],
            "corr_logged_plant_vs_oracle_ref": c_oracle if c_oracle is not None else "",
            "corr_logged_plant_vs_truth_vz_up_diagnostic": c_truth if c_truth is not None else "",
            "decision_column": "corr_logged_plant_vs_oracle_ref",
            "decision_status": status,
            "invalid_input": status == "INVALID_INPUT_NON_POSITIVE",
            "judge_may_run_for_scope": status == "PASS_POSITIVE",
        })
    return out, not invalid


def cut_intervention_rows(p: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["cluster_id"], row["cut_id"])].append(row)
    out = []
    for (cluster_id, cut_id), group in sorted(groups.items()):
        ages = [x for x in (fnum(r.get("age_s")) for r in group) if x is not None]
        before = [x for x in (fnum(r.get("r_before_mps")) for r in group) if x is not None]
        after = [x for x in (fnum(r.get("r_after_valid_plant_mps")) for r in group) if x is not None]
        plant = [x for x in (fnum(r.get("logged_setpoint_vz_up_mps")) for r in group) if x is not None]
        auth = [x for x in (fnum(r.get("auth_at_latch")) for r in group) if x is not None]
        b0_before, b1_before = linreg(ages, before)
        b0_after, b1_after = linreg(ages, after)
        plant_rms = rms(plant)
        near_zero = isinstance(plant_rms, float) and plant_rms < NEAR_ZERO_RMS_MPS
        auth_med = median(auth)
        auth_full = isinstance(auth_med, float) and auth_med >= AUTH_FULL
        out.append({
            **meta(p),
            "cluster_id": cluster_id,
            "cut_id": cut_id,
            "flight_id": group[0].get("flight_id", ""),
            "flight": group[0].get("flight", ""),
            "era": group[0].get("era", ""),
            "recording_regime": group[0].get("recording_regime", ""),
            "n_rows": len(group),
            "age_min_s": min(ages) if ages else "",
            "age_max_s": max(ages) if ages else "",
            "auth_at_latch_median": auth_med,
            "auth_ge_0p999": auth_full,
            "logged_plant_rms_mps": plant_rms,
            "near_zero_logged_plant_activity": near_zero,
            "b0_before_mps": b0_before,
            "b1_before_mps2": b1_before,
            "abs_b1_before_mps2": abs(b1_before) if isinstance(b1_before, float) else "",
            "large_b1_before": isinstance(b1_before, float) and abs(b1_before) > LARGE_B1_MPS2,
            "b0_after_valid_plant_mps": b0_after,
            "b1_after_valid_plant_mps2": b1_after,
            "abs_b1_after_valid_plant_mps2": abs(b1_after) if isinstance(b1_after, float) else "",
            "large_b1_after": isinstance(b1_after, float) and abs(b1_after) > LARGE_B1_MPS2,
            "prediction_filter_refutation_cut": (
                auth_full and near_zero and isinstance(b1_before, float) and abs(b1_before) > LARGE_B1_MPS2
            ),
            "plant_signal": p["plant_signal"],
            "after_formula": p["after_formula"],
        })
    return out


def summarize_invalid(p: dict[str, Any], precheck: list[dict[str, Any]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    invalid_rows = [r for r in precheck if r["decision_status"] == "INVALID_INPUT_NON_POSITIVE"]
    max_feature_diff = max(
        [abs(x) for x in (fnum(r.get("features_archive_setpoint_diff_mps")) for r in rows) if x is not None],
        default=0.0,
    )
    return {
        "diagnostic_only": True,
        "repo_head": p["report_generator_commit"],
        "criterion_commit": p["criterion_commit"],
        "response58_commit": p["response58_commit"],
        "input_manifest_path": p["input_manifest_path"],
        "input_manifest_sha256": p["input_manifest_sha256"],
        "plant_signal": p["plant_signal"],
        "plant_formula": p["plant_formula"],
        "n_samples": len(rows),
        "n_clusters": len({r["cluster_id"] for r in rows}),
        "n_unique_exposures": len({(r["flight_id"], r["frame_id"], r["feature_ts_ns"]) for r in rows}),
        "max_abs_diff_vs_features_archive_setpoint_vz_up_mps": max_feature_diff,
        "validity_precheck_passed": len(invalid_rows) == 0,
        "invalid_input_scopes": [
            {
                "era": r["era"],
                "recording_regime": r["recording_regime"],
                "corr_logged_plant_vs_oracle_ref": r["corr_logged_plant_vs_oracle_ref"],
            }
            for r in invalid_rows
        ],
        "judge_status": (
            "NOT_RUN_INVALID_INPUT_PRECHECK"
            if invalid_rows else "ELIGIBLE_TO_RUN"
        ),
        "driver_decomposition_status": (
            "NOT_RUN_INVALID_INPUT_PRECHECK"
            if invalid_rows else "ELIGIBLE_TO_RUN"
        ),
        "stop_rule": "non-positive per-era oracle-reference correlation => INVALID-INPUT before judge",
    }


def run(args: argparse.Namespace) -> Path:
    assert_csv_safe()
    head = git("rev-parse", "HEAD")
    if not is_ancestor(args.minimum_tip, head):
        raise SystemExit(f"HEAD {head} does not include requested tip {args.minimum_tip}")
    criterion_commit = last_commit_for(CRITERION)
    if not is_ancestor(criterion_commit, head):
        raise SystemExit(f"criterion {criterion_commit} is not an ancestor of HEAD {head}")
    samples = read_csv(SOURCE_DIR / "02_shadow_forced_withhold_samples.csv")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ROOT / "tuning" / f"{OUT_PREFIX}-{head[:7]}-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=False)
    p = packet(head, out_dir, samples)
    features = load_features()
    enriched = enrich_samples(samples, features, p)
    precheck, may_run_judge = validity_precheck(p, enriched)

    write_text(
        out_dir / "plant_stream_derivation.md",
        "\n".join([
            "# Plant Stream Derivation",
            "",
            "Source: archived `flight.jsonl` records, topic `setpoint`.",
            "",
            "Per-era field naming is disclosed in `harness_stream_disclosure.csv`.",
            "",
            "For each forced-withhold row, the generator locates the last setpoint",
            "sample at or before the replay feature `mono_ns`. The vertical body",
            "component is read from `setpoint.v_body[2]` when present, otherwise",
            "`setpoint.vel_body[2]` or `setpoint.velocity_body[2]`.",
            "",
            "The world-up conversion follows the adapter equation registered in",
            "the criterion:",
            "",
            "`v_up = -v_bz * cos(level_pitch) * cos(level_roll)`",
            "",
            "Here `v_bz` is the logged body-z plant input; negative body-z means",
            "climb in the NED/body convention used by the planner tests, so the",
            "leading minus maps climb to positive world-up.",
            "",
        ]) + "\n",
    )
    write_csv(out_dir / "plant_stream_samples.csv", [
        {
            **meta(p),
            "cluster_id": r["cluster_id"],
            "cut_id": r["cut_id"],
            "flight_id": r["flight_id"],
            "flight": r["flight"],
            "fixture_dir": r["fixture_dir"],
            "frame_id": r["frame_id"],
            "feature_ts_ns": r["feature_ts_ns"],
            "mono_ns": r["mono_ns"],
            "era": r["era"],
            "recording_regime": r["recording_regime"],
            "flight_log_path": r["flight_log_path"],
            "setpoint_field_name": r["setpoint_field_name"],
            "setpoint_phase": r["setpoint_phase"],
            "setpoint_mono_ns": r["setpoint_mono_ns"],
            "setpoint_age_s": r["setpoint_age_s"],
            "logged_setpoint_v_body_z_mps": r["logged_setpoint_v_body_z_mps"],
            "level_pitch_rad": r["level_pitch_rad"],
            "level_roll_rad": r["level_roll_rad"],
            "logged_setpoint_vz_up_mps": r["logged_setpoint_vz_up_mps"],
            "features_archive_setpoint_vz_up_mps": r["features_archive_setpoint_vz_up_mps"],
            "features_archive_setpoint_diff_mps": r["features_archive_setpoint_diff_mps"],
            "v_ref_oracle_mps": r["v_ref_oracle_mps"],
            "truth_vz_up_mps": r["truth_vz_up_mps"],
            "r_before_mps": r["r_before_mps"],
            "r_after_valid_plant_mps": r["r_after_valid_plant_mps"],
        }
        for r in enriched
    ])
    write_csv(out_dir / "validity_precheck_by_era.csv", precheck)

    field_groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in enriched:
        field_groups[(r["era"], r["recording_regime"], r["setpoint_field_name"])].append(r)
    disclosure = []
    for (era, regime, field), group in sorted(field_groups.items()):
        ages = [x for x in (fnum(r.get("setpoint_age_s")) for r in group) if x is not None]
        disclosure.append({
            **meta(p),
            "era": era,
            "recording_regime": regime,
            "flight_jsonl_setpoint_field": field,
            "rows": len(group),
            "clusters": len({r["cluster_id"] for r in group}),
            "plant_stream": p["plant_signal"],
            "world_up_conversion": p["plant_formula"],
            "setpoint_age_max_s": max(ages) if ages else "",
            "command_semantics": "0.0 is observed zero command; absent field is missing; no truthiness filter",
            "mixed_ownership_handling": "reported by era/recording_regime; judge is gated by validity precheck before any pooled read",
        })
    write_csv(out_dir / "harness_stream_disclosure.csv", disclosure)

    summary = summarize_invalid(p, precheck, enriched)
    if may_run_judge:
        cuts = cut_intervention_rows(p, enriched)
        write_csv(out_dir / "intervention_cut_b1_before_after_valid_plant.csv", cuts)
        summary["judge_status"] = "RUN"
        summary["large_cluster_count_before"] = len({
            r["cluster_id"] for r in cuts if str(r.get("large_b1_before")) == "True"
        })
        summary["large_cluster_count_after"] = len({
            r["cluster_id"] for r in cuts if str(r.get("large_b1_after")) == "True"
        })
        summary["prediction_refutation_candidate_clusters"] = sorted({
            r["cluster_id"] for r in cuts if str(r.get("prediction_filter_refutation_cut")) == "True"
        })
    else:
        write_csv(out_dir / "judge_not_run_invalid_input.csv", [{
            **meta(p),
            "judge_status": "NOT_RUN_INVALID_INPUT_PRECHECK",
            "driver_decomposition_status": "NOT_RUN_INVALID_INPUT_PRECHECK",
            "reason": "At least one era/recording_regime had non-positive corr(logged plant stream, oracle reference motion).",
            "criterion_stop_rule": "Non-positive => INVALID-INPUT, stop, report.",
        }])

    write_json(out_dir / "summary.json", summary)
    invalid_text = ", ".join(
        f"{r['era']}/{r['recording_regime']}={r['corr_logged_plant_vs_oracle_ref']}"
        for r in summary["invalid_input_scopes"]
    )
    write_text(
        out_dir / "summary.md",
        "\n".join([
            "# Valid-Plant Intervention Rerun",
            "",
            "Scope: DIAGNOSTIC, CSV/log replay only; no FlightSim/DCGame launch.",
            f"Repo HEAD: `{head}`.",
            f"Criterion commit: `{p['criterion_commit']}`.",
            f"Input manifest: `{p['input_manifest_path']}`.",
            f"Input manifest sha256: `{p['input_manifest_sha256']}`.",
            "",
            "## Plant Stream",
            "",
            "The stream is read from archived `flight.jsonl` setpoint records and",
            "converted with `v_up = -v_bz * cos(level_pitch) * cos(level_roll)`.",
            f"Max abs diff versus `features_archive.setpoint_vz_up_mps`: `{summary['max_abs_diff_vs_features_archive_setpoint_vz_up_mps']}`.",
            "",
            "## Validity Pre-Check",
            "",
            f"Passed: `{summary['validity_precheck_passed']}`.",
            f"Invalid scopes: `{invalid_text}`.",
            "",
            "## Judge",
            "",
            f"Judge status: `{summary['judge_status']}`.",
            f"Driver decomposition status: `{summary['driver_decomposition_status']}`.",
            "",
        ]) + "\n",
    )
    manifest_rows = []
    for path in sorted(out_dir.iterdir()):
        if path.is_file():
            manifest_rows.append({
                "artifact_path": path.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(path),
            })
    write_csv(out_dir / "artifact_manifest.csv", manifest_rows)
    print(out_dir)
    return out_dir


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--minimum-tip", default="c29db8d")
    args = ap.parse_args(argv)
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
