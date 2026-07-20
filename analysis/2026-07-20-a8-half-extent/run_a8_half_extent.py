"""P4 — A8 drone vertical half-extent from graze contacts.

Samples:
  - phase6d F1 (20260719T134326) nine micro-clips
  - phase6h try39 (163649) clip pair at t_ff≈4.035 / 4.042

Method (advisory-8 A8 convention):
  At each collision with threat_level≥1 and impulse in graze band, take
  nearest state gate_rel → true_world_dz; contact height proxy =
  opening_half_height 0.8 − true_dz_at_contact.
  Report MAX and scatter of (0.8 − true_dz).
  h_drone ≈ max(0, max_contact_clearance_deficit).
  Compare to 0.45 clamp borrowing 0.15 m.

Outputs:
  analysis/2026-07-20-a8-half-extent/summary.json
  analysis/2026-07-20-a8-half-extent.md
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
MD_ROOT = ROOT / "analysis" / "2026-07-20-a8-half-extent.md"
sys.path.insert(0, str(ROOT / "src"))

from aigp.core.messages import RelPose  # noqa: E402
from aigp.planning.approach import true_world_dz  # noqa: E402

OPENING_HALF_H = 0.8
CLAMP_BORROW = 0.45
BORROW_ASSUMED = 0.15  # 0.45 clamp borrows 0.15m on faith
GRAZE_IMPULSE = (0.02, 1.2)  # exclude hard death impulses
# try39 target times (pre-pass graze pair)
TRY39_CLIP_TIMES = (4.035, 4.042)

FLIGHTS = [
    {
        "label": "phase6d_F1",
        "fid": "20260719T134326-2477345e",
        "fixture": "20260719T134835-phase6d-fiction-guards",
        "note": "nine micro-clips",
        "select": "all_graze",
    },
    {
        "label": "try39_clip_pair",
        "fid": "20260719T163649-f170ead6",
        "fixture": "20260719T164956-phase6h-first-enable",
        "note": "clip pair t_ff≈4.035/4.042",
        "select": "try39_pair",
    },
]

FIX_ROOTS = [
    ROOT / "fixtures",
    Path(r"C:\Users\tsion\Projects\eni_dcim\fixtures"),
]
LOG_ROOTS = [
    Path(r"C:\Users\tsion\Projects\eni_dcim\logs"),
]


def resolve_log(fid: str, fixture: str) -> Path | None:
    for root in FIX_ROOTS:
        p = root / fixture / f"{fid}-flight.jsonl"
        if p.exists():
            return p
    for root in FIX_ROOTS + LOG_ROOTS:
        if not root.exists():
            continue
        hits = list(root.glob(f"**/{fid}-flight.jsonl"))
        if hits:
            return hits[0]
        p = root / fid / "flight.jsonl"
        if p.exists():
            return p
    return None


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def takeoff_mono(rows: list[dict]) -> int:
    for r in rows:
        if r.get("topic") == "fsm":
            d = r["data"]
            if d.get("dst") == "TAKEOFF" or "GO" in str(d.get("reason", "")).upper():
                return int(r["mono_ns"])
    for r in rows:
        if r.get("topic") == "setpoint" and r["data"].get("phase") == "takeoff":
            return int(r["mono_ns"])
    return int(rows[0]["mono_ns"])


def parse_flight(path: Path) -> dict:
    rows = load_jsonl(path)
    t0 = int(rows[0]["mono_ns"])
    toff = takeoff_mono(rows)
    states, dets, colls = [], [], []
    for r in rows:
        mono = int(r["mono_ns"])
        t_ff = (mono - toff) / 1e9
        topic = r.get("topic")
        d = r.get("data") or {}
        if topic == "state":
            states.append({
                "t_ff": t_ff,
                "gate_rel": d.get("gate_rel"),
                "q_att": d.get("q_att") or [1, 0, 0, 0],
                "level_roll": float(d.get("level_roll") or 0.0),
                "level_pitch": float(d.get("level_pitch") or 0.0),
                "age": d.get("gate_rel_age_s"),
            })
        elif topic == "detection":
            rp = d.get("rel_pose") or {}
            tvec = d.get("t_vec") or rp.get("t")
            if tvec is None:
                continue
            tvec = list(map(float, tvec))
            dets.append({
                "t_ff": t_ff, "t_vec": tvec,
                "R": float(np.linalg.norm(tvec)),
                "ty": tvec[1],
                "normal": rp.get("normal") or d.get("normal"),
            })
        elif topic == "collision":
            colls.append({
                "t_ff": t_ff,
                "impulse": float(d.get("impulse") or 0.0),
                "threat_level": int(d.get("threat_level") or 0),
            })
    return {"states": states, "dets": dets, "collisions": colls,
            "t0": t0, "takeoff": toff}


def nearest(items, t_ff, max_dt=0.12):
    if not items:
        return None
    best = min(items, key=lambda x: abs(x["t_ff"] - t_ff))
    return best if abs(best["t_ff"] - t_ff) <= max_dt else None


def select_grazes(meta: dict, colls: list[dict]) -> list[dict]:
    grazes = [c for c in colls
              if c["threat_level"] >= 1
              and GRAZE_IMPULSE[0] <= c["impulse"] <= GRAZE_IMPULSE[1]]
    if meta["select"] == "try39_pair":
        out = []
        for target in TRY39_CLIP_TIMES:
            near = [c for c in grazes if abs(c["t_ff"] - target) < 0.05]
            if not near:
                near = [c for c in colls if abs(c["t_ff"] - target) < 0.05]
            if near:
                out.append(min(near, key=lambda c: abs(c["t_ff"] - target)))
        # dedupe
        seen = set()
        uniq = []
        for c in out:
            key = round(c["t_ff"], 3)
            if key not in seen:
                seen.add(key)
                uniq.append(c)
        return uniq
    return grazes


def contact_row(c: dict, states, dets) -> dict:
    st = nearest(states, c["t_ff"], max_dt=0.15)
    det = nearest([d for d in dets if d["R"] < 4.0], c["t_ff"], max_dt=0.2)
    if det is None:
        det = nearest(dets, c["t_ff"], max_dt=0.2)

    tw = None
    ty_state = None
    R_state = None
    if st and st.get("gate_rel"):
        t = list(map(float, st["gate_rel"]["t"]))
        ty_state = t[1]
        R_state = float(np.linalg.norm(t))
        nrm = st["gate_rel"].get("normal") or [0, 0, 1]
        tw = float(true_world_dz(
            RelPose(t=np.asarray(t, float),
                    normal=np.asarray(nrm, float)),
            np.asarray(st["q_att"], float),
            st["level_roll"], st["level_pitch"]))

    ty_det = det["ty"] if det else None
    # Prefer state true_dz; if missing use det with nearest state attitude
    if tw is None and det is not None and st is not None:
        nrm = det.get("normal") or [0, 0, 1]
        tw = float(true_world_dz(
            RelPose(t=np.asarray(det["t_vec"], float),
                    normal=np.asarray(nrm, float)),
            np.asarray(st["q_att"], float),
            st["level_roll"], st["level_pitch"]))

    # A8: contact_clearance_proxy = 0.8 - true_dz
    # true_dz > 0 ⇒ gate below me ⇒ vehicle HIGH ⇒ less bottom clearance
    # If we graze TOP while HIGH, true_dz positive large ⇒ 0.8-tw small/neg
    # "clearance deficit" for half-extent: how much of the 0.8 half-opening
    # was eaten — max(0, -(0.8 - true_dz)) when overshooting high? 
    # Spec: report (0.8 - true_dz); h_drone ≈ max(0, max_contact_clearance_deficit)
    # Interpret clearance_deficit = max(0, -(0.8 - true_dz)) = max(0, true_dz - 0.8)
    # when vehicle is so high that gate center is >0.8 below → outside opening.
    # Also for LOW grazes (true_dz negative): 0.8 - (-|dz|) = 0.8+|dz| large.
    # The advisory wants MAX and scatter of (0.8 - true_dz) and
    # h_drone ≈ max(0, max_contact_clearance_deficit).
    # Practical: clearance_deficit = | |0.8| - |true_dz_toward_bar| | ...
    # From design: "contact height proxy = opening half-height 0.8 - true_dz"
    # and h_drone from the MAX of that series when it goes negative?
    proxy = None if tw is None else (OPENING_HALF_H - tw)
    # deficit: when proxy < 0, contact is outside the geometric half-opening
    # by -proxy meters → that sizes half-extent
    deficit = None if proxy is None else max(0.0, -proxy)

    return {
        "t_ff": c["t_ff"],
        "impulse": c["impulse"],
        "threat_level": c["threat_level"],
        "true_world_dz": tw,
        "proxy_0p8_minus_true_dz": proxy,
        "clearance_deficit": deficit,
        "ty_state": ty_state,
        "ty_det": ty_det,
        "R_state": R_state,
        "R_det": det["R"] if det else None,
        "dt_state": (abs(st["t_ff"] - c["t_ff"]) if st else None),
    }


def analyze_one(meta: dict) -> dict:
    path = resolve_log(meta["fid"], meta["fixture"])
    if path is None:
        return {"label": meta["label"], "fid": meta["fid"], "error": "log_not_found"}
    log = parse_flight(path)
    grazes = select_grazes(meta, log["collisions"])
    contacts = [contact_row(c, log["states"], log["dets"]) for c in grazes]
    proxies = [c["proxy_0p8_minus_true_dz"] for c in contacts
               if c["proxy_0p8_minus_true_dz"] is not None]
    deficits = [c["clearance_deficit"] for c in contacts
                if c["clearance_deficit"] is not None]
    return {
        "label": meta["label"],
        "fid": meta["fid"],
        "note": meta["note"],
        "path": str(path),
        "n_grazes_selected": len(grazes),
        "n_with_true_dz": len(proxies),
        "contacts": contacts,
        "proxy_stats": {
            "n": len(proxies),
            "max": float(max(proxies)) if proxies else None,
            "min": float(min(proxies)) if proxies else None,
            "mean": float(np.mean(proxies)) if proxies else None,
            "std": float(np.std(proxies)) if proxies else None,
            "median": float(np.median(proxies)) if proxies else None,
        },
        "max_clearance_deficit": float(max(deficits)) if deficits else None,
    }


def aggregate(rows: list[dict]) -> dict:
    all_proxies = []
    all_deficits = []
    all_contacts = []
    for r in rows:
        if r.get("error"):
            continue
        for c in r.get("contacts") or []:
            all_contacts.append({**c, "flight": r["label"]})
            if c.get("proxy_0p8_minus_true_dz") is not None:
                all_proxies.append(c["proxy_0p8_minus_true_dz"])
            if c.get("clearance_deficit") is not None:
                all_deficits.append(c["clearance_deficit"])
    max_proxy = float(max(all_proxies)) if all_proxies else None
    min_proxy = float(min(all_proxies)) if all_proxies else None
    max_def = float(max(all_deficits)) if all_deficits else 0.0
    h_drone = max(0.0, max_def)
    # Alternate reading used in some drafts: h_drone from how far proxy
    # falls below the borrowed 0.15 — report both.
    return {
        "n_contacts": len(all_contacts),
        "n_with_proxy": len(all_proxies),
        "proxy_0p8_minus_true_dz": {
            "max": max_proxy,
            "min": min_proxy,
            "mean": float(np.mean(all_proxies)) if all_proxies else None,
            "std": float(np.std(all_proxies)) if all_proxies else None,
            "median": float(np.median(all_proxies)) if all_proxies else None,
            "p10": float(np.percentile(all_proxies, 10)) if all_proxies else None,
            "p90": float(np.percentile(all_proxies, 90)) if all_proxies else None,
        },
        "max_contact_clearance_deficit_m": max_def if all_deficits else None,
        "h_drone_m": h_drone,
        "h_drone_formula": "max(0, max(clearance_deficit)) with deficit=max(0,-(0.8-true_dz))",
        "compare_to_clamp": {
            "clamp_m": CLAMP_BORROW,
            "borrowed_on_faith_m": BORROW_ASSUMED,
            "h_drone_vs_borrow": (
                None if not all_deficits else
                float(h_drone - BORROW_ASSUMED)
            ),
            "supports_0p15_borrow": (
                None if not all_deficits else bool(h_drone <= BORROW_ASSUMED + 0.05)
            ),
            "suggested_clamp": (
                None if not all_deficits else
                float(min(0.6, max(0.3, math.ceil(h_drone * 20) / 20)))
            ),
        },
    }


def write_md(summary: dict) -> str:
    agg = summary["aggregate"]
    p = agg["proxy_0p8_minus_true_dz"]
    lines = [
        "# A8 drone vertical half-extent",
        "",
        "Graze-contact sizing of vertical half-extent via "
        "`0.8 − true_world_dz` (advisory-8 A8 convention).",
        "",
        "## Verdict",
        "",
        f"- **(0.8 − true_dz) max / median / std**: "
        f"`{p.get('max')}` / `{p.get('median')}` / `{p.get('std')}`",
        f"- **max clearance deficit**: `{agg.get('max_contact_clearance_deficit_m')}` m",
        f"- **h_drone**: `{agg.get('h_drone_m')}` m "
        f"({agg.get('h_drone_formula')})",
        f"- vs 0.45 clamp borrowing 0.15 m: "
        f"supports_borrow=`{agg['compare_to_clamp'].get('supports_0p15_borrow')}` "
        f"(h_drone − 0.15 = `{agg['compare_to_clamp'].get('h_drone_vs_borrow')}`)",
        f"- suggested_clamp: `{agg['compare_to_clamp'].get('suggested_clamp')}`",
        "",
        "## Contacts",
        "",
        "| flight | t_ff | impulse | threat | true_dz | 0.8−dz | deficit | ty_det | R |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in summary["flights"]:
        if r.get("error"):
            lines.append(f"| {r['label']} | ERR {r['error']} | | | | | | | |")
            continue
        for c in r["contacts"]:
            lines.append(
                f"| {r['label']} | {c['t_ff']:.3f} | {c['impulse']:.3f} | "
                f"{c['threat_level']} | {_f(c['true_world_dz'])} | "
                f"{_f(c['proxy_0p8_minus_true_dz'])} | "
                f"{_f(c['clearance_deficit'])} | {_f(c['ty_det'])} | "
                f"{_f(c['R_state'] if c['R_state'] is not None else c['R_det'])} |"
            )
    lines += [
        "",
        "## Method",
        "",
        "1. Select grazes: threat_level≥1 and impulse ∈ [0.02, 1.2].",
        "2. try39: keep the pair nearest t_ff 4.035 / 4.042.",
        "3. Nearest state gate_rel → `true_world_dz` (level composition).",
        "4. proxy = 0.8 − true_dz; deficit = max(0, −proxy).",
        "5. h_drone = max deficit across all graze samples.",
        "",
        f"Generated by `{OUT.name}/run_a8_half_extent.py`.",
        "",
    ]
    return "\n".join(lines)


def _f(v) -> str:
    if v is None:
        return "—"
    return f"{v:.3f}"


def main():
    rows = [analyze_one(m) for m in FLIGHTS]
    summary = {
        "ask": "A8 drone vertical half-extent",
        "flights": rows,
        "aggregate": aggregate(rows),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8")
    md = write_md(summary)
    (OUT / "report.md").write_text(md, encoding="utf-8")
    MD_ROOT.write_text(md, encoding="utf-8")
    agg = summary["aggregate"]
    print("A8 done")
    print("proxy max/med/std", agg["proxy_0p8_minus_true_dz"])
    print("h_drone", agg.get("h_drone_m"))
    print("compare", agg.get("compare_to_clamp"))
    for r in rows:
        print(r.get("label"), "n", r.get("n_grazes_selected"),
              "with_dz", r.get("n_with_true_dz"), r.get("error"))


if __name__ == "__main__":
    main()
