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


def check_manifest(manifest_path: str | Path,
                   repo_root: str | Path | None = None) -> list[str]:
    """Returns a list of failures (empty list == manifest verifies)."""
    manifest_path = Path(manifest_path)
    repo = Path(repo_root) if repo_root is not None else manifest_path.parent
    while repo != repo.parent and not (repo / ".git").exists():
        repo = repo.parent
    failures: list[str] = []
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
    fails = check_manifest(sys.argv[1])
    for f in fails:
        print(f"FAIL {f}")
    print("MANIFEST VERIFIES" if not fails else
          f"{len(fails)} FAILURES — the walk may not proceed")
    sys.exit(1 if fails else 0)
