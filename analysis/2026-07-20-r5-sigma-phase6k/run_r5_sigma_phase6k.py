"""P3 — R5 sigma library on phase6k (cohort-2 REDO).

TERM validation endpoint + CORRIDOR_INTERIM expiry key.
Wraps the prepped envelope harness against the phase6k fixture
(live under eni_dcim until the sim-run lands on github fixtures).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PREP = ROOT / "analysis" / "2026-07-20-r5-envelope-prep"
sys.path.insert(0, str(PREP))

import run_r5_envelope_prep as prep  # noqa: E402

PHASE6K_DIRS = [
    ROOT / "fixtures" / "20260720T063618-phase6k-cohort-2-redo",
    Path(r"C:\Users\tsion\Projects\eni_dcim\fixtures\20260720T063618-phase6k-cohort-2-redo"),
]

LIVE_FIDS = [
    "20260720T062921-790186c4",  # F2 live
    "20260720T063147-790186c4",  # F4 live
    "20260720T063419-790186c4",  # F6 live
]
# Control pass (F1) also usable for envelope residual (not treatment)
CONTROL_PASS = "20260720T062804-c38fd469"


def find_fixture() -> Path | None:
    for p in PHASE6K_DIRS:
        if p.exists():
            return p
    return None


def build_cold(fixture: Path) -> list[dict]:
    cold = []
    for fid in LIVE_FIDS + [CONTROL_PASS]:
        log = fixture / f"{fid}-flight.jsonl"
        alt = Path(r"C:\Users\tsion\Projects\eni_dcim\logs") / fid / "flight.jsonl"
        cold.append({
            "fid": fid,
            "cohort": "cold_phase6k",
            "log": log if log.exists() else alt,
            "alt": alt,
        })
    return cold


def cohort_stats(rows, name):
    scored = []
    for r in rows:
        scored.extend([e for e in r.get("exposures") or []
                       if e.get("contained") is not None])
    if not scored:
        return {"cohort": name, "n": 0, "containment_rate": None,
                "n_miss_small_env": 0, "n_flights": len(rows),
                "n_errors": sum(1 for r in rows if r.get("error"))}
    return {
        "cohort": name,
        "n": len(scored),
        "n_flights": len(rows),
        "n_errors": sum(1 for r in rows if r.get("error")),
        "containment_rate": sum(1 for e in scored if e["contained"]) / len(scored),
        "n_miss_small_env": sum(
            1 for e in scored
            if e["contained"] is False and e.get("small_envelope")),
        "median_claimed": float(
            __import__("numpy").median([e["claimed_envelope"] for e in scored])),
        "median_abs_obs": float(
            __import__("numpy").median([abs(e["obs_miss"]) for e in scored
                                        if e.get("obs_miss") is not None])),
        "median_abs_ex": float(
            __import__("numpy").median([abs(e["e_x"]) for e in scored])),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fixture = find_fixture()
    if fixture is None:
        summary = {
            "phase6k_landed": False,
            "note": "awaiting fixtures/20260720T063618-phase6k-cohort-2-redo",
        }
        (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        (OUT / "report.md").write_text(
            "# R5 sigma library — BLOCKED\n\nphase6k fixtures not found.\n",
            encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return

    warm_rows = [prep.analyze(m) for m in prep.WARM_LIVE]
    cold_meta = build_cold(fixture)
    cold_rows = [prep.analyze(m) for m in cold_meta]
    warm_s = cohort_stats(warm_rows, "warm_phase6i_r")
    cold_s = cohort_stats(cold_rows, "cold_phase6k")

    # Expiry key: CORRIDOR_INTERIM expires when cold containment is measured
    # with n_exposures > 0 on the redo cohort.
    corridor_expiry = {
        "constant": "corridor_interim_m",
        "interim_value": 0.30,
        "successor": "C_contact = 0.18 with evidence sigmas",
        "expiry_condition": "phase6k cold sigma library landed with n>0",
        "expired": bool(cold_s.get("n", 0) > 0),
        "cold_n": cold_s.get("n"),
        "cold_containment": cold_s.get("containment_rate"),
        "action_if_expired": (
            "raise sigma_model on containment failures; never widen corridor; "
            "then set corridor := C_contact once sigmas hold"
        ),
    }

    summary = {
        "ask": "R5 sigma library — phase6k cohort-2 redo",
        "phase6k_landed": True,
        "fixture": str(fixture),
        "warm": warm_s,
        "cold": cold_s,
        "corridor_interim_expiry": corridor_expiry,
        "flights_warm": warm_rows,
        "flights_cold": cold_rows,
    }
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8")

    # Copy exposure CSVs from cold scored flights if harness wrote them
    lines = [
        "# R5 sigma library — phase6k (cohort-2 REDO)",
        "",
        "## Verdict",
        "",
        f"- **phase6k landed**: `{fixture.name}`",
        f"- **Warm (phase6i-R)**: n=`{warm_s.get('n')}`, "
        f"containment=`{warm_s.get('containment_rate')}`",
        f"- **Cold (phase6k)**: n=`{cold_s.get('n')}`, "
        f"containment=`{cold_s.get('containment_rate')}`, "
        f"miss_small_env=`{cold_s.get('n_miss_small_env')}`",
        f"- **CORRIDOR_INTERIM expiry**: "
        f"{'TRIGGERED' if corridor_expiry['expired'] else 'not yet'} "
        f"(cold n={corridor_expiry['cold_n']}) — successor "
        f"`{corridor_expiry['successor']}`",
        "",
        "### Per-flight cold status",
        "",
    ]
    for r in cold_rows:
        err = r.get("error")
        if err:
            status = f"ERROR: {err}"
        else:
            status = (
                f"n_exp={r.get('n_unique_exposures')} "
                f"contain={r.get('containment_rate')}"
            )
        lines.append(
            f"- `{r.get('fid')}` cohort=`{r.get('cohort')}` {status}"
        )
    lines += [
        "",
        "## Method",
        "",
        "Reuses `2026-07-20-r5-envelope-prep/run_r5_envelope_prep.py` "
        "analyze/summarize against phase6k live-arm (+ control pass) logs.",
        "",
        f"Generated by `{OUT.name}/run_r5_sigma_phase6k.py`.",
    ]
    text = "\n".join(lines)
    (OUT / "report.md").write_text(text, encoding="utf-8")
    (ROOT / "analysis" / "2026-07-20-r5-sigma-phase6k.md").write_text(
        text, encoding="utf-8")
    print(json.dumps({
        "phase6k_landed": True,
        "warm": warm_s,
        "cold": cold_s,
        "corridor_interim_expiry": corridor_expiry,
    }, indent=2, default=str))


if __name__ == "__main__":
    main()
