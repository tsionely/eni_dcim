"""Machine fixtures for the post-REG2 Contract-B generator.

These fixtures are deliberately synthetic and replay-free. They prove the
registered Step-E generator mechanics before any Step-F intervention artifact
is allowed to exist.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import statistics
import subprocess
import sys
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tuning.post_reg2_contract_b_generator import (
    CALIBRATION_DIGESTS,
    ContractBModel,
    StartupContractError,
    calibration_artifact_reconstructed_v_raw,
    apply_contract_b_response,
    canonical_residual_slice_sha,
    evaluate_cut_records,
    fit_cut,
    points_for_line,
    resolve_decision,
    runtime_twin_rate_anchor_v_raw,
    sensitivity_profile_rows,
    split_mixed_owner_rows,
    startup_contract,
)


class FixtureFailure(AssertionError):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise FixtureFailure(message)


def branch(summary: dict[str, object]) -> str:
    return str(summary["decision"]["branch"])


def line(slope: float, intercept: float = 0.0) -> list[dict[str, float]]:
    return points_for_line(slope=slope, intercept=intercept)


def rec(
    approach_id: str,
    cut_id: str,
    before_slope: float,
    after_slope: float | None = None,
    *,
    after_exit_reason: str = "",
    model_activity_rms_mps: float = 0.2,
) -> dict[str, object]:
    row: dict[str, object] = {
        "approach_id": approach_id,
        "cut_id": cut_id,
        "before_points": line(before_slope),
        "model_activity_rms_mps": model_activity_rms_mps,
    }
    if after_exit_reason:
        row["after_exit_reason"] = after_exit_reason
    else:
        row["after_points"] = line(before_slope if after_slope is None else after_slope)
    return row


def synthetic_completed_reg2_text(repo: Path, *, status: str = "CALIBRATED") -> str:
    text = (repo / "docs/criteria/legacy_response_model_registration.md").read_text(encoding="utf-8")
    calibration_dir = repo / "tuning/a091-response-model-calibration-0b60e91-20260721T061627Z"
    digest_lines = []
    for name in CALIBRATION_DIGESTS:
        actual = hashlib.sha256((calibration_dir / name).read_bytes()).hexdigest()
        digest_lines.append(f"        {name}\n          {actual}")
    block = "\n".join([
        "## 4. NUMERIC BLOCK (SYNTHETIC COMPLETE REG-2 FOR STARTUP FIXTURE ONLY)",
        "",
        "    g    = 0.50",
        "    tau  = 0.60 s",
        "    L    = 0 ticks",
        f"    calibration_status          = {status}",
        "    calibration_artifact_path =",
        "        tuning/a091-response-model-calibration-0b60e91-20260721T061627Z/",
        "    calibration_artifact_sha256 (per file):",
        *digest_lines,
        "",
    ])
    return re.sub(r"## 4\. NUMERIC BLOCK.*?(?=\n## 5\.)", block, text, count=1, flags=re.S)


def fixture_startup_current_reg2_pending_guard(repo: Path) -> None:
    touched = {"checkpoint": False, "result": False}

    def checkpoint_loader() -> list[dict[str, object]]:
        touched["checkpoint"] = True
        return []

    def result_dir_factory() -> Path:
        touched["result"] = True
        return repo / "tuning" / "SHOULD_NOT_BE_CREATED"

    try:
        startup_contract(repo, checkpoint_loader=checkpoint_loader, result_dir_factory=result_dir_factory, touch_checkpoint=True)
    except StartupContractError as exc:
        expect(exc.code == "REG2_CALIBRATION_STATUS_PENDING", f"unexpected startup error code {exc.code}")
        expect(not touched["checkpoint"], "checkpoint loader ran after pending REG-2")
        expect(not touched["result"], "result directory factory ran after pending REG-2")
        return
    raise FixtureFailure("current pending REG-2 unexpectedly passed")


def fixture_startup_completed_reg2_override(repo: Path) -> None:
    completed = synthetic_completed_reg2_text(repo, status="CALIBRATED")
    touched = {"checkpoint": False, "result": False}

    def checkpoint_loader() -> list[dict[str, object]]:
        touched["checkpoint"] = True
        return [{"checkpoint": "synthetic-23-approach-placeholder"}]

    def result_dir_factory() -> Path:
        touched["result"] = True
        return repo / "tuning" / "virtual-result-dir-not-created"

    audit = startup_contract(
        repo,
        reg2_text_override=completed,
        checkpoint_loader=checkpoint_loader,
        result_dir_factory=result_dir_factory,
        touch_checkpoint=True,
    )
    expect(audit.model.g == 0.50, "REG-2 g was not parsed as 0.50")
    expect(audit.model.tau_s == 0.60, "REG-2 tau was not parsed as 0.60")
    expect(audit.model.lag_ticks == 0, "REG-2 L was not parsed as 0")
    expect(touched["checkpoint"], "completed REG-2 happy path did not touch checkpoint")
    expect(touched["result"], "completed REG-2 happy path did not reach result factory")
    expect(audit.calibration_key_count == 13, "calibration key count drifted")
    expect(audit.sentinel_key_count == 31, "sentinel key count drifted")
    expect(audit.calibration_sentinel_overlap == 0, "calibration/sentinel key sets overlap")

def fixture_startup_incomplete_reg2_fails_before_checkpoint(repo: Path) -> None:
    bad_text = synthetic_completed_reg2_text(repo, status="NOT_IDENTIFIED")
    touched = {"checkpoint": False, "result": False}

    def checkpoint_loader() -> list[dict[str, object]]:
        touched["checkpoint"] = True
        return []

    def result_dir_factory() -> Path:
        touched["result"] = True
        return repo / "tuning" / "SHOULD_NOT_BE_CREATED"

    try:
        startup_contract(
            repo,
            reg2_text_override=bad_text,
            checkpoint_loader=checkpoint_loader,
            result_dir_factory=result_dir_factory,
            touch_checkpoint=True,
        )
    except StartupContractError as exc:
        expect(exc.code == "REG2_CALIBRATION_STATUS_NOT_IDENTIFIED", f"unexpected startup error code {exc.code}")
        expect(not touched["checkpoint"], "checkpoint loader ran after NOT_IDENTIFIED REG-2")
        expect(not touched["result"], "result directory factory ran after NOT_IDENTIFIED REG-2")
        expect(not exc.checkpoint_touched, "exception reports checkpoint_touched=True")
        return
    raise FixtureFailure("NOT_IDENTIFIED REG-2 did not fail")

def fixture_boundary_profile_rows() -> None:
    rows = sensitivity_profile_rows(ContractBModel(g=0.5, tau_s=0.6, lag_ticks=0))
    expect(len(rows) == 4, "sensitivity table does not carry four box corners")
    expect({r["g_min_face"] for r in rows} == {"OPEN", "CLOSED_PROFILE_EDGE"}, "g-min OPEN face not labeled")
    expect({r["tau_max_face"] for r in rows} == {"OPEN", "CLOSED_PROFILE_EDGE"}, "tau-max OPEN face not labeled")


def fixture_era_gating() -> None:
    rows = apply_contract_b_response([
        {
            "row_key": "off-era",
            "era": "phase6",
            "owner_state": "legacy",
            "age_s": 2.0,
            "v_ref_up_mps": 0.2,
            "v_latch_true_mps": 0.0,
            "feed_forward_delta_mps": 0.0,
            "v_ref_oracle_mps": 0.1,
        },
        {
            "row_key": "phase5c",
            "era": "phase5c",
            "owner_state": "legacy",
            "age_s": 2.0,
            "v_ref_up_mps": 0.0,
            "v_latch_true_mps": 0.0,
            "feed_forward_delta_mps": 0.0,
            "v_ref_oracle_mps": 0.0,
        },
    ], ContractBModel(g=0.5, tau_s=0.6, lag_ticks=0))
    expect(rows[0]["input_status"] == "OFF_SUPPORT", "non-phase5c row was not typed OFF_SUPPORT")
    expect(rows[0]["exit_reason"] == "PENDING_TRANSPORT_PROOF", "non-phase5c row lost transport proof reason")
    expect(rows[1]["input_status"] == "VALID", "phase5c legacy row should be valid")


def fixture_a_missing_large_behind_small_holds() -> None:
    summary = evaluate_cut_records([
        rec("A", "large_missing", 0.70, after_exit_reason="ABSENT_INPUT"),
        rec("A", "small_survives", 0.10, 0.10),
    ])
    expect(branch(summary) == "HOLD_INCOMPLETE_INTERVENTION_SUPPORT", "fixture a did not HOLD")
    expect(summary["M_RESOLUTION"] == 1, "fixture a did not count missing baseline-large cut")


def fixture_b_missing_after_support_baseline_small_holds_harm() -> None:
    summary = evaluate_cut_records([
        rec("BIG", "large_survives", 0.70, 0.70),
        rec("SMALL", "small_missing", 0.10, after_exit_reason="ABSENT_INPUT"),
    ])
    expect(branch(summary) == "HOLD_INCOMPLETE_INTERVENTION_SUPPORT", "fixture b did not HOLD")
    expect(summary["M_HARM"] == 1, "fixture b did not count M_HARM")


def fixture_c_newly_large_refuted_or_harmful() -> None:
    summary = evaluate_cut_records([
        rec("BASE", "large_stays", 0.70, 0.70),
        rec("NEW", "small_to_large", 0.10, 0.70),
    ])
    expect(branch(summary) == "REFUTED_OR_HARMFUL_INTERVENTION", "fixture c did not enter harmful branch")
    expect(summary["N"] == ["NEW"], "fixture c did not publish newly-large approach")
    expect(summary["C_B"] == ["BASE"], "fixture c C_B mismatch")
    expect(summary["C_A"] == ["BASE", "NEW"], "fixture c C_A mismatch")
    expect(summary["C_P"] == ["BASE", "NEW"], "fixture c C_P mismatch")


def fixture_d_zero_baseline_not_applicable() -> None:
    summary = evaluate_cut_records([rec("SMALL", "small", 0.10, 0.10)])
    expect(branch(summary) == "NO_REGISTERED_REMAINDER_TO_EXPLAIN", "fixture d did not return NOT_APPLICABLE branch")
    expect(summary["branch_order"] == 4, "fixture d B=0 complete support branch order mismatch")

    missing = evaluate_cut_records([rec("SMALL_MISS", "small_missing", 0.10, after_exit_reason="ABSENT_INPUT")])
    expect(branch(missing) == "HOLD_INCOMPLETE_INTERVENTION_SUPPORT", "fixture d M_HARM did not precede B=0")
    expect(missing["branch_order"] == 2, "fixture d M_HARM precedence order mismatch")

    newly_large = evaluate_cut_records([rec("NEW_ONLY", "small_to_large", 0.10, 0.70)])
    expect(branch(newly_large) == "REFUTED_OR_HARMFUL_INTERVENTION", "fixture d N did not precede B=0")
    expect(newly_large["branch_order"] == 3, "fixture d N precedence order mismatch")


def fixture_e_one_quiet_breach_holds_quiet() -> None:
    summary = evaluate_cut_records([rec("Q1", "quiet_large", 0.70, 0.70, model_activity_rms_mps=0.01)])
    expect(branch(summary) == "HOLD_INCONCLUSIVE_QUIET_BREACH", "fixture e did not HOLD_QUIET")
    expect(summary["Q_ids"] == ["Q1"], "fixture e quiet ID mismatch")


def fixture_f_two_quiet_breaches_refute() -> None:
    summary = evaluate_cut_records([
        rec("Q1", "quiet_large", 0.70, 0.70, model_activity_rms_mps=0.01),
        rec("Q2", "quiet_large", 0.80, 0.80, model_activity_rms_mps=0.01),
    ])
    expect(branch(summary) == "REFUTED", "fixture f did not REFUTE on K=2 quiet breaches")


def fixture_g_zero_vs_absent_input() -> None:
    rows = apply_contract_b_response([
        {
            "row_key": "explicit-zero",
            "era": "phase5c",
            "owner_state": "legacy",
            "age_s": 2.0,
            "v_ref_up_mps": 0.0,
            "v_latch_true_mps": 0.0,
            "feed_forward_delta_mps": 0.0,
            "v_ref_oracle_mps": 0.0,
        },
        {
            "row_key": "absent",
            "era": "phase5c",
            "owner_state": "legacy",
            "age_s": 2.0,
            "v_latch_true_mps": 0.0,
            "feed_forward_delta_mps": 0.0,
            "v_ref_oracle_mps": 0.0,
        },
    ], ContractBModel(g=0.5, tau_s=0.6, lag_ticks=0))
    by_key = {str(r["row_key"]): r for r in rows}
    expect(by_key["explicit-zero"]["input_status"] == "VALID", "explicit zero was not valid input")
    expect(by_key["explicit-zero"]["correction_term_mps"] == 0.0, "explicit zero was not preserved as zero correction")
    expect(by_key["absent"]["input_status"] == "OFF_SUPPORT", "absent input did not become OFF_SUPPORT")
    expect(by_key["absent"]["exit_reason"] == "ABSENT_INPUT", "absent input did not carry ABSENT_INPUT")
    expect("r_v_corrected_mps" not in by_key["absent"], "absent input emitted an admissible residual field")


def fixture_h_a091_term_noop_byte_identical() -> None:
    source = []
    for i, age in enumerate([0.0, 0.06, 0.16, 0.24, 0.32]):
        before = -0.44 + 0.03 * age
        source.append({
            "row_key": f"A091_TERM_{i:02d}",
            "era": "phase5c",
            "owner_state": "physical_TERM_episode_A091",
            "age_s": age,
            "v_ref_up_mps": -0.5,
            "v_latch_true_mps": 0.0,
            "feed_forward_delta_mps": 0.0,
            "v_ref_oracle_mps": before,
            "r_v_before_mps": before,
        })
    rows = apply_contract_b_response(source, ContractBModel(g=0.5, tau_s=0.6, lag_ticks=0))
    expect(all(r["owner_state"] == "physical_TERM_episode_A091" for r in rows), "A091 owner provenance drifted")
    expect(all(r["correction_term_mps"] == 0.0 for r in rows), "A091 TERM-owned correction was nonzero")
    expect(all(r["r_v_corrected_mps"] == r["r_v_before_mps"] for r in rows), "A091 before/after residuals changed")
    before_sha = canonical_residual_slice_sha(rows, "r_v_before_mps")
    after_sha = canonical_residual_slice_sha(rows, "r_v_corrected_mps")
    expect(before_sha == after_sha, "A091 no-op residual slice SHA changed")


def fixture_i_mixed_owner_split() -> None:
    rows = [
        {"row_key": "m0", "owner_state": "legacy"},
        {"row_key": "m1", "owner_state": "legacy"},
        {"row_key": "m2", "owner_state": "TERM"},
        {"row_key": "m3", "owner_state": "TERM"},
    ]
    split = split_mixed_owner_rows(rows)
    expect([r["ownership_segment_index"] for r in split] == [1, 1, 2, 2], "mixed-owner rows were not split by segment")
    expect(all(r["split_exit_reason"] == "OWNERSHIP_SPLIT" for r in split), "mixed-owner split did not publish exit reason")


def fixture_j_all_residual_admissibility_branches() -> None:
    cases = [
        ("INVALID_INPUT", {"input_validity_ok": False, "B": 1}),
        ("NO_REGISTERED_REMAINDER_TO_EXPLAIN", {"input_validity_ok": True, "B": 0}),
        ("HOLD_INCOMPLETE_INTERVENTION_SUPPORT", {"input_validity_ok": True, "B": 1, "M_RESOLUTION": 1}),
        ("REFUTED_OR_HARMFUL_INTERVENTION", {"input_validity_ok": True, "B": 1, "N": ["N1"]}),
        ("REFUTED", {"input_validity_ok": True, "B": 2, "Q_ids": ["Q1", "Q2"]}),
        ("HOLD_INCONCLUSIVE_QUIET_BREACH", {"input_validity_ok": True, "B": 1, "Q_ids": ["Q1"]}),
        ("CONFIRMED_SUFFICIENT_FOR_EVALUATOR", {"input_validity_ok": True, "B": 2, "R": ["A"], "S_B": ["A", "B"], "S_A": ["B"]}),
        ("CONTRIBUTORY_NOT_SUFFICIENT", {"input_validity_ok": True, "B": 3, "R": ["A"], "S_B": ["A", "B", "C"], "S_A": ["B", "C"]}),
        ("REFUTED_AS_REGISTERED_REMAINDER_EXPLANATION", {"input_validity_ok": True, "B": 1, "R": [], "S_B": ["A"], "S_A": ["A"]}),
    ]
    final_branches = {
        "INVALID_INPUT",
        "NO_REGISTERED_REMAINDER_TO_EXPLAIN",
        "HOLD_INCOMPLETE_INTERVENTION_SUPPORT",
        "CONFIRMED_SUFFICIENT_FOR_EVALUATOR",
    }
    admissibilities = set()
    for expected, summary in cases:
        result = resolve_decision(summary)
        expect(result["branch"] == expected, f"branch {expected} resolved as {result['branch']}")
        expected_finality = "FINAL" if expected in final_branches else "INTERIM_PENDING_RESTART"
        expect(result["verdict_finality"] == expected_finality, f"finality for {expected} was {result['verdict_finality']}")
        admissibilities.add(str(result["residual_admissibility"]))
    expect("CANDIDATE_EVALUATOR_CORRECTED_STATISTICAL_INPUT" in admissibilities, "release-candidate residual branch missing")
    expect("DIAGNOSTIC_ONLY" in admissibilities, "diagnostic residual branch missing")
    expect("INADMISSIBLE" in admissibilities, "inadmissible residual branch missing")
    expect("NO_RESIDUAL_CLAIM" in admissibilities, "no-claim residual branch missing")


def fixture_k_theil_sen_ols_boundary_disagreement_flagged() -> None:
    points = [
        {"age_s": 0.0, "r_v_mps": 0.0046},
        {"age_s": 0.03, "r_v_mps": -0.1436},
        {"age_s": 0.08, "r_v_mps": -0.6807},
        {"age_s": 0.16, "r_v_mps": -0.8604},
        {"age_s": 0.25, "r_v_mps": 0.0242},
        {"age_s": 0.34, "r_v_mps": 0.0180},
        {"age_s": 0.50, "r_v_mps": -0.0446},
    ]
    fit = fit_cut(points)
    expect(fit["estimable"], "boundary-disagreement points were not estimable")
    expect(fit["large_theil_sen"] is False, "Theil-Sen should stay below boundary")
    expect(fit["large_ols"] is True, "OLS should cross boundary")
    expect(fit["theil_sen_ols_boundary_disagreement"] is True, "boundary disagreement was not flagged")


def fixture_l_precedence_earlier_branch_wins() -> None:
    result = resolve_decision({
        "input_validity_ok": True,
        "B": 1,
        "M_RESOLUTION": 1,
        "N": ["N1"],
        "Q_ids": ["Q1", "Q2"],
    })
    expect(result["branch"] == "HOLD_INCOMPLETE_INTERVENTION_SUPPORT", "precedence did not select earlier HOLD branch")
    expect(result["branch_order"] == 2, "precedence branch order mismatch")


def fixed_window_impostor_rate(samples: list[dict[str, object]], anchor_ts_s: float, window_s: float = 0.50) -> float:
    pts: list[tuple[float, float]] = []
    start_s = anchor_ts_s - window_s
    for row in samples:
        if not bool(row.get("certified_full", True)):
            continue
        ts = float(row["ts_s"])
        if start_s <= ts <= anchor_ts_s:
            pts.append((ts, float(row["e_meas_m"])))
    pts.sort()
    deduped: list[tuple[float, float]] = []
    for ts, e_meas in pts:
        if deduped and ts <= deduped[-1][0]:
            continue
        deduped.append((ts, e_meas))
    slopes = [
        (e2 - e1) / (t2 - t1)
        for i, (t1, e1) in enumerate(deduped)
        for t2, e2 in deduped[i + 1:]
        if t2 > t1
    ]
    if not slopes:
        raise FixtureFailure("fixed-window impostor fixture had no slopes")
    return -float(statistics.median(slopes))


def piecewise_e(ts: float, *, break_s: float, e0: float, slope_before: float, slope_after: float) -> float:
    if ts <= break_s:
        return e0 + slope_before * ts
    e_break = e0 + slope_before * break_s
    return e_break + slope_after * (ts - break_s)


def assert_runtime_reconstruction_case(name: str, samples: list[dict[str, object]], anchor_ts_s: float, *, expect_fixed_window_diff: bool = False) -> None:
    runtime_rate = runtime_twin_rate_anchor_v_raw(samples, anchor_ts_s)
    calibration_rate = calibration_artifact_reconstructed_v_raw(samples, anchor_ts_s)
    expect(runtime_rate == calibration_rate, f"{name}: real oracle and calibration reconstruction differ")
    if expect_fixed_window_diff:
        impostor = fixed_window_impostor_rate(samples, anchor_ts_s)
        expect(abs(calibration_rate - impostor) > 1e-3, f"{name}: fixed-window impostor was not exposed")


def fixture_m_runtime_twin_equivalence() -> None:
    dense: list[dict[str, object]] = []
    for i in range(25):
        ts = i * 0.02
        dense.append({
            "row_key": f"full_{i:03d}",
            "ts_s": ts,
            "e_meas_m": piecewise_e(ts, break_s=0.24, e0=1.75, slope_before=-0.05, slope_after=-0.35),
            "certified_full": True,
        })
    assert_runtime_reconstruction_case("dense-last-12", dense, 0.48, expect_fixed_window_diff=True)

    gapped: list[dict[str, object]] = []
    for i, ts in enumerate([0.18, 0.20, 0.22, 0.24, 0.26, 0.28, 0.30, 0.32, 0.34]):
        gapped.append({
            "row_key": f"gap_old_{i:03d}",
            "ts_s": ts,
            "e_meas_m": 3.0 - 0.65 * ts,
            "certified_full": True,
        })
    for i, ts in enumerate([0.50, 0.52, 0.54, 0.56, 0.58, 0.60, 0.62, 0.64, 0.66, 0.68]):
        gapped.append({
            "row_key": f"gap_new_{i:03d}",
            "ts_s": ts,
            "e_meas_m": 1.2 - 0.12 * (ts - 0.50),
            "certified_full": True,
        })
    assert_runtime_reconstruction_case("gapped-fresh-tail", gapped, 0.68, expect_fixed_window_diff=True)

    duplicate: list[dict[str, object]] = []
    for i in range(18):
        ts = i * 0.02
        duplicate.append({
            "row_key": f"dup_{i:03d}",
            "ts_s": ts,
            "e_meas_m": 1.5 - 0.22 * ts,
            "certified_full": True,
        })
        if i == 10:
            duplicate.append({
                "row_key": "dup_010_rebroadcast",
                "ts_s": ts,
                "e_meas_m": 99.0,
                "certified_full": True,
            })
    assert_runtime_reconstruction_case("duplicate-timestamps", duplicate, 0.34)


def run(repo: Path) -> int:
    fixtures: list[tuple[str, Callable[[], None]]] = [
        ("startup_current_reg2_pending_guard", lambda: fixture_startup_current_reg2_pending_guard(repo)),
        ("startup_completed_reg2_override", lambda: fixture_startup_completed_reg2_override(repo)),
        ("startup_incomplete_reg2_fails_before_checkpoint", lambda: fixture_startup_incomplete_reg2_fails_before_checkpoint(repo)),
        ("boundary_profile_rows", fixture_boundary_profile_rows),
        ("era_gating", fixture_era_gating),
        ("a_missing_large_behind_small_holds", fixture_a_missing_large_behind_small_holds),
        ("b_missing_after_support_baseline_small_holds_harm", fixture_b_missing_after_support_baseline_small_holds_harm),
        ("c_newly_large_refuted_or_harmful", fixture_c_newly_large_refuted_or_harmful),
        ("d_zero_baseline_not_applicable", fixture_d_zero_baseline_not_applicable),
        ("e_one_quiet_breach_holds_quiet", fixture_e_one_quiet_breach_holds_quiet),
        ("f_two_quiet_breaches_refute", fixture_f_two_quiet_breaches_refute),
        ("g_zero_vs_absent_input", fixture_g_zero_vs_absent_input),
        ("h_a091_term_noop_byte_identical", fixture_h_a091_term_noop_byte_identical),
        ("i_mixed_owner_split", fixture_i_mixed_owner_split),
        ("j_all_residual_admissibility_branches", fixture_j_all_residual_admissibility_branches),
        ("k_theil_sen_ols_boundary_disagreement_flagged", fixture_k_theil_sen_ols_boundary_disagreement_flagged),
        ("l_precedence_earlier_branch_wins", fixture_l_precedence_earlier_branch_wins),
        ("m_runtime_twin_equivalence", fixture_m_runtime_twin_equivalence),
    ]
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    sim_lock = Path(r"C:\Temp\eni_dcim_sim.lock").exists()
    print("POST-REG2 GENERATOR FIXTURES")
    print(f"repo={repo}")
    print(f"head={head}")
    print(f"sim_lock={sim_lock}")
    print("scope=DIAGNOSTIC replay/csv only; no FlightSim/DCGame; no intervention artifacts")
    failures: list[tuple[str, str]] = []
    for name, fn in fixtures:
        try:
            fn()
        except Exception as exc:  # fixture runner should report every failed item.
            failures.append((name, f"{type(exc).__name__}: {exc}"))
            print(f"FAIL {name}: {type(exc).__name__}: {exc}")
        else:
            print(f"PASS {name}")
    print(f"SUMMARY passed={len(fixtures) - len(failures)} failed={len(failures)} total={len(fixtures)}")
    if failures:
        print("FAILURES_JSON=" + json.dumps(failures, sort_keys=True))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run(Path.cwd()))


