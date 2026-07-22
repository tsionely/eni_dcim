"""Pooled collision geometry autopsy — race-week fixtures r1..r1f.

Engineering notes (no criterion form). Mines every raceprep fixture under
the sibling eni_dcim checkout, extracts each collision (or aborting
collision + grinding samples), pairs the last detection/state before
impact, converts rel_pose to true-world vertical via
aigp.planning.approach.true_world_dz, and clusters hit class.
"""
from __future__ import annotations

import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SIBLING = Path(r"C:\Users\tsion\Projects\eni_dcim")
FIX_ROOT = SIBLING / "fixtures"

sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
from aigp.core.messages import RelPose  # noqa: E402
from aigp.planning.approach import true_world_dz  # noqa: E402

GATE_ID = 1001
ENV_ID = 1002
PHASE_RE = re.compile(
    r"(\d{8}T\d{6})-raceprep-(r1(?:-alt)?[b-f]?)-(A|B)-run(\d+)",
    re.I,
)


def fnum(v):
    if v is None or v == "":
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def discover_fixtures() -> list[dict]:
    out = []
    if not FIX_ROOT.is_dir():
        return out
    for d in sorted(FIX_ROOT.iterdir()):
        if not d.is_dir():
            continue
        m = PHASE_RE.search(d.name)
        if not m:
            continue
        logs = list(d.glob("*-flight.jsonl"))
        results = list(d.glob("*-result.json"))
        if not logs:
            continue
        out.append({
            "fixture_dir": d,
            "label": f"{m.group(2)}-{m.group(3)}-run{m.group(4)}",
            "series": m.group(2),
            "config": m.group(3),
            "run": int(m.group(4)),
            "flight_jsonl": logs[0],
            "result_json": results[0] if results else None,
            "notes": d / "notes.md",
            "run_summary": d / "run-summary.json",
        })
    return out


def load_result(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def classify_hit(det: dict | None, state: dict | None,
                 collision_id: int, tw_dz: float | None,
                 range_z: float | None, cx: float | None,
                 cy: float | None, tx: float | None,
                 ty_cam: float | None) -> str:
    """Heuristic engineering cluster — not a pass criterion."""
    if collision_id == GATE_ID:
        # Gate clip: which structure from image + true vertical
        if range_z is not None and range_z > 8.0:
            return "gate_clip_far_or_wrong_lock"
        if tw_dz is not None:
            # +tw_dz = gate BELOW me = we are HIGH → top bar / banner
            # -tw_dz = gate ABOVE me = we are LOW → bottom bar
            if tw_dz >= 0.35:
                if cy is not None and cy < 140:
                    return "gate_TOP_or_BANNER"
                return "gate_TOP_bar"
            if tw_dz <= -0.35:
                return "gate_BOTTOM_bar"
        if cy is not None:
            if cy < 120:
                return "gate_TOP_or_BANNER"
            if cy > 280:
                return "gate_BOTTOM_bar"
        if cx is not None and (cx < 120 or cx > 520):
            return "gate_SIDE_bar"
        if tx is not None and abs(tx) > 0.55 and (range_z or 99) < 4.0:
            return "gate_SIDE_bar"
        return "gate_OPENING_or_UNSPECIFIED"

    # Environment
    if det is None or range_z is None:
        return "env_NO_GATE_IN_VIEW"
    if range_z > 12.0:
        return "env_FAR_STRUCTURE_or_hangar"
    if range_z > 5.0:
        return "env_MID_STRUCTURE_intergate"
    # Close env hit with a gate still in view — often pillar/floor near gate
    if tw_dz is not None and tw_dz <= -0.5 and (range_z or 99) < 3.5:
        return "env_NEAR_gate_LOW_likely_floor_or_bottom"
    if tw_dz is not None and tw_dz >= 0.5 and (range_z or 99) < 3.5:
        return "env_NEAR_gate_HIGH_likely_banner_or_top_environs"
    if cx is not None and (cx < 80 or cx > 560) and (range_z or 99) < 4.0:
        return "env_NEAR_gate_LATERAL_likely_pillar_or_side_struct"
    return "env_NEAR_STRUCTURE_unspecified"


def nearest_before(events: list[tuple[int, dict]], mono_ns: int,
                   max_age_s: float = 0.5) -> dict | None:
    """events: list of (mono_ns, payload) sorted ascending."""
    best = None
    for m, payload in events:
        if m > mono_ns:
            break
        if (mono_ns - m) / 1e9 <= max_age_s:
            best = payload
    return best


def last_detection_rel(det: dict) -> tuple[RelPose | None, float | None, float | None]:
    rp = det.get("rel_pose")
    if not rp or "t" not in rp:
        return None, None, None
    t = rp["t"]
    if len(t) < 3:
        return None, None, None
    n = rp.get("normal") or [0.0, 0.0, 1.0]
    rel = RelPose(t=np.asarray(t, dtype=float),
                  normal=np.asarray(n, dtype=float))
    cx = cy = None
    c = det.get("center_px")
    if c and len(c) >= 2:
        cx, cy = float(c[0]), float(c[1])
    return rel, cx, cy


def process_flight(fx: dict) -> tuple[list[dict], dict]:
    path = fx["flight_jsonl"]
    result = load_result(fx["result_json"])
    collisions: list[tuple[int, dict]] = []
    detections: list[tuple[int, dict]] = []
    states: list[tuple[int, dict]] = []
    setpoints: list[tuple[int, dict]] = []
    fsm: list[tuple[int, dict]] = []
    gate_idx_events: list[tuple[int, int]] = []

    with path.open(encoding="utf-8") as fh:
        for line in fh:
            o = json.loads(line)
            topic = o.get("topic")
            mono = int(o.get("mono_ns") or 0)
            data = o.get("data") or {}
            if topic == "collision":
                collisions.append((mono, data))
            elif topic == "detection":
                detections.append((mono, data))
            elif topic == "state":
                states.append((mono, data))
            elif topic == "setpoint":
                setpoints.append((mono, data))
            elif topic == "fsm":
                fsm.append((mono, data))
            elif topic in ("race", "hud", "agi"):
                # optional gate index fields
                for k in ("gates_passed", "agi", "agi_max", "gate_index", "current_gate"):
                    if k in data and data[k] is not None:
                        try:
                            gate_idx_events.append((mono, int(data[k])))
                        except (TypeError, ValueError):
                            pass

    detections.sort(key=lambda x: x[0])
    states.sort(key=lambda x: x[0])
    setpoints.sort(key=lambda x: x[0])
    collisions.sort(key=lambda x: x[0])

    abort_reason = result.get("abort_reason") or ""
    env_hits = int(result.get("env_hits") or 0)
    gate_clips = int(result.get("gate_clips") or 0)
    gates_passed = int(result.get("gates_passed") or 0)
    duration_s = fnum(result.get("duration_s"))

    # Grinding class: huge env_hits + timeout abort
    is_grinding = (
        env_hits >= 5000
        and ("timeout" in abort_reason.lower() or env_hits >= 10000)
    )

    rows: list[dict] = []

    def gate_index_at(mono: int) -> int | None:
        best = None
        for m, g in gate_idx_events:
            if m <= mono:
                best = g
            else:
                break
        if best is not None:
            return best
        # fallback: gates_passed from result is end-state
        return gates_passed

    def enrich(mono: int, data: dict, sample_kind: str) -> dict:
        det_p = nearest_before(detections, mono, max_age_s=0.6)
        st_p = nearest_before(states, mono, max_age_s=0.25)
        sp_p = nearest_before(setpoints, mono, max_age_s=0.25)
        cid = int(data.get("collision_id") or 0)
        impulse = fnum(data.get("impulse"))
        threat = data.get("threat_level")

        rel = None
        cx = cy = None
        range_z = tx = ty = None
        tw_dz = None
        det_age_s = None
        det_cert = None
        q_att = level_roll = level_pitch = None
        phase = None
        v_body = None

        if det_p is not None:
            # age from mono of detection event — find its mono
            det_mono = None
            for m, d in reversed(detections):
                if m <= mono and d is det_p:
                    det_mono = m
                    break
            if det_mono is not None:
                det_age_s = (mono - det_mono) / 1e9
            rel, cx, cy = last_detection_rel(det_p)
            det_cert = det_p.get("cert_status")
            if rel is not None:
                range_z = float(rel.t[2])
                tx = float(rel.t[0])
                ty = float(rel.t[1])

        if st_p is not None:
            q = st_p.get("q_att")
            if q is not None:
                q_att = np.asarray(q, dtype=float)
            level_roll = float(st_p.get("level_roll") or 0.0)
            level_pitch = float(st_p.get("level_pitch") or 0.0)
            # Prefer detection rel; else state.gate_rel
            if rel is None and st_p.get("gate_rel") and st_p["gate_rel"].get("t"):
                t = st_p["gate_rel"]["t"]
                n = st_p["gate_rel"].get("normal") or [0, 0, 1]
                rel = RelPose(t=np.asarray(t, dtype=float),
                              normal=np.asarray(n, dtype=float))
                range_z = float(rel.t[2])
                tx = float(rel.t[0])
                ty = float(rel.t[1])
                cpx = st_p.get("gate_center_px")
                if cpx and len(cpx) >= 2:
                    cx, cy = float(cpx[0]), float(cpx[1])

        if rel is not None and q_att is not None:
            try:
                tw_dz = true_world_dz(rel, q_att, level_roll or 0.0,
                                      level_pitch or 0.0)
            except Exception:
                tw_dz = None

        if sp_p is not None:
            phase = sp_p.get("phase")
            vb = sp_p.get("v_body")
            if vb is not None:
                v_body = [float(x) for x in vb]

        hit_class = classify_hit(
            det_p, st_p, cid, tw_dz, range_z, cx, cy, tx, ty
        )

        return {
            "series": fx["series"],
            "label": fx["label"],
            "config": fx["config"],
            "run": fx["run"],
            "flight_id": path.name.replace("-flight.jsonl", ""),
            "fixture": fx["fixture_dir"].name,
            "sample_kind": sample_kind,
            "is_grinding_flight": is_grinding,
            "mono_ns": mono,
            "collision_id": cid,
            "collision_kind": "gate" if cid == GATE_ID else (
                "environment" if cid == ENV_ID else f"id_{cid}"
            ),
            "threat_level": threat,
            "impulse": impulse,
            "planner_phase": phase,
            "v_body": json.dumps(v_body) if v_body is not None else "",
            "v_body_x": v_body[0] if v_body else None,
            "v_body_y": v_body[1] if v_body else None,
            "v_body_z": v_body[2] if v_body else None,
            "gate_index_proxy": gate_index_at(mono),
            "det_age_s": det_age_s,
            "det_cert": det_cert,
            "range_z_m": range_z,
            "tx_m": tx,
            "ty_cam_m": ty,
            "true_world_dz_m": tw_dz,
            "center_x_px": cx,
            "center_y_px": cy,
            "hit_class": hit_class,
            "abort_reason": abort_reason,
            "env_hits_total": env_hits,
            "gate_clips_total": gate_clips,
            "gates_passed": gates_passed,
            "duration_s": duration_s,
        }

    if is_grinding:
        # Sample: first, every ~N, last, plus max-impulse
        n = len(collisions)
        if n == 0:
            return rows, {"label": fx["label"], "grinding": True, "n_collisions": 0}
        idxs = {0, n - 1}
        step = max(1, n // 20)
        for i in range(0, n, step):
            idxs.add(i)
        # max impulse among env
        max_i = max(range(n), key=lambda i: fnum(collisions[i][1].get("impulse")) or 0.0)
        idxs.add(max_i)
        for i in sorted(idxs):
            mono, data = collisions[i]
            rows.append(enrich(mono, data, sample_kind=f"grinding_sample_{i}"))
        # Also a dedicated summary row marker
        return rows, {
            "label": fx["label"],
            "grinding": True,
            "n_collisions": n,
            "env_hits": env_hits,
            "abort_reason": abort_reason,
            "duration_s": duration_s,
            "unique_collision_ids": sorted({int(c[1].get("collision_id") or 0) for c in collisions}),
            "threat_levels": dict(Counter(int(c[1].get("threat_level") or 0) for c in collisions)),
            "impulse_p50": statistics_percentile(
                [fnum(c[1].get("impulse")) for c in collisions], 50),
            "impulse_p95": statistics_percentile(
                [fnum(c[1].get("impulse")) for c in collisions], 95),
            "impulse_max": max((fnum(c[1].get("impulse")) or 0) for c in collisions),
        }

    # Non-grinding: every collision event (may be dozens; cap very large)
    if len(collisions) > 400:
        # still sample densely but not explode CSV
        step = max(1, len(collisions) // 200)
        chosen = list(range(0, len(collisions), step))
        if (len(collisions) - 1) not in chosen:
            chosen.append(len(collisions) - 1)
        for i in chosen:
            mono, data = collisions[i]
            rows.append(enrich(mono, data, sample_kind="collision_sampled"))
    else:
        for mono, data in collisions:
            rows.append(enrich(mono, data, sample_kind="collision"))

    # Ensure aborting collision is represented: last collision before ABORTED fsm
    abort_mono = None
    for m, d in fsm:
        if d.get("dst") == "ABORTED":
            abort_mono = m
            break
    if abort_mono is not None and collisions:
        last = None
        for mono, data in collisions:
            if mono <= abort_mono:
                last = (mono, data)
        if last is not None:
            # mark a duplicate-ok abort-focused row
            row = enrich(last[0], last[1], sample_kind="abort_collision")
            rows.append(row)

    return rows, {
        "label": fx["label"],
        "grinding": False,
        "n_collisions": len(collisions),
        "env_hits": env_hits,
        "gate_clips": gate_clips,
        "abort_reason": abort_reason,
        "gates_passed": gates_passed,
        "duration_s": duration_s,
    }


def statistics_percentile(vals, pct):
    xs = sorted(v for v in vals if v is not None)
    if not xs:
        return None
    if len(xs) == 1:
        return xs[0]
    pos = pct / 100.0 * (len(xs) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    frac = pos - lo
    return xs[lo] * (1 - frac) + xs[hi] * frac


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    # Flight summaries differ for grinding and normal flights.  Preserve
    # every available column rather than letting DictWriter reject the
    # grinding-only percentile and threat fields.
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    fixtures = discover_fixtures()
    all_rows: list[dict] = []
    flight_summaries: list[dict] = []
    grinding_summaries: list[dict] = []

    for fx in fixtures:
        rows, summary = process_flight(fx)
        all_rows.extend(rows)
        flight_summaries.append(summary)
        if summary.get("grinding"):
            grinding_summaries.append(summary)

    write_csv(OUT / "collision_events.csv", all_rows)
    write_csv(OUT / "flight_summaries.csv", flight_summaries)

    # Cluster counts (exclude grinding samples from main gate/env cluster table
    # but include abort_collision + collision*)
    cluster = Counter()
    cluster_gate = Counter()
    cluster_env = Counter()
    by_series = defaultdict(Counter)
    for r in all_rows:
        if r.get("is_grinding_flight") and str(r.get("sample_kind", "")).startswith("grinding_"):
            continue
        if r.get("sample_kind") == "abort_collision":
            # prefer unique abort rows for cluster of killing hits
            pass
        hc = r.get("hit_class") or "unknown"
        cluster[hc] += 1
        by_series[r["series"]][hc] += 1
        if r.get("collision_kind") == "gate":
            cluster_gate[hc] += 1
        else:
            cluster_env[hc] += 1

    # Aborting-hit focused table
    abort_rows = [r for r in all_rows if r.get("sample_kind") == "abort_collision"]
    write_csv(OUT / "abort_collisions.csv", abort_rows)

    abort_cluster = Counter(r["hit_class"] for r in abort_rows)

    summary = {
        "n_fixtures": len(fixtures),
        "series": sorted({fx["series"] for fx in fixtures}),
        "n_collision_rows_logged": len(all_rows),
        "n_abort_collisions": len(abort_rows),
        "n_grinding_flights": len(grinding_summaries),
        "grinding": grinding_summaries,
        "hit_class_all_non_grinding_samples": dict(cluster),
        "hit_class_abort_collisions": dict(abort_cluster),
        "hit_class_gate_clips": dict(cluster_gate),
        "hit_class_env": dict(cluster_env),
        "by_series": {k: dict(v) for k, v in by_series.items()},
        "fixture_root": str(FIX_ROOT),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    # Engineering notes report
    lines = [
        "# Pooled collision geometry — race-week fixtures (engineering notes)",
        "",
        f"Scope: `{FIX_ROOT}` — series {', '.join(summary['series'])} "
        f"({summary['n_fixtures']} fixtures).",
        "Conversion: last detection `rel_pose` → `true_world_dz` "
        "(`aigp.planning.approach`, PYTHONPATH=src). "
        "`+true_world_dz` = gate below aircraft (we are HIGH).",
        "",
        "## Grinding timeouts (separate class)",
        "",
    ]
    if grinding_summaries:
        for g in grinding_summaries:
            lines.append(
                f"- **{g['label']}**: {g.get('n_collisions')} collision events, "
                f"env_hits={g.get('env_hits')}, abort=`{g.get('abort_reason')}`, "
                f"duration={g.get('duration_s')}s, "
                f"threat_levels={g.get('threat_levels')}, "
                f"impulse p50/p95/max="
                f"{g.get('impulse_p50')}/{g.get('impulse_p95')}/{g.get('impulse_max')}, "
                f"collision_ids={g.get('unique_collision_ids')}"
            )
        lines += [
            "",
            "Both are sustained **environment** scrapes at `threat_level=1` "
            "(below the abort threshold of 2), so Safety never trips — the "
            "wall-clock / max-duration timeout ends the flight. They are "
            "NOT gate-clip budgets and NOT single hard impacts.",
            "",
        ]
        # Characterize grinding geometry from samples
        grind_rows = [r for r in all_rows if r.get("is_grinding_flight")]
        gc = Counter(r["hit_class"] for r in grind_rows)
        lines.append(f"Sampled grinding hit_class histogram: `{dict(gc)}`")
        # ranges
        ranges = [r["range_z_m"] for r in grind_rows if r.get("range_z_m") is not None]
        tws = [r["true_world_dz_m"] for r in grind_rows if r.get("true_world_dz_m") is not None]
        phases = Counter(r["planner_phase"] for r in grind_rows)
        lines.append(
            f"Sampled range_z median/min/max: "
            f"{statistics_percentile(ranges,50)} / "
            f"{min(ranges) if ranges else None} / {max(ranges) if ranges else None}"
        )
        lines.append(
            f"Sampled true_world_dz median: {statistics_percentile(tws,50)}; "
            f"phases={dict(phases)}"
        )
        lines.append("")
    else:
        lines.append("- (none found)")
        lines.append("")

    lines += [
        "## Aborting collisions — hit class cluster",
        "",
        "One row per flight: the last collision at/before FSM `ABORTED` "
        "(excludes grinding timeouts).",
        "",
        "| label | kind | phase | impulse | range_z | true_dz | center_xy | gate# | hit_class | abort |",
        "|---|---|---|---:|---:|---:|---|---:|---|---|",
    ]
    for r in sorted(abort_rows, key=lambda x: (x["series"], x["run"])):
        lines.append(
            f"| {r['label']} | {r['collision_kind']} | {r['planner_phase']} | "
            f"{r['impulse']} | {r['range_z_m']} | {r['true_world_dz_m']} | "
            f"[{r['center_x_px']},{r['center_y_px']}] | {r['gate_index_proxy']} | "
            f"`{r['hit_class']}` | {r['abort_reason'][:40]} |"
        )

    lines += [
        "",
        f"Abort hit_class counts: `{dict(abort_cluster)}`",
        "",
        "## Interpretation (engineering)",
        "",
        "- **Gate clips (1001):** classify by true-world vertical + image "
        "row. Positive `true_world_dz` + high image (small y) → TOP bar / "
        "banner; negative → BOTTOM bar; extreme u / center_x → SIDE.",
        "- **Env hits (1002) with a near gate in view:** often inter-gate "
        "structure (pillar / parked aircraft / hangar steel) while still "
        "locked or recently locked; far range → hangar/far structure.",
        "- **Env with no detection:** blind contact — strongest signal of "
        "obstacle outside the perception FOV during search/recover.",
        "- **Grinding class (r1c-B4, r1f-B8):** continuous threat-1 env "
        "contacts; geometry from samples says what they were pressed "
        "against while the timeout clock ran.",
        "",
        "## Deliverables",
        "",
        "- `collision_events.csv` — all mined collision rows (+ grinding samples)",
        "- `abort_collisions.csv` — killing hit per non-grinding flight",
        "- `flight_summaries.csv`",
        "- `summary.json`",
        "",
    ]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "n_fixtures": len(fixtures),
        "n_rows": len(all_rows),
        "n_abort": len(abort_rows),
        "grinding": [g["label"] for g in grinding_summaries],
        "abort_cluster": dict(abort_cluster),
    }))


if __name__ == "__main__":
    main()
