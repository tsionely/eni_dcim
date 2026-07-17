"""Closed-loop arbitration: HEAD vs 116b27e, 3x solo per requested test."""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = Path(os.environ.get(
    "PYTHON",
    r"C:\Users\tsion\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe",
))
OUT_DIR = ROOT / "tuning" / "closed-loop-arbitration-34d4f6b-vs-116b27e"
TMP_WORKTREES = ROOT / "tuning" / "_tmp_closed_loop_worktrees"
GIT = ["git", "-c", f"safe.directory={ROOT.as_posix()}"]

BUILDS = [
    ("HEAD-34d4f6b", "HEAD"),
    ("old-116b27e", "116b27e"),
]
TESTS = [
    (
        "single_gate",
        "tests/integration/test_mock_closed_loop.py::test_single_gate_pass",
    ),
    (
        "first_gate_with_second_visible",
        "tests/integration/test_mock_closed_loop.py::test_first_gate_pass_with_second_gate_visible",
    ),
]


def run(cmd: list[str], cwd: Path = ROOT, check: bool = True,
        timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(
            f"command failed ({proc.returncode}): {' '.join(cmd)}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return proc


def git_lines(*args: str) -> list[str]:
    proc = run([*GIT, *args])
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def prepare_worktree(label: str, ref: str) -> tuple[Path, str]:
    sha = git_lines("rev-parse", ref)[0]
    short = sha[:7]
    if ref == "HEAD":
        return ROOT, sha
    wt = TMP_WORKTREES / f"{label}-{short}"
    if wt.exists():
        run([*GIT, "worktree", "remove", "--force", str(wt)], check=False)
        if wt.exists():
            shutil.rmtree(wt)
    run([*GIT, "worktree", "add", "--detach", str(wt), sha])
    return wt, sha


def cleanup_worktree(wt: Path) -> None:
    if wt == ROOT:
        return
    run([*GIT, "worktree", "remove", "--force", str(wt)], check=False)
    if wt.exists() and str(wt).startswith(str(TMP_WORKTREES)):
        shutil.rmtree(wt)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if TMP_WORKTREES.exists():
        shutil.rmtree(TMP_WORKTREES)
    TMP_WORKTREES.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    builds: list[dict[str, str]] = []
    try:
        for build_label, ref in BUILDS:
            wt, sha = prepare_worktree(build_label, ref)
            builds.append({"label": build_label, "sha": sha})
            try:
                for test_label, nodeid in TESTS:
                    for run_idx in range(1, 4):
                        out_file = OUT_DIR / f"{build_label}-{test_label}-run{run_idx}.txt"
                        basetemp = Path(r"C:\Temp") / f"pytest-eni-arb-{build_label}-{test_label}-{run_idx}"
                        proc = run([
                            str(PYTHON), "-m", "pytest", nodeid, "-q",
                            f"--basetemp={basetemp}",
                        ], cwd=wt, check=False, timeout=240)
                        out_file.write_text(proc.stdout + proc.stderr, encoding="utf-8")
                        rows.append({
                            "build": build_label,
                            "sha": sha,
                            "test": test_label,
                            "nodeid": nodeid,
                            "run": run_idx,
                            "returncode": proc.returncode,
                            "passed": proc.returncode == 0,
                            "output": str(out_file.relative_to(ROOT)).replace("\\", "/"),
                        })
                        print(f"{build_label} {test_label} run {run_idx}: rc={proc.returncode}")
            finally:
                cleanup_worktree(wt)
    finally:
        if TMP_WORKTREES.exists():
            shutil.rmtree(TMP_WORKTREES)

    csv_path = OUT_DIR / "closed-loop-arbitration.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["build", "sha", "test", "nodeid", "run", "returncode", "passed", "output"],
        )
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Closed-Loop Arbitration: HEAD vs 116b27e",
        "",
        f"Generated UTC: {dt.datetime.now(dt.timezone.utc).isoformat()}",
        "",
        "Command shape: each test node was run solo, three times per build.",
        "",
        "## Builds",
        "",
        "| Label | SHA |",
        "|---|---|",
    ]
    for build in builds:
        lines.append(f"| `{build['label']}` | `{build['sha']}` |")
    lines.extend(["", "## Pass Rates", ""])
    lines.append("| Build | Test | Passed | Runs | Pass rate |")
    lines.append("|---|---|---:|---:|---:|")
    for build in builds:
        for test_label, _ in TESTS:
            subset = [r for r in rows if r["build"] == build["label"] and r["test"] == test_label]
            passed = sum(1 for r in subset if r["passed"])
            total = len(subset)
            rate = passed / total if total else 0.0
            lines.append(f"| `{build['label']}` | `{test_label}` | {passed} | {total} | {rate:.3f} |")
    lines.extend(["", "## Runs", ""])
    lines.append("| Build | Test | Run | Result | Output |")
    lines.append("|---|---|---:|---|---|")
    for row in rows:
        result = "PASS" if row["passed"] else f"FAIL rc={row['returncode']}"
        lines.append(
            f"| `{row['build']}` | `{row['test']}` | {row['run']} | {result} | `{row['output']}` |"
        )
    (OUT_DIR / "closed-loop-arbitration.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT_DIR / "closed-loop-arbitration.json").write_text(
        json.dumps({"builds": builds, "rows": rows}, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
