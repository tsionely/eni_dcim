"""Detector evaluation at scale over local .aigprec recordings.

DATA ANALYST harness (read-only on src/). Writes metrics + hard-frame JPEGs
under analysis/. Point --recordings-root at the operator checkout that holds
the large binaries.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aigp.core.messages import CameraFrame  # noqa: E402
from aigp.core.params import ParamSet  # noqa: E402
from aigp.io.udp_tap import STREAM_VISION, read_recording  # noqa: E402
from aigp.io.vision_rx import ChunkAssembler  # noqa: E402
from aigp.perception.gate_detector_hsv import HsvGateDetector  # noqa: E402


@dataclass
class HardCandidate:
    score: float
    reason: str
    frame_id: int
    ts_ns: int
    recording: str
    jpeg: bytes
    distance_m: float | None = None
    center_px: tuple[float, float] | None = None


@dataclass
class RecordingStats:
    path: str
    size_mb: float
    frames: int = 0
    decode_failures: int = 0
    detections: int = 0
    pnp_ok: int = 0
    distances_m: list[float] = field(default_factory=list)
    centers_px: list[tuple[float, float]] = field(default_factory=list)
    frame_gaps_ms: list[float] = field(default_factory=list)
    first_ts_ns: int | None = None
    last_ts_ns: int | None = None

    @property
    def detection_rate(self) -> float:
        return 100.0 * self.detections / self.frames if self.frames else 0.0

    @property
    def pnp_rate_of_det(self) -> float:
        return 100.0 * self.pnp_ok / self.detections if self.detections else 0.0

    @property
    def pnp_rate_of_frames(self) -> float:
        return 100.0 * self.pnp_ok / self.frames if self.frames else 0.0

    def stability(self) -> dict:
        out: dict = {}
        if len(self.distances_m) >= 2:
            d = np.asarray(self.distances_m, dtype=np.float64)
            out["distance_mean_m"] = float(d.mean())
            out["distance_std_m"] = float(d.std())
            out["distance_median_m"] = float(np.median(d))
            dd = np.diff(d)
            out["distance_step_std_m"] = float(dd.std())
            out["distance_step_p95_abs_m"] = float(np.percentile(np.abs(dd), 95))
        if len(self.centers_px) >= 2:
            c = np.asarray(self.centers_px, dtype=np.float64)
            out["center_std_px"] = [float(c[:, 0].std()), float(c[:, 1].std())]
            jumps = np.linalg.norm(np.diff(c, axis=0), axis=1)
            out["center_jump_mean_px"] = float(jumps.mean())
            out["center_jump_p95_px"] = float(np.percentile(jumps, 95))
        if self.frame_gaps_ms:
            g = np.asarray(self.frame_gaps_ms, dtype=np.float64)
            out["frame_gap_median_ms"] = float(np.median(g))
            out["frame_gap_p95_ms"] = float(np.percentile(g, 95))
            out["frame_gap_max_ms"] = float(g.max())
            out["large_gaps_gt_50ms"] = int((g > 50.0).sum())
        if self.first_ts_ns is not None and self.last_ts_ns is not None:
            out["span_s"] = (self.last_ts_ns - self.first_ts_ns) / 1e9
        return out

    def summary(self) -> dict:
        return {
            "path": self.path,
            "size_mb": self.size_mb,
            "frames": self.frames,
            "decode_failures": self.decode_failures,
            "detections": self.detections,
            "detection_rate_pct": round(self.detection_rate, 2),
            "pnp_ok": self.pnp_ok,
            "pnp_rate_of_detections_pct": round(self.pnp_rate_of_det, 2),
            "pnp_rate_of_frames_pct": round(self.pnp_rate_of_frames, 2),
            "stability": self.stability(),
        }


def discover_recordings(roots: list[Path]) -> list[Path]:
    found: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        if root.is_file() and root.suffix == ".aigprec":
            found.append(root)
            continue
        for p in root.rglob("*.aigprec"):
            if p.stat().st_size > 1_000_000:
                found.append(p)
    # De-dupe by resolved path, prefer unique content via size+name
    uniq: dict[str, Path] = {}
    for p in found:
        key = f"{p.name}:{p.stat().st_size}"
        # Prefer logs/vision and recordings/ over fixtures copies of same size
        prev = uniq.get(key)
        if prev is None:
            uniq[key] = p
        else:
            score = int("fixtures" not in str(p)) + int("logs" in str(p))
            prev_score = int("fixtures" not in str(prev)) + int("logs" in str(prev))
            if score > prev_score:
                uniq[key] = p
    return sorted(uniq.values(), key=lambda p: p.stat().st_size, reverse=True)


def hardness(
    det,
    prev_center: tuple[float, float] | None,
    prev_dist: float | None,
    *,
    frame_id: int = 0,
    rel_s: float = 0.0,
) -> tuple[float, str, float | None, tuple[float, float] | None]:
    """Higher score = harder / more interesting failure mode.

    Misses early in a recording (menu/idle) are down-weighted so mined frames
    prefer mid-race failures and pose jumps.
    """
    if det is None:
        # Prefer misses after the drone is likely racing (>5s / higher frame ids).
        base = 70.0 + min(25.0, max(0.0, rel_s - 5.0))
        if frame_id < 30:
            base -= 20.0
        return base, "miss", None, None
    center = det.center_px
    dist = det.rel_pose.distance if det.rel_pose is not None else None
    if det.rel_pose is None:
        return 80.0, "pnp_fail", None, center
    score = 0.0
    reason = "ok"
    if prev_dist is not None:
        jump = abs(dist - prev_dist)
        if jump > 3.0:
            score = max(score, min(70.0, 40.0 + jump))
            reason = f"distance_jump_{jump:.1f}m"
    if prev_center is not None:
        cjump = math.hypot(center[0] - prev_center[0], center[1] - prev_center[1])
        if cjump > 80.0:
            score = max(score, min(65.0, 30.0 + cjump / 4.0))
            reason = f"center_jump_{cjump:.0f}px"
    return score, reason, dist, center


def eval_recording(
    path: Path,
    detector: HsvGateDetector,
    hard_pool: list[HardCandidate],
    hard_keep: int,
    stride: int,
) -> RecordingStats:
    stats = RecordingStats(path=str(path), size_mb=round(path.stat().st_size / 1e6, 1))
    assembler = ChunkAssembler()
    prev_ts: int | None = None
    prev_center: tuple[float, float] | None = None
    prev_dist: float | None = None
    seen = 0
    t0_ns: int | None = None

    for mono_ns, stream_id, data in read_recording(str(path)):
        if stream_id != STREAM_VISION:
            continue
        done = assembler.feed(data)
        if done is None:
            continue
        frame_id, ts_ns, jpeg = done
        seen += 1
        if stride > 1 and (seen % stride) != 0:
            continue
        if t0_ns is None:
            t0_ns = mono_ns
        rel_s = (mono_ns - t0_ns) / 1e9

        if stats.first_ts_ns is None:
            stats.first_ts_ns = ts_ns
        if prev_ts is not None:
            stats.frame_gaps_ms.append((ts_ns - prev_ts) / 1e6)
        prev_ts = ts_ns
        stats.last_ts_ns = ts_ns

        img = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            stats.decode_failures += 1
            hard_pool.append(
                HardCandidate(95.0, "decode_fail", frame_id, ts_ns, str(path), jpeg)
            )
            continue

        stats.frames += 1
        det = detector.detect(CameraFrame(frame_id, ts_ns, img))
        score, reason, dist, center = hardness(
            det, prev_center, prev_dist, frame_id=frame_id, rel_s=rel_s
        )
        if det is not None:
            stats.detections += 1
            if det.rel_pose is not None:
                stats.pnp_ok += 1
                stats.distances_m.append(dist)  # type: ignore[arg-type]
            stats.centers_px.append(det.center_px)
            prev_center = det.center_px
            prev_dist = dist
        else:
            prev_center = None
            prev_dist = None

        if score >= 40.0:
            hard_pool.append(
                HardCandidate(
                    score=score,
                    reason=reason,
                    frame_id=frame_id,
                    ts_ns=ts_ns,
                    recording=str(path),
                    jpeg=jpeg,
                    distance_m=dist,
                    center_px=center,
                )
            )
            # Cap memory: keep only top candidates
            if len(hard_pool) > hard_keep * 4:
                hard_pool.sort(key=lambda c: c.score, reverse=True)
                del hard_pool[hard_keep * 3 :]

    return stats


def save_hard_frames(
    hard_pool: list[HardCandidate],
    out_dir: Path,
    n: int,
    max_width: int = 640,
    per_recording_cap: int | None = None,
) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    # Clear previous JPEGs from this run directory only
    for old in out_dir.glob("*.jpg"):
        old.unlink()
    hard_pool.sort(key=lambda c: c.score, reverse=True)
    if per_recording_cap is None:
        per_recording_cap = max(4, n // 4)
    saved: list[dict] = []
    per_rec: dict[str, int] = {}
    selected: list[HardCandidate] = []
    for cand in hard_pool:
        rec_path = Path(cand.recording)
        key = f"{rec_path.parent.name}/{rec_path.name}"
        if per_rec.get(key, 0) >= per_recording_cap:
            continue
        # Dedup near-identical frame ids from same recording
        if any(
            f"{Path(s.recording).parent.name}/{Path(s.recording).name}" == key
            and abs(s.frame_id - cand.frame_id) <= 2
            for s in selected
        ):
            continue
        selected.append(cand)
        per_rec[key] = per_rec.get(key, 0) + 1
        if len(selected) >= n:
            break
    # Include parent folder in filename so vision.aigprec sources stay distinct
    for i, cand in enumerate(selected):
        img = cv2.imdecode(np.frombuffer(cand.jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue
        h, w = img.shape[:2]
        scale_w = w
        if w > max_width:
            scale = max_width / w
            img = cv2.resize(img, (max_width, int(h * scale)), interpolation=cv2.INTER_AREA)
        # Annotate reason
        label = f"{cand.reason} id={cand.frame_id}"
        cv2.putText(img, label, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 1, cv2.LINE_AA)
        if cand.center_px is not None:
            cx, cy = cand.center_px
            if scale_w > max_width:
                cx *= max_width / scale_w
                cy *= max_width / scale_w
            cv2.drawMarker(img, (int(cx), int(cy)), (0, 255, 0), cv2.MARKER_CROSS, 16, 2)
        parent = Path(cand.recording).parent.name
        name = f"{i:02d}_{parent}_s{int(cand.score):03d}_{cand.reason}_f{cand.frame_id}.jpg"
        # Sanitize filename
        name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)
        out_path = out_dir / name
        cv2.imwrite(str(out_path), img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        saved.append(
            {
                "file": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                "score": cand.score,
                "reason": cand.reason,
                "frame_id": cand.frame_id,
                "ts_ns": cand.ts_ns,
                "recording": cand.recording,
                "distance_m": cand.distance_m,
                "center_px": list(cand.center_px) if cand.center_px else None,
                "bytes": out_path.stat().st_size,
            }
        )
    return saved


def write_report(stats_list: list[RecordingStats], hard_meta: list[dict], out_md: Path) -> None:
    lines = [
        "# Detector evaluation at scale",
        "",
        f"Generated by `analysis/eval_detector_scale.py`.",
        "",
        "## Per-recording summary",
        "",
        "| recording | MB | frames | det% | PnP/det% | PnP/frm% | dist mean±std (m) | center jump p95 (px) | span (s) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for s in stats_list:
        st = s.stability()
        dist = ""
        if "distance_mean_m" in st:
            dist = f"{st['distance_mean_m']:.2f}±{st['distance_std_m']:.2f}"
        cjump = f"{st.get('center_jump_p95_px', float('nan')):.1f}" if "center_jump_p95_px" in st else ""
        span = f"{st.get('span_s', float('nan')):.1f}" if "span_s" in st else ""
        name = Path(s.path).name
        parent = Path(s.path).parent.name
        lines.append(
            f"| `{parent}/{name}` | {s.size_mb} | {s.frames} | {s.detection_rate:.1f} | "
            f"{s.pnp_rate_of_det:.1f} | {s.pnp_rate_of_frames:.1f} | {dist} | {cjump} | {span} |"
        )

    total_frames = sum(s.frames for s in stats_list)
    total_det = sum(s.detections for s in stats_list)
    total_pnp = sum(s.pnp_ok for s in stats_list)
    lines += [
        "",
        "## Aggregate",
        "",
        f"- Recordings evaluated: **{len(stats_list)}**",
        f"- Frames: **{total_frames}**",
        f"- Detection rate: **{(100.0 * total_det / total_frames) if total_frames else 0:.2f}%** "
        f"({total_det}/{total_frames})",
        f"- PnP solve rate (of detections): **{(100.0 * total_pnp / total_det) if total_det else 0:.2f}%** "
        f"({total_pnp}/{total_det})",
        f"- PnP solve rate (of frames): **{(100.0 * total_pnp / total_frames) if total_frames else 0:.2f}%**",
        "",
        "## Cross-checks / anomalies",
        "",
    ]
    for s in stats_list:
        st = s.stability()
        name = Path(s.path).name
        notes = []
        if s.decode_failures:
            notes.append(f"{s.decode_failures} JPEG decode failures")
        if st.get("large_gaps_gt_50ms", 0):
            notes.append(
                f"{st['large_gaps_gt_50ms']} frame gaps >50ms "
                f"(max {st.get('frame_gap_max_ms', 0):.1f} ms)"
            )
        if st.get("distance_step_p95_abs_m", 0) and st["distance_step_p95_abs_m"] > 2.0:
            notes.append(
                f"unstable distance steps (p95 abs Δd={st['distance_step_p95_abs_m']:.2f} m)"
            )
        if s.frames and s.detection_rate < 95.0:
            notes.append(f"detection rate below 95% ({s.detection_rate:.1f}%)")
        if not notes:
            notes.append("no major anomalies flagged")
        lines.append(f"- `{name}`: " + "; ".join(notes))

    lines += [
        "",
        "## Hardest frames",
        "",
        f"Top {len(hard_meta)} saved under `analysis/hard_frames/` (downscaled JPEGs).",
        "",
        "| # | score | reason | frame | recording | file |",
        "|---:|---:|---|---:|---|---|",
    ]
    for i, h in enumerate(hard_meta):
        lines.append(
            f"| {i} | {h['score']:.0f} | `{h['reason']}` | {h['frame_id']} | "
            f"`{Path(h['recording']).name}` | `{h['file']}` |"
        )
    lines += [
        "",
        "## Notes for cloud agent",
        "",
        "- Detector `GateDetection.confidence` is currently hard-coded to `1.0` in "
        "`gate_detector_hsv.py`; hardness here uses miss / PnP-fail / jump heuristics instead.",
        "- Large `.aigprec` binaries were read from the operator checkout; they were not copied into git.",
        "",
    ]
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--recordings-root",
        action="append",
        default=[],
        help="Root(s) containing .aigprec files (repeatable)",
    )
    parser.add_argument("--params", default=str(ROOT / "config" / "params_default.json"))
    parser.add_argument("--hard-n", type=int, default=40)
    parser.add_argument("--stride", type=int, default=1, help="Evaluate every Nth assembled frame")
    parser.add_argument("--out-dir", default=str(ROOT / "analysis"))
    args = parser.parse_args()

    roots = [Path(p) for p in args.recordings_root] if args.recordings_root else [
        Path(r"C:\Users\tsion\Projects\eni_dcim_phase1\logs"),
        Path(r"C:\Users\tsion\Projects\eni_dcim_phase1\recordings"),
        Path(r"C:\Users\tsion\Projects\eni_dcim_phase1\fixtures"),
    ]
    recordings = discover_recordings(roots)
    if not recordings:
        print("No recordings found", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    hard_dir = out_dir / "hard_frames"
    params = ParamSet.load(args.params)
    detector = HsvGateDetector(params)

    print(f"Evaluating {len(recordings)} recordings (stride={args.stride})", flush=True)
    stats_list: list[RecordingStats] = []
    hard_pool: list[HardCandidate] = []
    for path in recordings:
        print(f"  -> {path} ({path.stat().st_size / 1e6:.1f} MB)", flush=True)
        st = eval_recording(path, detector, hard_pool, args.hard_n, args.stride)
        stats_list.append(st)
        print(
            f"     frames={st.frames} det={st.detection_rate:.1f}% "
            f"pnp/det={st.pnp_rate_of_det:.1f}%",
            flush=True,
        )

    hard_meta = save_hard_frames(hard_pool, hard_dir, args.hard_n)
    metrics_path = out_dir / "detector_eval_metrics.json"
    metrics_path.write_text(
        json.dumps(
            {
                "stride": args.stride,
                "recordings": [s.summary() for s in stats_list],
                "hard_frames": hard_meta,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    report_path = out_dir / "20260714-detector-eval-at-scale.md"
    write_report(stats_list, hard_meta, report_path)
    print(f"Wrote {metrics_path}", flush=True)
    print(f"Wrote {report_path}", flush=True)
    print(f"Wrote {len(hard_meta)} hard frames -> {hard_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
