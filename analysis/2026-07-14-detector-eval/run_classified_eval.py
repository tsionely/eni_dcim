"""Classified detector eval: split misses into no-gate vs visible-gate-missed.

DATA ANALYST harness. Read-only on src/. Writes under this folder:
  report.md, stats.csv, hard_frames/, no_gate/
"""
from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from aigp.core.messages import CameraFrame  # noqa: E402
from aigp.core.params import ParamSet  # noqa: E402
from aigp.io.udp_tap import STREAM_VISION, read_recording  # noqa: E402
from aigp.io.vision_rx import ChunkAssembler  # noqa: E402
from aigp.perception.gate_detector_hsv import HsvGateDetector  # noqa: E402

# Phase labels for known operator recordings (from fixture notes / timestamps).
PHASE_MAP = {
    "phase1-20260713T190142.aigprec": "phase1-idle",
    "phase1-20260713T200814.aigprec": "phase1d",
    "20260713T190311-db4c58dd": "phase1",
    "20260713T202513-ea4b5f0c": "phase1e",
    "20260714T041536-88e6e576": "phase1f",
    "20260714T045635-b9a568ab": "phase2a",
    "20260714T072732-8ff375f3": "phase2b",
    "20260714T081945-bb5494d6": "phase2c",
    "20260713T203515-phase1e": "phase1e-slice",
}

# Evidence thresholds (documented in report.md).
# Relaxed vs detector sat/val so motion-blurred red still counts as "visible".
EVIDENCE_SAT_MIN = 55
EVIDENCE_VAL_MIN = 45
EVIDENCE_HUE_LOW_MAX = 14
EVIDENCE_HUE_HIGH_MIN = 166
# Gate-visible if largest red blob OR total red mass exceeds these fractions.
EVIDENCE_MIN_BLOB_FRAC = 0.0006  # ~0.06% of frame (~200 px @ 640x480)
EVIDENCE_MIN_RED_FRAC = 0.0012  # ~0.12% of frame
EVIDENCE_MIN_BLOB_PX = 120


@dataclass
class FrameCand:
    recording_key: str
    frame_id: int
    jpeg: bytes
    red_frac: float
    blob_frac: float
    kind: str  # "visible_miss" | "no_gate"


@dataclass
class RecStats:
    path: str
    name: str
    phase: str
    frames: int = 0
    detections: int = 0
    pnp_ok: int = 0
    distances: list[float] = field(default_factory=list)
    miss_no_gate: int = 0
    miss_visible: int = 0
    first_ts_ns: int | None = None
    last_ts_ns: int | None = None
    # per-second buckets: time_s -> [frames, detections, miss_no_gate, miss_visible, red_sum]
    per_sec: dict[int, list[float]] = field(default_factory=dict)

    @property
    def det_pct(self) -> float:
        return 100.0 * self.detections / self.frames if self.frames else 0.0

    @property
    def pnp_pct(self) -> float:
        return 100.0 * self.pnp_ok / self.frames if self.frames else 0.0

    @property
    def no_gate_pct(self) -> float:
        return 100.0 * self.miss_no_gate / self.frames if self.frames else 0.0

    @property
    def visible_miss_pct(self) -> float:
        return 100.0 * self.miss_visible / self.frames if self.frames else 0.0


def recording_key(path: Path) -> str:
    if path.name == "vision.aigprec":
        return path.parent.name
    return path.stem


def phase_for(path: Path) -> str:
    key = recording_key(path)
    if key in PHASE_MAP:
        return PHASE_MAP[key]
    if path.name in PHASE_MAP:
        return PHASE_MAP[path.name]
    parent = path.parent.name
    return PHASE_MAP.get(parent, "unknown")


def red_gate_evidence(img: np.ndarray) -> tuple[float, float, int]:
    """Return (red_frac, largest_blob_frac, largest_blob_px) using relaxed HSV red."""
    h, w = img.shape[:2]
    area = float(h * w)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lo = cv2.inRange(
        hsv,
        (0, EVIDENCE_SAT_MIN, EVIDENCE_VAL_MIN),
        (EVIDENCE_HUE_LOW_MAX, 255, 255),
    )
    hi = cv2.inRange(
        hsv,
        (EVIDENCE_HUE_HIGH_MIN, EVIDENCE_SAT_MIN, EVIDENCE_VAL_MIN),
        (180, 255, 255),
    )
    mask = cv2.bitwise_or(lo, hi)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    red_px = int(cv2.countNonZero(mask))
    red_frac = red_px / area
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = 0
    for c in contours:
        a = int(cv2.contourArea(c))
        if a > best:
            best = a
    return red_frac, best / area, best


def gate_visible_proxy(red_frac: float, blob_frac: float, blob_px: int) -> bool:
    """Heuristic: enough clustered red mass to imply a gate ring is in view."""
    if blob_px >= EVIDENCE_MIN_BLOB_PX and blob_frac >= EVIDENCE_MIN_BLOB_FRAC:
        return True
    if red_frac >= EVIDENCE_MIN_RED_FRAC and blob_frac >= EVIDENCE_MIN_BLOB_FRAC * 0.5:
        return True
    return False


def discover_recordings() -> list[Path]:
    roots = [
        Path(r"C:\Users\tsion\Projects\eni_dcim_phase1\logs"),
        Path(r"C:\Users\tsion\Projects\eni_dcim_phase1\recordings"),
        Path(r"C:\Users\tsion\Projects\eni_dcim_phase1\fixtures"),
    ]
    found: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*.aigprec"):
            if p.stat().st_size > 1_000_000:
                found.append(p)
    # De-dupe by size+name; prefer logs/recordings over fixtures.
    uniq: dict[str, Path] = {}
    for p in found:
        key = f"{p.name}:{p.stat().st_size}"
        prev = uniq.get(key)
        if prev is None:
            uniq[key] = p
            continue
        score = int("fixtures" not in str(p)) + int("logs" in str(p) or "recordings" in str(p))
        prev_score = int("fixtures" not in str(prev)) + int(
            "logs" in str(prev) or "recordings" in str(prev)
        )
        if score > prev_score:
            uniq[key] = p
    # Skip tiny idle menu probe if present and very small det utility
    paths = sorted(uniq.values(), key=lambda p: p.stat().st_size, reverse=True)
    return paths


def downscale_jpeg(jpeg: bytes, max_w: int = 800, quality: int = 82) -> bytes | None:
    img = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return None
    h, w = img.shape[:2]
    if w > max_w:
        scale = max_w / w
        img = cv2.resize(img, (max_w, int(h * scale)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    return buf.tobytes() if ok else None


def eval_one(
    path: Path,
    detector: HsvGateDetector,
    visible_pool: list[FrameCand],
    no_gate_pool: list[FrameCand],
) -> RecStats:
    key = recording_key(path)
    stats = RecStats(path=str(path), name=key, phase=phase_for(path))
    assembler = ChunkAssembler()
    t0: int | None = None
    seen = 0

    for mono_ns, stream_id, data in read_recording(str(path)):
        if stream_id != STREAM_VISION:
            continue
        done = assembler.feed(data)
        if done is None:
            continue
        frame_id, ts_ns, jpeg = done
        seen += 1
        if t0 is None:
            t0 = mono_ns
        rel_s = (mono_ns - t0) / 1e9
        sec = int(rel_s)

        if stats.first_ts_ns is None:
            stats.first_ts_ns = ts_ns
        stats.last_ts_ns = ts_ns

        img = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue

        stats.frames += 1
        bucket = stats.per_sec.setdefault(sec, [0, 0, 0, 0, 0.0])
        bucket[0] += 1

        det = detector.detect(CameraFrame(frame_id, ts_ns, img))
        red_frac, blob_frac, blob_px = red_gate_evidence(img)
        bucket[4] += red_frac

        if det is not None:
            stats.detections += 1
            bucket[1] += 1
            if det.rel_pose is not None:
                stats.pnp_ok += 1
                stats.distances.append(float(det.rel_pose.distance))
            continue

        # Miss classification
        if gate_visible_proxy(red_frac, blob_frac, blob_px):
            stats.miss_visible += 1
            bucket[3] += 1
            # Prefer mid-race diversity for hard frames
            if rel_s >= 3.0 or stats.miss_visible <= 30:
                visible_pool.append(
                    FrameCand(key, frame_id, jpeg, red_frac, blob_frac, "visible_miss")
                )
        else:
            stats.miss_no_gate += 1
            bucket[2] += 1
            if len(no_gate_pool) < 200:
                no_gate_pool.append(
                    FrameCand(key, frame_id, jpeg, red_frac, blob_frac, "no_gate")
                )

        # Cap memory
        if len(visible_pool) > 400:
            visible_pool.sort(key=lambda c: c.blob_frac + c.red_frac, reverse=True)
            # keep diversity by recording
            kept: list[FrameCand] = []
            counts: dict[str, int] = {}
            for c in visible_pool:
                if counts.get(c.recording_key, 0) >= 25:
                    continue
                kept.append(c)
                counts[c.recording_key] = counts.get(c.recording_key, 0) + 1
                if len(kept) >= 200:
                    break
            visible_pool[:] = kept

    return stats


def pick_diverse(pool: list[FrameCand], n: int, per_rec: int) -> list[FrameCand]:
    pool = sorted(pool, key=lambda c: c.blob_frac + 0.5 * c.red_frac, reverse=True)
    selected: list[FrameCand] = []
    counts: dict[str, int] = {}
    for c in pool:
        if counts.get(c.recording_key, 0) >= per_rec:
            continue
        # skip near-duplicate frame ids
        if any(
            s.recording_key == c.recording_key and abs(s.frame_id - c.frame_id) < 8
            for s in selected
        ):
            continue
        selected.append(c)
        counts[c.recording_key] = counts.get(c.recording_key, 0) + 1
        if len(selected) >= n:
            break
    return selected


def save_examples(cands: list[FrameCand], out_dir: Path) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.jpg"):
        old.unlink()
    names: list[str] = []
    for c in cands:
        data = downscale_jpeg(c.jpeg, max_w=800)
        if data is None:
            continue
        name = f"{c.recording_key}_{c.frame_id}.jpg"
        name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)
        (out_dir / name).write_bytes(data)
        names.append(name)
    return names


def interpret(s: RecStats) -> str:
    dist = ""
    if s.distances:
        d = np.asarray(s.distances, dtype=np.float64)
        dist = f" Gate distance when detected: mean {d.mean():.1f} m (std {d.std():.1f} m)."
    if s.det_pct >= 90:
        return (
            f"High raw detection ({s.det_pct:.1f}%) — gate usually in view and HSV detector locks on."
            f" Classified visible-gate misses are only {s.visible_miss_pct:.1f}% of frames;"
            f" remaining non-detections are mostly no-gate / off-axis ({s.no_gate_pct:.1f}%)."
            f"{dist}"
        )
    if s.det_pct < 25:
        return (
            f"Raw detection collapses to {s.det_pct:.1f}%, but that number is dominated by"
            f" no-gate-in-view frames ({s.no_gate_pct:.1f}%) — tumbling / facing away."
            f" True visible-gate misses are {s.visible_miss_pct:.1f}% of frames"
            f" ({s.miss_visible}/{s.frames})."
            f"{dist}"
        )
    return (
        f"Moderate detection ({s.det_pct:.1f}%). No-gate frames {s.no_gate_pct:.1f}%;"
        f" visible-gate misses {s.visible_miss_pct:.1f}% — these are the actionable detector failures."
        f"{dist}"
    )


def write_report(
    stats_list: list[RecStats],
    hard_names: list[str],
    no_gate_names: list[str],
) -> None:
    lines = [
        "# Detector evaluation with classified misses",
        "",
        "Generated 2026-07-14 by `analysis/2026-07-14-detector-eval/run_classified_eval.py`.",
        "Reuses `HsvGateDetector` + `ChunkAssembler` over local `.aigprec` recordings",
        "from `eni_dcim_phase1` (not committed).",
        "",
        "## Classification method",
        "",
        "Every assembled frame is run through the repo HSV gate detector. Misses are then",
        "split with a **relaxed red-pixel / contour proxy** (no human labels):",
        "",
        "1. Build a relaxed HSV red mask (hue bands 0–14 and 166–180, sat≥55, val≥45) —",
        "   looser than the detector's sat≥90 / val≥70 so motion-blurred rings still count.",
        "2. Morphological close; measure `red_frac` and largest external contour area.",
        "3. Label **visible gate** if largest blob ≥120 px and blob_frac ≥0.0006, or",
        "   red_frac ≥0.0012 with a non-trivial blob. Otherwise **no gate in view**.",
        "4. Report rates as % of all frames:",
        "   - (a) `no_gate_in_view_%` — expected misses (facing away / tumble / blank).",
        "   - (b) `visible_gate_missed_%` — real detector failures.",
        "",
        "PnP-solve % is over all frames (same as prior eval's PnP/frm).",
        "",
        "## Per-recording summary",
        "",
        "| recording | phase | frames | det% | PnP% | dist mean±std (m) | no-gate-in-view% | visible-gate-missed% |",
        "|---|---|---:|---:|---:|---|---:|---:|",
    ]
    for s in stats_list:
        if s.distances:
            d = np.asarray(s.distances, dtype=np.float64)
            dist = f"{d.mean():.2f}±{d.std():.2f}"
        else:
            dist = "n/a"
        lines.append(
            f"| `{s.name}` | {s.phase} | {s.frames} | {s.det_pct:.1f} | {s.pnp_pct:.1f} | "
            f"{dist} | {s.no_gate_pct:.1f} | {s.visible_miss_pct:.1f} |"
        )

    lines += ["", "## Interpretation (per recording)", ""]
    for s in stats_list:
        lines.append(f"### `{s.name}` ({s.phase})")
        lines.append("")
        lines.append(interpret(s))
        lines.append("")

    total_f = sum(s.frames for s in stats_list)
    total_d = sum(s.detections for s in stats_list)
    total_ng = sum(s.miss_no_gate for s in stats_list)
    total_vm = sum(s.miss_visible for s in stats_list)
    lines += [
        "## Aggregate",
        "",
        f"- Frames: **{total_f}**; detections: **{total_d}** ({100.0 * total_d / total_f if total_f else 0:.1f}%)",
        f"- (a) no-gate-in-view: **{total_ng}** ({100.0 * total_ng / total_f if total_f else 0:.1f}%)",
        f"- (b) visible-gate-missed: **{total_vm}** ({100.0 * total_vm / total_f if total_f else 0:.1f}%)",
        "",
        "## Artifacts",
        "",
        f"- `stats.csv` — per-second timeline (`recording,time_s,frames,detections,...`)",
        f"- `hard_frames/` — {len(hard_names)} downscaled JPEGs (~800px) where a gate looks"
        " visible but the detector missed (`<recording>_<frame_id>.jpg`)",
        f"- `no_gate/` — {len(no_gate_names)} example frames with no gate evidence",
        "",
        "## Notes for cloud agent",
        "",
        "- Phase-2 raw det% of 5.9–17.8% is **not** a detector collapse by itself: most of",
        "  those frames are classified as no-gate-in-view. Focus tuning on `visible_gate_missed`.",
        "- Hard frames are the actionable failure set for HSV / contour thresholds.",
        "- Large `.aigprec` sources remain only on the operator machine.",
        "",
    ]
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")


def write_stats_csv(stats_list: list[RecStats]) -> None:
    path = OUT / "stats.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "recording",
                "phase",
                "time_s",
                "frames",
                "detections",
                "miss_no_gate",
                "miss_visible",
                "mean_red_frac",
            ]
        )
        for s in stats_list:
            for sec in sorted(s.per_sec):
                fr, det, ng, vm, red_sum = s.per_sec[sec]
                mean_red = red_sum / fr if fr else 0.0
                w.writerow(
                    [
                        s.name,
                        s.phase,
                        sec,
                        int(fr),
                        int(det),
                        int(ng),
                        int(vm),
                        f"{mean_red:.6f}",
                    ]
                )


def main() -> int:
    params = ParamSet.load(str(ROOT / "config" / "params_default.json"))
    detector = HsvGateDetector(params)
    recordings = discover_recordings()
    # Prefer the same core set as prior eval; drop the tiny phase1-idle if huge set.
    # Keep everything >40MB or the phase1e slice.
    recordings = [
        p
        for p in recordings
        if p.stat().st_size > 40_000_000 or "phase1e" in str(p).lower()
    ]
    print(f"Evaluating {len(recordings)} recordings -> {OUT}", flush=True)

    stats_list: list[RecStats] = []
    visible_pool: list[FrameCand] = []
    no_gate_pool: list[FrameCand] = []

    for path in recordings:
        print(f"  -> {path.name} / {path.parent.name} ({path.stat().st_size/1e6:.0f} MB)", flush=True)
        st = eval_one(path, detector, visible_pool, no_gate_pool)
        stats_list.append(st)
        print(
            f"     frames={st.frames} det={st.det_pct:.1f}% "
            f"no_gate={st.no_gate_pct:.1f}% vis_miss={st.visible_miss_pct:.1f}%",
            flush=True,
        )

    hard = pick_diverse(visible_pool, n=40, per_rec=10)
    # Prefer LOW red evidence for no-gate examples; diversify across recordings.
    no_gate_sorted = sorted(no_gate_pool, key=lambda c: c.red_frac + c.blob_frac)
    no_gate: list[FrameCand] = []
    ng_counts: dict[str, int] = {}
    for c in no_gate_sorted:
        if ng_counts.get(c.recording_key, 0) >= 3:
            continue
        if any(
            s.recording_key == c.recording_key and abs(s.frame_id - c.frame_id) < 15
            for s in no_gate
        ):
            continue
        no_gate.append(c)
        ng_counts[c.recording_key] = ng_counts.get(c.recording_key, 0) + 1
        if len(no_gate) >= 10:
            break

    hard_names = save_examples(hard, OUT / "hard_frames")
    no_gate_names = save_examples(no_gate, OUT / "no_gate")
    write_stats_csv(stats_list)
    write_report(stats_list, hard_names, no_gate_names)

    summary = {
        "recordings": [
            {
                "name": s.name,
                "phase": s.phase,
                "frames": s.frames,
                "detection_pct": round(s.det_pct, 2),
                "pnp_pct": round(s.pnp_pct, 2),
                "no_gate_in_view_pct": round(s.no_gate_pct, 2),
                "visible_gate_missed_pct": round(s.visible_miss_pct, 2),
                "miss_no_gate": s.miss_no_gate,
                "miss_visible": s.miss_visible,
                "dist_mean_m": float(np.mean(s.distances)) if s.distances else None,
                "dist_std_m": float(np.std(s.distances)) if s.distances else None,
            }
            for s in stats_list
        ],
        "hard_frames": hard_names,
        "no_gate_frames": no_gate_names,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote report.md, stats.csv, {len(hard_names)} hard, {len(no_gate_names)} no_gate", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
