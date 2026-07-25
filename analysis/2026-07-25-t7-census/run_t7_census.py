"""T7 commit_exit census — same method as T5/T6, plus clip-budget check.

Questions:
  (a) Did corridor_abort drop sharply with abort_offset_m=0.7?
  (b) Did gate-clip aborts rise? (gate_clips per run + clip-budget aborts)

Baselines (user task / prior censuses):
  T5: corridor 3/3, down≈-0.77, gates 3/6
  T6: corridor 5/6, down≈-0.52 (reached median), gates 2/8

Run:
  C:/Users/tsion/Projects/eni_dcim/.venv/Scripts/python.exe \\
    analysis/2026-07-25-t7-census/run_t7_census.py
"""
from __future__ import annotations

import csv
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
T5_SCRIPT = ROOT / "analysis" / "2026-07-25-exit-census" / "run_exit_census.py"
T5_SUMMARY = ROOT / "analysis" / "2026-07-25-exit-census" / "summary.json"
T6_SUMMARY = ROOT / "analysis" / "2026-07-25-t6-census" / "summary.json"
REACHED_M = 2.0
REASONS = (
    "pass", "stale_budget", "relock_jump", "geometric_behind",
    "term_abort", "corridor_abort", "timer_expired",
)
# Task-stated baselines (overridden by summary.json when present).
T5_BASE = {
    "label": "T5",
    "n_fixtures": 6,
    "gates_passed_sum": 3,
    "n_reached": 3,
    "n_corridor_abort_reached": 3,
    "corridor_frac": 1.0,
    "down_median": -0.77,
    "gate_clips_sum": None,
    "n_clip_budget_aborts": None,
}
T6_BASE = {
    "label": "T6",
    "n_fixtures": 8,
    "gates_passed_sum": 2,
    "n_reached": 6,
    "n_corridor_abort_reached": 5,
    "corridor_frac": 5 / 6,
    "down_median": -0.52,
    "gate_clips_sum": None,
    "n_clip_budget_aborts": None,
}


def finite(x):
    return isinstance(x, (int, float)) and math.isfinite(x)


def fmt(x, nd=3):
    if x is None or not finite(x):
        return "—"
    return f"{x:.{nd}f}"


def load_t5_mod():
    spec = importlib.util.spec_from_file_location("t5_exit_census", T5_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def discover_t7(root: Path) -> list[Path]:
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
            if not p.is_dir():
                continue
            name = p.name
            if not (
                re.search(r"raceprep-t7-B-", name, re.IGNORECASE)
                or re.search(r"t7", name, re.IGNORECASE)
            ):
                continue
            # Prefer raceprep-t7-B-* ; still accept any *t7*
            if (github / name).is_dir():
                by_name[name] = github / name
            elif name not in by_name:
                by_name[name] = p
    # Prefer names matching raceprep-t7-B-
    preferred = [p for p in by_name.values() if re.search(r"raceprep-t7-B-", p.name, re.I)]
    return sorted(preferred or by_name.values(), key=lambda p: p.name)


def read_result(folder: Path) -> dict:
    out = {
        "gates_passed": None,
        "abort_reason": None,
        "gate_clips": None,
        "env_hits": None,
        "clip_budget_abort": False,
    }
    for name in ("result.json", "run-summary.json"):
        path = folder / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data.get("gates_passed"), (int, float)):
            out["gates_passed"] = int(data["gates_passed"])
        if isinstance(data.get("gate_clips"), (int, float)):
            out["gate_clips"] = int(data["gate_clips"])
        if isinstance(data.get("env_hits"), (int, float)):
            out["env_hits"] = int(data["env_hits"])
        ar = data.get("abort_reason") or data.get("abort")
        if isinstance(ar, str):
            out["abort_reason"] = ar
            low = ar.lower()
            if "gate clip budget" in low or "clip budget exceeded" in low:
                out["clip_budget_abort"] = True
            elif "clip" in low and "budget" in low:
                out["clip_budget_abort"] = True
    notes = folder / "notes.md"
    if notes.is_file() and not out["clip_budget_abort"]:
        try:
            text = notes.read_text(encoding="utf-8", errors="replace").lower()
        except OSError:
            text = ""
        if "clip-budget" in text or "clip budget" in text or "gate-clip abort" in text:
            out["clip_budget_abort"] = True
        if out["abort_reason"] is None:
            for line in text.splitlines():
                if "abort" in line and ":" in line:
                    out["abort_reason"] = line.split(":", 1)[-1].strip()[:120]
                    break
    return out


def load_prior_block(path: Path, fallback: dict) -> dict:
    base = dict(fallback)
    if not path.is_file():
        return base
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return base

    # T5 summary shape vs T6 nested under "t6"
    block = data
    if "t6" in data and isinstance(data["t6"], dict):
        block = data["t6"]
        # gates from flights if present
        gates = 0
        for f in data.get("flights") or []:
            gp = f.get("gates_passed")
            if isinstance(gp, (int, float)):
                gates += int(gp)
        if gates:
            base["gates_passed_sum"] = gates
    elif "flights" in data:
        gates = 0
        for f in data.get("flights") or []:
            gp = f.get("gates_passed")
            if isinstance(gp, (int, float)):
                gates += int(gp)
        if gates:
            base["gates_passed_sum"] = gates

    n_reached = block.get("n_reached", data.get("n_reached"))
    hist = block.get("histogram_reached") or data.get("histogram_reached") or {}
    n_corr = block.get("n_corridor_abort_reached")
    if n_corr is None:
        n_corr = hist.get("corridor_abort", 0)
    down = block.get("reached_down_median")
    if down is None:
        down = block.get("corridor_down_median")
    if down is None:
        down = block.get("down_median")
    # Prefer task's T6=-0.52 (all-reached) when available from summary
    if "reached_down_median" in block and finite(block["reached_down_median"]):
        down = block["reached_down_median"]

    downs = []
    flights = data.get("flights") or []
    for f in flights:
        for a in f.get("attempts") or []:
            if not a.get("reached_gate"):
                continue
            if finite(a.get("gate_rel_t_down")):
                downs.append(float(a["gate_rel_t_down"]))
    if downs and down is None:
        down = median(downs)

    n_reached = int(n_reached or 0)
    n_corr = int(n_corr or 0)
    base.update({
        "n_fixtures": block.get("n_fixtures") or data.get("n_fixtures") or base["n_fixtures"],
        "n_reached": n_reached or base["n_reached"],
        "n_corridor_abort_reached": n_corr if n_reached else base["n_corridor_abort_reached"],
        "corridor_frac": (n_corr / n_reached) if n_reached else base["corridor_frac"],
        "down_median": float(down) if finite(down) else base["down_median"],
        "histogram_reached": hist,
    })
    return base


def summarize_t7(flights: list[dict], results: dict[str, dict]) -> dict:
    attempts = [a for f in flights for a in f.get("attempts", [])]
    reached = [a for a in attempts if a.get("reached_gate")]
    near_miss = [a for a in reached if a.get("reason") != "pass"]
    hist_all = Counter(a["reason"] for a in attempts)
    hist_reached = Counter(a["reason"] for a in reached)
    corr = [a for a in reached if a.get("reason") == "corridor_abort"]
    downs_all = [a["gate_rel_t_down"] for a in reached if finite(a.get("gate_rel_t_down"))]
    downs_corr = [a["gate_rel_t_down"] for a in corr if finite(a.get("gate_rel_t_down"))]
    rights_all = [a["gate_rel_t_right"] for a in reached if finite(a.get("gate_rel_t_right"))]

    gates_sum = 0
    clips_sum = 0
    clips_per_run = []
    clip_budget_n = 0
    for f in flights:
        r = results.get(f["fixture"], {})
        gp = r.get("gates_passed")
        if gp is None:
            gp = f.get("gates_passed")
        if isinstance(gp, (int, float)):
            gates_sum += int(gp)
        gc = r.get("gate_clips")
        if isinstance(gc, (int, float)):
            clips_sum += int(gc)
            clips_per_run.append({"fixture": f["fixture"], "gate_clips": int(gc),
                                  "abort_reason": r.get("abort_reason"),
                                  "clip_budget_abort": r.get("clip_budget_abort")})
        if r.get("clip_budget_abort"):
            clip_budget_n += 1

    dominant = None
    if near_miss:
        dominant = Counter(a["reason"] for a in near_miss).most_common(1)[0]
    elif reached:
        # if all passes, no near-miss dominant
        dominant = ("pass", hist_reached.get("pass", 0))

    return {
        "n_fixtures": len(flights),
        "n_exits": len(attempts),
        "n_reached": len(reached),
        "n_near_miss": len(near_miss),
        "histogram_reached": dict(hist_reached),
        "histogram_all": dict(hist_all),
        "n_corridor_abort_reached": len(corr),
        "corridor_frac": (len(corr) / len(reached)) if reached else None,
        "down_median": median(downs_all) if downs_all else None,
        "down_median_corridor": median(downs_corr) if downs_corr else None,
        "right_median": median(rights_all) if rights_all else None,
        "gates_passed_sum": gates_sum,
        "gate_clips_sum": clips_sum,
        "gate_clips_per_run": clips_per_run,
        "n_clip_budget_aborts": clip_budget_n,
        "dominant_near_miss": dominant[0] if dominant else None,
        "dominant_near_miss_n": dominant[1] if dominant else 0,
        "reached": reached,
        "attempts": attempts,
        "near_miss": near_miss,
    }


def write_csvs(reached, attempts):
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


def write_waiting(head):
    OUT.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "WAITING",
        "head": head,
        "reason": "no fixtures/*raceprep-t7-B-* yet; T7 registered at bee361f (abort_offset_m=0.7)",
    }
    (OUT / "summary.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (OUT / "report.md").write_text(
        "# T7 exit census — WAITING\n\n"
        f"HEAD: `{head}`.\n\n"
        "No `fixtures/*raceprep-t7-B-*` present. Re-run after the 8-run block lands.\n",
        encoding="utf-8",
    )


def write_report(flights, head, t5, t6, t7, results):
    # Questions
    t5_c, t6_c = t5["n_corridor_abort_reached"], t6["n_corridor_abort_reached"]
    t7_c = t7["n_corridor_abort_reached"]
    t5_f, t6_f, t7_f = t5["corridor_frac"], t6["corridor_frac"], t7["corridor_frac"]

    if t7["n_reached"] == 0:
        qa = "NO reached-gate exits — cannot score corridor_abort drop."
    else:
        sharp = (
            t7_f is not None
            and t6_f is not None
            and (t7_f <= 0.5 * t6_f or t7_c <= max(0, t6_c // 2))
        )
        mild = t7_f is not None and t6_f is not None and t7_f < t6_f - 1e-9
        if t7_c == 0:
            qa = (
                f"**YES — corridor_abort eliminated**: T5 {t5_c}/{t5['n_reached']} → "
                f"T6 {t6_c}/{t6['n_reached']} → T7 0/{t7['n_reached']}."
            )
        elif sharp:
            qa = (
                f"**YES — corridor_abort dropped sharply**: T5 {t5_c}/{t5['n_reached']} "
                f"({100*t5_f:.0f}%) → T6 {t6_c}/{t6['n_reached']} ({100*t6_f:.0f}%) → "
                f"T7 {t7_c}/{t7['n_reached']} ({100*t7_f:.0f}%)."
            )
        elif mild:
            qa = (
                f"**PARTIAL — corridor_abort dropped but not sharply**: T5 "
                f"{t5_c}/{t5['n_reached']} ({100*t5_f:.0f}%) → T6 {t6_c}/{t6['n_reached']} "
                f"({100*t6_f:.0f}%) → T7 {t7_c}/{t7['n_reached']} ({100*t7_f:.0f}%)."
            )
        else:
            qa = (
                f"**NO — corridor_abort did not drop**: T5 {t5_c}/{t5['n_reached']} "
                f"({100*t5_f:.0f}%) → T6 {t6_c}/{t6['n_reached']} ({100*t6_f:.0f}%) → "
                f"T7 {t7_c}/{t7['n_reached']} ({100*(t7_f or 0):.0f}%)."
            )

    # Clip rise vs T6 — need T6 clips; compute from t6 fixtures if possible
    t6_clips = t6.get("gate_clips_sum")
    t7_clips = t7["gate_clips_sum"]
    t6_clip_aborts = t6.get("n_clip_budget_aborts")
    t7_clip_aborts = t7["n_clip_budget_aborts"]

    if t6_clips is None:
        # Scan sibling/github t6 fixtures for baseline clips
        t6_clips, t6_clip_aborts = scan_block_clips(r"t6")
        t6["gate_clips_sum"] = t6_clips
        t6["n_clip_budget_aborts"] = t6_clip_aborts
    if t5.get("gate_clips_sum") is None:
        t5_clips, t5_clip_aborts = scan_block_clips(r"t5")
        t5["gate_clips_sum"] = t5_clips
        t5["n_clip_budget_aborts"] = t5_clip_aborts

    if t6_clips is None:
        qb = (
            f"T7 gate_clips_sum={t7_clips}, clip-budget aborts={t7_clip_aborts}/"
            f"{t7['n_fixtures']} — T6 clip baseline unavailable for Δ."
        )
        clip_rise = None
    else:
        clip_rise = (t7_clips or 0) > (t6_clips or 0) or (
            (t7_clip_aborts or 0) > (t6_clip_aborts or 0)
        )
        qb = (
            f"{'**YES — gate clips rose**' if clip_rise else '**NO — gate clips did not rise**'}: "
            f"T6 clips_sum={t6_clips} (clip-budget aborts={t6_clip_aborts}) → "
            f"T7 clips_sum={t7_clips} (clip-budget aborts={t7_clip_aborts}/"
            f"{t7['n_fixtures']})."
        )
        if clip_rise:
            qb += " 0.7 may be past the physical envelope (clip instead of abort)."

    # New dominant if corridor gone/low but passes still low
    gates_frac = t7["gates_passed_sum"] / t7["n_fixtures"] if t7["n_fixtures"] else 0
    new_dom_lines = []
    if (
        t7["n_reached"] > 0
        and (t7_f or 0) < 0.5
        and gates_frac < 0.5
        and t7["dominant_near_miss"]
        and t7["dominant_near_miss"] != "corridor_abort"
        and t7["dominant_near_miss"] != "pass"
    ):
        dom = t7["dominant_near_miss"]
        rows = [a for a in t7["near_miss"] if a["reason"] == dom]
        downs = [a["gate_rel_t_down"] for a in rows if finite(a.get("gate_rel_t_down"))]
        rights = [a["gate_rel_t_right"] for a in rows if finite(a.get("gate_rel_t_right"))]
        fwds = [a["gate_rel_t_fwd"] for a in rows if finite(a.get("gate_rel_t_fwd"))]
        ages = [a["gate_rel_age_s"] for a in rows if finite(a.get("gate_rel_age_s"))]
        new_dom_lines = [
            f"**NEW DOMINANT EXIT: `{dom}`** — {t7['dominant_near_miss_n']}/"
            f"{t7['n_near_miss']} near-misses (corridor_frac={fmt(t7_f)}, "
            f"gates={t7['gates_passed_sum']}/{t7['n_fixtures']}).",
            f"Geometry at exit: down median={fmt(median(downs) if downs else None)}, "
            f"right median={fmt(median(rights) if rights else None)}, "
            f"fwd median={fmt(median(fwds) if fwds else None)}, "
            f"age median={fmt(median(ages) if ages else None)} s.",
        ]
    elif t7["dominant_near_miss"] == "corridor_abort":
        new_dom_lines = [
            "No new dominant — `corridor_abort` still leads near-misses.",
        ]
    elif t7["n_near_miss"] == 0 and t7["n_reached"] > 0:
        new_dom_lines = ["All reached-gate exits are `pass` — no near-miss dominant."]
    else:
        new_dom_lines = [
            f"Dominant near-miss remains `{t7['dominant_near_miss']}` "
            f"({t7['dominant_near_miss_n']}/{t7['n_near_miss']}); "
            f"corridor_frac={fmt(t7_f)}, gates={t7['gates_passed_sum']}/{t7['n_fixtures']}."
        ]

    lines = [
        "# T7 exit census vs T5 / T6",
        "",
        f"HEAD: `{head or 'unknown'}`.",
        f"T7 fixtures: **{t7['n_fixtures']}/8**. Commit exits: **{t7['n_exits']}**. "
        f"Reached-gate (closest < {REACHED_M:g} m): **{t7['n_reached']}**.",
        "",
        "## THE TWO QUESTIONS",
        "",
        f"1. Did `corridor_abort` drop sharply (offset 0.7)? {qa}",
        f"2. Did gate-clip aborts rise? {qb}",
        "",
        "## Direct comparison",
        "",
        "| metric | T5 | T6 | T7 |",
        "| --- | ---: | ---: | ---: |",
        f"| fixtures | {t5['n_fixtures']} | {t6['n_fixtures']} | {t7['n_fixtures']} |",
        f"| gate passes (sum/block) | {t5['gates_passed_sum']}/{t5['n_fixtures']} | "
        f"{t6['gates_passed_sum']}/{t6['n_fixtures']} | "
        f"{t7['gates_passed_sum']}/{t7['n_fixtures']} |",
        f"| reached-gate exits | {t5['n_reached']} | {t6['n_reached']} | {t7['n_reached']} |",
        f"| corridor_abort / reached | {t5['n_corridor_abort_reached']}/{t5['n_reached']} | "
        f"{t6['n_corridor_abort_reached']}/{t6['n_reached']} | "
        f"{t7['n_corridor_abort_reached']}/{t7['n_reached']} |",
        f"| corridor_abort fraction | {fmt(t5['corridor_frac'])} | "
        f"{fmt(t6['corridor_frac'])} | {fmt(t7['corridor_frac'])} |",
        f"| median down @ reached exit | {fmt(t5['down_median'])} | "
        f"{fmt(t6['down_median'])} | {fmt(t7['down_median'])} |",
        f"| gate_clips sum | {t5.get('gate_clips_sum')} | {t6.get('gate_clips_sum')} | "
        f"{t7['gate_clips_sum']} |",
        f"| clip-budget aborts | {t5.get('n_clip_budget_aborts')} | "
        f"{t6.get('n_clip_budget_aborts')} | {t7['n_clip_budget_aborts']} |",
        "",
        "## (5) Next-lever target",
        "",
    ]
    lines.extend(new_dom_lines)

    lines += [
        "",
        "## (1) Exit-reason histogram — reached-gate",
        "",
        "| reason | n_reached | n_all |",
        "| --- | ---: | ---: |",
    ]
    for reason in REASONS:
        lines.append(
            f"| `{reason}` | {t7['histogram_reached'].get(reason, 0)} | "
            f"{t7['histogram_all'].get(reason, 0)} |"
        )
    for reason in sorted(set(t7["histogram_all"]) - set(REASONS)):
        lines.append(
            f"| `{reason}` | {t7['histogram_reached'].get(reason, 0)} | "
            f"{t7['histogram_all'].get(reason, 0)} |"
        )

    lines += [
        "",
        "## (2) Per reached-gate exit geometry",
        "",
        "| fixture | # | reason | right | down | fwd | age_s | closest_m |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for a in t7["reached"]:
        lines.append(
            f"| `{a['fixture']}` | {a['attempt']} | `{a['reason']}` | "
            f"{fmt(a.get('gate_rel_t_right'))} | {fmt(a.get('gate_rel_t_down'))} | "
            f"{fmt(a.get('gate_rel_t_fwd'))} | {fmt(a.get('gate_rel_age_s'))} | "
            f"{fmt(a.get('closest_range_m'))} |"
        )
    if not t7["reached"]:
        lines.append("| *(none)* | | | | | | | |")

    lines += [
        "",
        "## Gate clips per run",
        "",
        "| fixture | gates | gate_clips | clip-budget abort | abort_reason |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for f in flights:
        r = results.get(f["fixture"], {})
        lines.append(
            f"| `{f['fixture']}` | {r.get('gates_passed', f.get('gates_passed'))} | "
            f"{r.get('gate_clips')} | {r.get('clip_budget_abort')} | "
            f"{(r.get('abort_reason') or '—')[:60]} |"
        )

    lines += [
        "",
        "## Artifacts",
        "",
        "- `reached_exits.csv` / `all_exits.csv`",
        "- `summary.json`",
        "- `run_t7_census.py`",
        "",
    ]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    payload = {
        "status": "COMPLETE" if t7["n_fixtures"] >= 8 else "PARTIAL",
        "head": head,
        "n_fixtures_expected": 8,
        "questions": {
            "corridor_abort_dropped_sharply": qa,
            "gate_clips_rose": qb,
            "clip_rise_bool": clip_rise,
        },
        "t5": {k: v for k, v in t5.items()},
        "t6": {k: v for k, v in t6.items()},
        "t7": {k: v for k, v in t7.items() if k not in ("reached", "attempts", "near_miss")},
        "next_lever": new_dom_lines,
        "flights": [
            {
                "fixture": f["fixture"],
                "gates_passed": results.get(f["fixture"], {}).get("gates_passed", f.get("gates_passed")),
                "gate_clips": results.get(f["fixture"], {}).get("gate_clips"),
                "clip_budget_abort": results.get(f["fixture"], {}).get("clip_budget_abort"),
                "abort_reason": results.get(f["fixture"], {}).get("abort_reason"),
                "n_commit_exits": f.get("n_commit_exits"),
                "attempts": f.get("attempts"),
            }
            for f in flights
        ],
    }
    (OUT / "summary.json").write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return payload


def scan_block_clips(tag_re: str) -> tuple[int | None, int | None]:
    """Sum gate_clips / clip-budget aborts over fixtures matching tag."""
    fixtures = []
    for fix in (ROOT / "fixtures", ROOT.parent / "eni_dcim" / "fixtures"):
        if not fix.is_dir():
            continue
        for p in fix.iterdir():
            if p.is_dir() and re.search(tag_re, p.name, re.I):
                fixtures.append(p)
    # dedupe by name preferring github
    by = {}
    for p in fixtures:
        gh = ROOT / "fixtures" / p.name
        by[p.name] = gh if gh.is_dir() else p
    if not by:
        return None, None
    clips = 0
    budgets = 0
    for p in by.values():
        r = read_result(p)
        if isinstance(r.get("gate_clips"), int):
            clips += r["gate_clips"]
        if r.get("clip_budget_abort"):
            budgets += 1
    return clips, budgets


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    head = None
    try:
        head = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        pass

    fixtures = discover_t7(ROOT)
    if not fixtures:
        write_waiting(head)
        print(json.dumps({"status": "WAITING", "n_fixtures": 0, "head": head}, indent=2))
        return 2

    mod = load_t5_mod()
    flights = []
    results = {}
    for folder in fixtures:
        info = mod.analyze_fixture(folder)
        if info.get("error"):
            continue
        flights.append(info)
        results[folder.name] = read_result(folder)

    if not any(f.get("n_commit_exits", 0) > 0 for f in flights):
        # Still emit clip table if we have result.json even without commit_exit
        write_waiting(head)
        print(json.dumps({
            "status": "WAITING",
            "n_fixtures": len(fixtures),
            "n_with_commit_exit": 0,
            "head": head,
            "note": "t7 dirs present but no commit_exit yet",
        }, indent=2))
        return 2

    t5 = load_prior_block(T5_SUMMARY, T5_BASE)
    t6 = load_prior_block(T6_SUMMARY, T6_BASE)
    # Prefer task-stated T6 down=-0.52 if summary has reached median
    if finite(t6.get("down_median")) and abs(t6["down_median"] + 0.52) > 0.15:
        # keep summary value; task said -0.52 for reached
        pass
    t7 = summarize_t7(flights, results)
    write_csvs(t7["reached"], t7["attempts"])
    payload = write_report(flights, head, t5, t6, t7, results)
    print(json.dumps({
        "status": payload["status"],
        "n_fixtures": t7["n_fixtures"],
        "n_reached": t7["n_reached"],
        "histogram_reached": t7["histogram_reached"],
        "corridor_frac": t7["corridor_frac"],
        "down_median": t7["down_median"],
        "gates_passed_sum": t7["gates_passed_sum"],
        "gate_clips_sum": t7["gate_clips_sum"],
        "n_clip_budget_aborts": t7["n_clip_budget_aborts"],
        "dominant_near_miss": t7["dominant_near_miss"],
        "questions": payload["questions"],
        "next_lever": payload["next_lever"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
