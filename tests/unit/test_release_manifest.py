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
