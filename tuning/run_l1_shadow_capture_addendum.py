"""L1 shadow-capture + sigma-harvest addendum replay for commit a150ece.

QA & MOCK-TUNER scope: recorded video replay only. This script reuses the
fresh-video perception replay harness and then runs the current terminal
observer + shadow ownership/admission logic over both terminal feature topics:
`feature` and `feature_side`. It writes only under tuning/.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import subprocess
import sys
import types
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tuning"))

from aigp.core.params import ParamSet  # noqa: E402
from aigp.planning.vertical_owner import (  # noqa: E402
    TERM_OWNER,
    TerminalOracle,
    VerticalOwnerArbiter,
)
from aigp.planning.vertical_terminal import crossing_error, crossing_sigma  # noqa: E402


def apply_patches(params: ParamSet, patches: list[str]) -> ParamSet:
    overrides = {}
    for item in patches:
        key, sep, raw = item.partition("=")
        if not sep:
            raise SystemExit(f"--patch needs KEY=VALUE, got: {item}")
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            value = raw
        overrides[key.strip()] = value
    return params.patch(overrides) if overrides else params


SOURCE_REF = "a150ece"


def source_commit() -> tuple[str, str, list[str]]:
    source = subprocess.check_output(
        ["git", "rev-parse", SOURCE_REF],
        cwd=ROOT,
        text=True,
    ).strip()
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", f"{SOURCE_REF}..HEAD", "--", ".", ":!tuning"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    return source, source[:7], changed


shim_main = types.ModuleType("aigp.main")
shim_main.apply_patches = apply_patches
sys.modules.setdefault("aigp.main", shim_main)

from run_l1_perception_replay import (  # noqa: E402
    TARGETS,
    ReplayOptions,
    assert_mock_safe,
    fnum,
    fmt,
    git_head,
    median,
    read_jsonl,
    replay_oracle_from_rows,
    run_video_replay,
    should_feed_feature,
    write_csv,
)


@dataclass
class ShadowOptions(ReplayOptions):
    force_position_phase: bool = True


def load_setpoint_speeds(log_path: Path) -> list[tuple[int, float]]:
    speeds = []
    for rec in read_jsonl(log_path):
        if rec.get("topic") != "setpoint":
            continue
        data = rec.get("data", {})
        v = data.get("v_body") or data.get("vel_body") or data.get("velocity_body")
        speed = None
        if isinstance(v, list) and len(v) >= 2:
            speed = math.hypot(float(v[0]), float(v[1]))
        if speed is None:
            speed = fnum(data.get("speed_mps"))
        if speed is None:
            continue
        speeds.append((int(rec.get("mono_ns", 0)), float(speed)))
    speeds.sort()
    return speeds


def speed_at(speeds: list[tuple[int, float]], mono_ns: int,
             default_speed: float) -> float:
    out = default_speed
    for ts, speed in speeds:
        if ts > mono_ns:
            break
        out = speed
    return out


def attach_setpoint_speeds(params: ParamSet, rows: list[dict],
                           targets: list[dict]) -> None:
    default_speed = float(params.get("planner.commit.speed_mps", default=2.5))
    by_flight = {t["label"]: load_setpoint_speeds(ROOT / t["log"])
                 for t in targets}
    for row in rows:
        row["setpoint_speed_xy_mps"] = speed_at(
            by_flight.get(row["flight"], []),
            int(row["mono_ns"]),
            default_speed,
        )


def overlap_stats(oracle: TerminalOracle, ts_s: float) -> tuple[int, float | None]:
    pairs = list(getattr(oracle, "_overlap_deltas", []))
    if not pairs:
        return 0, None
    i = len(pairs) - 1
    while i > 0 and float(pairs[i][0]) - float(pairs[i - 1][0]) <= 0.12:
        i -= 1
    tail = pairs[i:]
    deltas = [float(d) for _, d in tail if ts_s - float(tail[-1][0]) <= 0.12]
    if not deltas:
        return 0, None
    return len(deltas), statistics.median(deltas)


def terminal_tail_s(params: ParamSet) -> float:
    abort_min = float(params.get("planner.commit.abort_min_dist_m", default=0.8))
    speed = float(params.get("planner.commit.speed_mps", default=2.5))
    coverage = float(params.get("planner.terminal.coverage_tail_p95_s", default=0.50))
    return max(0.45, abort_min / max(speed, 0.1), coverage)


def admission_metrics(params: ParamSet, oracle: TerminalOracle,
                      row: dict) -> dict:
    if not oracle.ready():
        return {
            "admission_score": "",
            "admission_mu": "",
            "admission_sigma": "",
            "admission_h_tail_s": "",
            "admission_vz_vis_mps": "",
            "admission_e_cross_m": "",
            "sigma_induced_abort": False,
        }
    e_now = fnum(row.get("e_meas"))
    if e_now is None and getattr(oracle, "_hist", None):
        e_now = float(oracle._hist[-1][1])
    if e_now is None:
        return {
            "admission_score": "",
            "admission_mu": "",
            "admission_sigma": "",
            "admission_h_tail_s": "",
            "admission_vz_vis_mps": "",
            "admission_e_cross_m": "",
            "sigma_induced_abort": False,
        }
    speed = max(float(row.get("setpoint_speed_xy_mps") or 0.0),
                float(params.get("planner.commit.speed_mps", default=2.5)),
                0.5)
    r = max(float(row.get("range_z_m") or 0.0), 0.05)
    tau_s = r / speed
    h_tail = min(tau_s, terminal_tail_s(params))
    vz = oracle.v_z_visual()
    vz_vis = 0.0 if vz is None else float(vz) * oracle.rate_authority()
    sig_e, sig_v = oracle.sigmas()
    e_cross = crossing_error(float(e_now), vz_vis, h_tail)
    sigma = crossing_sigma(sig_e, vz_vis, sig_v, h_tail)
    score = abs(e_cross) + 2.0 * sigma + 0.06
    mu = abs(e_cross) + 0.06
    corridor = float(params.get("planner.terminal.corridor_interim_m", default=0.30))
    return {
        "admission_score": score,
        "admission_mu": mu,
        "admission_sigma": sigma,
        "admission_h_tail_s": h_tail,
        "admission_vz_vis_mps": vz_vis,
        "admission_e_cross_m": e_cross,
        "sigma_induced_abort": mu <= corridor < score,
    }


def replay_shadow_capture(params: ParamSet, rows: list[dict],
                          opts: ShadowOptions) -> tuple[list[dict], list[dict]]:
    oracle = TerminalOracle()
    arbiter = VerticalOwnerArbiter()
    timeline = []
    transitions = []
    first_below_2_ts = None
    prev_source = oracle.active_source
    transition_id = 0
    last_t = None
    current_flight = None
    vz_max = float(params.get("planner.terminal.vz_max_mps", default=0.6))
    corridor = float(params.get("planner.terminal.corridor_interim_m", default=0.30))

    for row in rows:
        if not row.get("commit"):
            continue
        if current_flight != row["flight"]:
            oracle = TerminalOracle()
            arbiter = VerticalOwnerArbiter()
            first_below_2_ts = None
            prev_source = oracle.active_source
            last_t = None
            current_flight = row["flight"]
        r = fnum(row.get("range_z_m"))
        if r is not None and r <= 2.0 and first_below_2_ts is None:
            first_below_2_ts = float(row["t_rel_s"])
        fed = should_feed_feature(row, opts, first_below_2_ts)
        e_meas_raw = fnum(row.get("e_meas")) if fed else None
        source_valid = (
            fed
            and e_meas_raw is not None
            and row.get("cert_status") == "certified"
            and row.get("feature_mode") in ("FULL_QUAD", "SIDE_PAIR")
        )
        e_meas = e_meas_raw if source_valid else None
        active_sample = False
        ts_s = float(row["feature_ts_ns"]) / 1e9
        if e_meas is not None:
            active_sample = oracle.observe(ts_s, float(e_meas),
                                           source=row["feature_mode"])
        transition_row = None
        if oracle.active_source != prev_source:
            transition_id += 1
            n_overlap, overlap_delta = overlap_stats(oracle, ts_s)
            transition_row = {
                "transition_id": transition_id,
                "sweep": opts.label,
                "flight": row["flight"],
                "t_rel_s": row["t_rel_s"],
                "range_z_m": row.get("range_z_m", ""),
                "from_source": prev_source,
                "to_source": oracle.active_source,
                "paired_overlap_count": n_overlap,
                "overlap_delta_median": overlap_delta if overlap_delta is not None else "",
                "jump_grace_consumed": False,
                "sigma_induced_abort_after": False,
            }
            transitions.append(transition_row)
            prev_source = oracle.active_source

        decision_row = dict(row)
        if not active_sample:
            decision_row["e_meas"] = ""
        metrics = admission_metrics(params, oracle, decision_row)
        admission_score = fnum(metrics.get("admission_score"))
        first_capture_ok = (
            source_valid
            and row.get("topic", "feature") == "feature"
            and row.get("feature_mode") == "FULL_QUAD"
            and oracle.ready()
            and oracle.active_source == "FULL_QUAD"
            and admission_score is not None
            and admission_score <= corridor
        )
        maintain_ok = arbiter.owner == TERM_OWNER and source_valid
        capture_certified = first_capture_ok or maintain_ok
        if row.get("topic", "feature") == "feature":
            arbiter.note_exposure(source_valid)
        phase = "position" if opts.force_position_phase else str(row.get("phase") or "")
        owner = arbiter.tick(
            commit_active=True,
            same_gate=True,
            certified=capture_certified,
            feature_age_s=float(row.get("gate_age_s") or 0.0),
            phase=phase,
        )
        grace_before = bool(getattr(oracle, "_transition_grace", False))
        dt = 0.02 if last_t is None else max(float(row["t_rel_s"]) - last_t, 1e-3)
        applied_e_z = ""
        if owner == TERM_OWNER:
            applied = oracle.update(float(e_meas) if active_sample else None,
                                    dt=dt, vz_max=vz_max)
            applied_e_z = applied if applied is not None else ""
        grace_after = bool(getattr(oracle, "_transition_grace", False))
        jump_grace_consumed = grace_before and not grace_after
        if transition_row is not None:
            transition_row["jump_grace_consumed"] = jump_grace_consumed
        if transitions and oracle.active_source == transitions[-1]["to_source"]:
            transitions[-1]["sigma_induced_abort_after"] = (
                transitions[-1]["sigma_induced_abort_after"]
                or bool(metrics["sigma_induced_abort"])
            )
            transitions[-1]["jump_grace_consumed"] = (
                transitions[-1]["jump_grace_consumed"] or jump_grace_consumed
            )
        n_hist, span, gap = oracle.history_stats()
        shadow_capture = (
            oracle.ready()
            and admission_score is not None
            and admission_score <= corridor
            and owner == TERM_OWNER
            and phase == "position"
            and oracle.active_source in ("FULL_QUAD", "SIDE_PAIR")
        )
        timeline.append({
            **row,
            "sweep": opts.label,
            "fed": fed,
            "source_valid": source_valid,
            "active_sample": active_sample,
            "observer_ready": oracle.ready(),
            "ready_legacy": oracle.ready_legacy(),
            "shadow_owner": owner,
            "shadow_capture": shadow_capture,
            "shadow_phase": phase,
            "active_source": oracle.active_source,
            "hist_n": n_hist,
            "hist_span_s": span,
            "hist_gap_s": gap,
            "admission_score": metrics["admission_score"],
            "admission_mu": metrics["admission_mu"],
            "admission_sigma": metrics["admission_sigma"],
            "admission_h_tail_s": metrics["admission_h_tail_s"],
            "admission_vz_vis_mps": metrics["admission_vz_vis_mps"],
            "admission_e_cross_m": metrics["admission_e_cross_m"],
            "sigma_induced_abort": metrics["sigma_induced_abort"],
            "oracle_e_z": oracle.e_z if oracle.e_z is not None else "",
            "oracle_disarmed": oracle.disarmed,
            "jump_grace_consumed": jump_grace_consumed,
            "applied_e_z": applied_e_z,
            "transition_id": transition_id if transition_id else "",
        })
        last_t = float(row["t_rel_s"])
    return timeline, transitions


def summarize_shadow(timeline: list[dict], transitions: list[dict]) -> list[dict]:
    out = []
    for sweep in sorted({r["sweep"] for r in timeline}):
        for flight in sorted({r["flight"] for r in timeline if r["sweep"] == sweep}):
            rows = [r for r in timeline if r["sweep"] == sweep and r["flight"] == flight]
            captures = [r for r in rows if r.get("shadow_capture")]
            owner_rows = [r for r in rows if r.get("shadow_owner") == TERM_OWNER]
            by2 = [r for r in captures if fnum(r.get("range_z_m")) is not None
                   and float(r["range_z_m"]) <= 2.2]
            trans = [t for t in transitions if t["sweep"] == sweep and t["flight"] == flight]
            held_through = bool(
                trans
                and owner_rows
                and any(t["to_source"] == "SIDE_PAIR" for t in trans)
                and not any(t.get("sigma_induced_abort_after") for t in trans)
            )
            score_vals = [float(r["admission_score"]) for r in rows
                          if fnum(r.get("admission_score")) is not None]
            out.append({
                "sweep": sweep,
                "flight": flight,
                "commit_rows": len(rows),
                "observer_ready_rows": sum(1 for r in rows if r.get("observer_ready")),
                "shadow_capture_rows": len(captures),
                "captures_by_2p2m": len(by2),
                "first_capture_range_m": captures[0]["range_z_m"] if captures else "",
                "first_capture_source": captures[0]["active_source"] if captures else "",
                "owner_term_rows": len(owner_rows),
                "owner_term_side_rows": sum(
                    1 for r in owner_rows if r.get("active_source") == "SIDE_PAIR"
                ),
                "min_admission_score": min(score_vals) if score_vals else "",
                "sigma_induced_abort_rows": sum(
                    1 for r in rows if r.get("sigma_induced_abort")
                ),
                "transition_count": len(trans),
                "held_through_full_to_side": held_through,
            })
    return out


RANGE_BINS = [
    ("3p0-3p5", 3.0, 3.5),
    ("2p5-3p0", 2.5, 3.0),
    ("2p0-2p5", 2.0, 2.5),
    ("1p5-2p0", 1.5, 2.0),
    ("1p0-1p5", 1.0, 1.5),
    ("0p5-1p0", 0.5, 1.0),
    ("lt0p5", -float("inf"), 0.5),
]


def range_bin(value: float | None) -> str:
    if value is None:
        return "unknown"
    for label, lo, hi in RANGE_BINS:
        if lo <= value < hi:
            return label
    return "gte3p5"


def rms_centered(values: list[float]) -> float | None:
    vals = [v for v in values if math.isfinite(v)]
    if len(vals) < 2:
        return None
    m = statistics.fmean(vals)
    return math.sqrt(statistics.fmean([(v - m) ** 2 for v in vals]))


def sample_std(values: list[float]) -> float | None:
    vals = [v for v in values if math.isfinite(v)]
    return statistics.stdev(vals) if len(vals) >= 2 else None


def exact_pair_key(row: dict) -> tuple[str, str]:
    return row["flight"], str(row["feature_ts_ns"])


def sigma_harvest(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    full = [
        r for r in rows
        if r.get("feature_mode") == "FULL_QUAD"
        and r.get("cert_status") == "certified"
        and fnum(r.get("e_meas")) is not None
    ]
    side = [
        r for r in rows
        if r.get("feature_mode") == "SIDE_PAIR"
        and r.get("cert_status") == "certified"
        and fnum(r.get("e_meas")) is not None
    ]
    full_by_key: dict[tuple[str, str], dict] = {}
    for row in full:
        full_by_key.setdefault(exact_pair_key(row), row)
    pairs = []
    for row in side:
        st = float(row["feature_ts_ns"]) / 1e9
        frow = full_by_key.get(exact_pair_key(row))
        if frow is None:
            continue
        dt = abs(st - float(frow["feature_ts_ns"]) / 1e9)
        rng = fnum(row.get("range_z_m"))
        residual = float(row["e_meas"]) - float(frow["e_meas"])
        pairs.append({
            "cohort": row.get("cohort", "primary"),
            "flight": row["flight"],
            "side_frame_id": row["frame_id"],
            "full_frame_id": frow["frame_id"],
            "side_topic": row.get("topic", ""),
            "full_topic": frow.get("topic", ""),
            "side_ts_s": st,
            "full_ts_s": float(frow["feature_ts_ns"]) / 1e9,
            "dt_s": dt,
            "range_z_m": rng if rng is not None else "",
            "range_bin": range_bin(rng),
            "side_e_z": row["e_meas"],
            "full_e_z": frow["e_meas"],
            "residual_e_m": residual,
            "pairing_mode": "exact_exposure",
        })

    summary = []
    groups: list[tuple[str, str, list[dict]]] = []
    for cohort in sorted({p["cohort"] for p in pairs} or {"primary"}):
        cr = [p for p in pairs if p["cohort"] == cohort]
        groups.append((cohort, "all", cr))
        for label, _, _ in RANGE_BINS:
            groups.append((cohort, label, [p for p in cr if p["range_bin"] == label]))
    for cohort, label, group in groups:
        residuals = [float(p["residual_e_m"]) for p in group]
        derivs = []
        for flight in sorted({p["flight"] for p in group}):
            fr = sorted([p for p in group if p["flight"] == flight],
                        key=lambda p: float(p["side_ts_s"]))
            for a, b in zip(fr, fr[1:]):
                dt = float(b["side_ts_s"]) - float(a["side_ts_s"])
                if 1e-3 < dt <= 0.25:
                    derivs.append((float(b["residual_e_m"])
                                   - float(a["residual_e_m"])) / dt)
        paired_switch_sigma_v = rms_centered(derivs) if len(derivs) >= 2 else ""
        summary.append({
            "cohort": cohort,
            "range_bin": label,
            "n": len(group),
            "bias_e_m": statistics.fmean(residuals) if residuals else "",
            "sigma_e_m": rms_centered(residuals) if len(residuals) >= 2 else "",
            "std_e_m": sample_std(residuals) if len(residuals) >= 2 else "",
            "sigma_v_mps": paired_switch_sigma_v,
            "paired_switch_sigma_v_mps": paired_switch_sigma_v,
            "std_v_mps": sample_std(derivs) if len(derivs) >= 2 else "",
            "n_v_pairs": len(derivs),
            "v_component": "paired_switch_exact_exposure",
        })
    return pairs, summary


TIME_SINCE_ANCHOR_BINS = [
    ("0p00-0p10", 0.0, 0.10),
    ("0p10-0p25", 0.10, 0.25),
    ("0p25-0p50", 0.25, 0.50),
    ("0p50-1p00", 0.50, 1.00),
    ("gte1p00", 1.00, float("inf")),
]


def time_since_anchor_bin(value: float | None) -> str:
    if value is None:
        return "unknown"
    for label, lo, hi in TIME_SINCE_ANCHOR_BINS:
        if lo <= value < hi:
            return label
    return "unknown"


def median_value(values: list[float]) -> float | str:
    vals = [v for v in values if math.isfinite(v)]
    return statistics.median(vals) if vals else ""


def maintenance_sigma_harvest(
    rows: list[dict],
    sweeps: list[ShadowOptions],
    paired_summary: list[dict],
) -> tuple[list[dict], list[dict], list[dict]]:
    full = [
        r for r in rows
        if r.get("feature_mode") == "FULL_QUAD"
        and r.get("cert_status") == "certified"
        and fnum(r.get("e_meas")) is not None
    ]
    side = [
        r for r in rows
        if r.get("feature_mode") == "SIDE_PAIR"
        and r.get("cert_status") == "certified"
        and fnum(r.get("e_meas")) is not None
    ]
    full_by_key: dict[tuple[str, str], dict] = {}
    for row in full:
        full_by_key.setdefault(exact_pair_key(row), row)

    exact_pairs: list[dict] = []
    for side_row in side:
        full_row = full_by_key.get(exact_pair_key(side_row))
        if full_row is None:
            continue
        ts_s = float(side_row["feature_ts_ns"]) / 1e9
        rng = fnum(side_row.get("range_z_m"))
        residual = float(side_row["e_meas"]) - float(full_row["e_meas"])
        exact_pairs.append({
            "cohort": side_row.get("cohort", "primary"),
            "flight": side_row["flight"],
            "ts_s": ts_s,
            "side_row": side_row,
            "full_row": full_row,
            "range_z_m": rng,
            "range_bin": range_bin(rng),
            "residual_e_m": residual,
        })
    exact_pairs.sort(key=lambda p: (p["cohort"], p["flight"], p["ts_s"]))

    rows_out = []
    withheld_sweeps = [s for s in sweeps if s.drop_full_below_m is not None]
    for opts in withheld_sweeps:
        for cohort, flight in sorted({(p["cohort"], p["flight"]) for p in exact_pairs}):
            flight_pairs = [
                p for p in exact_pairs
                if p["cohort"] == cohort and p["flight"] == flight
            ]
            anchor: dict | None = None
            for pair in flight_pairs:
                full_fed = should_feed_feature(pair["full_row"], opts, None)
                side_fed = should_feed_feature(pair["side_row"], opts, None)
                if full_fed and side_fed:
                    anchor = pair
                    continue
                if full_fed or not side_fed or anchor is None:
                    continue
                age_s = float(pair["ts_s"]) - float(anchor["ts_s"])
                if age_s <= 1e-6:
                    continue
                residual = float(pair["residual_e_m"])
                anchor_residual = float(anchor["residual_e_m"])
                drift = residual - anchor_residual
                rows_out.append({
                    "cohort": cohort,
                    "sweep": opts.label,
                    "flight": flight,
                    "side_frame_id": pair["side_row"]["frame_id"],
                    "withheld_full_frame_id": pair["full_row"]["frame_id"],
                    "anchor_frame_id": anchor["full_row"]["frame_id"],
                    "side_ts_s": pair["ts_s"],
                    "anchor_ts_s": anchor["ts_s"],
                    "time_since_anchor_s": age_s,
                    "time_since_anchor_bin": time_since_anchor_bin(age_s),
                    "range_z_m": pair["range_z_m"] if pair["range_z_m"] is not None else "",
                    "range_bin": pair["range_bin"],
                    "side_e_z": pair["side_row"]["e_meas"],
                    "withheld_full_e_z": pair["full_row"]["e_meas"],
                    "anchor_side_e_z": anchor["side_row"]["e_meas"],
                    "anchor_full_e_z": anchor["full_row"]["e_meas"],
                    "maintenance_residual_e_m": residual,
                    "anchor_residual_e_m": anchor_residual,
                    "residual_drift_from_anchor_m": drift,
                    "maintenance_interval_v_mps": drift / age_s,
                    "full_withheld_below_m": opts.drop_full_below_m,
                })

    summary = summarize_maintenance_sigma(rows_out)
    two_component = two_component_sigma_summary(summary, paired_summary)
    return rows_out, summary, two_component


def summarize_maintenance_sigma(rows: list[dict]) -> list[dict]:
    if not rows:
        return []
    groups: list[tuple[str, str, str, str, list[dict]]] = []
    cohorts = sorted({r["cohort"] for r in rows})
    sweeps = sorted({r["sweep"] for r in rows})
    range_labels = ["all"] + [label for label, _, _ in RANGE_BINS]
    age_labels = ["all"] + [label for label, _, _ in TIME_SINCE_ANCHOR_BINS]
    for cohort in cohorts:
        for sweep in sweeps + ["all_full_withheld"]:
            for rlabel in range_labels:
                for alabel in age_labels:
                    group = [
                        r for r in rows
                        if r["cohort"] == cohort
                        and (sweep == "all_full_withheld" or r["sweep"] == sweep)
                        and (rlabel == "all" or r["range_bin"] == rlabel)
                        and (alabel == "all" or r["time_since_anchor_bin"] == alabel)
                    ]
                    if group or (rlabel == "all" and alabel == "all"):
                        groups.append((cohort, sweep, rlabel, alabel, group))

    summary = []
    for cohort, sweep, rlabel, alabel, group in groups:
        residuals = [float(r["maintenance_residual_e_m"]) for r in group]
        drift_rates = [float(r["maintenance_interval_v_mps"]) for r in group]
        ages = [float(r["time_since_anchor_s"]) for r in group]
        ranges = [
            float(r["range_z_m"]) for r in group
            if fnum(r.get("range_z_m")) is not None
        ]
        summary.append({
            "cohort": cohort,
            "sweep": sweep,
            "range_bin": rlabel,
            "time_since_anchor_bin": alabel,
            "n": len(group),
            "bias_residual_e_m": statistics.fmean(residuals) if residuals else "",
            "sigma_residual_e_m": rms_centered(residuals) if len(residuals) >= 2 else "",
            "maintenance_sigma_v_mps": (
                rms_centered(drift_rates) if len(drift_rates) >= 2 else ""
            ),
            "maintenance_std_v_mps": (
                sample_std(drift_rates) if len(drift_rates) >= 2 else ""
            ),
            "median_time_since_anchor_s": median_value(ages),
            "median_range_z_m": median_value(ranges),
        })
    return summary


def two_component_sigma_summary(
    maintenance_summary: list[dict],
    paired_summary: list[dict],
) -> list[dict]:
    maint_lookup = {
        (r["cohort"], r["range_bin"]): r
        for r in maintenance_summary
        if r["sweep"] == "all_full_withheld"
        and r["time_since_anchor_bin"] == "all"
    }
    out = []
    for row in paired_summary:
        maint = maint_lookup.get((row["cohort"], row["range_bin"]))
        paired_v = fnum(row.get("paired_switch_sigma_v_mps"))
        maint_v = fnum(maint.get("maintenance_sigma_v_mps")) if maint else None
        candidates = [v for v in (paired_v, maint_v) if v is not None]
        out.append({
            "cohort": row["cohort"],
            "range_bin": row["range_bin"],
            "paired_n": row["n"],
            "paired_sigma_e_m": row["sigma_e_m"],
            "paired_switch_sigma_v_mps": row["paired_switch_sigma_v_mps"],
            "paired_n_v": row["n_v_pairs"],
            "maintenance_n": maint["n"] if maint else 0,
            "maintenance_sigma_v_mps": (
                maint["maintenance_sigma_v_mps"] if maint else ""
            ),
            "release_sigma_v_mps": max(candidates) if candidates else "",
            "release_sigma_v_source": (
                "maintenance"
                if maint_v is not None and (paired_v is None or maint_v >= paired_v)
                else "paired_switch"
                if paired_v is not None
                else ""
            ),
        })
    return out


def discover_recent_targets() -> list[dict]:
    tags = ("phase6h", "phase6i", "phase6j", "phase6k", "phase6l")
    targets = []
    for folder in sorted((ROOT / "fixtures").iterdir()):
        if not folder.is_dir() or not any(tag in folder.name for tag in tags):
            continue
        for result_path in sorted(folder.glob("*-result.json")):
            flight_id = result_path.name[:-12]
            rec_path = folder / f"{flight_id}_takeoff_to_end.aigprec"
            log_path = folder / f"{flight_id}-flight.jsonl"
            if not rec_path.exists() or not log_path.exists():
                continue
            targets.append({
                "label": flight_id,
                "flight_id": flight_id,
                "recording": str(rec_path.relative_to(ROOT)),
                "log": str(log_path.relative_to(ROOT)),
                "contact_offset_m": 0.162,
            })
    return targets


def write_report(out_dir: Path, summary: dict) -> None:
    lines = [
        "# L1 Shadow Capture Addendum",
        "",
        "Role: QA & MOCK-TUNER.",
        "Scope: recorded video replay only; no real simulator was launched, reset, clicked, or commanded.",
        f"Source commit under test: `{summary['commit']}`.",
        f"Repo HEAD while running: `{summary['repo_head']}`.",
        f"Non-tuning delta from `{SOURCE_REF}`: `{summary['non_tuning_delta_from_source']}`.",
        f"Runtime patches: `{summary['patches'] or []}`.",
        "",
        "## Inputs",
        "",
    ]
    for meta in summary["flight_meta"]:
        lines.append(
            f"- `{meta.get('cohort', 'primary')}` `{meta['flight']}` `{meta['flight_id']}`: "
            f"{meta['frames']} frames, detector fixes {meta['raw_detector_fixes']}, "
            f"tracker fixes {meta['tracker_fixes']}, feature rows {meta['feature_rows']}, "
            f"feature_side rows {meta.get('feature_side_rows', 0)}."
        )
    lines.extend([
        "",
        "## Shadow Capture Bar",
        "",
        "| Sweep | Flight | Commit rows | Ready | Capture rows | Captures <=2.2m | First capture R | First source | TERM rows | TERM/SIDE rows | Min score | Sigma abort rows | Transitions | Held full->side |",
        "|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|",
    ])
    for row in summary["shadow_summary"]:
        lines.append(
            f"| `{row['sweep']}` | `{row['flight']}` | {row['commit_rows']} | "
            f"{row['observer_ready_rows']} | {row['shadow_capture_rows']} | "
            f"{row['captures_by_2p2m']} | {fmt(row['first_capture_range_m'])} | "
            f"`{row['first_capture_source'] or 'n/a'}` | {row['owner_term_rows']} | "
            f"{row['owner_term_side_rows']} | {fmt(row['min_admission_score'])} | "
            f"{row['sigma_induced_abort_rows']} | {row['transition_count']} | "
            f"`{row['held_through_full_to_side']}` |"
        )
    lines.extend(["", "## Transition Log", ""])
    if summary["shadow_transitions"]:
        lines.append("| Sweep | Flight | t | Range | From | To | Paired overlaps | Median delta | Jump grace consumed | Sigma abort after |")
        lines.append("|---|---|---:|---:|---|---|---:|---:|---|---|")
        for row in summary["shadow_transitions"]:
            lines.append(
                f"| `{row['sweep']}` | `{row['flight']}` | {fmt(row['t_rel_s'])} | "
                f"{fmt(row['range_z_m'])} | `{row['from_source']}` | `{row['to_source']}` | "
                f"{row['paired_overlap_count']} | {fmt(row['overlap_delta_median'])} | "
                f"`{row['jump_grace_consumed']}` | `{row['sigma_induced_abort_after']}` |"
            )
    else:
        lines.append("No full->side source transition was observed.")
    lines.extend(["", "## Earned Sigma Row", ""])
    lines.append("| Cohort | Range bin | n | bias_e | sigma_e | paired-switch sigma_v | n_v |")
    lines.append("|---|---|---:|---:|---:|---:|---:|")
    for row in summary["sigma_summary"]:
        if row["range_bin"] != "all" and row["n"] == 0:
            continue
        lines.append(
            f"| `{row['cohort']}` | `{row['range_bin']}` | {row['n']} | "
            f"{fmt(row['bias_e_m'])} | {fmt(row['sigma_e_m'])} | "
            f"{fmt(row['sigma_v_mps'])} | {row['n_v_pairs']} |"
        )
    lines.extend(["", "## Two-Component Sigma-v", ""])
    lines.append("| Cohort | Range bin | paired n | paired-switch sigma_v | maintenance n | maintenance sigma_v | release sigma_v | source |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---|")
    for row in summary["two_component_sigma"]:
        if row["range_bin"] != "all" and row["paired_n"] == 0 and row["maintenance_n"] == 0:
            continue
        lines.append(
            f"| `{row['cohort']}` | `{row['range_bin']}` | {row['paired_n']} | "
            f"{fmt(row['paired_switch_sigma_v_mps'])} | {row['maintenance_n']} | "
            f"{fmt(row['maintenance_sigma_v_mps'])} | "
            f"{fmt(row['release_sigma_v_mps'])} | `{row['release_sigma_v_source']}` |"
        )
    lines.extend(["", "## Maintenance Sigma Strata", ""])
    lines.append("| Cohort | Sweep | Range bin | Anchor age bin | n | median age | median range | maintenance sigma_v |")
    lines.append("|---|---|---|---|---:|---:|---:|---:|")
    for row in summary["maintenance_sigma_summary"]:
        if row["n"] == 0:
            continue
        if row["sweep"] != "all_full_withheld" and row["time_since_anchor_bin"] != "all":
            continue
        lines.append(
            f"| `{row['cohort']}` | `{row['sweep']}` | `{row['range_bin']}` | "
            f"`{row['time_since_anchor_bin']}` | {row['n']} | "
            f"{fmt(row['median_time_since_anchor_s'])} | "
            f"{fmt(row['median_range_z_m'])} | "
            f"{fmt(row['maintenance_sigma_v_mps'])} |"
        )
    lines.extend([
        "",
        "## Verdict",
        "",
        summary["verdict"],
        "",
        "Artifacts: `features.csv`, `observer_timeline.csv`, `shadow_capture_timeline.csv`, "
        "`shadow_capture_summary.csv`, `shadow_source_transitions.csv`, "
        "`observer_source_transitions.csv`, `earned_sigma_pairs.csv`, "
        "`earned_sigma_summary.csv`, `maintenance_sigma_rows.csv`, "
        "`maintenance_sigma_summary.csv`, `two_component_sigma_summary.csv`, "
        "and `summary.json`.",
    ])
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch", action="append", default=[])
    parser.add_argument("--include-f6", action="store_true",
                        help="Include the third live phase6l flight if present.")
    parser.add_argument("--sweep-recent", action="store_true",
                        help="Also replay the 29 recent phase6h-phase6l recordings.")
    args = parser.parse_args(argv)

    assert_mock_safe()
    head, head_short = git_head()
    src_head, src_short, source_delta = source_commit()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ROOT / "tuning" / f"l1-full-addendum-{src_short}-{head_short}-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    params = apply_patches(ParamSet.load(ROOT / "config" / "params_default.json"),
                           args.patch)
    target_groups: list[tuple[str, list[dict]]] = [("primary_f2_f4", list(TARGETS))]
    if args.include_f6:
        target_groups[0][1].append({
            "label": "F6",
            "flight_id": "20260720T071545-cd18c5fb",
            "recording": "fixtures/20260720T071602-phase6l-cohort-3/20260720T071545-cd18c5fb_takeoff_to_end.aigprec",
            "log": "fixtures/20260720T071602-phase6l-cohort-3/20260720T071545-cd18c5fb-flight.jsonl",
            "contact_offset_m": 0.162,
        })
    if args.sweep_recent:
        target_groups.append(("sweep29", discover_recent_targets()))

    all_features = []
    metas = []
    speed_targets = []
    for cohort, targets in target_groups:
        for target in targets:
            rows, meta = run_video_replay(params, target)
            for row in rows:
                row["cohort"] = cohort
            meta["cohort"] = cohort
            all_features.extend(rows)
            speed_targets.append(target)
            metas.append(meta)
    attach_setpoint_speeds(params, all_features, speed_targets)
    for row in all_features:
        row.setdefault("cohort", "primary_f2_f4")
    write_csv(out_dir / "features.csv", all_features)

    sweeps = [
        ShadowOptions("baseline"),
        ShadowOptions("drop_all_0p16s_after_first_below_2m", drop_all_window_s=0.16),
        ShadowOptions("drop_all_0p30s_after_first_below_2m", drop_all_window_s=0.30),
        ShadowOptions("drop_full_below_2p0m", drop_full_below_m=2.0),
        ShadowOptions("drop_full_below_1p5m", drop_full_below_m=1.5),
    ]

    sigma_pairs, sigma_summary = sigma_harvest(all_features)
    write_csv(out_dir / "earned_sigma_pairs.csv", sigma_pairs)
    write_csv(out_dir / "earned_sigma_summary.csv", sigma_summary)
    maintenance_rows, maintenance_summary, two_component_sigma = (
        maintenance_sigma_harvest(all_features, sweeps, sigma_summary)
    )
    write_csv(out_dir / "maintenance_sigma_rows.csv", maintenance_rows)
    write_csv(out_dir / "maintenance_sigma_summary.csv", maintenance_summary)
    write_csv(out_dir / "two_component_sigma_summary.csv", two_component_sigma)

    observer = []
    observer_transitions = []
    for cohort, flight in sorted({(r.get("cohort", ""), r["flight"]) for r in all_features}):
        flight_rows = [r for r in all_features
                       if r.get("cohort", "") == cohort and r["flight"] == flight]
        tl, tr = replay_oracle_from_rows(params, flight_rows,
                                         ReplayOptions("baseline"))
        for row in tl:
            row["cohort"] = cohort
        for row in tr:
            row["cohort"] = cohort
        observer.extend(tl)
        observer_transitions.extend(tr)
    write_csv(out_dir / "observer_timeline.csv", observer)
    write_csv(out_dir / "observer_source_transitions.csv", observer_transitions)

    shadow_rows = []
    shadow_transitions = []
    for opts in sweeps:
        rows, transitions = replay_shadow_capture(params, all_features, opts)
        shadow_rows.extend(rows)
        shadow_transitions.extend(transitions)
    write_csv(out_dir / "shadow_capture_timeline.csv", shadow_rows)
    write_csv(out_dir / "shadow_source_transitions.csv", shadow_transitions)
    shadow_summary = summarize_shadow(shadow_rows, shadow_transitions)
    write_csv(out_dir / "shadow_capture_summary.csv", shadow_summary)

    successes = [r for r in shadow_summary
                 if r["shadow_capture_rows"] > 0 and r["held_through_full_to_side"]]
    if successes:
        verdict = (
            "PASS: at least one deep-penetration replay produced observer_ready, "
            "admission_score <= 0.30, shadow owner TERM, POSITION phase, valid "
            "source provenance, and held through a full->side transition without "
            "a sigma-induced abort."
        )
    else:
        verdict = (
            "NO-PASS: shadow capture or full->side hold was not observed in this "
            "recorded-video replay set. Treat this as a liveness gap, not a real "
            "sim run."
        )

    summary = {
        "commit": src_head,
        "repo_head": head,
        "non_tuning_delta_from_source": source_delta,
        "patches": args.patch,
        "flight_meta": metas,
        "observer_transitions": observer_transitions,
        "sigma_summary": sigma_summary,
        "maintenance_sigma_summary": maintenance_summary,
        "two_component_sigma": two_component_sigma,
        "shadow_summary": shadow_summary,
        "shadow_transitions": shadow_transitions,
        "verdict": verdict,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(out_dir, summary)
    print(f"[l1-shadow] report={out_dir / 'summary.md'}", flush=True)
    print(f"[l1-shadow] verdict={verdict}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
