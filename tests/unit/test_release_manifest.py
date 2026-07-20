"""Release-manifest checker fixtures (RESPONSE43/44 disposition): the
control that turns RESPONSE-43's manual walk into standing law must
itself be pinned — it fails loudly on exactly the advisory-22 failure
classes: nonexistent artifacts, nonexistent commit objects, digest
drift, criteria registered after their evidence, and empty walks."""
import hashlib
import json
import subprocess
from pathlib import Path

from tools.release_manifest import check_manifest

REPO = Path(__file__).resolve().parents[2]


def _head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                          capture_output=True, text=True).stdout.strip()


def _row(**over):
    art = REPO / "config" / "params_default.json"
    row = {
        "board_row": 1,
        "claim": "test claim",
        "criterion_registered_at": _head(),
        "artifact_path": "config/params_default.json",
        "artifact_sha256": hashlib.sha256(art.read_bytes()).hexdigest(),
        "generator_commit": _head(),
        "generator_command": "pytest",
        "independent_unit": "physical_approach",
        "independent_n": 6,
        "result": "ok",
        "status": "GREEN",
    }
    row.update(over)
    return row


def _write(tmp_path, rows):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(rows))
    return p


def test_valid_manifest_verifies(tmp_path):
    assert check_manifest(_write(tmp_path, [_row()]), REPO) == []


def test_advisory22_failure_classes_all_fail(tmp_path):
    """The four classes the incident exhibited, each named in its own
    failure line: missing artifact, nonexistent commit hash, digest
    mismatch, and the empty walk."""
    fails = check_manifest(_write(tmp_path, [
        _row(board_row=3, artifact_path="tuning/does-not-exist/summary.md"),
        _row(board_row=7, generator_commit="b41c7f2b41c7f2b41c7f2"),
        _row(board_row=4, artifact_sha256="0" * 64),
    ]), REPO)
    assert any("row 3" in f and "does not exist" in f for f in fails)
    assert any("row 7" in f and "does not resolve" in f for f in fails)
    assert any("row 4" in f and "digest mismatch" in f for f in fails)
    assert check_manifest(_write(tmp_path, []), REPO) == [
        "manifest empty: a walk with no rows verifies nothing"]


def test_criterion_must_predate_evidence(tmp_path):
    """A bar registered after the number it gates is not a bar: the
    criterion commit must be an ancestor of the generator commit."""
    first = subprocess.run(
        ["git", "rev-list", "--max-parents=0", "HEAD"], cwd=REPO,
        capture_output=True, text=True).stdout.split()[0]
    ok = _row(criterion_registered_at=first)          # root predates HEAD
    bad = _row(board_row=9, criterion_registered_at=_head(),
               generator_commit=first)                # criterion AFTER
    fails = check_manifest(_write(tmp_path, [ok, bad]), REPO)
    assert not any("row 1" in f for f in fails)
    assert any("row 9" in f and "predate" in f for f in fails)


def test_rows_never_units(tmp_path):
    fails = check_manifest(_write(tmp_path, [_row(independent_n=0)]), REPO)
    assert any("independent_n" in f for f in fails)


def test_checkpoint_lineage_pair_and_digest(tmp_path):
    """Channel-1 §3 appendix: 'recomputed from the checkpoints' must
    be provable — the input-manifest pair travels together and its
    digest must match, so a report layer can never silently read a
    different intermediate than the computation wrote."""
    art = REPO / "config" / "params_default.json"
    good = hashlib.sha256(art.read_bytes()).hexdigest()
    fails = check_manifest(_write(tmp_path, [
        _row(board_row=1, input_manifest_path="config/params_default.json"),
        _row(board_row=2, input_manifest_path="config/params_default.json",
             input_manifest_sha256="0" * 64),
        _row(board_row=3, input_manifest_path="config/params_default.json",
             input_manifest_sha256=good),
    ]), REPO)
    assert any("row 1" in f and "pair" in f for f in fails)
    assert any("row 2" in f and "digest mismatch" in f for f in fails)
    assert not any("row 3" in f for f in fails)


def test_accounting_pair_and_identity(tmp_path):
    """Hardening 5.1: attempted/analyzable travel together, and
    independent_n == analyzable_n unless a typed accounting_mode
    declares otherwise — the rows-6-8 unit-count error class becomes
    machine-impossible."""
    fails = check_manifest(_write(tmp_path, [
        _row(board_row=1, attempted_n=5),                    # pair broken
        _row(board_row=2, attempted_n=5, analyzable_n=4,
             independent_n=99),                              # 99 != 4
        _row(board_row=3, attempted_n=5, analyzable_n=4,
             independent_n=4),                               # clean
        _row(board_row=4, attempted_n=1, analyzable_n=1,
             independent_n=5, accounting_mode="analyzable"), # 5 != 1
    ]), REPO)
    assert any("row 1" in f and "pair" in f for f in fails)
    assert any("row 2" in f and "accounting_mode" in f for f in fails)
    assert not any("row 3" in f for f in fails)
    assert any("row 4" in f for f in fails)


def test_release_grade_requires_evidence_and_bound_head(tmp_path):
    """Hardenings 5.2-5.4: with a reviewed tip bound, every row needs
    evidence_commit; the artifact must survive unchanged AT the tip;
    and HEAD must BE the tip (a clean checkout of a different commit
    verifies nothing about this one)."""
    head = _head()
    parent = subprocess.run(["git", "rev-parse", "HEAD~1"], cwd=REPO,
                            capture_output=True, text=True).stdout.strip()
    # Row without evidence_commit + tip bound to the PARENT (not HEAD).
    fails = check_manifest(_write(tmp_path, [_row()]), REPO,
                           reviewed_tip=parent)
    assert any("evidence_commit is required" in f for f in fails)
    assert any("is not the reviewed tip" in f for f in fails)
    # Evidence chain with committed-byte lookup: a file that exists at
    # HEAD but not at the root commit fails the survive-at-tip check
    # when the digest comes from a different revision's bytes.
    root = subprocess.run(["git", "rev-list", "--max-parents=0", "HEAD"],
                          cwd=REPO, capture_output=True,
                          text=True).stdout.split()[0]
    fails2 = check_manifest(_write(tmp_path, [
        _row(evidence_commit=root)]), REPO)
    assert any("absent at" in f or "digest mismatch" in f
               for f in fails2)
