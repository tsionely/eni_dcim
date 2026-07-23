"""Compare the final approach of the T2-R1 stall with recorded R1 passes.

Run from the repository root with the repository virtualenv:
  python analysis/2026-07-23-crossing-autopsy/run_crossing_autopsy.py
"""
from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
CASES = {
    "stall_t2r1_B_run2": ("STALL", "fixtures/20260723T203357-raceprep-t2r1-B-run2"),
    "pass_r1k_off_run3": ("PASS", "fixtures/20260723T191736-raceprep-r1k-off-run3"),
    "pass_r1_alt_B_run2": ("PASS", "fixtures/20260721T193502-raceprep-r1-alt-B-run2"),
    "pass_r1_alt_A_run5": ("PASS", "fixtures/20260721T193902-raceprep-r1-alt-A-run5"),
    "pass_r1_alt_B_run10": ("PASS", "fixtures/20260721T194532-raceprep-r1-alt-B-run10"),
}
TIMELINE_COLUMNS = [
    "case", "cohort", "t_rel_closest_s", "mono_s", "phase", "v_body_x",
    "v_body_y", "v_body_z", "detection_present", "detection_certified",
    "detection_range_m", "detection_z_m", "state_range_m", "state_z_m",
    "state_age_s", "state_true_dz_m", "lateral_m", "events",
]


def finite(value):
    return value is not None and isinstance(value, (int, float)) and math.isfinite(value)


def vec3(value):
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return None
    try:
        return tuple(float(value[i]) for i in range(3))
    except (TypeError, ValueError):
        return None


def norm(v):
    return math.sqrt(sum(x * x for x in v)) if v else None


def load_events(folder):
    log = next(folder.glob("*flight.jsonl"), None)
    if log is None:
        raise FileNotFoundError(f"No flight log in {folder}")
    events = []
    with log.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                row = json.loads(line)
                row["_mono"] = int(row["mono_ns"])
                events.append(row)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue
    return sorted(events, key=lambda row: row["_mono"]), log


def quat_rotate(q, v):
    """Rotate v by unit quaternion q=[w,x,y,z]."""
    if not q or len(q) != 4:
        return v
    w, x, y, z = (float(a) for a in q)
    # q * (0,v) * q_conjugate, expanded.
    tx = 2.0 * (y * v[2] - z * v[1])
    ty = 2.0 * (z * v[0] - x * v[2])
    tz = 2.0 * (x * v[1] - y * v[0])
    return (
        v[0] + w * tx + (y * tz - z * ty),
        v[1] + w * ty + (z * tx - x * tz),
        v[2] + w * tz + (x * ty - y * tx),
    )


def true_world_dz(gate, state):
    """Reproduce the logged-state vertical diagnostic without imports."""
    v = vec3(gate)
    q = state.get("q_att") if state else None
    if not v or not isinstance(q, list) or len(q) != 4:
        return None
    # level_roll/pitch are the rest-frame attitude removed by the filter.
    # Applying q_att and then the rest tilt gives physical world vertical.
    roll = float(state.get("level_roll", 0.0))
    pitch = float(state.get("level_pitch", 0.0))
    cp, sp, cr, sr = math.cos(pitch / 2), math.sin(pitch / 2), math.cos(roll / 2), math.sin(roll / 2)
    level_q = (cp * cr, -cp * sr, -sp * cr, sp * sr)
    return quat_rotate(level_q, quat_rotate(q, v))[2]


def extract_samples(events):
    samples = []
    for row in events:
        data = row.get("data", {})
        topic = row.get("topic")
        if topic == "detection":
            pose = (data.get("rel_pose") or {}).get("t")
            v = vec3(pose)
            if v:
                samples.append({
                    "mono": row["_mono"], "kind": "detection", "range": norm(v),
                    "z": v[2], "lateral": v[0], "certified": data.get("cert_status") == "certified",
                    "data": data,
                })
        elif topic == "state":
            v = vec3((data.get("gate_rel") or {}).get("t"))
            if v:
                samples.append({
                    "mono": row["_mono"], "kind": "state", "range": norm(v), "z": v[2],
                    "lateral": v[0], "age": data.get("gate_rel_age_s"),
                    "true_dz": true_world_dz(v, data), "data": data,
                })
    return samples


def last_before(rows, mono):
    prior = [r for r in rows if r["_mono"] <= mono]
    return prior[-1] if prior else None


def detect_gate_pass(events):
    """Return only observed race-counter increments, not routine race status."""
    found = []
    previous_index = None
    previous_last = None
    for row in events:
        data = row.get("data", {})
        if row.get("topic") != "race":
            continue
        index = data.get("active_gate_index")
        last = data.get("last_gate_race_time")
        incremented = (
            finite(index) and previous_index is not None and index > previous_index
        ) or (
            finite(last) and last >= 0 and (previous_last is None or last != previous_last)
        )
        if incremented:
            found.append({"mono": row["_mono"], "topic": "race", "data": data})
        if finite(index):
            previous_index = index
        if finite(last):
            previous_last = last
    return found


def transitions(setpoints, start, end):
    relevant = [r for r in setpoints if start <= r["_mono"] <= end]
    transitions = []
    previous = None
    for row in relevant:
        phase = row["data"].get("phase")
        if phase != previous:
            transitions.append((row["_mono"], previous, phase))
            previous = phase
    return transitions


def analyze_case(name, cohort, relative):
    folder = ROOT / relative
    events, log = load_events(folder)
    start_mono = events[0]["_mono"]
    samples = extract_samples(events)
    detections = [s for s in samples if s["kind"] == "detection" and s["certified"]]
    states_with_gate = [s for s in samples if s["kind"] == "state"]
    pass_events = detect_gate_pass(events)
    # A passing flight continues toward the next gate. Anchor the autopsy to
    # gate 1 by selecting only samples near its first counter increment.
    cutoff = pass_events[0]["mono"] + int(.6e9) if pass_events else None
    candidates = detections + states_with_gate
    if cutoff is not None:
        candidates = [s for s in candidates if s["mono"] <= cutoff]
    # The planner's terminal geometry is range-along-gate-normal/t[2], not
    # Euclidean camera distance. Select the smallest still-ahead t[2], using
    # state after the ring disappears (direct detections cannot see through
    # the aperture at the true closest point).
    ahead = [s for s in candidates if s["z"] > 0]
    closest = min(ahead or candidates, key=lambda s: abs(s["z"]))
    closest_mono = closest["mono"]
    window_start = closest_mono - int(3e9)
    window_end = closest_mono + int(.5e9)
    states = [r for r in events if r.get("topic") == "state"]
    setpoints = [r for r in events if r.get("topic") == "setpoint"]
    collisions = [r for r in events if r.get("topic") == "collision"]
    planner_events = [r for r in events if r.get("topic") not in {"imu", "actuator", "frame", "detection", "state", "setpoint"}]

    # Fixed 100ms bins: closest detection in-bin and last state/setpoint before bin.
    timeline = []
    for mono in range(window_start, window_end + 1, int(.1e9)):
        state_row = last_before(states, mono)
        sp_row = last_before(setpoints, mono)
        state = state_row.get("data", {}) if state_row else {}
        sp = sp_row.get("data", {}) if sp_row else {}
        bin_dets = [d for d in detections if mono <= d["mono"] < mono + int(.1e9)]
        det = min(bin_dets, key=lambda d: d["range"]) if bin_dets else None
        gate = vec3((state.get("gate_rel") or {}).get("t"))
        state_range = norm(gate)
        v_body = vec3(sp.get("v_body")) or (None, None, None)
        event_text = []
        for r in collisions + planner_events:
            if mono <= r["_mono"] < mono + int(.1e9):
                event_text.append(f"{r.get('topic')}:{r.get('data')}")
        timeline.append({
            "case": name, "cohort": cohort, "t_rel_closest_s": round((mono - closest_mono) / 1e9, 3),
            "mono_s": round((mono - start_mono) / 1e9, 3), "phase": sp.get("phase"),
            "v_body_x": v_body[0], "v_body_y": v_body[1], "v_body_z": v_body[2],
            "detection_present": bool(det), "detection_certified": bool(det),
            "detection_range_m": det["range"] if det else None, "detection_z_m": det["z"] if det else None,
            "state_range_m": state_range, "state_z_m": gate[2] if gate else None,
            "state_age_s": state.get("gate_rel_age_s"), "state_true_dz_m": true_world_dz(gate, state) if gate else None,
            "lateral_m": (det or {"lateral": gate[0] if gate else None})["lateral"],
            "events": " | ".join(event_text),
        })

    tr = transitions(setpoints, window_start, window_end)
    phase_at_min = last_before(setpoints, closest_mono)
    one_second = [r for r in timeline if -1.0 <= r["t_rel_closest_s"] <= 0]
    half_second = [r for r in timeline if -.5 <= r["t_rel_closest_s"] <= 0]
    det_last = [d for d in detections if closest_mono - int(1e9) <= d["mono"] <= closest_mono]
    # Regression over direct PnP ranges in last second (positive means separating).
    if len(det_last) >= 2:
        x = [(d["mono"] - closest_mono) / 1e9 for d in det_last]
        y = [d["range"] for d in det_last]
        xbar, ybar = mean(x), mean(y)
        denom = sum((a - xbar) ** 2 for a in x)
        range_rate = sum((a - xbar) * (b - ybar) for a, b in zip(x, y)) / denom if denom else None
    else:
        range_rate = None
    closest_state = last_before(states, closest_mono)
    closest_state_data = closest_state.get("data", {}) if closest_state else {}
    closest_gate = vec3((closest_state_data.get("gate_rel") or {}).get("t"))
    phase_transitions = [
        {"t_rel_s": round((m - closest_mono) / 1e9, 3), "from": old, "to": new}
        for m, old, new in tr
    ]
    commit_entries = [t for t in phase_transitions if t["to"] == "commit" and t["from"] != "commit"]
    commit_exits = [t for t in phase_transitions if t["from"] == "commit" and t["to"] != "commit"]
    first_exit = commit_exits[0]["t_rel_s"] if commit_exits else None
    retreat_before_min = any(t["to"] in {"retreat", "recover"} and t["t_rel_s"] < 0 for t in phase_transitions)
    post = [d["range"] for d in detections if closest_mono < d["mono"] <= closest_mono + int(.5e9)]
    summary = {
        "case": name, "cohort": cohort, "fixture": relative, "log": str(log.relative_to(ROOT)),
        "closest_t_s": round((closest_mono - start_mono) / 1e9, 3),
        "closest_source": closest["kind"], "min_range_m": closest["range"], "min_z_m": closest["z"],
        "lateral_at_min_m": closest["lateral"],
        "true_dz_at_min_m": (closest.get("true_dz") if closest["kind"] == "state"
                              else true_world_dz(closest["data"].get("rel_pose", {}).get("t"),
                                                 closest_state_data)),
        "phase_at_min": phase_at_min.get("data", {}).get("phase") if phase_at_min else None,
        "vx_forward_at_min_mps": (vec3(phase_at_min.get("data", {}).get("v_body")) or (None,))[0] if phase_at_min else None,
        "vz_at_min_mps": (vec3(phase_at_min.get("data", {}).get("v_body")) or (None, None, None))[2] if phase_at_min else None,
        "mean_vx_last_1s_mps": mean([r["v_body_x"] for r in one_second if finite(r["v_body_x"])]) if any(finite(r["v_body_x"]) for r in one_second) else None,
        "time_in_commit_s": sum(.1 for r in timeline if r["phase"] == "commit"),
        "n_commit_entries": len(commit_entries), "n_commit_exits": len(commit_exits),
        "commit_active_at_closest": phase_at_min.get("data", {}).get("phase") == "commit" if phase_at_min else False,
        "first_commit_exit_rel_s": first_exit, "retreat_or_recover_before_min": retreat_before_min,
        "detection_bin_fraction_last_1s": sum(r["detection_present"] for r in one_second) / len(one_second) if one_second else None,
        "detection_bin_fraction_last_0_5s": sum(r["detection_present"] for r in half_second) / len(half_second) if half_second else None,
        "range_rate_last_1s_mps": range_rate,
        "inside_abort_min_while_commit": any(
            r["phase"] == "commit" and finite(r["state_range_m"]) and r["state_range_m"] < .8 for r in timeline
        ),
        "post_closest_detection_range_increases": bool(post and min(post) > closest["range"]),
        "gate_pass_events": pass_events,
        "gate_pass_times_rel_to_closest_s": [
            round((event["mono"] - closest_mono) / 1e9, 3) for event in pass_events
        ],
        "phase_transitions": phase_transitions,
    }
    return summary, timeline


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    summaries, all_rows = [], []
    for name, (cohort, fixture) in CASES.items():
        summary, timeline = analyze_case(name, cohort, fixture)
        summaries.append(summary)
        all_rows.extend(timeline)
        with (OUT / f"per_flight_timeline_{name}.csv").open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=TIMELINE_COLUMNS)
            writer.writeheader()
            writer.writerows(timeline)
    with (OUT / "comparison.csv").open("w", newline="", encoding="utf-8") as fh:
        fields = [key for key in summaries[0] if key not in {"gate_pass_events", "phase_transitions"}]
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows([{key: row[key] for key in fields} for row in summaries])
    with (OUT / "summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summaries, fh, indent=2, allow_nan=False)
    print(json.dumps(summaries, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
