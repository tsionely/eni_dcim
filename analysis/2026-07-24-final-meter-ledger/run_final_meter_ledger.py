"""Build control-tick final-meter ledgers for the three ADVISORY_36 fixtures.

Run from the repository root:
  C:/Users/tsion/Projects/eni_dcim/.venv/Scripts/python.exe analysis/2026-07-24-final-meter-ledger/run_final_meter_ledger.py
"""
from __future__ import annotations

import csv
import json
import math
from bisect import bisect_right
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
CASES = {
    "stall_t2r1_B_run2": ("STALL", "fixtures/20260723T203357-raceprep-t2r1-B-run2"),
    "pass_r1k_off_run3": ("PASS", "fixtures/20260723T191736-raceprep-r1k-off-run3"),
    "stall_r1j3390_val_run2": ("STALL", "fixtures/20260723T171931-raceprep-r1j3390-val-run2"),
}
LEDGER_COLUMNS = [
    "t_rel_s", "signed_plane_m", "active_gate_index", "lock_present",
    "det_present", "det_certified", "det_confidence", "det_class",
    "gate_rel_age_s", "commit_predicate_vector",
    "range_m", "lateral_m", "true_world_dz_m", "opening_off_m",
    "abort_corridor_breach_proxy", "margin_lateral_m", "margin_vertical_m",
    "last_full_quad_signed_plane_m",
    "phase", "v_cmd_body_xyz", "yaw_rate", "blind_hold", "speed_cap_mps",
    "v_est_body_xyz", "phase_transition", "exit_cause", "proxy_exit_cause",
    "collision_impulse",
]
TRACE_COLUMNS = [
    "t_rel_s", "signed_plane_m", "v_cmd_along_plane", "v_est_along_plane",
    "v_cmd_lat", "v_est_lat", "v_cmd_vert", "v_est_vert",
]
UNLOGGED = [
    "commit_predicate_vector (per-conjunct booleans and sustain counter)",
    "speed_cap_mps and binding-rule source",
    "planner exit_cause enum (EXPIRED/DETECTION_LOST/CORRIDOR/MIN_DIST/etc.)",
    "logged approach-axis / gate-plane orientation convention",
    "logged opening dimensions and aim-up target",
]


def finite(x):
    return isinstance(x, (int, float)) and math.isfinite(x)


def vec3(x):
    if not isinstance(x, (list, tuple)) or len(x) < 3:
        return None
    try:
        v = tuple(float(x[i]) for i in range(3))
    except (TypeError, ValueError):
        return None
    return v if all(math.isfinite(a) for a in v) else None


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def norm(v):
    return math.sqrt(dot(v, v)) if v else None


def unit(v):
    length = norm(v)
    return tuple(x / length for x in v) if length and length > 1e-9 else None


def signed_plane(t, normal):
    """Return forward-positive gate-plane distance, falling back to camera z.

    Logged PnP normals point camera-ward in these fixtures, so a unit normal
    with negative camera-z is reversed before dotting; this makes a facing
    plane agree with the required t[2] convention (positive before passage).
    """
    t = vec3(t)
    raw_n = vec3(normal)
    raw_len = norm(raw_n)
    if not t or not raw_n or not (0.8 <= raw_len <= 1.2):
        return t[2] if t else None
    n = unit(raw_n)
    if n[2] < 0:
        n = tuple(-x for x in n)
    return dot(t, n)


def quat_rotate(q, v):
    if not isinstance(q, (list, tuple)) or len(q) != 4 or not vec3(v):
        return v
    try:
        w, x, y, z = (float(a) for a in q)
    except (TypeError, ValueError):
        return v
    tx = 2.0 * (y * v[2] - z * v[1])
    ty = 2.0 * (z * v[0] - x * v[2])
    tz = 2.0 * (x * v[1] - y * v[0])
    return (v[0] + w * tx + y * tz - z * ty,
            v[1] + w * ty + z * tx - x * tz,
            v[2] + w * tz + x * ty - y * tx)


def quat_inverse_rotate(q, v):
    if not isinstance(q, (list, tuple)) or len(q) != 4:
        return v
    return quat_rotate((q[0], -q[1], -q[2], -q[3]), v)


def true_world_dz(gate, state):
    gate = vec3(gate)
    q = state.get("q_att") if state else None
    if not gate or not isinstance(q, list) or len(q) != 4:
        return None
    roll = float(state.get("level_roll", 0.0))
    pitch = float(state.get("level_pitch", 0.0))
    cp, sp = math.cos(pitch / 2), math.sin(pitch / 2)
    cr, sr = math.cos(roll / 2), math.sin(roll / 2)
    level_q = (cp * cr, -cp * sr, -sp * cr, sp * sr)
    return quat_rotate(level_q, quat_rotate(q, gate))[2]


def body_velocity(state):
    v = vec3(state.get("v_world") if state else None)
    q = state.get("q_att") if state else None
    return quat_inverse_rotate(q, v) if v and q else None


def load(folder):
    rows = []
    with (folder / "flight.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            try:
                row = json.loads(line)
                row["_mono"] = int(row["mono_ns"])
                rows.append(row)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                pass
    return sorted(rows, key=lambda r: r["_mono"])


def value_at(rows, monos, mono, max_age_ns=20_000_000):
    i = bisect_right(monos, mono) - 1
    if i >= 0 and mono - monos[i] <= max_age_ns:
        return rows[i]
    return None


def params_at(params, path, default):
    node = params
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node if finite(node) else default


def classify_detection(det):
    if not det:
        return False, False, None, "none"
    data = det["data"]
    pose = (data.get("rel_pose") or {}).get("t")
    present = vec3(pose) is not None
    certified = present and data.get("cert_status") == "certified"
    corners = data.get("corners_px")
    return present, certified, data.get("confidence"), (
        "FULL_QUAD" if certified and isinstance(corners, list) and len(corners) >= 4
        else "partial" if present else "none"
    )


def race_increments(races):
    out, last_index, last_time = [], None, None
    for r in races:
        index = r["data"].get("active_gate_index")
        gate_time = r["data"].get("last_gate_race_time")
        if (finite(index) and last_index is not None and index > last_index) or (
            finite(gate_time) and gate_time >= 0 and (last_time is None or gate_time != last_time)
        ):
            out.append(r["_mono"])
        if finite(index):
            last_index = index
        if finite(gate_time):
            last_time = gate_time
    return out


def make_ticks(rows, params):
    topics = {name: [r for r in rows if r.get("topic") == name]
              for name in ("state", "setpoint", "detection", "race", "collision")}
    monos = {name: [r["_mono"] for r in values] for name, values in topics.items()}
    first = rows[0]["_mono"]
    active_gate = None
    last_full_s = None
    ticks = []
    for sp in topics["setpoint"]:
        mono, spd = sp["_mono"], sp["data"]
        state_row = value_at(topics["state"], monos["state"], mono)
        det_row = value_at(topics["detection"], monos["detection"], mono)
        race_row = value_at(topics["race"], monos["race"], mono, 300_000_000)
        if race_row and finite(race_row["data"].get("active_gate_index")):
            active_gate = int(race_row["data"]["active_gate_index"])
        state = state_row["data"] if state_row else {}
        det = det_row["data"] if det_row else {}
        gate_rel = state.get("gate_rel") or {}
        state_t, det_t = vec3(gate_rel.get("t")), vec3((det.get("rel_pose") or {}).get("t"))
        state_n, det_n = vec3(gate_rel.get("normal")), vec3((det.get("rel_pose") or {}).get("normal"))
        lock = state_t is not None
        t, n, source = (state_t, state_n, "state") if lock else (det_t, det_n, "detection")
        s = signed_plane(t, n) if t else None
        det_present, certified, confidence, det_class = classify_detection(det_row)
        if det_class == "FULL_QUAD" and s is not None:
            last_full_s = s
        collision = value_at(topics["collision"], monos["collision"], mono, 15_000_000)
        impulse = collision["data"].get("impulse") if collision else None
        cmd = vec3(spd.get("v_body"))
        est = body_velocity(state)
        dz = true_world_dz(t, state) if t else None
        lateral = t[0] if t else None
        off = math.hypot(lateral, dz) if finite(lateral) and finite(dz) else None
        rng = norm(t)
        age = state.get("gate_rel_age_s") if lock else None
        ticks.append({
            "mono": mono, "mono_s": (mono - first) / 1e9, "phase": spd.get("phase"),
            "signed_plane_m": s, "active_gate_index": active_gate, "lock_present": lock,
            "det_present": det_present, "det_certified": certified,
            "det_confidence": confidence, "det_class": det_class,
            "gate_rel_age_s": age, "range_m": rng, "lateral_m": lateral,
            "true_world_dz_m": dz, "opening_off_m": off,
            "last_full_quad_signed_plane_m": last_full_s, "v_cmd": cmd,
            "v_est": est, "yaw_rate": spd.get("yaw_rate"),
            "blind_hold": spd.get("blind_hold"), "normal": n, "collision_impulse": impulse,
            "source": source,
        })
    return ticks, topics, race_increments(topics["race"])


def segments(ticks):
    qualifying = []
    for tick in ticks:
        near = finite(tick["range_m"]) and tick["range_m"] < 3.0
        phase = str(tick["phase"] or "").lower()
        qualifying.append(near or phase in {"approach", "align", "commit"})
    result, start = [], None
    for i, yes in enumerate(qualifying + [False]):
        if yes and start is None:
            start = i
        elif not yes and start is not None:
            if i - start >= 2:
                result.append((start, i - 1))
            start = None
    return result


def locate_alignment(ticks, start, end):
    for i in range(max(start + 1, 1), end + 1):
        before, now = ticks[i - 1]["signed_plane_m"], ticks[i]["signed_plane_m"]
        if finite(before) and finite(now) and before > 1.0 >= now:
            return i
    return None


def phase_transition(prev, now):
    return f"{prev}→{now}" if prev is not None and now != prev else ""


def proxy_exit(tick, passed):
    phase = str(tick["phase"] or "").lower()
    if passed:
        return "PASSED"
    if finite(tick["collision_impulse"]):
        return "COLLISION/HARD_SAFETY"
    if phase in {"retreat", "recover"}:
        return phase.upper()
    if finite(tick["signed_plane_m"]) and tick["signed_plane_m"] < -0.4:
        return "GEOMETRIC_BEHIND"
    return "NONE"


def slice_ledger(ticks, start, end, pass_monos, params):
    aligned = locate_alignment(ticks, start, end)
    if aligned is None:
        return None
    abort_min = params_at(params, ("planner", "commit", "abort_min_dist_m"), 0.8)
    off_limit = params_at(params, ("planner", "commit", "abort_offset_m"), 0.45)
    blind = params_at(params, ("planner", "commit", "entry_max_age_s"), 0.6)
    out, previous_phase = [], None
    for i in range(aligned, end + 1):
        tick = dict(ticks[i])
        prior = out[-1] if out else None
        passed = any((prior["mono"] if prior else tick["mono"]) < p <= tick["mono"] for p in pass_monos)
        tick["phase_transition"] = phase_transition(previous_phase, tick["phase"])
        tick["proxy_exit_cause"] = proxy_exit(tick, passed)
        tick["abort_corridor_breach_proxy"] = bool(
            finite(tick["range_m"]) and abort_min < tick["range_m"] < 1.5 and
            finite(tick["opening_off_m"]) and tick["opening_off_m"] > off_limit and
            finite(tick["gate_rel_age_s"]) and tick["gate_rel_age_s"] <= blind
        )
        out.append(tick)
        previous_phase = tick["phase"]
        if tick["proxy_exit_cause"] != "NONE" or (
            finite(tick["signed_plane_m"]) and tick["signed_plane_m"] < -0.5
        ):
            break
    return out


def approach_axis(tick):
    n = unit(tick["normal"])
    if n:
        return tuple(-x for x in n)  # camera/body direction toward the gate plane
    return (0.0, 0.0, 1.0)


def along(v, axis):
    return dot(v, axis) if v and axis else None


def trace_rows(ledger):
    rows = []
    for tick in ledger:
        axis = approach_axis(tick)
        cmd, est = tick["v_cmd"], tick["v_est"]
        rows.append({
            "t_rel_s": round((tick["mono"] - ledger[0]["mono"]) / 1e9, 4),
            "signed_plane_m": tick["signed_plane_m"],
            "v_cmd_along_plane": along(cmd, axis),
            "v_est_along_plane": along(est, axis),
            "v_cmd_lat": cmd[0] if cmd else None, "v_est_lat": est[0] if est else None,
            "v_cmd_vert": cmd[2] if cmd else None, "v_est_vert": est[2] if est else None,
        })
    return rows


def nearest_by_s(ledger, target):
    candidates = [x for x in ledger if finite(x["signed_plane_m"])]
    return min(candidates, key=lambda x: abs(x["signed_plane_m"] - target)) if candidates else None


def angle_xy(v, axis):
    if not v or not axis:
        return None
    a, b = (v[0], v[1]), (axis[0], axis[1])
    na, nb = math.hypot(*a), math.hypot(*b)
    if na < 1e-6 or nb < 1e-6:
        return None
    return math.degrees(math.acos(max(-1.0, min(1.0, (a[0] * b[0] + a[1] * b[1]) / (na * nb)))))


def metrics(ledger, traces, pass_monos):
    closest = min((x for x in ledger if finite(x["signed_plane_m"])),
                  key=lambda x: abs(x["signed_plane_m"]))
    samples = {"s_plus_1_0": nearest_by_s(ledger, 1.0),
               "s_plus_0_5": nearest_by_s(ledger, 0.5),
               "closest": closest,
               "last_certified_detection": next((x for x in reversed(ledger)
                                                 if x["det_certified"]), None)}
    margins = {}
    for name, tick in samples.items():
        if tick:
            margins[name] = {
                "signed_plane_m": tick["signed_plane_m"], "lateral_m": tick["lateral_m"],
                "true_world_dz_m": tick["true_world_dz_m"], "opening_off_m": tick["opening_off_m"],
                "margin_lateral_m": 0.8 - abs(tick["lateral_m"]) if finite(tick["lateral_m"]) else None,
                "margin_vertical_m": 0.8 - abs(tick["true_world_dz_m"]) if finite(tick["true_world_dz_m"]) else None,
            }
    ratios = [r["v_est_along_plane"] / r["v_cmd_along_plane"] for r in traces
              if finite(r["v_cmd_along_plane"]) and r["v_cmd_along_plane"] > .3 and
              finite(r["v_est_along_plane"]) and 0 < r["signed_plane_m"] <= 1.0]
    approach_rows = [r for r in traces if finite(r["signed_plane_m"]) and 0 < r["signed_plane_m"] <= 1.0]
    final = [r for r in traces if r["t_rel_s"] >= traces[-1]["t_rel_s"] - .5]
    s_delta = final[-1]["signed_plane_m"] - final[0]["signed_plane_m"] if len(final) >= 2 else None
    at_one, at_close = nearest_by_s(ledger, 1.0), closest
    a1, ac = angle_xy(at_one["v_cmd"], approach_axis(at_one)), angle_xy(at_close["v_cmd"], approach_axis(at_close))
    early = [r for r in approach_rows if r["signed_plane_m"] > .2 and finite(r["v_cmd_along_plane"])]
    high = max((r["v_cmd_along_plane"] for r in early), default=None)
    withdrew = bool(high and high > 0 and any(r["v_cmd_along_plane"] < .5 * high for r in early))
    # Race telemetry is only 4 Hz while the ledger stops at a retreat/recover.
    # Attribute the next counter event within one second to this terminal
    # approach, retaining the last plane estimate before that event.
    nearby_pass = next((p for p in pass_monos
                        if ledger[0]["mono"] < p <= ledger[-1]["mono"] + 1_000_000_000), None)
    before_pass = max((t for t in ledger if nearby_pass and t["mono"] <= nearby_pass),
                      key=lambda t: t["mono"], default=None)
    premature = bool(nearby_pass and before_pass and finite(before_pass["signed_plane_m"]) and
                     before_pass["signed_plane_m"] > .2)
    return {
        "s_min_m": closest["signed_plane_m"], "closest_phase": closest["phase"],
        "margins": margins,
        "tracking_ratio": {
            "mean_rho": mean(ratios) if ratios else None, "median_rho": median(ratios) if ratios else None,
            "fraction_rho_lt_0_5": sum(x < .5 for x in ratios) / len(ratios) if ratios else None,
            "n_ticks": len(ratios),
        },
        "closing": {
            "delta_s_final_0_5s_m": s_delta, "cmd_along_at_closest_mps": traces[-1]["v_cmd_along_plane"],
            "cmd_withdrew_before_closest": withdrew,
        },
        "vector_rotation": {
            "angle_deg_at_s_1m": a1, "angle_deg_at_closest": ac,
            "growth_deg": ac - a1 if finite(a1) and finite(ac) else None,
        },
        "scoring_order_check": {
            "active_gate_increment_while_s_gt_0_2": premature,
            "counter_increment_mono_ns": nearby_pass,
            "last_signed_plane_before_increment_m": before_pass["signed_plane_m"] if before_pass else None,
        },
    }


def classify(case_cohort, ledger, met):
    pass_seen = (any(t["proxy_exit_cause"] == "PASSED" for t in ledger) or
                 met["scoring_order_check"]["counter_increment_mono_ns"] is not None)
    smin, rho = met["s_min_m"], met["tracking_ratio"]["mean_rho"]
    closing = met["closing"]
    phases = [str(t["phase"] or "").lower() for t in ledger]
    cmd_along = [along(t["v_cmd"], approach_axis(t)) for t in ledger]
    command_high = sum(x >= .8 for x in cmd_along if finite(x)) >= max(2, len([x for x in cmd_along if finite(x)]) // 2)
    rot = met["vector_rotation"]["growth_deg"]
    if pass_seen and smin <= 0:
        return "PASS", f"gate counter incremented after plane crossing; s_min={smin:.3f} m."
    if met["scoring_order_check"]["active_gate_increment_while_s_gt_0_2"]:
        return "D scoring-order", f"gate index incremented before crossing (s_min={smin:.3f} m)."
    if (closing["cmd_withdrew_before_closest"] or any(p in {"retreat", "recover"} for p in phases)) and (
        rho is None or rho >= .5
    ):
        return "A command-withdrawal", (
            f"withdraw={closing['cmd_withdrew_before_closest']}; rho={rho}; "
            f"phase tail={phases[-1]}; s_min={smin:.3f} m."
        )
    if command_high and rho is not None and rho < .5:
        return "B plant-non-tracking", f"command stayed >=0.8 m/s for most ticks; rho={rho:.3f}; s_min={smin:.3f} m."
    if rot is not None and rot > 25 and not any(p in {"retreat", "recover"} for p in phases):
        return "C vector-rotation", f"command axis angle grew {rot:.1f}°; rho={rho}; s_min={smin:.3f} m."
    # Required non-pass best-supported class; no false precision when a ledger
    # misses an observable discriminator.
    return "A command-withdrawal (proxy)", (
        f"no logged exit enum/predicate vector; final phase={phases[-1]}, "
        f"withdraw={closing['cmd_withdrew_before_closest']}, rho={rho}, s_min={smin:.3f} m."
    )


def csv_write(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def ledger_rows(ledger):
    rows = []
    for t in ledger:
        rows.append({
            "t_rel_s": round((t["mono"] - ledger[0]["mono"]) / 1e9, 4),
            "signed_plane_m": t["signed_plane_m"], "active_gate_index": t["active_gate_index"],
            "lock_present": t["lock_present"], "det_present": t["det_present"],
            "det_certified": t["det_certified"], "det_confidence": t["det_confidence"],
            "det_class": t["det_class"], "gate_rel_age_s": t["gate_rel_age_s"],
            "commit_predicate_vector": "UNLOGGED", "range_m": t["range_m"],
            "lateral_m": t["lateral_m"], "true_world_dz_m": t["true_world_dz_m"],
            "opening_off_m": t["opening_off_m"],
            "abort_corridor_breach_proxy": t["abort_corridor_breach_proxy"],
            "margin_lateral_m": .8 - abs(t["lateral_m"]) if finite(t["lateral_m"]) else None,
            "margin_vertical_m": .8 - abs(t["true_world_dz_m"]) if finite(t["true_world_dz_m"]) else None,
            "last_full_quad_signed_plane_m": t["last_full_quad_signed_plane_m"], "phase": t["phase"],
            "v_cmd_body_xyz": t["v_cmd"], "yaw_rate": t["yaw_rate"], "blind_hold": t["blind_hold"],
            "speed_cap_mps": "UNLOGGED", "v_est_body_xyz": t["v_est"],
            "phase_transition": t["phase_transition"], "exit_cause": "UNLOGGED",
            "proxy_exit_cause": t["proxy_exit_cause"], "collision_impulse": t["collision_impulse"],
        })
    return rows


def main():
    summaries = []
    for case, (cohort, rel) in CASES.items():
        folder = ROOT / rel
        rows = load(folder)
        params = json.loads((folder / "params.json").read_text(encoding="utf-8"))
        ticks, topics, passes = make_ticks(rows, params)
        n = 0
        for start, end in segments(ticks):
            ledger = slice_ledger(ticks, start, end, passes, params)
            if not ledger:
                continue
            n += 1
            suffix = f"{case}_approach{n}"
            traces = trace_rows(ledger)
            met = metrics(ledger, traces, passes)
            classification, rationale = classify(cohort, ledger, met)
            csv_write(OUT / f"ledger_{suffix}.csv", LEDGER_COLUMNS, ledger_rows(ledger))
            csv_write(OUT / f"paired_traces_{suffix}.csv", TRACE_COLUMNS, traces)
            summaries.append({
                "case": case, "cohort": cohort, "approach": n, "fixture": rel,
                "t0_mono_ns": ledger[0]["mono"], "ticks": len(ledger),
                "classification": classification, "classification_rationale": rationale,
                "metrics": met, "proxy_exit_cause": ledger[-1]["proxy_exit_cause"],
                "unlogged_backlog": UNLOGGED,
            })
    payload = {"method": {
        "alignment": "first forward-positive signed-plane crossing through +1.0 m per contiguous near/approach segment",
        "plane_sign": "unit PnP normal, reoriented to camera-forward positive; t[2] fallback",
        "sampling": "setpoint/control ticks with state/detection forward-fill no older than 20 ms",
        "margin_proxy": "0.8 m half-opening, lateral=t[0], vertical=true_world_dz; aim-up is unlogged",
    }, "approaches": summaries, "unlogged_backlog": UNLOGGED}
    (OUT / "summary.json").write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
