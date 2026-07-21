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
    assert any("row 2" in f and "violates mode" in f for f in fails)
    assert not any("row 3" in f for f in fails)
    assert any("row 4" in f and "violates mode" in f for f in fails)


def test_unknown_accounting_mode_fails_closed(tmp_path):
    """Channel-2 §4.1 closure: accounting_mode is a CLOSED enum — an
    unknown string is not an escape hatch from the count equation."""
    fails = check_manifest(_write(tmp_path, [
        _row(attempted_n=5, analyzable_n=4, independent_n=99,
             accounting_mode="anything_else")]), REPO)
    assert any("unknown accounting_mode" in f for f in fails)


def test_procedural_rows_mode_requires_typed_scope(tmp_path):
    """Channel-2 on R64 §6: procedural_rows counts DISPOSITION TASKS,
    never approaches — the mode demands a non-statistical
    evidence_scope and rejects statistical independent_unit claims."""
    fails = check_manifest(_write(tmp_path, [
        _row(board_row=1, attempted_n=5, analyzable_n=5, independent_n=5,
             accounting_mode="procedural_rows",
             evidence_scope="NO_GO_DISPOSITION",
             independent_unit="criterion_task"),              # clean
        _row(board_row=2, attempted_n=5, analyzable_n=5, independent_n=5,
             accounting_mode="procedural_rows",
             independent_unit="criterion_task"),   # scope missing
        _row(board_row=3, attempted_n=5, analyzable_n=5, independent_n=5,
             accounting_mode="procedural_rows",
             evidence_scope="NO_GO_DISPOSITION",
             independent_unit="physical_approach"),  # unit claims stats
    ]), REPO)
    assert not any("row 1" in f for f in fails)
    assert any("row 2" in f and "violates mode" in f for f in fails)
    assert any("row 3" in f and "violates mode" in f for f in fails)


def _mini_repo(tmp_path):
    """Throwaway repo for release-grade scenarios: c1 commits the
    artifact; the caller then evolves history deterministically."""
    repo = tmp_path / "mini"
    repo.mkdir()

    def g(*args):
        r = subprocess.run(["git", *args], cwd=repo, capture_output=True,
                           text=True)
        assert r.returncode == 0, r.stderr
        return r.stdout.strip()

    g("init", "-q")
    g("config", "user.email", "t@t")
    g("config", "user.name", "t")
    (repo / "artifact.txt").write_text("v1")
    g("add", "-A")
    g("commit", "-qm", "c1")
    c1 = g("rev-parse", "HEAD")
    return repo, g, c1


def _mini_row(repo, c1):
    art = repo / "artifact.txt"
    return {
        "board_row": 1, "claim": "mini", "criterion_registered_at": c1,
        "artifact_path": "artifact.txt",
        "artifact_sha256": hashlib.sha256(art.read_bytes()).hexdigest(),
        "generator_commit": c1, "generator_command": "test",
        "independent_unit": "physical_approach", "independent_n": 1,
        "result": "ok", "status": "REPORTED", "evidence_commit": c1,
    }


def test_release_grade_full_pass_then_tip_mutation_and_deletion(tmp_path):
    """Channel-2 §4.3 fixtures: a clean committed state passes
    release-grade; a descendant that MUTATES the artifact fails
    survive-at-tip; a descendant that DELETES it fails absent-at-tip
    — with HEAD==tip and clean tree throughout, so the failures are
    exactly the ones claimed."""
    repo, g, c1 = _mini_repo(tmp_path)
    (repo / "manifest.json").write_text(json.dumps([_mini_row(repo, c1)]))
    g("add", "-A")
    g("commit", "-qm", "manifest")
    c2 = g("rev-parse", "HEAD")
    assert check_manifest(repo / "manifest.json", repo,
                          reviewed_tip=c2) == []
    # Mutation in a descendant:
    (repo / "artifact.txt").write_text("v2")
    g("add", "-A")
    g("commit", "-qm", "mutate")
    c3 = g("rev-parse", "HEAD")
    fails = check_manifest(repo / "manifest.json", repo, reviewed_tip=c3)
    assert any("modified between evidence commit and reviewed tip" in f
               for f in fails)
    # Deletion in a further descendant:
    g("rm", "-q", "artifact.txt")
    g("commit", "-qm", "delete")
    c4 = g("rev-parse", "HEAD")
    fails = check_manifest(repo / "manifest.json", repo, reviewed_tip=c4)
    assert any("absent at the reviewed tip" in f for f in fails)


def test_manifest_self_binding(tmp_path):
    """Channel-2 §5: the manifest ITSELF must be the committed file at
    the reviewed tip — an external manifest is refused, and worktree
    bytes differing from the committed manifest are refused."""
    repo, g, c1 = _mini_repo(tmp_path)
    (repo / "manifest.json").write_text(json.dumps([_mini_row(repo, c1)]))
    g("add", "-A")
    g("commit", "-qm", "manifest")
    c2 = g("rev-parse", "HEAD")
    # External manifest (outside the repo): not committed-byte-bindable.
    ext = tmp_path / "external.json"
    ext.write_text(json.dumps([_mini_row(repo, c1)]))
    fails = check_manifest(ext, repo, reviewed_tip=c2)
    assert any("not repository-relative" in f for f in fails)
    # Worktree manifest modified after commit: dirty tree AND byte
    # mismatch are both named.
    (repo / "manifest.json").write_text(
        json.dumps([_mini_row(repo, c1)], indent=1))
    fails = check_manifest(repo / "manifest.json", repo, reviewed_tip=c2)
    assert any("manifest bytes differ" in f for f in fails)
    assert any("not clean" in f for f in fails)


def test_cli_token_separation(tmp_path):
    """Channel-2 §4.2 fixture: the CLI's diagnostic success token and
    release-grade success token are distinct strings — a diagnostic
    run can never print the release token."""
    repo, g, c1 = _mini_repo(tmp_path)
    (repo / "manifest.json").write_text(json.dumps([_mini_row(repo, c1)]))
    g("add", "-A")
    g("commit", "-qm", "manifest")
    c2 = g("rev-parse", "HEAD")
    tool = str(REPO / "tools" / "release_manifest.py")
    diag = subprocess.run(
        ["python", tool, str(repo / "manifest.json")],
        capture_output=True, text=True)
    rel = subprocess.run(
        ["python", tool, str(repo / "manifest.json"), c2],
        capture_output=True, text=True)
    assert "DIAGNOSTIC" in diag.stdout and "RELEASE-GRADE" not in diag.stdout
    assert "RELEASE-GRADE" in rel.stdout and rel.returncode == 0


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
