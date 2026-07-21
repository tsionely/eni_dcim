"""Valid-plant stream intervention rerun for RESPONSE58.

CSV/log replay only. This script never launches FlightSim/DCGame.

It fixes the stream defect from run_second_mechanism_update.py by reading
the logged setpoint body-z stream from each archived flight.jsonl and
converting it to world-up with the adapter equation:

    v_up = -v_bz * cos(level_pitch) * cos(level_roll)

The current criterion withdraws the earlier zero-lag correlation gate:
setpoint.v_body[2] is Contract-B COMMANDED VELOCITY REFERENCE, so the judge
uses a declared lag-aware response model and keeps the correlation table as
diagnostic disclosure only.
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
import sys
sys.path.insert(0, str(ROOT / "tuning"))

FIT_BACKEND = "local_constrained_variance_no_scipy"

SOURCE_DIR = ROOT / "tuning" / "ordered-round-A-G-DIAGNOSTIC-de19d88-20260720T220957Z"
FEATURES_ARCHIVE = ROOT / "tuning" / "taskA-full-archive-retro-census-bb0dbcf-20260720T165623Z" / "features_archive.csv"
OUT_PREFIX = "valid-plant-intervention-DIAGNOSTIC"
LOCK_PATH = Path("C:/Temp/eni_dcim_sim.lock")

CRITERION = ROOT / "docs" / "criteria" / "second_mechanism_refutation_thresholds.md"
RESPONSE58 = ROOT / "docs" / "thinktank" / "RESPONSE58.md"
RESPONSE61 = ROOT / "docs" / "thinktank" / "RESPONSE61.md"
RESPONSE62 = ROOT / "docs" / "thinktank" / "RESPONSE62.md"
RESPONSE63 = ROOT / "docs" / "thinktank" / "RESPONSE63.md"

COMPUTATION_COMMIT = "de19d881ce8fa0ddc27dd71d7306d0d366c43e90"
CHECKPOINT_EVIDENCE_COMMIT = "c19602f384bc30b0a53d649238b429f9085b6b8f"
NEAR_ZERO_RMS_MPS = 0.05
LARGE_B1_MPS2 = 0.35
AUTH_FULL = 0.999
QUIET_REFUTATION_K = 2
MIN_UNIQUE_AGES = 4
MIN_CUT_ROWS = 4
MIN_AGE_SPAN_S = 0.15

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


def percentile(values: list[float], pct: float) -> float | str:
    vals = sorted(v for v in values if math.isfinite(v))
    if not vals:
        return ""
    if len(vals) == 1:
        return vals[0]
    pos = (len(vals) - 1) * pct / 100.0
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return vals[int(pos)]
    return vals[lo] * (hi - pos) + vals[hi] * (pos - lo)


def fit_release_fast(samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Local constrained variance fallback for the diagnostic A/B/C/D read.

    The release-grade shadow-fit generator uses SciPy. This round only needs a
    declared driver decomposition in the current Windows environment, so this
    pure-Python fallback fits the same variance form non-negatively by robust
    residual moments and labels the backend in every output row.
    """
    clean = [
        (fnum(r.get("age_s")), fnum(r.get("r_v_mps")))
        for r in samples
    ]
    pairs = [(float(a), float(r)) for a, r in clean if a is not None and r is not None]
    if not pairs:
        return {
            "b0": "",
            "b1": "",
            "mean_fit_residual_rms_mps": "",
            "sigma_0_mps": "",
            "sigma_a_mps2": "",
            "nll": "",
            "profile_u95_sigma_a_mps2": "",
            "profile_threshold_nll": "",
            "profile_nearly_flat": "",
            "profile_loss_min": "",
            "profile_loss_max": "",
            "fit_backend": FIT_BACKEND,
        }
    ages = [a for a, _ in pairs]
    residuals = [r for _, r in pairs]
    b0, b1 = linreg(ages, residuals)
    b0f = float(b0) if isinstance(b0, float) else statistics.fmean(residuals)
    b1f = float(b1) if isinstance(b1, float) else 0.0
    centered = [r - (b0f + b1f * a) for a, r in pairs]
    a2 = [a * a for a in ages]
    y2 = [e * e for e in centered]
    ma2 = statistics.fmean(a2)
    my2 = statistics.fmean(y2)
    den = sum((x - ma2) ** 2 for x in a2)
    slope = sum((x - ma2) * (y - my2) for x, y in zip(a2, y2)) / den if den > 1e-18 else 0.0
    intercept = my2 - slope * ma2
    if slope < 0.0:
        slope = 0.0
        intercept = my2
    if intercept < 0.0:
        intercept = 0.0
        den0 = sum(x * x for x in a2)
        slope = sum(x * y for x, y in zip(a2, y2)) / den0 if den0 > 1e-18 else 0.0
    slope = max(0.0, slope)
    sigma0 = math.sqrt(max(0.0, intercept))
    sigmaa = math.sqrt(slope)
    age_slopes = [abs(e) / a for a, e in zip(ages, centered) if abs(a) > 1e-6]
    profile_u95 = max(sigmaa, float(percentile(age_slopes, 95) or 0.0))
    scale_resid = [
        y - (sigma0 * sigma0 + sigmaa * sigmaa * x)
        for x, y in zip(a2, y2)
    ]
    loss = sum(v * v for v in scale_resid)
    return {
        "b0": b0f,
        "b1": b1f,
        "mean_fit_residual_rms_mps": rms(centered),
        "sigma_0_mps": sigma0,
        "sigma_a_mps2": sigmaa,
        "nll": loss,
        "profile_u95_sigma_a_mps2": profile_u95,
        "profile_threshold_nll": "",
        "profile_nearly_flat": False,
        "profile_loss_min": loss,
        "profile_loss_max": "",
        "fit_backend": FIT_BACKEND,
    }


def cluster_bootstrap_fast(samples: list[dict[str, Any]], n_boot: int = 2000) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in samples:
        groups[str(row["cluster_id"])].append(row)
    ids = sorted(groups)
    rng = __import__("random").Random(20260721)
    vals: list[float] = []
    b0s: list[float] = []
    b1s: list[float] = []
    for _ in range(n_boot):
        draw: list[dict[str, Any]] = []
        for _cid in ids:
            draw.extend(groups[rng.choice(ids)])
        fit = fit_release_fast(draw)
        sa = fnum(fit.get("sigma_a_mps2"))
        b0 = fnum(fit.get("b0"))
        b1 = fnum(fit.get("b1"))
        if sa is not None:
            vals.append(sa)
        if b0 is not None:
            b0s.append(b0)
        if b1 is not None:
            b1s.append(b1)
    return {
        "cluster_bootstrap_n": n_boot,
        "cluster_bootstrap_u95_sigma_a_mps2": percentile(vals, 95),
        "cluster_bootstrap_sigma_a_min_mps2": min(vals) if vals else "",
        "cluster_bootstrap_sigma_a_max_mps2": max(vals) if vals else "",
        "b0_ci_low_mps": percentile(b0s, 2.5),
        "b0_ci_median_mps": percentile(b0s, 50),
        "b0_ci_high_mps": percentile(b0s, 97.5),
        "b1_ci_low_mps_per_s": percentile(b1s, 2.5),
        "b1_ci_median_mps_per_s": percentile(b1s, 50),
        "b1_ci_high_mps_per_s": percentile(b1s, 97.5),
        "fit_backend": FIT_BACKEND,
    }


def loao_sensitivity_fast(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for cid in sorted({str(r["cluster_id"]) for r in samples}):
        train = [r for r in samples if str(r["cluster_id"]) != cid]
        fit = fit_release_fast(train)
        u95 = fnum(fit.get("profile_u95_sigma_a_mps2"))
        rows.append({
            "left_out_approach": cid,
            "train_clusters": len({r["cluster_id"] for r in train}),
            "train_rows": len(train),
            "point_sigma_a_mps2": fit["sigma_a_mps2"],
            "profile_u95_sigma_a_mps2": u95 if u95 is not None else "",
            "pushes_over_gate": (u95 is not None and u95 > LARGE_B1_MPS2),
            "profile_nearly_flat": fit["profile_nearly_flat"],
            "fit_backend": FIT_BACKEND,
        })
    return rows


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


def load_term_statuses(log_path: Path) -> list[dict[str, Any]]:
    rows = []
    for rec in read_jsonl(log_path):
        if rec.get("topic") != "term_status":
            continue
        data = rec.get("data", {})
        rows.append({
            "mono_ns": int(rec.get("mono_ns", 0)),
            "owner": data.get("owner", ""),
            "engaged": data.get("engaged", ""),
            "ready": data.get("ready", ""),
            "v_bz_applied": data.get("v_bz_applied", ""),
        })
    rows.sort(key=lambda r: int(r["mono_ns"]))
    return rows


def setpoint_at(setpoints: list[dict[str, Any]], mono_ns: int) -> dict[str, Any] | None:
    monos = [int(r["mono_ns"]) for r in setpoints]
    idx = bisect.bisect_right(monos, mono_ns) - 1
    if idx < 0:
        return None
    return setpoints[idx]


def term_status_at(statuses: list[dict[str, Any]], mono_ns: int) -> dict[str, Any] | None:
    monos = [int(r["mono_ns"]) for r in statuses]
    idx = bisect.bisect_right(monos, mono_ns) - 1
    if idx < 0:
        return None
    return statuses[idx]


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
        "response61_commit": last_commit_for(RESPONSE61),
        "response62_commit": last_commit_for(RESPONSE62),
        "response63_commit": last_commit_for(RESPONSE63),
        "source_checkpoint_dir": SOURCE_DIR.relative_to(ROOT).as_posix(),
        "features_archive": FEATURES_ARCHIVE.relative_to(ROOT).as_posix(),
        "plant_signal": "flight.jsonl setpoint.<v_body|vel_body|velocity_body>[2] converted to world-up",
        "plant_formula": "v_up = -v_bz * cos(level_pitch) * cos(level_roll)",
        "stream_contract": "Contract B: commanded velocity reference",
        "response_model": "pure-delay commanded-reference response calibrated from A091; TERM-owned support correction is structural no-op; zero-lag sensitivity disclosed",
        "fit_backend": FIT_BACKEND,
        "before_formula": "r_before = v_ref_oracle_mps - v_latch_true_mps",
        "after_formula": "r_after = v_ref_oracle_mps - (v_latch_true_mps + contract_b_correction_vz_up_mps)",
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
        "response61_commit": p["response61_commit"],
        "response62_commit": p["response62_commit"],
        "response63_commit": p["response63_commit"],
        "creation_time_utc": p["creation_time_utc"],
        "source_checkpoint_dir": p["source_checkpoint_dir"],
        "input_manifest_path": p["input_manifest_path"],
        "input_manifest_sha256": p["input_manifest_sha256"],
        "fit_backend": p["fit_backend"],
    }


def enrich_samples(samples: list[dict[str, str]], features: dict[tuple[str, str, str], dict[str, str]],
                   p: dict[str, Any], response_lag_s: float = 0.0) -> list[dict[str, Any]]:
    setpoint_cache: dict[Path, list[dict[str, Any]]] = {}
    term_status_cache: dict[Path, list[dict[str, Any]]] = {}
    rows = []
    for row in samples:
        feature = features[(row["flight_id"], row["frame_id"], row["feature_ts_ns"])]
        log_path = flight_log_path(row)
        if log_path not in setpoint_cache:
            setpoint_cache[log_path] = load_setpoints(log_path)
        if log_path not in term_status_cache:
            term_status_cache[log_path] = load_term_statuses(log_path)
        setpoints = setpoint_cache[log_path]
        term_statuses = term_status_cache[log_path]
        mono_ns = int(feature["mono_ns"])
        sp = setpoint_at(setpoints, mono_ns)
        if sp is None:
            raise SystemExit(f"no setpoint at/before mono_ns={mono_ns} for {log_path}")
        ts = term_status_at(term_statuses, mono_ns)
        lagged_mono_ns = mono_ns - int(round(float(response_lag_s) * 1e9))
        lagged_sp = setpoint_at(setpoints, lagged_mono_ns)
        level_pitch = float(feature.get("level_pitch_rad") or 0.0)
        level_roll = float(feature.get("level_roll_rad") or 0.0)
        logged_vz_up = convert_body_z_to_world_up(float(sp["v_body_z"]), level_pitch, level_roll)
        delayed_vz_up = (
            convert_body_z_to_world_up(float(lagged_sp["v_body_z"]), level_pitch, level_roll)
            if lagged_sp is not None else None
        )
        term_owner = str(ts.get("owner", "")) if ts is not None else ""
        term_owned_support = term_owner == "term"
        correction_vz_up = 0.0 if term_owned_support else delayed_vz_up
        feature_vz_up = fnum(feature.get("setpoint_vz_up_mps"))
        v_ref = fnum(row.get("v_ref_oracle_mps"))
        v_latch = fnum(row.get("v_latch_true_mps"))
        r_before = v_ref - v_latch if v_ref is not None and v_latch is not None else ""
        r_after = (
            v_ref - (v_latch + correction_vz_up)
            if v_ref is not None and v_latch is not None and correction_vz_up is not None else ""
        )
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
            "term_status_mono_ns": ts["mono_ns"] if ts is not None else "",
            "term_status_age_s": (mono_ns - int(ts["mono_ns"])) / 1e9 if ts is not None else "",
            "term_status_owner": term_owner,
            "term_status_engaged": ts.get("engaged", "") if ts is not None else "",
            "term_status_ready": ts.get("ready", "") if ts is not None else "",
            "term_owned_support": term_owned_support,
            "level_pitch_rad": level_pitch,
            "level_roll_rad": level_roll,
            "logged_setpoint_vz_up_mps": logged_vz_up,
            "response_lag_s": response_lag_s,
            "lagged_setpoint_mono_ns": lagged_sp["mono_ns"] if lagged_sp is not None else "",
            "lagged_setpoint_age_s": (
                (mono_ns - int(lagged_sp["mono_ns"])) / 1e9
                if lagged_sp is not None else ""
            ),
            "delayed_logged_setpoint_vz_up_mps": delayed_vz_up if delayed_vz_up is not None else "",
            "contract_b_correction_vz_up_mps": correction_vz_up if correction_vz_up is not None else "",
            "ownership_gate_rule": "owner=term => correction 0.0 structural no-op; otherwise delayed logged setpoint world-up",
            "features_archive_setpoint_vz_up_mps": feature_vz_up if feature_vz_up is not None else "",
            "features_archive_setpoint_diff_mps": (
                logged_vz_up - feature_vz_up if feature_vz_up is not None else ""
            ),
            "truth_vz_up_mps": feature.get("truth_vz_up_mps", ""),
            "plant_stream_derivation": p["plant_formula"],
            "r_before_mps": r_before,
            "r_after_contract_b_mps": r_after,
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
    for (era, regime), exposure_map in sorted(grouped.items()):
        uniq = list(exposure_map.values())
        plant = [fnum(r.get("logged_setpoint_vz_up_mps")) for r in uniq]
        delayed = [fnum(r.get("delayed_logged_setpoint_vz_up_mps")) for r in uniq]
        oracle = [fnum(r.get("v_ref_oracle_mps")) for r in uniq]
        truth = [fnum(r.get("truth_vz_up_mps")) for r in uniq]
        plant_oracle = [(x, y) for x, y in zip(plant, oracle) if x is not None and y is not None]
        delayed_oracle = [(x, y) for x, y in zip(delayed, oracle) if x is not None and y is not None]
        plant_truth = [(x, y) for x, y in zip(plant, truth) if x is not None and y is not None]
        delayed_truth = [(x, y) for x, y in zip(delayed, truth) if x is not None and y is not None]
        c_oracle = corr([x for x, _ in plant_oracle], [y for _, y in plant_oracle])
        c_delayed_oracle = corr([x for x, _ in delayed_oracle], [y for _, y in delayed_oracle])
        c_truth = corr([x for x, _ in plant_truth], [y for _, y in plant_truth])
        c_delayed_truth = corr([x for x, _ in delayed_truth], [y for _, y in delayed_truth])
        if c_oracle is None:
            status = "DIAGNOSTIC_NOT_EVALUABLE_ZERO_VARIANCE_OR_N_LT_2"
        elif c_oracle > 0.0:
            status = "DIAGNOSTIC_POSITIVE"
        else:
            status = "DIAGNOSTIC_NON_POSITIVE_GATE_WITHDRAWN"
        out.append({
            **meta(p),
            "scope": "era_recording_regime_unique_exposures",
            "era": era,
            "recording_regime": regime,
            "unique_exposures": len(uniq),
            "plant_field_source": "flight.jsonl setpoint stream",
            "plant_world_up_formula": p["plant_formula"],
            "corr_logged_plant_vs_oracle_ref": c_oracle if c_oracle is not None else "",
            "corr_delayed_logged_plant_vs_oracle_ref": c_delayed_oracle if c_delayed_oracle is not None else "",
            "corr_logged_plant_vs_truth_vz_up_diagnostic": c_truth if c_truth is not None else "",
            "corr_delayed_logged_plant_vs_truth_vz_up_diagnostic": c_delayed_truth if c_delayed_truth is not None else "",
            "decision_column": "none",
            "decision_status": status,
            "invalid_input": False,
            "judge_may_run_for_scope": True,
            "criterion_note": "zero-lag positive-correlation gate withdrawn in RESPONSE61; table is diagnostic only",
        })
    return out, True


def lag_calibration_from_a091(p: dict[str, Any], rows: list[dict[str, Any]]) -> tuple[float, list[dict[str, Any]]]:
    exposure_rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        if row.get("cluster_id") == "20260719T201851-50f9dcc8:A1":
            exposure_rows[(row["flight_id"], row["frame_id"], row["feature_ts_ns"])] = row
    ordered = sorted(exposure_rows.values(), key=lambda r: int(r["mono_ns"]))
    if len(ordered) < 4:
        return 0.0, [{
            **meta(p),
            "calibration_source": "A091",
            "status": "UNCALIBRATABLE_DEFAULT_ZERO_LAG",
            "reason": "fewer than 4 A091 unique exposures",
        }]
    t0 = int(ordered[0]["mono_ns"]) / 1e9
    command = [
        (int(r["mono_ns"]) / 1e9 - t0, fnum(r.get("logged_setpoint_vz_up_mps")))
        for r in ordered
    ]
    truth = [
        (int(r["mono_ns"]) / 1e9 - t0, fnum(r.get("truth_vz_up_mps")))
        for r in ordered if fnum(r.get("truth_vz_up_mps")) is not None
    ]

    def at_or_before(series: list[tuple[float, float | None]], t_s: float) -> float | None:
        prev = None
        for ts, value in series:
            if ts <= t_s:
                prev = value
            else:
                break
        return prev

    grid_rows = []
    best_lag_s = 0.0
    best_corr = None
    for lag_ms in range(0, 301, 10):
        lag_s = lag_ms / 1000.0
        xs: list[float] = []
        ys: list[float] = []
        for t_s, y in truth:
            x = at_or_before(command, t_s - lag_s)
            if x is not None and y is not None:
                xs.append(float(x))
                ys.append(float(y))
        c = corr(xs, ys)
        row = {
            **meta(p),
            "calibration_source": "A091",
            "lag_ms": lag_ms,
            "pairs": len(xs),
            "corr_delayed_command_vs_truth_vz_up": c if c is not None else "",
            "status": "GRID_ROW",
            "selection_rule": "max corr(command(t-lag), truth_vz_up(t)) over A091 only; no 23-approach fitting",
        }
        grid_rows.append(row)
        if c is not None and (best_corr is None or c > best_corr):
            best_corr = c
            best_lag_s = lag_s
    grid_rows.append({
        **meta(p),
        "calibration_source": "A091",
        "lag_ms": int(round(best_lag_s * 1000)),
        "pairs": "",
        "corr_delayed_command_vs_truth_vz_up": best_corr if best_corr is not None else "",
        "status": "SELECTED_LAG",
        "selection_rule": "A091-only physical calibration source; pure-delay response model",
    })
    return best_lag_s, grid_rows


def cut_intervention_rows(p: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["cluster_id"], row["cut_id"])].append(row)
    out = []
    for (cluster_id, cut_id), group in sorted(groups.items()):
        ages = [x for x in (fnum(r.get("age_s")) for r in group) if x is not None]
        before = [x for x in (fnum(r.get("r_before_mps")) for r in group) if x is not None]
        after = [x for x in (fnum(r.get("r_after_contract_b_mps")) for r in group) if x is not None]
        raw_plant = [x for x in (fnum(r.get("delayed_logged_setpoint_vz_up_mps")) for r in group) if x is not None]
        correction = [x for x in (fnum(r.get("contract_b_correction_vz_up_mps")) for r in group) if x is not None]
        auth = [x for x in (fnum(r.get("auth_at_latch")) for r in group) if x is not None]
        owners = sorted({str(r.get("term_status_owner", "")) for r in group if str(r.get("term_status_owner", ""))})
        unique_ages = sorted(set(round(x, 9) for x in ages))
        age_span = (max(ages) - min(ages)) if ages else 0.0
        estimable = len(group) >= MIN_CUT_ROWS and len(unique_ages) >= MIN_UNIQUE_AGES and age_span >= MIN_AGE_SPAN_S
        b0_before, b1_before = linreg(ages, before)
        b0_after, b1_after = linreg(ages, after)
        raw_plant_rms = rms(raw_plant)
        correction_rms = rms(correction)
        near_zero = isinstance(correction_rms, float) and correction_rms < NEAR_ZERO_RMS_MPS
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
            "n_unique_ages": len(unique_ages),
            "age_min_s": min(ages) if ages else "",
            "age_max_s": max(ages) if ages else "",
            "age_span_s": age_span if ages else "",
            "estimable_cut": estimable,
            "estimability_rule": ">=4 rows, >=4 unique ages, age span >=0.15s",
            "auth_at_latch_median": auth_med,
            "auth_ge_0p999": auth_full,
            "term_status_owners": "|".join(owners),
            "term_owned_rows": sum(1 for r in group if str(r.get("term_owned_support")) == "True"),
            "logged_plant_rms_mps": raw_plant_rms,
            "contract_b_correction_rms_mps": correction_rms,
            "near_zero_logged_plant_activity": near_zero,
            "near_zero_basis": "contract_b_correction_rms_mps after TERM ownership gate",
            "b0_before_mps": b0_before,
            "b1_before_mps2": b1_before,
            "abs_b1_before_mps2": abs(b1_before) if isinstance(b1_before, float) else "",
            "large_b1_before": estimable and isinstance(b1_before, float) and abs(b1_before) > LARGE_B1_MPS2,
            "b0_after_valid_plant_mps": b0_after,
            "b1_after_valid_plant_mps2": b1_after,
            "abs_b1_after_valid_plant_mps2": abs(b1_after) if isinstance(b1_after, float) else "",
            "large_b1_after": estimable and isinstance(b1_after, float) and abs(b1_after) > LARGE_B1_MPS2,
            "prediction_filter_refutation_cut": (
                estimable and auth_full and near_zero and isinstance(b1_before, float) and abs(b1_before) > LARGE_B1_MPS2
            ),
            "plant_signal": p["plant_signal"],
            "after_formula": p["after_formula"],
        })
    return out


def cluster_intervention_rows(p: dict[str, Any], cuts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in cuts:
        groups[row["cluster_id"]].append(row)
    out = []
    for cluster_id, group in sorted(groups.items()):
        estimable = [r for r in group if str(r.get("estimable_cut")) == "True"]
        before_large = [r for r in estimable if str(r.get("large_b1_before")) == "True"]
        after_large = [r for r in estimable if str(r.get("large_b1_after")) == "True"]
        near_zero = [r for r in estimable if str(r.get("near_zero_logged_plant_activity")) == "True"]
        weights = [int(r.get("n_rows") or 0) for r in estimable]
        before_weighted = (
            sum(w for w, r in zip(weights, estimable) if str(r.get("large_b1_before")) == "True") / sum(weights)
            if weights and sum(weights) > 0 else ""
        )
        after_weighted = (
            sum(w for w, r in zip(weights, estimable) if str(r.get("large_b1_after")) == "True") / sum(weights)
            if weights and sum(weights) > 0 else ""
        )
        out.append({
            **meta(p),
            "cluster_id": cluster_id,
            "flight_id": group[0].get("flight_id", ""),
            "flight": group[0].get("flight", ""),
            "era": group[0].get("era", ""),
            "recording_regime": group[0].get("recording_regime", ""),
            "n_cuts_total": len(group),
            "n_cuts_estimable": len(estimable),
            "n_cuts_excluded": len(group) - len(estimable),
            "large_any_cut_before": bool(before_large),
            "large_any_cut_after": bool(after_large),
            "large_support_weighted_before": before_weighted,
            "large_support_weighted_after": after_weighted,
            "near_zero_estimable_cuts": len(near_zero),
            "near_zero_any_after_large": any(str(r.get("large_b1_after")) == "True" for r in near_zero),
            "refutation_candidate_cuts": sum(1 for r in estimable if str(r.get("prediction_filter_refutation_cut")) == "True"),
            "max_abs_b1_before_mps2": max([float(r["abs_b1_before_mps2"]) for r in estimable if fnum(r.get("abs_b1_before_mps2")) is not None], default=""),
            "max_abs_b1_after_mps2": max([float(r["abs_b1_after_valid_plant_mps2"]) for r in estimable if fnum(r.get("abs_b1_after_valid_plant_mps2")) is not None], default=""),
        })
    return out


def fit_linear_predictor(cuts: list[dict[str, Any]], target_key: str) -> list[float]:
    xs = []
    ys = []
    for row in cuts:
        y = fnum(row.get(target_key))
        auth = fnum(row.get("auth_at_latch_median"))
        plant = fnum(row.get("contract_b_correction_rms_mps"))
        if y is None or auth is None or plant is None:
            continue
        xs.append([1.0, auth, plant])
        ys.append(y)
    if len(xs) < 3:
        return [statistics.fmean(ys) if ys else 0.0, 0.0, 0.0]
    # Small normal-equation solver for 3 coefficients.
    a = [[0.0] * 3 for _ in range(3)]
    b = [0.0] * 3
    for x, y in zip(xs, ys):
        for i in range(3):
            b[i] += x[i] * y
            for j in range(3):
                a[i][j] += x[i] * x[j]
    # Ridge keeps singular all-auth/all-plant cases invertible without changing scale materially.
    for i in range(3):
        a[i][i] += 1e-9
    for col in range(3):
        pivot = max(range(col, 3), key=lambda r: abs(a[r][col]))
        a[col], a[pivot] = a[pivot], a[col]
        b[col], b[pivot] = b[pivot], b[col]
        div = a[col][col]
        if abs(div) < 1e-18:
            return [statistics.fmean(ys), 0.0, 0.0]
        for j in range(col, 3):
            a[col][j] /= div
        b[col] /= div
        for r in range(3):
            if r == col:
                continue
            factor = a[r][col]
            for j in range(col, 3):
                a[r][j] -= factor * a[col][j]
            b[r] -= factor * b[col]
    return b


def pred(coeffs: list[float], row: dict[str, Any]) -> float:
    auth = fnum(row.get("auth_at_latch_median")) or 0.0
    plant = fnum(row.get("contract_b_correction_rms_mps")) or 0.0
    return coeffs[0] + coeffs[1] * auth + coeffs[2] * plant


def driver_decomposition(p: dict[str, Any], samples: list[dict[str, Any]],
                         cuts: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    estimable_cuts = [r for r in cuts if str(r.get("estimable_cut")) == "True"]
    estimable_cut_ids = {r["cut_id"] for r in estimable_cuts}
    cuts_by_id = {r["cut_id"]: r for r in estimable_cuts}
    sample_rows = [r for r in samples if r["cut_id"] in estimable_cut_ids]
    out_samples = []
    for held_out in sorted({r["cluster_id"] for r in sample_rows}):
        train_cuts = [r for r in estimable_cuts if r["cluster_id"] != held_out]
        coeff_before = fit_linear_predictor(train_cuts, "b0_before_mps")
        coeff_after = fit_linear_predictor(train_cuts, "b0_after_valid_plant_mps")
        for row in [r for r in sample_rows if r["cluster_id"] == held_out]:
            cut = cuts_by_id[row["cut_id"]]
            r_before = fnum(row.get("r_before_mps"))
            r_after = fnum(row.get("r_after_contract_b_mps"))
            if r_before is None or r_after is None:
                continue
            b_pred = pred(coeff_before, cut)
            d_pred = pred(coeff_after, cut)
            base = {
                **meta(p),
                "cluster_id": row["cluster_id"],
                "flight_id": row["flight_id"],
                "cut_id": row["cut_id"],
                "frame_id": row["frame_id"],
                "age_s": row["age_s"],
                "command_regime": row.get("command_regime", ""),
                "crossfit_held_out_cluster": held_out,
                "raw_before_r_v_mps": r_before,
                "contract_b_after_r_v_mps": r_after,
                "predicted_b0_before_from_train_mps": b_pred,
                "predicted_b0_after_from_train_mps": d_pred,
                "A_raw_shadow_residual_mps": r_before,
                "B_cut_intercept_adjusted_mps": r_before - b_pred,
                "C_response_adjusted_mps": r_after,
                "D_both_adjusted_mps": r_after - d_pred,
            }
            out_samples.append(base)

    fit_rows = []
    loao_rows = []
    for label, key in [
        ("A_raw_shadow_residual", "A_raw_shadow_residual_mps"),
        ("B_cut_intercept_adjusted", "B_cut_intercept_adjusted_mps"),
        ("C_response_adjusted", "C_response_adjusted_mps"),
        ("D_both_adjusted", "D_both_adjusted_mps"),
    ]:
        fit_input = [
            {
                "cluster_id": r["cluster_id"],
                "flight_id": r["flight_id"],
                "age_s": r["age_s"],
                "r_v_mps": r[key],
            }
            for r in out_samples if fnum(r.get(key)) is not None
        ]
        if not fit_input:
            continue
        fit = fit_release_fast(fit_input)
        boot = cluster_bootstrap_fast(fit_input)
        u95 = max(float(fit["profile_u95_sigma_a_mps2"]), float(boot["cluster_bootstrap_u95_sigma_a_mps2"]))
        fit_rows.append({
            **meta(p),
            "driver": label,
            "n_clusters": len({r["cluster_id"] for r in fit_input}),
            "n_rows": len(fit_input),
            "point_sigma_a_mps2": fit["sigma_a_mps2"],
            "profile_u95_sigma_a_mps2": fit["profile_u95_sigma_a_mps2"],
            "approach_bootstrap_u95_sigma_a_mps2": boot["cluster_bootstrap_u95_sigma_a_mps2"],
            "u95_conservative_mps2": u95,
            "b0_mps": fit["b0"],
            "b1_mps_per_s": fit["b1"],
            "profile_nearly_flat": fit["profile_nearly_flat"],
            "fit_backend": fit.get("fit_backend", FIT_BACKEND),
            "crossfit": "approach-outer; intercept predictors trained excluding held-out approach",
        })
        for row in loao_sensitivity_fast(fit_input):
            loao_rows.append({**meta(p), "driver": label, **row})
    return out_samples, fit_rows, loao_rows


def summarize_contract(p: dict[str, Any], diagnostic_corr: list[dict[str, Any]], rows: list[dict[str, Any]],
                       cuts: list[dict[str, Any]], clusters: list[dict[str, Any]],
                       lag_s: float, driver_fits: list[dict[str, Any]]) -> dict[str, Any]:
    max_feature_diff = max(
        [abs(x) for x in (fnum(r.get("features_archive_setpoint_diff_mps")) for r in rows) if x is not None],
        default=0.0,
    )
    before_large = [r for r in clusters if str(r.get("large_any_cut_before")) == "True"]
    after_large = [r for r in clusters if str(r.get("large_any_cut_after")) == "True"]
    before_ids = {r["cluster_id"] for r in before_large}
    after_ids = {r["cluster_id"] for r in after_large}
    dropped_ids = sorted(before_ids - after_ids)
    near_zero_bad = [
        r for r in clusters
        if int(r.get("near_zero_estimable_cuts") or 0) > 0
        and str(r.get("near_zero_any_after_large")) == "True"
    ]
    refutation_clusters = sorted({
        r["cluster_id"] for r in cuts if str(r.get("prediction_filter_refutation_cut")) == "True"
    })
    b_count = len(before_large)
    a_count = len(before_ids & after_ids)
    d_count = b_count - a_count
    q_count = len(near_zero_bad)
    collapse_threshold = math.ceil(b_count / 2.0) if b_count else 0
    fell_by_half = d_count >= collapse_threshold if b_count else False
    near_zero_compliant = not near_zero_bad
    if q_count >= QUIET_REFUTATION_K:
        verdict = "REFUTED"
        residual_admissibility = "INADMISSIBLE_as_mechanism_corrected_drift_measurement"
    elif 0 < q_count < QUIET_REFUTATION_K:
        verdict = "HOLD_INCONCLUSIVE_QUIET_BREACH"
        residual_admissibility = "INADMISSIBLE_pending_quiet_breach_resolution"
    elif q_count == 0 and d_count >= collapse_threshold and b_count > 0:
        verdict = "CONFIRMED_SUFFICIENT_FOR_EVALUATOR"
        residual_admissibility = "CANDIDATE_evaluator_corrected_statistical_input"
    elif q_count == 0 and 0 < d_count < collapse_threshold:
        verdict = "CONTRIBUTORY_NOT_SUFFICIENT"
        residual_admissibility = "DIAGNOSTIC_ONLY_next_naming_round_input"
    elif q_count == 0 and d_count <= 0:
        verdict = "REFUTED_AS_REGISTERED_REMAINDER_EXPLANATION"
        residual_admissibility = "INADMISSIBLE_as_corrected_mechanism_drift_measurement"
    elif len(refutation_clusters) >= 2:
        # Kept unreachable under the machine table except as a consistency guard.
        verdict = "REFUTED_BY_QUIET_CELL"
        residual_admissibility = "INADMISSIBLE_as_mechanism_corrected_drift_measurement"
    else:
        verdict = "NO_COLLAPSE_OR_UNJUDGED"
        residual_admissibility = "DIAGNOSTIC_ONLY_unclassified"
    return {
        "diagnostic_only": True,
        "repo_head": p["report_generator_commit"],
        "criterion_commit": p["criterion_commit"],
        "response58_commit": p["response58_commit"],
        "response61_commit": p["response61_commit"],
        "response62_commit": p["response62_commit"],
        "response63_commit": p["response63_commit"],
        "input_manifest_path": p["input_manifest_path"],
        "input_manifest_sha256": p["input_manifest_sha256"],
        "plant_signal": p["plant_signal"],
        "plant_formula": p["plant_formula"],
        "stream_contract": p["stream_contract"],
        "response_model": p["response_model"],
        "fit_backend": p["fit_backend"],
        "a091_calibrated_lag_s": lag_s,
        "n_samples": len(rows),
        "n_clusters": len({r["cluster_id"] for r in rows}),
        "n_unique_exposures": len({(r["flight_id"], r["frame_id"], r["feature_ts_ns"]) for r in rows}),
        "max_abs_diff_vs_features_archive_setpoint_vz_up_mps": max_feature_diff,
        "correlation_table_status": "DIAGNOSTIC_ONLY_GATE_WITHDRAWN",
        "correlation_negative_scopes": [
            {
                "era": r["era"],
                "recording_regime": r["recording_regime"],
                "corr_logged_plant_vs_oracle_ref": r["corr_logged_plant_vs_oracle_ref"],
            }
            for r in diagnostic_corr if fnum(r.get("corr_logged_plant_vs_oracle_ref")) is not None
            and float(r["corr_logged_plant_vs_oracle_ref"]) <= 0.0
        ],
        "estimable_cuts": sum(1 for r in cuts if str(r.get("estimable_cut")) == "True"),
        "excluded_cuts": sum(1 for r in cuts if str(r.get("estimable_cut")) != "True"),
        "large_cluster_count_before": len(before_large),
        "large_cluster_count_after_total": len(after_large),
        "large_cluster_count_after_on_before_support": a_count,
        "machine_decision_B_before_large_approaches": b_count,
        "machine_decision_A_same_approaches_large_after": a_count,
        "machine_decision_D_collapsed_approaches": d_count,
        "machine_decision_Q_quiet_after_large_approaches": q_count,
        "machine_decision_K_quiet_refutation": QUIET_REFUTATION_K,
        "machine_decision_collapse_threshold_ceil_B_over_2": collapse_threshold,
        "clusters_dropped_by_intervention": dropped_ids,
        "large_count_fell_by_half": fell_by_half,
        "near_zero_after_large_count": len(near_zero_bad),
        "prediction_refutation_candidate_clusters": refutation_clusters,
        "prediction_refutation_branch_met": q_count >= QUIET_REFUTATION_K,
        "intervention_verdict": verdict,
        "residual_admissibility": residual_admissibility,
        "post_intervention_residual_field": "plant_stream_samples.csv:r_after_contract_b_mps",
        "post_intervention_residual_admissible_input": (
            "plant_stream_samples.csv:r_after_contract_b_mps"
            if residual_admissibility.startswith("CANDIDATE") else ""
        ),
        "driver_decomposition_status": "RUN",
        "driver_count": len(driver_fits),
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
    zero_lag_enriched = enrich_samples(samples, features, p, response_lag_s=0.0)
    lag_s, lag_rows = lag_calibration_from_a091(p, zero_lag_enriched)
    enriched = enrich_samples(samples, features, p, response_lag_s=lag_s)
    diagnostic_corr, _may_run_judge = validity_precheck(p, enriched)
    zero_lag_cuts = cut_intervention_rows(p, zero_lag_enriched)
    cuts = cut_intervention_rows(p, enriched)
    clusters = cluster_intervention_rows(p, cuts)
    driver_samples, driver_fits, driver_loao = driver_decomposition(p, enriched, cuts)

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
            "Stream contract: Contract B, commanded velocity reference. The logged",
            "setpoint is the innermost commanded reference delivered to the velocity",
            "backend, not achieved motion. The counterfactual therefore enters through",
            "the declared response model rather than raw zero-lag subtraction.",
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
            f"Response model: pure-delay command reference, lag calibrated from A091 only at `{lag_s:.3f}` s.",
            "Ownership gate: rows whose prior `term_status.owner` is `term` get",
            "`contract_b_correction_vz_up_mps = 0.0` as the RESPONSE63 structural no-op.",
            "All other rows use the delayed logged setpoint world-up value.",
            "For each feature row:",
            "",
            "`delayed_logged_setpoint_vz_up_mps = setpoint_world_up_at_or_before(feature_mono_ns - lag)`",
            "",
            "The intervention residual is:",
            "",
            "`r_after = v_ref_oracle_mps - (v_latch_true_mps + contract_b_correction_vz_up_mps)`",
            "",
            "The old zero-lag correlation gate is withdrawn by RESPONSE61 and is",
            "published only as diagnostic disclosure.",
            "",
        ]) + "\n",
    )
    write_json(out_dir / "lineage_packet.json", p)
    write_csv(out_dir / "lag_calibration_a091.csv", lag_rows)
    write_csv(out_dir / "plant_stream_samples.csv", [
        {
            **meta(p),
            "approach_id": r.get("approach_id", ""),
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
            "term_status_mono_ns": r["term_status_mono_ns"],
            "term_status_age_s": r["term_status_age_s"],
            "term_status_owner": r["term_status_owner"],
            "term_status_engaged": r["term_status_engaged"],
            "term_status_ready": r["term_status_ready"],
            "term_owned_support": r["term_owned_support"],
            "level_pitch_rad": r["level_pitch_rad"],
            "level_roll_rad": r["level_roll_rad"],
            "logged_setpoint_vz_up_mps": r["logged_setpoint_vz_up_mps"],
            "response_lag_s": r["response_lag_s"],
            "lagged_setpoint_mono_ns": r["lagged_setpoint_mono_ns"],
            "lagged_setpoint_age_s": r["lagged_setpoint_age_s"],
            "delayed_logged_setpoint_vz_up_mps": r["delayed_logged_setpoint_vz_up_mps"],
            "contract_b_correction_vz_up_mps": r["contract_b_correction_vz_up_mps"],
            "ownership_gate_rule": r["ownership_gate_rule"],
            "features_archive_setpoint_vz_up_mps": r["features_archive_setpoint_vz_up_mps"],
            "features_archive_setpoint_diff_mps": r["features_archive_setpoint_diff_mps"],
            "v_ref_oracle_mps": r["v_ref_oracle_mps"],
            "truth_vz_up_mps": r["truth_vz_up_mps"],
            "v_latch_true_mps": r.get("v_latch_true_mps", ""),
            "r_before_mps": r["r_before_mps"],
            "r_after_contract_b_mps": r["r_after_contract_b_mps"],
            "before_formula": r["before_formula"],
            "after_formula": r["after_formula"],
        }
        for r in enriched
    ])
    write_csv(out_dir / "contract_b_diagnostic_correlation_by_era.csv", diagnostic_corr)
    write_csv(out_dir / "zero_lag_sensitivity_cut.csv", zero_lag_cuts)
    write_csv(out_dir / "intervention_cut_b1_before_after_contract_b.csv", cuts)
    write_csv(out_dir / "intervention_cluster_b1_before_after_contract_b.csv", clusters)
    write_csv(out_dir / "driver_decomposition_samples.csv", driver_samples)
    write_csv(out_dir / "driver_decomposition_fit.csv", driver_fits)
    write_csv(out_dir / "driver_decomposition_loao.csv", driver_loao)

    field_groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in enriched:
        field_groups[(r["era"], r["recording_regime"], r["setpoint_field_name"], r["term_status_owner"])].append(r)
    disclosure = []
    for (era, regime, field, owner), group in sorted(field_groups.items()):
        ages = [x for x in (fnum(r.get("setpoint_age_s")) for r in group) if x is not None]
        disclosure.append({
            **meta(p),
            "era": era,
            "recording_regime": regime,
            "flight_jsonl_setpoint_field": field,
            "term_status_owner": owner,
            "rows": len(group),
            "clusters": len({r["cluster_id"] for r in group}),
            "term_owned_rows": sum(1 for r in group if str(r.get("term_owned_support")) == "True"),
            "plant_stream": p["plant_signal"],
            "world_up_conversion": p["plant_formula"],
            "stream_contract": p["stream_contract"],
            "response_model": p["response_model"],
            "response_lag_s": lag_s,
            "setpoint_age_max_s": max(ages) if ages else "",
            "command_semantics": "0.0 is observed zero command; absent field is missing; no truthiness filter",
            "mixed_ownership_handling": "reported by era/recording_regime; TERM/common-arm rows remain disclosed, no silent pooling by ownership state",
            "feed_forward_reference_used_by_sigma_eval": "delayed logged setpoint world-up reference per Contract B",
        })
    write_csv(out_dir / "harness_stream_disclosure.csv", disclosure)

    summary = summarize_contract(p, diagnostic_corr, enriched, cuts, clusters, lag_s, driver_fits)

    write_json(out_dir / "summary.json", summary)
    corr_text = ", ".join(
        f"{r['era']}/{r['recording_regime']}={r['corr_logged_plant_vs_oracle_ref']}"
        for r in summary["correlation_negative_scopes"]
    )
    driver_lines = [
        (
            f"- `{r['driver']}`: point `{r['point_sigma_a_mps2']}`, "
            f"profile U95 `{r['profile_u95_sigma_a_mps2']}`, "
            f"bootstrap U95 `{r['approach_bootstrap_u95_sigma_a_mps2']}`, "
            f"conservative `{r['u95_conservative_mps2']}`"
        )
        for r in driver_fits
    ]
    write_text(
        out_dir / "summary.md",
        "\n".join([
            "# Contract-B Plant-Stream Intervention Rerun",
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
            "It is typed as Contract B commanded velocity reference, with pure-delay",
            "response before entering the counterfactual residual.",
            f"A091 selected response lag: `{lag_s}` seconds.",
            f"Max abs diff versus `features_archive.setpoint_vz_up_mps`: `{summary['max_abs_diff_vs_features_archive_setpoint_vz_up_mps']}`.",
            "",
            "## Diagnostic Correlation",
            "",
            "The old zero-lag positive-correlation gate is withdrawn; these rows are diagnostic only.",
            f"Non-positive zero-lag scopes: `{corr_text}`.",
            "",
            "## Judge",
            "",
            f"Judge status: `RUN_CONTRACT_B_RESPONSE_MODEL`.",
            f"Intervention verdict: `{summary['intervention_verdict']}`.",
            f"Residual admissibility: `{summary['residual_admissibility']}`.",
            f"B before-large approaches: `{summary['machine_decision_B_before_large_approaches']}`.",
            f"A same-approach large-after: `{summary['machine_decision_A_same_approaches_large_after']}`.",
            f"D collapsed approaches: `{summary['machine_decision_D_collapsed_approaches']}`.",
            f"Q quiet-after-large approaches: `{summary['machine_decision_Q_quiet_after_large_approaches']}`.",
            f"Large cluster count after total: `{summary['large_cluster_count_after_total']}`.",
            f"Clusters dropped by intervention: `{summary['clusters_dropped_by_intervention']}`.",
            f"Prediction refutation branch met: `{summary['prediction_refutation_branch_met']}`.",
            f"Driver decomposition status: `{summary['driver_decomposition_status']}`.",
            "",
            "## A/B/C/D",
            "",
            *(driver_lines or ["No driver decomposition rows were generated."]),
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
