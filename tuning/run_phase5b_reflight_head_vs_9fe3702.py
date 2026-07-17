"""Phase 5b offline reflight matrix: HEAD detector vs 9fe3702.

Uses the fixed HEAD scripts/reflight.py harness for both builds. For the old
build, the harness is copied into a temporary worktree so imports resolve
against that build's src/config while the frame dedupe + log-timing fix stays
constant.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = Path(os.environ.get(
    "PYTHON",
    r"C:\Users\tsion\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe",
))
RUN_ID = "phase5b-reflight-e9c1d97"
OUT_DIR = ROOT / "tuning" / RUN_ID
TMP_WORKTREES = ROOT / "tuning" / "_tmp_phase5b_reflight_worktrees"
LOCK_PATH = Path(r"C:\Temp\eni_dcim_sim.lock")
GIT = ["git", "-c", f"safe.directory={ROOT.as_posix()}"]

BUILDS = [
    ("old-9fe3702", "9fe3702"),
    ("new-HEAD", "HEAD"),
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

    target = wt / "scripts" / "reflight.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "scripts" / "reflight.py", target)
    if not (wt / "src" / "aigp" / "perception" / "close_tracker.py").exists():
        text = target.read_text(encoding="utf-8")
        text = text.replace(
            "from aigp.perception.close_tracker import GateCloseTracker\n",
            "try:\n"
            "    from aigp.perception.close_tracker import GateCloseTracker\n"
            "except ModuleNotFoundError:\n"
            "    GateCloseTracker = None\n",
        )
        text = text.replace(
            "    tracker = None if args.no_tracker else GateCloseTracker(params, detector)\n",
            "    tracker = None if args.no_tracker or GateCloseTracker is None else GateCloseTracker(params, detector)\n",
        )
        text = text.replace(
            "            det = detector.detect(cf, prior)\n",
            "            try:\n"
            "                det = detector.detect(cf, prior)\n"
            "            except TypeError:\n"
            "                det = detector.detect(cf)\n",
        )
        target.write_text(text, encoding="utf-8")
    return wt, sha


def cleanup_worktree(wt: Path) -> None:
    run([*GIT, "worktree", "remove", "--force", str(wt)], check=False)
    if wt.exists() and str(wt).startswith(str(TMP_WORKTREES)):
        shutil.rmtree(wt)


def parse_reflight(stdout: str) -> dict[str, object]:
    row: dict[str, object] = {f"range_{r}": 0 for r in RANGES}
    for line in stdout.splitlines():
        m = re.search(r"imu samples:\s*(\d+), unique frames:\s*(\d+)", line)
        if m:
            row["imu_samples"] = int(m.group(1))
            row["unique_frames"] = int(m.group(2))
        m = re.search(r"frame mono span:\s*([0-9.]+)s\s*\(ids\s*(\d+)\.\.(\d+)\)", line)
        if m:
            row["frame_span_s"] = float(m.group(1))
            row["frame_id_first"] = int(m.group(2))
            row["frame_id_last"] = int(m.group(3))
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
        m = re.search(
            r"close-tracker fixes:\s*(\d+)\s*"
            r"\(range\s*([0-9.]+)-([0-9.]+)m,\s*median\s*([0-9.]+)\)",
            line,
        )
        if m:
            row["close_tracker_fixes"] = int(m.group(1))
            row["close_tracker_min_m"] = float(m.group(2))
            row["close_tracker_max_m"] = float(m.group(3))
            row["close_tracker_median_m"] = float(m.group(4))
    row.setdefault("imu_samples", "")
    row.setdefault("unique_frames", "")
    row.setdefault("frame_span_s", "")
    row.setdefault("frame_id_first", "")
    row.setdefault("frame_id_last", "")
    row.setdefault("fixes", 0)
    row.setdefault("accepted", "")
    row.setdefault("coverage_events", "")
    row.setdefault("closest_fix_m", "")
    row.setdefault("close_tracker_fixes", 0)
    row.setdefault("close_tracker_min_m", "")
    row.setdefault("close_tracker_max_m", "")
    row.setdefault("close_tracker_median_m", "")
    frames = row.get("unique_frames", 0)
    fixes = row.get("fixes", 0)
    row["fix_rate"] = float(fixes) / float(frames) if frames else ""
    return row


def range_lt5(row: dict[str, object]) -> int:
    return sum(int(row.get(f"range_{r}") or 0) for r in RANGES[:-1])


def write_reports(rows: list[dict[str, object]], builds: list[dict[str, str]]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUT_DIR / "fix-rate-head-vs-9fe3702.csv"
    fieldnames = [
        "build", "build_sha", "slice", "log", "pairing", "status",
        "returncode", "imu_samples", "unique_frames", "frame_span_s",
        "frame_id_first", "frame_id_last", "fixes", "fix_rate", "accepted",
        "coverage_events", "closest_fix_m",
        "close_tracker_fixes", "close_tracker_min_m",
        "close_tracker_max_m", "close_tracker_median_m",
        *(f"range_{r}" for r in RANGES),
        "error",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    by_slice: dict[str, dict[str, dict[str, object]]] = {}
    for row in rows:
        by_slice.setdefault(str(row["slice"]), {})[str(row["build"])] = row

    lines = [
        "# Phase 5b Reflight: HEAD vs 9fe3702",
        "",
        f"Generated UTC: {dt.datetime.now(dt.timezone.utc).isoformat()}",
        "",
        "Scope: all committed `.aigprec` slices in HEAD, including "
        "`fixtures/20260716T212744-phase5-closerange-frames` and the "
        "three full-approach slices under "
        "`fixtures/20260717T092008-phase5b-confirm`.",
        "",
        "Harness: fixed HEAD `scripts/reflight.py` for both builds "
        "(frame dedupe + frame timing from flight log). For `9fe3702`, the "
        "fixed harness was copied into a temporary worktree while imports "
        "resolved against the old detector/config.",
        "",
        "SIM guard: checked before the matrix and between slices; no real "
        "simulator was launched or controlled.",
        "",
        "## Builds",
        "",
        "| Label | SHA |",
        "|---|---|",
    ]
    for build in builds:
        lines.append(f"| `{build['label']}` | `{build['sha']}` |")

    lines.extend(["", "## Summary", ""])
    lines.append("| Build | runnable | skipped no-log | errors | unique frames | fixes | fix rate | accepted | <5m fixes | >=5m fixes | close-tracker fixes |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for build in builds:
        label = build["label"]
        br = [r for r in rows if r["build"] == label]
        ok = [r for r in br if r["status"] == "ok"]
        skipped = [r for r in br if r["status"] == "skipped"]
        errors = [r for r in br if r["status"] == "error"]
        frames = sum(int(r.get("unique_frames") or 0) for r in ok)
        fixes = sum(int(r.get("fixes") or 0) for r in ok)
        accepted = sum(int(r.get("accepted") or 0) for r in ok)
        lt5 = sum(range_lt5(r) for r in ok)
        ge5 = sum(int(r.get("range_5.0-100.0") or 0) for r in ok)
        tracker = sum(int(r.get("close_tracker_fixes") or 0) for r in ok)
        rate = fixes / frames if frames else 0.0
        lines.append(
            f"| `{label}` | {len(ok)} | {len(skipped)} | {len(errors)} | "
            f"{frames} | {fixes} | {rate:.3f} | {accepted} | {lt5} | {ge5} | {tracker} |"
        )

    lines.extend(["", "## Per-Slice Old/New Detector", ""])
    lines.append("| slice | unique frames | old fixes/rate | new fixes/rate | old accepted | new accepted | old closest | new closest | old tracker | new tracker | note |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for slice_name in sorted(by_slice):
        old = by_slice[slice_name].get("old-9fe3702", {})
        new = by_slice[slice_name].get("new-HEAD", {})
        note = ""
        if old.get("status") == "skipped" or new.get("status") == "skipped":
            note = "skipped: no unique flight log"
        elif old.get("status") == "error" or new.get("status") == "error":
            note = "error"
        frames = new.get("unique_frames") or old.get("unique_frames") or ""
        old_rate = old.get("fix_rate", "")
        new_rate = new.get("fix_rate", "")
        old_rate_s = f"{float(old_rate):.3f}" if old_rate != "" else ""
        new_rate_s = f"{float(new_rate):.3f}" if new_rate != "" else ""
        lines.append(
            f"| `{slice_name}` | {frames} | "
            f"{old.get('fixes', '')}/{old_rate_s} | "
            f"{new.get('fixes', '')}/{new_rate_s} | "
            f"{old.get('accepted', '')} | {new.get('accepted', '')} | "
            f"{old.get('closest_fix_m', '')} | {new.get('closest_fix_m', '')} | "
            f"{old.get('close_tracker_fixes', '')} | {new.get('close_tracker_fixes', '')} | {note} |"
        )

    md_path = OUT_DIR / "fix-rate-head-vs-9fe3702.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT_DIR / "fix-rate-head-vs-9fe3702.json").write_text(
        json.dumps({"builds": builds, "rows": rows}, indent=2),
        encoding="utf-8",
    )


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
                        row.update({
                            "status": "skipped",
                            "returncode": "",
                            "error": "no unique flight log",
                        })
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
                        err = (proc.stderr or proc.stdout).strip()
                        row["error"] = err.splitlines()[-1][:500] if err else "nonzero return"
                    rows.append(row)
                    print(f"[{label}] {idx}/{len(pairs)} {row['status']} {slice_rel.as_posix()}")
            finally:
                cleanup_worktree(wt)
    finally:
        if TMP_WORKTREES.exists():
            shutil.rmtree(TMP_WORKTREES)

    write_reports(rows, resolved_builds)
    print(f"wrote {OUT_DIR / 'fix-rate-head-vs-9fe3702.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
