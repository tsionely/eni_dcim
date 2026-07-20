"""RESPONSE53 sequencing closure-read report layer.

CSV-only. This script does not run the simulator and does not recompute
bootstrap/LOAO arithmetic. It reads the checkpointed A-G diagnostic outputs
and regenerates the closure-read report layer after the unambiguous
RESPONSE53 criterion lineage.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tuning"))

from run_l1_perception_replay import assert_mock_safe  # noqa: E402

SOURCE_DIR = ROOT / "tuning" / "ordered-round-A-G-DIAGNOSTIC-de19d88-20260720T220957Z"
OUT_PREFIX = "response53-closure-read-DIAGNOSTIC"
SEQUENCING_FLOOR = "181f41f"
RESPONSE53_COMMIT = "02b32cc"
FIXTURE_LEVEL_SCOPE = (
    "PASS at 1/1 is a FIXTURE-LEVEL pass (one physical approach, "
    "four correlated variants), not population evidence."
)
COPIED_CHECKPOINT_FILES = [
    "02_shadow_old_vs_new_release_fit_by_set.csv",
    "02_shadow_b0_exact_maxima.csv",
    "02_shadow_legacy_discovery_appendix_5_listed_4_analyzable.csv",
    "02_shadow_old_vs_new_loao_by_set.csv",
    "02_shadow_old_vs_new_balanced_coverage_by_set.csv",
    "01_wrong_sign_definition_scorecard.csv",
    "01_wrong_sign_approach_level_rescore.csv",
]
DERIVED_EVENT_SUPPORT_FILES = [
    "01_wrong_sign_mask_accounting.csv",
    "01_wrong_sign_approach_level_rescore.csv",
    "01_wrong_sign_definition_scorecard.csv",
]


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def is_ancestor(older: str, newer: str) -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", older, newer],
        cwd=ROOT,
        capture_output=True,
    ).returncode == 0


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def committed_digest(rel_path: str) -> str:
    blob = subprocess.check_output(["git", "show", f"HEAD:{rel_path}"], cwd=ROOT)
    return hashlib.sha256(blob).hexdigest()


def write_checkpoint_input_manifest(source_dir: Path, out_dir: Path) -> tuple[Path, str]:
    rel_files = []
    for name in [*COPIED_CHECKPOINT_FILES, *DERIVED_EVENT_SUPPORT_FILES]:
        rel = str((source_dir / name).relative_to(ROOT)).replace("\\", "/")
        if rel not in rel_files:
            rel_files.append(rel)
    rows = [{"path": rel, "sha256": committed_digest(rel)} for rel in rel_files]
    path = out_dir / "checkpoint_input_manifest.json"
    path.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path, digest(path)


def add_report_metadata(rows: list[dict[str, str]], head: str, source_dir: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        rec: dict[str, Any] = {
            "report_layer_generator_commit": head,
            "sequencing_floor_commit": git("rev-parse", SEQUENCING_FLOOR),
            "response53_commit": git("rev-parse", RESPONSE53_COMMIT),
            "generator_postdates_181f41f": is_ancestor(SEQUENCING_FLOOR, head),
            "source_checkpoint_dir": str(source_dir.relative_to(ROOT)).replace("\\", "/"),
        }
        rec.update(row)
        out.append(rec)
    return out


def summarize_event_support(mask_rows: list[dict[str, str]],
                            approach_rows: list[dict[str, str]],
                            score_rows: list[dict[str, str]],
                            head: str,
                            source_dir: Path) -> list[dict[str, Any]]:
    by_layer = {r["layer"]: r for r in mask_rows}
    verdict = approach_rows[0] if approach_rows else {}
    registered = [
        r for r in score_rows
        if r.get("definition") == "registered_needed_correction_event_support"
    ]
    return [{
        "report_layer_generator_commit": head,
        "sequencing_floor_commit": git("rev-parse", SEQUENCING_FLOOR),
        "response53_commit": git("rev-parse", RESPONSE53_COMMIT),
        "generator_postdates_181f41f": is_ancestor(SEQUENCING_FLOOR, head),
        "source_checkpoint_dir": str(source_dir.relative_to(ROOT)).replace("\\", "/"),
        "physical_approaches": 1,
        "correlated_variants": 4,
        "trace_rows": by_layer["traceability_term_side_with_new_command"]["rows"],
        "command_event_support": by_layer["command_event_support"]["rows"],
        "sign_evaluable_events": by_layer["sign_evaluable_events"]["rows"],
        "zero_on_support_events": by_layer["zero_neutral_on_support"]["rows"],
        "new_excess_wrong_sign_events": verdict.get("new_excess_wrong_sign_events", ""),
        "wrong_sign_clause_result": verdict.get("wrong_sign_clause_result", ""),
        "registered_old_violations": next((r["violations"] for r in registered if r.get("path") == "old_policy_forecast"), ""),
        "registered_new_violations": next((r["violations"] for r in registered if r.get("path") == "new_shadow_forecast"), ""),
        "verdict_scope_language": FIXTURE_LEVEL_SCOPE,
        "population_claim": "none",
    }]


def run(args: argparse.Namespace) -> Path:
    assert_mock_safe()
    head = git("rev-parse", "HEAD")
    short = head[:7]
    if not is_ancestor(SEQUENCING_FLOOR, head):
        raise SystemExit(f"generator HEAD {head} does not postdate {SEQUENCING_FLOOR}")

    source = args.source_dir.resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ROOT / "tuning" / f"{OUT_PREFIX}-{short}-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=False)
    input_manifest_path, input_manifest_sha = write_checkpoint_input_manifest(source, out_dir)

    copied = [
        ("closure_read_shadow_fit_by_set.csv", "02_shadow_old_vs_new_release_fit_by_set.csv"),
        ("closure_read_shadow_b0_exact_maxima.csv", "02_shadow_b0_exact_maxima.csv"),
        ("closure_read_legacy_appendix.csv", "02_shadow_legacy_discovery_appendix_5_listed_4_analyzable.csv"),
        ("closure_read_loao_by_set.csv", "02_shadow_old_vs_new_loao_by_set.csv"),
        ("closure_read_balanced_coverage_by_set.csv", "02_shadow_old_vs_new_balanced_coverage_by_set.csv"),
        ("closure_read_wrong_sign_scorecard.csv", "01_wrong_sign_definition_scorecard.csv"),
        ("closure_read_wrong_sign_approach_verdict.csv", "01_wrong_sign_approach_level_rescore.csv"),
    ]
    manifest_rows: list[dict[str, Any]] = []
    for out_name, src_name in copied:
        src = source / src_name
        dst = out_dir / out_name
        write_csv(dst, add_report_metadata(read_csv(src), head, source))
        manifest_rows.append({
            "output_artifact": out_name,
            "source_checkpoint_artifact": str(src.relative_to(ROOT)).replace("\\", "/"),
            "output_sha256": digest(dst),
        })
    manifest_rows.insert(0, {
        "output_artifact": input_manifest_path.name,
        "source_checkpoint_artifact": "checkpoint lineage manifest",
        "output_sha256": input_manifest_sha,
    })

    event_rows = summarize_event_support(
        read_csv(source / "01_wrong_sign_mask_accounting.csv"),
        read_csv(source / "01_wrong_sign_approach_level_rescore.csv"),
        read_csv(source / "01_wrong_sign_definition_scorecard.csv"),
        head,
        source,
    )
    event_path = out_dir / "closure_read_event_support_accounting.csv"
    write_csv(event_path, event_rows)
    manifest_rows.append({
        "output_artifact": event_path.name,
        "source_checkpoint_artifact": "derived from wrong-sign mask/accounting checkpoints",
        "output_sha256": digest(event_path),
    })

    write_csv(out_dir / "closure_read_artifact_manifest.csv", manifest_rows)
    summary = {
        "repo_head": head,
        "diagnostic_only": True,
        "report_layer_only": True,
        "source_checkpoint_dir": str(source.relative_to(ROOT)).replace("\\", "/"),
        "checkpoint_input_manifest_path": str(input_manifest_path.relative_to(ROOT)).replace("\\", "/"),
        "checkpoint_input_manifest_sha256": input_manifest_sha,
        "sequencing_floor_commit": git("rev-parse", SEQUENCING_FLOOR),
        "response53_commit": git("rev-parse", RESPONSE53_COMMIT),
        "generator_postdates_181f41f": is_ancestor(SEQUENCING_FLOOR, head),
        "shadow_partition": "3 overlap / 20 confirmatory / 23 pooled; legacy 5 listed / 4 analyzable appendix kept separate",
        "event_support": "16 trace rows -> 9 command events -> 7 sign-evaluable + 2 zero-on-support",
        "r26_1_verdict_scope": FIXTURE_LEVEL_SCOPE,
        "artifacts": [r["output_artifact"] for r in manifest_rows],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "summary.md").write_text(
        "\n".join([
            "# RESPONSE53 Closure-Read Report Layer",
            "",
            "Scope: DIAGNOSTIC, CSV-only; no FlightSim/DCGame launch.",
            f"Repo HEAD / report generator: `{head}`.",
            f"Source checkpoints: `{summary['source_checkpoint_dir']}`.",
            f"Checkpoint input manifest: `{summary['checkpoint_input_manifest_path']}`.",
            f"Checkpoint input manifest sha256: `{summary['checkpoint_input_manifest_sha256']}`.",
            "",
            f"- Generator postdates `181f41f`: `{summary['generator_postdates_181f41f']}`.",
            f"- Shadow partition: {summary['shadow_partition']}.",
            f"- Event support: {summary['event_support']}.",
            f"- R26-1 verdict scope: {FIXTURE_LEVEL_SCOPE}",
            "",
            "The resample arithmetic is reused from checkpointed outputs; this artifact is the fresh closure-read report layer.",
            "",
        ]),
        encoding="utf-8",
    )
    print(out_dir)
    return out_dir


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dir", type=Path, default=SOURCE_DIR)
    args = ap.parse_args(argv)
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
