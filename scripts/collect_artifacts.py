"""Package the latest run artifacts into fixtures/ for commit.

Run on the sim machine after a flight/check (see AGENTS.md):

    python scripts/collect_artifacts.py --label phase1 --report phase1_report.txt

Collects into fixtures/<utc-timestamp>-<label>/:
- the given report file (console output)
- logs/frame_probe/probe.json if present
- the newest logs/<flight_id>/ (flight.jsonl, result.json, params.json)
- the newest recordings/*.aigprec, zipped (skipped if > --max-recording-mb)
- manifest.json describing everything collected
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def newest(paths: list[Path]) -> Path | None:
    paths = [p for p in paths if p.exists()]
    return max(paths, key=lambda p: p.stat().st_mtime) if paths else None


def git_head() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect run artifacts into fixtures/")
    parser.add_argument("--label", required=True, help="e.g. phase1, hover, gate")
    parser.add_argument("--report", default=None, help="captured console output file")
    parser.add_argument("--max-recording-mb", type=float, default=50.0)
    args = parser.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_dir = REPO_ROOT / "fixtures" / f"{stamp}-{args.label}"
    out_dir.mkdir(parents=True, exist_ok=False)
    manifest: dict = {"label": args.label, "created_utc": stamp,
                      "code_commit": git_head(), "items": []}

    def note(kind: str, src: str, dest: Path) -> None:
        manifest["items"].append({"kind": kind, "source": src,
                                  "file": dest.name,
                                  "bytes": dest.stat().st_size if dest.exists() else 0})
        print(f"  + {kind}: {dest.name}")

    # Console report.
    if args.report and Path(args.report).exists():
        dest = out_dir / "report.txt"
        shutil.copy(args.report, dest)
        note("report", args.report, dest)
    else:
        print("  ! no report file given/found — remember to Tee the console output")

    # frame_probe output.
    probe = REPO_ROOT / "logs" / "frame_probe" / "probe.json"
    if probe.exists():
        dest = out_dir / "probe.json"
        shutil.copy(probe, dest)
        note("frame_probe", str(probe), dest)

    # Newest flight log directory.
    logs_root = REPO_ROOT / "logs"
    flight_dirs = [d for d in logs_root.glob("*") if d.is_dir()
                   and (d / "flight.jsonl").exists()] if logs_root.exists() else []
    flight = newest(flight_dirs)
    if flight is not None:
        for name in ("flight.jsonl", "result.json", "params.json"):
            src = flight / name
            if src.exists():
                dest = out_dir / f"{flight.name}-{name}"
                shutil.copy(src, dest)
                note("flight_log", str(src), dest)

    # Newest recording (flight-embedded or standalone), zipped.
    candidates = list((REPO_ROOT / "recordings").glob("*.aigprec")) if (REPO_ROOT / "recordings").exists() else []
    if flight is not None and (flight / "vision.aigprec").exists():
        candidates.append(flight / "vision.aigprec")
    recording = newest(candidates)
    if recording is not None:
        size_mb = recording.stat().st_size / 1e6
        if size_mb <= args.max_recording_mb:
            dest = out_dir / "recording.zip"
            with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(recording, recording.name)
            note("recording", str(recording), dest)
        else:
            manifest["items"].append({"kind": "recording_skipped",
                                      "source": str(recording),
                                      "reason": f"{size_mb:.0f} MB > limit; upload to Drive"})
            print(f"  ! recording {recording.name} is {size_mb:.0f} MB — "
                  f"upload it to Drive ('AI-GP Simulator/recordings') instead")

    with open(out_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nCollected into {out_dir.relative_to(REPO_ROOT)}")
    print("Now: add notes.md with your observations, then commit + push (see AGENTS.md).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
