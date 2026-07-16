"""Phase 5 offline reflight matrix for QA.

Runs the HEAD reflight harness against all committed .aigprec slices while
swapping the imported source tree by build. Outputs stay under tuning/.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = Path(os.environ.get(
    "PYTHON",
    r"C:\Users\tsion\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe",
))
RUN_ID = "phase5-reflight-9fe3702"
OUT_DIR = ROOT / "tuning" / RUN_ID
TMP_WORKTREES = ROOT / "tuning" / "_tmp_phase5_reflight_worktrees"
LOCK_PATH = Path(r"C:\Temp\eni_dcim_sim.lock")
GIT = ["git", "-c", f"safe.directory={ROOT.as_posix()}"]

BUILDS = [
    ("fd9d419", "fd9d419"),
    ("54a75a1", "54a75a1"),
    ("80c6d44", "80c6d44"),
    ("HEAD", "HEAD"),
]

RANGES = [
    "0.0-0.5",
    "0.5-1.0",
    "1.0-1.5",
    "1.5-2.0",
    "2.0-3.0",
    "3.0-5.0",
    "5.0-100.0",
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


def guard_clear() -> None:
    details: list[str] = []
    if LOCK_PATH.exists():
        details.append("lock=" + LOCK_PATH.read_text(errors="replace").strip())
    proc = run([
        "powershell", "-NoProfile", "-Command",
        "Get-Process FlightSim,DCGame -ErrorAction SilentlyContinue | "
        "Select-Object -ExpandProperty ProcessName",
    ], check=False)
    names = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if names:
        details.append("processes=" + ",".join(names))
    if details:
        raise RuntimeError("sim guard blocked reflight: " + "; ".join(details))


def git_lines(*args: str) -> list[str]:
    proc = run([*GIT, *args])
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def build_log_map() -> dict[str, Path]:
    logs = [Path(p) for p in git_lines("ls-files", "*-flight.jsonl")]
    return {str(path).replace("\\", "/"): ROOT / path for path in logs}


def flight_number(stem: str) -> int | None:
    match = re.search(r"(?:^|[_-])f(\d+)(?:[_-]|$)", stem)
    return int(match.group(1)) if match else None


def paired_log(slice_path: Path, log_map: dict[str, Path]) -> tuple[Path | None, str]:
    rel = slice_path.as_posix()
    parent = Path(rel).parent
    stem = Path(rel).stem
    prefix = stem.split("_", 1)[0]
    if "-" in prefix:
        direct = (parent / f"{prefix}-flight.jsonl").as_posix()
        if direct in log_map:
            return log_map[direct], "direct-prefix"

    same_dir = sorted(
        path for key, path in log_map.items()
        if Path(key).parent.as_posix() == parent.as_posix()
    )
    if len(same_dir) == 1:
        return same_dir[0], "single-log-dir"

    num = flight_number(stem)
    if num is not None and 1 <= num <= len(same_dir):
        return same_dir[num - 1], f"flight-index-f{num}"

    return None, "no-unique-flight-log"


def prepare_worktree(label: str, ref: str) -> tuple[Path, str]:
    sha = git_lines("rev-parse", ref)[0]
    short = sha[:7]
    wt = TMP_WORKTREES / f"{label}-{short}"
    if wt.exists():
        run([*GIT, "worktree", "remove", "--force", str(wt)], check=False)
        if wt.exists():
            shutil.rmtree(wt)
    run([*GIT, "worktree", "add", "--detach", str(wt), sha])

    # Older builds predate scripts/reflight.py; keep the harness constant while
    # letting imports resolve to the checked-out build's src/config.
    target = wt / "scripts" / "reflight.py"
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "scripts" / "reflight.py", target)
    return wt, sha


def cleanup_worktree(wt: Path) -> None:
    run([*GIT, "worktree", "remove", "--force", str(wt)], check=False)
    if wt.exists() and str(wt).startswith(str(TMP_WORKTREES)):
        shutil.rmtree(wt)


def parse_reflight(stdout: str) -> dict[str, str | int | float]:
    row: dict[str, str | int | float] = {f"range_{r}": 0 for r in RANGES}
    for line in stdout.splitlines():
        m = re.search(r"imu samples:\s*(\d+), frames:\s*(\d+)", line)
        if m:
            row["imu_samples"] = int(m.group(1))
            row["frames"] = int(m.group(2))
        m = re.search(r"fixes produced:\s*(\d+)", line)
        if m:
            row["fixes"] = int(m.group(1))
        m = re.search(r"range\s+([0-9.]+)-([0-9.]+)m:\s*(\d+)\s+fixes", line)
        if m:
            row[f"range_{m.group(1)}-{m.group(2)}"] = int(m.group(3))
        m = re.search(r"accepted by lock:\s*(\d+)/(\d+)", line)
        if m:
            row["accepted"] = int(m.group(1))
            row["coverage_events"] = int(m.group(2))
        m = re.search(r"closest fix range:\s*([0-9.]+)m", line)
        if m:
            row["closest_fix_m"] = float(m.group(1))
    row.setdefault("imu_samples", "")
    row.setdefault("frames", "")
    row.setdefault("fixes", 0)
    row.setdefault("accepted", "")
    row.setdefault("coverage_events", "")
    row.setdefault("closest_fix_m", "")
    return row


def write_reports(rows: list[dict[str, object]], builds: list[dict[str, str]]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "fix-coverage-vs-range.csv"
    fieldnames = [
        "build", "build_sha", "slice", "log", "pairing", "status",
        "returncode", "imu_samples", "frames", "fixes", "accepted",
        "coverage_events", "closest_fix_m",
        *(f"range_{r}" for r in RANGES),
        "error",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    md = OUT_DIR / "fix-coverage-vs-range.md"
    lines = [
        "# Phase 5 Reflight Fix Coverage vs Range",
        "",
        f"Generated UTC: {dt.datetime.now(dt.timezone.utc).isoformat()}",
        "",
        "Scope: all committed `.aigprec` slices in HEAD, crossed with builds "
        "`fd9d419`, `54a75a1`, `80c6d44`, and `HEAD`.",
        "",
        "Harness note: the stable HEAD `scripts/reflight.py` harness was used "
        "for all builds; older worktrees predated the script, so the harness "
        "was copied into temporary worktrees while imports resolved against "
        "each build's `src/` and `config/`.",
        "",
        "SIM guard: checked before CI and before the reflight matrix; no real "
        "simulator was launched or controlled.",
        "",
        "## Builds",
        "",
        "| Build | SHA |",
        "|---|---|",
    ]
    for build in builds:
        lines.append(f"| `{build['label']}` | `{build['sha']}` |")

    lines.extend(["", "## Summary", ""])
    lines.append("| Build | runnable slices | skipped no-log | errors | fixes | accepted | closest fix m | <3m fixes | 3-5m fixes | >=5m fixes |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for build in builds:
        label = build["label"]
        br = [r for r in rows if r["build"] == label]
        runnable = [r for r in br if r["status"] == "ok"]
        skipped = [r for r in br if r["status"] == "skipped"]
        errors = [r for r in br if r["status"] == "error"]
        fixes = sum(int(r.get("fixes") or 0) for r in runnable)
        accepted = sum(int(r.get("accepted") or 0) for r in runnable)
        close_vals = [
            float(r["closest_fix_m"]) for r in runnable
            if str(r.get("closest_fix_m", "")) not in ("", "nan")
        ]
        closest = f"{min(close_vals):.2f}" if close_vals else ""
        lt3 = sum(
            int(r.get("range_0.0-0.5") or 0)
            + int(r.get("range_0.5-1.0") or 0)
            + int(r.get("range_1.0-1.5") or 0)
            + int(r.get("range_1.5-2.0") or 0)
            + int(r.get("range_2.0-3.0") or 0)
            for r in runnable
        )
        r3to5 = sum(int(r.get("range_3.0-5.0") or 0) for r in runnable)
        r5 = sum(int(r.get("range_5.0-100.0") or 0) for r in runnable)
        lines.append(
            f"| `{label}` | {len(runnable)} | {len(skipped)} | {len(errors)} | "
            f"{fixes} | {accepted} | {closest} | {lt3} | {r3to5} | {r5} |"
        )

    for build in builds:
        label = build["label"]
        br = [r for r in rows if r["build"] == label]
        lines.extend(["", f"## Build `{label}`", ""])
        lines.append("| slice | status | fixes | accepted | closest m | <3m | 3-5m | >=5m | note |")
        lines.append("|---|---|---:|---:|---:|---:|---:|---:|---|")
        for r in br:
            lt3 = (
                int(r.get("range_0.0-0.5") or 0)
                + int(r.get("range_0.5-1.0") or 0)
                + int(r.get("range_1.0-1.5") or 0)
                + int(r.get("range_1.5-2.0") or 0)
                + int(r.get("range_2.0-3.0") or 0)
            )
            note = r.get("pairing", "")
            if r["status"] == "error":
                note = str(r.get("error", ""))[:120].replace("|", "/")
            elif r["status"] == "skipped":
                note = "no unique flight log"
            lines.append(
                f"| `{r['slice']}` | {r['status']} | {r.get('fixes', '')} | "
                f"{r.get('accepted', '')} | {r.get('closest_fix_m', '')} | "
                f"{lt3} | {r.get('range_3.0-5.0', '')} | "
                f"{r.get('range_5.0-100.0', '')} | {note} |"
            )

    md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    json_path = OUT_DIR / "fix-coverage-vs-range.json"
    json_path.write_text(json.dumps({
        "builds": builds,
        "rows": rows,
    }, indent=2), encoding="utf-8")


def main() -> int:
    guard_clear()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if TMP_WORKTREES.exists():
        shutil.rmtree(TMP_WORKTREES)
    TMP_WORKTREES.mkdir(parents=True, exist_ok=True)

    log_map = build_log_map()
    slices = [Path(p) for p in git_lines("ls-files", "*.aigprec")]
    pairs = [(s, *paired_log(s, log_map)) for s in slices]

    rows: list[dict[str, object]] = []
    resolved_builds: list[dict[str, str]] = []
    try:
        for label, ref in BUILDS:
            guard_clear()
            wt, sha = prepare_worktree(label, ref)
            resolved_builds.append({"label": label, "sha": sha})
            try:
                for idx, (slice_rel, log_abs, pairing) in enumerate(pairs, 1):
                    guard_clear()
                    row: dict[str, object] = {
                        "build": label,
                        "build_sha": sha,
                        "slice": slice_rel.as_posix(),
                        "log": str(log_abs.relative_to(ROOT)).replace("\\", "/") if log_abs else "",
                        "pairing": pairing,
                    }
                    if log_abs is None:
                        row.update({"status": "skipped", "returncode": "", "error": "no unique flight log"})
                        rows.append(row)
                        continue

                    proc = run([
                        str(PYTHON),
                        str(wt / "scripts" / "reflight.py"),
                        "--slice", str((ROOT / slice_rel).resolve()),
                        "--log", str(log_abs.resolve()),
                    ], cwd=wt, check=False, timeout=240)
                    row["returncode"] = proc.returncode
                    if proc.returncode == 0:
                        row.update(parse_reflight(proc.stdout))
                        row["status"] = "ok"
                        row["error"] = ""
                    else:
                        row.update({f"range_{r}": "" for r in RANGES})
                        row["status"] = "error"
                        row["error"] = (proc.stderr or proc.stdout).strip().splitlines()[-1][:500] if (proc.stderr or proc.stdout).strip() else "nonzero return"
                    rows.append(row)
                    print(f"[{label}] {idx}/{len(pairs)} {row['status']} {slice_rel.as_posix()}")
            finally:
                cleanup_worktree(wt)
    finally:
        if TMP_WORKTREES.exists():
            shutil.rmtree(TMP_WORKTREES)

    write_reports(rows, resolved_builds)
    print(f"wrote {OUT_DIR / 'fix-coverage-vs-range.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
