"""P2 — phase6l endpoints (RESPONSE16 pre-registration).

When phase6l fixtures land, report:
  (a) commit vision survival past 3m vs cohorts 1–2
  (b) blind-brake range census (4.3–4.8m cluster must vanish/re-attribute)
  (c) R5 library extension with any live-arm crossings (expiry re-arm)
  (d) fork metric (first commit <1.1m ⇒ pass) on non-blind attempts

Auto-discovers fixtures/*phase6l*; writes BLOCKED report if absent.
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
sys.path.insert(0, str(ROOT / "analysis" / "2026-07-20-vision-death-3m"))
sys.path.insert(0, str(ROOT / "analysis" / "2026-07-20-r5-envelope-prep"))

from run_vision_death_3m import (  # noqa: E402
    COHORT1, COHORT2, analyze_one, cohort_summary, first_commit_window,
    load_flight, NEAR_R_LOSS_BAND, BLIND_BUDGET_S,
)
import run_r5_envelope_prep as r5  # noqa: E402

FIX_ROOTS = [
    ROOT / "fixtures",
    Path(r"C:\Users\tsion\Projects\eni_dcim\fixtures"),
]
LOG_ROOTS = [Path(r"C:\Users\tsion\Projects\eni_dcim\logs")]

FORK_RANGE_M = 1.1
BLIND_BRAKE_CLUSTER = (4.3, 4.8)


def discover_phase6l() -> list[Path]:
    found = []
    for root in FIX_ROOTS:
        if root.exists():
            found.extend(sorted(root.glob("*phase6l*")))
    # de-dupe by name
    by = {}
    for p in found:
        by.setdefault(p.name, p)
    return list(by.values())


def list_flights(fixture: Path) -> list[dict]:
    """Infer arm from params or summary.json / notes."""
    flights = []
    summary_path = fixture / "summary.json"
    if summary_path.exists():
        s = json.loads(summary_path.read_text(encoding="utf-8"))
        for row in s.get("flights") or []:
            flights.append({
                "slot": row.get("slot"),
                "arm": row.get("arm") or "unknown",
                "fid": row.get("fid"),
                "fixture": fixture,
            })
        if flights:
            return flights
    for log in sorted(fixture.glob("*-flight.jsonl")):
        fid = log.name.replace("-flight.jsonl", "")
        arm = "unknown"
        params = fixture / f"{fid}-params.json"
        if params.exists():
            try:
                p = json.loads(params.read_text(encoding="utf-8"))
                # terminal.enable patch ⇒ live
                flat = p if isinstance(p, dict) else {}
                te = flat.get("planner", {}).get("terminal", {}).get("enable")
                if te is True:
                    arm = "live"
                elif te is False:
                    arm = "control"
            except Exception:
                pass
        flights.append({"slot": None, "arm": arm, "fid": fid, "fixture": fixture})
    return flights


def first_commit_closest(log: dict) -> dict:
    c0, c1 = first_commit_window(log["setpoints"])
    if c0 is None:
        return {"error": "no_commit"}
    near = []
    for d in log["dets"]:
        if d["R"] is None:
            continue
        if c0 - 0.05 <= d["t_ff"] <= (c1 or c0 + 8) and d["R"] < 8:
            if d.get("cert") in ("certified", "probation", None):
                near.append(d)
    # also state ranges during commit
    state_min = None
    for s in log["states"]:
        if c0 <= s["t_ff"] <= (c1 or c0 + 8) and s["R"] is not None:
            if state_min is None or s["R"] < state_min["R"]:
                state_min = s
    det_min = min(near, key=lambda d: d["R"]) if near else None
    closest = None
    if det_min and state_min:
        closest = det_min if det_min["R"] <= state_min["R"] else {
            "R": state_min["R"], "t_ff": state_min["t_ff"], "source": "state"}
        if closest is det_min:
            closest = {**det_min, "source": "det"}
    elif det_min:
        closest = {**det_min, "source": "det"}
    elif state_min:
        closest = {"R": state_min["R"], "t_ff": state_min["t_ff"], "source": "state"}

    # Blind during first commit?
    max_age = 0.0
    inf_age = False
    for s in log["states"]:
        if not (c0 <= s["t_ff"] <= (c1 or c0 + 8)):
            continue
        a = s["age"]
        if a is None or not math.isfinite(a) or a > 1e6:
            inf_age = True
            max_age = float("inf")
        else:
            max_age = max(max_age, a)
    blind = bool(inf_age or max_age >= BLIND_BUDGET_S)
    return {
        "commit_start": c0,
        "commit_end": c1,
        "closest_R": closest["R"] if closest else None,
        "closest_t": closest.get("t_ff") if closest else None,
        "closest_source": closest.get("source") if closest else None,
        "max_age": None if not math.isfinite(max_age) else max_age,
        "max_age_inf": inf_age,
        "blind_first_commit": blind,
        "fork_trigger": (
            closest is not None and closest["R"] < FORK_RANGE_M and not blind
        ),
    }


def gates_passed(fid: str, fixture: Path) -> int | None:
    for root in [fixture, *LOG_ROOTS]:
        for name in (f"{fid}-result.json", "result.json"):
            p = root / name if name.startswith(fid) else root / fid / name
            if p.exists():
                try:
                    return int(json.loads(p.read_text(encoding="utf-8"))
                               .get("gates_passed") or 0)
                except Exception:
                    pass
    return None


def blind_brake_ranges(log: dict) -> list[dict]:
    """Ranges where age first breaches blind budget during first commit."""
    c0, c1 = first_commit_window(log["setpoints"])
    if c0 is None:
        return []
    out = []
    stale_from = None
    for s in log["states"]:
        if s["t_ff"] < c0:
            continue
        if c1 is not None and s["t_ff"] > c1 + 1.0:
            break
        age = s["age"]
        bad = age is None or not math.isfinite(age) or age >= BLIND_BUDGET_S
        if bad:
            if stale_from is None:
                stale_from = s
                out.append({
                    "t_ff": s["t_ff"],
                    "R_believed": s["R"],
                    "age": age if age is not None and math.isfinite(age) else None,
                    "age_inf": age is None or not math.isfinite(age) or age > 1e6,
                    "in_4p3_4p8_cluster": (
                        s["R"] is not None
                        and BLIND_BRAKE_CLUSTER[0] <= s["R"] <= BLIND_BRAKE_CLUSTER[1]
                    ),
                })
        else:
            stale_from = None
    return out


def analyze_phase6l_flight(meta: dict) -> dict:
    fixture = meta["fixture"]
    path = fixture / f"{meta['fid']}-flight.jsonl"
    if not path.exists():
        for root in LOG_ROOTS:
            alt = root / meta["fid"] / "flight.jsonl"
            if alt.exists():
                path = alt
                break
    if not path.exists():
        return {**meta, "error": "log_missing"}
    log = load_flight(path)
    # Reuse vision-death analyzer
    vd = analyze_one(
        {"slot": meta.get("slot"), "arm": meta.get("arm"), "fid": meta["fid"]},
        fixture, do_frames=False)
    fork = first_commit_closest(log)
    brakes = blind_brake_ranges(log)
    gp = gates_passed(meta["fid"], fixture)
    survived_past_3 = False
    ln = (vd.get("vision_death") or {}).get("last_near_detection") or {}
    # Survival past 3m: got a near fix with R<3 without vision death,
    # OR closest during commit < 3 with age fresh
    if fork.get("closest_R") is not None and fork["closest_R"] < 3.0:
        if not fork.get("blind_first_commit"):
            survived_past_3 = True
    if (not vd.get("vision_died_no_reacq")
            and ln.get("R") is not None and ln["R"] < 3.0):
        survived_past_3 = True

    return {
        **meta,
        "log_path": str(path),
        "gates_passed": gp,
        "vision_death": vd.get("vision_death"),
        "vision_died_no_reacq": vd.get("vision_died_no_reacq"),
        "loss_mode": vd.get("loss_mode"),
        "survived_past_3m": survived_past_3,
        "fork": fork,
        "blind_brakes": brakes,
        "n_blind_brake_in_cluster": sum(
            1 for b in brakes if b.get("in_4p3_4p8_cluster")),
        "passed": gp is not None and gp >= 1,
    }


def r5_live_extension(flights: list[dict]) -> dict:
    live = [f for f in flights if f.get("arm") == "live" and not f.get("error")]
    rows = []
    for f in live:
        path = Path(f["log_path"])
        rows.append(r5.analyze({
            "fid": f["fid"],
            "cohort": "cold_phase6l_live",
            "log": path,
            "alt": path,
        }))
    scored = []
    for r in rows:
        scored.extend([e for e in r.get("exposures") or []
                       if e.get("contained") is not None])
    n_pass = sum(1 for r in rows if r.get("t_pass_ff") is not None)
    return {
        "n_live_flights": len(live),
        "n_live_with_hud_pass": n_pass,
        "n_scored_exposures": len(scored),
        "containment_rate": (
            sum(1 for e in scored if e["contained"]) / len(scored)
            if scored else None),
        "expiry_rearm_live_arm_met": n_pass > 0 and len(scored) > 0,
        "flights": [{k: v for k, v in r.items() if k != "exposures"} for r in rows],
    }


def blocked_report():
    text = "\n".join([
        "# phase6l endpoints — BLOCKED",
        "",
        "phase6l fixtures not found under `fixtures/*phase6l*`.",
        "",
        "Pre-registered (RESPONSE16 / HEAD `4fc71bb` damper):",
        "",
        "(a) commit vision survival past 3 m vs cohorts 1–2",
        "(b) blind-brake range census (4.3–4.8 m cluster)",
        "(c) R5 library extension — live-arm crossings (CORRIDOR_INTERIM re-arm)",
        "(d) fork metric: first commit <1.1 m ⇒ pass, on non-blind attempts",
        "",
        "Re-run: `python analysis/2026-07-20-phase6l-endpoints/run_phase6l_endpoints.py`",
        "",
    ])
    (OUT / "report.md").write_text(text, encoding="utf-8")
    (ROOT / "analysis" / "2026-07-20-phase6l-endpoints.md").write_text(
        text, encoding="utf-8")
    (OUT / "summary.json").write_text(json.dumps({
        "phase6l_landed": False,
        "awaiting": "fixtures/*phase6l*",
    }, indent=2), encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fixtures = discover_phase6l()
    if not fixtures:
        blocked_report()
        print(json.dumps({"phase6l_landed": False}, indent=2))
        return

    # Baseline cohorts (already on disk)
    c1 = [analyze_one(m, COHORT1["fixture"], do_frames=False)
          for m in COHORT1["flights"]]
    c2 = [analyze_one(m, COHORT2["fixture"], do_frames=False)
          for m in COHORT2["flights"]]
    s1, s2 = cohort_summary(c1), cohort_summary(c2)

    all_f = []
    for fx in fixtures:
        all_f.extend(list_flights(fx))
    rows = [analyze_phase6l_flight(m) for m in all_f]

    n = len(rows)
    n_surv = sum(1 for r in rows if r.get("survived_past_3m"))
    n_death = sum(1 for r in rows if r.get("vision_died_no_reacq"))
    cluster_hits = sum(r.get("n_blind_brake_in_cluster") or 0 for r in rows)
    n_with_cluster = sum(1 for r in rows if (r.get("n_blind_brake_in_cluster") or 0) > 0)

    # Fork metric on non-blind
    nonblind = [r for r in rows if not (r.get("fork") or {}).get("blind_first_commit")]
    fork_trig = [r for r in nonblind if (r.get("fork") or {}).get("fork_trigger")]
    fork_pass = [r for r in fork_trig if r.get("passed")]
    fork_metric = {
        "n_nonblind": len(nonblind),
        "n_fork_trigger_lt_1p1": len(fork_trig),
        "n_fork_pass": len(fork_pass),
        "pass_rate_given_trigger": (
            len(fork_pass) / len(fork_trig) if fork_trig else None),
        "claim": "first commit <1.1m => pass (non-blind only)",
    }

    r5ext = r5_live_extension(rows)

    # Survival past 3m rates
    def surv_rate(cohort_rows):
        # cohort vision-death rows: survived = not vision_died
        # Also approximate: last near R < 3 and not death
        ok = 0
        for r in cohort_rows:
            vd = r.get("vision_death") or {}
            ln = vd.get("last_near_detection") or {}
            if (not r.get("vision_died_no_reacq")
                    and ln.get("R") is not None and ln["R"] < 3.0):
                ok += 1
            elif not r.get("vision_died_no_reacq"):
                # held vision somehow
                ok += 1
        return ok, len(cohort_rows)

    # For c1/c2 use inverse of death as "survival" proxy matching prior ledger
    c1_surv = s1["n"] - s1["n_vision_death_no_reacq"]
    c2_surv = s2["n"] - s2["n_vision_death_no_reacq"]

    summary = {
        "phase6l_landed": True,
        "fixtures": [str(p) for p in fixtures],
        "a_vision_survival_past_3m": {
            "phase6l": {"n_survived": n_surv, "n": n, "frac": n_surv / n if n else None},
            "cohort1_held_vision": {"n": c1_surv, "of": s1["n"], "frac": c1_surv / s1["n"]},
            "cohort2_held_vision": {"n": c2_surv, "of": s2["n"], "frac": c2_surv / s2["n"]},
            "cohort2_was": "1/6 held in RESPONSE16 wording; measured death 6/6 on phase6j",
            "claim": "survival past 3m rises materially from cohort-2",
            "claim_met": (n_surv / n > c2_surv / s2["n"]) if n and s2["n"] else None,
        },
        "b_blind_brake_census": {
            "cluster_m": list(BLIND_BRAKE_CLUSTER),
            "n_flights_with_cluster_hit": n_with_cluster,
            "n_cluster_events": cluster_hits,
            "cluster_vanished": n_with_cluster == 0,
            "per_flight": [
                {"fid": r["fid"], "arm": r.get("arm"),
                 "n_cluster": r.get("n_blind_brake_in_cluster"),
                 "brakes": r.get("blind_brakes")}
                for r in rows if not r.get("error")
            ],
        },
        "c_r5_live_extension": r5ext,
        "d_fork_metric": fork_metric,
        "flights": rows,
        "baselines": {"cohort1": s1, "cohort2": s2},
    }
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8")

    a = summary["a_vision_survival_past_3m"]
    b = summary["b_blind_brake_census"]
    lines = [
        "# phase6l endpoints",
        "",
        "## Verdict",
        "",
        f"- **Fixtures**: `{[p.name for p in fixtures]}`",
        f"- **(a) Vision survival past 3 m**: phase6l "
        f"{n_surv}/{n}; cohort-1 held {c1_surv}/{s1['n']}; "
        f"cohort-2 held {c2_surv}/{s2['n']}; claim_met=`{a['claim_met']}`",
        f"- **(b) Blind-brake 4.3–4.8 m cluster**: "
        f"flights_with_hit=`{n_with_cluster}`, events=`{cluster_hits}`, "
        f"vanished=`{b['cluster_vanished']}`",
        f"- **(c) R5 live-arm extension**: "
        f"hud_passes=`{r5ext['n_live_with_hud_pass']}`, "
        f"scored_exp=`{r5ext['n_scored_exposures']}`, "
        f"rearm_met=`{r5ext['expiry_rearm_live_arm_met']}`",
        f"- **(d) Fork metric** (non-blind, <1.1 m ⇒ pass): "
        f"trigger `{fork_metric['n_fork_trigger_lt_1p1']}` / "
        f"nonblind `{fork_metric['n_nonblind']}`; "
        f"pass given trigger=`{fork_metric['pass_rate_given_trigger']}`",
        "",
        "## Per-flight",
        "",
        "| fid | arm | past_3m | vision_death | closest_R | blind | fork | gates | cluster |",
        "|---|---|:---:|:---:|---:|:---:|:---:|---:|---:|",
    ]
    for r in rows:
        fk = r.get("fork") or {}
        lines.append(
            f"| `{r.get('fid')}` | {r.get('arm')} | "
            f"{'Y' if r.get('survived_past_3m') else 'n'} | "
            f"{'Y' if r.get('vision_died_no_reacq') else 'n'} | "
            f"{fk.get('closest_R') if fk.get('closest_R') is not None else float('nan'):.2f} | "
            f"{'Y' if fk.get('blind_first_commit') else 'n'} | "
            f"{'Y' if fk.get('fork_trigger') else 'n'} | "
            f"{r.get('gates_passed')} | {r.get('n_blind_brake_in_cluster')} |"
        )
    lines += [
        "",
        "## Method",
        "",
        "Auto-discovers `fixtures/*phase6l*`. Vision survival / death reuses "
        "`run_vision_death_3m`. Blind-brake = first age≥0.6s in commit with "
        "believed R. R5 live extension reuses envelope prep analyze(). "
        "Fork = closest R<1.1 m on non-blind first commit.",
        "",
        f"Generated by `{OUT.name}/run_phase6l_endpoints.py`.",
    ]
    text = "\n".join(lines)
    (OUT / "report.md").write_text(text, encoding="utf-8")
    (ROOT / "analysis" / "2026-07-20-phase6l-endpoints.md").write_text(
        text, encoding="utf-8")
    print(json.dumps({
        "phase6l_landed": True,
        "a": a,
        "b": {"cluster_vanished": b["cluster_vanished"],
              "n_with_hit": n_with_cluster},
        "c": {k: r5ext[k] for k in (
            "n_live_with_hud_pass", "n_scored_exposures",
            "expiry_rearm_live_arm_met", "containment_rate")},
        "d": fork_metric,
    }, indent=2, default=str))


if __name__ == "__main__":
    main()
