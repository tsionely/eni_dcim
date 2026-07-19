from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = Path("C:/Temp/eni_dcim_sim.lock")
PYTHON = Path(os.environ.get("ENI_PYTHON", "C:/Temp/eni_dcim_venv/Scripts/python.exe"))
TEST_NODE = "tests/integration/test_mock_closed_loop.py::test_single_gate_pass"
RUNS = int(os.environ.get("ENI_SINGLE_GATE_RUNS", "10"))
OUT_DIR = ROOT / "tuning" / f"framefix-single-gate-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
WORKTREE_ROOT = Path("C:/Temp/eni_dcim_worktrees")


@dataclass
class Build:
    label: str
    sha: str
    path: Path


def git(args: list[str], cwd: Path = ROOT) -> str:
    return subprocess.check_output(["git", "-c", f"safe.directory={ROOT.as_posix()}", *args], cwd=cwd, text=True).strip()


def run(args: list[str], cwd: Path, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)


def flight_sim_processes() -> list[str]:
    rows: list[str] = []
    for image in ("FlightSim.exe", "DCGame.exe"):
        proc = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {image}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
        )
        text = proc.stdout.strip()
        if text and "No tasks are running" not in text:
            rows.extend(line for line in text.splitlines() if line.strip())
    return rows


def assert_mock_safe() -> None:
    details: list[str] = []
    if LOCK_PATH.exists():
        details.append(f"lock={LOCK_PATH.read_text(errors='replace').strip()}")
    procs = flight_sim_processes()
    if procs:
        details.append("processes=" + " | ".join(procs))
    if details:
        raise RuntimeError("SIM guard blocked reliability run: " + "; ".join(details))


def ensure_pre_fix_worktree(pre_fix_sha: str) -> Path:
    WORKTREE_ROOT.mkdir(parents=True, exist_ok=True)
    path = WORKTREE_ROOT / f"pre-frame-{pre_fix_sha[:8]}"
    if path.exists():
        current = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()
        if current.startswith(pre_fix_sha) or pre_fix_sha.startswith(current):
            return path
        subprocess.run(["git", "worktree", "remove", "--force", str(path)], cwd=ROOT, check=False)
        if path.exists():
            shutil.rmtree(path)
    subprocess.run(["git", "worktree", "add", "--detach", str(path), pre_fix_sha], cwd=ROOT, check=True)
    return path


def extract_summary(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    interesting = [
        line for line in lines
        if "failed" in line.lower()
        or "passed" in line.lower()
        or "TimeoutError" in line
        or "AssertionError" in line
        or "environment collision" in line
        or "never passed" in line
        or "race did not finish" in line
    ]
    return " | ".join(interesting[-8:])[:1200]


def run_build(build: Build) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for idx in range(1, RUNS + 1):
        assert_mock_safe()
        basetemp = Path("C:/Temp") / f"pytest-eni-single-{build.label}-{idx:02d}"
        log_path = OUT_DIR / f"{build.label}-run{idx:02d}.txt"
        cmd = [
            str(PYTHON),
            "-m",
            "pytest",
            TEST_NODE,
            "-q",
            "-p",
            "no:cacheprovider",
            f"--basetemp={basetemp}",
        ]
        started = datetime.now(timezone.utc)
        proc = run(cmd, cwd=build.path, timeout=180)
        ended = datetime.now(timezone.utc)
        output = proc.stdout + proc.stderr
        log_path.write_text(output, encoding="utf-8", errors="replace")
        row = {
            "build": build.label,
            "sha": build.sha,
            "run": idx,
            "returncode": proc.returncode,
            "pass": proc.returncode == 0,
            "duration_s": round((ended - started).total_seconds(), 3),
            "log": str(log_path.relative_to(ROOT)),
            "summary": extract_summary(output),
        }
        rows.append(row)
        print(
            f"[single-gate] {build.label} {idx}/{RUNS} "
            f"{'PASS' if row['pass'] else 'FAIL'} rc={proc.returncode}",
            flush=True,
        )
        time.sleep(0.5)
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def build_summary(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    summary: list[dict[str, object]] = []
    for label in sorted({str(r["build"]) for r in rows}):
        build_rows = [r for r in rows if r["build"] == label]
        passed = sum(1 for r in build_rows if r["pass"])
        summary.append({
            "build": label,
            "sha": build_rows[0]["sha"],
            "passes": passed,
            "runs": len(build_rows),
            "pass_rate": passed / len(build_rows) if build_rows else 0.0,
        })
    return summary


def write_report(rows: list[dict[str, object]], summary: list[dict[str, object]]) -> None:
    lines = [
        "# Frame-Fix Single-Gate Reliability",
        "",
        "Role: QA & MOCK-TUNER.",
        "Scope: mock only. No real simulator was launched, reset, clicked, or commanded.",
        f"Test node: `{TEST_NODE}`.",
        f"Runs per build: `{RUNS}`.",
        f"Python: `{PYTHON}`.",
        "",
        "## Pass Rate",
        "",
        "| Build | Commit | Passes | Runs | Pass rate |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"| `{row['build']}` | `{str(row['sha'])[:12]}` | "
            f"{row['passes']} | {row['runs']} | {float(row['pass_rate']):.1%} |"
        )
    lines.extend([
        "",
        "## Attempts",
        "",
        "| Build | Run | Verdict | Duration s | Log | Summary |",
        "|---|---:|---|---:|---|---|",
    ])
    for row in rows:
        verdict = "PASS" if row["pass"] else f"FAIL rc={row['returncode']}"
        lines.append(
            f"| `{row['build']}` | {row['run']} | {verdict} | "
            f"{row['duration_s']} | `{row['log']}` | "
            f"{str(row['summary']).replace('|', '/')[:240]} |"
        )
    (OUT_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    if not PYTHON.exists():
        raise SystemExit(f"Python not found: {PYTHON}")
    assert_mock_safe()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    head_sha = git(["rev-parse", "HEAD"])
    frame_fix_sha = git(["rev-parse", "2c5057a"])
    pre_fix_sha = git(["rev-parse", "2c5057a^"])
    pre_fix_path = ensure_pre_fix_worktree(pre_fix_sha)

    builds = [
        Build(label=f"head-{head_sha[:7]}", sha=head_sha, path=ROOT),
        Build(label=f"pre-fix-{pre_fix_sha[:7]}", sha=pre_fix_sha, path=pre_fix_path),
    ]
    rows: list[dict[str, object]] = []
    for build in builds:
        rows.extend(run_build(build))
    summary = build_summary(rows)
    write_csv(OUT_DIR / "single-gate-runs.csv", rows)
    (OUT_DIR / "single-gate-runs.json").write_text(
        json.dumps({"head": head_sha, "frame_fix": frame_fix_sha,
                    "pre_fix": pre_fix_sha, "summary": summary,
                    "rows": rows}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(rows, summary)
    print(f"[single-gate] report={OUT_DIR / 'summary.md'}", flush=True)
    return 0 if any(r["pass"] for r in rows if str(r["build"]).startswith("head-")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
