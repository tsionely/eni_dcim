"""Diversified hardest-frame mining (post-pass / standalone).

Keeps top-N per recording so tumble/DSQ flights are not drowned out by early
misses from the first large parked-race recording.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
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
class Cand:
    score: float
    reason: str
    frame_id: int
    ts_ns: int
    recording: str
    jpeg: bytes
    distance_m: float | None
    center_px: tuple[float, float] | None


def score_det(det, prev_c, prev_d):
    if det is None:
        return 100.0, "miss", None, None
    center = det.center_px
    dist = det.rel_pose.distance if det.rel_pose is not None else None
    if det.rel_pose is None:
        return 85.0, "pnp_fail", None, center
    score, reason = 0.0, "ok"
    if prev_d is not None and abs(dist - prev_d) > 3.0:
        jump = abs(dist - prev_d)
        score, reason = min(75.0, 40.0 + jump), f"distance_jump_{jump:.1f}m"
    if prev_c is not None:
        cjump = math.hypot(center[0] - prev_c[0], center[1] - prev_c[1])
        if cjump > 80.0:
            s2 = min(70.0, 30.0 + cjump / 4.0)
            if s2 >= score:
                score, reason = s2, f"center_jump_{cjump:.0f}px"
    return score, reason, dist, center


def mine_one(path: Path, detector: HsvGateDetector, per_rec: int, stride: int) -> list[Cand]:
    asm = ChunkAssembler()
    prev_c = prev_d = None
    seen = 0
    pool: list[Cand] = []
    for _, stream_id, data in read_recording(str(path)):
        if stream_id != STREAM_VISION:
            continue
        done = asm.feed(data)
        if done is None:
            continue
        frame_id, ts_ns, jpeg = done
        seen += 1
        if stride > 1 and (seen % stride) != 0:
            continue
        img = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            pool.append(Cand(95.0, "decode_fail", frame_id, ts_ns, str(path), jpeg, None, None))
            continue
        det = detector.detect(CameraFrame(frame_id, ts_ns, img))
        sc, reason, dist, center = score_det(det, prev_c, prev_d)
        if det is not None:
            prev_c, prev_d = det.center_px, dist
        else:
            prev_c = prev_d = None
        if sc >= 40.0:
            pool.append(Cand(sc, reason, frame_id, ts_ns, str(path), jpeg, dist, center))
            if len(pool) > per_rec * 8:
                pool.sort(key=lambda c: (c.score, c.frame_id), reverse=True)
                # diversify by frame_id buckets
                kept: list[Cand] = []
                used_ids: set[int] = set()
                for c in pool:
                    bucket = c.frame_id // 50
                    if bucket in used_ids and c.reason == "miss":
                        continue
                    used_ids.add(bucket)
                    kept.append(c)
                    if len(kept) >= per_rec * 3:
                        break
                pool = kept
    pool.sort(key=lambda c: (c.score, c.frame_id), reverse=True)
    # Final per-recording diversity: max 1 miss per 25-frame bucket
    out: list[Cand] = []
    used_buckets: set[tuple[str, int]] = set()
    for c in pool:
        bucket = (c.reason.split("_")[0], c.frame_id // 25)
        if bucket in used_buckets:
            continue
        used_buckets.add(bucket)
        out.append(c)
        if len(out) >= per_rec:
            break
    return out


def save(cands: list[Cand], out_dir: Path, max_width: int = 640) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.jpg"):
        old.unlink()
    meta = []
    for i, c in enumerate(cands):
        img = cv2.imdecode(np.frombuffer(c.jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue
        h, w = img.shape[:2]
        scale = 1.0
        if w > max_width:
            scale = max_width / w
            img = cv2.resize(img, (max_width, int(h * scale)), interpolation=cv2.INTER_AREA)
        rec_name = Path(c.recording).parent.name
        if rec_name in ("recordings", "fixtures") or rec_name.endswith("phase1e"):
            rec_name = Path(c.recording).stem[:24]
        label = f"{rec_name} {c.reason} f={c.frame_id}"
        cv2.putText(img, label[:60], (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
        if c.center_px is not None:
            cx, cy = c.center_px[0] * scale, c.center_px[1] * scale
            cv2.drawMarker(img, (int(cx), int(cy)), (0, 255, 0), cv2.MARKER_CROSS, 16, 2)
        name = f"{i:02d}_s{int(c.score):03d}_{rec_name}_{c.reason}_f{c.frame_id}.jpg"
        name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)
        path = out_dir / name
        cv2.imwrite(str(path), img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        meta.append({
            "file": str(path.relative_to(ROOT)).replace("\\", "/"),
            "score": c.score,
            "reason": c.reason,
            "frame_id": c.frame_id,
            "ts_ns": c.ts_ns,
            "recording": c.recording,
            "distance_m": c.distance_m,
            "center_px": list(c.center_px) if c.center_px else None,
            "bytes": path.stat().st_size,
        })
    return meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-recording", type=int, default=8)
    ap.add_argument("--stride", type=int, default=2)
    ap.add_argument("--params", default=str(ROOT / "config" / "params_default.json"))
    ap.add_argument("--out-dir", default=str(ROOT / "analysis" / "hard_frames"))
    args = ap.parse_args()

    roots = [
        Path(r"C:\Users\tsion\Projects\eni_dcim_phase1\logs"),
        Path(r"C:\Users\tsion\Projects\eni_dcim_phase1\recordings"),
    ]
    paths = []
    for root in roots:
        for p in root.rglob("*.aigprec"):
            if p.stat().st_size > 1_000_000:
                paths.append(p)
    paths = sorted(paths, key=lambda p: p.stat().st_size, reverse=True)

    detector = HsvGateDetector(ParamSet.load(args.params))
    all_cands: list[Cand] = []
    for p in paths:
        print(f"mining {p} ...", flush=True)
        cands = mine_one(p, detector, args.per_recording, args.stride)
        print(f"  kept {len(cands)}", flush=True)
        all_cands.extend(cands)

    # Global order: prefer non-miss novelty, then score
    reason_rank = {"miss": 0, "pnp_fail": 1, "distance": 2, "center": 2, "decode_fail": 1}
    all_cands.sort(
        key=lambda c: (
            reason_rank.get(c.reason.split("_")[0], 0) if c.reason != "miss" else -1,
            c.score,
            c.frame_id,
        ),
        reverse=True,
    )
    # Interleave by recording for the final 40
    by_rec: dict[str, list[Cand]] = defaultdict(list)
    for c in all_cands:
        by_rec[c.recording].append(c)
    final: list[Cand] = []
    while len(final) < 40 and any(by_rec.values()):
        for rec in list(by_rec.keys()):
            if not by_rec[rec]:
                continue
            final.append(by_rec[rec].pop(0))
            if len(final) >= 40:
                break

    meta = save(final, Path(args.out_dir))
    out_json = ROOT / "analysis" / "hard_frames_index.json"
    out_json.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Wrote {len(meta)} frames + {out_json}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
