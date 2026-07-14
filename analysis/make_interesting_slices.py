"""DATA ANALYST: extract interesting-moment slices from large recordings.

Uses scripts/slice_recording.py logic (DatagramRecorder) but lives under
analysis/ so DATA ANALYST stays out of scripts/. Writes under fixtures/.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aigp.io.udp_tap import STREAM_MAVLINK, STREAM_VISION, DatagramRecorder, read_recording  # noqa: E402


def slice_recording(
    src: Path,
    dst: Path,
    start_s: float,
    duration_s: float | None,
    max_mb: float,
) -> dict:
    out = DatagramRecorder(dst)
    t0 = None
    written_bytes = 0
    total = kept = 0
    vision = mavlink = 0
    for mono_ns, stream_id, data in read_recording(src):
        total += 1
        if t0 is None:
            t0 = mono_ns
        rel_s = (mono_ns - t0) / 1e9
        if rel_s < start_s:
            continue
        if duration_s is not None and rel_s > start_s + duration_s:
            break
        if written_bytes + len(data) > max_mb * 1e6:
            break
        out.write(stream_id, data, mono_ns=mono_ns)
        written_bytes += len(data)
        kept += 1
        if stream_id == STREAM_VISION:
            vision += 1
        elif stream_id == STREAM_MAVLINK:
            mavlink += 1
    out.close()
    return {
        "src": str(src),
        "dst": str(dst),
        "start_s": start_s,
        "duration_s": duration_s,
        "max_mb": max_mb,
        "kept_datagrams": kept,
        "total_scanned": total,
        "written_mb": round(written_bytes / 1e6, 2),
        "vision_datagrams": vision,
        "mavlink_datagrams": mavlink,
    }


# Curated moments based on known operator phases / recording names.
# start_s chosen to land near race activity rather than idle preamble.
DEFAULT_SLICES = [
    {
        "id": "phase1d-race-vision",
        "src": r"C:\Users\tsion\Projects\eni_dcim_phase1\recordings\phase1-20260713T200814.aigprec",
        "start_s": 10.0,
        "duration_s": 2.5,
        "max_mb": 38.0,
        "shows": "Phase-1d first real race vision window (early race after idle preamble).",
    },
    {
        "id": "phase1e-inflight",
        "src": r"C:\Users\tsion\Projects\eni_dcim_phase1\logs\20260713T202513-ea4b5f0c\vision.aigprec",
        "start_s": 5.0,
        "duration_s": 2.0,
        "max_mb": 38.0,
        "shows": "Phase-1e in-flight attempt vision; pair with flight.jsonl IMU motion check.",
    },
    {
        "id": "phase2a-controlled-flight",
        "src": r"C:\Users\tsion\Projects\eni_dcim_phase1\logs\20260714T045635-b9a568ab\vision.aigprec",
        "start_s": 8.0,
        "duration_s": 2.0,
        "max_mb": 38.0,
        "shows": "Phase-2a first controlled att_rate flight vision window.",
    },
    {
        "id": "phase2b-race-legal",
        "src": r"C:\Users\tsion\Projects\eni_dcim_phase1\logs\20260714T072732-8ff375f3\vision.aigprec",
        "start_s": 8.0,
        "duration_s": 2.0,
        "max_mb": 38.0,
        "shows": "Phase-2b race-legal takeoff attempt vision window (countdown/GO era).",
    },
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-root", default=str(ROOT / "fixtures" / "20260714T111500-analysis-slices"))
    parser.add_argument("--max-mb", type=float, default=38.0)
    args = parser.parse_args()

    out_root = Path(args.out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "label": "analysis-slices",
        "role": "DATA ANALYST",
        "slices": [],
    }

    for spec in DEFAULT_SLICES:
        src = Path(spec["src"])
        if not src.exists() or src.stat().st_size < 1_000_000:
            print(f"SKIP missing/small: {src}", flush=True)
            continue
        dst = out_root / f"{spec['id']}.aigprec"
        print(f"Slicing {src.name} -> {dst.name} @ {spec['start_s']}s ...", flush=True)
        info = slice_recording(
            src,
            dst,
            start_s=float(spec["start_s"]),
            duration_s=float(spec["duration_s"]) if spec.get("duration_s") is not None else None,
            max_mb=min(args.max_mb, float(spec["max_mb"])),
        )
        info["id"] = spec["id"]
        info["shows"] = spec["shows"]
        # Enforce <50 MB commit rule
        size_mb = dst.stat().st_size / 1e6
        info["final_size_mb"] = round(size_mb, 2)
        if size_mb >= 50.0:
            print(f"  WARNING: slice {dst} is {size_mb:.1f} MB (>=50); deleting", flush=True)
            dst.unlink(missing_ok=True)
            info["committed"] = False
        else:
            info["committed"] = True
            print(f"  kept {info['kept_datagrams']} datagrams, {size_mb:.1f} MB", flush=True)
        manifest["slices"].append(info)

    notes = [
        "# Analysis slices — interesting moments",
        "",
        "Created by DATA ANALYST (`analysis/make_interesting_slices.py`).",
        "Each `.aigprec` is a short wire-format slice from a large operator recording.",
        "",
    ]
    for s in manifest["slices"]:
        notes.append(f"## `{s.get('id')}`")
        notes.append(f"- shows: {s.get('shows')}")
        notes.append(f"- src: `{s.get('src')}`")
        notes.append(
            f"- window: start_s={s.get('start_s')}, duration_s={s.get('duration_s')}, "
            f"size={s.get('final_size_mb')} MB, committed={s.get('committed')}"
        )
        notes.append("")

    (out_root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (out_root / "notes.md").write_text("\n".join(notes), encoding="utf-8")
    # Also drop a pointer under analysis/
    analysis_ptr = ROOT / "analysis" / "20260714-interesting-slices.md"
    analysis_ptr.write_text(
        "\n".join(
            [
                "# Interesting-moment slices",
                "",
                f"Fixture folder: `{out_root.relative_to(ROOT).as_posix()}`",
                "",
                *notes[4:],
            ]
        ),
        encoding="utf-8",
    )
    print(f"Wrote {out_root / 'manifest.json'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
