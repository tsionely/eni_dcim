"""PHASE-WIRE blast radius � tau-at-TERM retro audit (RESPONSE34 �3)."""
from __future__ import annotations

import bisect
import csv
import json
import subprocess
import math
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from aigp.planning.vertical_terminal import guidance_phase  # noqa: E402

POSITION_UNTIL_S = 0.45
GAP_S = 0.5
MIN_RANGE = 0.05
MIN_SPEED = 0.5

SEARCH_ROOTS: list[Path] = [
    ROOT / "fixtures",
    ROOT / "tuning",
    Path(r"C:\Users\tsion\Projects\eni_dcim\fixtures"),
    Path(r"C:\Users\tsion\Projects\eni_dcim_qa\tuning\runtime-logs"),
    Path(r"C:\Users\tsion\Projects\eni_dcim\logs"),
]


def discover_flight_logs() -> list[Path]:
    seen: set[str] = set()
    out: list[Path] = []
    for base in SEARCH_ROOTS:
        if not base.is_dir():
            continue
        for p in base.rglob("*flight.jsonl"):
            key = str(p.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(p)
    return sorted(out)


def discover_shadow_csvs() -> list[Path]:
    seen: set[str] = set()
    out: list[Path] = []
    for base in [ROOT / "tuning", ROOT / "analysis"]:
        if not base.is_dir():
            continue
        for p in base.rglob("*.csv"):
            try:
                with p.open(newline="", encoding="utf-8") as f:
                    row = f.readline()
                if "shadow_owner" not in row:
                    continue
            except OSError:
                continue
            key = str(p.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(p)
    return sorted(out)


def flight_key_from_path(p: Path) -> str:
    name = p.name
    if name.endswith("-flight.jsonl"):
        return name[: -len("-flight.jsonl")]
    return p.stem


def nearest_idx(sorted_mono: list[int], target: int) -> int | None:
    if not sorted_mono:
        return None
    i = bisect.bisect_left(sorted_mono, target)
    if i == 0:
        return 0
    if i >= len(sorted_mono):
        return len(sorted_mono) - 1
    if abs(sorted_mono[i] - target) < abs(sorted_mono[i - 1] - target):
        return i
    return i - 1


def tau_from_gate_vbody(gate_rel: dict | None, v_body: list[float] | None) -> float | None:
    if not gate_rel or not v_body:
        return None
    t = gate_rel.get("t")
    if not t or len(t) < 3:
        return None
    rz = max(float(t[2]), MIN_RANGE)
    spd = max(math.hypot(float(v_body[0]), float(v_body[1])), MIN_SPEED)
    return rz / spd


def tau_from_range_speed(range_z_m: float | None, speed_xy: float | None) -> float | None:
    if range_z_m is None or speed_xy is None:
        return None
    try:
        rz = max(float(range_z_m), MIN_RANGE)
        spd = max(float(speed_xy), MIN_SPEED)
    except (TypeError, ValueError):
        return None
    return rz / spd


def percentiles(values: list[float], ps: tuple[float, ...]) -> dict[str, float]:
    if not values:
        return {f"p{int(p)}": None for p in ps}
    s = sorted(values)
    out: dict[str, float] = {}
    for p in ps:
        k = (len(s) - 1) * (p / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            out[f"p{int(p)}"] = s[int(k)]
        else:
            out[f"p{int(p)}"] = s[f] * (c - k) + s[c] * (k - f)
    return out


@dataclass
class TermTick:
    source: str  # live | replay
    flight_key: str
    path: str
    mono_ns: int
    t_rel_s: float | None
    tau_s: float | None
    owner: str
    guidance_phase: str | None
    engaged: bool | None = None
    shadow_capture: bool | None = None
    is_first_capture: bool = False


@dataclass
class Episode:
    source: str
    flight_key: str
    path: str
    start_mono_ns: int
    end_mono_ns: int
    n_ticks: int
    tau_min: float | None
    tau_first: float | None
    any_tau_le_threshold: bool
    first_capture_tau_le_threshold: bool
    handback_tau_le_threshold: int = 0


def load_mono_index(path: Path) -> tuple[list[int], list[dict], list[int], list[dict]]:
    state_mono: list[int] = []
    states: list[dict] = []
    sp_mono: list[int] = []
    setpoints: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            topic = o.get("topic")
            mono = o.get("mono_ns")
            if mono is None:
                continue
            if topic == "state":
                state_mono.append(int(mono))
                states.append(o.get("data") or {})
            elif topic == "setpoint":
                sp_mono.append(int(mono))
                setpoints.append(o.get("data") or {})
    return state_mono, states, sp_mono, setpoints


def log_contains_term_owner(path: Path) -> bool:
    with path.open("rb") as f:
        for line in f:
            if b'"owner": "term"' in line and b"term_status" in line:
                return True
    return False


def mine_flight_log(path: Path, ticks: list[TermTick], row_keys: set[tuple], handbacks: list[dict] | None = None) -> None:
    if not log_contains_term_owner(path):
        return
    fk = flight_key_from_path(path)
    sm, states, spm, sps = load_mono_index(path)
    prev_owner: str | None = None
    t0_mono: int | None = None
    with path.open(encoding="utf-8") as f:
        for line in f:
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            if o.get("topic") != "term_status":
                continue
            data = o.get("data") or {}
            owner = data.get("owner")
            mono = int(o["mono_ns"])
            si = nearest_idx(sm, mono)
            pi = nearest_idx(spm, mono)
            gate_rel = states[si].get("gate_rel") if si is not None else None
            v_body = sps[pi].get("v_body") if pi is not None else None
            tau_h = data.get("tau_s")
            if tau_h is not None:
                tau_h = float(tau_h)
            else:
                tau_h = tau_from_gate_vbody(gate_rel, v_body)
            if handbacks is not None and prev_owner == "term" and owner == "alt":
                handbacks.append(
                    {
                        "flight_key": fk,
                        "path": str(path),
                        "mono_ns": mono,
                        "tau_s": tau_h,
                        "tau_le_threshold": tau_h is not None and tau_h <= POSITION_UNTIL_S,
                    }
                )
            if owner != "term":
                prev_owner = owner
                continue
            key = (fk, mono, "live")
            if key in row_keys:
                prev_owner = owner
                continue
            row_keys.add(key)

            tau = tau_h
            first_cap = prev_owner != "term"

            if t0_mono is None:
                t0_mono = mono
            t_rel = (mono - t0_mono) / 1e9 if t0_mono is not None else None

            phase = guidance_phase(tau, None) if tau is not None else None
            ticks.append(
                TermTick(
                    source="live",
                    flight_key=fk,
                    path=str(path),
                    mono_ns=mono,
                    t_rel_s=t_rel,
                    tau_s=tau,
                    owner=owner,
                    guidance_phase=phase,
                    engaged=data.get("engaged"),
                    is_first_capture=first_cap,
                )
            )
            prev_owner = owner


def mine_shadow_csv(path: Path, ticks: list[TermTick], row_keys: set[tuple]) -> None:
    prev_owner_by_flight: dict[str, str | None] = {}
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            owner = row.get("shadow_owner") or ""
            fk = str(row.get("flight_id") or row.get("flight") or path.stem)
            prev_owner = prev_owner_by_flight.get(fk)
            prev_owner_by_flight[fk] = owner
            if owner != "term":
                continue
            mono_s = row.get("mono_ns") or row.get("feature_ts_ns") or "0"
            try:
                mono = int(float(mono_s))
            except ValueError:
                mono = hash((fk, row.get("frame_id"), row.get("t_rel_s"))) & ((1 << 62) - 1)
            simple = (fk, mono, "replay")
            if simple in row_keys:
                continue
            row_keys.add(simple)

            t_rel = None
            if row.get("t_rel_s"):
                try:
                    t_rel = float(row["t_rel_s"])
                except ValueError:
                    t_rel = None

            tau = tau_from_range_speed(
                _float_or_none(row.get("range_z_m")),
                _float_or_none(row.get("setpoint_speed_xy_mps")),
            )
            phase = guidance_phase(tau, None) if tau is not None else None
            cap = row.get("shadow_capture", "").lower() in ("true", "1", "yes")
            first_cap = prev_owner != "term"
            ticks.append(
                TermTick(
                    source="replay",
                    flight_key=fk,
                    path=str(path),
                    mono_ns=mono,
                    t_rel_s=t_rel,
                    tau_s=tau,
                    owner="term",
                    guidance_phase=phase,
                    shadow_capture=cap,
                    is_first_capture=first_cap,
                )
            )


def _float_or_none(s: str | None) -> float | None:
    if s is None or s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def build_episodes(ticks: list[TermTick]) -> list[Episode]:
    episodes: list[Episode] = []
    by_flight: dict[tuple[str, str], list[TermTick]] = {}
    for t in ticks:
        by_flight.setdefault((t.source, t.flight_key), []).append(t)
    for (source, fk), rows in by_flight.items():
        rows.sort(key=lambda r: r.mono_ns)
        prev_mono: int | None = None
        prev_owner: str | None = None
        buf: list[TermTick] = []
        path = rows[0].path if rows else ""

        def flush() -> None:
            nonlocal buf
            if not buf:
                return
            taus = [x.tau_s for x in buf if x.tau_s is not None]
            tau_first = buf[0].tau_s
            tau_min = min(taus) if taus else None
            any_le = any(t is not None and t <= POSITION_UNTIL_S for t in taus)
            first_le = (
                buf[0].is_first_capture
                and tau_first is not None
                and tau_first <= POSITION_UNTIL_S
            )
            handbacks = 0
            for i in range(1, len(buf)):
                # within episode all term-owned; handback is end of episode
                pass
            episodes.append(
                Episode(
                    source=source,
                    flight_key=fk,
                    path=path,
                    start_mono_ns=buf[0].mono_ns,
                    end_mono_ns=buf[-1].mono_ns,
                    n_ticks=len(buf),
                    tau_min=tau_min,
                    tau_first=tau_first,
                    any_tau_le_threshold=any_le,
                    first_capture_tau_le_threshold=first_le,
                    handback_tau_le_threshold=handbacks,
                )
            )
            buf = []

        for row in rows:
            gap = prev_mono is not None and (row.mono_ns - prev_mono) / 1e9 > GAP_S
            if gap and buf:
                flush()
            buf.append(row)
            prev_mono = row.mono_ns
        flush()

    # handbacks: scan full term/alt timeline per live flight log
    return episodes


def scan_handbacks_live_unused(log_paths: list[Path]) -> list[dict]:
    events: list[dict] = []
    for path in log_paths:
        fk = flight_key_from_path(path)
        sm, states, spm, sps = load_mono_index(path)
        prev_owner: str | None = None
        prev_mono: int | None = None
        with path.open(encoding="utf-8") as f:
            for line in f:
                try:
                    o = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if o.get("topic") != "term_status":
                    continue
                data = o.get("data") or {}
                owner = data.get("owner")
                mono = int(o["mono_ns"])
                si = nearest_idx(sm, mono)
                pi = nearest_idx(spm, mono)
                tau = data.get("tau_s")
                if tau is None:
                    gate_rel = states[si].get("gate_rel") if si is not None else None
                    v_body = sps[pi].get("v_body") if pi is not None else None
                    tau = tau_from_gate_vbody(gate_rel, v_body)
                if prev_owner == "term" and owner == "alt":
                    events.append(
                        {
                            "flight_key": fk,
                            "path": str(path),
                            "mono_ns": mono,
                            "tau_s": tau,
                            "tau_le_threshold": tau is not None and tau <= POSITION_UNTIL_S,
                        }
                    )
                prev_owner = owner
                prev_mono = mono
    return events


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    logs = discover_flight_logs()
    csvs = discover_shadow_csvs()
    ticks: list[TermTick] = []
    row_keys: set[tuple] = set()

    handbacks: list[dict] = []
    for p in logs:
        mine_flight_log(p, ticks, row_keys, handbacks)
    for p in csvs:
        mine_shadow_csv(p, ticks, row_keys)

    live = [t for t in ticks if t.source == "live"]
    replay = [t for t in ticks if t.source == "replay"]

    live_taus = [t.tau_s for t in live if t.tau_s is not None]
    replay_taus = [t.tau_s for t in replay if t.tau_s is not None]
    all_taus = live_taus + replay_taus

    episodes = build_episodes(ticks)
    ep_any_le = [e for e in episodes if e.any_tau_le_threshold]
    ep_first_le = [e for e in episodes if e.first_capture_tau_le_threshold]

    first_capture_bad = [
        e for e in episodes if e.first_capture_tau_le_threshold
    ]
    live_first_bad = [e for e in first_capture_bad if e.source == "live"]

    handbacks_le = [h for h in handbacks if h["tau_le_threshold"]]

    verdict_change = bool(first_capture_bad)
    retro_verdict = "CHANGE" if verdict_change else "NO_CHANGE"

    try:
        repo_head = (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        )
    except Exception:
        repo_head = None

    summary = {
        "repo_head_sha": repo_head,
        "head_note": "Run against archived TERM-owned rows; position_until_s=0.45",
        "position_until_s": POSITION_UNTIL_S,
        "data_sources": {
            "flight_logs_scanned": len(logs),
            "shadow_csvs_scanned": len(csvs),
            "search_roots": [str(p) for p in SEARCH_ROOTS],
        },
        "term_rows": {
            "live": len(live),
            "replay": len(replay),
            "total": len(ticks),
            "tau_missing_live": sum(1 for t in live if t.tau_s is None),
            "tau_missing_replay": sum(1 for t in replay if t.tau_s is None),
        },
        "tau_distribution_all": {
            "n": len(all_taus),
            **percentiles(all_taus, (5, 25, 50, 75, 90, 95)),
            "min": min(all_taus) if all_taus else None,
            "max": max(all_taus) if all_taus else None,
            "mean": statistics.fmean(all_taus) if all_taus else None,
        },
        "tau_distribution_live": percentiles(live_taus, (5, 25, 50, 75, 90, 95)),
        "tau_distribution_replay": percentiles(replay_taus, (5, 25, 50, 75, 90, 95)),
        "episodes": {
            "total": len(episodes),
            "any_tick_tau_le_threshold": len(ep_any_le),
            "first_capture_tau_le_threshold": len(ep_first_le),
        },
        "first_captures_tau_le_threshold": len(first_capture_bad),
        "first_captures_tau_le_threshold_live": len(live_first_bad),
        "term_to_alt_handbacks": len(handbacks),
        "term_to_alt_handbacks_tau_le_threshold": len(handbacks_le),
        "RETRO_VERDICT": retro_verdict,
        "verdict_change": verdict_change,
        "verdict_rationale": (
            "First-capture-at-tau<=0.45 would be refused under corrected phase wire."
            if verdict_change
            else "No first-capture at tau<=0.45 in archive; handbacks at low tau do not imply recorded verdict change without refused captures."
        ),
    }

    tick_rows = [
        {
            "source": t.source,
            "flight_key": t.flight_key,
            "mono_ns": t.mono_ns,
            "t_rel_s": t.t_rel_s,
            "tau_s": t.tau_s,
            "guidance_phase": t.guidance_phase,
            "tau_le_threshold": t.tau_s is not None and t.tau_s <= POSITION_UNTIL_S,
            "path": t.path,
        }
        for t in ticks
    ]
    ep_rows = [
        {
            "source": e.source,
            "flight_key": e.flight_key,
            "n_ticks": e.n_ticks,
            "tau_first": e.tau_first,
            "tau_min": e.tau_min,
            "any_tau_le_threshold": e.any_tau_le_threshold,
            "first_capture_tau_le_threshold": e.first_capture_tau_le_threshold,
            "path": e.path,
        }
        for e in episodes
    ]

    write_csv(
        OUT / "term_owned_ticks.csv",
        tick_rows,
        [
            "source",
            "flight_key",
            "mono_ns",
            "t_rel_s",
            "tau_s",
            "guidance_phase",
            "tau_le_threshold",
            "path",
        ],
    )
    write_csv(
        OUT / "term_episodes.csv",
        ep_rows,
        [
            "source",
            "flight_key",
            "n_ticks",
            "tau_first",
            "tau_min",
            "any_tau_le_threshold",
            "first_capture_tau_le_threshold",
            "path",
        ],
    )
    if first_capture_bad:
        bad_rows = [
            {
                "source": e.source,
                "flight_key": e.flight_key,
                "n_ticks": e.n_ticks,
                "tau_first": e.tau_first,
                "tau_min": e.tau_min,
                "any_tau_le_threshold": e.any_tau_le_threshold,
                "first_capture_tau_le_threshold": e.first_capture_tau_le_threshold,
                "path": e.path,
            }
            for e in first_capture_bad
        ]
        write_csv(
            OUT / "first_capture_tau_le_threshold.csv",
            ep_rows,
            ep_rows[0].keys() if ep_rows else [],
        )

    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    report_lines = [
        "# Phase-wire blast radius � tau-at-TERM retro audit",
        "",
        "RESPONSE34 �3: before the fix, `terminal_override` passed constant `position` to the arbiter;",
        "no-return latch never engaged; first-capture-in-damping existed only in unit tests.",
        "Corrected wire: `guidance_phase(tau_s, �)` with `position_until_s=0.45`.",
        "",
        f"## RETRO_VERDICT: **{retro_verdict}**",
        "",
        summary["verdict_rationale"],
        "",
        "## Data mined",
        f"- Flight logs scanned: **{len(logs)}**",
        f"- Shadow CSVs with `shadow_owner`: **{len(csvs)}**",
        f"- TERM-owned rows � live: **{len(live)}**, replay: **{len(replay)}**, total: **{len(ticks)}**",
        "",
        "## Tau while TERM owned (seconds)",
        f"- All rows with tau: **{len(all_taus)}**",
    ]
    dist = summary["tau_distribution_all"]
    for k in ("min", "p5", "p25", "p50", "p75", "p90", "p95", "max", "mean"):
        if k in dist:
            report_lines.append(f"- {k}: **{dist[k]}**")
    report_lines += [
        "",
        "## Episodes (gap >0.5s or new flight splits)",
        f"- Episodes: **{len(episodes)}**",
        f"- Episodes with any tick tau ? {POSITION_UNTIL_S}: **{len(ep_any_le)}**",
        f"- First-capture (episode start) tau ? {POSITION_UNTIL_S}: **{len(ep_first_le)}**",
        "",
        "## Handbacks (live term_status TERM?ALT)",
        f"- Total handbacks: **{len(handbacks)}**",
        f"- Handbacks at tau ? {POSITION_UNTIL_S}: **{len(handbacks_le)}**",
        "",
        "## Deliverables",
        "- `term_owned_ticks.csv`",
        "- `term_episodes.csv`",
        "- `summary.json`",
        "",
    ]
    (OUT / "report.md").write_text("\n".join(report_lines), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
