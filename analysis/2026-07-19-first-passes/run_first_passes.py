"""THE TWO PASSES — full decomposition + readiness backfill (phase6h).

Fixture: sibling eni_dcim/.../20260719T164956-phase6h-first-enable
Flights: 20260719T160537 (clean pass), 20260719T163649 (pass + 2 clips).

Uses TerminalOracle / terminal_observe from the FLOWN tree (eni_dcim HEAD
6b1b3e3+), not necessarily this checkout — readiness APIs may lag here.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
FIX = Path(r"C:\Users\tsion\Projects\eni_dcim\fixtures\20260719T164956-phase6h-first-enable")
FLOWN_SRC = Path(r"C:\Users\tsion\Projects\eni_dcim\src")

# Prefer flown tree for TerminalOracle / readiness predicate.
# Insert flown LAST so it sits at sys.path[0] (insert(0) prepends).
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(FLOWN_SRC))

from aigp.core.messages import RelPose, TerminalFeature  # noqa: E402
from aigp.planning.approach import true_world_dz  # noqa: E402
from aigp.planning.vertical_owner import (  # noqa: E402
    ALT_OWNER,
    TERM_OWNER,
    TerminalOracle,
    VerticalOwnerArbiter,
    terminal_observe,
)
from aigp.planning.vertical_terminal import (  # noqa: E402
    crossing_error,
    crossing_sigma,
    terminal_vz_command,
)

FLIGHTS = {
    "F_CLEAN": {
        "id": "20260719T160537-f170ead6",
        "label": "try15 clean pass",
        "note": "gates=1 clips=0; death env impulse=5.2",
    },
    "F_CLIP": {
        "id": "20260719T163649-f170ead6",
        "label": "try39 pass with 2 clips",
        "note": "gates=1 clips=2; death env impulse=2.4",
    },
}

D_STAR = 0.8
GATE_W = 1.6
PITCH_CAL = -0.33
E_CLAMP = 0.45
ENGAGE_Z = 2.5
VZ_MAX = 0.6


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def takeoff_mono(rows: list[dict]) -> int:
    for r in rows:
        if r.get("topic") != "fsm":
            continue
        d = r["data"]
        if d.get("dst") == "TAKEOFF" or "GO" in str(d.get("reason", "")).upper():
            return int(r["mono_ns"])
    # fallback: first setpoint takeoff
    for r in rows:
        if r.get("topic") == "setpoint" and r["data"].get("phase") == "takeoff":
            return int(r["mono_ns"])
    return int(rows[0]["mono_ns"])


def t_rel(mono: int, t0: int) -> float:
    return (mono - t0) / 1e9


def t_ff(mono: int, takeoff: int) -> float:
    return (mono - takeoff) / 1e9


def finite_age(v) -> float | None:
    if v is None:
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def parse_log(rows: list[dict]) -> dict:
    t0 = int(rows[0]["mono_ns"])
    toff = takeoff_mono(rows)
    states, feats, dets, shadows, colls, setpoints, race = [], [], [], [], [], [], []
    for r in rows:
        mono = int(r["mono_ns"])
        topic = r.get("topic")
        d = r.get("data") or {}
        base = {"mono": mono, "t_rel": t_rel(mono, t0), "t_ff": t_ff(mono, toff)}
        if topic == "state":
            gr = d.get("gate_rel")
            states.append({
                **base,
                "gate_rel": gr,
                "q_att": d.get("q_att") or [1, 0, 0, 0],
                "level_roll": float(d.get("level_roll") or 0.0),
                "level_pitch": float(d.get("level_pitch") or 0.0),
                "age": finite_age(d.get("gate_rel_age_s")),
                "center_px": d.get("gate_center_px"),
                "image_size": d.get("image_size") or [640, 360],
                "v_world": d.get("v_world") or [0, 0, 0],
            })
        elif topic == "feature":
            feats.append({
                **base,
                "y_top_px": float(d["y_top_px"]),
                "span_px": float(d["span_px"]),
                "center_x_px": float(d["center_x_px"]),
                "cert_status": d.get("cert_status"),
                "mode": d.get("mode", "BAR_FULL"),
                "ts_ns": int(d.get("ts_ns") or mono),
            })
        elif topic == "detection":
            rp = d.get("rel_pose") or {}
            tvec = d.get("t_vec") or rp.get("t")
            if tvec is None:
                continue
            tvec = list(map(float, tvec))
            dets.append({
                **base,
                "t_vec": tvec,
                "R": float(np.linalg.norm(tvec)),
                "center_px": d.get("center_px"),
                "corners": d.get("corners_px") or d.get("corners"),
                "cert_status": d.get("cert_status"),
                "confidence": d.get("confidence"),
                "normal": rp.get("normal") or d.get("normal"),
            })
        elif topic == "shadow":
            shadows.append({**base, **{k: d.get(k) for k in
                           ("owner", "up_legacy_mps", "adapter_delta_mps",
                            "adapter_ok")}})
        elif topic == "collision":
            colls.append({**base, "impulse": d.get("impulse"),
                          "threat_level": d.get("threat_level")})
        elif topic == "setpoint":
            setpoints.append({**base, "phase": d.get("phase"),
                              "v_body": d.get("v_body")})
        elif topic == "race":
            race.append({**base,
                         "active_gate_index": d.get("active_gate_index"),
                         "gates_passed": d.get("gates_passed"),
                         "last_gate_race_time": d.get("last_gate_race_time")})
    return {
        "t0": t0, "takeoff": toff, "states": states, "features": feats,
        "dets": dets, "shadows": shadows, "collisions": colls,
        "setpoints": setpoints, "race": race,
    }


def nearest(items, t_ff_val, key="t_ff", max_dt=0.08):
    if not items:
        return None
    best = min(items, key=lambda x: abs(x[key] - t_ff_val))
    return best if abs(best[key] - t_ff_val) <= max_dt else None


def plane_crosses(states: list[dict]) -> list[dict]:
    out = []
    prev = None
    for s in states:
        gr = s.get("gate_rel")
        if gr is None:
            prev = None
            continue
        tz = float(gr["t"][2])
        if prev is not None and prev * tz < 0:
            out.append({
                "t_ff": s["t_ff"], "t_rel": s["t_rel"],
                "t_vec": list(map(float, gr["t"])),
                "age": s.get("age"), "center_px": s.get("center_px"),
                "sign": f"{prev:+.3f}->{tz:+.3f}",
            })
        prev = tz
    return out


def hud_pass_events(race: list[dict]) -> list[dict]:
    out = []
    prev_idx = None
    for r in race:
        idx = r.get("active_gate_index")
        if idx is None:
            continue
        if prev_idx is not None and idx > prev_idx:
            out.append({
                "t_ff": r["t_ff"], "t_rel": r["t_rel"],
                "active_gate_index": idx,
                "gates_passed": r.get("gates_passed"),
            })
        prev_idx = idx
    return out


def pixel_truth_crossing(dets, states, t_pass_ff: float) -> dict:
    """Pixel-truth crossing height/lateral from live dets near the pass.

    Prefer the last accepted detection with R<2.5m and tz>0 before pass,
    then the first after. Report cam t and TRUE-world vertical using the
    nearest state's attitude.
    """
    before = [d for d in dets
              if t_pass_ff - 0.8 <= d["t_ff"] <= t_pass_ff and d["R"] < 3.0
              and d["t_vec"][2] > 0]
    after = [d for d in dets
             if t_pass_ff < d["t_ff"] <= t_pass_ff + 0.4 and d["R"] < 3.0]
    candidates = sorted(before, key=lambda d: d["t_ff"])[-5:] + \
        sorted(after, key=lambda d: d["t_ff"])[:3]
    rows = []
    for d in candidates:
        st = nearest(states, d["t_ff"], max_dt=0.1)
        tw = None
        if st is not None:
            tw = float(true_world_dz(
                RelPose(t=np.asarray(d["t_vec"], float),
                        normal=np.asarray(d.get("normal") or [0, 0, 1], float)),
                np.asarray(st["q_att"], float),
                st["level_roll"], st["level_pitch"]))
        # +UP crossing error vs opening center: -true_world_dz
        # (gate below ⇒ vehicle HIGH ⇒ negative e_up)
        e_up = None if tw is None else -tw
        lat = float(d["t_vec"][0])  # cam x ~ body y lateral
        rows.append({
            "t_ff": d["t_ff"], "R": d["R"], "t_vec": d["t_vec"],
            "center_px": d.get("center_px"), "cert": d.get("cert_status"),
            "true_world_dz": tw, "e_up_opening": e_up, "lat_cam_x": lat,
        })
    # Pick the sample closest to the plane (min |tz|)
    best = None
    if rows:
        best = min(rows, key=lambda r: abs(r["t_vec"][2]))
    # Also state at pass
    st_pass = nearest(states, t_pass_ff, max_dt=0.15)
    state_cross = None
    if st_pass and st_pass.get("gate_rel"):
        t = list(map(float, st_pass["gate_rel"]["t"]))
        tw = float(true_world_dz(
            RelPose(t=np.asarray(t), normal=np.asarray(
                st_pass["gate_rel"].get("normal") or [0, 0, 1], float)),
            np.asarray(st_pass["q_att"], float),
            st_pass["level_roll"], st_pass["level_pitch"]))
        state_cross = {
            "t_ff": st_pass["t_ff"], "t_vec": t, "age": st_pass.get("age"),
            "true_world_dz": tw, "e_up_opening": -tw, "lat": t[0],
            "center_px": st_pass.get("center_px"),
        }
    return {"samples": rows, "best_det": best, "state_at_pass": state_cross}


def bar_label(det: dict) -> str:
    ty = det["t_vec"][1]
    tx = det["t_vec"][0]
    cy = None
    if det.get("center_px"):
        cy = float(det["center_px"][1])
    if det["R"] > 8:
        return "FAR"
    if abs(tx) > abs(ty) + 0.3 and abs(tx) > 0.4:
        return "RIGHT" if tx > 0 else "LEFT"
    # cam y down: ty>0 gate below optical axis ⇒ vehicle HIGH ⇒ top contact risk
    if ty > 0.12 or (cy is not None and cy > 220):
        return "TOP_bar_vehicle_HIGH"
    if ty < -0.12 or (cy is not None and cy < 140):
        return "BOTTOM_bar_vehicle_LOW"
    return "CENTER"


def clip_attribution(collisions, dets, t_pass_ff: float) -> list[dict]:
    """Attribute pre-pass clips to a bar."""
    out = []
    for c in collisions:
        if c["t_ff"] >= t_pass_ff - 0.05:
            # keep only clearly pre-pass or mark
            role = "pre_pass" if c["t_ff"] < t_pass_ff else "at_or_post_pass"
        else:
            role = "pre_pass"
        near = [d for d in dets if abs(d["t_ff"] - c["t_ff"]) < 0.25]
        near = sorted(near, key=lambda d: abs(d["t_ff"] - c["t_ff"]))[:6]
        labels = Counter(bar_label(d) for d in near)
        out.append({
            "t_ff": c["t_ff"], "t_rel": c["t_rel"],
            "impulse": c.get("impulse"), "threat": c.get("threat_level"),
            "role": role,
            "nearby_labels": dict(labels),
            "nearby": [{
                "t_ff": d["t_ff"], "R": d["R"], "t_vec": d["t_vec"],
                "center_px": d.get("center_px"), "cert": d.get("cert_status"),
                "label": bar_label(d),
            } for d in near],
            "winner": (max(labels, key=labels.get) if labels else None),
        })
    return out


@dataclass
class ReadyTick:
    t_ff: float
    t_rel: float
    phase: str
    e_meas: float | None
    ready: bool
    n_hist: int
    span_s: float
    gap_s: float
    vz_vis: float | None
    rate_auth: float
    certified_det: bool
    feat_cert: str | None
    feat_age: float | None
    R: float | None
    tz: float | None
    admit_ok: bool | None
    e_cross: float | None
    would_capture: bool
    owner: str
    vz_cmd_if_term: float | None


def readiness_backfill(log: dict) -> dict:
    """Replay observer against FEATURE+STATE on commit ticks.

    Settles: would TERM have been READY? captured? what vz at crossing?
    Note: live SHADOW owner=term does NOT imply readiness — shadow uses
    certified-det alone; the advisory remedy is this backfill.
    """
    oracle = TerminalOracle()
    arbiter = VerticalOwnerArbiter()
    ticks: list[ReadyTick] = []
    last_feat = None
    last_feat_t = None
    last_det_cert = False
    prev_phase = None
    ready_onset = None
    capture_t = None
    hist_at_pass = None

    # Merge events by mono
    events = []
    for s in log["states"]:
        events.append(("state", s["mono"], s))
    for f in log["features"]:
        events.append(("feature", f["mono"], f))
    for d in log["dets"]:
        events.append(("det", d["mono"], d))
    for sp in log["setpoints"]:
        events.append(("setpoint", sp["mono"], sp))
    events.sort(key=lambda e: e[1])

    cur_state = None
    cur_phase = "hover"
    for kind, mono, payload in events:
        if kind == "state":
            cur_state = payload
            continue
        if kind == "feature":
            last_feat = payload
            last_feat_t = payload["t_ff"]
            continue
        if kind == "det":
            last_det_cert = payload.get("cert_status") == "certified"
            continue
        if kind != "setpoint":
            continue
        phase = payload.get("phase") or "hover"
        # Reset oracle on leaving commit (app.py semantics)
        if prev_phase == "commit" and phase != "commit":
            oracle.reset()
            arbiter.tick(False, False, False, 9.0, "position")
        prev_phase = phase
        cur_phase = phase
        if phase != "commit" or cur_state is None:
            continue

        feat_age = None
        if last_feat is not None and last_feat_t is not None:
            feat_age = abs(payload["t_ff"] - last_feat_t)

        # Build state/feature objects for terminal_observe
        st_obj = SimpleNamespace(
            q_att=np.asarray(cur_state["q_att"], float),
            level_roll=cur_state["level_roll"],
            level_pitch=cur_state["level_pitch"],
            image_size=tuple(cur_state["image_size"] or [640, 360]),
            gate_rel=None,
            gate_rel_age_s=cur_state.get("age") or 9.0,
            v_world=np.asarray(cur_state.get("v_world") or [0, 0, 0], float),
        )
        if cur_state.get("gate_rel"):
            st_obj.gate_rel = RelPose(
                t=np.asarray(cur_state["gate_rel"]["t"], float),
                normal=np.asarray(
                    cur_state["gate_rel"].get("normal") or [0, 0, 1], float))
            st_obj.gate_rel_age_s = cur_state.get("age") or 0.0

        feat_obj = None
        if last_feat is not None:
            feat_obj = TerminalFeature(
                ts_ns=int(last_feat["ts_ns"]),
                y_top_px=last_feat["y_top_px"],
                span_px=last_feat["span_px"],
                center_x_px=last_feat["center_x_px"],
                cert_status=str(last_feat["cert_status"]),
                mode=str(last_feat.get("mode") or "BAR_FULL"),
            )

        e_meas = terminal_observe(
            oracle, st_obj, feat_obj, feat_age,
            d_star=D_STAR, gate_w=GATE_W,
            pitch_cal_rad=PITCH_CAL, e_z_clamp_m=E_CLAMP)

        n, span, gap = oracle.history_stats()
        ready = oracle.ready()
        vz_vis = oracle.v_z_visual()
        auth = oracle.rate_authority()
        if ready and ready_onset is None:
            ready_onset = payload["t_ff"]

        # Admission / would-capture (mirror terminal_override)
        R = tz = None
        if st_obj.gate_rel is not None:
            R = float(np.linalg.norm(st_obj.gate_rel.t))
            tz = float(st_obj.gate_rel.t[2])
        admit_ok = None
        e_x = None
        certified = last_det_cert and feat_obj is not None and \
            feat_obj.cert_status in ("certified", "probation")
        # Use detection cert for streak (app notes exposure on det cert)
        arbiter.note_exposure(last_det_cert)
        capture_ok = last_det_cert
        if arbiter.owner != TERM_OWNER:
            capture_ok = last_det_cert and ready
            if capture_ok and tz is not None:
                tau = max(tz, 0.05) / 2.0  # ~commit speed proxy
                e_now = e_meas if e_meas is not None else (
                    oracle._hist[-1][1] if oracle._hist else 0.0)
                vz = (vz_vis * auth) if vz_vis is not None else 0.0
                e_x = crossing_error(e_now, vz, tau)
                s_x = crossing_sigma(0.05, vz, 0.10, tau)
                admit_ok = abs(e_x) + 2.0 * s_x + 0.06 <= 0.30
                capture_ok = bool(admit_ok)
            else:
                admit_ok = False if ready else None

        in_range = tz is not None and tz <= ENGAGE_Z
        owner = arbiter.tick(
            commit_active=True, same_gate=True,
            certified=capture_ok and in_range,
            feature_age_s=st_obj.gate_rel_age_s,
            phase="position")
        if owner == TERM_OWNER and capture_t is None:
            capture_t = payload["t_ff"]

        vz_cmd = None
        if e_meas is not None and ready:
            tau = max(tz if tz is not None else 1.0, 0.05) / 2.0
            vz_cmd = terminal_vz_command(
                e_meas, tau, vz_max=VZ_MAX)

        ticks.append(ReadyTick(
            t_ff=payload["t_ff"], t_rel=payload["t_rel"], phase=phase,
            e_meas=e_meas, ready=ready, n_hist=n, span_s=span, gap_s=gap,
            vz_vis=vz_vis, rate_auth=auth, certified_det=last_det_cert,
            feat_cert=(feat_obj.cert_status if feat_obj else None),
            feat_age=feat_age, R=R, tz=tz, admit_ok=admit_ok,
            e_cross=e_x, would_capture=bool(capture_ok and in_range),
            owner=owner, vz_cmd_if_term=vz_cmd,
        ))

    ready_ticks = [t for t in ticks if t.ready]
    term_ticks = [t for t in ticks if t.owner == TERM_OWNER]
    # At crossing: nearest tick
    return {
        "n_commit_ticks": len(ticks),
        "n_ready_ticks": len(ready_ticks),
        "ready_onset_t_ff": ready_onset,
        "capture_t_ff": capture_t,
        "ever_ready": ready_onset is not None,
        "ever_captured": capture_t is not None,
        "max_hist": max((t.n_hist for t in ticks), default=0),
        "e_meas_at_ready": (ready_ticks[0].e_meas if ready_ticks else None),
        "ticks_sample": [t.__dict__ for t in ticks[:: max(1, len(ticks)//40)]],
        "all_ticks": [t.__dict__ for t in ticks],
    }


def command_at_crossing(backfill: dict, t_pass_ff: float) -> dict:
    ticks = backfill.get("all_ticks") or []
    if not ticks:
        return {"status": "no_ticks"}
    near = [t for t in ticks if abs(t["t_ff"] - t_pass_ff) < 0.5]
    if not near:
        # last ready before pass
        before = [t for t in ticks if t["t_ff"] <= t_pass_ff]
        near = before[-5:] if before else ticks[:5]
    last = near[-1]
    return {
        "t_ff": last["t_ff"],
        "ready": last["ready"],
        "owner": last["owner"],
        "e_meas": last["e_meas"],
        "vz_cmd_if_term": last["vz_cmd_if_term"],
        "vz_vis": last["vz_vis"],
        "admit_ok": last["admit_ok"],
        "would_capture": last["would_capture"],
        "n_hist": last["n_hist"],
        "verdict": _term_verdict(last),
    }


def _term_verdict(t: dict) -> str:
    if not t.get("ready"):
        return "IDLED — oracle never READY (no actuation even with enable)"
    if t.get("owner") != TERM_OWNER and not t.get("would_capture"):
        return "READY but NOT captured (admission/cert/range failed)"
    e = t.get("e_meas")
    vz = t.get("vz_cmd_if_term")
    if e is None or (isinstance(e, float) and abs(e) < 0.05):
        return "CAPTURED/READY — near-zero correction (would IDLE harmlessly)"
    if e < -0.05:
        return f"CAPTURED/READY — would DESCEND (e_meas={e:.3f}, vz≈{vz})"
    return f"CAPTURED/READY — would CLIMB (e_meas={e:.3f}, vz≈{vz})"


def post_pass_autopsy(log: dict, t_pass_ff: float, t_death_ff: float) -> dict:
    """What did the planner chase after gate index advanced, and what hit?"""
    phases = []
    prev = None
    for sp in log["setpoints"]:
        if sp["t_ff"] < t_pass_ff:
            continue
        if sp["t_ff"] > t_death_ff + 0.5:
            break
        if sp["phase"] != prev:
            phases.append({"t_ff": sp["t_ff"], "phase": sp["phase"]})
            prev = sp["phase"]

    dets = [d for d in log["dets"]
            if t_pass_ff <= d["t_ff"] <= t_death_ff and d["R"] < 40]
    # Cluster by range band + lateral
    bands = {"near_<3": [], "mid_3_10": [], "far_10_25": [], "vfar_>25": []}
    for d in dets:
        if d["R"] < 3:
            bands["near_<3"].append(d)
        elif d["R"] < 10:
            bands["mid_3_10"].append(d)
        elif d["R"] < 25:
            bands["far_10_25"].append(d)
        else:
            bands["vfar_>25"].append(d)

    def summarise(arr):
        if not arr:
            return {"n": 0}
        txs = [d["t_vec"][0] for d in arr]
        tys = [d["t_vec"][1] for d in arr]
        labels = Counter(bar_label(d) for d in arr)
        return {
            "n": len(arr),
            "R_med": float(np.median([d["R"] for d in arr])),
            "tx_med": float(np.median(txs)),
            "ty_med": float(np.median(tys)),
            "labels": dict(labels),
            "cert": dict(Counter(d.get("cert_status") for d in arr)),
        }

    # State lock around death
    st_death = nearest(log["states"], t_death_ff, max_dt=0.2)
    death_state = None
    if st_death:
        gr = st_death.get("gate_rel")
        death_state = {
            "t_ff": st_death["t_ff"],
            "age": st_death.get("age"),
            "t_vec": (list(map(float, gr["t"])) if gr else None),
            "R": (float(np.linalg.norm(gr["t"])) if gr else None),
            "center_px": st_death.get("center_px"),
        }

    colls = [c for c in log["collisions"] if c["t_ff"] >= t_pass_ff - 0.1]
    # Exit vector: mean bearing of mid/far dets in first 2s after pass
    early = [d for d in dets if d["t_ff"] <= t_pass_ff + 2.0 and d["R"] > 3]
    exit_vec = None
    if early:
        tx = float(np.median([d["t_vec"][0] for d in early]))
        ty = float(np.median([d["t_vec"][1] for d in early]))
        tz = float(np.median([d["t_vec"][2] for d in early]))
        exit_vec = {
            "n": len(early),
            "t_med": [tx, ty, tz],
            "R_med": float(np.median([d["R"] for d in early])),
            "azimuth_atan2_tx_tz_deg": float(np.degrees(np.arctan2(tx, max(tz, 0.1)))),
            "elevation_atan2_ty_tz_deg": float(np.degrees(np.arctan2(-ty, max(tz, 0.1)))),
            "note": "seeds Advisory-6 S4.1 exit-vector banking",
        }

    det_bands = {k: summarise(v) for k, v in bands.items()}
    return {
        "phase_after_pass": phases,
        "det_bands": det_bands,
        "n_dets_post": len(dets),
        "death_state": death_state,
        "collisions_post": colls,
        "exit_vector_early": exit_vec,
        "chase_verdict": _chase_verdict(det_bands, death_state, exit_vec),
    }


def _chase_verdict(bands, death_state, exit_vec) -> str:
    far = bands.get("far_10_25", {}).get("n", 0) + bands.get("vfar_>25", {}).get("n", 0)
    mid = bands.get("mid_3_10", {}).get("n", 0)
    if death_state and death_state.get("R") and death_state["R"] > 5:
        return (f"Died locked on FAR target R≈{death_state['R']:.1f}m "
                f"(age={death_state.get('age')}) — classic post-pass far-gate chase")
    if death_state and death_state.get("t_vec") is None:
        return "Died with gate_rel=null (lock cleared) — blind into environment"
    if far > mid:
        return "Post-pass detections dominated by FAR gates — exit-vector banking needed"
    return "Mixed mid-range chase; see exit_vector_early + death_state"


def denominator(summary: dict, report_path: Path) -> dict:
    attempts = summary.get("all_attempts") or []
    n = len(attempts)
    passes = [a for a in attempts if int(a.get("gates") or 0) >= 1]
    # frames: treat as real if frames_after_takeoff >= 100 or detections >= 50
    real = [a for a in attempts
            if int(a.get("frames_after_takeoff") or 0) >= 100
            or int(a.get("detections") or 0) >= 50]
    tooling_reject_unique0 = None
    slice_ok = None
    if report_path.exists():
        # report may be UTF-16
        raw = report_path.read_bytes()
        text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") \
            else raw.decode("utf-8", errors="replace")
        tooling_reject_unique0 = text.count("unique=0")
        slice_ok = text.count("unique_frames")
    return {
        "all_attempts": n,
        "real_full_control_flights": len(real),
        "passes": len(passes),
        "pass_fids": [a["fid"] for a in passes],
        "honest_pass_rate": (len(passes) / len(real)) if real else None,
        "honest_pass_rate_str": (
            f"{len(passes)}/{len(real)} = {100*len(passes)/len(real):.1f}%"
            if real else None),
        "tooling_REJECT_unique0_count": tooling_reject_unique0,
        "report_SLICE_mentions": slice_ok,
        "note": (
            "All all_attempts entries are REAL flown control-arm flights. "
            "The PowerShell slicer bug falsely REJECTED them as unique=0 "
            "despite SLICE JSON reporting 300+ unique frames. Denominator "
            "for the campaign baseline is the real flight count, not the "
            "tooling-accepted count."
        ),
        "abort_reasons": dict(Counter(
            (a.get("reason") or "").split("(")[0].strip() for a in attempts)),
        "attempts_table": [
            {"fid": a["fid"], "gates": a.get("gates"), "clips": a.get("clips"),
             "env_hits": a.get("env_hits"), "duration_s": a.get("duration_s"),
             "frames": a.get("frames_after_takeoff"),
             "reason": a.get("reason")}
            for a in attempts
        ],
    }


def analyze_flight(key: str, meta: dict) -> dict:
    fid = meta["id"]
    log_path = FIX / f"{fid}-flight.jsonl"
    rows = load_jsonl(log_path)
    log = parse_log(rows)
    crosses = plane_crosses(log["states"])
    hud = hud_pass_events(log["race"])
    # Primary pass time: HUD gate index advance, else first plane cross
    if hud:
        t_pass = hud[0]["t_ff"]
        t_pass_rel = hud[0]["t_rel"]
        pass_source = "hud_active_gate_index"
    elif crosses:
        t_pass = crosses[0]["t_ff"]
        t_pass_rel = crosses[0]["t_rel"]
        pass_source = "state_tz_signflip"
    else:
        # closest approach as fallback
        st = min((s for s in log["states"] if s.get("gate_rel")),
                 key=lambda s: abs(s["gate_rel"]["t"][2]), default=None)
        t_pass = st["t_ff"] if st else 0.0
        t_pass_rel = st["t_rel"] if st else 0.0
        pass_source = "closest_tz_fallback"

    truth = pixel_truth_crossing(log["dets"], log["states"], t_pass)
    clips = clip_attribution(log["collisions"], log["dets"], t_pass)
    backfill = readiness_backfill(log)
    at_cross = command_at_crossing(backfill, t_pass)

    # Death = last high-impulse collision
    big = max(log["collisions"], key=lambda c: float(c.get("impulse") or 0),
              default=None)
    t_death = big["t_ff"] if big else log["states"][-1]["t_ff"]
    autopsy = post_pass_autopsy(log, t_pass, t_death)

    # Live shadow owner hist (NOT readiness)
    shadow_hist = dict(Counter(s.get("owner") for s in log["shadows"]))

    # Drop all_ticks from nested copy for summary size — keep in CSV
    bf_summary = {k: v for k, v in backfill.items() if k != "all_ticks"}

    return {
        "key": key,
        "meta": meta,
        "fid": fid,
        "t0": log["t0"],
        "takeoff": log["takeoff"],
        "pass": {
            "t_ff": t_pass, "t_rel": t_pass_rel, "source": pass_source,
            "hud": hud, "plane_crosses": crosses[:5],
        },
        "crossing_truth": truth,
        "clip_attribution": clips,
        "readiness": bf_summary,
        "at_crossing_command": at_cross,
        "shadow_owner_hist_LIVE": shadow_hist,
        "shadow_note": (
            "Live SHADOW owner=term uses certified-det without the "
            "readiness/admission predicate — do NOT read it as READY."
        ),
        "death": big,
        "post_pass": autopsy,
        "n_features": len(log["features"]),
        "n_dets": len(log["dets"]),
        "feature_cert_hist": dict(Counter(f["cert_status"] for f in log["features"])),
        "_ticks": backfill.get("all_ticks") or [],
    }


def render_report(bundle: dict) -> str:
    den = bundle["denominator"]
    lines = []
    lines.append("# THE TWO PASSES — phase6h first counted passes")
    lines.append("")
    lines.append("Fixture: `20260719T164956-phase6h-first-enable` "
                 "(sibling `eni_dcim` checkout).")
    lines.append("HEAD flown: `6b1b3e3` (first-enable predicate). "
                 "Protocol was PARTIAL — control-arm only; live TERM enable "
                 "arm never flew. This report is the record of the campaign's "
                 "**first counted gate passes** plus the advisory's "
                 "deterministic readiness backfill.")
    lines.append("")
    lines.append("Timebases: **t_ff** = seconds since race GO; "
                 "**t_rel** = seconds since log start "
                 "(user windows ≈ t_rel).")
    lines.append("")

    # Denominator first — campaign baseline
    lines.append("## 3. Denominator — honest pass rate")
    lines.append("")
    lines.append(f"- Real full-control flights in retry loop: "
                 f"**{den['real_full_control_flights']}** "
                 f"(all_attempts={den['all_attempts']})")
    lines.append(f"- Counted passes: **{den['passes']}** "
                 f"`{den['pass_fids']}`")
    lines.append(f"- **Honest pass rate: {den['honest_pass_rate_str']}** "
                 "← campaign's new baseline number")
    lines.append(f"- Tooling false-REJECT `unique=0` count: "
                 f"{den['tooling_REJECT_unique0_count']} "
                 "(SLICE JSON still reported 300+ unique frames)")
    lines.append("")
    lines.append(den["note"])
    lines.append("")
    lines.append("Abort-reason rollup:")
    lines.append("```json")
    lines.append(json.dumps(den["abort_reasons"], indent=2))
    lines.append("```")
    lines.append("")

    for key in ("F_CLEAN", "F_CLIP"):
        f = bundle["flights"][key]
        lines.append(f"## {key} — {f['meta']['label']} (`{f['fid']}`)")
        lines.append("")
        lines.append(f"_{f['meta']['note']}_")
        lines.append("")
        p = f["pass"]
        lines.append(f"### Crossing reconstruction")
        lines.append("")
        lines.append(f"- Pass time: **t_ff={p['t_ff']:.3f}** / "
                     f"t_rel={p['t_rel']:.3f} (source={p['source']})")
        if p.get("hud"):
            lines.append(f"- HUD: `{p['hud']}`")
        if p.get("plane_crosses"):
            lines.append(f"- State tz sign-flips: "
                         f"`{json.dumps(p['plane_crosses'][:3], default=str)}`")
        lines.append("")
        ct = f["crossing_truth"]
        best = ct.get("best_det")
        stc = ct.get("state_at_pass")
        lines.append("**Pixel-truth / state at pass:**")
        lines.append("")
        if best:
            lines.append(
                f"- best live det: t_ff={best['t_ff']:.3f} R={best['R']:.3f} "
                f"t_vec={best['t_vec']} e_up={best.get('e_up_opening')} "
                f"lat={best.get('lat_cam_x')} cert={best.get('cert')} "
                f"center={best.get('center_px')}"
            )
        if stc:
            lines.append(
                f"- state: t_ff={stc['t_ff']:.3f} t_vec={stc['t_vec']} "
                f"age={stc.get('age')} e_up={stc.get('e_up_opening')} "
                f"lat={stc.get('lat')} center={stc.get('center_px')}"
            )
        # Verify user claim -0.09..+0.01 / centered
        e_vals = [s.get("e_up_opening") for s in ct.get("samples") or []
                  if s.get("e_up_opening") is not None and s["R"] < 1.5]
        if stc and stc.get("e_up_opening") is not None:
            e_vals.append(stc["e_up_opening"])
        if e_vals:
            lines.append(
                f"- e_up samples near plane (R<1.5 + state): "
                f"min={min(e_vals):+.3f} med={float(np.median(e_vals)):+.3f} "
                f"max={max(e_vals):+.3f}  "
                f"(live-det claim −0.09..+0.01 / centered: "
                f"{'CONFIRMED' if abs(float(np.median(e_vals))) < 0.12 else 'NOT in that band — see samples'})"
            )
        lines.append("")
        lines.append("Sample table (live dets near pass):")
        lines.append("")
        lines.append("| t_ff | R | t_vec | e_up | lat | cert | center |")
        lines.append("|---:|---:|---|---:|---:|---|---|")
        for s in (ct.get("samples") or [])[:12]:
            e_s = "" if s.get("e_up_opening") is None else f"{s['e_up_opening']:+.3f}"
            lines.append(
                f"| {s['t_ff']:.3f} | {s['R']:.2f} | "
                f"`{[round(x,3) for x in s['t_vec']]}` | "
                f"{e_s} | "
                f"{s.get('lat_cam_x', 0):+.3f} | {s.get('cert')} | "
                f"`{s.get('center_px')}` |"
            )
        lines.append("")

        if key == "F_CLIP":
            lines.append("### try39 clip attribution")
            lines.append("")
            for c in f["clip_attribution"]:
                if c["role"] != "pre_pass" and c["t_ff"] > p["t_ff"]:
                    continue
                lines.append(
                    f"- t_ff={c['t_ff']:.3f} (t_rel={c['t_rel']:.3f}) "
                    f"impulse={c.get('impulse')} threat={c.get('threat')} "
                    f"→ **{c.get('winner')}** `{c.get('nearby_labels')}`"
                )
            lines.append("")

        lines.append("### Deterministic readiness backfill")
        lines.append("")
        lines.append(f"_{f['shadow_note']}_")
        lines.append("")
        lines.append(f"- Live SHADOW owner hist: `{f['shadow_owner_hist_LIVE']}`")
        r = f["readiness"]
        lines.append(f"- commit ticks observed: {r['n_commit_ticks']}")
        lines.append(f"- ever READY: **{r['ever_ready']}** "
                     f"(onset t_ff={r['ready_onset_t_ff']})")
        lines.append(f"- ever CAPTURED (ready∧admit∧range≤{ENGAGE_Z}m): "
                     f"**{r['ever_captured']}** (t_ff={r['capture_t_ff']})")
        lines.append(f"- max unique oracle hist: {r['max_hist']}")
        lines.append(f"- ready ticks: {r['n_ready_ticks']}")
        ac = f["at_crossing_command"]
        lines.append("")
        lines.append(f"**At crossing:** `{json.dumps(ac, default=str)}`")
        lines.append("")
        lines.append(f"**TERM verdict: {ac.get('verdict')}**")
        lines.append("")

        lines.append("### Post-pass autopsy → death")
        lines.append("")
        dth = f.get("death") or {}
        lines.append(
            f"- Death: t_ff={dth.get('t_ff')} t_rel={dth.get('t_rel')} "
            f"impulse={dth.get('impulse')} "
            f"(user window t_rel≈{p['t_rel']:.2f}→{dth.get('t_rel')})"
        )
        pp = f["post_pass"]
        lines.append(f"- Phases after pass: "
                     f"`{pp.get('phase_after_pass')}`")
        lines.append(f"- Chase verdict: **{pp.get('chase_verdict')}**")
        lines.append(f"- Exit vector (first 2s, R>3m): "
                     f"`{json.dumps(pp.get('exit_vector_early'), default=str)}`")
        lines.append(f"- Death state: `{pp.get('death_state')}`")
        lines.append(f"- Det bands: `{json.dumps(pp.get('det_bands'), default=str)}`")
        lines.append("")

    lines.append("## Synthesis — did TERM help, hurt, or idle?")
    lines.append("")
    for key in ("F_CLEAN", "F_CLIP"):
        f = bundle["flights"][key]
        lines.append(f"- **{key}**: {f['at_crossing_command'].get('verdict')}")
    lines.append("")
    lines.append("Live shadow `owner=term` counts are **not** readiness "
                 "evidence (shadow path omits the oracle READY + admission "
                 "corridor). The backfill is the enable-gate answer.")
    lines.append("")
    lines.append("## Exit-vector banking seed (Advisory-6 S4.1)")
    lines.append("")
    lines.append("Both deaths occur AFTER a counted pass while the planner "
                 "re-acquires. The early post-pass detection median (R>3m) "
                 "is the exit-vector observation the banking spec should "
                 "hold: azimuth/elevation of the next lock relative to the "
                 "just-passed gate, plus a distance-sanity reject for "
                 "far-gate steal (already partially in relock code).")
    lines.append("")
    for key in ("F_CLEAN", "F_CLIP"):
        ev = bundle["flights"][key]["post_pass"].get("exit_vector_early")
        lines.append(f"- {key}: `{ev}`")
    lines.append("")
    lines.append("## Deliverables")
    lines.append("")
    lines.append("- `first-passes.md` (this file)")
    lines.append("- `summary.json`, per-flight `*_readiness.csv`, "
                 "`denominator.csv`")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    summary = json.loads((FIX / "summary.json").read_text(encoding="utf-8"))
    den = denominator(summary, FIX / "report.txt")

    flights = {}
    for key, meta in FLIGHTS.items():
        print(f"analyzing {key}...", flush=True)
        flights[key] = analyze_flight(key, meta)
        # write readiness CSV
        ticks = flights[key].pop("_ticks")
        csv_path = OUT / f"{key.lower()}_readiness.csv"
        if ticks:
            with csv_path.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(ticks[0].keys()))
                w.writeheader()
                w.writerows(ticks)

    with (OUT / "denominator.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(den["attempts_table"][0].keys()))
        w.writeheader()
        w.writerows(den["attempts_table"])

    bundle = {"denominator": den, "flights": flights,
              "fixture": str(FIX), "d_star": D_STAR, "engage_z": ENGAGE_Z}
    # Strip heavy samples for summary if needed — keep crossing samples
    (OUT / "summary.json").write_text(
        json.dumps(bundle, indent=2, default=str), encoding="utf-8")

    report = render_report(bundle)
    (OUT / "first-passes.md").write_text(report, encoding="utf-8")
    (ROOT / "analysis" / "2026-07-19-first-passes.md").write_text(
        report, encoding="utf-8")

    # Compact stdout
    print(json.dumps({
        "denominator": {
            "real": den["real_full_control_flights"],
            "passes": den["passes"],
            "rate": den["honest_pass_rate_str"],
        },
        "F_CLEAN": {
            "pass_t_ff": flights["F_CLEAN"]["pass"]["t_ff"],
            "pass_t_rel": flights["F_CLEAN"]["pass"]["t_rel"],
            "state_cross": flights["F_CLEAN"]["crossing_truth"].get("state_at_pass"),
            "ready": flights["F_CLEAN"]["readiness"]["ever_ready"],
            "captured": flights["F_CLEAN"]["readiness"]["ever_captured"],
            "at_cross": flights["F_CLEAN"]["at_crossing_command"],
            "chase": flights["F_CLEAN"]["post_pass"]["chase_verdict"],
        },
        "F_CLIP": {
            "pass_t_ff": flights["F_CLIP"]["pass"]["t_ff"],
            "pass_t_rel": flights["F_CLIP"]["pass"]["t_rel"],
            "state_cross": flights["F_CLIP"]["crossing_truth"].get("state_at_pass"),
            "clips": [{
                "t_ff": c["t_ff"], "impulse": c["impulse"],
                "winner": c["winner"],
            } for c in flights["F_CLIP"]["clip_attribution"]],
            "ready": flights["F_CLIP"]["readiness"]["ever_ready"],
            "captured": flights["F_CLIP"]["readiness"]["ever_captured"],
            "at_cross": flights["F_CLIP"]["at_crossing_command"],
            "chase": flights["F_CLIP"]["post_pass"]["chase_verdict"],
        },
    }, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
