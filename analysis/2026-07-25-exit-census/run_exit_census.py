"""T5 commit_exit census — which branch ends near-gate attempts.

Over all T5 fixtures (*t5* under fixtures/, also sibling eni_dcim/fixtures):
  (1) histogram of exit reasons for attempts that REACHED the gate
      (closest range < 2 m during the commit);
  (2) per exit: gate_rel_t (right/down/fwd) + age — believed pose at exit;
  (3) dominant exit cause among those near-misses.

Run:
  C:/Users/tsion/Projects/eni_dcim/.venv/Scripts/python.exe \\
    analysis/2026-07-25-exit-census/run_exit_census.py
"""
from __future__ import annotations

import csv
import json
import math
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
REACHED_M = 2.0
REASONS = (
    "pass", "stale_budget", "relock_jump", "geometric_behind",
    "term_abort", "corridor_abort", "timer_expired",
)


def finite(x):
    return isinstance(x, (int, float)) and math.isfinite(x)


def vec3(x):
    if not isinstance(x, (list, tuple)) or len(x) < 3:
        return None
    try:
        v = tuple(float(x[i]) for i in range(3))
    except (TypeError, ValueError):
        return None
    return v if all(math.isfinite(a) for a in v) else None


def norm(v):
    return math.sqrt(sum(a * a for a in v)) if v else None


def discover_t5(root: Path) -> list[Path]:
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
            if not re.search(r"t5", p.name, re.IGNORECASE):
                continue
            if (github / p.name).is_dir():
                by_name[p.name] = github / p.name
            elif p.name not in by_name:
                by_name[p.name] = p
    return sorted(by_name.values(), key=lambda p: p.name)


def flight_log(folder: Path) -> Path | None:
    hits = sorted(folder.glob("*flight.jsonl"))
    if hits:
        return hits[0]
    p = folder / "flight.jsonl"
    return p if p.is_file() else None


def gates_passed(folder: Path) -> int | None:
    for name in ("result.json", "run-summary.json"):
        path = folder / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data.get("gates_passed"), (int, float)):
            return int(data["gates_passed"])
    return None


def load_rows(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                row = json.loads(line)
                row["_mono"] = int(row["mono_ns"])
                rows.append(row)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue
    return sorted(rows, key=lambda r: r["_mono"])


def closest_before(exits_and_states, exit_mono: int, commit_start: int | None) -> dict:
    """Min range from state.gate_rel between commit_start and exit."""
    best = None
    for st in exits_and_states:
        if st["_mono"] > exit_mono:
            break
        if commit_start is not None and st["_mono"] < commit_start:
            continue
        t = vec3((st.get("data") or {}).get("gate_rel", {}).get("t")
                 if isinstance((st.get("data") or {}).get("gate_rel"), dict)
                 else None)
        if t is None:
            continue
        rng = norm(t)
        if rng is None:
            continue
        if best is None or rng < best["range_m"]:
            best = {
                "range_m": rng,
                "t": t,
                "mono": st["_mono"],
                "fwd_m": t[2],
            }
    return best or {}


def analyze_fixture(folder: Path) -> dict:
    log = flight_log(folder)
    if log is None:
        return {"fixture": str(folder), "error": "no flight.jsonl"}
    rows = load_rows(log)
    setpoints = [r for r in rows if r.get("topic") == "setpoint"]
    states = [r for r in rows if r.get("topic") == "state"]
    exits = [r for r in rows if r.get("topic") == "commit_exit"]

    # Commit windows: rising edges of phase==commit.
    commit_starts = []
    prev = None
    for sp in setpoints:
        phase = str((sp.get("data") or {}).get("phase") or "").lower()
        if phase == "commit" and prev != "commit":
            commit_starts.append(sp["_mono"])
        prev = phase

    attempts = []
    for i, ex in enumerate(exits):
        data = ex.get("data") or {}
        reason = data.get("reason")
        t = vec3(data.get("gate_rel_t"))
        age = data.get("gate_rel_age_s")
        # Associate the latest commit start before this exit.
        starts = [s for s in commit_starts if s <= ex["_mono"]]
        c0 = starts[-1] if starts else None
        # Next commit start bounds the window for closest.
        c1 = None
        later = [s for s in commit_starts if s > ex["_mono"]]
        # Closest during this commit: states from c0 to exit.
        closest = closest_before(states, ex["_mono"], c0)
        reached = bool(closest.get("range_m") is not None
                       and closest["range_m"] < REACHED_M)
        # Also treat exit-time range < 2m as reached if no state samples.
        exit_range = norm(t)
        if not reached and exit_range is not None and exit_range < REACHED_M:
            reached = True
            if not closest:
                closest = {"range_m": exit_range, "t": t, "fwd_m": t[2] if t else None}

        attempts.append({
            "fixture": folder.name,
            "attempt": i + 1,
            "mono_ns": ex["_mono"],
            "reason": reason,
            "gate_rel_t_right": t[0] if t else None,
            "gate_rel_t_down": t[1] if t else None,
            "gate_rel_t_fwd": t[2] if t else None,
            "gate_rel_age_s": age if finite(age) else None,
            "exit_range_m": exit_range,
            "closest_range_m": closest.get("range_m"),
            "closest_fwd_m": closest.get("fwd_m"),
            "reached_gate": reached,
            "commit_start_mono_ns": c0,
            "gates_passed_flight": gates_passed(folder),
        })
    return {
        "fixture": folder.name,
        "path": str(folder),
        "gates_passed": gates_passed(folder),
        "n_commit_exits": len(exits),
        "n_commit_starts": len(commit_starts),
        "attempts": attempts,
    }


def write_waiting(head: str | None):
    payload = {
        "status": "WAITING",
        "head": head,
        "reason": "no fixtures/*t5* with commit_exit yet; T5 registered at 1c8c83f",
    }
    (OUT / "summary.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (OUT / "report.md").write_text(
        "\n".join([
            "# T5 exit-reason census — WAITING",
            "",
            f"HEAD: `{head or 'unknown'}`.",
            "",
            "No `fixtures/*t5*` present (or no `commit_exit` records). Phase T5 is",
            "registered to fly the T4 config with `commit_exit` instrumentation;",
            "re-run this script after the 6-run block lands.",
            "",
            "Expected reasons: " + ", ".join(REASONS),
            "",
        ]),
        encoding="utf-8",
    )


def write_report(flights: list[dict], head: str | None):
    attempts = [a for f in flights for a in f.get("attempts", [])]
    reached = [a for a in attempts if a["reached_gate"]]
    near_miss = [a for a in reached if a["reason"] != "pass"]
    hist_all = Counter(a["reason"] for a in attempts)
    hist_reached = Counter(a["reason"] for a in reached)
    hist_miss = Counter(a["reason"] for a in near_miss)
    dominant = hist_miss.most_common(1)[0] if hist_miss else (None, 0)

    # CSV of every reached-gate exit
    fields = [
        "fixture", "attempt", "reason", "reached_gate",
        "gate_rel_t_right", "gate_rel_t_down", "gate_rel_t_fwd",
        "gate_rel_age_s", "exit_range_m", "closest_range_m", "closest_fwd_m",
        "gates_passed_flight",
    ]
    with (OUT / "reached_exits.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for a in reached:
            w.writerow(a)
    with (OUT / "all_exits.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for a in attempts:
            w.writerow(a)

    lines = [
        "# T5 exit-reason census",
        "",
        f"HEAD: `{head or 'unknown'}`.",
        f"Fixtures: **{len(flights)}**. Commit exits: **{len(attempts)}**. "
        f"Reached-gate (closest < {REACHED_M:g} m): **{len(reached)}**. "
        f"Near-misses (reached ∧ reason≠pass): **{len(near_miss)}**.",
        "",
        "## (1) Exit-reason histogram — reached-gate attempts",
        "",
        "| reason | n_reached | n_all |",
        "| --- | ---: | ---: |",
    ]
    for reason in REASONS:
        lines.append(
            f"| `{reason}` | {hist_reached.get(reason, 0)} | {hist_all.get(reason, 0)} |"
        )
    other = set(hist_all) - set(REASONS)
    for reason in sorted(other):
        lines.append(
            f"| `{reason}` | {hist_reached.get(reason, 0)} | {hist_all.get(reason, 0)} |"
        )

    lines += [
        "",
        "## (3) Dominant near-miss exit cause",
        "",
    ]
    if dominant[0] is None:
        lines.append("No reached-gate non-pass exits in the block.")
    else:
        lines.append(
            f"**`{dominant[0]}`** — {dominant[1]}/{len(near_miss)} near-misses "
            f"({100.0 * dominant[1] / len(near_miss):.0f}%)."
        )
        # Geometry summary for dominant
        dom_rows = [a for a in near_miss if a["reason"] == dominant[0]]
        fwds = [a["gate_rel_t_fwd"] for a in dom_rows if finite(a["gate_rel_t_fwd"])]
        ages = [a["gate_rel_age_s"] for a in dom_rows if finite(a["gate_rel_age_s"])]
        rights = [a["gate_rel_t_right"] for a in dom_rows if finite(a["gate_rel_t_right"])]
        downs = [a["gate_rel_t_down"] for a in dom_rows if finite(a["gate_rel_t_down"])]
        if fwds:
            lines.append(
                f"At exit (believed): fwd median={sorted(fwds)[len(fwds)//2]:.3f} m, "
                f"range [{min(fwds):.3f}, {max(fwds):.3f}]; "
                f"right median={sorted(rights)[len(rights)//2]:.3f} m; "
                f"down median={sorted(downs)[len(downs)//2]:.3f} m; "
                f"age median={sorted(ages)[len(ages)//2]:.3f} s."
                if rights and downs and ages else
                f"At exit (believed): fwd [{min(fwds):.3f}, {max(fwds):.3f}] m."
            )

    lines += [
        "",
        "## (2) Per-exit believed geometry (reached-gate)",
        "",
        "| fixture | # | reason | right | down | fwd | age_s | closest_m |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for a in reached:
        lines.append(
            f"| `{a['fixture']}` | {a['attempt']} | `{a['reason']}` | "
            f"{_fmt(a['gate_rel_t_right'])} | {_fmt(a['gate_rel_t_down'])} | "
            f"{_fmt(a['gate_rel_t_fwd'])} | {_fmt(a['gate_rel_age_s'])} | "
            f"{_fmt(a['closest_range_m'])} |"
        )
    if not reached:
        lines.append("| *(none)* | | | | | | | |")

    lines += [
        "",
        "## Per-fixture",
        "",
        "| fixture | gates | n_exits | n_reached |",
        "| --- | ---: | ---: | ---: |",
    ]
    for f in flights:
        n_r = sum(1 for a in f.get("attempts", []) if a["reached_gate"])
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
        "- `run_exit_census.py`",
        "",
        "Note: `gate_rel_t` is the *believed* camera-frame pose at exit",
        "(right/down/fwd). True-world reconstruction is not in the",
        "`commit_exit` record; age is the freshness of that believed pose.",
        "",
    ]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    payload = {
        "status": "COMPLETE",
        "head": head,
        "n_fixtures": len(flights),
        "n_exits": len(attempts),
        "n_reached": len(reached),
        "n_near_miss": len(near_miss),
        "histogram_reached": dict(hist_reached),
        "histogram_all": dict(hist_all),
        "dominant_near_miss_reason": dominant[0],
        "dominant_near_miss_count": dominant[1],
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
    (OUT / "summary.json").write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return payload


def _fmt(x):
    if x is None or not finite(x):
        return "—"
    return f"{x:.3f}"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    head = None
    try:
        head = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        pass

    fixtures = discover_t5(ROOT)
    if not fixtures:
        write_waiting(head)
        print(json.dumps({"status": "WAITING", "n_fixtures": 0, "head": head}, indent=2))
        return 2

    flights = []
    for folder in fixtures:
        info = analyze_fixture(folder)
        if info.get("error"):
            continue
        # Skip fixtures with zero commit_exit (wrong build).
        if info.get("n_commit_exits", 0) == 0:
            info["warning"] = "no commit_exit records"
        flights.append(info)

    if not any(f.get("n_commit_exits", 0) > 0 for f in flights):
        write_waiting(head)
        print(json.dumps({
            "status": "WAITING",
            "n_fixtures": len(fixtures),
            "n_with_commit_exit": 0,
            "head": head,
            "note": "t5 dirs present but no commit_exit topic yet",
        }, indent=2))
        return 2

    payload = write_report(flights, head)
    print(json.dumps({
        "status": payload["status"],
        "n_fixtures": payload["n_fixtures"],
        "n_exits": payload["n_exits"],
        "n_reached": payload["n_reached"],
        "histogram_reached": payload["histogram_reached"],
        "dominant_near_miss_reason": payload["dominant_near_miss_reason"],
        "dominant_near_miss_count": payload["dominant_near_miss_count"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
