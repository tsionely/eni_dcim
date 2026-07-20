"""P2 — Non-contact ledger (RESPONSE23 / advisory-15 §1.1).

Every clean crossing (logged dz, zero gate clips) is a one-sided envelope
bound:
  no contact ⇒ h_up < 0.8 − dz  and  h_down < 0.8 + dz

Emit provenance-graded table; report tightest defensible bound per tail.
"""
from __future__ import annotations

import csv
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

from aigp.core.messages import RelPose  # noqa: E402
from aigp.planning.approach import true_world_dz  # noqa: E402
from run_a8_half_extent import resolve_log, parse_flight, nearest  # noqa: E402

OPENING_HALF = 0.8

# Anchors named by think-tank + inventory clean (gates≥1, clips=0)
KNOWN = [
    {
        "flight": "milestone_first_clean_pass",
        "fid": "20260716T131137-2ca531c3",
        "fixture": "20260716T132549-phase3j-r2training-rerun",
        "dz": 0.100,
        "truth_source": "miss_map_true_vertical / milestone autopsy "
                        "(closest STATE crossing vector)",
        "grade": "A_canonical",
        "gate_clips": 0,
        "note": "first clean pass; think-tank anchor h_up < 0.70",
    },
    {
        "flight": "phase6h_try15_clean",
        "fid": "20260719T160537-f170ead6",
        "fixture": "20260719T164956-phase6h-first-enable",
        "dz": None,  # fill from log
        "truth_source": "state true_world_dz at closest fresh approach",
        "grade": "A_logged",
        "gate_clips": 0,
        "note": "phase6h clean pass (clips=0)",
    },
    {
        "flight": "phase6i_slot1_pass",
        "fid": "20260719T200816-f170ead6",
        "fixture": "20260719T204430-phase6i-r-rate-ab",
        "dz": None,
        "truth_source": "state true_world_dz at closest fresh approach",
        "grade": "A_logged",
        "gate_clips": 0,
        "note": "phase6i-r inventory clean pass",
    },
    {
        "flight": "phase6i_slot4_pass",
        "fid": "20260719T201851-50f9dcc8",
        "fixture": "20260719T204430-phase6i-r-rate-ab",
        "dz": None,
        "truth_source": "state true_world_dz at closest fresh approach",
        "grade": "A_logged",
        "gate_clips": 0,
        "note": "phase6i-r inventory clean pass",
    },
]

# Think-tank stated 4/4 cohort envelope (RESPONSE12/23) — cite as
# provenance-B until per-flight dz reconstructed.
THINK_TANK_4OF4 = {
    "flight": "thinktank_4of4_cohort_aggregate",
    "fid": None,
    "dz_implied_for_h_up_0p79": 0.8 - 0.79,   # +0.01
    "dz_implied_for_h_down_0p71": 0.71 - 0.8,  # -0.09
    "h_up_bound": 0.79,
    "h_down_bound": 0.71,
    "truth_source": "docs/thinktank RESPONSE12/23 (4/4 pass cohort aggregate)",
    "grade": "B_aggregate_cite",
    "note": "cited bound; superseded by tighter per-flight rows when present",
}


def closest_fresh_dz(path: Path) -> dict | None:
    log = parse_flight(path)
    best = None
    for st in log["states"]:
        gr = st.get("gate_rel")
        if not gr or not gr.get("t"):
            continue
        age = st.get("age")
        if age is None or not math.isfinite(float(age)) or float(age) > 0.35:
            continue
        t = list(map(float, gr["t"]))
        R = float(np.linalg.norm(t))
        if R > 2.0:
            continue
        q = np.asarray(st.get("q_att") or [1, 0, 0, 0], float)
        lr = float(st.get("level_roll") or 0.0)
        lp = float(st.get("level_pitch") or 0.0)
        n = np.asarray(gr.get("normal") or [0.0, 0.0, 1.0], float)
        dz = float(true_world_dz(RelPose(t=np.array(t), normal=n), q, lr, lp))
        score = R
        if best is None or score < best["R"]:
            best = {
                "t_ff": st["t_ff"], "R": R, "age": float(age), "dz": dz,
            }
    return best


def bounds_from_dz(dz: float) -> dict:
    return {
        "dz": dz,
        "h_up_lt": OPENING_HALF - dz,
        "h_down_lt": OPENING_HALF + dz,
    }


def load_inventory_clean() -> list[dict]:
    inv_path = ROOT / "analysis" / "_d7_inventory_out.json"
    if not inv_path.exists():
        return []
    inv = json.loads(inv_path.read_text(encoding="utf-8"))
    out = []
    for fx in inv.get("fixtures", []):
        for f in fx.get("flights", []):
            if int(f.get("gates") or 0) >= 1 and int(f.get("clips") or 0) == 0:
                out.append({
                    "fixture": fx["fixture"],
                    "fid": f["id"],
                    "closest_state_r": f.get("closest_state_r"),
                })
    return out


def main() -> None:
    rows = []
    # Seed known anchors
    for k in KNOWN:
        entry = dict(k)
        if entry["dz"] is None:
            path = resolve_log(entry["fid"], entry["fixture"])
            if path is None:
                entry["status"] = "MISSING_LOG"
                entry["dz"] = None
            else:
                hit = closest_fresh_dz(path)
                if hit is None:
                    entry["status"] = "NO_FRESH_CLOSE_STATE"
                    entry["dz"] = None
                else:
                    entry["status"] = "OK"
                    entry["dz"] = hit["dz"]
                    entry["R"] = hit["R"]
                    entry["age"] = hit["age"]
                    entry["t_ff"] = hit["t_ff"]
                    entry["log"] = str(path)
        else:
            entry["status"] = "OK"
            entry["R"] = 0.103  # milestone closest
            entry["age"] = None
        if entry.get("dz") is not None:
            b = bounds_from_dz(float(entry["dz"]))
            entry.update(b)
        rows.append(entry)

    # Any inventory clean not already present
    have = {r["fid"] for r in rows if r.get("fid")}
    for inv in load_inventory_clean():
        if inv["fid"] in have:
            continue
        path = resolve_log(inv["fid"], inv["fixture"])
        entry = {
            "flight": f"inventory_{inv['fid']}",
            "fid": inv["fid"],
            "fixture": inv["fixture"],
            "truth_source": "inventory clean + closest fresh true_world_dz",
            "grade": "A_logged",
            "gate_clips": 0,
            "note": "extra inventory clean pass",
        }
        if path is None:
            entry["status"] = "MISSING_LOG"
        else:
            hit = closest_fresh_dz(path)
            if hit is None:
                entry["status"] = "NO_FRESH_CLOSE_STATE"
            else:
                entry["status"] = "OK"
                entry["dz"] = hit["dz"]
                entry["R"] = hit["R"]
                entry["age"] = hit["age"]
                entry["t_ff"] = hit["t_ff"]
                entry.update(bounds_from_dz(hit["dz"]))
                entry["log"] = str(path)
        rows.append(entry)

    usable = [r for r in rows if r.get("status") == "OK" and r.get("dz") is not None]
    # Tightest defensible: min of upper bounds, min of lower bounds
    # (smaller bound = tighter constraint on half-extent)
    h_up_vals = [r["h_up_lt"] for r in usable]
    h_down_vals = [r["h_down_lt"] for r in usable]
    # Only positive / meaningful one-sided bounds (crossing inside opening)
    h_up_def = [v for v in h_up_vals if v > 0]
    h_down_def = [v for v in h_down_vals if v > 0]

    tight_up = min(h_up_def) if h_up_def else None
    tight_down = min(h_down_def) if h_down_def else None
    who_up = next((r for r in usable if r.get("h_up_lt") == tight_up), None)
    who_down = next((r for r in usable if r.get("h_down_lt") == tight_down), None)

    # Compare to think-tank 4/4 cite
    cite = THINK_TANK_4OF4

    summary = {
        "ask": "non-contact ledger — one-sided envelope bounds",
        "formula": "no clip ⇒ h_up < 0.8 − dz ; h_down < 0.8 + dz",
        "n_rows": len(rows),
        "n_usable": len(usable),
        "thinktank_4of4_cite": cite,
        "tightest_defensible": {
            "h_up_lt": tight_up,
            "from_flight": None if who_up is None else who_up.get("flight"),
            "from_fid": None if who_up is None else who_up.get("fid"),
            "dz": None if who_up is None else who_up.get("dz"),
            "h_down_lt": tight_down,
            "from_flight_down": None if who_down is None else who_down.get("flight"),
            "from_fid_down": None if who_down is None else who_down.get("fid"),
            "dz_down": None if who_down is None else who_down.get("dz"),
        },
        "envelope_may_close_from_archive": bool(
            tight_up is not None and tight_up <= 0.70
            and tight_down is not None
        ),
        "rows": rows,
    }

    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8")

    fields = [
        "flight", "fid", "dz", "h_up_lt", "h_down_lt", "grade",
        "truth_source", "gate_clips", "R", "age", "status", "note",
    ]
    with (OUT / "ledger.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

    lines = [
        "# Non-contact ledger",
        "",
        "Every clean crossing (zero gate clips) with logged dz is a "
        "**one-sided** envelope bound:",
        "",
        "```",
        "no contact ⇒  h_up < 0.8 − dz",
        "              h_down < 0.8 + dz",
        "```",
        "",
        "## Tightest defensible bounds",
        "",
        f"- **h_up < {tight_up:.3f}** "
        f"(from `{who_up['fid'] if who_up else '?'}` "
        f"dz={who_up['dz']:+.3f})" if who_up else "- h_up: none",
        f"- **h_down < {tight_down:.3f}** "
        f"(from `{who_down['fid'] if who_down else '?'}` "
        f"dz={who_down['dz']:+.3f})" if who_down else "- h_down: none",
        "",
        "Think-tank 4/4 aggregate cite: "
        f"h_up < {cite['h_up_bound']}, h_down < {cite['h_down_bound']} "
        f"(grade {cite['grade']}).",
        "",
        "## Provenance table",
        "",
        "| flight | fid | dz | h_up < | h_down < | grade | truth source |",
        "|--------|-----|---:|-------:|---------:|:-----:|--------------|",
    ]
    for r in rows:
        if r.get("dz") is None:
            lines.append(
                f"| {r.get('flight')} | `{r.get('fid')}` | — | — | — | "
                f"{r.get('grade')} | {r.get('status')}: {r.get('truth_source')} |"
            )
        else:
            lines.append(
                f"| {r.get('flight')} | `{r.get('fid')}` | "
                f"{r['dz']:+.3f} | {r['h_up_lt']:.3f} | {r['h_down_lt']:.3f} | "
                f"{r.get('grade')} | {r.get('truth_source')} |"
            )
    lines += [
        "",
        "## Reading",
        "",
        "The milestone pass (+0.100) remains the tightest **upper** "
        "archive bound (h_up < 0.70). Lower-tail tightness comes from "
        "the most negative clean-crossing dz. Contact-harvest numbers "
        "(0.744 / 0.638) are **not** ledger rows — they require clips.",
        "",
        "## Deliverables",
        "",
        "- `ledger.csv`, `summary.json`, this report",
    ]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary["tightest_defensible"], indent=2))


if __name__ == "__main__":
    main()
