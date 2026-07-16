"""Extract FPV frames from vision.aigprec at key flight times for collision ID.

Operator f4_late/f4_end are NOT sim FPV (pause menu / terminal) — ID must come from vision.
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

from aigp.io.udp_tap import STREAM_VISION, read_recording  # noqa: E402
from aigp.io.vision_rx import ChunkAssembler  # noqa: E402

PASS_FLIGHT = "20260716T131137-2ca531c3"
FLIGHT_LOG = (
    ROOT
    / "fixtures"
    / "20260716T132549-phase3j-r2training-rerun"
    / f"{PASS_FLIGHT}-flight.jsonl"
)
VISION = Path(
    r"C:\Users\tsion\Projects\eni_dcim_phase1\logs"
) / PASS_FLIGHT / "vision.aigprec"

CYAN_H_LO, CYAN_H_HI = 90, 98
CYAN_S_MIN, CYAN_V_MIN = 120, 120

TARGETS = [
    (26.4, "pass"),
    (32.5, "commit"),
    (33.0, "retreat"),
    (35.5, ""),
    (37.5, ""),
    (38.5, ""),
    (39.5, ""),
    (39.79, "collision"),
]


def downscale(img: np.ndarray, max_w: int = 900) -> np.ndarray:
    h, w = img.shape[:2]
    if w <= max_w:
        return img
    return cv2.resize(img, (max_w, int(h * max_w / w)))


def cyan_mask(img: np.ndarray) -> tuple[np.ndarray, float]:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(
        hsv, (CYAN_H_LO, CYAN_S_MIN, CYAN_V_MIN), (CYAN_H_HI, 255, 255)
    )
    frac = float(cv2.countNonZero(mask)) / (img.shape[0] * img.shape[1])
    return mask, frac


def center_brightness(img: np.ndarray, crop: int = 80) -> float:
    h, w = img.shape[:2]
    y0, x0 = max(0, h // 2 - crop // 2), max(0, w // 2 - crop // 2)
    patch = img[y0 : y0 + crop, x0 : x0 + crop]
    gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
    return float(gray.mean())


def main() -> None:
    assert FLIGHT_LOG.exists(), FLIGHT_LOG
    assert VISION.exists(), VISION

    first = json.loads(FLIGHT_LOG.read_text(encoding="utf-8").splitlines()[0])
    t0 = int(first["mono_ns"])
    print(f"t0 mono_ns={t0}")

    out_dir = OUT / "collision_frames"
    out_dir.mkdir(parents=True, exist_ok=True)

    best: dict[float, tuple[float, float, bytes] | None] = {t: None for t, _ in TARGETS}

    assembler = ChunkAssembler()
    n = 0
    for mono_ns, stream_id, data in read_recording(str(VISION)):
        if stream_id != STREAM_VISION:
            continue
        done = assembler.feed(data)
        if done is None:
            continue
        _fid, _ts, jpeg = done
        n += 1
        t = (mono_ns - t0) / 1e9
        for tgt, _ in TARGETS:
            err = abs(t - tgt)
            cur = best[tgt]
            if cur is None or err < cur[0]:
                best[tgt] = (err, t, jpeg)

    print(f"assembled_frames={n}")
    rows = []
    for tgt, label in TARGETS:
        pack = best[tgt]
        if pack is None:
            print(f"MISSING tgt={tgt} {label}")
            continue
        err, t, jpeg = pack
        img = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            print(f"DECODE_FAIL tgt={tgt}")
            continue
        mask, frac = cyan_mask(img)
        bright = center_brightness(img)
        img_ds = downscale(img)
        name = f"vision_t{tgt:.1f}.jpg"
        path = out_dir / name
        cv2.imwrite(str(path), img_ds, [int(cv2.IMWRITE_JPEG_QUALITY), 85])

        overlay = img.copy()
        overlay[mask > 0] = (255, 255, 0)
        vis = cv2.addWeighted(overlay, 0.35, img, 0.65, 0)
        cv2.putText(
            vis,
            f"t={t:.3f} err={err:.3f} cyan={frac:.4f} {label}",
            (8, 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        cyan_path = out_dir / f"vision_t{tgt:.1f}_cyan.jpg"
        cv2.imwrite(str(cyan_path), downscale(vis), [int(cv2.IMWRITE_JPEG_QUALITY), 85])

        row = {
            "tgt": tgt,
            "label": label,
            "t": t,
            "err": err,
            "cyan_frac": frac,
            "center_bright_80": bright,
            "file": name,
        }
        rows.append(row)
        print(
            f"tgt={tgt:.2f} t={t:.4f} err={err:.4f} cyan_frac={frac:.6f} "
            f"center_bright={bright:.1f} {label}"
        )

    (OUT / "collision_frames" / "vision_extract_summary.json").write_text(
        json.dumps({"t0": t0, "n_assembled": n, "frames": rows}, indent=2),
        encoding="utf-8",
    )
    print("done ->", out_dir)


if __name__ == "__main__":
    main()