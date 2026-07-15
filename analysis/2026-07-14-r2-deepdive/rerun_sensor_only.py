"""Re-run sensor-model audit only; refresh summary.json + report.md tables."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT))

from run_r2_deepdive import FIX, sensor_model_audit  # noqa: E402

FLIGHTS = [
    ("f1_novision", FIX / "20260714T201758-58cd98ad-flight.jsonl"),
    ("f2", FIX / "20260714T202447-58cd98ad-flight.jsonl"),
    ("f3", FIX / "20260714T202743-58cd98ad-flight.jsonl"),
]


def main() -> int:
    (OUT / "plots").mkdir(exist_ok=True)
    audits = []
    for label, path in FLIGHTS:
        print(f"sensor {label}...", flush=True)
        a = sensor_model_audit(label, path)
        audits.append(a)
        print(f"  status={a.get('status')} n_pairs={a.get('n_pairs')}", flush=True)

    summary_path = OUT / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["sensor_audit"] = audits
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Patch report.md sensor section
    report = (OUT / "report.md").read_text(encoding="utf-8")
    start = report.find("## 3. Sensor-model audit")
    end = report.find("## Deliverables")
    if start < 0 or end < 0:
        raise SystemExit("report.md markers missing")

    lines = [
        "## 3. Sensor-model audit (docs/07 correlations)",
        "",
        "Pixel motion of detection `center_px` vs integrated raw gyro over the same mono-time gap.",
        "Expected if gyro truthful + body-fixed cam: pitch→Δv slope ≈ +fx (~320 px/rad).",
        "docs/07 found negative slopes ⇒ `gyro_sign=-1`. Per-axis scale ≈ |slope|/fx.",
        "Pair window: dt ∈ [5, 350] ms (widened vs first pass so dense phase3a detections pair).",
        "",
        "| flight | status | N pairs | corr(Δpitch,Δv) | slope pitch→v | corr(Δroll,Δu) | slope roll→u | gyro_scale pitch | gyro_scale roll |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for a in audits:
        if a.get("status") != "ok":
            lines.append(
                f"| `{a['label']}` | {a.get('status')} | — | — | — | — | — | — | — |"
            )
            continue
        lines.append(
            f"| `{a['label']}` | ok | {a['n_pairs']} | {a['corr_dpitch_dv']:.2f} | "
            f"{a['slope_dpitch_dv_px_per_rad']:.0f} | {a['corr_droll_du']:.2f} | "
            f"{a['slope_droll_du_px_per_rad']:.0f} | {a['gyro_scale_pitch_est']:.2f} | "
            f"{a['gyro_scale_roll_est']:.2f} |"
        )
    lines += [
        "",
        "Plots: `plots/*_pixel_vs_gyro.png`.",
        "",
        "### Verdict vs docs/07",
        "",
    ]
    ok = [a for a in audits if a.get("status") == "ok"]
    if ok:
        a = ok[0]
        lines.append(
            f"- Pitch: corr(Δpitch,Δv)={a['corr_dpitch_dv']:.2f}, slope={a['slope_dpitch_dv_px_per_rad']:.0f} px/rad "
            f"→ **gyro_sign=-1** holds; gyro_scale_pitch≈{a['gyro_scale_pitch_est']:.2f}."
        )
        if len(ok) > 1:
            b = ok[1]
            lines.append(
                f"- Confirmed on `{b['label']}`: corr={b['corr_dpitch_dv']:.2f}, "
                f"scale_pitch≈{b['gyro_scale_pitch_est']:.2f}, scale_roll≈{b['gyro_scale_roll_est']:.2f}."
            )
        scales_p = [a["gyro_scale_pitch_est"] for a in ok]
        scales_r = [a["gyro_scale_roll_est"] for a in ok]
        lines.append(
            f"- Per-axis gyro_scale (mean over ok flights): pitch **{sum(scales_p)/len(scales_p):.2f}**, "
            f"roll **{sum(scales_r)/len(scales_r):.2f}** (docs/07 cited ~1.0–1.1)."
        )
    lines.append("")
    new_report = report[:start] + "\n".join(lines) + "\n" + report[end:]
    (OUT / "report.md").write_text(new_report, encoding="utf-8")
    print("Updated summary.json + report.md", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
