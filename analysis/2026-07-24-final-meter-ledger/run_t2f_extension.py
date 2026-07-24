"""T2f final-meter ledger extension — same §4-5 spec + impossibility audit.

Discovers fixtures/*t2f*, runs the final-meter ledger on every stall
(gates_passed == 0), and answers:

  Did any withdrawal happen with believed s in [-0.9, -0.4] or on
  evidence older than 0.3 s? (should be IMPOSSIBLE under T2f patches
  geom_term_z_m=-0.9, geom_term_fresh_s=0.3)

  What A–D class are the residual stalls?

Run from repository root:
  C:/Users/tsion/Projects/eni_dcim/.venv/Scripts/python.exe \\
    analysis/2026-07-24-final-meter-ledger/run_t2f_extension.py

If no t2f fixtures are present, writes WAITING status and exits 2.
"""
from __future__ import annotations

import importlib.util
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "t2f"
LEDGER_SCRIPT = Path(__file__).resolve().parent / "run_final_meter_ledger.py"

# T2f block patches (COMPETITION_PLAN predictions).
GEOM_TERM_Z_BLOCK = -0.9
GEOM_TERM_FRESH_BLOCK = 0.3
IMPOSSIBLE_S_LO = -0.9
IMPOSSIBLE_S_HI = -0.4  # inclusive band where class-A phantom retreats lived


def load_ledger():
    spec = importlib.util.spec_from_file_location("final_meter_ledger", LEDGER_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def finite(x):
    return isinstance(x, (int, float)) and math.isfinite(x)


def discover_t2f_fixtures(root: Path) -> list[Path]:
    """Prefer github fixtures/; also scan sibling eni_dcim/fixtures for local runs."""
    github_fix = root / "fixtures"
    roots = [github_fix]
    sibling = root.parent / "eni_dcim" / "fixtures"
    if sibling.is_dir() and sibling.resolve() != github_fix.resolve():
        roots.append(sibling)
    by_name: dict[str, Path] = {}
    for fix in roots:
        if not fix.is_dir():
            continue
        for p in sorted(fix.iterdir()):
            if not p.is_dir() or not re.search(r"t2f", p.name, re.IGNORECASE):
                continue
            # Prefer a copy under the analysis repo when both exist.
            if p.name in by_name and fix != github_fix:
                continue
            by_name[p.name] = p
            if (github_fix / p.name).is_dir():
                by_name[p.name] = github_fix / p.name
    return sorted(by_name.values(), key=lambda p: p.name)


def gates_passed(folder: Path) -> int | None:
    for name in ("result.json", "run-summary.json"):
        path = folder / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if "gates_passed" in data and isinstance(data["gates_passed"], (int, float)):
            return int(data["gates_passed"])
        # nested variants
        for key in ("result", "summary"):
            nested = data.get(key) if isinstance(data, dict) else None
            if isinstance(nested, dict) and "gates_passed" in nested:
                return int(nested["gates_passed"])
    return None


def read_geom_params(folder: Path) -> dict:
    path = folder / "params.json"
    out = {
        "geom_term_z_m": None,
        "geom_term_fresh_s": None,
        "patches_look_like_t2f": False,
    }
    if not path.is_file():
        return out
    try:
        params = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return out
    commit = (params.get("planner") or {}).get("commit") or {}
    z = commit.get("geom_term_z_m")
    fresh = commit.get("geom_term_fresh_s")
    out["geom_term_z_m"] = z
    out["geom_term_fresh_s"] = fresh
    # Accept float equality within 1e-6, or missing defaults (not T2f).
    if finite(z) and finite(fresh):
        out["patches_look_like_t2f"] = (
            abs(float(z) - GEOM_TERM_Z_BLOCK) < 1e-6
            and abs(float(fresh) - GEOM_TERM_FRESH_BLOCK) < 1e-6
        )
    return out


def withdrawal_events(ledger: list[dict]) -> list[dict]:
    """Every commit→retreat/recover transition with s and age at the edge."""
    events = []
    for i, tick in enumerate(ledger):
        phase = str(tick.get("phase") or "").lower()
        if phase not in {"retreat", "recover"}:
            continue
        prev = ledger[i - 1] if i > 0 else None
        prev_phase = str(prev.get("phase") or "").lower() if prev else ""
        if prev_phase not in {"commit", "align", "approach"} and i > 0:
            # only count first entry into retreat/recover from approach family
            if prev_phase in {"retreat", "recover"}:
                continue
        s = tick.get("signed_plane_m")
        if s is None and prev is not None:
            s = prev.get("signed_plane_m")
        age = tick.get("gate_rel_age_s")
        if age is None and prev is not None:
            age = prev.get("gate_rel_age_s")
        in_band = finite(s) and IMPOSSIBLE_S_LO <= s <= IMPOSSIBLE_S_HI
        stale = finite(age) and age > GEOM_TERM_FRESH_BLOCK
        events.append({
            "t_rel_s": round((tick["mono"] - ledger[0]["mono"]) / 1e9, 4),
            "from_phase": prev_phase or None,
            "to_phase": phase,
            "signed_plane_m": s,
            "gate_rel_age_s": age,
            "impossible_s_band": bool(in_band),
            "impossible_stale_gt_0_3": bool(stale),
            "impossible": bool(in_band or stale),
        })
    return events


def analyze_fixture(mod, folder: Path) -> dict:
    try:
        rel = str(folder.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        rel = str(folder)
    gp = gates_passed(folder)
    geom = read_geom_params(folder)
    cohort = "PASS" if (gp is not None and gp > 0) else "STALL"
    case = folder.name
    # shorten case id
    m = re.search(r"(t2f[^/\\]*)", case, re.IGNORECASE)
    case_id = m.group(1) if m else case

    rows = mod.load(folder)
    params = json.loads((folder / "params.json").read_text(encoding="utf-8"))
    ticks, _topics, passes = mod.make_ticks(rows, params)
    approaches = []
    n = 0
    for start, end in mod.segments(ticks):
        ledger = mod.slice_ledger(ticks, start, end, passes, params)
        if not ledger:
            continue
        n += 1
        traces = mod.trace_rows(ledger)
        met = mod.metrics(ledger, traces, passes)
        classification, rationale = mod.classify(cohort, ledger, met)
        wd = withdrawal_events(ledger)
        suffix = f"{case_id}_approach{n}"
        mod.csv_write(OUT / f"ledger_{suffix}.csv", mod.LEDGER_COLUMNS, mod.ledger_rows(ledger))
        mod.csv_write(OUT / f"paired_traces_{suffix}.csv", mod.TRACE_COLUMNS, traces)
        approaches.append({
            "case": case_id,
            "fixture": rel,
            "approach": n,
            "cohort": cohort,
            "gates_passed_flight": gp,
            "ticks": len(ledger),
            "classification": classification,
            "classification_rationale": rationale,
            "metrics": met,
            "proxy_exit_cause": ledger[-1]["proxy_exit_cause"],
            "withdrawals": wd,
            "n_impossible_withdrawals": sum(1 for e in wd if e["impossible"]),
            "n_impossible_s_band": sum(1 for e in wd if e["impossible_s_band"]),
            "n_impossible_stale": sum(1 for e in wd if e["impossible_stale_gt_0_3"]),
        })
    return {
        "case": case_id,
        "fixture": rel,
        "gates_passed": gp,
        "cohort": cohort,
        "geom_params": geom,
        "approaches": approaches,
    }


def write_waiting():
    OUT.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "WAITING",
        "reason": "no fixtures/*t2f* on disk; T2f implemented (bd84e79) but block not collected",
        "head_note": "re-run run_t2f_extension.py after [sim-run] t2f fixtures land",
        "impossibility_checks": {
            "s_band": [IMPOSSIBLE_S_LO, IMPOSSIBLE_S_HI],
            "stale_age_s": GEOM_TERM_FRESH_BLOCK,
        },
    }
    (OUT / "summary.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (OUT / "report.md").write_text(
        "\n".join([
            "# T2f final-meter ledger — WAITING",
            "",
            "No `fixtures/*t2f*` present on this checkout. T2f code/plan is on",
            "main (`geom_term_z_m` / `geom_term_fresh_s`); the 8-run block has",
            "not been pushed as sim-run fixtures yet.",
            "",
            "When fixtures land, re-run:",
            "",
            "```",
            "python analysis/2026-07-24-final-meter-ledger/run_t2f_extension.py",
            "```",
            "",
            "Audit (should be IMPOSSIBLE under T2f patches):",
            f"- withdrawal with believed s in [{IMPOSSIBLE_S_LO}, {IMPOSSIBLE_S_HI}]",
            f"- withdrawal on evidence older than {GEOM_TERM_FRESH_BLOCK} s",
            "",
            "Then classify residual stalls A/B/C/D per the parent ledger.",
            "",
        ]),
        encoding="utf-8",
    )


def write_report(flights: list[dict], head_sha: str | None):
    stalls = [f for f in flights if f["cohort"] == "STALL"]
    passes = [f for f in flights if f["cohort"] == "PASS"]
    all_approaches = [a for f in flights for a in f["approaches"]]
    stall_approaches = [a for a in all_approaches if a["cohort"] == "STALL"]
    n_imp = sum(a["n_impossible_withdrawals"] for a in all_approaches)
    n_band = sum(a["n_impossible_s_band"] for a in all_approaches)
    n_stale = sum(a["n_impossible_stale"] for a in all_approaches)

    lines = [
        "# T2f final-meter ledger — impossibility audit + residual classes",
        "",
        f"HEAD at analysis time: `{head_sha or 'unknown'}`.",
        f"Block coverage: **{len(flights)}/8** fixtures "
        f"({'COMPLETE' if len(flights) >= 8 else 'PARTIAL — re-run when remaining sim-runs land'}).",
        "",
        "## Questions",
        "",
        "1. Did any withdrawal happen with believed s in [-0.9, -0.4] or on",
        "   evidence older than 0.3s? *(should be IMPOSSIBLE under T2f)*",
        f"   → **{'YES — PREDICTION VIOLATED' if n_imp else 'NO — PREDICTION HELD'}** "
        f"(impossible events={n_imp}: s-band={n_band}, stale={n_stale}).",
        "",
        "2. What class are the residual stalls?",
        "",
    ]
    from collections import Counter
    census = Counter(a["classification"] for a in stall_approaches)
    if census:
        for cls, n in census.most_common():
            lines.append(f"   - **{cls}**: {n}")
    else:
        lines.append("   - *(no stall approaches)*")

    lines += [
        "",
        "Same §4–5 control-tick ledger as the parent directory,",
        "extended to every discovered T2f stall. Impossibility checks encode",
        "the T2f block prediction (COMPETITION_PLAN): no retreat on believed",
        f"s∈[{IMPOSSIBLE_S_LO},{IMPOSSIBLE_S_HI}] and none on evidence",
        f"older than {GEOM_TERM_FRESH_BLOCK}s.",
        "",
        "## Block summary",
        "",
        f"- Flights discovered: **{len(flights)}** "
        f"(stalls={len(stalls)}, passes={len(passes)})",
        f"- Stall approaches ledgered: **{len(stall_approaches)}**",
        f"- Impossible withdrawals (any): **{n_imp}** "
        f"(s-band={n_band}, stale={n_stale})",
        f"- Verdict: "
        + ("**PREDICTION VIOLATED** — impossible withdrawals observed."
           if n_imp else
           "**PREDICTION HELD** — no withdrawal in the forbidden band or on stale>0.3s evidence."),
        "",
        "## Per-flight geom patches",
        "",
        "| Fixture | gates | geom_term_z_m | geom_term_fresh_s | looks_like_t2f |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for f in flights:
        g = f["geom_params"]
        lines.append(
            f"| `{f['case']}` | {f['gates_passed']} | {g['geom_term_z_m']} | "
            f"{g['geom_term_fresh_s']} | {g['patches_look_like_t2f']} |"
        )

    lines += [
        "",
        "## Stall classifications",
        "",
        "| Fixture / approach | Class | s_ahead | ρ | impossible wd |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for a in stall_approaches:
        rho = a["metrics"]["tracking_ratio"]["mean_rho"]
        lines.append(
            f"| `{a['case']}` / {a['approach']} | **{a['classification']}** | "
            f"{a['metrics']['s_min_ahead_m']:.3f} | {rho} | "
            f"{a['n_impossible_withdrawals']} |"
        )
    if not stall_approaches:
        lines.append("| *(no stall approaches)* | — | — | — | — |")

    lines += [
        "",
        "## Withdrawal events (all approaches)",
        "",
    ]
    any_wd = False
    for a in all_approaches:
        for e in a["withdrawals"]:
            any_wd = True
            flag = "IMPOSSIBLE" if e["impossible"] else "ok"
            lines.append(
                f"- `{a['case']}` a{a['approach']} t={e['t_rel_s']:+.3f}s "
                f"{e['from_phase']}→{e['to_phase']} s={e['signed_plane_m']} "
                f"age={e['gate_rel_age_s']} → **{flag}**"
            )
    if not any_wd:
        lines.append("- *(no commit→retreat/recover edges in ledger windows)*")

    lines += [
        "",
        "## Artifacts",
        "",
        "- `ledger_*.csv` / `paired_traces_*.csv` — per stall/pass approach",
        "- `summary.json` — machine-readable audit",
        "- `run_t2f_extension.py` — this runner (also scans sibling eni_dcim/fixtures)",
        "",
    ]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    # clear prior outputs
    for pat in ("ledger_*.csv", "paired_traces_*.csv"):
        for path in OUT.glob(pat):
            path.unlink()

    fixtures = discover_t2f_fixtures(ROOT)
    if not fixtures:
        write_waiting()
        print(json.dumps({"status": "WAITING", "n_fixtures": 0}, indent=2))
        return 2

    mod = load_ledger()
    head_sha = None
    try:
        import subprocess
        head_sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        pass

    flights = [analyze_fixture(mod, folder) for folder in fixtures]
    stalls = [f for f in flights if f["cohort"] == "STALL"]
    all_approaches = [a for f in flights for a in f["approaches"]]
    stall_approaches = [a for a in all_approaches if a["cohort"] == "STALL"]
    n_imp = sum(a["n_impossible_withdrawals"] for a in all_approaches)

    payload = {
        "status": "COMPLETE" if len(fixtures) >= 8 else "PARTIAL",
        "n_fixtures_expected_block": 8,
        "head": head_sha,
        "n_fixtures": len(fixtures),
        "n_stall_flights": len(stalls),
        "n_stall_approaches": len(stall_approaches),
        "impossible_withdrawals_total": n_imp,
        "prediction_held": n_imp == 0,
        "impossibility_checks": {
            "s_band": [IMPOSSIBLE_S_LO, IMPOSSIBLE_S_HI],
            "stale_age_s": GEOM_TERM_FRESH_BLOCK,
        },
        "flights": flights,
        "residual_stall_classes": {
            a["case"] + f"/a{a['approach']}": a["classification"]
            for a in stall_approaches
        },
    }
    (OUT / "summary.json").write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    write_report(flights, head_sha)
    print(json.dumps({
        "status": "COMPLETE",
        "n_fixtures": len(fixtures),
        "n_stall_flights": len(stalls),
        "impossible_withdrawals_total": n_imp,
        "prediction_held": n_imp == 0,
        "residual_stall_classes": payload["residual_stall_classes"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
