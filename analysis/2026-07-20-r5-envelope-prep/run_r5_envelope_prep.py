"""P3 — R5 empirical envelope prep (pre-registered for phase6j / cohort-2).

Per unique exposure in the LIVE arm:
  predicted_tail_miss = e_z - h_tail * v_z,  h_tail = min(tau, 0.45)
  vs observed true-axis crossing miss.
Containment of claimed envelope |e_x| + 2*sigma_x + 0.06.
Failures raise sigma_model — never the corridor.

phase6j has NOT landed as of this writing: the harness runs a WARM
prep on phase6i-R live-arm passes and leaves the COLD cohort empty
until those fixtures arrive.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
FLOWN_SRC = Path(r"C:\Users\tsion\Projects\eni_dcim\src")
sys.path.insert(0, str(FLOWN_SRC if FLOWN_SRC.exists() else ROOT / "src"))
sys.path.insert(0, str(ROOT / "src"))

from aigp.core.messages import RelPose, TerminalFeature  # noqa: E402
from aigp.planning.approach import true_world_dz  # noqa: E402
from aigp.planning.vertical_owner import TerminalOracle, terminal_observe  # noqa: E402
from aigp.planning.vertical_terminal import (  # noqa: E402
    crossing_error,
    crossing_sigma,
)

D_STAR = 0.8
GATE_W = 1.6
PITCH_CAL = -0.33
E_CLAMP = 0.45
H_TAIL_CAP = 0.45
SIGMA_E = 0.05
SIGMA_V = 0.10
CORRIDOR_PAD = 0.06

# Warm prep: phase6i-R live-arm counted passes (quarantine note: ambiguous
# TermStatus instrument on some; still usable for envelope residual).
WARM_LIVE = [
    {
        "fid": "20260719T200816-f170ead6",
        "cohort": "warm_phase6i_r",
        "log": Path(r"C:\Users\tsion\Projects\eni_dcim\logs\20260719T200816-f170ead6\flight.jsonl"),
        "alt": ROOT / "fixtures" / "20260719T204430-phase6i-r-rate-ab"
               / "20260719T200816-f170ead6-flight.jsonl",
    },
    {
        "fid": "20260719T201851-50f9dcc8",
        "cohort": "warm_phase6i_r",
        "log": Path(r"C:\Users\tsion\Projects\eni_dcim\logs\20260719T201851-50f9dcc8\flight.jsonl"),
        "alt": ROOT / "fixtures" / "20260719T204430-phase6i-r-rate-ab"
               / "20260719T201851-50f9dcc8-flight.jsonl",
    },
]
# Cold: phase6j — empty until fixtures land
COLD_GLOB = list((ROOT / "fixtures").glob("*phase6j*")) + list(
    Path(r"C:\Users\tsion\Projects\eni_dcim\fixtures").glob("*phase6j*")
    if Path(r"C:\Users\tsion\Projects\eni_dcim\fixtures").exists() else [])


def resolve(meta: dict) -> Path | None:
    if meta["log"].exists():
        return meta["log"]
    if meta.get("alt") and meta["alt"].exists():
        return meta["alt"]
    return None


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def takeoff_mono(rows: list[dict]) -> int:
    for r in rows:
        if r.get("topic") == "fsm":
            d = r["data"]
            if d.get("dst") == "TAKEOFF" or "GO" in str(d.get("reason", "")).upper():
                return int(r["mono_ns"])
    return int(rows[0]["mono_ns"])


def hud_pass_t(rows: list[dict], toff: int) -> float | None:
    prev = None
    for r in rows:
        if r.get("topic") != "race":
            continue
        idx = r["data"].get("active_gate_index")
        if idx is not None and prev is not None and idx > prev:
            return (int(r["mono_ns"]) - toff) / 1e9
        if idx is not None:
            prev = idx
    return None


def analyze(meta: dict) -> dict:
    path = resolve(meta)
    if path is None:
        return {"fid": meta["fid"], "cohort": meta["cohort"],
                "error": "log_not_found"}
    rows = load_jsonl(path)
    toff = takeoff_mono(rows)
    t_pass = hud_pass_t(rows, toff)
    if t_pass is None:
        return {"fid": meta["fid"], "cohort": meta["cohort"],
                "error": "no_hud_pass", "path": str(path)}

    # Observed true-axis crossing miss: state at pass, e_up = -true_world_dz
    obs_miss = None
    for r in rows:
        t_ff = (int(r["mono_ns"]) - toff) / 1e9
        if r.get("topic") != "state":
            continue
        if abs(t_ff - t_pass) > 0.15:
            continue
        d = r["data"]
        gr = d.get("gate_rel")
        if gr is None:
            continue
        tw = float(true_world_dz(
            RelPose(t=np.asarray(gr["t"], float),
                    normal=np.asarray(gr.get("normal") or [0, 0, 1], float)),
            np.asarray(d.get("q_att") or [1, 0, 0, 0], float),
            float(d.get("level_roll") or 0),
            float(d.get("level_pitch") or 0)))
        obs_miss = -tw  # +UP required displacement at crossing
        break

    # Replay oracle on commit ticks near final approach (t_pass-2 .. t_pass)
    oracle = TerminalOracle()
    exposures = []
    last_feat = None
    last_feat_t = None
    cur_state = None
    phase = None
    seen_ts = set()

    events = []
    for r in rows:
        topic = r.get("topic")
        if topic not in ("state", "feature", "setpoint"):
            continue
        t_ff = (int(r["mono_ns"]) - toff) / 1e9
        events.append((t_ff, topic, r["data"]))
    events.sort(key=lambda e: e[0])

    for t_ff, topic, d in events:
        if topic == "state":
            cur_state = d
            cur_state["_t_ff"] = t_ff
            continue
        if topic == "feature":
            last_feat = d
            last_feat_t = t_ff
            continue
        if topic != "setpoint":
            continue
        ph = d.get("phase")
        if phase == "commit" and ph != "commit":
            oracle.reset()
        phase = ph
        if ph != "commit" or cur_state is None:
            continue
        if t_ff < t_pass - 2.5 or t_ff > t_pass + 0.05:
            continue

        feat_age = (abs(t_ff - last_feat_t) if last_feat_t is not None else None)
        st_obj = SimpleNamespace(
            q_att=np.asarray(cur_state.get("q_att") or [1, 0, 0, 0], float),
            level_roll=float(cur_state.get("level_roll") or 0),
            level_pitch=float(cur_state.get("level_pitch") or 0),
            image_size=tuple(cur_state.get("image_size") or [640, 360]),
            gate_rel=None,
            gate_rel_age_s=float(cur_state.get("gate_rel_age_s") or 9)
            if math.isfinite(float(cur_state.get("gate_rel_age_s") or 9)) else 9.0,
            v_world=np.asarray(cur_state.get("v_world") or [0, 0, 0], float),
        )
        if cur_state.get("gate_rel"):
            st_obj.gate_rel = RelPose(
                t=np.asarray(cur_state["gate_rel"]["t"], float),
                normal=np.asarray(
                    cur_state["gate_rel"].get("normal") or [0, 0, 1], float))

        feat_obj = None
        if last_feat is not None:
            ts = int(last_feat.get("ts_ns") or 0)
            feat_obj = TerminalFeature(
                ts_ns=ts,
                y_top_px=float(last_feat["y_top_px"]),
                span_px=float(last_feat["span_px"]),
                center_x_px=float(last_feat["center_x_px"]),
                cert_status=str(last_feat.get("cert_status")),
                mode=str(last_feat.get("mode") or "BAR_FULL"),
            )

        e_meas = terminal_observe(
            oracle, st_obj, feat_obj, feat_age,
            d_star=D_STAR, gate_w=GATE_W,
            pitch_cal_rad=PITCH_CAL, e_z_clamp_m=E_CLAMP)
        if e_meas is None or feat_obj is None:
            continue
        ts_key = feat_obj.ts_ns
        if ts_key in seen_ts:
            continue
        seen_ts.add(ts_key)

        tz = float(st_obj.gate_rel.t[2]) if st_obj.gate_rel is not None else None
        if tz is None or tz <= 0.05:
            continue
        # speed proxy from setpoint
        vb = d.get("v_body") or [2.0, 0, 0]
        speed = max(float(np.linalg.norm(vb[:2])), 0.5)
        tau = tz / speed
        h_tail = min(tau, H_TAIL_CAP)
        vz = oracle.v_z_visual()
        if vz is None:
            vz = 0.0
        else:
            vz = float(vz) * oracle.rate_authority()
        e_x = crossing_error(e_meas, vz, h_tail)
        s_x = crossing_sigma(SIGMA_E, vz, SIGMA_V, h_tail)
        claimed = abs(e_x) + 2.0 * s_x + CORRIDOR_PAD
        # Residual vs observed crossing miss
        residual = None
        contained = None
        if obs_miss is not None:
            residual = float(e_x - obs_miss)  # prediction error of tail miss
            # Containment: observed miss inside claimed envelope around 0
            # i.e. |obs_miss| <= claimed  (envelope is about predicted miss;
            # also check |obs_miss - e_x| <= 2*s_x+pad as calibration form)
            contained = abs(obs_miss) <= claimed

        exposures.append({
            "t_ff": t_ff,
            "e_z": e_meas,
            "vz": vz,
            "tau": tau,
            "h_tail": h_tail,
            "e_x": e_x,
            "sigma_x": s_x,
            "claimed_envelope": claimed,
            "tz": tz,
            "R": float(np.linalg.norm(st_obj.gate_rel.t)),
            "obs_miss": obs_miss,
            "residual_ex_minus_obs": residual,
            "contained": contained,
            "small_envelope": claimed < 0.20,
        })

    contained_n = sum(1 for e in exposures if e["contained"] is True)
    scored = [e for e in exposures if e["contained"] is not None]
    small_miss = [e for e in scored
                  if e["contained"] is False and e["small_envelope"]]

    return {
        "fid": meta["fid"],
        "cohort": meta["cohort"],
        "path": str(path),
        "t_pass_ff": t_pass,
        "obs_crossing_miss_up": obs_miss,
        "n_unique_exposures": len(exposures),
        "n_scored": len(scored),
        "containment_rate": (
            contained_n / len(scored) if scored else None),
        "n_miss_with_small_envelope": len(small_miss),
        "exposures": exposures,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    phase6j_landed = len(COLD_GLOB) > 0
    warm = []
    for m in WARM_LIVE:
        print(f"warm {m['fid']}", flush=True)
        warm.append(analyze(m))

    cold = []
    # Auto-discover phase6j live-arm logs when present
    if phase6j_landed:
        for fx in COLD_GLOB:
            for log in fx.glob("*-flight.jsonl"):
                cold.append(analyze({
                    "fid": log.name.replace("-flight.jsonl", ""),
                    "cohort": "cold_phase6j",
                    "log": log,
                    "alt": None,
                }))

    def cohort_stats(rows, name):
        scored = []
        for r in rows:
            scored.extend([e for e in r.get("exposures") or []
                           if e.get("contained") is not None])
        if not scored:
            return {"cohort": name, "n": 0, "containment_rate": None,
                    "n_miss_small_env": 0}
        return {
            "cohort": name,
            "n": len(scored),
            "containment_rate": sum(1 for e in scored if e["contained"]) / len(scored),
            "n_miss_small_env": sum(
                1 for e in scored
                if (not e["contained"]) and e.get("small_envelope")),
            "median_claimed": float(np.median(
                [e["claimed_envelope"] for e in scored])),
            "median_abs_obs": float(np.median(
                [abs(e["obs_miss"]) for e in scored
                 if e.get("obs_miss") is not None])),
            "median_abs_ex": float(np.median(
                [abs(e["e_x"]) for e in scored])),
        }

    bundle = {
        "phase6j_landed": phase6j_landed,
        "protocol": {
            "h_tail": "min(tau, 0.45)",
            "predicted_tail_miss": "e_z - h_tail*v_z",
            "claimed_envelope": "|e_x| + 2*sigma_x + 0.06",
            "sigma_e": SIGMA_E,
            "sigma_v": SIGMA_V,
            "failure_action": "raise sigma_model — never the corridor",
        },
        "warm": cohort_stats(warm, "warm_phase6i_r"),
        "cold": cohort_stats(cold, "cold_phase6j"),
        "flights_warm": [
            {**{k: v for k, v in r.items() if k != "exposures"},
             "n_exp": len(r.get("exposures") or [])}
            for r in warm
        ],
        "flights_cold": [
            {k: v for k, v in r.items() if k != "exposures"}
            for r in cold
        ],
        "note": (
            "Cold cohort empty until phase6j lands. Warm numbers are "
            "PREP only — not the registered R5 verdict."
        ),
    }

    # Save exposures for warm
    with (OUT / "warm_exposures.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["fid", "t_ff", "e_z", "vz", "tau", "h_tail", "e_x",
                  "sigma_x", "claimed_envelope", "obs_miss", "contained",
                  "small_envelope", "R"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in warm:
            for e in r.get("exposures") or []:
                w.writerow({"fid": r["fid"], **{k: e.get(k) for k in fields
                                                 if k != "fid"}})

    (OUT / "summary.json").write_text(
        json.dumps(bundle, indent=2, default=str), encoding="utf-8")
    # also stash full warm with exposures in a separate file
    (OUT / "warm_full.json").write_text(
        json.dumps(warm, indent=2, default=str), encoding="utf-8")

    report = render(bundle)
    (OUT / "r5-envelope-prep.md").write_text(report, encoding="utf-8")
    (ROOT / "analysis" / "2026-07-20-r5-envelope-prep.md").write_text(
        report, encoding="utf-8")
    print(json.dumps({
        "phase6j_landed": phase6j_landed,
        "warm": bundle["warm"],
        "cold": bundle["cold"],
    }, indent=2))
    return 0


def render(b: dict) -> str:
    lines = [
        "# R5 empirical envelope prep (P3)",
        "",
        "Pre-registered (RESPONSE12 / e16d506): per unique live-arm "
        "exposure, predicted tail miss "
        "`e_x = e_z − h_tail·v_z` with `h_tail = min(τ, 0.45)` vs "
        "observed true-axis crossing miss; containment of "
        "`|e_x| + 2σ_x + 0.06`. Failures raise `sigma_model` — "
        "**never the corridor**.",
        "",
        f"## phase6j landed? **{b['phase6j_landed']}**",
        "",
        b["note"],
        "",
        "## Warm prep (phase6i-R live passes)",
        "",
        "```json",
        json.dumps(b["warm"], indent=2),
        "```",
        "",
        "### Per flight",
        "",
        "| fid | obs_miss | n_exp | containment | small-env misses |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in b["flights_warm"]:
        if r.get("error"):
            lines.append(f"| `{r['fid']}` | — | — | — | {r['error']} |")
            continue
        cr = r.get("containment_rate")
        cr_s = "" if cr is None else f"{100*cr:.0f}%"
        lines.append(
            f"| `{r['fid']}` | {r.get('obs_crossing_miss_up')} | "
            f"{r.get('n_unique_exposures')} | {cr_s} | "
            f"{r.get('n_miss_with_small_envelope')} |"
        )
    lines += [
        "",
        "## Cold cohort (phase6j)",
        "",
        "```json",
        json.dumps(b["cold"], indent=2),
        "```",
        "",
        "## Re-run recipe (when phase6j lands)",
        "",
        "```text",
        "python analysis/2026-07-20-r5-envelope-prep/run_r5_envelope_prep.py",
        "# auto-discovers fixtures/*phase6j* live-arm logs into cold cohort",
        "```",
        "",
        "## Deliverables",
        "",
        "- `r5-envelope-prep.md`, `summary.json`, `warm_exposures.csv`",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
