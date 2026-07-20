"""P3 — Telemetry completeness audit (cohort-4 gate row 11).

Diff CURRENT TermStatus + feature logs against the mandatory provenance
set. Deliverable: present/missing table + which missing fields block
cohort-4 adjudication vs nice-to-have.
"""
from __future__ import annotations

import csv
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
sys.path.insert(0, str(ROOT / "src"))

from aigp.core.messages import TermStatus, TerminalFeature, ShadowTerminal  # noqa: E402
import dataclasses

# Mandatory provenance set (advisory / RESPONSE19–27 synthesis)
MANDATORY = [
    # identity / exposure
    {"field": "gate_lock_epoch", "where": "term|feature|state",
     "blocks_c4": True,
     "why": "epoch hygiene; wrong-epoch metrology adjudication"},
    {"field": "exposure_id", "where": "feature|term",
     "blocks_c4": True,
     "why": "exact-exposure pairing FULL/SIDE; switch legality"},
    {"field": "cert_status", "where": "feature|detection",
     "blocks_c4": True,
     "why": "probation-out + identity; already on feature"},
    {"field": "psi_age", "where": "feature|term (SIDE)",
     "blocks_c4": True,
     "why": "S4 disposition; orientation-prior age on side rung"},
    # readiness / tail
    {"field": "fresh_tail_n", "where": "term",
     "blocks_c4": True,
     "why": "ready predicate audit (n/span/gap of contiguous tail)"},
    {"field": "fresh_tail_span_s", "where": "term",
     "blocks_c4": True,
     "why": "ready predicate audit"},
    {"field": "fresh_tail_max_gap_s", "where": "term",
     "blocks_c4": True,
     "why": "ready predicate audit"},
    {"field": "ready", "where": "term_status",
     "blocks_c4": True,
     "why": "TERM_READY adjudication"},
    {"field": "ready_legacy", "where": "term_status",
     "blocks_c4": False,
     "why": "dual-readiness A/B; nice for semantic check"},
    # measurement
    {"field": "e_z_raw", "where": "term",
     "blocks_c4": True,
     "why": "pre-clamp / pre-admission measurement"},
    {"field": "e_z_accepted", "where": "term",
     "blocks_c4": True,
     "why": "post-door accepted e (or null if rejected)"},
    {"field": "e_z", "where": "term_status",
     "blocks_c4": True,
     "why": "oracle effective e_z (present but conflates raw/accepted)"},
    {"field": "sigma_e", "where": "term",
     "blocks_c4": True,
     "why": "admission corridor + crossing test"},
    {"field": "sigma_v", "where": "term",
     "blocks_c4": True,
     "why": "admission / rate authority"},
    # transitions / ownership
    {"field": "source_mode", "where": "term_status",
     "blocks_c4": True,
     "why": "active rung FULL_QUAD|SIDE_PAIR"},
    {"field": "transition_fields", "where": "term",
     "blocks_c4": True,
     "why": "from/to source, reason, overlap median Δe at switch"},
    {"field": "tau_s", "where": "term",
     "blocks_c4": True,
     "why": "admission horizon / guidance"},
    {"field": "t_tail_s", "where": "term",
     "blocks_c4": False,
     "why": "admission parameter; static config OK if logged once"},
    {"field": "admission_score", "where": "term",
     "blocks_c4": True,
     "why": "corridor residual that passed/failed capture"},
    {"field": "owner", "where": "term_status",
     "blocks_c4": True,
     "why": "alt|term actuating owner"},
    {"field": "shadow_owner", "where": "shadow_terminal",
     "blocks_c4": False,
     "why": "shadow vs applied; present on Topic.SHADOW"},
    {"field": "applied_owner", "where": "term_status.owner + v_bz_applied",
     "blocks_c4": True,
     "why": "live adjudication (phase6i lesson)"},
    # rate anchor (RESPONSE27)
    {"field": "rate_source", "where": "term_status",
     "blocks_c4": True,
     "why": "FULL_QUAD vs FULL_RATE_ANCHOR provenance split"},
    {"field": "rate_anchor_age_s", "where": "term_status",
     "blocks_c4": True,
     "why": "anchor age / invalidation for (a) ruling"},
    {"field": "rate_anchor_valid", "where": "term",
     "blocks_c4": True,
     "why": "falsification monitor outcome"},
    {"field": "rate_anchor_exposure_id", "where": "term",
     "blocks_c4": False,
     "why": "nice; ties anchor to exposure"},
    # feature geometry
    {"field": "feature.mode", "where": "feature",
     "blocks_c4": True,
     "why": "FULL_QUAD|SIDE_PAIR|ROW_ONLY"},
    {"field": "feature.span_px", "where": "feature",
     "blocks_c4": True,
     "why": "scale gate product"},
    {"field": "feature.y_top_px", "where": "feature",
     "blocks_c4": True,
     "why": "e_z row formula"},
    {"field": "engaged", "where": "term_status",
     "blocks_c4": True,
     "why": "2.5m engagement gate"},
    {"field": "v_bz_applied", "where": "term_status",
     "blocks_c4": True,
     "why": "what actually replaced legacy vertical"},
]

# Sample flights for log presence
SAMPLE_LOGS = [
    ROOT / "fixtures" / "20260720T071602-phase6l-cohort-3"
    / "20260720T071112-cd18c5fb-flight.jsonl",
    ROOT / "fixtures" / "20260719T204430-phase6i-r-rate-ab"
    / "20260719T201630-f170ead6-flight.jsonl",
]


def dataclass_fields(cls) -> set[str]:
    return {f.name for f in dataclasses.fields(cls)}


def scan_log_keys(path: Path) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    if not path.exists():
        return out
    for line in path.open(encoding="utf-8"):
        r = json.loads(line)
        t = r.get("topic")
        d = r.get("data") or {}
        if not isinstance(d, dict):
            continue
        out.setdefault(t, set()).update(d.keys())
    return out


def present_map(code_term: set[str], code_feat: set[str],
                code_shadow: set[str],
                log_keys: dict[str, set[str]]) -> list[dict]:
    log_term = log_keys.get("term_status", set())
    log_feat = log_keys.get("feature", set())
    log_shadow = log_keys.get("shadow_terminal", set()) | log_keys.get("shadow", set())
    log_all = set()
    for s in log_keys.values():
        log_all |= s

    rows = []
    for m in MANDATORY:
        name = m["field"]
        # Heuristic presence checks
        in_code = False
        in_log = False
        notes = []
        if name == "gate_lock_epoch":
            in_code = False
            in_log = "gate_lock_epoch" in log_all or "lock_epoch" in log_all
        elif name == "exposure_id":
            # ts_ns doubles as exposure id in observe()
            in_code = "ts_ns" in code_feat
            in_log = "ts_ns" in log_feat
            notes.append("proxy=feature.ts_ns (exact-exposure pairing)")
        elif name == "cert_status":
            in_code = "cert_status" in code_feat
            in_log = "cert_status" in log_feat
        elif name == "psi_age":
            in_code = False
            in_log = "psi_age" in log_all or "psi_age_s" in log_all
        elif name.startswith("fresh_tail"):
            in_code = False  # history_stats() exists but not logged on TermStatus
            in_log = name in log_term
            notes.append("TerminalOracle.history_stats() computes; not on TermStatus")
        elif name == "ready":
            in_code = "ready" in code_term
            in_log = "ready" in log_term
        elif name == "ready_legacy":
            in_code = "ready_legacy" in code_term
            in_log = "ready_legacy" in log_term
            if in_code and not in_log:
                notes.append("on TermStatus dataclass; older logs predate field")
        elif name == "e_z_raw":
            in_code = False
            in_log = "e_z_raw" in log_term
        elif name == "e_z_accepted":
            in_code = False
            in_log = "e_z_accepted" in log_term
            notes.append("TermStatus.e_z is effective only")
        elif name == "e_z":
            in_code = "e_z" in code_term
            in_log = "e_z" in log_term
        elif name in ("sigma_e", "sigma_v"):
            in_code = False
            in_log = name in log_term
            notes.append("oracle.sigmas_for_active() exists; not logged")
        elif name == "source_mode":
            in_code = "source_mode" in code_term
            in_log = "source_mode" in log_term
            if in_code and not in_log:
                notes.append("on TermStatus; phase6l sample may predate")
        elif name == "transition_fields":
            in_code = False
            in_log = any(k.startswith("transition") or k in ("from_source", "to_source")
                         for k in log_term)
        elif name == "tau_s":
            in_code = False
            in_log = "tau_s" in log_term or "tau" in log_term
        elif name == "t_tail_s":
            in_code = False
            in_log = "t_tail_s" in log_term
        elif name == "admission_score":
            in_code = False
            in_log = "admission_score" in log_term
        elif name == "owner":
            in_code = "owner" in code_term
            in_log = "owner" in log_term
        elif name == "shadow_owner":
            in_code = "owner" in code_shadow
            in_log = "owner" in log_shadow
        elif name == "applied_owner":
            in_code = "owner" in code_term and "v_bz_applied" in code_term
            in_log = "owner" in log_term and "v_bz_applied" in log_term
        elif name == "rate_source":
            in_code = "rate_source" in code_term
            in_log = "rate_source" in log_term
        elif name == "rate_anchor_age_s":
            in_code = "rate_anchor_age_s" in code_term
            in_log = "rate_anchor_age_s" in log_term
        elif name == "rate_anchor_valid":
            in_code = False
            in_log = "rate_anchor_valid" in log_term
            notes.append("oracle.rate_anchor_valid exists; not on TermStatus")
        elif name == "rate_anchor_exposure_id":
            in_code = False
            in_log = False
        elif name == "feature.mode":
            in_code = "mode" in code_feat
            in_log = "mode" in log_feat
        elif name == "feature.span_px":
            in_code = "span_px" in code_feat
            in_log = "span_px" in log_feat
        elif name == "feature.y_top_px":
            in_code = "y_top_px" in code_feat
            in_log = "y_top_px" in log_feat
        elif name == "engaged":
            in_code = "engaged" in code_term
            in_log = "engaged" in log_term
        elif name == "v_bz_applied":
            in_code = "v_bz_applied" in code_term
            in_log = "v_bz_applied" in log_term
        else:
            notes.append("unclassified")

        status = "PRESENT" if (in_code and in_log) else (
            "CODE_ONLY" if in_code and not in_log else (
                "LOG_ONLY" if in_log and not in_code else "MISSING"))
        rows.append({
            **m,
            "in_code": in_code,
            "in_sample_log": in_log,
            "status": status,
            "notes": "; ".join(notes),
        })
    return rows


def main() -> None:
    code_term = dataclass_fields(TermStatus)
    code_feat = dataclass_fields(TerminalFeature)
    code_shadow = dataclass_fields(ShadowTerminal)

    log_keys: dict[str, set[str]] = {}
    for p in SAMPLE_LOGS:
        for t, ks in scan_log_keys(p).items():
            log_keys.setdefault(t, set()).update(ks)

    # Also peek newest tuning term CSV if present (richer schema)
    tun = list((ROOT / "tuning").glob("**/term_status_live/*.csv"))
    tuning_cols: set[str] = set()
    if tun:
        with tun[0].open(encoding="utf-8") as f:
            tuning_cols = set(next(csv.reader(f)))

    rows = present_map(code_term, code_feat, code_shadow, log_keys)
    # Enrich rate_* from code even if sample log old
    for r in rows:
        if r["field"] in ("rate_source", "rate_anchor_age_s", "ready_legacy",
                          "source_mode") and r["in_code"] and not r["in_sample_log"]:
            r["notes"] = (r["notes"] + "; " if r["notes"] else "") + (
                "PRESENT in TermStatus on HEAD — sample fixture predates field"
            )
            if r["status"] == "CODE_ONLY":
                # For cohort-4 build completeness, code presence counts as
                # shipped; logging gap is still a gap until a flight on HEAD
                pass

    missing_block = [r for r in rows
                     if r["blocks_c4"] and r["status"] in ("MISSING", "CODE_ONLY", "LOG_ONLY")
                     and not (r["status"] == "CODE_ONLY"
                              and r["field"] in (
                                  "rate_source", "rate_anchor_age_s",
                                  "ready_legacy", "source_mode"))]
    # Treat CODE_ONLY for brand-new TermStatus fields as "shipped, needs flight"
    shipped_pending_flight = [r for r in rows
                              if r["status"] == "CODE_ONLY"
                              and r["field"] in (
                                  "rate_source", "rate_anchor_age_s",
                                  "ready_legacy", "source_mode")]
    missing_nice = [r for r in rows
                    if (not r["blocks_c4"]) and r["status"] != "PRESENT"]

    summary = {
        "ask": "telemetry completeness audit (cohort-4 gate row 11)",
        "TermStatus_fields_HEAD": sorted(code_term),
        "TerminalFeature_fields_HEAD": sorted(code_feat),
        "sample_log_topics": {k: sorted(v) for k, v in log_keys.items()
                              if k in ("term_status", "feature", "shadow_terminal",
                                       "detection", "state")},
        "tuning_term_csv_cols_example": sorted(tuning_cols)[:40],
        "n_mandatory": len(rows),
        "n_present": sum(1 for r in rows if r["status"] == "PRESENT"),
        "n_missing_block_c4": len(missing_block),
        "n_shipped_pending_flight": len(shipped_pending_flight),
        "n_missing_nice": len(missing_nice),
        "missing_block_c4": [r["field"] for r in missing_block],
        "missing_nice_to_have": [r["field"] for r in missing_nice],
        "shipped_code_awaiting_head_flight": [r["field"] for r in shipped_pending_flight],
        "rows": rows,
    }
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8")

    with (OUT / "telemetry_gap_table.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["field", "where", "blocks_c4", "status", "in_code",
                        "in_sample_log", "why", "notes"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    lines = [
        "# Telemetry completeness audit (gate row 11)",
        "",
        f"- mandatory fields checked: {summary['n_mandatory']}",
        f"- PRESENT in code+sample log: {summary['n_present']}",
        f"- **MISSING that block cohort-4 adjudication: "
        f"{summary['n_missing_block_c4']}**",
        f"- CODE_ONLY (shipped on HEAD, awaiting flight log): "
        f"{summary['n_shipped_pending_flight']}",
        f"- missing nice-to-have: {summary['n_missing_nice']}",
        "",
        "## Blocks cohort-4 (build must close)",
        "",
    ]
    if not missing_block:
        lines.append("_None — or only pending HEAD flight exposure._")
    else:
        lines += [
            "| field | status | why |",
            "|-------|:------:|-----|",
        ]
        for r in missing_block:
            lines.append(
                f"| `{r['field']}` | {r['status']} | {r['why']} |"
            )
    lines += [
        "",
        "## Nice-to-have gaps",
        "",
        "| field | status | why |",
        "|-------|:------:|-----|",
    ]
    for r in missing_nice:
        lines.append(f"| `{r['field']}` | {r['status']} | {r['why']} |")
    lines += [
        "",
        "## Full table",
        "",
        "| field | blocks C4? | status | notes |",
        "|-------|:----------:|:------:|-------|",
    ]
    for r in rows:
        lines.append(
            f"| `{r['field']}` | {r['blocks_c4']} | **{r['status']}** | "
            f"{r['notes'][:80]} |"
        )
    lines += [
        "",
        f"TermStatus on HEAD: `{sorted(code_term)}`",
        "",
        "The build closes the **blocks_c4** MISSING/CODE_ONLY rows "
        "(except CODE_ONLY fields already on TermStatus that only need "
        "a HEAD flight to appear in logs).",
        "",
        "## Deliverables",
        "",
        "- `telemetry_gap_table.csv`, `summary.json`, this report",
    ]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "n_missing_block_c4": summary["n_missing_block_c4"],
        "missing_block_c4": summary["missing_block_c4"],
        "shipped_pending_flight": summary["shipped_code_awaiting_head_flight"],
        "missing_nice": summary["missing_nice_to_have"],
    }, indent=2))


if __name__ == "__main__":
    main()
