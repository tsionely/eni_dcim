"""P1 — Phantom-crossing reclassification on the phase6h 47-flight rescue set.

Question: of the 44 env-collision deaths, how many began with a
first-commit abort where geometric termination (gate.t[2] < -0.4) fired
with gate_rel_age_s > 0.6? That is the stale dead-reckoned "crossing"
that 8596c24 now refuses.
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
FIX = ROOT / "fixtures" / "20260719T164956-phase6h-first-enable"
LOGS = [
    Path(r"C:\Users\tsion\Projects\eni_dcim\logs"),
    ROOT / "logs",
]
AGE_THRESH = 0.6
TZ_CROSS = -0.4


def resolve_log(fid: str) -> Path | None:
    for root in LOGS:
        p = root / fid / "flight.jsonl"
        if p.exists():
            return p
    # fixture flat copies
    p = FIX / f"{fid}-flight.jsonl"
    return p if p.exists() else None


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


def finite(x) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def analyze_flight(fid: str, meta: dict) -> dict:
    path = resolve_log(fid)
    out = {
        "fid": fid,
        "reason": meta.get("reason"),
        "gates": meta.get("gates"),
        "clips": meta.get("clips"),
        "env_hits": meta.get("env_hits"),
        "duration_s": meta.get("duration_s"),
        "log": str(path) if path else None,
        "is_env_death": "environment collision" in str(meta.get("reason") or ""),
        "phantom_first_commit": False,
    }
    if path is None:
        out["error"] = "log_not_found"
        return out

    rows = load_jsonl(path)
    toff = takeoff_mono(rows)
    # Merge state + setpoint by time
    events = []
    for r in rows:
        topic = r.get("topic")
        if topic not in ("state", "setpoint", "collision", "fsm"):
            continue
        t_ff = (int(r["mono_ns"]) - toff) / 1e9
        events.append((t_ff, topic, r["data"]))
    events.sort(key=lambda e: e[0])

    # Find first commit window
    phase = None
    commit_i = 0
    first_commit_start = None
    first_commit_end = None
    for t_ff, topic, d in events:
        if topic != "setpoint":
            continue
        ph = d.get("phase")
        if ph == "commit" and phase != "commit":
            commit_i += 1
            if commit_i == 1:
                first_commit_start = t_ff
        if commit_i == 1 and phase == "commit" and ph != "commit":
            first_commit_end = t_ff
            break
        phase = ph
    if first_commit_start is None:
        out["error"] = "no_commit"
        return out
    if first_commit_end is None:
        first_commit_end = events[-1][0]

    # Within first commit: look for tz < -0.4 with age > 0.6
    phantom = None
    fresh_cross = None
    min_R = None
    last_state = None
    for t_ff, topic, d in events:
        if t_ff < first_commit_start - 0.01:
            continue
        if t_ff > first_commit_end + 0.05:
            break
        if topic == "state":
            last_state = (t_ff, d)
            gr = d.get("gate_rel")
            if gr is None:
                continue
            t = gr["t"]
            R = float(np.linalg.norm(t))
            age = finite(d.get("gate_rel_age_s"))
            if min_R is None or R < min_R[0]:
                min_R = (R, t_ff, age, list(map(float, t)))
            if float(t[2]) < TZ_CROSS:
                rec = {
                    "t_ff": t_ff,
                    "tz": float(t[2]),
                    "R": R,
                    "age": age,
                    "t_vec": list(map(float, t)),
                }
                if age is not None and age > AGE_THRESH:
                    if phantom is None:
                        phantom = rec
                else:
                    if fresh_cross is None:
                        fresh_cross = rec

    # How did first commit end?
    end_phase = None
    for t_ff, topic, d in events:
        if topic != "setpoint":
            continue
        if first_commit_end - 0.05 <= t_ff <= first_commit_end + 0.2:
            if d.get("phase") != "commit":
                end_phase = d.get("phase")
                break

    # Subsequent death mode
    death_mode = "unknown"
    reason = str(meta.get("reason") or "")
    if "environment collision" in reason:
        death_mode = "env_collision"
    elif "gate clip" in reason:
        death_mode = "gate_clip_budget"
    if meta.get("gates", 0) and meta.get("gates", 0) >= 1:
        death_mode = "pass_then_" + death_mode

    # Collisions after first commit
    post_coll = []
    for t_ff, topic, d in events:
        if topic != "collision" or t_ff < first_commit_start:
            continue
        post_coll.append({
            "t_ff": t_ff,
            "impulse": d.get("impulse"),
            "threat": d.get("threat_level"),
        })

    out.update({
        "first_commit_start_ff": first_commit_start,
        "first_commit_end_ff": first_commit_end,
        "first_commit_dur_s": first_commit_end - first_commit_start,
        "first_commit_end_phase": end_phase,
        "closest_in_first_commit": (
            {"R": min_R[0], "t_ff": min_R[1], "age": min_R[2], "t_vec": min_R[3]}
            if min_R else None),
        "phantom_termination": phantom,
        "fresh_cross_termination": fresh_cross,
        "phantom_first_commit": phantom is not None,
        "abort_range_m": phantom["R"] if phantom else (
            min_R[0] if min_R else None),
        "believed_age_at_termination": (
            phantom["age"] if phantom else None),
        "death_mode": death_mode,
        "n_collisions_after_commit_start": len(post_coll),
        "first_post_collision": post_coll[0] if post_coll else None,
    })
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    summary = json.loads((FIX / "summary.json").read_text(encoding="utf-8"))
    attempts = summary["all_attempts"]
    env = [a for a in attempts
           if "environment collision" in str(a.get("reason") or "")]
    results = []
    for a in attempts:
        print(f"  {a['fid']}", flush=True)
        results.append(analyze_flight(a["fid"], a))

    env_results = [r for r in results if r.get("is_env_death")]
    phantoms = [r for r in env_results if r.get("phantom_first_commit")]
    missing = [r for r in results if r.get("error")]

    bundle = {
        "n_attempts": len(attempts),
        "n_env_deaths": len(env_results),
        "n_phantom_first_commit": len(phantoms),
        "fraction_of_env": (
            len(phantoms) / len(env_results) if env_results else None),
        "age_thresh_s": AGE_THRESH,
        "tz_cross": TZ_CROSS,
        "fix_sizes": "8596c24 requires age <= entry_max_age_s for geometric term",
        "missing_logs": [r["fid"] for r in missing],
        "phantom_flights": phantoms,
        "all": results,
    }

    (OUT / "summary.json").write_text(
        json.dumps(bundle, indent=2, default=str), encoding="utf-8")

    with (OUT / "per_flight.csv").open("w", newline="", encoding="utf-8") as f:
        fields = [
            "fid", "is_env_death", "phantom_first_commit", "abort_range_m",
            "believed_age_at_termination", "tz_at_term",
            "first_commit_dur_s", "closest_R", "death_mode",
            "end_phase", "reason", "error",
        ]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in results:
            ph = r.get("phantom_termination") or {}
            cl = r.get("closest_in_first_commit") or {}
            w.writerow({
                "fid": r["fid"],
                "is_env_death": r.get("is_env_death"),
                "phantom_first_commit": r.get("phantom_first_commit"),
                "abort_range_m": r.get("abort_range_m"),
                "believed_age_at_termination": r.get("believed_age_at_termination"),
                "tz_at_term": ph.get("tz"),
                "first_commit_dur_s": r.get("first_commit_dur_s"),
                "closest_R": cl.get("R"),
                "death_mode": r.get("death_mode"),
                "end_phase": r.get("first_commit_end_phase"),
                "reason": r.get("reason"),
                "error": r.get("error"),
            })

    report = render(bundle)
    (OUT / "phantom-crossing.md").write_text(report, encoding="utf-8")
    (ROOT / "analysis" / "2026-07-20-phantom-crossing.md").write_text(
        report, encoding="utf-8")
    print(json.dumps({
        "n_env_deaths": bundle["n_env_deaths"],
        "n_phantom_first_commit": bundle["n_phantom_first_commit"],
        "fraction": bundle["fraction_of_env"],
        "missing": len(missing),
    }, indent=2))
    return 0


def render(b: dict) -> str:
    lines = [
        "# Phantom-crossing reclassification — phase6h 47-flight rescue set",
        "",
        "Context: commit `8596c24` — geometric termination now requires "
        f"`gate_rel_age_s <= entry_max_age_s` (~{b['age_thresh_s']}s). "
        "This report sizes how many of the 44 env-collision deaths began "
        "with the stale phantom-crossing abort the fix refuses.",
        "",
        "## Verdict",
        "",
        f"- Env-collision deaths: **{b['n_env_deaths']}** / {b['n_attempts']}",
        f"- Phantom first-commit abort "
        f"(tz < {b['tz_cross']} ∧ age > {b['age_thresh_s']}s): "
        f"**{b['n_phantom_first_commit']}**",
        f"- Fraction of env deaths: "
        f"**{100*(b['fraction_of_env'] or 0):.1f}%**",
        f"- Missing logs: {len(b['missing_logs'])}",
        "",
        "## Per-flight table (phantom cases)",
        "",
        "| fid | abort R | age@term | tz | commit dur | closest R | end→ | death |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for r in b["phantom_flights"]:
        ph = r.get("phantom_termination") or {}
        cl = r.get("closest_in_first_commit") or {}
        def _f(x, nd=2):
            return "" if x is None else f"{float(x):.{nd}f}"
        lines.append(
            f"| `{r['fid']}` | {_f(r.get('abort_range_m'))} | "
            f"{_f(r.get('believed_age_at_termination'))} | "
            f"{_f(ph.get('tz'))} | {_f(r.get('first_commit_dur_s'))} | "
            f"{_f(cl.get('R'))} | {r.get('first_commit_end_phase')} | "
            f"{r.get('death_mode')} |"
        )
    if not b["phantom_flights"]:
        lines.append("| — | — | — | — | — | — | — | — |")
    lines += [
        "",
        "## All env deaths (compact)",
        "",
        "| fid | phantom? | abort R | age | closest R | death_mode |",
        "|---|---|---:|---:|---:|---|",
    ]
    lines = lines[:lines.index("## All env deaths (compact)")]
    lines += [
        "## All env deaths (compact)",
        "",
        "| fid | phantom? | abort R | age | closest R | death_mode |",
        "|---|---|---:|---:|---:|---|",
    ]
    for r in b["all"]:
        if not r.get("is_env_death"):
            continue
        ar = r.get("abort_range_m")
        ag = r.get("believed_age_at_termination")
        cl = r.get("closest_in_first_commit") or {}
        ar_s = "" if ar is None else f"{ar:.2f}"
        ag_s = "" if ag is None else f"{ag:.2f}"
        cl_s = "" if cl.get("R") is None else f"{cl['R']:.2f}"
        lines.append(
            f"| `{r['fid']}` | {r.get('phantom_first_commit')} | "
            f"{ar_s} | {ag_s} | {cl_s} | {r.get('death_mode')} |"
        )
    lines += [
        "",
        "## Implication",
        "",
        f"The shipped freshness gate on geometric termination "
        f"(age ≤ {b['age_thresh_s']}s) would have blocked "
        f"**{b['n_phantom_first_commit']}** first-commit phantom aborts "
        f"in this rescue set. Those flights then entered the post-abort "
        f"churn that ends in env collision — the fix sizes to that count.",
        "",
        "## Deliverables",
        "",
        "- `phantom-crossing.md`, `summary.json`, `per_flight.csv`",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
