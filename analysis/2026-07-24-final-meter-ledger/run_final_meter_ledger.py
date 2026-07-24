"""Build control-tick final-meter ledgers for the three race-risk fixtures.

Signed plane distance uses camera-forward depth t[2] (planner convention:
positive in front of the gate, negative after crossing). Along-plane
command/estimate use body-x (controller forward). Ledger continues through
retreat/recover until geometric behind, pass, collision, or segment end.

Run from the repository root:
  C:/Users/tsion/Projects/eni_dcim/.venv/Scripts/python.exe \\
    analysis/2026-07-24-final-meter-ledger/run_final_meter_ledger.py
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
    "t_rel_s", "signed_plane_m", "signed_plane_dot_n_m", "active_gate_index",
    "lock_present", "det_present", "det_certified", "det_confidence", "det_class",
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


def signed_plane_t2(t, _normal=None):
    """Planner pass-axis depth: t[2] > 0 in front, < 0 after crossing."""
    t = vec3(t)
    return t[2] if t else None


def signed_plane_dot_n(t, normal):
    """Optional secondary: |n|~1 normal dotted with t, n flipped to n_z>0."""
    t = vec3(t)
    raw_n = vec3(normal)
    raw_len = norm(raw_n)
    if not t or not raw_n or not (0.8 <= raw_len <= 1.2):
        return None
    n = unit(raw_n)
    if n[2] < 0:
        n = tuple(-x for x in n)
    return dot(t, n)


# Back-compat for unit tests / callers that still say signed_plane(...).
def signed_plane(t, normal):
    return signed_plane_t2(t, normal)


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


def value_at(rows, monos, mono, max_age_ns=40_000_000):
    """Nearest prior sample within max_age (default 40 ms — state≈setpoint)."""
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
        state_t = vec3(gate_rel.get("t"))
        det_t = vec3((det.get("rel_pose") or {}).get("t"))
        state_n = vec3(gate_rel.get("normal"))
        det_n = vec3((det.get("rel_pose") or {}).get("normal"))
        lock = state_t is not None
        t, n, source = (state_t, state_n, "state") if lock else (det_t, det_n, "detection")
        s = signed_plane_t2(t) if t else None
        s_dot = signed_plane_dot_n(t, n) if t else None
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
        ticks.append({
            "mono": mono, "mono_s": (mono - first) / 1e9, "phase": spd.get("phase"),
            "signed_plane_m": s, "signed_plane_dot_n_m": s_dot,
            "active_gate_index": active_gate, "lock_present": lock,
            "det_present": det_present, "det_certified": certified,
            "det_confidence": confidence, "det_class": det_class,
            "gate_rel_age_s": state.get("gate_rel_age_s") if lock else None,
            "range_m": norm(t), "lateral_m": lateral,
            "true_world_dz_m": dz, "opening_off_m": off,
            "last_full_quad_signed_plane_m": last_full_s, "v_cmd": cmd,
            "v_est": est, "yaw_rate": spd.get("yaw_rate"),
            "blind_hold": spd.get("blind_hold"), "normal": n,
            "collision_impulse": impulse, "source": source,
        })
    return ticks, topics, race_increments(topics["race"])


def segments(ticks):
    """One segment per commit entry that later reaches near-gate range."""
    result = []
    i = 0
    n = len(ticks)
    while i < n:
        phase = str(ticks[i]["phase"] or "").lower()
        if phase != "commit":
            i += 1
            continue
        # Walk back to include preceding approach/align of this attempt.
        start = i
        j = i - 1
        while j >= 0 and str(ticks[j]["phase"] or "").lower() in {"approach", "align", "commit"}:
            start = j
            j -= 1
        end = i
        while end + 1 < n and str(ticks[end + 1]["phase"] or "").lower() in {
            "approach", "align", "commit", "retreat", "recover", "search", "hover"
        }:
            end += 1
            # Soft end: after leaving commit into search/hover with s far or missing.
            p = str(ticks[end]["phase"] or "").lower()
            s = ticks[end]["signed_plane_m"]
            if p in {"search", "hover"} and (s is None or s > 3.0 or s < -0.5):
                break
            if p in {"search", "hover"} and end > i + 5:
                # End shortly after leaving the attempt.
                nxt = str(ticks[end]["phase"] or "").lower()
                if nxt in {"search", "hover"} and (end - i) > 30:
                    break
        # Keep if the segment ever gets within 3 m or crosses +1.0m.
        planes = [t["signed_plane_m"] for t in ticks[start:end + 1] if finite(t["signed_plane_m"])]
        ranges = [t["range_m"] for t in ticks[start:end + 1] if finite(t["range_m"])]
        if planes and (min(planes) < 3.0 or (ranges and min(ranges) < 3.0)):
            if any(finite(a) and finite(b) and a > 1.0 >= b
                   for a, b in zip(planes, planes[1:])) or any(p <= 1.0 for p in planes):
                result.append((start, end))
        # Advance past this commit block.
        i = end + 1
    # Deduplicate overlapping windows (keep earliest start / latest end merge).
    if not result:
        return result
    merged = [result[0]]
    for start, end in result[1:]:
        ps, pe = merged[-1]
        if start <= pe:
            merged[-1] = (ps, max(pe, end))
        else:
            merged.append((start, end))
    return merged


def locate_alignment(ticks, start, end):
    for i in range(max(start + 1, 1), end + 1):
        before, now = ticks[i - 1]["signed_plane_m"], ticks[i]["signed_plane_m"]
        if finite(before) and finite(now) and before > 1.0 >= now:
            return i
    # Fallback: first tick already inside +1.0 with a prior >1.0 outside window.
    for i in range(start, end + 1):
        s = ticks[i]["signed_plane_m"]
        if finite(s) and s <= 1.0:
            # Require evidence we came from farther out in the segment.
            prior = [ticks[k]["signed_plane_m"] for k in range(start, i)
                     if finite(ticks[k]["signed_plane_m"])]
            if prior and max(prior) > 1.0:
                return i
            if i == start and s > 0.3:
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
    if finite(tick["signed_plane_m"]) and tick["signed_plane_m"] < -0.4:
        return "GEOMETRIC_BEHIND"
    if phase in {"retreat", "recover"}:
        return phase.upper()
    return "NONE"


def slice_ledger(ticks, start, end, pass_monos, params):
    aligned = locate_alignment(ticks, start, end)
    if aligned is None:
        return None
    abort_min = params_at(params, ("planner", "commit", "abort_min_dist_m"), 0.8)
    off_limit = params_at(params, ("planner", "commit", "abort_offset_m"), 0.45)
    blind = params_at(params, ("planner", "commit", "blind_age_s"), 0.3)
    out, previous_phase = [], None
    for i in range(aligned, end + 1):
        tick = dict(ticks[i])
        prior = out[-1] if out else None
        passed = any(
            (prior["mono"] if prior else tick["mono"]) < p <= tick["mono"]
            for p in pass_monos
        )
        tick["phase_transition"] = phase_transition(previous_phase, tick["phase"])
        tick["proxy_exit_cause"] = proxy_exit(tick, passed)
        tick["abort_corridor_breach_proxy"] = bool(
            finite(tick["range_m"]) and abort_min < tick["range_m"] < 1.5 and
            finite(tick["opening_off_m"]) and tick["opening_off_m"] > off_limit and
            finite(tick["gate_rel_age_s"]) and tick["gate_rel_age_s"] <= blind
        )
        out.append(tick)
        previous_phase = tick["phase"]
        # Hard stops only: do NOT stop on retreat/recover alone (pass may follow).
        if passed or finite(tick["collision_impulse"]):
            break
        if finite(tick["signed_plane_m"]) and tick["signed_plane_m"] < -0.5:
            break
        # Cap: 4 s after alignment.
        if (tick["mono"] - out[0]["mono"]) > 4_000_000_000:
            break
    return out


def along_body_x(v):
    return v[0] if v else None


def trace_rows(ledger):
    rows = []
    for tick in ledger:
        cmd, est = tick["v_cmd"], tick["v_est"]
        rows.append({
            "t_rel_s": round((tick["mono"] - ledger[0]["mono"]) / 1e9, 4),
            "signed_plane_m": tick["signed_plane_m"],
            "v_cmd_along_plane": along_body_x(cmd),
            "v_est_along_plane": along_body_x(est),
            "v_cmd_lat": cmd[1] if cmd else None,
            "v_est_lat": est[1] if est else None,
            "v_cmd_vert": cmd[2] if cmd else None,
            "v_est_vert": est[2] if est else None,
        })
    return rows


def nearest_by_s(ledger, target):
    candidates = [x for x in ledger if finite(x["signed_plane_m"])]
    return min(candidates, key=lambda x: abs(x["signed_plane_m"] - target)) if candidates else None


def angle_cmd_forward(v):
    """Angle of body xy command away from +x (degrees)."""
    if not v:
        return None
    mag = math.hypot(v[0], v[1])
    if mag < 1e-6:
        return None
    return math.degrees(math.acos(max(-1.0, min(1.0, v[0] / mag))))


def metrics(ledger, traces, pass_monos):
    # Closest approach = minimum |s| among positive-s ticks, else min s overall.
    ahead = [x for x in ledger if finite(x["signed_plane_m"]) and x["signed_plane_m"] >= 0]
    closest = min(ahead, key=lambda x: x["signed_plane_m"]) if ahead else min(
        (x for x in ledger if finite(x["signed_plane_m"])),
        key=lambda x: abs(x["signed_plane_m"]),
    )
    s_values = [x["signed_plane_m"] for x in ledger if finite(x["signed_plane_m"])]
    s_min_signed = min(s_values) if s_values else None
    samples = {
        "s_plus_1_0": nearest_by_s(ledger, 1.0),
        "s_plus_0_5": nearest_by_s(ledger, 0.5),
        "closest": closest,
        "last_certified_detection": next(
            (x for x in reversed(ledger) if x["det_certified"]), None
        ),
    }
    margins = {}
    for name, tick in samples.items():
        if tick:
            margins[name] = {
                "signed_plane_m": tick["signed_plane_m"],
                "lateral_m": tick["lateral_m"],
                "true_world_dz_m": tick["true_world_dz_m"],
                "opening_off_m": tick["opening_off_m"],
                "margin_lateral_m": (
                    0.8 - abs(tick["lateral_m"]) if finite(tick["lateral_m"]) else None
                ),
                "margin_vertical_m": (
                    0.8 - abs(tick["true_world_dz_m"])
                    if finite(tick["true_world_dz_m"]) else None
                ),
            }
    ratios = [
        r["v_est_along_plane"] / r["v_cmd_along_plane"]
        for r in traces
        if finite(r["v_cmd_along_plane"]) and r["v_cmd_along_plane"] > 0.3
        and finite(r["v_est_along_plane"])
        and finite(r["signed_plane_m"]) and 0 < r["signed_plane_m"] <= 1.0
    ]
    approach_rows = [
        r for r in traces
        if finite(r["signed_plane_m"]) and 0 < r["signed_plane_m"] <= 1.0
    ]
    final = [r for r in traces if r["t_rel_s"] >= traces[-1]["t_rel_s"] - 0.5]
    s_delta = (
        final[-1]["signed_plane_m"] - final[0]["signed_plane_m"]
        if len(final) >= 2 and finite(final[-1]["signed_plane_m"])
        and finite(final[0]["signed_plane_m"]) else None
    )
    at_one, at_close = nearest_by_s(ledger, 1.0), closest
    a1 = angle_cmd_forward(at_one["v_cmd"]) if at_one else None
    ac = angle_cmd_forward(at_close["v_cmd"]) if at_close else None
    early = [
        r for r in approach_rows
        if r["signed_plane_m"] > 0.2 and finite(r["v_cmd_along_plane"])
    ]
    high = max((r["v_cmd_along_plane"] for r in early), default=None)
    # Withdrawal: cmd drops >50% while still in front, OR phase retreat/recover
    # with s>0.2 before the minimum positive s.
    withdrew_cmd = bool(
        high and high > 0 and any(r["v_cmd_along_plane"] < 0.5 * high for r in early)
    )
    closest_mono = closest["mono"]
    withdrew_phase = any(
        str(t["phase"] or "").lower() in {"retreat", "recover"}
        and finite(t["signed_plane_m"]) and t["signed_plane_m"] > 0.2
        and t["mono"] < closest_mono
        for t in ledger
    )
    nearby_pass = next(
        (p for p in pass_monos
         if ledger[0]["mono"] - 100_000_000 < p <= ledger[-1]["mono"] + 1_000_000_000),
        None,
    )
    before_pass = max(
        (t for t in ledger if nearby_pass and t["mono"] <= nearby_pass),
        key=lambda t: t["mono"], default=None,
    )
    # Premature scoring: counter while still clearly in front AND never behind.
    crossed = s_min_signed is not None and s_min_signed <= 0.0
    premature = bool(
        nearby_pass and before_pass and finite(before_pass["signed_plane_m"])
        and before_pass["signed_plane_m"] > 0.2 and not crossed
    )
    cmd_at_closest = along_body_x(closest["v_cmd"])
    return {
        "s_min_ahead_m": closest["signed_plane_m"],
        "s_min_signed_m": s_min_signed,
        "closest_phase": closest["phase"],
        "margins": margins,
        "tracking_ratio": {
            "mean_rho": mean(ratios) if ratios else None,
            "median_rho": median(ratios) if ratios else None,
            "fraction_rho_lt_0_5": (
                sum(x < 0.5 for x in ratios) / len(ratios) if ratios else None
            ),
            "n_ticks": len(ratios),
        },
        "closing": {
            "delta_s_final_0_5s_m": s_delta,
            "cmd_along_at_closest_mps": cmd_at_closest,
            "cmd_withdrew_before_closest": withdrew_cmd or withdrew_phase,
            "withdrew_by_cmd_drop": withdrew_cmd,
            "withdrew_by_phase": withdrew_phase,
        },
        "vector_rotation": {
            "angle_deg_at_s_1m": a1,
            "angle_deg_at_closest": ac,
            "growth_deg": ac - a1 if finite(a1) and finite(ac) else None,
        },
        "scoring_order_check": {
            "active_gate_increment_while_s_gt_0_2": premature,
            "counter_increment_mono_ns": nearby_pass,
            "last_signed_plane_before_increment_m": (
                before_pass["signed_plane_m"] if before_pass else None
            ),
            "plane_went_nonpositive": crossed,
        },
    }


def classify(case_cohort, ledger, met):
    smin = met["s_min_ahead_m"]
    s_signed = met["s_min_signed_m"]
    rho = met["tracking_ratio"]["mean_rho"]
    closing = met["closing"]
    phases = [str(t["phase"] or "").lower() for t in ledger]
    cmd_along = [along_body_x(t["v_cmd"]) for t in ledger
                 if finite(t["signed_plane_m"]) and 0 < t["signed_plane_m"] <= 1.0]
    finite_cmds = [x for x in cmd_along if finite(x)]
    command_high = (
        len(finite_cmds) > 0
        and sum(x >= 0.8 for x in finite_cmds) >= max(2, len(finite_cmds) // 2)
    )
    rot = met["vector_rotation"]["growth_deg"]
    pass_counter = met["scoring_order_check"]["counter_increment_mono_ns"] is not None
    crossed = met["scoring_order_check"]["plane_went_nonpositive"]

    # PASS requires the sim race counter in this window. A later dead-reckoned
    # plane crossing without a new counter is post-pass coast, not a new PASS.
    if pass_counter and crossed:
        return "PASS", (
            f"race counter incremented with plane going non-positive "
            f"(s_min_signed={s_signed:.3f} m, closest_ahead={smin:.3f} m)."
        )
    if pass_counter and not crossed:
        # Physical pass can score while believed t[2] is still slightly positive
        # (r1k-off-run3: counter at s≈+0.25). That is D under the ledger rule.
        return "D scoring-order", (
            f"gate index incremented while estimated plane stayed positive "
            f"(last_s_before={met['scoring_order_check']['last_signed_plane_before_increment_m']}, "
            f"s_min_signed={s_signed}). "
            f"If result.json gates_passed>0 this is a scored pass with "
            f"estimator still in front — scoring/estimate order, not a stall."
        )
    if crossed and not pass_counter:
        if case_cohort == "PASS":
            return "POST_PASS_OR_PHANTOM_CROSS", (
                f"plane went non-positive (s_min_signed={s_signed:.3f} m) without a "
                f"race-counter event in-window — post-pass DR or phantom cross."
            )
        # Stall cohort: believed behind the plane but sim never scored a pass.
        if closing["cmd_withdrew_before_closest"] and (rho is None or rho >= 0.5):
            return "A command-withdrawal", (
                f"phantom/estimate cross (s_min_signed={s_signed:.3f} m) then "
                f"command/phase withdrawal without race score; rho={rho}."
            )
        return "D scoring-order", (
            f"estimate crossed plane (s_min_signed={s_signed:.3f} m) without race "
            f"score — estimator/scoring order disagreement; rho={rho}."
        )

    if closing["cmd_withdrew_before_closest"] and (rho is None or rho >= 0.5):
        return "A command-withdrawal", (
            f"withdraw_cmd={closing['withdrew_by_cmd_drop']}, "
            f"withdraw_phase={closing['withdrew_by_phase']}; "
            f"rho={rho}; closest_ahead={smin:.3f} m; cmd@closest={closing['cmd_along_at_closest_mps']}."
        )
    if command_high and rho is not None and rho < 0.5:
        return "B plant-non-tracking", (
            f"command stayed >=0.8 m/s for most final-meter ticks; "
            f"rho={rho:.3f}; closest_ahead={smin:.3f} m."
        )
    early_retreat = any(
        str(t["phase"] or "").lower() in {"retreat", "recover"}
        and finite(t["signed_plane_m"]) and t["signed_plane_m"] > 0.2
        for t in ledger
    )
    if rot is not None and rot > 25 and not early_retreat:
        return "C vector-rotation", (
            f"command axis angle grew {rot:.1f}°; rho={rho}; closest_ahead={smin:.3f} m."
        )
    # Prefer B when rho is available and low even without sustained-high bit.
    if rho is not None and rho < 0.5:
        return "B plant-non-tracking (qualified)", (
            f"rho={rho:.3f} (n={met['tracking_ratio']['n_ticks']}); "
            f"command_high={command_high}; closest_ahead={smin:.3f} m; "
            f"cmd@closest={closing['cmd_along_at_closest_mps']}."
        )
    return "INCONCLUSIVE (needs UNLOGGED exit/predicate)", (
        f"final phase={phases[-1]}, withdraw={closing['cmd_withdrew_before_closest']}, "
        f"rho={rho}, closest_ahead={smin:.3f} m, s_min_signed={s_signed}."
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
            "signed_plane_m": t["signed_plane_m"],
            "signed_plane_dot_n_m": t.get("signed_plane_dot_n_m"),
            "active_gate_index": t["active_gate_index"],
            "lock_present": t["lock_present"], "det_present": t["det_present"],
            "det_certified": t["det_certified"], "det_confidence": t["det_confidence"],
            "det_class": t["det_class"], "gate_rel_age_s": t["gate_rel_age_s"],
            "commit_predicate_vector": "UNLOGGED", "range_m": t["range_m"],
            "lateral_m": t["lateral_m"], "true_world_dz_m": t["true_world_dz_m"],
            "opening_off_m": t["opening_off_m"],
            "abort_corridor_breach_proxy": t["abort_corridor_breach_proxy"],
            "margin_lateral_m": (
                0.8 - abs(t["lateral_m"]) if finite(t["lateral_m"]) else None
            ),
            "margin_vertical_m": (
                0.8 - abs(t["true_world_dz_m"]) if finite(t["true_world_dz_m"]) else None
            ),
            "last_full_quad_signed_plane_m": t["last_full_quad_signed_plane_m"],
            "phase": t["phase"],
            "v_cmd_body_xyz": t["v_cmd"], "yaw_rate": t["yaw_rate"],
            "blind_hold": t["blind_hold"],
            "speed_cap_mps": "UNLOGGED", "v_est_body_xyz": t["v_est"],
            "phase_transition": t["phase_transition"], "exit_cause": "UNLOGGED",
            "proxy_exit_cause": t["proxy_exit_cause"],
            "collision_impulse": t["collision_impulse"],
        })
    return rows


def write_report(summaries):
    lines = [
        "# Final-meter ledger — 2026-07-24",
        "",
        "## Provenance and scope",
        "",
        "Implements the user-requested +1.0 m-aligned control-tick ledger and",
        "the extractables from channel-2 `ADVISORY_36.md` §4 (Downloads). The",
        "literal memo titled **“RACE-RISK ADVISORY 1”** with the A–D stall labels",
        "was not present on disk; A–D are applied from the analyst task wording,",
        "with ADVISORY_36 as the extraction parent.",
        "",
        "Method (corrected after first-pass frame bugs):",
        "- **Signed plane** = camera-forward depth `gate_rel.t[2]` (planner",
        "  convention). `signed_plane_dot_n` is logged as a secondary column.",
        "- **Along-plane cmd/est** = body-x (controller forward) — not a camera",
        "  normal dotted into body velocity.",
        "- Ledger **continues through retreat/recover** until geometric behind",
        "  (`s < -0.5`), race pass, collision, or 4 s post-alignment.",
        "- Sampling: setpoint ticks, state/detection fill ≤40 ms.",
        "",
        "## Verdicts",
        "",
        "| Fixture / approach | Class | Deciding values |",
        "| --- | --- | --- |",
    ]
    for row in summaries:
        m = row["metrics"]
        tr = m["tracking_ratio"]
        cl = m["closing"]
        sc = m["scoring_order_check"]
        decide = (
            f"s_ahead_min={m['s_min_ahead_m']:.3f} m; "
            f"s_signed_min={m['s_min_signed_m']}; "
            f"ρ={tr['mean_rho']} (n={tr['n_ticks']}); "
            f"cmd@closest={cl['cmd_along_at_closest_mps']}; "
            f"withdraw={cl['cmd_withdrew_before_closest']}; "
            f"pass_counter={sc['counter_increment_mono_ns'] is not None}; "
            f"crossed={sc['plane_went_nonpositive']}. "
            f"{row['classification_rationale']}"
        )
        lines.append(
            f"| `{row['case']}` / {row['approach']} | **{row['classification']}** | {decide} |"
        )
    lines += [
        "",
        "## Discriminating observations",
        "",
    ]
    for row in summaries:
        if row["cohort"] == "STALL" or "PASS" in row["classification"] or row["classification"].startswith("D"):
            m = row["metrics"]
            lines.append(
                f"- **{row['case']} a{row['approach']}** → {row['classification']}: "
                f"closest_ahead={m['s_min_ahead_m']:.3f} m / "
                f"true_dz={m['margins'].get('closest', {}).get('true_world_dz_m')}; "
                f"ρ_mean={m['tracking_ratio']['mean_rho']}; "
                f"Δs(last 0.5s)={m['closing']['delta_s_final_0_5s_m']}."
            )
    lines += [
        "",
        "## UNLOGGED instrumentation backlog",
        "",
    ]
    for i, item in enumerate(UNLOGGED, 1):
        lines.append(f"{i}. {item}")
    lines += [
        "",
        "Literal `UNLOGGED` cells are retained in the CSV ledgers.",
        "",
        "## Artifacts",
        "",
        "- `ledger_*.csv` — §4 identity/geometry/command/exit tick tables",
        "- `paired_traces_*.csv` — §5 cmd vs est along/lat/vert",
        "- `summary.json` — metrics + classifications",
        "- `run_final_meter_ledger.py` — reproducible extractor",
        "",
    ]
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    # Remove stale per-approach outputs from earlier buggy runs.
    for path in OUT.glob("ledger_*.csv"):
        path.unlink()
    for path in OUT.glob("paired_traces_*.csv"):
        path.unlink()

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
                "classification": classification,
                "classification_rationale": rationale,
                "metrics": met, "proxy_exit_cause": ledger[-1]["proxy_exit_cause"],
                "unlogged_backlog": UNLOGGED,
            })
    payload = {
        "method": {
            "alignment": "first t[2] downward crossing through +1.0 m per commit-rooted approach",
            "plane_sign": "primary signed_plane = t[2]; secondary signed_plane_dot_n logged",
            "along_axis": "body-x command/estimate (controller forward)",
            "sampling": "setpoint ticks with state/detection forward-fill ≤40 ms",
            "margin_proxy": "0.8 m half-opening; aim-up unlogged",
            "slice_end": "continue through retreat/recover until s<-0.5, pass, collision, or 4s",
        },
        "approaches": summaries,
        "unlogged_backlog": UNLOGGED,
    }
    (OUT / "summary.json").write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    write_report(summaries)
    print(json.dumps({
        "n_approaches": len(summaries),
        "classes": [
            {"case": s["case"], "approach": s["approach"],
             "classification": s["classification"],
             "ticks": s["ticks"],
             "s_ahead": s["metrics"]["s_min_ahead_m"],
             "s_signed": s["metrics"]["s_min_signed_m"],
             "rho": s["metrics"]["tracking_ratio"]["mean_rho"]}
            for s in summaries
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
