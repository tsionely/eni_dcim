"""Remine up to 40 visible-miss + 10 no-gate JPEGs into this analysis folder.

Faster pass (stride=2) with looser diversity so we fill the quota.
"""
from __future__ import annotations

import json
import sys
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

# Import helpers from the main eval module
sys.path.insert(0, str(OUT))
from run_classified_eval import (  # noqa: E402
    FrameCand,
    discover_recordings,
    downscale_jpeg,
    gate_visible_proxy,
    recording_key,
    red_gate_evidence,
    save_examples,
)


def main() -> int:
    params = ParamSet.load(str(ROOT / "config" / "params_default.json"))
    detector = HsvGateDetector(params)
    recordings = [
        p
        for p in discover_recordings()
        if p.stat().st_size > 40_000_000 or "phase1e" in str(p).lower()
    ]

    visible: list[FrameCand] = []
    no_gate: list[FrameCand] = []
    stride = 2

    for path in recordings:
        key = recording_key(path)
        print(f"Mining {key}...", flush=True)
        assembler = ChunkAssembler()
        seen = 0
        t0 = None
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
            if t0 is None:
                t0 = mono_ns
            rel_s = (mono_ns - t0) / 1e9
            img = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                continue
            det = detector.detect(CameraFrame(frame_id, ts_ns, img))
            if det is not None:
                continue
            red_frac, blob_frac, blob_px = red_gate_evidence(img)
            if gate_visible_proxy(red_frac, blob_frac, blob_px):
                # Prefer mid-recording for hard cases
                if rel_s < 1.0 and len([c for c in visible if c.recording_key == key]) > 2:
                    continue
                visible.append(
                    FrameCand(key, frame_id, jpeg, red_frac, blob_frac, "visible_miss")
                )
            else:
                no_gate.append(
                    FrameCand(key, frame_id, jpeg, red_frac, blob_frac, "no_gate")
                )

    # Diversify visible: sort by evidence, spread frame_ids, fill to 40
    visible.sort(key=lambda c: c.blob_frac + 0.5 * c.red_frac, reverse=True)
    hard: list[FrameCand] = []
    counts: dict[str, int] = {}
    for c in visible:
        if counts.get(c.recording_key, 0) >= 12:
            continue
        if any(
            s.recording_key == c.recording_key and abs(s.frame_id - c.frame_id) < 25
            for s in hard
        ):
            continue
        hard.append(c)
        counts[c.recording_key] = counts.get(c.recording_key, 0) + 1
        if len(hard) >= 40:
            break

    # If still short, loosen spacing
    if len(hard) < 40:
        for c in visible:
            if any(
                s.recording_key == c.recording_key and s.frame_id == c.frame_id
                for s in hard
            ):
                continue
            if any(
                s.recording_key == c.recording_key and abs(s.frame_id - c.frame_id) < 5
                for s in hard
            ):
                continue
            hard.append(c)
            if len(hard) >= 40:
                break

    no_gate.sort(key=lambda c: c.red_frac + c.blob_frac)
    ng: list[FrameCand] = []
    ng_counts: dict[str, int] = {}
    for c in no_gate:
        if ng_counts.get(c.recording_key, 0) >= 3:
            continue
        if any(
            s.recording_key == c.recording_key and abs(s.frame_id - c.frame_id) < 40
            for s in ng
        ):
            continue
        # Prefer mid/late race blanks over frame 0 menu
        if c.frame_id < 5 and ng_counts.get(c.recording_key, 0) >= 1:
            continue
        ng.append(c)
        ng_counts[c.recording_key] = ng_counts.get(c.recording_key, 0) + 1
        if len(ng) >= 10:
            break
    if len(ng) < 10:
        for c in no_gate:
            if any(s.frame_id == c.frame_id and s.recording_key == c.recording_key for s in ng):
                continue
            ng.append(c)
            if len(ng) >= 10:
                break

    hard_names = save_examples(hard, OUT / "hard_frames")
    no_gate_names = save_examples(ng, OUT / "no_gate")

    # Patch report artifact counts + summary.json
    summary_path = OUT / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["hard_frames"] = hard_names
    summary["no_gate_frames"] = no_gate_names
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    report = (OUT / "report.md").read_text(encoding="utf-8")
    import re

    report = re.sub(
        r"`hard_frames/` — \d+ downscaled",
        f"`hard_frames/` — {len(hard_names)} downscaled",
        report,
    )
    report = re.sub(
        r"`no_gate/` — \d+ example",
        f"`no_gate/` — {len(no_gate_names)} example",
        report,
    )
    (OUT / "report.md").write_text(report, encoding="utf-8")
    print(f"Saved {len(hard_names)} hard, {len(no_gate_names)} no_gate", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
