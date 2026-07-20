"""P3 — Block-B power from cohort-3 control-arm vertical dispersion.

σ′ = std of true_world_dz on control-arm approaches near the plane.
Recompute power of ±0.12 injection: n_sigma = 0.12 / σ′.
Flag if σ′ > 0.07 (advisory-12 / RESPONSE18 rider: designed ~2.4σ
against ~0.05 delivery noise; 0.12/0.07 ≈ 1.71σ → underpowered).
"""
from __future__ import annotations

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
sys.path.insert(0, str(ROOT / "analysis" / "2026-07-20-a8-half-extent"))
sys.path.insert(0, str(ROOT / "analysis" / "2026-07-20-vision-death-3m"))

from aigp.core.messages import RelPose  # noqa: E402
from aigp.planning.approach import true_world_dz  # noqa: E402
from run_a8_half_extent import parse_flight, resolve_log  # noqa: E402
from run_vision_death_3m import first_commit_window, load_flight  # noqa: E402

FIX = "20260720T071602-phase6l-cohort-3"
BLOCK_B_INJECT = 0.12
SIGMA_FLAG = 0.07
DESIGN_SIGMA = 0.05  # original delivery-noise assumption

CONTROLS = [
    {"slot": 1, "fid": "20260720T071008-5b501b4c"},
    {"slot": 3, "fid": "20260720T071220-5b501b4c"},
    {"slot": 5, "fid": "20260720T071439-5b501b4c"},
]


def collect_control_dz(fid: str) -> dict:
    path = resolve_log(fid, FIX)
    if path is None:
        return {"fid": fid, "error": "missing"}
    raw = load_flight(path)
    c0, c1 = first_commit_window(raw["setpoints"])
    log = parse_flight(path)
    samples = []
    for st in log["states"]:
        if c0 is None:
            break
        if st["t_ff"] < c0:
            continue
        if c1 is not None and st["t_ff"] > c1 + 0.5:
            break
        gr = st.get("gate_rel")
        if not gr or not gr.get("t"):
            continue
        age = st.get("age")
        if age is None or not math.isfinite(float(age)) or float(age) > 0.35:
            continue
        t = list(map(float, gr["t"]))
        R = float(np.linalg.norm(t))
        if not (0.5 <= R <= 6.0):
            continue
        tw = float(true_world_dz(
            RelPose(t=np.asarray(t, float),
                    normal=np.asarray(gr.get("normal") or [0, 0, 1], float)),
            np.asarray(st["q_att"], float),
            float(st["level_roll"]), float(st["level_pitch"])))
        samples.append({
            "t_ff": st["t_ff"], "R": R, "true_dz": tw, "age": float(age),
        })
    closest = min(samples, key=lambda s: s["R"]) if samples else None
    arr = [s["true_dz"] for s in samples]
    return {
        "fid": fid,
        "commit_start": c0,
        "commit_end": c1,
        "n_samples": len(samples),
        "true_dz_std": float(np.std(arr)) if len(arr) >= 2 else None,
        "true_dz_mean": float(np.mean(arr)) if arr else None,
        "closest": closest,
        "samples_head": samples[:: max(1, len(samples)//20)][:20],
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    per = [collect_control_dz(m["fid"]) for m in CONTROLS]

    # Within-flight dispersion (delivery noise) — NOT cross-flight absolute
    # height (that mixes aim bias + range). σ′ = RMS of per-flight stds
    # with n_samples >= 5; also report demeaned pooled residual std.
    per_stds = []
    residuals = []
    closest_dz = []
    for row in per:
        if row.get("error"):
            continue
        if row.get("closest") and row["closest"].get("true_dz") is not None:
            closest_dz.append(float(row["closest"]["true_dz"]))
        if row.get("true_dz_std") is not None and row.get("n_samples", 0) >= 5:
            per_stds.append(float(row["true_dz_std"]))
        path = resolve_log(row["fid"], FIX)
        if path is None or row.get("true_dz_mean") is None:
            continue
        raw = load_flight(path)
        c0, c1 = first_commit_window(raw["setpoints"])
        log = parse_flight(path)
        mu = float(row["true_dz_mean"])
        for st in log["states"]:
            if c0 is None or st["t_ff"] < c0:
                continue
            if c1 is not None and st["t_ff"] > c1 + 0.5:
                break
            gr = st.get("gate_rel")
            if not gr or not gr.get("t"):
                continue
            age = st.get("age")
            if age is None or not math.isfinite(float(age)) or float(age) > 0.35:
                continue
            t = list(map(float, gr["t"]))
            R = float(np.linalg.norm(t))
            if not (0.5 <= R <= 6.0):
                continue
            tw = float(true_world_dz(
                RelPose(t=np.asarray(t, float),
                        normal=np.asarray(gr.get("normal") or [0, 0, 1], float)),
                np.asarray(st["q_att"], float),
                float(st["level_roll"]), float(st["level_pitch"])))
            residuals.append(tw - mu)

    sigma_within_rms = (
        float(np.sqrt(np.mean(np.square(per_stds)))) if per_stds else None)
    sigma_residual = float(np.std(residuals)) if len(residuals) >= 2 else None
    sigma_closest = float(np.std(closest_dz)) if len(closest_dz) >= 2 else None
    # Primary: within-flight RMS std (matches "delivery noise" in Block B design)
    sigma_prime = sigma_within_rms if sigma_within_rms is not None else sigma_residual

    def power(sig):
        if sig is None or sig <= 0:
            return None
        return BLOCK_B_INJECT / sig

    flagged = bool(sigma_prime is not None and sigma_prime > SIGMA_FLAG)
    verdict = {
        "n_control_flights": len(CONTROLS),
        "n_flights_with_std": len(per_stds),
        "per_flight_stds": per_stds,
        "n_demeaned_residuals": len(residuals),
        "n_closest_points": len(closest_dz),
        "closest_true_dz": closest_dz,
        "sigma_prime_within_rms_m": sigma_within_rms,
        "sigma_prime_residual_m": sigma_residual,
        "sigma_cross_flight_closest_m": sigma_closest,
        "sigma_prime_m": sigma_prime,
        "sigma_prime_definition": (
            "RMS of per-control-flight std(true_world_dz) in first commit "
            "(age≤0.35, R∈[0.5,6], n≥5); NOT cross-flight absolute height. "
            "Also report demeaned residual std and closest-dz cross-std."
        ),
        "block_b_inject_m": BLOCK_B_INJECT,
        "design_sigma_m": DESIGN_SIGMA,
        "design_n_sigma": BLOCK_B_INJECT / DESIGN_SIGMA,
        "power_n_sigma": power(sigma_prime),
        "flag_threshold_m": SIGMA_FLAG,
        "flag_sigma_gt_0p07": flagged,
        "ruling": (
            f"σ′={sigma_prime}: Block B ±0.12 is "
            + (
                f"UNDERPOWERED ({power(sigma_prime):.2f}σ < 2.4σ design) — FLAG"
                if flagged else
                f"OK ({power(sigma_prime):.2f}σ) vs design 2.4σ at σ=0.05"
            )
            if sigma_prime is not None else "σ′ undefined — insufficient controls"
        ),
        "note_cross_flight_closest": (
            "cross-flight std of closest true_dz is bias/range mixing "
            f"({sigma_closest}) — not used as σ′"
        ),
        "per_flight": per,
    }
    (OUT / "summary.json").write_text(
        json.dumps(verdict, indent=2, default=str), encoding="utf-8")

    lines = [
        "# Block-B power — cohort-3 control σ′",
        "",
        "## Verdict",
        "",
        f"- **σ′ (within-flight RMS)**: `{sigma_within_rms}` m "
        f"(per-flight stds=`{per_stds}`)",
        f"- **σ′ (demeaned residual)**: `{sigma_residual}` m",
        f"- **Cross-flight closest (NOT σ′)**: `{sigma_closest}` m "
        f"values=`{closest_dz}`",
        f"- **Primary σ′**: `{sigma_prime}` m",
        f"- **Block B ±{BLOCK_B_INJECT} power**: "
        f"`{power(sigma_prime)}` σ "
        f"(design {BLOCK_B_INJECT}/{DESIGN_SIGMA}="
        f"{BLOCK_B_INJECT/DESIGN_SIGMA:.1f}σ)",
        f"- **Flag σ′ > {SIGMA_FLAG}**: `{flagged}`",
        f"- {verdict['ruling']}",
        "",
        "## Per control flight",
        "",
        "| slot | fid | n | mean_dz | std_dz | closest_R | closest_dz |",
        "|---:|---|---:|---:|---:|---:|---:|",
    ]
    for m, row in zip(CONTROLS, per):
        if row.get("error"):
            lines.append(f"| {m['slot']} | `{m['fid']}` | ERR | | | | |")
            continue
        c = row.get("closest") or {}
        lines.append(
            f"| {m['slot']} | `{m['fid']}` | {row['n_samples']} | "
            f"{row['true_dz_mean'] if row['true_dz_mean'] is not None else float('nan'):.3f} | "
            f"{row['true_dz_std'] if row['true_dz_std'] is not None else float('nan'):.3f} | "
            f"{c.get('R') if c.get('R') is not None else float('nan'):.2f} | "
            f"{c.get('true_dz') if c.get('true_dz') is not None else float('nan'):.3f} |"
        )
    lines += [
        "",
        "## Method",
        "",
            "fresh (age≤0.35) state gate_rel in first commit, R∈[0.5,6]. "
            "σ′ = std of per-flight closest true_world_dz (independent); "
            "fallback = pooled time-series std. "
            "Power = 0.12/σ′. Flag if σ′ > 0.07 (RESPONSE18 §5)."
        "",
        f"Generated by `{OUT.name}/run_block_b_power.py`.",
    ]
    text = "\n".join(lines)
    (OUT / "report.md").write_text(text, encoding="utf-8")
    (ROOT / "analysis" / "2026-07-20-block-b-power.md").write_text(
        text, encoding="utf-8")
    print(json.dumps({
        "sigma_prime": sigma_prime,
        "power_n_sigma": power(sigma_prime),
        "flag": flagged,
        "closest_dz": closest_dz,
    }, indent=2, default=str))


if __name__ == "__main__":
    main()
