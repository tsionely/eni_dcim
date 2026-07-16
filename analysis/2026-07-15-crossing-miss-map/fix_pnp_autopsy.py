"""Regenerate honest PnP outlier evidence for crossing-miss map."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from aigp.io.udp_tap import STREAM_VISION, read_recording  # noqa: E402
from aigp.io.vision_rx import ChunkAssembler  # noqa: E402


def vision_roots():
    roots = [
        ROOT / "recordings",
        ROOT / "logs",
        ROOT.parent / "eni_dcim" / "recordings",
        ROOT.parent / "eni_dcim" / "logs",
        Path.home() / "Documents" / "eni_dcim" / "recordings",
        Path.home() / "Documents" / "eni_dcim" / "logs",
    ]
    return [r for r in roots if r.exists()]


def find_sources(fix_dir: Path, flight_id: str) -> list[Path]:
    cands, seen = [], set()

    def add(p: Path):
        try:
            rp = p.resolve()
        except OSError:
            return
        if rp in seen or not p.is_file():
            return
        seen.add(rp)
        cands.append(p)

    for root in vision_roots():
        for p in root.rglob(f"*{flight_id}*.aigprec"):
            add(p)
        for d in root.rglob(f"*{flight_id}*"):
            if d.is_dir():
                for p in d.glob("*.aigprec"):
                    add(p)
                v = d / "vision.aigprec"
                if v.exists():
                    add(v)
    if fix_dir.exists():
        for p in fix_dir.glob(f"{flight_id}*.aigprec"):
            add(p)

    def rank(p: Path):
        name = p.name.lower()
        is_start = "slice_start" in name
        return (1 if is_start else 0, -p.stat().st_size, str(p))

    cands.sort(key=rank)
    return cands


def extract_by_ts(rec_path: Path, target_ts_ns: int, max_err_s: float = 0.08):
    asm = ChunkAssembler()
    best = None
    first_mono = None
    n = 0
    for mono_ns, stream_id, data in read_recording(str(rec_path)):
        if stream_id != STREAM_VISION:
            continue
        done = asm.feed(data)
        if done is None:
            continue
        frame_id, ts_ns, jpeg = done
        n += 1
        if first_mono is None:
            first_mono = mono_ns
        t_rel = (mono_ns - first_mono) / 1e9
        err = abs(int(ts_ns) - int(target_ts_ns)) / 1e9
        if best is None or err < best[0]:
            best = (err, t_rel, frame_id, jpeg, ts_ns)
        if int(ts_ns) > int(target_ts_ns) and best[0] < max_err_s:
            break
    if best is None:
        return None, {"error": "no_frames", "source": str(rec_path), "n_frames": n}
    err, t_rel, frame_id, jpeg, ts_ns = best
    meta = {
        "source": str(rec_path),
        "source_name": rec_path.name,
        "err_s": err,
        "t_rel": t_rel,
        "frame_id": frame_id,
        "ts_ns": ts_ns,
        "n_frames": n,
    }
    if err > max_err_s:
        meta["error"] = f"best_err {err:.3f}s > {max_err_s}s"
        return None, meta
    img = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
    return img, meta


def load_det(flight_jsonl: Path, ts_ns: int):
    with flight_jsonl.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec.get("topic") != "detection":
                continue
            d = rec.get("data") or {}
            if d.get("ts_ns") == ts_ns:
                return d
    return None


def classify(det, ty, dist):
    notes = []
    corners = det.get("corners_px")
    center = det.get("center_px")
    normal = (det.get("rel_pose") or {}).get("normal")
    w, h = (det.get("image_size") or [640, 360])[:2]
    pts = np.asarray(corners, float).reshape(-1, 2)
    cx, cy = float(center[0]), float(center[1])
    top = float(np.linalg.norm(pts[1] - pts[0]))
    bot = float(np.linalg.norm(pts[2] - pts[3]))
    left = float(np.linalg.norm(pts[3] - pts[0]))
    right = float(np.linalg.norm(pts[2] - pts[1]))
    trap = abs(top - bot) / (0.5 * (top + bot) + 1e-9)
    elev = math.degrees(math.atan2(abs(ty), max(dist, 1e-3)))
    notes.append(
        f"corners_px={corners}; center_px=[{cx:.1f},{cy:.1f}]; "
        f"edges top/bot/left/right={top:.0f}/{bot:.0f}/{left:.0f}/{right:.0f}px; trap={trap:.2f}"
    )
    if normal is not None:
        n = [float(x) for x in normal]
        notes.append(f"PnP normal={n}")
        if abs(n[1]) > 0.7:
            notes.append(
                "VERDICT: bad PnP / wrong quad — normal y-dominant (implausible for face-on ring)."
            )
        elif abs(n[2]) < 0.5:
            notes.append("VERDICT: normal not camera-facing — partial ring or mis-ordered corners.")
        elif elev > 25 and dist < 5:
            notes.append(
                f"VERDICT: ring-like quad but |ty|~{elev:.0f}deg at {dist:.1f}m — "
                "lock-rejected pose blow-up (banner/other-gate/partial), not true opening offset."
            )
        else:
            notes.append("VERDICT: inconclusive from geometry alone.")
    if cy < h * 0.28:
        notes.append("quad center high in frame.")
    if cx < w * 0.22 or cx > w * 0.78:
        notes.append("quad near L/R edge (partial/off-axis).")
    if trap > 0.22:
        notes.append("strong trapezoid — steep perspective or partial ring.")
    return notes


def render(out_path, title, corners, center, image_size=(640, 360), backdrop=None, footer=""):
    w, h = int(image_size[0]), int(image_size[1])
    if backdrop is not None:
        vis = backdrop.copy()
        if vis.shape[0] != h or vis.shape[1] != w:
            vis = cv2.resize(vis, (w, h), interpolation=cv2.INTER_AREA)
    else:
        vis = np.full((h, w, 3), 32, np.uint8)
        cv2.putText(
            vis,
            "NO PIXEL FRAME (schematic from corners_px)",
            (12, h // 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (80, 80, 200),
            1,
            cv2.LINE_AA,
        )
    if corners is not None:
        pts = np.asarray(corners, np.int32).reshape(-1, 2)
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
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), vis, [int(cv2.IMWRITE_JPEG_QUALITY), 85])


def phase_dir(phase: str) -> Path | None:
    for d in sorted((ROOT / "fixtures").glob(f"*{phase}*")):
        return d
    return None


def main():
    summary_path = OUT / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    outliers = summary.get("pnp_outliers") or []
    autopsy = []
    out_dir = OUT / "pnp_outliers"
    # remove stale wrong frames
    if out_dir.exists():
        for old in out_dir.glob("*.jpg"):
            old.unlink()

    for o in outliers:
        phase = o["phase"]
        flight_id = o["flight_id"]
        fix_dir = phase_dir(phase)
        if fix_dir is None:
            autopsy.append(f"{phase} `{flight_id}`: fixture dir missing")
            continue
        fp = fix_dir / f"{flight_id}-flight.jsonl"
        det = load_det(fp, int(o["ts_ns"])) if fp.exists() else None
        if det is None:
            autopsy.append(f"{phase} `{flight_id}` t={o['t']:.2f}: detection ts_ns not found in flight.jsonl")
            continue
        corners = det.get("corners_px")
        center = det.get("center_px")
        o["corners_px"] = corners
        o["center_px"] = center
        o["normal"] = (det.get("rel_pose") or {}).get("normal")
        o["image_size"] = det.get("image_size") or [640, 360]

        fname = f"{phase}_{flight_id[-6:]}_t{o['t']:.1f}_ty{o['ty']:+.1f}.jpg"
        out_img = out_dir / fname
        title = f"{phase} {flight_id[-8:]} t={o['t']:.1f}s d={o['dist']:.1f} ty={o['ty']:+.2f}"

        sources = find_sources(fix_dir, flight_id)
        img, meta = None, None
        for src in sources:
            img, meta = extract_by_ts(src, int(o["ts_ns"]), max_err_s=0.08)
            if img is not None:
                break

        geom = classify(det, float(o["ty"]), float(o["dist"]))

        if img is not None:
            render(out_img, title, corners, center, tuple(o["image_size"]), backdrop=img)
            o["frame_file"] = f"pnp_outliers/{fname}"
            o["evidence_kind"] = "exact_frame"
            note = (
                f"`{fname}` EXACT frame from `{Path(meta['source']).name}` "
                f"via ts_ns (err={meta['err_s']*1000:.1f}ms). {o['reason']}."
            )
        else:
            # schematic; optional late screen backdrop (labeled NOT exact)
            flights = sorted(fix_dir.glob("*-flight.jsonl"))
            idx = None
            for i, fpath in enumerate(flights, 1):
                if fpath.stem.replace("-flight", "") == flight_id:
                    idx = i
                    break
            backdrop = None
            late_note = "no late screen"
            if idx is not None:
                late = fix_dir / "screens" / f"f{idx}_late.jpg"
                if late.exists():
                    backdrop = cv2.imread(str(late))
                    late_note = f"backdrop=operator {late.name} (NOT exact outlier frame)"
            rejected = ""
            if meta is not None:
                rejected = (
                    f" Best local source `{meta.get('source_name')}` rejected: "
                    f"{meta.get('error')} (slice covers ~{meta.get('t_rel', 0):.2f}s)."
                )
            elif not sources:
                rejected = " No local .aigprec under recordings/logs/fixtures."
            footer = f"ts_ns={o['ts_ns']} | corners_px evidence | full recording unavailable | {late_note}"
            render(
                out_img,
                title + " [SCHEMATIC]",
                corners,
                center,
                tuple(o["image_size"]),
                backdrop=backdrop,
                footer=footer,
            )
            o["frame_file"] = f"pnp_outliers/{fname}"
            o["evidence_kind"] = "schematic_corners_px"
            note = (
                f"`{fname}` frames UNAVAILABLE at outlier t={o['t']:.2f}s (ts_ns={o['ts_ns']})."
                f"{rejected} Attached schematic from detection corners_px/center_px. {o['reason']}."
            )
        for g in geom:
            note += " " + g
        autopsy.append(note)
        print(note[:240], flush=True)

    summary["pnp_outliers"] = outliers
    summary["autopsy_notes"] = autopsy
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Rewrite report.md autopsy section honestly
    report_path = OUT / "report.md"
    report = report_path.read_text(encoding="utf-8")
    marker = "## Close-range PnP outlier autopsy"
    if marker not in report:
        raise SystemExit("autopsy section missing")
    head = report.split(marker)[0]
    # keep reading-the-convergence if present
    tail_marker = "## Reading the convergence"
    tail = ""
    if tail_marker in report:
        tail = tail_marker + report.split(tail_marker, 1)[1]
    else:
        # deliverables fallback
        dmark = "## Deliverables"
        if dmark in report:
            tail = dmark + report.split(dmark, 1)[1]

    lines = [
        marker + " (2-4.5 m)",
        "",
        "Raw detections (for autopsy only). Looking for |ty|>=2 m or consecutive dty>=0.8 m.",
        "Frames are matched by detection `ts_ns` against full recordings when present;",
        "start slices (~1s) are **rejected** when they do not cover the outlier time.",
        "Full ~300MB recordings were not available locally (only `*_slice_start.aigprec`);",
        "evidence plates below are schematics from `corners_px` unless an exact frame matched.",
        "",
        "| phase | flight | t (s) | dist (m) | ty (m) | dty | reason | evidence |",
        "|---|---|---:|---:|---:|---:|---|---|",
    ]
    for o in outliers:
        dty = f"{o['dty']:.2f}" if o.get("dty") is not None else "-"
        lines.append(
            f"| {o['phase']} | `{o['flight_id']}` | {o['t']:.2f} | {o['dist']:.2f} | "
            f"{o['ty']:+.2f} | {dty} | {o['reason']} | {o.get('frame_file','-')} ({o.get('evidence_kind','?')}) |"
        )
    lines += ["", "### What the detector saw", ""]
    for note in autopsy:
        lines.append(f"- {note}")
    lines += ["", ""]
    report_path.write_text(head + "\n".join(lines) + "\n" + tail, encoding="utf-8")
    print(f"Updated {len(outliers)} outliers; wrote report autopsy", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())