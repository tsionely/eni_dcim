"""Extract commit-sized interesting-moment slices into fixtures/."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVENTS = ROOT / "analysis" / "flight_events.json"
SLICE_PY = ROOT / "scripts" / "slice_recording.py"
OUT_ROOT = ROOT / "fixtures" / "20260714-analysis-slices"
MANIFEST = OUT_ROOT / "manifest.json"

# Curated slices: prioritize DSQ countdown, closest approaches, parked race.
CURATED = [
    {
        "flight_id": "20260714T072732-8ff375f3",
        "label": "phase2b_countdown_future_start",
        "start_s": 15.671,
        "duration_s": 5.0,
        "max_mb": 35.0,
        "note": "Countdown where race_start is ~2781ms in the future; early-start DSQ window.",
    },
    {
        "flight_id": "20260714T072732-8ff375f3",
        "label": "phase2b_closest_gate_3p97m",
        "start_s": 23.222,
        "duration_s": 4.0,
        "max_mb": 35.0,
        "note": "Closest logged gate approach in phase2b tumble (~3.97m).",
    },
    {
        "flight_id": "20260714T045635-b9a568ab",
        "label": "phase2a_countdown_future_start",
        "start_s": 14.576,
        "duration_s": 5.0,
        "max_mb": 35.0,
        "note": "Phase2a early-start DSQ countdown (~2891ms future start).",
    },
    {
        "flight_id": "20260714T081945-bb5494d6",
        "label": "phase2c_countdown_future_start",
        "start_s": 16.877,
        "duration_s": 5.0,
        "max_mb": 35.0,
        "note": "Phase2c countdown; race_start ~2751ms ahead of boot.",
    },
    {
        "flight_id": "20260714T081945-bb5494d6",
        "label": "phase2c_closest_gate_6p98m",
        "start_s": 20.041,
        "duration_s": 4.0,
        "max_mb": 35.0,
        "note": "Phase2c closest gate (~6.98m) near THROTTLE_DOWN->TAKEOFF.",
    },
    {
        "flight_id": "20260713T202513-ea4b5f0c",
        "label": "phase1e_countdown_and_gate",
        "start_s": 15.678,
        "duration_s": 5.0,
        "max_mb": 35.0,
        "note": "Parked/race vision with future race_start (~2834ms); high detection regime.",
    },
]


def main() -> int:
    py = Path(r"C:\Users\tsion\Projects\eni_dcim\.venv\Scripts\python.exe")
    events = {e["flight_id"]: e for e in json.loads(EVENTS.read_text(encoding="utf-8"))}
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    entries = []
    for spec in CURATED:
        fid = spec["flight_id"]
        ev = events.get(fid)
        if not ev or not ev.get("vision_recording"):
            print(f"skip {fid}: no vision", flush=True)
            continue
        src = Path(ev["vision_recording"])
        if not src.exists() or src.stat().st_size < 1_000_000:
            print(f"skip {fid}: missing/empty {src}", flush=True)
            continue
        dst = OUT_ROOT / f"{spec['label']}.aigprec"
        cmd = [
            str(py),
            str(SLICE_PY),
            str(src),
            str(dst),
            "--start-s",
            str(spec["start_s"]),
            "--duration-s",
            str(spec["duration_s"]),
            "--max-mb",
            str(spec["max_mb"]),
        ]
        print(" ".join(cmd), flush=True)
        subprocess.check_call(cmd)
        size_mb = dst.stat().st_size / 1e6
        if size_mb >= 50:
            print(f"WARNING: {dst} is {size_mb:.1f} MB (>=50)", flush=True)
        entries.append({
            **spec,
            "src": str(src),
            "dst": str(dst.relative_to(ROOT)).replace("\\", "/"),
            "size_mb": round(size_mb, 2),
        })

    notes = [
        "# Analysis slices — interesting moments",
        "",
        "Extracted by DATA ANALYST from operator-local large recordings.",
        "Each `.aigprec` is a wire-format slice suitable for `aigp --mode replay`.",
        "",
    ]
    for e in entries:
        notes.append(f"## `{Path(e['dst']).name}`")
        notes.append("")
        notes.append(f"- flight: `{e['flight_id']}`")
        notes.append(f"- window: start_s={e['start_s']}, duration_s={e['duration_s']}, size={e['size_mb']} MB")
        notes.append(f"- note: {e['note']}")
        notes.append("")
    (OUT_ROOT / "notes.md").write_text("\n".join(notes), encoding="utf-8")
    MANIFEST.write_text(json.dumps({"slices": entries}, indent=2), encoding="utf-8")
    print(f"Wrote {MANIFEST} ({len(entries)} slices)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
