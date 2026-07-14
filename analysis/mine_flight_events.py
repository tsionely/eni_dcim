"""Summarize flight.jsonl logs and propose interesting slice windows."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGS = Path(r"C:\Users\tsion\Projects\eni_dcim_phase1\logs")
OUT = ROOT / "analysis" / "flight_events.json"


def analyze(flight_dir: Path) -> dict:
    fl = flight_dir / "flight.jsonl"
    topics: Counter = Counter()
    fsm = []
    race_changes = []
    collisions = []
    imu_std = None
    first = last = None
    det_dists = []
    prev_race = None
    with fl.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            topics[rec["topic"]] += 1
            mono = rec.get("mono_ns")
            if mono is None:
                continue
            if first is None:
                first = mono
            last = mono
            t = (mono - first) / 1e9
            data = rec.get("data", {})
            if rec["topic"] == "fsm":
                fsm.append({"t_s": round(t, 3), "src": data.get("src"), "dst": data.get("dst")})
            elif rec["topic"] == "race":
                key = (
                    data.get("started"),
                    data.get("race_start_boot_time_ms"),
                    data.get("active_gate_index"),
                    data.get("finished"),
                )
                if key != prev_race:
                    race_changes.append({
                        "t_s": round(t, 3),
                        "started": data.get("started"),
                        "finished": data.get("finished"),
                        "active_gate_index": data.get("active_gate_index"),
                        "race_start_boot_time_ms": data.get("race_start_boot_time_ms"),
                        "sim_boot_time_ms": data.get("sim_boot_time_ms"),
                    })
                    prev_race = key
            elif rec["topic"] == "collision":
                collisions.append({"t_s": round(t, 3), **data})
            elif rec["topic"] == "detection":
                rp = data.get("rel_pose")
                if rp and rp.get("t"):
                    tt = rp["t"]
                    det_dists.append((t, (tt[0] ** 2 + tt[1] ** 2 + tt[2] ** 2) ** 0.5))

    # Propose slice windows around race start / first detection approach / collisions
    windows = []
    for rc in race_changes:
        if rc.get("started") and rc.get("race_start_boot_time_ms", -1) >= 0:
            windows.append({
                "label": "race_go",
                "start_s": max(0.0, rc["t_s"] - 1.0),
                "duration_s": 4.0,
                "note": f"race started/changed at t={rc['t_s']}s",
            })
            break
    if det_dists:
        # closest approach
        t_min, d_min = min(det_dists, key=lambda x: x[1])
        windows.append({
            "label": "closest_gate",
            "start_s": max(0.0, t_min - 1.5),
            "duration_s": 4.0,
            "note": f"min gate distance {d_min:.2f}m at t={t_min:.2f}s",
        })
    if collisions:
        c0 = collisions[0]
        windows.append({
            "label": "first_collision",
            "start_s": max(0.0, c0["t_s"] - 1.0),
            "duration_s": 3.0,
            "note": f"collision at t={c0['t_s']}s id={c0.get('collision_id')}",
        })
    # DSQ heuristic: early race_start with future timestamp vs boot
    for rc in race_changes:
        rs = rc.get("race_start_boot_time_ms")
        boot = rc.get("sim_boot_time_ms")
        if rs is not None and boot is not None and rs >= 0 and rs > boot:
            windows.append({
                "label": "countdown_future_start",
                "start_s": max(0.0, rc["t_s"] - 0.5),
                "duration_s": 5.0,
                "note": f"race_start={rs} > boot={boot} (delta {rs-boot} ms) at t={rc['t_s']}s",
            })
            break

    result = flight_dir / "result.json"
    result_data = json.loads(result.read_text(encoding="utf-8")) if result.exists() else {}
    return {
        "flight_id": flight_dir.name,
        "span_s": round((last - first) / 1e9, 3) if first and last else 0,
        "topics": dict(topics),
        "fsm": fsm,
        "race_changes": race_changes,
        "collisions": collisions,
        "result": result_data,
        "min_gate_distance_m": round(min(d for _, d in det_dists), 3) if det_dists else None,
        "detection_count": topics.get("detection", 0),
        "proposed_slices": windows,
        "vision_recording": str(flight_dir / "vision.aigprec")
        if (flight_dir / "vision.aigprec").exists() else None,
    }


def main() -> int:
    reports = []
    for d in sorted(LOGS.iterdir()):
        if (d / "flight.jsonl").exists():
            print(f"analyze {d.name}", flush=True)
            reports.append(analyze(d))
    OUT.write_text(json.dumps(reports, indent=2), encoding="utf-8")
    # Markdown summary
    md = ["# Flight event mining", "", f"Source logs: `{LOGS}`", ""]
    for r in reports:
        md.append(f"## `{r['flight_id']}`")
        md.append("")
        md.append(f"- span: {r['span_s']}s")
        md.append(f"- topics: `{r['topics']}`")
        md.append(f"- detections in log: {r['detection_count']}")
        md.append(f"- min gate distance: {r['min_gate_distance_m']}")
        if r.get("result"):
            md.append(f"- result: `{json.dumps(r['result'], separators=(',', ':'))}`")
        md.append("- race changes:")
        for rc in r["race_changes"][:12]:
            md.append(f"  - t={rc['t_s']}s started={rc['started']} gate={rc['active_gate_index']} "
                      f"rstart={rc['race_start_boot_time_ms']} boot={rc['sim_boot_time_ms']}")
        md.append("- FSM:")
        for ev in r["fsm"][:20]:
            md.append(f"  - t={ev['t_s']}s {ev['src']} -> {ev['dst']}")
        if len(r["fsm"]) > 20:
            md.append(f"  - ... {len(r['fsm'])-20} more")
        md.append("- proposed slices:")
        for w in r["proposed_slices"]:
            md.append(f"  - `{w['label']}` start_s={w['start_s']} dur={w['duration_s']} — {w['note']}")
        md.append("")
    (ROOT / "analysis" / "20260714-flight-events.md").write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
