"""T6 commit_exit census — same method as T5, with direct T5 comparison.

Questions:
  Did corridor_abort exits drop vs T5?
  Did exit `down` move from ~-0.77 toward 0 (centered)?

Run:
  C:/Users/tsion/Projects/eni_dcim/.venv/Scripts/python.exe \\
    analysis/2026-07-25-t6-census/run_t6_census.py
"""
from __future__ import annotations

import importlib.util
import json
import math
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
T5_SUMMARY = ROOT / "analysis" / "2026-07-25-exit-census" / "summary.json"
T5_SCRIPT = ROOT / "analysis" / "2026-07-25-exit-census" / "run_exit_census.py"
REACHED_M = 2.0
REASONS = (
    "pass", "stale_budget", "relock_jump", "geometric_behind",
    "term_abort", "corridor_abort", "timer_expired",
)
# T5 reached-gate corridor_abort downs (from census report): -0.768, -0.885, -0.533
T5_BASELINE = {
    "n_fixtures": 6,
    "n_reached": 3,
    "n_corridor_abort_reached": 3,
    "corridor_abort_frac_reached": 1.0,
    "down_median": -0.768,
    "down_values": [-0.768, -0.885, -0.533],
    "right_median": 0.029,
    "fwd_median": 0.986,
}


def finite(x):
    return isinstance(x, (int, float)) and math.isfinite(x)


def load_t5_module():
    spec = importlib.util.spec_from_file_location("t5_exit_census", T5_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def discover_t6(root: Path) -> list[Path]:
    roots = [root / "fixtures"]
    sibling = root.parent / "eni_dcim" / "fixtures"
    if sibling.is_dir():
        roots.append(sibling)
    by_name: dict[str, Path] = {}
    github = root / "fixtures"
    for fix in roots:
        if not fix.is_dir():
            continue
        for p in sorted(fix.iterdir()):
            if not p.is_dir() or not re.search(r"t6", p.name, re.IGNORECASE):
                continue
            if (github / p.name).is_dir():
                by_name[p.name] = github / p.name
            elif p.name not in by_name:
                by_name[p.name] = p
    return sorted(by_name.values(), key=lambda p: p.name)


def load_t5_baseline() -> dict:
    base = dict(T5_BASELINE)
    if not T5_SUMMARY.is_file():
        return base
    try:
        data = json.loads(T5_SUMMARY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return base
    hist = data.get("histogram_reached") or {}
    n_reached = int(data.get("n_reached") or 0)
    n_corr = int(hist.get("corridor_abort") or 0)
    downs, rights, fwds = [], [], []
    for flight in data.get("flights") or []:
        for a in flight.get("attempts") or []:
            if not a.get("reached_gate"):
                continue
            if a.get("reason") != "corridor_abort":
                continue
            if finite(a.get("gate_rel_t_down")):
                downs.append(float(a["gate_rel_t_down"]))
            if finite(a.get("gate_rel_t_right")):
                rights.append(float(a["gate_rel_t_right"]))
            if finite(a.get("gate_rel_t_fwd")):
                fwds.append(float(a["gate_rel_t_fwd"]))
    base.update({
        "n_fixtures": data.get("n_fixtures", base["n_fixtures"]),
        "n_reached": n_reached,
        "n_corridor_abort_reached": n_corr,
        "corridor_abort_frac_reached": (n_corr / n_reached) if n_reached else None,
        "down_median": median(downs) if downs else base["down_median"],
        "down_values": downs or base["down_values"],
        "right_median": median(rights) if rights else base["right_median"],
        "fwd_median": median(fwds) if fwds else base["fwd_median"],
        "histogram_reached": hist,
    })
    return base


def summarize(flights: list[dict]) -> dict:
    attempts = [a for f in flights for a in f.get("attempts", [])]
    reached = [a for a in attempts if a.get("reached_gate")]
    near_miss = [a for a in reached if a.get("reason") != "pass"]
    hist_all = Counter(a["reason"] for a in attempts)
    hist_reached = Counter(a["reason"] for a in reached)
    corr = [a for a in reached if a.get("reason") == "corridor_abort"]
    downs = [a["gate_rel_t_down"] for a in corr if finite(a.get("gate_rel_t_down"))]
    rights = [a["gate_rel_t_right"] for a in corr if finite(a.get("gate_rel_t_right"))]
    fwds = [a["gate_rel_t_fwd"] for a in corr if finite(a.get("gate_rel_t_fwd"))]
    # Also report downs for ALL reached exits (not only corridor)
    downs_all_r = [a["gate_rel_t_down"] for a in reached if finite(a.get("gate_rel_t_down"))]
    rights_all_r = [a["gate_rel_t_right"] for a in reached if finite(a.get("gate_rel_t_right"))]
    return {
        "n_fixtures": len(flights),
        "n_exits": len(attempts),
        "n_reached": len(reached),
        "n_near_miss": len(near_miss),
        "histogram_reached": dict(hist_reached),
        "histogram_all": dict(hist_all),
        "n_corridor_abort_reached": len(corr),
        "corridor_abort_frac_reached": (len(corr) / len(reached)) if reached else None,
        "corridor_down_median": median(downs) if downs else None,
        "corridor_down_values": downs,
        "corridor_right_median": median(rights) if rights else None,
        "corridor_fwd_median": median(fwds) if fwds else None,
        "reached_down_median": median(downs_all_r) if downs_all_r else None,
        "reached_right_median": median(rights_all_r) if rights_all_r else None,
        "reached": reached,
        "attempts": attempts,
    }


def write_waiting(head: str | None):
    OUT.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "WAITING",
        "head": head,
        "reason": "no fixtures/*t6* yet; T6 registered (aim_up_floor_m=0.3)",
        "t5_baseline": load_t5_baseline(),
    }
    (OUT / "summary.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (OUT / "report.md").write_text(
        "\n".join([
            "# T6 exit census — WAITING",
            "",
            f"HEAD: `{head or 'unknown'}`.",
            "",
            "No `fixtures/*t6*` present. Re-run after the 8-run T6 block lands.",
            "",
            "T5 baseline (reached-gate): corridor_abort 3/3, down median −0.77 m.",
            "",
        ]),
        encoding="utf-8",
    )


def write_csvs(reached, attempts):
    import csv
    fields = [
        "fixture", "attempt", "reason", "reached_gate",
        "gate_rel_t_right", "gate_rel_t_down", "gate_rel_t_fwd",
        "gate_rel_age_s", "exit_range_m", "closest_range_m", "closest_fwd_m",
        "gates_passed_flight",
    ]
    for name, rows in (("reached_exits.csv", reached), ("all_exits.csv", attempts)):
        with (OUT / name).open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            for row in rows:
                w.writerow(row)


def fmt(x):
    if x is None or not finite(x):
        return "—"
    return f"{x:.3f}"


def write_report(flights: list[dict], head: str | None, t5: dict, t6: dict):
    corr_drop = None
    if t5.get("corridor_abort_frac_reached") is not None and t6.get("corridor_abort_frac_reached") is not None:
        corr_drop = t5["corridor_abort_frac_reached"] - t6["corridor_abort_frac_reached"]
    down_delta = None
    if finite(t5.get("down_median")) and finite(t6.get("corridor_down_median")):
        down_delta = t6["corridor_down_median"] - t5["down_median"]
    elif finite(t5.get("down_median")) and finite(t6.get("reached_down_median")):
        # No corridor exits — use all reached downs
        down_delta = t6["reached_down_median"] - t5["down_median"]

    # Verdicts
    if t6["n_reached"] == 0:
        q1 = "NO REACHED-GATE EXITS — cannot score corridor_abort drop."
        q2 = "NO REACHED-GATE EXITS — cannot score down centering."
    else:
        t5_c = t5["n_corridor_abort_reached"]
        t6_c = t6["n_corridor_abort_reached"]
        t5_f = t5.get("corridor_abort_frac_reached")
        t6_f = t6.get("corridor_abort_frac_reached")
        if t6_c < t5_c or (t6_f is not None and t5_f is not None and t6_f < t5_f - 1e-9):
            q1 = (
                f"**YES — corridor_abort dropped**: T5 {t5_c}/{t5['n_reached']} "
                f"({100*(t5_f or 0):.0f}%) → T6 {t6_c}/{t6['n_reached']} "
                f"({100*(t6_f or 0):.0f}%)."
            )
        elif t6_c == 0:
            q1 = (
                f"**YES — corridor_abort eliminated**: T5 {t5_c}/{t5['n_reached']} → "
                f"T6 0/{t6['n_reached']}."
            )
        else:
            q1 = (
                f"**NO — corridor_abort did not drop**: T5 {t5_c}/{t5['n_reached']} "
                f"({100*(t5_f or 0):.0f}%) → T6 {t6_c}/{t6['n_reached']} "
                f"({100*(t6_f or 0):.0f}%)."
            )

        t5_down = t5.get("down_median")
        t6_down = t6.get("corridor_down_median")
        if t6_down is None:
            t6_down = t6.get("reached_down_median")
            down_src = "all reached-gate exits (no corridor_abort sample)"
        else:
            down_src = "corridor_abort exits"
        if t6_down is None:
            q2 = "NO down samples at reached-gate exits."
        else:
            # Move toward 0 means |t6_down| < |t5_down| and preferably t6 closer to 0
            improved = abs(t6_down) < abs(t5_down) - 0.05
            q2 = (
                f"{'**YES — down moved toward 0**' if improved else '**NO — down did not center**'}: "
                f"T5 median down={t5_down:.3f} m → T6 median down={t6_down:.3f} m "
                f"(Δ={t6_down - t5_down:+.3f} m; {down_src})."
            )

    lines = [
        "# T6 exit census vs T5",
        "",
        f"HEAD: `{head or 'unknown'}`.",
        f"T6 fixtures: **{t6['n_fixtures']}/8**. Commit exits: **{t6['n_exits']}**. "
        f"Reached-gate (closest < {REACHED_M:g} m): **{t6['n_reached']}**.",
        "",
        "## THE QUESTIONS",
        "",
        f"1. Did `corridor_abort` exits drop? {q1}",
        f"2. Did exit `down` move from −0.77 toward 0? {q2}",
        "",
        "## Direct comparison",
        "",
        "| metric | T5 | T6 | Δ |",
        "| --- | ---: | ---: | ---: |",
        f"| fixtures | {t5.get('n_fixtures')} | {t6['n_fixtures']} | |",
        f"| reached-gate exits | {t5.get('n_reached')} | {t6['n_reached']} | |",
        f"| corridor_abort (reached) | {t5.get('n_corridor_abort_reached')} | "
        f"{t6['n_corridor_abort_reached']} | "
        f"{(t6['n_corridor_abort_reached'] - t5.get('n_corridor_abort_reached', 0)):+d} |",
        f"| corridor_abort fraction | "
        f"{fmt(t5.get('corridor_abort_frac_reached'))} | "
        f"{fmt(t6.get('corridor_abort_frac_reached'))} | "
        f"{fmt(corr_drop) if corr_drop is not None else '—'} |",
        f"| down median (corr / reached) | {fmt(t5.get('down_median'))} | "
        f"{fmt(t6.get('corridor_down_median') if t6.get('corridor_down_median') is not None else t6.get('reached_down_median'))} | "
        f"{fmt(down_delta) if down_delta is not None else '—'} |",
        f"| right median | {fmt(t5.get('right_median'))} | "
        f"{fmt(t6.get('corridor_right_median') if t6.get('corridor_right_median') is not None else t6.get('reached_right_median'))} | |",
        f"| fwd median | {fmt(t5.get('fwd_median'))} | "
        f"{fmt(t6.get('corridor_fwd_median'))} | |",
        "",
        "## (1) T6 exit-reason histogram — reached-gate",
        "",
        "| reason | n_reached | n_all |",
        "| --- | ---: | ---: |",
    ]
    hist_r = t6["histogram_reached"]
    hist_a = t6["histogram_all"]
    for reason in REASONS:
        lines.append(
            f"| `{reason}` | {hist_r.get(reason, 0)} | {hist_a.get(reason, 0)} |"
        )
    for reason in sorted(set(hist_a) - set(REASONS)):
        lines.append(
            f"| `{reason}` | {hist_r.get(reason, 0)} | {hist_a.get(reason, 0)} |"
        )

    lines += [
        "",
        "## (2) Per-exit down/right at reached-gate (T6)",
        "",
        "| fixture | # | reason | right | down | fwd | age_s | closest_m |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for a in t6["reached"]:
        lines.append(
            f"| `{a['fixture']}` | {a['attempt']} | `{a['reason']}` | "
            f"{fmt(a.get('gate_rel_t_right'))} | {fmt(a.get('gate_rel_t_down'))} | "
            f"{fmt(a.get('gate_rel_t_fwd'))} | {fmt(a.get('gate_rel_age_s'))} | "
            f"{fmt(a.get('closest_range_m'))} |"
        )
    if not t6["reached"]:
        lines.append("| *(none)* | | | | | | | |")

    lines += [
        "",
        "## Per-fixture",
        "",
        "| fixture | gates | n_exits | n_reached |",
        "| --- | ---: | ---: | ---: |",
    ]
    for f in flights:
        n_r = sum(1 for a in f.get("attempts", []) if a.get("reached_gate"))
        lines.append(
            f"| `{f['fixture']}` | {f.get('gates_passed')} | "
            f"{f.get('n_commit_exits')} | {n_r} |"
        )

    lines += [
        "",
        "## Artifacts",
        "",
        "- `reached_exits.csv` / `all_exits.csv`",
        "- `summary.json`",
        "- `run_t6_census.py`",
        "",
    ]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    payload = {
        "status": "COMPLETE" if t6["n_fixtures"] >= 8 else "PARTIAL",
        "head": head,
        "n_fixtures_expected": 8,
        "questions": {
            "corridor_abort_dropped": q1,
            "down_moved_toward_zero": q2,
        },
        "t5": {k: v for k, v in t5.items() if k != "down_values" or True},
        "t6": {
            k: v for k, v in t6.items()
            if k not in ("reached", "attempts")
        },
        "comparison": {
            "corridor_abort_frac_delta": corr_drop,
            "down_median_delta": down_delta,
        },
        "flights": [
            {
                "fixture": f["fixture"],
                "gates_passed": f.get("gates_passed"),
                "n_commit_exits": f.get("n_commit_exits"),
                "attempts": f.get("attempts"),
            }
            for f in flights
        ],
    }
    # trim large nested from t5 copy
    if "down_values" in payload["t5"]:
        payload["t5"]["down_values"] = list(payload["t5"]["down_values"])
    (OUT / "summary.json").write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return payload


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    head = None
    try:
        head = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        pass

    fixtures = discover_t6(ROOT)
    if not fixtures:
        write_waiting(head)
        print(json.dumps({"status": "WAITING", "n_fixtures": 0, "head": head}, indent=2))
        return 2

    mod = load_t5_module()
    # Temporarily point OUT writes for csv helper — we write ourselves
    flights = []
    for folder in fixtures:
        info = mod.analyze_fixture(folder)
        if info.get("error"):
            continue
        flights.append(info)

    if not any(f.get("n_commit_exits", 0) > 0 for f in flights):
        write_waiting(head)
        print(json.dumps({
            "status": "WAITING",
            "n_fixtures": len(fixtures),
            "n_with_commit_exit": 0,
            "head": head,
        }, indent=2))
        return 2

    t5 = load_t5_baseline()
    t6 = summarize(flights)
    write_csvs(t6["reached"], t6["attempts"])
    payload = write_report(flights, head, t5, t6)
    print(json.dumps({
        "status": payload["status"],
        "n_fixtures": t6["n_fixtures"],
        "n_reached": t6["n_reached"],
        "histogram_reached": t6["histogram_reached"],
        "n_corridor_abort_reached": t6["n_corridor_abort_reached"],
        "corridor_down_median": t6["corridor_down_median"],
        "reached_down_median": t6["reached_down_median"],
        "questions": payload["questions"],
        "comparison": payload["comparison"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
