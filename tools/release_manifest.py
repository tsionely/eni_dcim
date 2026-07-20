"""Release-manifest checker (RESPONSE43/44 disposition, permanent
release control): a HOLD-lift walk cites ONLY a committed manifest whose
every board row is machine-checkable. This converts the manual
repository verification of RESPONSE-43 into standing CI law.

Manifest format: a JSON list of rows (JSON, not YAML, so the checker
has zero dependencies and runs anywhere the repo runs):

    [{"board_row": 4,
      "claim": "boundary-aware U95(sigma_a) <= 0.35",
      "criterion_registered_at": "<commit that registered the bar>",
      "artifact_path": "tuning/<run>/summary.md",
      "artifact_sha256": "<hex digest>",
      "generator_commit": "<commit whose code produced it>",
      "generator_command": "python tuning/...",
      "input_manifest_sha256": "<hex digest or null>",
      "independent_unit": "physical_approach",
      "independent_n": 6,
      "result": "U95=...",
      "status": "GREEN"}, ...]

A row FAILS unless: the artifact path exists at the reviewed tip, its
digest matches, the generator and criterion commits resolve in the
object store, and the criterion commit is an ANCESTOR of the generator
commit (the criterion predates its evidence — a bar registered after
the number it gates is not a bar). Every failure names its row and
reason; an empty manifest is itself a failure — a walk with no rows
verifies nothing.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

REQUIRED_FIELDS = (
    "board_row", "claim", "criterion_registered_at", "artifact_path",
    "artifact_sha256", "generator_commit", "generator_command",
    "independent_unit", "independent_n", "result", "status",
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _commit_exists(repo: Path, ref: str) -> bool:
    r = subprocess.run(["git", "cat-file", "-t", ref], cwd=repo,
                       capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == "commit"


def _is_ancestor(repo: Path, older: str, newer: str) -> bool:
    r = subprocess.run(["git", "merge-base", "--is-ancestor", older, newer],
                       cwd=repo, capture_output=True)
    return r.returncode == 0


def _sha256_at_commit(repo: Path, commit: str, path: str) -> str | None:
    r = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=repo,
                       capture_output=True)
    if r.returncode != 0:
        return None
    return hashlib.sha256(r.stdout).hexdigest()


def _tree_clean(repo: Path) -> bool:
    r = subprocess.run(["git", "status", "--porcelain"], cwd=repo,
                       capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == ""


def check_manifest(manifest_path: str | Path,
                   repo_root: str | Path | None = None,
                   reviewed_tip: str | None = None) -> list[str]:
    """Returns a list of failures (empty list == manifest verifies).

    Release-grade contract (channel-2 §7 strengthening): pass
    reviewed_tip (full hash) to additionally enforce — clean working
    tree; criterion <= generator <= evidence <= reviewed_tip ancestry
    per row; and, when a row carries evidence_commit, its digest is
    computed from the COMMITTED bytes (git show evidence:path), never
    the mutable worktree."""
    manifest_path = Path(manifest_path)
    repo = Path(repo_root) if repo_root is not None else manifest_path.parent
    while repo != repo.parent and not (repo / ".git").exists():
        repo = repo.parent
    failures: list[str] = []
    if reviewed_tip is not None:
        if not _commit_exists(repo, reviewed_tip):
            return [f"reviewed_tip '{reviewed_tip}' does not resolve"]
        if not _tree_clean(repo):
            failures.append("working tree not clean at verification "
                            "time — the transcript would not describe "
                            "a committed state")
        # Hardening 5.4: the checkout being verified must BE the
        # reviewed tip — a clean checkout of some other commit would
        # verify a different history while claiming this one.
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                              capture_output=True, text=True
                              ).stdout.strip()
        tip_full = subprocess.run(["git", "rev-parse", reviewed_tip],
                                  cwd=repo, capture_output=True,
                                  text=True).stdout.strip()
        if head != tip_full:
            failures.append(f"HEAD ({head[:12]}) is not the reviewed "
                            f"tip ({tip_full[:12]})")
    try:
        rows = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        return [f"manifest unreadable: {e}"]
    if not isinstance(rows, list) or not rows:
        return ["manifest empty: a walk with no rows verifies nothing"]
    for row in rows:
        rid = f"row {row.get('board_row', '?')}"
        for field in REQUIRED_FIELDS:
            if field not in row or row[field] in (None, ""):
                failures.append(f"{rid}: missing field '{field}'")
        if any(f.startswith(rid + ":") and "missing" in f
               for f in failures):
            continue
        ev = row.get("evidence_commit")
        # Hardening 5.2: in release-grade mode (reviewed_tip bound)
        # the evidence chain is mandatory on every row.
        if reviewed_tip is not None and ev in (None, ""):
            failures.append(f"{rid}: evidence_commit is required in "
                            "release-grade mode")
        if ev not in (None, ""):
            # Committed-byte lookup: the digest describes what the
            # evidence commit STORES, never mutable worktree bytes.
            committed = _sha256_at_commit(repo, ev, row["artifact_path"])
            if committed is None:
                failures.append(f"{rid}: artifact absent at "
                                f"{ev}:{row['artifact_path']}")
            elif committed != row["artifact_sha256"]:
                failures.append(f"{rid}: committed-byte digest mismatch "
                                f"at {ev}:{row['artifact_path']}")
            # Hardening 5.3: the artifact must SURVIVE unchanged at
            # the reviewed tip — a descendant could delete or modify
            # it while keeping the evidence commit in its ancestry.
            if reviewed_tip is not None:
                at_tip = _sha256_at_commit(repo, reviewed_tip,
                                           row["artifact_path"])
                if at_tip is None:
                    failures.append(f"{rid}: artifact absent at the "
                                    f"reviewed tip: "
                                    f"{row['artifact_path']}")
                elif at_tip != row["artifact_sha256"]:
                    failures.append(f"{rid}: artifact modified between "
                                    "evidence commit and reviewed tip")
        else:
            art = repo / row["artifact_path"]
            if not art.exists():
                failures.append(f"{rid}: artifact does not exist on the "
                                f"reviewed tip: {row['artifact_path']}")
            elif _sha256(art) != row["artifact_sha256"]:
                failures.append(f"{rid}: artifact digest mismatch: "
                                f"{row['artifact_path']}")
        for key in ("generator_commit", "criterion_registered_at"):
            if not _commit_exists(repo, row[key]):
                failures.append(f"{rid}: {key} '{row[key]}' does not "
                                "resolve in the object store")
        # Optional typed evidence-landing commit (channel-2 amendment:
        # dual roles must be TYPED fields, never filename or free
        # text). When present it must resolve, and the full chain
        # criterion <= generator <= evidence (<= reviewed_tip) holds.
        if ev not in (None, ""):
            if not _commit_exists(repo, ev):
                failures.append(f"{rid}: evidence_commit '{ev}' does "
                                "not resolve in the object store")
            else:
                if (_commit_exists(repo, row["generator_commit"])
                        and not _is_ancestor(repo, row["generator_commit"],
                                             ev)):
                    failures.append(f"{rid}: generator_commit is not an "
                                    "ancestor of evidence_commit")
                if reviewed_tip is not None and not _is_ancestor(
                        repo, ev, reviewed_tip):
                    failures.append(f"{rid}: evidence_commit is not an "
                                    "ancestor of the reviewed tip")
        # Attempted/analyzable accounting (hardening 5.1 — the unit-
        # count error class becomes machine-impossible, not merely
        # discouraged): the pair travels together, and unless a typed
        # accounting_mode says otherwise, independent_n IS the
        # analyzable count.
        att, ana = row.get("attempted_n"), row.get("analyzable_n")
        if (att is None) != (ana is None):
            failures.append(f"{rid}: attempted_n and analyzable_n are "
                            "a pair — supply both or neither")
        elif att is not None:
            if not (isinstance(att, int) and isinstance(ana, int)
                    and 0 <= ana <= att):
                failures.append(f"{rid}: analyzable_n must be an int "
                                "with 0 <= analyzable_n <= attempted_n")
            elif (row.get("accounting_mode", "analyzable")
                    == "analyzable" and row.get("independent_n") != ana):
                failures.append(f"{rid}: independent_n "
                                f"({row.get('independent_n')}) != "
                                f"analyzable_n ({ana}) — declare a "
                                "typed accounting_mode if the relation "
                                "is legitimately different")
        if (_commit_exists(repo, row["criterion_registered_at"])
                and _commit_exists(repo, row["generator_commit"])
                and not _is_ancestor(repo, row["criterion_registered_at"],
                                     row["generator_commit"])):
            failures.append(f"{rid}: criterion does not predate its "
                            "evidence (not an ancestor of the generator "
                            "commit)")
        if not isinstance(row.get("independent_n"), int) \
                or row.get("independent_n", 0) < 1:
            failures.append(f"{rid}: independent_n must be a positive "
                            "integer (units, never rows)")
    return failures


if __name__ == "__main__":
    import sys
    tip = sys.argv[2] if len(sys.argv) > 2 else None
    fails = check_manifest(sys.argv[1], reviewed_tip=tip)
    for f in fails:
        print(f"FAIL {f}")
    # Hardening 5.2 (token separation): diagnostic runs must never
    # print the release-grade success token.
    ok_token = ("MANIFEST VERIFIES (RELEASE-GRADE)" if tip is not None
                else "MANIFEST VERIFIES (DIAGNOSTIC — no reviewed tip "
                     "bound; not a release verification)")
    print(ok_token if not fails else
          f"{len(fails)} FAILURES — the walk may not proceed")
    sys.exit(1 if fails else 0)
