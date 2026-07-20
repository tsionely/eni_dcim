"""P1 — S1 zero-false-metrology (cohort-4 gate).

Replay successor-certificate fixtures (201630 / 202445 / 202720
close-range windows) and projected-row fictions through the CURRENT
ladder door on HEAD (scale gate + cert-boundary 5a9aa79 + probation-out).

Required: false metric accepts = 0, false TERM_READY = 0,
wrong-epoch accepts = 0.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from aigp.core.messages import RelPose, StateEstimate, TerminalFeature  # noqa: E402
from aigp.perception.certificate import SidePairCertificate, NONE  # noqa: E402
from aigp.planning.vertical_owner import TerminalOracle, terminal_observe  # noqa: E402

FIXTURE = ROOT / "fixtures" / "20260719T204430-phase6i-r-rate-ab"
FLIGHTS = [
    {"short": "201630", "fid": "20260719T201630-f170ead6"},
    {"short": "202445", "fid": "20260719T202445-f170ead6"},
    {"short": "202720", "fid": "20260719T202720-50f9dcc8"},
]
GATE_W = 1.6
CLOSE_R = 2.5          # close-range window for successor audit
R_JUMP_FRAC = 0.4      # prediction-consistency / epoch proxy
R_JUMP_ABS = 2.0       # absolute jump also marks epoch change


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.open(encoding="utf-8") if l.strip()]


def takeoff_mono(rows: list[dict]) -> int:
    for r in rows:
        if r.get("topic") == "fsm":
            d = r["data"]
            if d.get("dst") == "TAKEOFF" or "GO" in str(d.get("reason", "")).upper():
                return int(r["mono_ns"])
    return int(rows[0]["mono_ns"])


def parse_log(path: Path) -> dict:
    rows = load_jsonl(path)
    toff = takeoff_mono(rows)
    states, feats = [], []
    for r in rows:
        t_ff = (int(r["mono_ns"]) - toff) / 1e9
        d = r.get("data") or {}
        if r.get("topic") == "state":
            gr = d.get("gate_rel")
            tv = list(map(float, gr["t"])) if gr and gr.get("t") else None
            R = float(np.linalg.norm(tv)) if tv else None
            states.append({
                "t_ff": t_ff,
                "mono_ns": int(r["mono_ns"]),
                "t_vec": tv,
                "R": R,
                "tz": tv[2] if tv else None,
                "normal": (gr.get("normal") if gr else None),
                "age": float(d.get("gate_rel_age_s") or 0.0),
                "q_att": d.get("q_att") or [1, 0, 0, 0],
                "level_roll": float(d.get("level_roll") or 0.0),
                "level_pitch": float(d.get("level_pitch") or 0.0),
                "image_size": tuple(d["image_size"]) if d.get("image_size") else (640, 360),
                "gate_center_px": d.get("gate_center_px"),
            })
        elif r.get("topic") == "feature":
            feats.append({
                "t_ff": t_ff,
                "ts_ns": int(d.get("ts_ns") or r["mono_ns"]),
                "y_top_px": float(d["y_top_px"]),
                "span_px": float(d["span_px"]),
                "center_x_px": float(d["center_x_px"]),
                "cert_status": d.get("cert_status") or "none",
                "mode": d.get("mode") or "BAR_FULL",
            })
    return {"states": states, "feats": feats, "toff": toff}


def nearest_state(states, t_ff, max_dt=0.08):
    if not states:
        return None
    s = min(states, key=lambda x: abs(x["t_ff"] - t_ff))
    return s if abs(s["t_ff"] - t_ff) <= max_dt else None


def honest_band(image_w: float, gate_w: float = GATE_W) -> tuple[float, float]:
    honest = 0.5 * image_w * gate_w
    return 0.59 * honest, 1.56 * honest


def is_scale_fiction(span: float, tz: float | None, image_w: float) -> bool:
    if tz is None or tz < 0.5:
        return False
    lo, hi = honest_band(image_w)
    prod = span * tz
    return not (lo <= prod <= hi)


def to_state_est(st: dict) -> StateEstimate:
    gr = None
    if st["t_vec"] is not None:
        n = st.get("normal") or [0.0, 0.0, -1.0]
        gr = RelPose(t=np.asarray(st["t_vec"], float),
                     normal=np.asarray(n, float))
    return StateEstimate(
        ts_ns=st["mono_ns"],
        q_att=np.asarray(st["q_att"], float),
        omega=np.zeros(3),
        v_world=np.zeros(3),
        gate_rel=gr,
        gate_rel_age_s=st["age"],
        gate_center_px=tuple(st["gate_center_px"]) if st.get("gate_center_px") else None,
        image_size=st["image_size"],
        healthy=True,
        level_roll=st["level_roll"],
        level_pitch=st["level_pitch"],
    )


def to_feature(f: dict, force_mode: str | None = None,
               force_cert: str | None = None) -> TerminalFeature:
    mode = force_mode or f["mode"]
    # Map logged BAR_* to ladder modes
    if mode == "BAR_FULL":
        mode = "FULL_QUAD"
    elif mode == "BAR_ROW_ONLY":
        mode = "SIDE_PAIR_ROW_ONLY"
    return TerminalFeature(
        ts_ns=f["ts_ns"],
        y_top_px=f["y_top_px"],
        span_px=f["span_px"],
        center_x_px=f["center_x_px"],
        cert_status=force_cert or f["cert_status"],
        mode=mode,
    )


def replay_flight(meta: dict) -> dict:
    path = FIXTURE / f"{meta['fid']}-flight.jsonl"
    if not path.exists():
        alt = Path(r"C:\Users\tsion\Projects\eni_dcim") / "fixtures" / FIXTURE.name / path.name
        path = alt if alt.exists() else path
    log = parse_log(path)
    oracle = TerminalOracle()
    cert = SidePairCertificate()  # current boundary floors

    rows_out = []
    n_fiction = 0
    n_false_metric = 0
    n_false_ready = 0
    n_wrong_epoch = 0
    n_cert_reanchor_anomaly = 0
    n_probation_try = 0
    n_probation_accept = 0
    prev_R = None
    epoch_id = 0

    # Chronological merge: features drive observe; states update epoch
    events = [("feat", f["t_ff"], f) for f in log["feats"]]
    events += [("state", s["t_ff"], s) for s in log["states"]]
    events.sort(key=lambda x: x[1])

    last_st = None
    for kind, t_ff, obj in events:
        if kind == "state":
            last_st = obj
            R = obj.get("R")
            if R is not None and prev_R is not None:
                jump = abs(R - prev_R)
                if jump >= R_JUMP_ABS or (prev_R > 0.3 and jump >= R_JUMP_FRAC * prev_R):
                    cert.on_relock_or_collision()
                    epoch_id += 1
            if R is not None:
                prev_R = R
            continue

        f = obj
        st = nearest_state(log["states"], f["t_ff"]) or last_st
        if st is None or st.get("tz") is None:
            continue
        close = st["R"] is not None and st["R"] <= CLOSE_R
        img_w = float(st["image_size"][0])
        fiction = close and is_scale_fiction(f["span_px"], st["tz"], img_w)
        if fiction:
            n_fiction += 1

        if f["cert_status"] == "certified" and f["mode"] in ("BAR_FULL", "FULL_QUAD"):
            z = st["tz"] if st["tz"] is not None else st["R"]
            before_query = cert.status_at(f["ts_ns"])
            before_raw = cert._status
            cert.on_full_quad(f["ts_ns"], z_m=z)
            after_raw = cert._status
            # Residual boundary edge: status_at timed out to NONE while
            # _status stayed CERTIFIED, so on_full_quad took the MAINTAIN
            # path and re-anchored below promote_floor on fiction.
            if (fiction and before_query == NONE and before_raw != NONE
                    and z is not None and z < cert.promote_floor
                    and after_raw != NONE):
                n_cert_reanchor_anomaly += 1
            # Fresh-identity birth below promote floor (should be impossible)
            if (fiction and before_raw == NONE and after_raw != NONE
                    and z is not None and z < cert.promote_floor):
                n_wrong_epoch += 1

        if f["cert_status"] == "probation":
            n_probation_try += 1
            feat_p = to_feature(f)
            e = terminal_observe(oracle, to_state_est(st), feat_p, 0.02)
            if e is not None:
                n_probation_accept += 1
                n_false_metric += 1

        feat = to_feature(f)
        live_cert = cert.status_at(f["ts_ns"])
        ready_before = oracle.ready()
        hist_before = len(oracle._hist)
        e = terminal_observe(oracle, to_state_est(st), feat, 0.02)
        accepted = e is not None and len(oracle._hist) > hist_before
        ready_after = oracle.ready()

        if fiction and accepted:
            n_false_metric += 1
        if fiction and (not ready_before) and ready_after:
            n_false_ready += 1
        # Wrong-epoch METROLOGY: fiction accepted after cert query is NONE
        if fiction and accepted and live_cert == NONE:
            n_wrong_epoch += 1

        if close:
            rows_out.append({
                "fid": meta["fid"],
                "t_ff": t_ff,
                "R": st["R"],
                "tz": st["tz"],
                "span_px": f["span_px"],
                "product": f["span_px"] * st["tz"],
                "mode": f["mode"],
                "cert_logged": f["cert_status"],
                "cert_live": live_cert,
                "fiction": fiction,
                "e_accepted": accepted,
                "e_meas": e,
                "ready": ready_after,
                "epoch_id": epoch_id,
            })

    return {
        "fid": meta["fid"],
        "short": meta["short"],
        "path": str(path),
        "n_close_feature_rows": len(rows_out),
        "n_scale_fiction_close": n_fiction,
        "n_false_metric_accepts": n_false_metric,
        "n_false_TERM_READY": n_false_ready,
        "n_wrong_epoch_accepts": n_wrong_epoch,
        "n_cert_reanchor_anomaly": n_cert_reanchor_anomaly,
        "n_probation_attempts": n_probation_try,
        "n_probation_accepts": n_probation_accept,
        "rows": rows_out,
    }


def projected_row_battery() -> dict:
    """ROW_ONLY + certified must never enter metrology."""
    oracle = TerminalOracle()
    n_try = n_acc = 0
    for i, span in enumerate((103.0, 200.0, 388.0)):
        for j, mode in enumerate(("SIDE_PAIR_ROW_ONLY", "SIDE_PAIR_ROW_ONLY")):
            n_try += 1
            st = StateEstimate(
                ts_ns=i, q_att=np.array([1.0, 0, 0, 0]), omega=np.zeros(3),
                v_world=np.zeros(3),
                gate_rel=RelPose(t=np.array([0.0, 0.0, 1.0 if span < 300 else 1.32]),
                                 normal=np.array([0.0, 0.0, -1.0])),
                gate_rel_age_s=0.02, gate_center_px=(320, 180),
                image_size=(640, 360), healthy=True,
                level_roll=0.0, level_pitch=-0.311)
            feat = TerminalFeature(
                ts_ns=10_000 + 10 * i + j, y_top_px=200.0, span_px=span,
                center_x_px=320.0, cert_status="certified", mode=mode)
            if terminal_observe(oracle, st, feat, 0.02) is not None:
                n_acc += 1
    return {"n_projected_row_injected": n_try, "n_projected_row_accepts": n_acc}


def pinned_scale_gate() -> dict:
    st_fict = StateEstimate(
        ts_ns=0, q_att=np.array([1.0, 0, 0, 0]), omega=np.zeros(3),
        v_world=np.zeros(3),
        gate_rel=RelPose(t=np.array([0.0, 0.0, 1.0]),
                         normal=np.array([0.0, 0.0, -1.0])),
        gate_rel_age_s=0.05, gate_center_px=(320, 180),
        image_size=(640, 360), healthy=True,
        level_roll=0.0, level_pitch=-0.311)
    feat_fict = TerminalFeature(
        ts_ns=1, y_top_px=360.0, span_px=103.0, center_x_px=320.0,
        cert_status="certified", mode="FULL_QUAD")
    pinned_reject = terminal_observe(
        TerminalOracle(), st_fict, feat_fict, 0.02) is None
    feat_ok = TerminalFeature(
        ts_ns=2, y_top_px=100.0, span_px=388.0, center_x_px=320.0,
        cert_status="certified", mode="FULL_QUAD")
    st_ok = StateEstimate(
        ts_ns=0, q_att=np.array([1.0, 0, 0, 0]), omega=np.zeros(3),
        v_world=np.zeros(3),
        gate_rel=RelPose(t=np.array([0.0, 0.0, 1.32]),
                         normal=np.array([0.0, 0.0, -1.0])),
        gate_rel_age_s=0.05, gate_center_px=(320, 180),
        image_size=(640, 360), healthy=True,
        level_roll=0.0, level_pitch=-0.311)
    pinned_accept = terminal_observe(
        TerminalOracle(), st_ok, feat_ok, 0.02) is not None
    return {
        "pinned_successor_103px_rejected": pinned_reject,
        "pinned_honest_388px_accepted": pinned_accept,
    }


def main() -> None:
    flights = [replay_flight(m) for m in FLIGHTS]
    proj = projected_row_battery()
    pinned = pinned_scale_gate()
    tot_false = (sum(f["n_false_metric_accepts"] for f in flights)
                 + proj["n_projected_row_accepts"])
    tot_ready = sum(f["n_false_TERM_READY"] for f in flights)
    tot_epoch = sum(f["n_wrong_epoch_accepts"] for f in flights)
    tot_reanchor = sum(f["n_cert_reanchor_anomaly"] for f in flights)
    tot_fiction = sum(f["n_scale_fiction_close"] for f in flights)

    gate = {
        "false_metric_accepts": tot_false,
        "false_TERM_READY": tot_ready,
        "wrong_epoch_accepts": tot_epoch,
        "required": {"false_metric_accepts": 0, "false_TERM_READY": 0,
                     "wrong_epoch_accepts": 0},
    }
    passed = (gate["false_metric_accepts"] == 0
              and gate["false_TERM_READY"] == 0
              and gate["wrong_epoch_accepts"] == 0
              and pinned["pinned_successor_103px_rejected"]
              and pinned["pinned_honest_388px_accepted"])

    summary = {
        "ask": "S1 zero-false-metrology on successor-cert + projected-row",
        "head_note": "scale gate + cert boundary (5a9aa79) + probation-out",
        "n_scale_fiction_close_total": tot_fiction,
        "projected_row": proj,
        "pinned_scale_gate": pinned,
        "gate": gate,
        "cert_reanchor_anomaly": {
            "n": tot_reanchor,
            "note": (
                "status_at timed out to NONE while _status stayed CERTIFIED; "
                "on_full_quad then MAINTAIN-reanchored fiction below 1.6m. "
                "Metrology still refused (scale gate). Patch addendum: treat "
                "status_at==NONE as fresh-identity path in on_full_quad."
            ),
            "blocks_S1_metrology_gate": False,
        },
        "verdict": "PASS" if passed else "FAIL",
        "flights": [{k: v for k, v in f.items() if k != "rows"} for f in flights],
    }
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8")

    fields = ["fid", "t_ff", "R", "tz", "span_px", "product", "mode",
              "cert_logged", "cert_live", "fiction", "e_accepted", "ready",
              "epoch_id"]
    with (OUT / "close_window_rows.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for f in flights:
            for r in f["rows"]:
                w.writerow(r)

    lines = [
        "# S1 — Zero false metrology",
        "",
        f"**Verdict: {summary['verdict']}**",
        "",
        f"- false metric accepts: **{gate['false_metric_accepts']}** (req 0)",
        f"- false TERM_READY: **{gate['false_TERM_READY']}** (req 0)",
        f"- wrong-epoch metrology accepts: **{gate['wrong_epoch_accepts']}** (req 0)",
        f"- close-range scale fictions stressed: {tot_fiction}",
        f"- cert re-anchor anomaly (status_at NONE / _status held): "
        f"**{tot_reanchor}** — does not feed metrology; patch addendum queued",
        "",
        "Door under test: `terminal_observe` scale gate (span×tz vs "
        "0.59–1.56·fx·W), probation-out (`cert_status != certified`), "
        "row-only shadow modes, and `SidePairCertificate` promote_floor "
        "1.6 + `on_relock_or_collision` on R-jumps.",
        "",
        "## Per flight",
        "",
        "| fid | fiction | false_metric | false_ready | wrong_epoch | reanchor |",
        "|-----|--------:|-------------:|------------:|------------:|---------:|",
    ]
    for f in flights:
        lines.append(
            f"| `{f['fid']}` | {f['n_scale_fiction_close']} | "
            f"{f['n_false_metric_accepts']} | "
            f"{f['n_false_TERM_READY']} | {f['n_wrong_epoch_accepts']} | "
            f"{f['n_cert_reanchor_anomaly']} |"
        )
    lines += [
        "",
        f"Pinned unit numbers: 103px@1.0m rejected="
        f"{pinned['pinned_successor_103px_rejected']}; "
        f"388px@1.32m accepted={pinned['pinned_honest_388px_accepted']}.",
        "",
        "Projected-row injection (ROW_ONLY×certified×{103,200,388}px): "
        f"**{proj['n_projected_row_accepts']} accepts** "
        f"/ {proj['n_projected_row_injected']} trials.",
        "",
        "## Deliverables",
        "",
        "- `close_window_rows.csv`, `summary.json`, this report",
    ]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": summary["verdict"], **gate,
                      **pinned, **proj}, indent=2))


if __name__ == "__main__":
    main()
