"""Phase 5 DATA ANALYST: close-range blindness + true gate size."""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(OUT))

from aigp.core.messages import CameraFrame  # noqa: E402
from aigp.core.params import ParamSet  # noqa: E402
from aigp.main import apply_patches  # noqa: E402
from aigp.perception.gate_detector_hsv import HsvGateDetector  # noqa: E402

from reflight_ext import (  # noqa: E402
    BINS,
    annotate_frame,
    discover_pairs,
    load_frames,
    red_mask,
    replay_source_v2,
)

GATE_W = 1.6
GATE_H = 1.6
HALF_W = GATE_W / 2.0
HALF_H = GATE_H / 2.0


def closest_state_miss(log_path: Path) -> dict | None:
    t0 = None
    best = None
    with log_path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec["topic"] != "state":
                continue
            mono = int(rec["mono_ns"])
            if t0 is None:
                t0 = mono
            gr = rec["data"].get("gate_rel")
            if not gr or gr.get("t") is None:
                continue
            tx, ty, tz = (float(x) for x in gr["t"])
            dist = math.sqrt(tx * tx + ty * ty + tz * tz)
            age = float(rec["data"].get("gate_rel_age_s") or 0.0)
            if best is None or dist < best["dist"]:
                best = {
                    "t": (mono - t0) / 1e9,
                    "dist": dist,
                    "lat": tx,
                    "vert": ty,
                    "fwd": tz,
                    "age": age,
                }
    return best


def gate_size_study() -> dict:
    """Bound real opening from PASS + clips + zero-clip near-misses."""
    rows = []
    for result_path in sorted((ROOT / "fixtures").glob("**/*-result.json")):
        if "phase3" not in str(result_path) and "phase4" not in str(result_path) and "phase5" not in str(result_path):
            # still allow phase3 primarily
            if "phase" not in result_path.parent.name:
                continue
        res = json.loads(result_path.read_text(encoding="utf-8"))
        fid = res.get("flight_id") or result_path.name.replace("-result.json", "")
        log = result_path.with_name(f"{fid}-flight.jsonl")
        if not log.exists():
            continue
        miss = closest_state_miss(log)
        gp = int(res.get("gates_passed") or 0)
        gc = int(res.get("gate_clips") or 0)
        eh = int(res.get("env_hits") or 0)
        label = "other"
        if gp >= 1:
            label = "PASS"
        elif gc > 0:
            label = "CLIP"
        elif miss and miss["dist"] < 2.0 and gc == 0 and gp == 0:
            label = "ZERO_CLIP_NEAR_MISS"
        rows.append(
            {
                "flight_id": fid,
                "fixture": result_path.parent.name,
                "label": label,
                "gates_passed": gp,
                "gate_clips": gc,
                "env_hits": eh,
                "abort": res.get("abort_reason"),
                "closest": miss,
            }
        )

    # Nominal model opening
    model = {"width_m": GATE_W, "height_m": GATE_H, "half_w": HALF_W, "half_h": HALF_H}

    passes = [r for r in rows if r["label"] == "PASS" and r["closest"]]
    clips = [r for r in rows if r["label"] == "CLIP" and r["closest"]]
    near = [r for r in rows if r["label"] == "ZERO_CLIP_NEAR_MISS" and r["closest"]]

    # Empirical bounds: PASS samples are INSIDE; CLIP closest-state may be
    # inside the model opening (state fiction) — those force opening ≤ that
    # radius OR prove state error.
    def radii(rs):
        out = []
        for r in rs:
            m = r["closest"]
            out.append(
                {
                    "flight_id": r["flight_id"],
                    "lat": m["lat"],
                    "vert": m["vert"],
                    "radial": math.sqrt(m["lat"] ** 2 + m["vert"] ** 2),
                    "dist": m["dist"],
                    "age": m["age"],
                    "gate_clips": r["gate_clips"],
                }
            )
        return out

    pass_pts = radii(passes)
    clip_pts = radii(clips)
    near_pts = radii(near)

    # Inside model opening?
    def inside_model(p):
        return abs(p["lat"]) < HALF_W and abs(p["vert"]) < HALF_H

    clip_inside_model = [p for p in clip_pts if inside_model(p)]
    near_inside_model = [p for p in near_pts if inside_model(p)]

    verdict = {
        "model": model,
        "pass_pts": pass_pts,
        "clip_pts": clip_pts,
        "near_miss_pts": near_pts,
        "n_clip_state_inside_model": len(clip_inside_model),
        "n_near_state_inside_model": len(near_inside_model),
        "interpretation": [],
    }
    if pass_pts:
        p = pass_pts[0]
        verdict["interpretation"].append(
            f"PASS at state (lat={p['lat']:+.3f}, vert={p['vert']:+.3f}) is deep inside "
            f"the ±{HALF_W:.1f}m model half-opening — consistent with width_m=1.6 if state≈truth."
        )
    if clip_inside_model:
        verdict["interpretation"].append(
            f"{len(clip_inside_model)} CLIP flight(s) have closest STATE inside the model "
            f"opening (±{HALF_W:.1f}m) yet recorded gate_clips>0 — either the true scoring "
            "volume is smaller than 1.6×1.6, or (more likely given Phase 5) the dead-reckoned "
            "state is fiction at the bar (blind stretch)."
        )
    if near_inside_model:
        verdict["interpretation"].append(
            f"{len(near_inside_model)} zero-clip near-misses also sit inside the model "
            "opening in STATE — same fiction/size ambiguity; clips are the harder bound."
        )
    # Conservative physical upper bound from PASS alone: opening ≥ max(|lat|,|vert|) of pass
    if pass_pts:
        p = pass_pts[0]
        verdict["lower_bound_half_from_pass_m"] = max(abs(p["lat"]), abs(p["vert"]))
    # If clips have state outside model — that bounds opening from above poorly
    # because state may be wrong. Report radial of clips anyway.
    if clip_pts:
        verdict["clip_radial_median_m"] = float(np.median([p["radial"] for p in clip_pts]))
        verdict["clip_vert_abs_median_m"] = float(np.median([abs(p["vert"]) for p in clip_pts]))

    verdict["all_rows"] = [
        {
            "flight_id": r["flight_id"],
            "fixture": r["fixture"],
            "label": r["label"],
            "gates_passed": r["gates_passed"],
            "gate_clips": r["gate_clips"],
            "closest": r["closest"],
            "abort": r["abort"],
        }
        for r in rows
        if r["label"] in ("PASS", "CLIP", "ZERO_CLIP_NEAR_MISS")
    ]
    return verdict


def select_annotation_targets(rows, n_total=36):
    """Prefer close-bin misses with diverse reasons; include some hits."""
    close_bins = {"5-8m", "3-5m", "2-3m", "<2m"}
    by_key = defaultdict(list)
    for r in rows:
        if r.bin_name not in close_bins:
            continue
        key = (r.bin_name, r.reason if not r.detected else "ok")
        by_key[key].append(r)

    selected = []
    # Round-robin across keys
    keys = sorted(by_key.keys(), key=lambda k: (k[0], k[1]))
    idx = {k: 0 for k in keys}
    while len(selected) < n_total and keys:
        progressed = False
        for k in keys:
            lst = by_key[k]
            i = idx[k]
            if i < len(lst):
                # spread within source: take every Nth
                selected.append(lst[i])
                idx[k] = i + max(1, len(lst) // 8)
                progressed = True
                if len(selected) >= n_total:
                    break
        if not progressed:
            break
    return selected


def export_annotations(targets, params: ParamSet) -> list[dict]:
    detector = HsvGateDetector(params)
    # group by source
    by_src = defaultdict(list)
    for r in targets:
        by_src[r.source].append(r)

    pairs = {sid: (sl, lg) for sid, sl, lg in discover_pairs()}
    meta = []
    out_dir = OUT / "annotated_frames"
    out_dir.mkdir(parents=True, exist_ok=True)
    # clear old
    for old in out_dir.glob("*.jpg"):
        old.unlink()

    n_saved = 0
    for sid, rows in by_src.items():
        if sid not in pairs:
            continue
        sl, _lg = pairs[sid]
        # Load frames once; index by frame_id (may collide — also match t)
        frames = load_frames(sl)
        by_fid = {fid: (mono, sim, img) for mono, fid, sim, img in frames}
        want_t = {r.frame_id: r for r in rows}
        for r in rows:
            pack = by_fid.get(r.frame_id)
            if pack is None:
                # nearest by scanning — skip if missing
                continue
            _mono, sim_ns, img = pack
            det = detector.detect(CameraFrame(frame_id=r.frame_id, ts_ns=sim_ns, image=img))
            corners = det.corners_px if det is not None else None
            vis = annotate_frame(img, r, det_corners=corners)
            fname = (
                f"{n_saved:02d}_{r.bin_name.replace('<', 'lt').replace('>', 'gt')}_"
                f"{r.reason}_{sid.split('/')[-1][:24]}_f{r.frame_id}.jpg"
            )
            fname = fname.replace(" ", "_")
            cv2.imwrite(str(out_dir / fname), vis, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
            meta.append({"file": fname, **asdict(r)})
            n_saved += 1
    return meta


def plot_bin_bars(agg_by_bin: dict):
    names = [b[0] for b in BINS]
    fixes = [agg_by_bin.get(n, {}).get("fixes", 0) for n in names]
    misses = [agg_by_bin.get(n, {}).get("misses", 0) for n in names]
    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(names))
    ax.bar(x - 0.2, fixes, 0.4, label="fixes", color="#2ca02c")
    ax.bar(x + 0.2, misses, 0.4, label="misses", color="#d62728")
    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.set_ylabel("frames (binned by preceding fix range)")
    ax.set_title("Detector fixes vs misses by preceding PnP range")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.3)
    (OUT / "plots").mkdir(exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT / "plots" / "fixes_by_preceding_range.png", dpi=140)
    plt.close(fig)

    # reason stacked for misses in close bins
    reasons = Counter()
    reason_by_bin = defaultdict(Counter)
    for n in names:
        for rsn, c in agg_by_bin.get(n, {}).get("reasons", {}).items():
            reasons[rsn] += c
            reason_by_bin[n][rsn] += c
    if reasons:
        top = [r for r, _ in reasons.most_common(8)]
        fig, ax = plt.subplots(figsize=(9, 4))
        bottom = np.zeros(len(names))
        for rsn in top:
            vals = np.array([reason_by_bin[n][rsn] for n in names], float)
            ax.bar(names, vals, bottom=bottom, label=rsn)
            bottom += vals
        ax.set_ylabel("miss frames")
        ax.set_title("Miss reasons by preceding-range bin")
        ax.legend(fontsize=7, loc="upper right")
        fig.tight_layout()
        fig.savefig(OUT / "plots" / "miss_reasons_by_bin.png", dpi=140)
        plt.close(fig)


def plot_gate_size(gs: dict):
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.add_patch(
        plt.Rectangle((-HALF_W, -HALF_H), GATE_W, GATE_H, fill=False, ls="--", color="gray", label="model ±0.8m")
    )
    ax.axhline(0, color="k", lw=0.6)
    ax.axvline(0, color="k", lw=0.6)
    for p in gs.get("pass_pts") or []:
        ax.scatter([p["lat"]], [p["vert"]], c="lime", s=200, marker="*", edgecolors="k", zorder=5, label="PASS")
    for i, p in enumerate(gs.get("clip_pts") or []):
        ax.scatter(
            [p["lat"]],
            [p["vert"]],
            c="red",
            s=80,
            marker="x",
            zorder=4,
            label="CLIP" if i == 0 else None,
        )
        ax.annotate(p["flight_id"][-6:], (p["lat"], p["vert"]), fontsize=6, color="red")
    for i, p in enumerate(gs.get("near_miss_pts") or []):
        ax.scatter(
            [p["lat"]],
            [p["vert"]],
            c="orange",
            s=40,
            marker="o",
            alpha=0.7,
            zorder=3,
            label="zero-clip near" if i == 0 else None,
        )
    ax.set_xlabel("lateral (m) [+ LEFT]")
    ax.set_ylabel("vertical (m) [+ HIGH]")
    ax.set_title("Scoring volume: STATE closest vs model gate 1.6×1.6")
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "plots" / "gate_size_bounds.png", dpi=140)
    plt.close(fig)


def write_report(summaries, agg, ann_meta, gs, sources_close):
    lines = [
        "# Phase 5 — close-range perception + true gate size",
        "",
        "AGENTS.md DATA ANALYST Phase 5 (HEAD ≥ `9fe3702`).",
        "Harness: `reflight_ext.py` (extends `scripts/reflight.py`, fixes "
        "`read_recording` unpack) + `run_phase5_study.py`.",
        "",
        "## 1. Why detection stops below ~5 m",
        "",
        "Frames are binned by the **nearest preceding PnP fix range** "
        "(5–8 / 3–5 / 2–3 / <2 m). A miss in the 3–5 m bin means: we had a "
        "fix near that range, then subsequent frames produced no detection.",
        "",
        "### Aggregate (all R2 sources)",
        "",
        "| preceding bin | frames | fixes | misses | fix rate | top miss reasons |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for name, _, _ in BINS:
        b = agg.get(name, {})
        fr = b.get("frames", 0)
        fx = b.get("fixes", 0)
        ms = b.get("misses", 0)
        rate = 100.0 * fx / fr if fr else 0.0
        reasons = b.get("reasons") or {}
        top = ", ".join(f"{k}:{v}" for k, v in sorted(reasons.items(), key=lambda kv: -kv[1])[:4]) or "—"
        lines.append(f"| {name} | {fr} | {fx} | {ms} | {rate:.1f}% | {top} |")

    lines += [
        "",
        "![fixes by range](plots/fixes_by_preceding_range.png)",
        "",
        "![miss reasons](plots/miss_reasons_by_bin.png)",
        "",
        "### Minimum fix range per source (detector produced a PnP)",
        "",
        "| source | frames | fixes | min fix range (m) |",
        "|---|---:|---:|---:|",
    ]
    for s in sorted(summaries, key=lambda x: (x.min_fix_range is None, x.min_fix_range or 99)):
        mn = f"{s.min_fix_range:.2f}" if s.min_fix_range is not None else "—"
        lines.append(f"| `{s.source}` | {s.n_frames} | {s.n_fixes} | {mn} |")

    lines += [
        "",
        "### Characterization",
        "",
    ]
    # Auto narrative from agg
    close = agg.get("3-5m", {})
    closer = agg.get("2-3m", {})
    closest = agg.get("<2m", {})
    r35 = close.get("reasons") or {}
    r23 = closer.get("reasons") or {}
    r2 = closest.get("reasons") or {}

    def dominant(reasons: dict) -> str:
        if not reasons:
            return "n/a"
        return max(reasons.items(), key=lambda kv: kv[1])[0]

    lines.append(
        f"- In the **3–5 m** preceding bin, dominant miss reason = **`{dominant(r35)}`** "
        f"(counts: {dict(sorted(r35.items(), key=lambda kv: -kv[1]))})."
    )
    lines.append(
        f"- In **2–3 m**: dominant = **`{dominant(r23)}`** ({dict(sorted(r23.items(), key=lambda kv: -kv[1]))})."
    )
    lines.append(
        f"- In **<2 m**: dominant = **`{dominant(r2)}`** ({dict(sorted(r2.items(), key=lambda kv: -kv[1]))})."
    )
    lines += [
        "",
        "Reason legend:",
        "- `edge_clip` — red mass touches frame border (ring leaving FOV)",
        "- `too_large` — red blob exceeds `max_area_frac` (ring fills frame)",
        "- `partial_ring` — red present but no convex 4-gon (broken / occluded ring)",
        "- `motion_blur` — low Laplacian variance with red present",
        "- `exposure_dark` / `exposure_bright` — mean V extreme",
        "- `no_red` — almost no red HSV mass",
        "- `area_reject` — quads exist but fail rectangularity/confidence gates",
        "",
        f"Annotated frames: **{len(ann_meta)}** under `annotated_frames/`.",
        "",
        "Sources with any preceding-bin activity below 5 m "
        f"(close-range material): **{len(sources_close)}**.",
        "",
        "## 2. True gate size / scoring volume vs `width_m=1.6`",
        "",
        f"Model: `{GATE_W}` × `{GATE_H}` m → half-opening **±{HALF_W:.1f} m** "
        "lateral/vertical (opening center).",
        "",
        "![gate size](plots/gate_size_bounds.png)",
        "",
        "### PASS (ground-truth inside)",
        "",
    ]
    for p in gs.get("pass_pts") or []:
        lines.append(
            f"- `{p['flight_id']}`: state lat={p['lat']:+.3f}, vert={p['vert']:+.3f}, "
            f"radial={p['radial']:.3f} m, dist={p['dist']:.3f} m, age={p['age']:.2f}s"
        )
    lines += ["", "### CLIP flights (gate_clips>0)", ""]
    if not gs.get("clip_pts"):
        lines.append("- (none)")
    for p in gs.get("clip_pts") or []:
        inside = abs(p["lat"]) < HALF_W and abs(p["vert"]) < HALF_H
        lines.append(
            f"- `{p['flight_id']}` gc={p['gate_clips']}: lat={p['lat']:+.3f}, "
            f"vert={p['vert']:+.3f}, radial={p['radial']:.3f} m "
            f"{'**STATE inside model opening**' if inside else '(state outside model)'}"
        )
    lines += ["", "### Zero-clip near-misses (closest STATE <2 m, gc=0, gp=0)", ""]
    # limit list
    for p in (gs.get("near_miss_pts") or [])[:12]:
        inside = abs(p["lat"]) < HALF_W and abs(p["vert"]) < HALF_H
        lines.append(
            f"- `{p['flight_id']}`: lat={p['lat']:+.3f}, vert={p['vert']:+.3f}, "
            f"dist={p['dist']:.2f} m {'(inside model)' if inside else ''}"
        )
    lines += ["", "### Reconciliation", ""]
    for note in gs.get("interpretation") or []:
        lines.append(f"- {note}")
    lines += [
        "",
        "**Verdict on `perception.gate.width_m=1.6`:**",
        "",
        "- As a **PnP model size**, 1.6 m remains the working assumption; the PASS "
        "at (+0.006,+0.100) does not contradict it.",
        "- As a **scoring-volume / planner tolerance**, STATE at clips/near-misses "
        "often lies well inside ±0.8 m while the aircraft still clips or misses — "
        "so **do not treat 1.6 m as a trusted pass corridor in dead-reckoned state**. "
        "The Phase 5 finding (blind below ~5 m) explains this better than a much "
        "smaller physical gate: the opening may still be ~1.6 m, but the estimator "
        "is guessing for most of the final approach.",
        "- Practical bound: PASS proves half-opening ≳ 0.10 m; clips-with-centered-STATE "
        "do **not** prove half-opening ≪ 0.8 m until close-range vision is restored.",
        "",
        "## Deliverables",
        "",
        "- `report.md`, `summary.json`, `frames.csv`",
        "- `annotated_frames/` (≥30)",
        "- `plots/fixes_by_preceding_range.png`, `miss_reasons_by_bin.png`, `gate_size_bounds.png`",
        "- `reflight_ext.py` — reusable offline replay (correct mono unpack)",
        "",
    ]
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "plots").mkdir(exist_ok=True)
    params = apply_patches(ParamSet.load(str(ROOT / "config" / "params_default.json")), [])

    pairs = discover_pairs()
    print(f"sources: {len(pairs)}", flush=True)

    all_rows = []
    summaries = []
    for sid, sl, lg in pairs:
        # Cap huge local vision to keep runtime sane but cover close range
        max_f = None
        if "local_pass" in sid:
            max_f = 8000  # ~enough for pass→collision window sampling
        print(f"replay {sid} ...", flush=True)
        rows, summary = replay_source_v2(sl, lg, params, sid, max_frames=max_f)
        summaries.append(summary)
        all_rows.extend(rows)
        print(
            f"  frames={summary.n_frames} fixes={summary.n_fixes} "
            f"min_range={summary.min_fix_range}",
            flush=True,
        )

    # Aggregate bins
    agg = defaultdict(lambda: {"frames": 0, "fixes": 0, "misses": 0, "reasons": Counter()})
    for s in summaries:
        for bname, b in s.by_bin.items():
            agg[bname]["frames"] += b["frames"]
            agg[bname]["fixes"] += b["fixes"]
            agg[bname]["misses"] += b["misses"]
            for rsn, c in b.get("reasons", {}).items():
                agg[bname]["reasons"][rsn] += c
    # convert counters
    agg_out = {
        k: {
            "frames": v["frames"],
            "fixes": v["fixes"],
            "misses": v["misses"],
            "reasons": dict(v["reasons"]),
        }
        for k, v in agg.items()
    }

    plot_bin_bars(agg_out)

    # Annotations — prefer close bins; pad with 5-8m if needed for ≥30
    targets = select_annotation_targets(all_rows, n_total=40)
    if len(targets) < 30:
        have = {(r.source, r.frame_id) for r in targets}
        for r in all_rows:
            if r.bin_name == "5-8m" and (r.source, r.frame_id) not in have:
                targets.append(r)
                have.add((r.source, r.frame_id))
            if len(targets) >= 36:
                break
    print(f"annotating {len(targets)} frames ...", flush=True)
    ann_meta = export_annotations(targets, params)
    print(f"saved {len(ann_meta)} annotated frames", flush=True)

    gs = gate_size_study()
    plot_gate_size(gs)

    sources_close = [
        s.source
        for s in summaries
        if any(s.by_bin.get(b, {}).get("frames", 0) > 0 for b in ("3-5m", "2-3m", "<2m"))
    ]

    # CSV of all close-bin rows (not every far frame — keep file smaller)
    with (OUT / "frames.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "source",
                "t_s",
                "frame_id",
                "preceding_range_m",
                "bin_name",
                "detected",
                "det_range_m",
                "reason",
                "red_frac",
                "lap_var",
                "mean_v",
                "touches_edge",
                "n_quads",
            ]
        )
        for r in all_rows:
            if r.bin_name in ("5-8m", "3-5m", "2-3m", "<2m") or (r.det_range_m and r.det_range_m < 8):
                w.writerow(
                    [
                        r.source,
                        r.t_s,
                        r.frame_id,
                        r.preceding_range_m,
                        r.bin_name,
                        r.detected,
                        r.det_range_m,
                        r.reason,
                        r.red_frac,
                        r.lap_var,
                        r.mean_v,
                        r.touches_edge,
                        r.n_quads,
                    ]
                )

    write_report(summaries, agg_out, ann_meta, gs, sources_close)

    summary = {
        "n_sources": len(pairs),
        "n_frames_total": sum(s.n_frames for s in summaries),
        "n_fixes_total": sum(s.n_fixes for s in summaries),
        "agg_by_bin": agg_out,
        "min_fix_ranges": {s.source: s.min_fix_range for s in summaries},
        "n_annotated": len(ann_meta),
        "sources_with_sub5m_bins": sources_close,
        "gate_size": {
            k: gs[k]
            for k in gs
            if k != "all_rows"
        },
        "gate_size_rows": gs.get("all_rows"),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (OUT / "gate_size.json").write_text(json.dumps(gs, indent=2), encoding="utf-8")
    print("Done.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
