"""L1 perception replay for phase6l F2/F4.

QA & MOCK-TUNER scope: recorded video replay only. This harness replays the
committed phase6l .aigprec video through the current detector + close tracker,
then feeds freshly emitted TerminalFeature rows into the current TerminalOracle.
It writes only under tuning/.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from aigp.core.messages import CameraFrame, ImuSample, RelPose, TerminalFeature  # noqa: E402
from aigp.core.params import ParamSet  # noqa: E402
from aigp.estimation.state_estimator import StateEstimator  # noqa: E402
from aigp.main import apply_patches  # noqa: E402
from aigp.perception.close_tracker import GateCloseTracker  # noqa: E402
from aigp.perception.gate_detector_hsv import HsvGateDetector  # noqa: E402
from aigp.planning.vertical_owner import TerminalOracle, terminal_observe  # noqa: E402
from aigp.planning.vertical_terminal import robust_slope  # noqa: E402
from scripts.reflight import load_frame_monos, load_frames, load_imu  # noqa: E402


LOCK_PATH = Path("C:/Temp/eni_dcim_sim.lock")
TARGETS = [
    {
        "label": "F2",
        "flight_id": "20260720T071112-cd18c5fb",
        "recording": "fixtures/20260720T071602-phase6l-cohort-3/20260720T071112-cd18c5fb_takeoff_to_end.aigprec",
        "log": "fixtures/20260720T071602-phase6l-cohort-3/20260720T071112-cd18c5fb-flight.jsonl",
        "contact_offset_m": 0.162,
    },
    {
        "label": "F4",
        "flight_id": "20260720T071333-cd18c5fb",
        "recording": "fixtures/20260720T071602-phase6l-cohort-3/20260720T071333-cd18c5fb_takeoff_to_end.aigprec",
        "log": "fixtures/20260720T071602-phase6l-cohort-3/20260720T071333-cd18c5fb-flight.jsonl",
        "contact_offset_m": 0.162,
    },
]


def fnum(value) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(out):
        return None
    return out


def mean(values: list[float]) -> float | None:
    vals = [v for v in values if math.isfinite(v)]
    return statistics.fmean(vals) if vals else None


def median(values: list[float]) -> float | None:
    vals = [v for v in values if math.isfinite(v)]
    return statistics.median(vals) if vals else None


def sample_std(values: list[float]) -> float | None:
    vals = [v for v in values if math.isfinite(v)]
    return statistics.stdev(vals) if len(vals) >= 2 else None


def rms_centered(values: list[float]) -> float | None:
    vals = [v for v in values if math.isfinite(v)]
    if len(vals) < 2:
        return None
    m = statistics.fmean(vals)
    return math.sqrt(statistics.fmean([(v - m) ** 2 for v in vals]))


def fmt(value, digits: int = 3) -> str:
    value = fnum(value)
    return "n/a" if value is None else f"{value:.{digits}f}"


def fmt_pct(value, digits: int = 1) -> str:
    value = fnum(value)
    return "n/a" if value is None else f"{100.0 * value:.{digits}f}%"


def git_head() -> tuple[str, str]:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"],
                                   cwd=ROOT, text=True).strip()
    return head, head[:7]


def assert_mock_safe() -> None:
    if LOCK_PATH.exists():
        raise SystemExit(f"SIM lock exists; refusing replay: {LOCK_PATH}")
    # Never launch or kill the real sim. Just refuse to run if visible.
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command",
             "Get-Process FlightSim,DCGame -ErrorAction SilentlyContinue | "
             "Select-Object -ExpandProperty Id"],
            text=True,
        )
    except subprocess.CalledProcessError:
        out = ""
    if out.strip():
        raise SystemExit(f"FlightSim/DCGame process visible; refusing replay: {out.strip()}")


def read_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def load_level_ref(log_path: Path) -> tuple[float, float]:
    for rec in read_jsonl(log_path):
        if rec.get("topic") != "state":
            continue
        data = rec.get("data", {})
        if data.get("level_pitch") is not None:
            return float(data.get("level_roll") or 0.0), float(data["level_pitch"])
    # Fallback: derive from the first quiet IMU samples.
    accels = []
    for rec in read_jsonl(log_path):
        if rec.get("topic") == "imu":
            accels.append(np.asarray(rec["data"]["accel"], dtype=np.float64))
            if len(accels) >= 50:
                break
    if not accels:
        return 0.0, 0.0
    ax, ay, az = np.mean(accels, axis=0)
    return float(np.arctan2(-ay, -az)), float(np.arctan2(ax, np.sqrt(ay * ay + az * az)))


def load_setpoint_phases(log_path: Path) -> list[tuple[int, str]]:
    phases = []
    for rec in read_jsonl(log_path):
        if rec.get("topic") == "setpoint":
            phases.append((int(rec.get("mono_ns", 0)), rec.get("data", {}).get("phase", "")))
    phases.sort()
    return phases


def phase_at(phases: list[tuple[int, str]], mono_ns: int) -> str:
    out = ""
    for ts, phase in phases:
        if ts > mono_ns:
            break
        out = phase
    return out


def gate_range_z(state) -> float | None:
    if state.gate_rel is None:
        return None
    return float(state.gate_rel.t[2])


def feature_from_full(det) -> TerminalFeature | None:
    if det is None or det.rel_pose is None or det.cert_status != "certified":
        return None
    c = np.asarray(det.corners_px, dtype=np.float64)
    span = float(np.hypot(*(c[1] - c[0])))
    if span <= 1.0:
        return None
    return TerminalFeature(
        ts_ns=int(det.ts_ns),
        y_top_px=float((c[0][1] + c[1][1]) / 2.0),
        span_px=span,
        center_x_px=float((c[0][0] + c[1][0]) / 2.0),
        cert_status=det.cert_status,
        mode="FULL_QUAD",
    )


def feature_e_meas(params: ParamSet, state, feature: TerminalFeature,
                   pitch_cal_rad: float | None = None) -> tuple[float | None, str]:
    if feature is None:
        return None, "no_feature"
    if feature.span_px <= 1.0:
        return None, "span_le_1"
    if feature.cert_status not in ("certified", "probation"):
        return None, "not_certified"
    if getattr(feature, "mode", "FULL_QUAD") in ("BAR_ROW_ONLY", "SIDE_PAIR_ROW_ONLY"):
        return None, "row_only_shadow"
    if state.image_size is None:
        return None, "no_image_size"
    gate_w = float(params.get("perception.gate.width_m"))
    d_star = float(params.get("planner.terminal.d_star_m"))
    e_clamp = float(params.get("planner.terminal.e_z_clamp_m"))
    pitch_cal = (float(params.get("planner.terminal.pitch_cal_rad"))
                 if pitch_cal_rad is None else float(pitch_cal_rad))
    if state.gate_rel is not None:
        r_b = float(state.gate_rel.t[2])
        honest = 0.5 * float(state.image_size[0]) * gate_w
        product = float(feature.span_px) * r_b
        if r_b >= 0.5 and not (0.59 * honest <= product <= 1.56 * honest):
            return None, "scale_gate"
    cy = state.image_size[1] / 2.0
    fx = state.image_size[0] / 2.0
    e_meas = gate_w * (cy - float(feature.y_top_px)) / float(feature.span_px) - d_star
    q = np.asarray(state.q_att, dtype=np.float64)
    pitch_t = float(np.arcsin(np.clip(
        2.0 * (q[0] * q[2] - q[3] * q[1]), -1.0, 1.0))) + float(state.level_pitch)
    e_meas += gate_w * fx * (np.tan(pitch_t) - np.tan(pitch_cal)) / float(feature.span_px)
    return float(np.clip(e_meas, -e_clamp, e_clamp)), "ok"


@dataclass
class ReplayOptions:
    label: str = "baseline"
    drop_all_window_s: float = 0.0
    drop_full_below_m: float | None = None
    drop_full_all: bool = False


def should_feed_feature(row: dict, opts: ReplayOptions,
                        first_below_2_ts: float | None) -> bool:
    if opts.drop_full_all and row["feature_mode"] == "FULL_QUAD":
        return False
    if opts.drop_full_below_m is not None and row["feature_mode"] == "FULL_QUAD":
        r = fnum(row.get("range_z_m"))
        if r is not None and r <= opts.drop_full_below_m:
            return False
    if opts.drop_all_window_s > 0.0 and first_below_2_ts is not None:
        t = float(row["t_rel_s"])
        if first_below_2_ts <= t <= first_below_2_ts + opts.drop_all_window_s:
            return False
    return True


def replay_oracle_from_rows(params: ParamSet, rows: list[dict],
                            opts: ReplayOptions) -> tuple[list[dict], list[dict]]:
    oracle = TerminalOracle()
    timeline = []
    transitions = []
    first_below_2_ts = None
    prev_source = oracle.active_source
    for row in rows:
        if not row.get("commit"):
            continue
        r = fnum(row.get("range_z_m"))
        if r is not None and r <= 2.0 and first_below_2_ts is None:
            first_below_2_ts = float(row["t_rel_s"])
        fed = should_feed_feature(row, opts, first_below_2_ts)
        e_meas = fnum(row.get("e_meas")) if (
            fed
            and row.get("cert_status") == "certified"
            and row.get("feature_mode") in ("FULL_QUAD", "SIDE_PAIR")
        ) else None
        if e_meas is not None:
            oracle.observe(float(row["feature_ts_ns"]) / 1e9, e_meas,
                           source=row["feature_mode"])
        if oracle.active_source != prev_source:
            transitions.append({
                "sweep": opts.label,
                "flight": row["flight"],
                "t_rel_s": row["t_rel_s"],
                "range_z_m": row.get("range_z_m", ""),
                "from_source": prev_source,
                "to_source": oracle.active_source,
            })
            prev_source = oracle.active_source
        n, span, gap = oracle.history_stats()
        timeline.append({
            **row,
            "sweep": opts.label,
            "fed": fed,
            "active_source": oracle.active_source,
            "ready": oracle.ready(),
            "ready_legacy": oracle.ready_legacy(),
            "hist_n": n,
            "hist_span_s": span,
            "hist_gap_s": gap,
            "oracle_e_z": oracle.e_z if oracle.e_z is not None else "",
        })
    return timeline, transitions


def source_residuals(rows: list[dict]) -> dict:
    full = [r for r in rows if r.get("feature_mode") == "FULL_QUAD" and fnum(r.get("e_meas")) is not None]
    side = [r for r in rows if r.get("feature_mode") == "SIDE_PAIR" and fnum(r.get("e_meas")) is not None]
    residual_rows = []
    for s in side:
        st = float(s["feature_ts_ns"]) / 1e9
        candidates = []
        for f in full:
            ft = float(f["feature_ts_ns"]) / 1e9
            dt = abs(st - ft)
            if dt <= 0.15:
                candidates.append((dt, f))
        if not candidates:
            continue
        _, f = min(candidates, key=lambda x: x[0])
        residual_rows.append({
            "flight": s["flight"],
            "side_frame_id": s["frame_id"],
            "full_frame_id": f["frame_id"],
            "range_z_m": s.get("range_z_m", ""),
            "dt_s": abs(float(s["feature_ts_ns"]) - float(f["feature_ts_ns"])) / 1e9,
            "side_e_z": s["e_meas"],
            "full_e_z": f["e_meas"],
            "residual_e_m": float(s["e_meas"]) - float(f["e_meas"]),
        })
    residuals = [float(r["residual_e_m"]) for r in residual_rows]
    residual_rows.sort(key=lambda r: (r["flight"], float(r["range_z_m"] or 999.0)))
    derivs = []
    for flight in sorted({r["flight"] for r in residual_rows}):
        rs = [r for r in residual_rows if r["flight"] == flight]
        rs.sort(key=lambda r: float(r["side_frame_id"]))
        for a, b in zip(rs, rs[1:]):
            dt = abs(float(b["dt_s"]) - float(a["dt_s"]))
            # Use feature time from frame id ordering fallback; most paired dt_s are near zero.
            fa = next((x for x in side if x["flight"] == flight and x["frame_id"] == a["side_frame_id"]), None)
            fb = next((x for x in side if x["flight"] == flight and x["frame_id"] == b["side_frame_id"]), None)
            if fa is not None and fb is not None:
                dt = (float(fb["feature_ts_ns"]) - float(fa["feature_ts_ns"])) / 1e9
            if dt > 1e-3:
                derivs.append((float(b["residual_e_m"]) - float(a["residual_e_m"])) / dt)
    return {
        "rows": residual_rows,
        "n_overlap": len(residual_rows),
        "bias_e_m": mean(residuals),
        "sigma_e_m": rms_centered(residuals),
        "std_e_m": sample_std(residuals),
        "sigma_v_mps": rms_centered(derivs),
        "std_v_mps": sample_std(derivs),
    }


def run_video_replay(params: ParamSet, target: dict) -> tuple[list[dict], dict]:
    rec_path = ROOT / target["recording"]
    log_path = ROOT / target["log"]
    level_roll, level_pitch = load_level_ref(log_path)
    phases = load_setpoint_phases(log_path)
    frame_monos = load_frame_monos(str(log_path))
    frames = load_frames(str(rec_path), frame_monos)
    imu = load_imu(str(log_path))
    if not frames or not imu:
        raise RuntimeError(f"missing frames or imu for {target['label']}")

    detector = HsvGateDetector(params)
    tracker = GateCloseTracker(params, detector)
    parallel_below_m = float(params.get("perception.close_tracker.parallel_below_m",
                                        default=3.5))
    est = StateEstimator(params)
    est.set_level_reference(level_roll, level_pitch)
    est.attitude.set_attitude_euler(level_roll, level_pitch)

    t_warm = frames[0][0] - int(3.0 * 1e9)
    events = ([("imu", t, (ts, a, g)) for t, ts, a, g in imu if t >= t_warm]
              + [("frame", mono, (fid, sim_ns, img)) for mono, fid, sim_ns, img in frames])
    events.sort(key=lambda e: e[1])
    t0 = events[0][1]

    rows = []
    last_full_mono = None
    raw_detector_fixes = 0
    tracker_fixes = 0
    feature_side_rows = 0
    center_only = 0
    for kind, mono, payload in events:
        if kind == "imu":
            ts, accel, gyro = payload
            est.predict(ImuSample(ts_ns=ts, accel=accel, gyro=gyro))
            continue

        fid, sim_ns, img = payload
        phase = phase_at(phases, mono)
        state_before = est.state
        prior = gate_range_z(state_before) if state_before.gate_rel is not None \
            and state_before.gate_rel_age_s < 1.0 else None
        frame = CameraFrame(frame_id=int(fid), ts_ns=int(sim_ns), image=img)
        det = detector.detect(frame, prior)
        emitted: list[tuple[str, str, TerminalFeature, object]] = []
        center_hint = None

        if det is not None and det.rel_pose is not None:
            raw_detector_fixes += 1
            anchored = False
            if det.confidence >= 0.55:
                last_full_mono = mono
            if det.cert_status == "certified":
                r_fix = float(np.linalg.norm(det.rel_pose.t))
                if prior is None or abs(r_fix - prior) <= 0.4 * prior:
                    tracker.certificate.on_full_quad(det.ts_ns)
                    anchored = True
            est.update_vision(det)
            feat = feature_from_full(det) if anchored else None
            if feat is not None:
                emitted.append(("feature", "detector", feat, det))
            if (anchored and tracker.enabled and det.rel_pose is not None
                    and float(det.rel_pose.t[2]) <= parallel_below_m):
                tracked_side = tracker.track(frame, det.rel_pose,
                                             center_hint_px=det.center_px)
                if tracked_side is not None and tracker.last_feature is not None:
                    feature_side_rows += 1
                    emitted.append(("feature_side", "tracker_parallel",
                                    tracker.last_feature, tracked_side))
        elif det is not None:
            center_only += 1
            center_hint = det.center_px

        if (det is None or det.rel_pose is None) and tracker.enabled \
                and last_full_mono is not None \
                and (mono - last_full_mono) / 1e9 <= tracker.max_solo_s \
                and est.state.gate_rel is not None:
            tracked = tracker.track(frame, est.state.gate_rel, center_hint_px=center_hint)
            if tracked is not None:
                tracker_fixes += 1
                est.update_vision(tracked)
                if tracker.last_feature is not None:
                    emitted.append(("feature", "tracker", tracker.last_feature, tracked))

        for topic, source, feat, used_det in emitted:
            state = est.state
            e_meas, reject = feature_e_meas(params, state, feat)
            r_z = gate_range_z(state)
            t = state.gate_rel.t if state.gate_rel is not None else np.array([math.nan] * 3)
            rows.append({
                "flight": target["label"],
                "flight_id": target["flight_id"],
                "frame_id": int(fid),
                "mono_ns": int(mono),
                "t_rel_s": (int(mono) - t0) / 1e9,
                "feature_ts_ns": int(feat.ts_ns),
                "topic": topic,
                "phase": phase,
                "commit": phase == "commit",
                "source": source,
                "feature_mode": feat.mode,
                "cert_status": feat.cert_status,
                "range_z_m": r_z if r_z is not None else "",
                "range_norm_m": float(np.linalg.norm(t)) if np.isfinite(t).all() else "",
                "x_m": float(t[0]) if np.isfinite(t).all() else "",
                "y_down_m": float(t[1]) if np.isfinite(t).all() else "",
                "gate_age_s": state.gate_rel_age_s,
                "center_x_px": feat.center_x_px,
                "y_top_px": feat.y_top_px,
                "span_px": feat.span_px,
                "span_x_range": (feat.span_px * r_z if r_z is not None else ""),
                "e_meas": e_meas if e_meas is not None else "",
                "e_reject": reject,
                "level_pitch_rad": state.level_pitch,
                "level_roll_rad": state.level_roll,
                "image_w": state.image_size[0] if state.image_size else "",
                "image_h": state.image_size[1] if state.image_size else "",
                "det_confidence": getattr(used_det, "confidence", ""),
                "det_cert_status": getattr(used_det, "cert_status", ""),
            })

    meta = {
        "flight": target["label"],
        "flight_id": target["flight_id"],
        "recording": str(rec_path.relative_to(ROOT)),
        "log": str(log_path.relative_to(ROOT)),
        "frames": len(frames),
        "imu_samples": len(imu),
        "raw_detector_fixes": raw_detector_fixes,
        "tracker_fixes": tracker_fixes,
        "feature_side_rows": feature_side_rows,
        "center_only_detections": center_only,
        "feature_rows": len(rows),
        "level_roll": level_roll,
        "level_pitch": level_pitch,
    }
    return rows, meta


def summarize_liveness(timeline: list[dict]) -> list[dict]:
    bins = [(2.0, 1.5), (1.5, 1.0), (1.0, 0.5), (0.5, 0.0)]
    out = []
    for flight in sorted({r["flight"] for r in timeline}):
        rows = [r for r in timeline if r["flight"] == flight]
        for hi, lo in bins:
            br = [r for r in rows
                  if fnum(r.get("range_z_m")) is not None
                  and lo <= float(r["range_z_m"]) < hi]
            out.append({
                "flight": flight,
                "range_bin_m": f"{lo:.1f}-{hi:.1f}",
                "rows": len(br),
                "ready_rows": sum(1 for r in br if r.get("ready")),
                "ready_legacy_rows": sum(1 for r in br if r.get("ready_legacy")),
                "side_rows": sum(1 for r in br if r.get("feature_mode") == "SIDE_PAIR"),
                "full_rows": sum(1 for r in br if r.get("feature_mode") == "FULL_QUAD"),
                "active_side_rows": sum(1 for r in br if r.get("active_source") == "SIDE_PAIR"),
            })
    return out


def summarize_accuracy(timeline: list[dict], targets: dict[str, dict]) -> list[dict]:
    out = []
    for flight in sorted({r["flight"] for r in timeline}):
        metric = [r for r in timeline
                  if r["flight"] == flight
                  and fnum(r.get("range_z_m")) is not None
                  and fnum(r.get("e_meas")) is not None]
        rows = [r for r in metric if float(r["range_z_m"]) < 1.0]
        near_rows = [r for r in metric if float(r["range_z_m"]) <= 1.1]
        closest = min(metric, key=lambda r: float(r["range_z_m"])) if metric else None
        e_vals = [float(r["e_meas"]) for r in rows]
        near_e_vals = [float(r["e_meas"]) for r in near_rows]
        expected = float(targets[flight]["contact_offset_m"])
        out.append({
            "flight": flight,
            "final_meter_rows": len(rows),
            "e_z_mean_m": mean(e_vals),
            "e_z_median_m": median(e_vals),
            "e_z_std_m": sample_std(e_vals),
            "near_1p1m_rows": len(near_rows),
            "near_1p1m_e_z_median_m": median(near_e_vals),
            "closest_metric_range_m": (
                float(closest["range_z_m"]) if closest is not None else None
            ),
            "closest_metric_e_z_m": (
                float(closest["e_meas"]) if closest is not None else None
            ),
            "contact_implied_offset_m": expected,
            "median_minus_contact_m": (
                median(e_vals) - expected if median(e_vals) is not None else None
            ),
            "closest_abs_minus_contact_m": (
                abs(float(closest["e_meas"])) - expected if closest is not None else None
            ),
            "within_0p1_0p2_band_rows": sum(1 for v in e_vals if 0.1 <= abs(v) <= 0.2),
            "near_1p1m_within_0p1_0p2_band_rows": sum(
                1 for v in near_e_vals if 0.1 <= abs(v) <= 0.2
            ),
        })
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def write_report(out_dir: Path, summary: dict) -> None:
    lines = [
        "# L1 Perception Replay",
        "",
        "Role: QA & MOCK-TUNER.",
        "Scope: recorded video replay only; no real simulator was launched, reset, clicked, or commanded.",
        f"Commit: `{summary['commit']}`.",
        "",
        "## QA Notes",
        "",
        "- Observer-only replay: this measures TerminalOracle observe/readiness/source history from fresh video-derived features, without running the terminal controller update or actuator ownership path.",
        "- `ready_legacy` is reported beside the current fresh-tail readiness semantic.",
        "- Sub-1m row-only shadow features are not counted as metric accuracy rows.",
        "",
        "## Inputs",
        "",
    ]
    for meta in summary["flight_meta"]:
        lines.append(
            f"- `{meta['flight']}` `{meta['flight_id']}`: "
            f"{meta['frames']} frames, detector fixes {meta['raw_detector_fixes']}, "
            f"tracker fixes {meta['tracker_fixes']}, feature rows {meta['feature_rows']}, "
            f"level_pitch {meta['level_pitch']:.6f} rad."
        )
    lines.extend(["", "## Ready Below 2m", ""])
    lines.append("| Flight | Range bin | Rows | Ready | Ready legacy | FULL | SIDE | Active SIDE |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for row in summary["liveness"]:
        lines.append(
            f"| `{row['flight']}` | {row['range_bin_m']} | {row['rows']} | "
            f"{row['ready_rows']} | {row['ready_legacy_rows']} | "
            f"{row['full_rows']} | {row['side_rows']} | {row['active_side_rows']} |"
        )
    lines.extend(["", "## Final Meter Accuracy", ""])
    lines.append("| Flight | <1.0m rows | e_z median | <=1.1m rows | <=1.1m median | closest R | closest e_z | contact offset | closest abs-contact |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in summary["accuracy"]:
        lines.append(
            f"| `{row['flight']}` | {row['final_meter_rows']} | "
            f"{fmt(row['e_z_median_m'])} | {row['near_1p1m_rows']} | "
            f"{fmt(row['near_1p1m_e_z_median_m'])} | "
            f"{fmt(row['closest_metric_range_m'])} | {fmt(row['closest_metric_e_z_m'])} | "
            f"{fmt(row['contact_implied_offset_m'])} | "
            f"{fmt(row['closest_abs_minus_contact_m'])} |"
        )
    res = summary["side_residuals"]
    lines.extend([
        "",
        "## Earned Sigma Row",
        "",
        f"- Overlap rows: `{res['n_overlap']}`.",
        f"- SIDE_PAIR minus FULL_QUAD bias_e: `{fmt(res['bias_e_m'])}` m.",
        f"- Measured sigma_e: `{fmt(res['sigma_e_m'])}` m.",
        f"- Measured sigma_v: `{fmt(res['sigma_v_mps'])}` m/s.",
        "",
        "## Source Transitions",
        "",
    ])
    if summary["transitions"]:
        lines.append("| Sweep | Flight | t | Range | From | To |")
        lines.append("|---|---|---:|---:|---|---|")
        for row in summary["transitions"]:
            lines.append(
                f"| `{row['sweep']}` | `{row['flight']}` | {fmt(row['t_rel_s'])} | "
                f"{fmt(row.get('range_z_m'))} | `{row['from_source']}` | `{row['to_source']}` |"
            )
    else:
        lines.append("No source transitions observed in baseline replay.")
    lines.extend(["", "## S5 Dropout Sweeps", ""])
    lines.append("| Sweep | Flight | Fed rows | Ready below 2m | Legacy ready below 2m | Active SIDE below 2m | First ready range | Transitions |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
    for row in summary["s5"]:
        lines.append(
            f"| `{row['sweep']}` | `{row['flight']}` | {row['fed_rows']} | "
            f"{row['ready_below_2_rows']} | {row['ready_legacy_below_2_rows']} | "
            f"{row['active_side_below_2_rows']} | {fmt(row['first_ready_range_m'])} | "
            f"{row['transition_count']} |"
        )
    lines.extend([
        "",
        "Artifacts: `features.csv`, `timeline_baseline.csv`, `side_residuals.csv`, "
        "`source_transitions.csv`, `s5_dropout_sweeps.csv`, and `summary.json`.",
    ])
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch", action="append", default=[])
    args = parser.parse_args(argv)

    assert_mock_safe()
    head, head_short = git_head()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = ROOT / "tuning" / f"l1-perception-replay-7b2626b-{head_short}-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    params = apply_patches(ParamSet.load(ROOT / "config" / "params_default.json"),
                           args.patch)
    all_features = []
    metas = []
    for target in TARGETS:
        rows, meta = run_video_replay(params, target)
        all_features.extend(rows)
        metas.append(meta)
    write_csv(out_dir / "features.csv", all_features)

    baseline, transitions = replay_oracle_from_rows(params, all_features,
                                                    ReplayOptions("baseline"))
    write_csv(out_dir / "timeline_baseline.csv", baseline)
    write_csv(out_dir / "source_transitions.csv", transitions)

    target_by_label = {t["label"]: t for t in TARGETS}
    liveness = summarize_liveness(baseline)
    accuracy = summarize_accuracy(baseline, target_by_label)
    residuals = source_residuals(baseline)
    write_csv(out_dir / "side_residuals.csv", residuals["rows"])

    sweeps = [
        ReplayOptions("baseline"),
        ReplayOptions("drop_all_0p16s_after_first_below_2m", drop_all_window_s=0.16),
        ReplayOptions("drop_all_0p30s_after_first_below_2m", drop_all_window_s=0.30),
        ReplayOptions("drop_full_below_2p0m", drop_full_below_m=2.0),
        ReplayOptions("drop_full_below_1p5m", drop_full_below_m=1.5),
        ReplayOptions("drop_full_source_all", drop_full_all=True),
    ]
    s5_rows = []
    all_sweep_transitions = []
    for opts in sweeps:
        tl, tr = replay_oracle_from_rows(params, all_features, opts)
        all_sweep_transitions.extend(tr)
        for flight in sorted({r["flight"] for r in tl}):
            fr = [r for r in tl if r["flight"] == flight]
            below = [r for r in fr if fnum(r.get("range_z_m")) is not None
                     and float(r["range_z_m"]) < 2.0]
            ready_below = [r for r in below if r.get("ready")]
            s5_rows.append({
                "sweep": opts.label,
                "flight": flight,
                "fed_rows": sum(1 for r in fr if r.get("fed")),
                "ready_below_2_rows": len(ready_below),
                "ready_legacy_below_2_rows": sum(1 for r in below if r.get("ready_legacy")),
                "active_side_below_2_rows": sum(1 for r in below if r.get("active_source") == "SIDE_PAIR"),
                "first_ready_range_m": (
                    ready_below[0]["range_z_m"] if ready_below else None
                ),
                "transition_count": sum(1 for r in tr if r["flight"] == flight),
            })
    write_csv(out_dir / "s5_dropout_sweeps.csv", s5_rows)
    if all_sweep_transitions and not transitions:
        write_csv(out_dir / "source_transitions_sweeps.csv", all_sweep_transitions)

    summary = {
        "commit": head,
        "patches": args.patch,
        "flight_meta": metas,
        "liveness": liveness,
        "accuracy": accuracy,
        "side_residuals": {k: v for k, v in residuals.items() if k != "rows"},
        "transitions": transitions,
        "s5": s5_rows,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(out_dir, summary)
    print(f"[l1] report={out_dir / 'summary.md'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
