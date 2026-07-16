"""Crossing-miss map across phase3c–3i (as fixtures land).

From STATE gate_rel (lock-accepted / dead-reckoned), NOT raw detections.
Miss vector at closest approach per gate attempt: lateral = cam tx (body y),
vertical = cam ty (body z, down+). Positive vertical => aircraft HIGH / top-bar.

Phase3h+ may RETRY (approach→commit→retreat→approach). Each cycle is a
separate attempt, segmented via setpoint.data.phase (not FSM).
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from aigp.io.udp_tap import STREAM_VISION, read_recording  # noqa: E402
from aigp.io.vision_rx import ChunkAssembler  # noqa: E402

PHASE_DIRS = [
    ("phase3c", ROOT / "fixtures" / "20260715T052244-phase3c-r2training"),
    ("phase3d", ROOT / "fixtures" / "20260715T135600-phase3d-r2training"),
    ("phase3e", ROOT / "fixtures" / "20260715T190627-phase3e-r2training-slow"),
    ("phase3f", ROOT / "fixtures" / "20260715T200734-phase3f-r2training-slow"),
]
for tag in ("phase3g", "phase3h", "phase3i"):
    for d in sorted((ROOT / "fixtures").glob(f"*{tag}*")):
        PHASE_DIRS.append((tag, d))

PHASE_COLORS = {
    "phase3c": "#d62728",
    "phase3d": "#ff7f0e",
    "phase3e": "#2ca02c",
    "phase3f": "#1f77b4",
    "phase3g": "#9467bd",
    "phase3h": "#8c564b",
    "phase3i": "#e377c2",
}

# Planner phases that belong to a gate attempt window.
_ATTEMPT_START = "approach"


@dataclass
class Attempt:
    phase: str
    flight_id: str
    attempt_n: int  # 1-based within flight; retries get 2, 3, …
    n_attempts_in_flight: int
    status: str
    n_states_with_gate: int
    closest_dist_m: float | None
    miss_lateral_m: float | None  # + = opening right of aircraft = aircraft LEFT of opening
    miss_vertical_m: float | None  # + = opening below aircraft = aircraft HIGH
    t_closest_s: float | None
    t_attempt_start_s: float | None
    t_attempt_end_s: float | None
    gate_rel_age_s: float | None
    attempt_phases: str  # e.g. "approach+commit+retreat"
    ended_retreat: bool
    result: str | None
    gates_passed: int | None


def load_result(path: Path) -> dict:
    rp = path.with_name(path.name.replace("-flight.jsonl", "-result.json"))
    if rp.exists():
        return json.loads(rp.read_text(encoding="utf-8"))
    return {}


def _segment_attempts_from_setpoints(
    setpoints: list[tuple[float, str]],
) -> list[tuple[float, float, list[str]]]:
    """Return [(t_start, t_end, phases_in_attempt), ...] from (t, phase) stream.

    An attempt starts on `approach` after takeoff/hover/retreat/recover/search
    (or at first approach). `commit→approach` continues the SAME attempt
    (live-steered mid-pass, not a retry). `retreat`/`recover` closes the
    attempt; a later `approach` is a new retry cycle.
    """
    if not setpoints:
        return []
    attempts: list[tuple[float, float, list[str]]] = []
    cur_start: float | None = None
    cur_phases: list[str] = []
    prev: str | None = None

    def close(at_t: float) -> None:
        nonlocal cur_start, cur_phases
        if cur_start is not None:
            attempts.append((cur_start, at_t, list(cur_phases)))
        cur_start = None
        cur_phases = []

    for t, ph in setpoints:
        if ph == _ATTEMPT_START:
            if cur_start is None:
                cur_start = t
                cur_phases = [ph]
            elif prev == "commit":
                # Same physical pass — do not split.
                if cur_phases[-1] != ph:
                    cur_phases.append(ph)
            elif prev in ("retreat", "recover", "hover", "search", "takeoff"):
                # Should already be closed; start fresh if not.
                if cur_start is not None:
                    close(t)
                cur_start = t
                cur_phases = [ph]
        elif ph == "commit" and cur_start is not None:
            if not cur_phases or cur_phases[-1] != ph:
                cur_phases.append(ph)
        elif ph in ("retreat", "recover"):
            if cur_start is not None:
                if not cur_phases or cur_phases[-1] != ph:
                    cur_phases.append(ph)
                close(t)
        elif ph in ("hover", "search") and cur_start is not None:
            close(t)
        prev = ph

    if cur_start is not None and setpoints:
        attempts.append((cur_start, setpoints[-1][0], list(cur_phases)))
    return attempts


def reconstruct_misses(phase: str, path: Path) -> list[Attempt]:
    """One Attempt row per gate attempt (retries are separate rows)."""
    flight_id = path.stem.replace("-flight", "")
    result = load_result(path)
    abort = result.get("abort_reason") or ("finished" if result.get("finished") else None)
    gates_passed = int(result.get("gates_passed") or 0)

    t0 = None
    states: list[tuple[float, float, float, float, float, float]] = []
    # (t, dist, tx, ty, tz, age)
    n_gate_total = 0
    setpoints_dwell: list[tuple[float, str]] = []
    last_ph = None
    last_t = None

    with path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            topic = rec["topic"]
            mono = int(rec["mono_ns"])
            if t0 is None:
                t0 = mono
            t = (mono - t0) / 1e9
            d = rec["data"]
            if topic == "setpoint":
                ph = d.get("phase")
                if isinstance(ph, str):
                    if last_ph is None or ph != last_ph:
                        setpoints_dwell.append((t, ph))
                        last_ph = ph
                    last_t = t
            elif topic == "state":
                gr = d.get("gate_rel")
                if not gr or gr.get("t") is None:
                    continue
                n_gate_total += 1
                tx, ty, tz = (float(x) for x in gr["t"])
                dist = math.sqrt(tx * tx + ty * ty + tz * tz)
                age = float(d.get("gate_rel_age_s") or 0.0)
                states.append((t, dist, tx, ty, tz, age))

    if last_t is not None and setpoints_dwell:
        # synthetic end marker so the last dwell has a closing time
        setpoints_dwell.append((last_t, setpoints_dwell[-1][1]))

    windows = _segment_attempts_from_setpoints(setpoints_dwell)
    # Fallback: no approach segments — single whole-flight closest (legacy)
    if not windows:
        best = None
        for t, dist, tx, ty, tz, age in states:
            if best is None or dist < best[1] - 1e-6 or (
                abs(dist - best[1]) < 0.05 and age < best[5]
            ):
                best = (t, dist, tx, ty, tz, age)
        if best is None:
            return [
                Attempt(
                    phase=phase,
                    flight_id=flight_id,
                    attempt_n=1,
                    n_attempts_in_flight=1,
                    status="no_gate_rel",
                    n_states_with_gate=0,
                    closest_dist_m=None,
                    miss_lateral_m=None,
                    miss_vertical_m=None,
                    t_closest_s=None,
                    t_attempt_start_s=None,
                    t_attempt_end_s=None,
                    gate_rel_age_s=None,
                    attempt_phases="",
                    ended_retreat=False,
                    result=abort,
                    gates_passed=gates_passed,
                )
            ]
        t, dist, tx, ty, tz, age = best
        return [
            Attempt(
                phase=phase,
                flight_id=flight_id,
                attempt_n=1,
                n_attempts_in_flight=1,
                status="ok",
                n_states_with_gate=n_gate_total,
                closest_dist_m=dist,
                miss_lateral_m=tx,
                miss_vertical_m=ty,
                t_closest_s=t,
                t_attempt_start_s=None,
                t_attempt_end_s=None,
                gate_rel_age_s=age,
                attempt_phases="(no setpoint approach)",
                ended_retreat=False,
                result=abort,
                gates_passed=gates_passed,
            )
        ]

    out: list[Attempt] = []
    n_att = len(windows)
    for i, (t0a, t1a, phases) in enumerate(windows, start=1):
        # Evaluate miss only during approach+commit (exclude retreat motion)
        eval_end = t1a
        if "retreat" in phases or "recover" in phases:
            # end at first retreat/recover transition = t1a already
            pass
        best = None
        n_gate = 0
        for t, dist, tx, ty, tz, age in states:
            if t < t0a - 1e-6 or t > eval_end + 1e-6:
                continue
            # Prefer states while still in approach/commit window: if we have
            # retreat in phases, still use states up to t1a (retreat start).
            n_gate += 1
            if best is None or dist < best[1] - 1e-6 or (
                abs(dist - best[1]) < 0.05 and age < best[5]
            ):
                best = (t, dist, tx, ty, tz, age)
        ended_retreat = "retreat" in phases or "recover" in phases
        if best is None:
            out.append(
                Attempt(
                    phase=phase,
                    flight_id=flight_id,
                    attempt_n=i,
                    n_attempts_in_flight=n_att,
                    status="no_gate_rel",
                    n_states_with_gate=0,
                    closest_dist_m=None,
                    miss_lateral_m=None,
                    miss_vertical_m=None,
                    t_closest_s=None,
                    t_attempt_start_s=t0a,
                    t_attempt_end_s=t1a,
                    gate_rel_age_s=None,
                    attempt_phases="+".join(phases),
                    ended_retreat=ended_retreat,
                    result=abort,
                    gates_passed=gates_passed,
                )
            )
            continue
        t, dist, tx, ty, tz, age = best
        out.append(
            Attempt(
                phase=phase,
                flight_id=flight_id,
                attempt_n=i,
                n_attempts_in_flight=n_att,
                status="ok",
                n_states_with_gate=n_gate,
                closest_dist_m=dist,
                miss_lateral_m=tx,
                miss_vertical_m=ty,
                t_closest_s=t,
                t_attempt_start_s=t0a,
                t_attempt_end_s=t1a,
                gate_rel_age_s=age,
                attempt_phases="+".join(phases),
                ended_retreat=ended_retreat,
                result=abort,
                gates_passed=gates_passed,
            )
        )
    return out


def find_pnp_outliers(phase: str, path: Path, dist_lo=2.0, dist_hi=4.5, min_abs_ty=2.0, min_dty=0.8):
    """Find close-range detections with huge |ty| or large consecutive Δty."""
    t0 = None
    dets = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec["topic"] != "detection" or not rec["data"].get("rel_pose"):
                continue
            mono = int(rec["mono_ns"])
            if t0 is None:
                t0 = mono
            t = (mono - t0) / 1e9
            d = rec["data"]
            tx, ty, tz = (float(x) for x in d["rel_pose"]["t"])
            dist = math.sqrt(tx * tx + ty * ty + tz * tz)
            dets.append(
                {
                    "t": t,
                    "dist": dist,
                    "tx": tx,
                    "ty": ty,
                    "tz": tz,
                    "center": d.get("center_px"),
                    "corners": d.get("corners_px"),
                    "conf": d.get("confidence"),
                    "ts_ns": d.get("ts_ns"),
                }
            )

    outliers = []
    for i, det in enumerate(dets):
        if not (dist_lo <= det["dist"] <= dist_hi):
            continue
        reason = None
        dty = None
        if abs(det["ty"]) >= min_abs_ty:
            reason = f"|ty|={abs(det['ty']):.2f}m at {det['dist']:.2f}m"
        if i > 0:
            prev = dets[i - 1]
            dt = det["t"] - prev["t"]
            if 0 < dt < 0.4 and dist_lo <= prev["dist"] <= dist_hi:
                dty = abs(det["ty"] - prev["ty"])
                if dty >= min_dty:
                    reason = (reason + "; " if reason else "") + f"Δty={dty:.2f}m"
        if reason:
            outliers.append({**det, "reason": reason, "dty": dty, "phase": phase, "flight_id": path.stem.replace("-flight", "")})
    # Dedupe near-in-time
    outliers.sort(key=lambda o: abs(o["ty"]), reverse=True)
    kept = []
    for o in outliers:
        if any(abs(o["t"] - k["t"]) < 0.15 and o["flight_id"] == k["flight_id"] for k in kept):
            continue
        kept.append(o)
        if len(kept) >= 12:
            break
    return kept


def vision_search_roots() -> list[Path]:
    roots = [
        ROOT / "recordings",
        ROOT / "logs",
        ROOT.parent / "eni_dcim" / "recordings",
        ROOT.parent / "eni_dcim" / "logs",
        Path.home() / "Documents" / "eni_dcim" / "recordings",
        Path.home() / "Documents" / "eni_dcim" / "logs",
    ]
    return [r for r in roots if r.exists()]


def find_vision_sources(fix_dir: Path, flight_id: str) -> list[Path]:
    cands: list[Path] = []
    seen: set[Path] = set()

    def add(p: Path) -> None:
        try:
            rp = p.resolve()
        except OSError:
            return
        if rp in seen or not p.is_file():
            return
        seen.add(rp)
        cands.append(p)

    for root in vision_search_roots():
        for p in root.rglob("*%s*.aigprec" % flight_id):
            add(p)
        for d in root.rglob("*%s*" % flight_id):
            if d.is_dir():
                for p in d.glob("*.aigprec"):
                    add(p)
                v = d / "vision.aigprec"
                if v.exists():
                    add(v)
    if fix_dir.exists():
        for p in fix_dir.glob("%s*.aigprec" % flight_id):
            add(p)

    def rank(p: Path):
        return (1 if "slice_start" in p.name.lower() else 0, -p.stat().st_size, str(p))

    cands.sort(key=rank)
    return cands


def extract_frame_by_ts_ns(rec_path: Path, target_ts_ns: int | None, target_t_s: float | None = None, max_err_s: float = 0.08):
    if not rec_path.exists():
        return None, {"error": "missing", "source": str(rec_path)}
    assembler = ChunkAssembler()
    best = None
    first_mono = None
    n_frames = 0
    for mono_ns, stream_id, data in read_recording(str(rec_path)):
        if stream_id != STREAM_VISION:
            continue
        done = assembler.feed(data)
        if done is None:
            continue
        frame_id, ts_ns, jpeg = done
        n_frames += 1
        if first_mono is None:
            first_mono = mono_ns
        t_rel = (mono_ns - first_mono) / 1e9
        if target_ts_ns is not None and ts_ns is not None:
            err_s = abs(int(ts_ns) - int(target_ts_ns)) / 1e9
            mode = "ts_ns"
        elif target_t_s is not None:
            err_s = abs(t_rel - float(target_t_s))
            mode = "slice_t"
        else:
            continue
        if best is None or err_s < best[0]:
            best = (err_s, t_rel, frame_id, jpeg, ts_ns, mode)
        if target_ts_ns is not None and ts_ns is not None and int(ts_ns) > int(target_ts_ns) and best[0] < max_err_s:
            break
    if best is None:
        return None, {"error": "no_frames", "source": str(rec_path), "n_frames": n_frames}
    err_s, t_rel, frame_id, jpeg, ts_ns, mode = best
    meta = {
        "source": str(rec_path),
        "source_name": rec_path.name,
        "match_mode": mode,
        "err_s": err_s,
        "t_rel": t_rel,
        "frame_id": frame_id,
        "ts_ns": ts_ns,
        "n_frames": n_frames,
        "accepted": err_s <= max_err_s,
    }
    if err_s > max_err_s:
        meta["error"] = "best_err %.3fs > %.3fs (recording does not cover outlier)" % (err_s, max_err_s)
        return None, meta
    img = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
    return img, meta


def load_detection_at_ts(flight_jsonl: Path, ts_ns: int) -> dict | None:
    with flight_jsonl.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("topic") != "detection":
                continue
            data = rec.get("data") or {}
            if data.get("ts_ns") == ts_ns:
                return data
    return None


def classify_pnp_outlier(det: dict, ty: float, dist: float) -> list[str]:
    notes: list[str] = []
    corners = det.get("corners_px") or det.get("corners")
    center = det.get("center_px") or det.get("center")
    pose = det.get("rel_pose") or {}
    normal = pose.get("normal")
    image_size = det.get("image_size") or [640, 360]
    w, h = int(image_size[0]), int(image_size[1])
    if corners is None or center is None:
        notes.append("detection lacks corners/center")
        return notes
    pts = np.asarray(corners, dtype=float).reshape(-1, 2)
    cx, cy = float(center[0]), float(center[1])
    top = float(np.linalg.norm(pts[1] - pts[0]))
    bot = float(np.linalg.norm(pts[2] - pts[3]))
    left = float(np.linalg.norm(pts[3] - pts[0]))
    right = float(np.linalg.norm(pts[2] - pts[1]))
    trap = abs(top - bot) / (0.5 * (top + bot) + 1e-9)
    elev_deg = math.degrees(math.atan2(abs(ty), max(dist, 1e-3)))
    notes.append(
        "corners_px=%s; center_px=[%.1f,%.1f]; edges top/bot/L/R=%.0f/%.0f/%.0f/%.0f; trap=%.2f"
        % (corners, cx, cy, top, bot, left, right, trap)
    )
    if normal is not None:
        n = [float(x) for x in normal]
        notes.append("PnP normal=%s" % n)
        if abs(n[1]) > 0.7:
            notes.append("VERDICT: bad PnP / wrong quad - normal y-dominant (implausible for face-on ring).")
        elif abs(n[2]) < 0.5:
            notes.append("VERDICT: normal not camera-facing - partial ring or mis-ordered corners.")
        elif elev_deg > 25 and dist < 5.0:
            notes.append(
                "VERDICT: ring-like quad but |ty| implies ~%.0fdeg at %.1fm - lock-rejected pose blow-up (banner/other-gate/partial), not true opening offset."
                % (elev_deg, dist)
            )
        else:
            notes.append("VERDICT: inconclusive from geometry alone.")
    if cy < h * 0.28:
        notes.append("quad center high in frame.")
    if cx < w * 0.22 or cx > w * 0.78:
        notes.append("quad near L/R edge (partial/off-axis).")
    if trap > 0.22:
        notes.append("strong trapezoid - steep perspective or partial ring.")
    return notes


def render_corners_evidence(out_path: Path, title: str, corners, center, image_size=(640, 360), backdrop=None, footer: str = "") -> bool:
    w, h = int(image_size[0]), int(image_size[1])
    if backdrop is not None:
        vis = backdrop.copy()
        if vis.shape[0] != h or vis.shape[1] != w:
            vis = cv2.resize(vis, (w, h), interpolation=cv2.INTER_AREA)
    else:
        vis = np.full((h, w, 3), 32, dtype=np.uint8)
        cv2.putText(vis, "NO PIXEL FRAME (schematic from corners_px)", (12, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (80, 80, 200), 1, cv2.LINE_AA)
    if corners is not None:
        pts = np.asarray(corners, dtype=np.int32).reshape(-1, 2)
        cv2.polylines(vis, [pts], True, (0, 255, 255), 2)
        for i, (x, y) in enumerate(pts):
            cv2.circle(vis, (int(x), int(y)), 4, (0, 200, 255), -1)
            cv2.putText(vis, str(i), (int(x) + 4, int(y) - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
    if center is not None:
        cv2.circle(vis, (int(center[0]), int(center[1])), 6, (0, 0, 255), -1)
        cv2.drawMarker(vis, (w // 2, h // 2), (180, 180, 180), cv2.MARKER_CROSS, 16, 1)
    cv2.putText(vis, title[:90], (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    if footer:
        y0 = h - 10
        for j, chunk in enumerate(reversed(footer.split(" | ")[:4])):
            cv2.putText(vis, chunk[:90], (8, y0 - 16 * j), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (220, 220, 220), 1, cv2.LINE_AA)
    if w > 800:
        scale = 800 / w
        vis = cv2.resize(vis, (800, int(h * scale)), interpolation=cv2.INTER_AREA)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), vis, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    return True


def annotate_and_save(img, out_path: Path, title: str, corners=None, center=None):
    if img is None:
        return False
    return render_corners_evidence(out_path, title, corners, center, backdrop=img)


def find_late_screen(fix_dir: Path, flight_index: int | None = None) -> Path | None:
    screens = fix_dir / "screens"
    if not screens.exists():
        return None
    if flight_index is not None:
        for name in ("f%d_late.jpg" % flight_index, "f%d_approach.jpg" % flight_index):
            p = screens / name
            if p.exists():
                return p
    cands = sorted(screens.glob("*late*.jpg")) + sorted(screens.glob("*approach*.jpg"))
    return cands[0] if cands else None
def write_dashboard(attempts: list[Attempt], outliers: list[dict], autopsy_notes: list[str]):
    lines = [
        "# Crossing-miss map (phase3c–3i convergence dashboard)",
        "",
        "Generated by `analysis/2026-07-15-crossing-miss-map/run_crossing_miss_map.py`.",
        "Miss vectors from **STATE `gate_rel`** (lock-accepted / dead-reckoned), "
        "**not** raw detections (which include lock-rejected fixes).",
        "",
        "Convention at closest approach:",
        "- **lateral_m** = cam `t_x` (body y): + = opening RIGHT of aircraft = aircraft LEFT of opening",
        "- **vertical_m** = cam `t_y` (body z, down+): + = opening BELOW aircraft = aircraft HIGH / top-bar",
        "",
        "Phase3h+ **retry cycles**: each `approach→commit→(retreat)?` segmented via "
        "`setpoint.data.phase` is a separate row (`att` column). Earlier phases usually "
        "have one attempt per flight.",
        "",
        "## Miss table (every R2 attempt)",
        "",
        "| phase | flight | att | cycle | status | closest dist (m) | lateral (m) | vertical (m) | age (s) | gates | result |",
        "|---|---|---:|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for a in attempts:
        att = f"{a.attempt_n}/{a.n_attempts_in_flight}"
        cycle = a.attempt_phases or "—"
        if a.status != "ok":
            lines.append(
                f"| {a.phase} | `{a.flight_id}` | {att} | `{cycle}` | {a.status} | — | — | — | — | "
                f"{a.gates_passed if a.gates_passed is not None else '—'} | {a.result or '—'} |"
            )
            continue
        lines.append(
            f"| {a.phase} | `{a.flight_id}` | {att} | `{cycle}` | ok | {a.closest_dist_m:.2f} | "
            f"{a.miss_lateral_m:+.2f} | {a.miss_vertical_m:+.2f} | "
            f"{a.gate_rel_age_s:.2f} | {a.gates_passed} | {a.result or '—'} |"
        )

    # Phase summaries (close approaches only — far post-retreat flails excluded)
    CLOSE_M = 5.0
    lines += [
        "",
        f"## Phase summary (ok attempts with closest dist ≤ {CLOSE_M:.0f} m)",
        "",
        "Far retries / search flails remain in the table above but are excluded "
        "here and from the scatter so the convergence chart stays readable.",
        "",
    ]
    lines.append("| phase | n | mean |lat| | mean lat | mean vert | mean |vert| | rms miss |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for phase in ["phase3c", "phase3d", "phase3e", "phase3f", "phase3g", "phase3h", "phase3i"]:
        ok = [
            a
            for a in attempts
            if a.phase == phase
            and a.status == "ok"
            and a.closest_dist_m is not None
            and a.closest_dist_m <= CLOSE_M
        ]
        if not ok:
            continue
        lat = np.array([a.miss_lateral_m for a in ok], float)
        vert = np.array([a.miss_vertical_m for a in ok], float)
        rms = float(np.sqrt(np.mean(lat**2 + vert**2)))
        lines.append(
            f"| {phase} | {len(ok)} | {np.mean(np.abs(lat)):.2f} | {np.mean(lat):+.2f} | "
            f"{np.mean(vert):+.2f} | {np.mean(np.abs(vert)):.2f} | {rms:.2f} |"
        )

    # phase3h retry spotlight
    h_rows = [a for a in attempts if a.phase == "phase3h"]
    if h_rows:
        lines += [
            "",
            "## Phase3h retry spotlight",
            "",
            "Each flight may have multiple attempts (retreat-and-retry). "
            "Misses below are per attempt — not collapsed to one closest-overall.",
            "",
        ]
        by_f: dict[str, list[Attempt]] = {}
        for a in h_rows:
            by_f.setdefault(a.flight_id, []).append(a)
        for fid, rows in by_f.items():
            lines.append(f"- `{fid}`: {len(rows)} attempt(s)")
            for a in rows:
                if a.status != "ok":
                    lines.append(f"  - att {a.attempt_n}: {a.status} (`{a.attempt_phases}`)")
                else:
                    lines.append(
                        f"  - att {a.attempt_n}: dist={a.closest_dist_m:.2f} m, "
                        f"lat={a.miss_lateral_m:+.2f}, vert={a.miss_vertical_m:+.2f}, "
                        f"age={a.gate_rel_age_s:.2f}s, cycle=`{a.attempt_phases}`"
                        + (" → retreated" if a.ended_retreat else "")
                    )

    lines += [
        "",
        "## Scatter",
        "",
        "![miss scatter](plots/miss_scatter.png)",
        "",
        "Origin = gate opening center. Points = STATE closest approach **per attempt** "
        "(closest dist ≤ 5 m). Ideal pass sits near (0,0). Right/up = aircraft LEFT / HIGH. "
        "Labels: flight hex; `#N` when a flight has multiple attempts. "
        "Far retries stay in the table only.",
        "",
        "## Close-range PnP outlier autopsy (2–4.5 m)",
        "",
        "Raw detections (for autopsy only). Looking for |ty|>=2 m. Frames matched by detection ts_ns; start slices rejected if they do not cover the outlier time.",
        "",
    ]
    if not outliers:
        lines.append("No outliers matched the thresholds in the scanned flights.")
    else:
        lines.append("| phase | flight | t (s) | dist (m) | ty (m) | Δty | reason | frame |")
        lines.append("|---|---|---:|---:|---:|---:|---|---|")
        for o in outliers:
            frame = o.get("frame_file") or "—"
            dty = f"{o['dty']:.2f}" if o.get("dty") is not None else "—"
            lines.append(
                f"| {o['phase']} | `{o['flight_id']}` | {o['t']:.2f} | {o['dist']:.2f} | "
                f"{o['ty']:+.2f} | {dty} | {o['reason']} | {frame} |"
            )
    lines += ["", "### What the detector saw", ""]
    for note in autopsy_notes:
        lines.append(f"- {note}")
    if not autopsy_notes:
        lines.append("- (no annotated frames extracted)")

    lines += [
        "",
        "## Reading the convergence",
        "",
        "- **phase3c→3d** (mount_pitch=29): vertical should shrink if altitude phantom died.",
        "- **phase3e** (slow): both axes may shrink via phantom starvation.",
        "- **phase3f** (cross-track): lateral |mean| should drop vs 3e.",
        "- **phase3g** (altitude hold): vertical residual is the target if present.",
        "- **phase3h** (age-aware lock + retreat-and-retry): multiple points per flight; "
          "did retries improve the miss?",
        "- **phase3i**: include when fixture lands.",
        "",
        "## Deliverables",
        "",
        "- `report.md`, `summary.json`, `miss_table.csv`",
        "- `plots/miss_scatter.png`",
        "- `pnp_outliers/` annotated frames",
        "",
    ]
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")


def plot_scatter(attempts: list[Attempt], close_m: float = 5.0):
    fig, ax = plt.subplots(figsize=(9.5, 7.5))
    for phase, color in PHASE_COLORS.items():
        pts = [
            a
            for a in attempts
            if a.phase == phase
            and a.status == "ok"
            and a.closest_dist_m is not None
            and a.closest_dist_m <= close_m
        ]
        if not pts:
            continue
        xs = [a.miss_lateral_m for a in pts]
        ys = [a.miss_vertical_m for a in pts]  # +UP = aircraft HIGH
        marker = "D" if phase in ("phase3h", "phase3i") else "o"
        ax.scatter(
            xs, ys, c=color, s=70, marker=marker, label=f"{phase} (n={len(pts)})", zorder=3
        )
        for a, x, y in zip(pts, xs, ys):
            label = a.flight_id[-6:]
            if a.n_attempts_in_flight > 1:
                label = f"{label}#{a.attempt_n}"
            ax.annotate(label, (x, y), textcoords="offset points", xytext=(4, 4), fontsize=7, color=color)
    ax.axhline(0, color="k", lw=0.8)
    ax.axvline(0, color="k", lw=0.8)
    # Opening size reference (~1.5m half-width / half-height typical)
    ax.add_patch(plt.Rectangle((-0.75, -0.75), 1.5, 1.5, fill=False, ls="--", color="gray", label="~opening ±0.75m"))
    ax.set_xlabel("lateral miss (m)  [+ = aircraft LEFT of opening]")
    ax.set_ylabel("vertical miss (m)  [+ UP = aircraft HIGH / top-bar]")
    ax.set_title(f"R2 crossing-miss map (STATE, per attempt, dist≤{close_m:.0f}m)")
    ax.grid(True, alpha=0.3)
    ax.set_aspect("equal", adjustable="datalim")
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    (OUT / "plots").mkdir(exist_ok=True)
    fig.savefig(OUT / "plots" / "miss_scatter.png", dpi=140)
    plt.close(fig)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "plots").mkdir(exist_ok=True)
    (OUT / "pnp_outliers").mkdir(exist_ok=True)

    attempts: list[Attempt] = []
    all_outliers: list[dict] = []
    autopsy_notes: list[str] = []

    for phase, fix_dir in PHASE_DIRS:
        if not fix_dir.exists():
            print(f"skip missing {fix_dir}", flush=True)
            continue
        flights = sorted(fix_dir.glob("*-flight.jsonl"))
        print(f"{phase}: {len(flights)} flights in {fix_dir.name}", flush=True)
        for fp in flights:
            flight_attempts = reconstruct_misses(phase, fp)
            attempts.extend(flight_attempts)
            for a in flight_attempts:
                print(
                    f"  {a.flight_id} att{a.attempt_n}/{a.n_attempts_in_flight} "
                    f"[{a.attempt_phases}]: {a.status} dist={a.closest_dist_m} "
                    f"lat={a.miss_lateral_m} vert={a.miss_vertical_m}",
                    flush=True,
                )
            # PnP autopsy focus on phase3f (and others that have big outliers)
            outs = find_pnp_outliers(phase, fp)
            for o in outs:
                o["fix_dir"] = str(fix_dir)
            all_outliers.extend(outs)

    # Prefer phase3f outliers for frame extraction; fall back to largest |ty|
    all_outliers.sort(key=lambda o: abs(o["ty"]), reverse=True)
    # Keep diverse top set
    selected = []
    for o in all_outliers:
        if len(selected) >= 8:
            break
        if any(o["flight_id"] == s["flight_id"] and abs(o["t"] - s["t"]) < 0.3 for s in selected):
            continue
        selected.append(o)

    # Enrich outliers with detection corners_px / normal via ts_ns.
    for o in selected:
        fix_dir = Path(o["fix_dir"])
        fp = fix_dir / ("%s-flight.jsonl" % o["flight_id"])
        det = load_detection_at_ts(fp, int(o["ts_ns"])) if fp.exists() and o.get("ts_ns") else None
        o["detection"] = det
        if det is not None:
            o["corners"] = det.get("corners_px") or det.get("corners")
            o["center"] = det.get("center_px") or det.get("center")
            o["image_size"] = det.get("image_size") or [640, 360]
            o["normal"] = (det.get("rel_pose") or {}).get("normal")
            o["corners_px"] = o["corners"]
            o["center_px"] = o["center"]

    flight_index: dict[str, int] = {}
    for phase, fix_dir in PHASE_DIRS:
        if not fix_dir.exists():
            continue
        for idx, fp in enumerate(sorted(fix_dir.glob("*-flight.jsonl")), start=1):
            flight_index[fp.stem.replace("-flight", "")] = idx

    for old in (OUT / "pnp_outliers").glob("*.jpg"):
        old.unlink()

    for i, o in enumerate(selected):
        fix_dir = Path(o["fix_dir"])
        fname = "%s_%s_t%.1f_ty%+.1f.jpg" % (o["phase"], o["flight_id"][-6:], o["t"], o["ty"])
        out_img = OUT / "pnp_outliers" / fname
        title = "%s %s t=%.1fs d=%.1f ty=%+.2f" % (o["phase"], o["flight_id"][-8:], o["t"], o["dist"], o["ty"])
        sources = find_vision_sources(fix_dir, o["flight_id"])
        img = None
        meta = None
        for src in sources:
            img, meta = extract_frame_by_ts_ns(src, o.get("ts_ns"), target_t_s=o.get("t"), max_err_s=0.08)
            if img is not None:
                break
        geom_notes = []
        if o.get("detection") is not None:
            geom_notes = classify_pnp_outlier(o["detection"], float(o["ty"]), float(o["dist"]))
        rejected = ""
        if img is not None:
            ok = annotate_and_save(img, out_img, title, corners=o.get("corners"), center=o.get("center"))
            evidence_kind = "exact_frame"
        else:
            backdrop = None
            late = find_late_screen(fix_dir, flight_index.get(o["flight_id"]))
            late_note = "no late/approach screen"
            if late is not None:
                backdrop = cv2.imread(str(late))
                late_note = "backdrop=operator %s (NOT exact outlier frame)" % late.name
            if meta is not None:
                rejected = " Best candidate `%s` rejected: %s (duration~%.2fs)." % (
                    Path(meta.get("source", "?")).name,
                    meta.get("error", "err"),
                    float(meta.get("t_rel", 0) or 0),
                )
            elif not sources:
                rejected = " No local .aigprec under recordings/logs/fixtures."
            footer = "ts_ns=%s | corners_px evidence | full recording unavailable locally | %s" % (
                o.get("ts_ns"),
                late_note,
            )
            ok = render_corners_evidence(
                out_img,
                title + " [SCHEMATIC]",
                o.get("corners"),
                o.get("center"),
                image_size=tuple(o.get("image_size") or [640, 360]),
                backdrop=backdrop,
                footer=footer,
            )
            evidence_kind = "schematic_corners_px"
        if ok:
            o["frame_file"] = "pnp_outliers/%s" % fname
            o["evidence_kind"] = evidence_kind
            if evidence_kind == "exact_frame" and meta is not None:
                note = "`%s` EXACT frame from `%s` via %s (err=%.1fms). %s." % (
                    fname,
                    Path(meta["source"]).name,
                    meta["match_mode"],
                    meta["err_s"] * 1000,
                    o["reason"],
                )
            else:
                note = (
                    "`%s` frames UNAVAILABLE at outlier t=%.2fs (ts_ns=%s).%s "
                    "Attached schematic from detection corners_px/center_px. %s."
                    % (fname, o["t"], o.get("ts_ns"), rejected, o["reason"])
                )
            for g in geom_notes:
                note += " " + g
            autopsy_notes.append(note)
        else:
            autopsy_notes.append(
                "%s `%s` t=%.1f: %s - could not write evidence plate."
                % (o["phase"], o["flight_id"], o["t"], o["reason"])
            )
    plot_scatter(attempts)
    write_dashboard(attempts, selected, autopsy_notes)

    # CSV
    import csv

    with (OUT / "miss_table.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "phase",
                "flight_id",
                "attempt_n",
                "n_attempts_in_flight",
                "attempt_phases",
                "ended_retreat",
                "status",
                "closest_dist_m",
                "miss_lateral_m",
                "miss_vertical_m",
                "t_closest_s",
                "t_attempt_start_s",
                "t_attempt_end_s",
                "gate_rel_age_s",
                "gates_passed",
                "result",
            ]
        )
        for a in attempts:
            w.writerow(
                [
                    a.phase,
                    a.flight_id,
                    a.attempt_n,
                    a.n_attempts_in_flight,
                    a.attempt_phases,
                    a.ended_retreat,
                    a.status,
                    a.closest_dist_m,
                    a.miss_lateral_m,
                    a.miss_vertical_m,
                    a.t_closest_s,
                    a.t_attempt_start_s,
                    a.t_attempt_end_s,
                    a.gate_rel_age_s,
                    a.gates_passed,
                    a.result,
                ]
            )

    present = sorted({p for p, d in PHASE_DIRS if d.exists()})
    summary = {
        "attempts": [a.__dict__ for a in attempts],
        "pnp_outliers": [
            {k: v for k, v in o.items() if k not in ("corners", "fix_dir", "detection")} for o in selected
        ],
        "autopsy_notes": autopsy_notes,
        "phases_present": present,
        "phase3h_present": "phase3h" in present,
        "phase3i_present": "phase3i" in present,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote report + {len(attempts)} attempts, {len(selected)} outliers", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
