"""L1 shadow-capture addendum replay for commit 04baee1.

QA & MOCK-TUNER scope: recorded video replay only. This script reuses the
fresh-video perception replay harness and then runs the current terminal
observer + shadow ownership/admission logic over those feature rows. It writes
only under tuning/.
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


def source_commit() -> tuple[str, str, list[str]]:
    source = subprocess.check_output(
        ["git", "rev-parse", "04baee1"],
        cwd=ROOT,
        text=True,
    ).strip()
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", "04baee1..HEAD", "--", ".", ":!tuning"],
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
    deltas = [float(d) for t, d in getattr(oracle, "_overlap_deltas", [])
              if ts_s - float(t) <= 0.5]
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
        e_meas = fnum(row.get("e_meas")) if fed else None
        source_valid = (
            fed
            and e_meas is not None
            and row.get("cert_status") == "certified"
            and row.get("feature_mode") in ("FULL_QUAD", "SIDE_PAIR")
        )
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

        metrics = admission_metrics(params, oracle, row)
        admission_score = fnum(metrics.get("admission_score"))
        first_capture_ok = (
            source_valid
            and oracle.ready()
            and oracle.active_source == "FULL_QUAD"
            and admission_score is not None
            and admission_score <= corridor
        )
        maintain_ok = arbiter.owner == TERM_OWNER and source_valid
        capture_certified = first_capture_ok or maintain_ok
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


def write_report(out_dir: Path, summary: dict) -> None:
    lines = [
        "# L1 Shadow Capture Addendum",
        "",
        "Role: QA & MOCK-TUNER.",
        "Scope: recorded video replay only; no real simulator was launched, reset, clicked, or commanded.",
        f"Source commit under test: `{summary['commit']}`.",
        f"Repo HEAD while running: `{summary['repo_head']}`.",
        f"Non-tuning delta from `04baee1`: `{summary['non_tuning_delta_from_04baee1']}`.",
        f"Runtime patches: `{summary['patches'] or []}`.",
        "",
        "## Inputs",
        "",
    ]
    for meta in summary["flight_meta"]:
        lines.append(
            f"- `{meta['flight']}` `{meta['flight_id']}`: "
            f"{meta['frames']} frames, detector fixes {meta['raw_detector_fixes']}, "
            f"tracker fixes {meta['tracker_fixes']}, feature rows {meta['feature_rows']}."
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
    lines.extend([
        "",
        "## Verdict",
        "",
        summary["verdict"],
        "",
        "Artifacts: `features.csv`, `observer_timeline.csv`, `shadow_capture_timeline.csv`, "
        "`shadow_capture_summary.csv`, `shadow_source_transitions.csv`, "
        "`observer_source_transitions.csv`, and `summary.json`.",
    ])
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch", action="append", default=[])
    parser.add_argument("--include-f6", action="store_true",
                        help="Include the third live phase6l flight if present.")
    args = parser.parse_args(argv)

    assert_mock_safe()
    head, head_short = git_head()
    src_head, src_short, source_delta = source_commit()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ROOT / "tuning" / f"l1-shadow-capture-{src_short}-{head_short}-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    params = apply_patches(ParamSet.load(ROOT / "config" / "params_default.json"),
                           args.patch)
    targets = list(TARGETS)
    if args.include_f6:
        targets.append({
            "label": "F6",
            "flight_id": "20260720T071545-cd18c5fb",
            "recording": "fixtures/20260720T071602-phase6l-cohort-3/20260720T071545-cd18c5fb_takeoff_to_end.aigprec",
            "log": "fixtures/20260720T071602-phase6l-cohort-3/20260720T071545-cd18c5fb-flight.jsonl",
            "contact_offset_m": 0.162,
        })

    all_features = []
    metas = []
    for target in targets:
        rows, meta = run_video_replay(params, target)
        all_features.extend(rows)
        metas.append(meta)
    attach_setpoint_speeds(params, all_features, targets)
    write_csv(out_dir / "features.csv", all_features)

    observer = []
    observer_transitions = []
    for flight in sorted({r["flight"] for r in all_features}):
        flight_rows = [r for r in all_features if r["flight"] == flight]
        tl, tr = replay_oracle_from_rows(params, flight_rows,
                                         ReplayOptions("baseline"))
        observer.extend(tl)
        observer_transitions.extend(tr)
    write_csv(out_dir / "observer_timeline.csv", observer)
    write_csv(out_dir / "observer_source_transitions.csv", observer_transitions)

    sweeps = [
        ShadowOptions("baseline"),
        ShadowOptions("drop_all_0p16s_after_first_below_2m", drop_all_window_s=0.16),
        ShadowOptions("drop_all_0p30s_after_first_below_2m", drop_all_window_s=0.30),
        ShadowOptions("drop_full_below_2p0m", drop_full_below_m=2.0),
        ShadowOptions("drop_full_below_1p5m", drop_full_below_m=1.5),
    ]
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
        "non_tuning_delta_from_04baee1": source_delta,
        "patches": args.patch,
        "flight_meta": metas,
        "observer_transitions": observer_transitions,
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
