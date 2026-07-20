#!/usr/bin/env python3
"""Inventory fixtures for D7 / N-ask analysis. Writes JSON report."""
import json
import math
import re
from pathlib import Path
from collections import defaultdict

OUT = Path(r"C:\Users\tsion\Projects\eni_dcim_github\analysis\_d7_inventory_out.json")
ROOTS = [
    Path(r"C:\Users\tsion\Projects\eni_dcim_github\fixtures"),
    Path(r"C:\Users\tsion\Projects\eni_dcim\fixtures"),
]
LOGS = Path(r"C:\Users\tsion\Projects\eni_dcim\logs")


def has_r2(name: str) -> bool:
    n = name.lower()
    return any(
        k in n
        for k in (
            "r2training", "r2-training", "phase3", "phase4", "phase5",
            "phase6", "132549", "milestone",
        )
    )


def range_from_t(t):
    return math.sqrt(sum(x * x for x in t))


def analyze_jsonl(path: Path) -> dict:
    if not path.exists():
        return {"missing": True}
    detections = []  # (t, r)
    closest_state = None
    det_count = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            topic = rec.get("topic")
            data = rec.get("data") or {}
            t = None
            if "mono_ns" in rec:
                # relative time unknown here; use ts from data if present
                pass
            ts = data.get("ts_ns")
            if topic == "state":
                gr = data.get("gate_rel")
                if isinstance(gr, dict) and gr.get("t"):
                    r = range_from_t(gr["t"])
                    if closest_state is None or r < closest_state:
                        closest_state = r
            elif topic == "detection" and data.get("rel_pose"):
                rp = data["rel_pose"]
                tvec = rp.get("t")
                if tvec:
                    r = range_from_t(tvec)
                    det_count += 1
                    # use detection count as pseudo-time bucket index fallback
                    detections.append((det_count, r))

    # Re-parse with mono_ns for time windows
    detections = []
    t0 = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("topic") != "detection":
                continue
            data = rec.get("data") or {}
            rp = data.get("rel_pose")
            if not rp or not rp.get("t"):
                continue
            mono = rec.get("mono_ns")
            if mono is None:
                continue
            if t0 is None:
                t0 = mono
            t_s = (mono - t0) / 1e9
            r = range_from_t(rp["t"])
            detections.append((t_s, r))

    multi = 0
    if detections:
        buckets = defaultdict(list)
        for t, r in detections:
            buckets[round(t / 0.2) * 0.2].append(r)
        for rs in buckets.values():
            if any(r < 2.0 for r in rs) and any(3.0 <= r <= 12.0 for r in rs):
                multi += 1

    return {
        "closest_state_r": closest_state,
        "multi_gate_windows": multi,
        "detection_count": len(detections),
    }


def load_summary_metrics(d: Path) -> list[dict]:
    sp = d / "summary.json"
    if not sp.exists():
        return []
    with open(sp, encoding="utf-8") as f:
        s = json.load(f)
    out = []
    for m in s.get("metrics", []):
        fid = m.get("flight_id")
        res = m.get("result") or {}
        cd = m.get("closest_direct") or {}
        cs = m.get("closest_state") or {}
        out.append(
            {
                "id": fid,
                "gates": res.get("gates_passed"),
                "clips": res.get("gate_clips"),
                "env": res.get("env_hits"),
                "closest_direct_r": cd.get("range_m"),
                "closest_state_r": cs.get("range_m"),
                "phase_sequence": m.get("phase_sequence"),
            }
        )
    return out


def slice_map(d: Path) -> dict[str, list[str]]:
    m = defaultdict(list)
    for s in d.glob("*takeoff_to_end*.aigprec"):
        prefix = s.name.split("_takeoff")[0]
        m[prefix].append(s.name)
    return dict(m)


def main():
    seen = set()
    fixtures = []
    for root in ROOTS:
        if not root.exists():
            continue
        for d in sorted(root.iterdir()):
            if not d.is_dir() or d.name in seen or not has_r2(d.name):
                continue
            seen.add(d.name)
            sm = load_summary_metrics(d)
            slices = slice_map(d)
            flights = []
            if sm:
                for fl in sm:
                    pref = fl["id"]
                    fl["slice"] = pref in slices or any(
                        pref.startswith(k) or k.startswith(pref.split("-")[0])
                        for k in slices
                    )
                    fl["slice_files"] = []
                    for k, v in slices.items():
                        if pref.startswith(k) or k.startswith(pref.split("-")[0]):
                            fl["slice_files"].extend(v)
                    fj = d / f"{pref}-flight.jsonl"
                    if fj.exists():
                        ja = analyze_jsonl(fj)
                        fl["multi_gate_windows"] = ja.get("multi_gate_windows", 0)
                    flights.append(fl)
            else:
                for rp in sorted(d.glob("*-result.json")):
                    with open(rp, encoding="utf-8") as f:
                        res = json.load(f)
                    fid = rp.stem.replace("-result", "")
                    fj = d / f"{fid}-flight.jsonl"
                    ja = analyze_jsonl(fj)
                    cd_r = None
                    # quick closest from jsonl state not reimplemented
                    gates = res.get("gates_passed")
                    clips = res.get("gate_clips", 0)
                    flights.append(
                        {
                            "id": fid,
                            "gates": gates,
                            "clips": clips,
                            "env": res.get("env_hits"),
                            "closest_direct_r": None,
                            "closest_state_r": ja.get("closest_state_r"),
                            "multi_gate_windows": ja.get("multi_gate_windows", 0),
                            "slice": fid in slices or any(
                                fid.startswith(k) for k in slices
                            ),
                            "slice_files": slices.get(fid, []),
                        }
                    )
            interesting = [
                f
                for f in flights
                if (f.get("gates") or 0) >= 1
                or (f.get("closest_direct_r") or 99) < 2.0
                or (f.get("closest_state_r") or 99) < 2.0
                or (f.get("clips") or 0) >= 3
            ]
            if interesting or slices:
                fixtures.append(
                    {
                        "fixture": d.name,
                        "path": str(d),
                        "flights": interesting or flights,
                        "slice_count": sum(len(v) for v in slices.values()),
                    }
                )

    # recent logs (flight dirs from last 2 days pattern)
    log_dirs = []
    if LOGS.exists():
        for p in sorted(LOGS.iterdir(), key=lambda x: x.name, reverse=True)[:40]:
            if p.is_dir() and (p / "flight.jsonl").exists():
                rp = p / "result.json"
                gates = None
                if rp.exists():
                    with open(rp, encoding="utf-8") as f:
                        gates = json.load(f).get("gates_passed")
                log_dirs.append({"id": p.name, "gates_passed": gates})

    OUT.write_text(json.dumps({"fixtures": fixtures, "recent_logs": log_dirs}, indent=2))
    print(f"Wrote {OUT} ({len(fixtures)} fixtures)")


if __name__ == "__main__":
    main()
