"""P2 — Certificate-inheritance audit: span×range honesty gate.

Among unique CERTIFIED BAR_FULL terminal features with believed range
>= 0.5m, what fraction has span_px * believed_range outside [300, 800]
px·m? Bin by range. Known fiction cases: 202445/201630/202720 below 1.2m.
Question: how widespread, and does it ever occur ABOVE 2m?
"""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
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
PRODUCT_LO, PRODUCT_HI = 300.0, 800.0
PRODUCT_NOM = 512.0  # fx * GATE_W at 640px / 90°
KNOWN = {"202445", "201630", "202720"}


def iter_flight_logs() -> list[Path]:
    paths = []
    for root in (ROOT / "fixtures",
                 Path(r"C:\Users\tsion\Projects\eni_dcim\fixtures"),
                 Path(r"C:\Users\tsion\Projects\eni_dcim\logs")):
        if not root.exists():
            continue
        paths.extend(root.rglob("*-flight.jsonl"))
        paths.extend(root.rglob("**/flight.jsonl"))
    # dedupe by resolved path
    seen = set()
    out = []
    for p in paths:
        rp = str(p.resolve())
        if rp in seen:
            continue
        seen.add(rp)
        out.append(p)
    return out


def fid_of(path: Path) -> str:
    if path.name == "flight.jsonl":
        return path.parent.name
    return path.name.replace("-flight.jsonl", "")


def nearest_state_R(states: list[tuple[float, float]], t: float,
                    max_dt: float = 0.1) -> float | None:
    if not states:
        return None
    best = min(states, key=lambda s: abs(s[0] - t))
    return best[1] if abs(best[0] - t) <= max_dt else None


def scan_log(path: Path) -> list[dict]:
    """Return unique CERTIFIED BAR_FULL feature samples with believed R."""
    rows = []
    try:
        f = path.open(encoding="utf-8")
    except OSError:
        return rows
    t0 = None
    states = []  # (t_rel, R)
    feats = []
    with f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            mono = int(r["mono_ns"])
            if t0 is None:
                t0 = mono
            t = (mono - t0) / 1e9
            topic = r.get("topic")
            d = r.get("data") or {}
            if topic == "state":
                gr = d.get("gate_rel")
                if gr is not None:
                    states.append((t, float(np.linalg.norm(gr["t"]))))
            elif topic == "feature":
                if d.get("cert_status") != "certified":
                    continue
                if d.get("mode") != "BAR_FULL":
                    continue
                span = float(d.get("span_px") or 0)
                if span <= 1.0:
                    continue
                feats.append({
                    "t": t,
                    "span_px": span,
                    "y_top_px": d.get("y_top_px"),
                    "ts_ns": d.get("ts_ns"),
                })
    # Dedupe by feature ts_ns (unique exposure)
    uniq = {}
    for fe in feats:
        key = fe.get("ts_ns") or round(fe["t"], 3)
        uniq[key] = fe
    out = []
    for fe in uniq.values():
        R = nearest_state_R(states, fe["t"])
        if R is None or R < 0.5:
            continue
        product = fe["span_px"] * R
        out.append({
            "fid": fid_of(path),
            "t": fe["t"],
            "span_px": fe["span_px"],
            "R": R,
            "product": product,
            "outside": product < PRODUCT_LO or product > PRODUCT_HI,
            "ratio_to_512": product / PRODUCT_NOM,
        })
    return out


def bin_range(R: float) -> str:
    edges = [0.5, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0, 10.0, 99.0]
    labels = ["0.5-1.0", "1.0-1.2", "1.2-1.5", "1.5-2.0", "2.0-2.5",
              "2.5-3.0", "3.0-4.0", "4.0-6.0", "6.0-10", ">=10"]
    for i in range(len(labels)):
        if edges[i] <= R < edges[i + 1]:
            return labels[i]
    return ">=10"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    logs = iter_flight_logs()
    print(f"scanning {len(logs)} flight logs...", flush=True)
    samples = []
    for i, p in enumerate(logs):
        if i % 20 == 0:
            print(f"  [{i}/{len(logs)}] {p.name}", flush=True)
        samples.extend(scan_log(p))

    n = len(samples)
    n_out = sum(1 for s in samples if s["outside"])
    above2 = [s for s in samples if s["R"] >= 2.0]
    above2_out = [s for s in above2 if s["outside"]]
    below12 = [s for s in samples if s["R"] < 1.2]
    below12_out = [s for s in below12 if s["outside"]]

    by_bin = defaultdict(lambda: {"n": 0, "outside": 0, "products": []})
    for s in samples:
        b = bin_range(s["R"])
        by_bin[b]["n"] += 1
        by_bin[b]["products"].append(s["product"])
        if s["outside"]:
            by_bin[b]["outside"] += 1

    bin_table = []
    order = ["0.5-1.0", "1.0-1.2", "1.2-1.5", "1.5-2.0", "2.0-2.5",
             "2.5-3.0", "3.0-4.0", "4.0-6.0", "6.0-10", ">=10"]
    for b in order:
        d = by_bin.get(b)
        if not d or d["n"] == 0:
            continue
        bin_table.append({
            "bin": b,
            "n": d["n"],
            "outside": d["outside"],
            "frac_outside": d["outside"] / d["n"],
            "product_median": float(np.median(d["products"])),
            "product_p10": float(np.percentile(d["products"], 10)),
            "product_p90": float(np.percentile(d["products"], 90)),
        })

    # Known-case presence
    known_hits = [s for s in samples
                  if any(k in s["fid"] for k in KNOWN) and s["outside"]]

    # Per-flight outside counts
    by_fid = defaultdict(lambda: {"n": 0, "outside": 0, "min_R_out": 99, "max_R_out": 0})
    for s in samples:
        by_fid[s["fid"]]["n"] += 1
        if s["outside"]:
            by_fid[s["fid"]]["outside"] += 1
            by_fid[s["fid"]]["min_R_out"] = min(
                by_fid[s["fid"]]["min_R_out"], s["R"])
            by_fid[s["fid"]]["max_R_out"] = max(
                by_fid[s["fid"]]["max_R_out"], s["R"])

    worst = sorted(
        [{"fid": k, **v, "frac": v["outside"] / v["n"]}
         for k, v in by_fid.items() if v["outside"] > 0],
        key=lambda x: -x["outside"])[:30]

    bundle = {
        "n_logs_scanned": len(logs),
        "n_unique_certified_bar_full_Rge0p5": n,
        "n_outside_300_800": n_out,
        "fraction_outside": n_out / n if n else None,
        "product_band": [PRODUCT_LO, PRODUCT_HI],
        "above_2m": {
            "n": len(above2),
            "outside": len(above2_out),
            "fraction_outside": (
                len(above2_out) / len(above2) if above2 else None),
            "ever_outside_above_2m": len(above2_out) > 0,
        },
        "below_1p2m": {
            "n": len(below12),
            "outside": len(below12_out),
            "fraction_outside": (
                len(below12_out) / len(below12) if below12 else None),
        },
        "bins": bin_table,
        "known_case_hits": len(known_hits),
        "worst_flights": worst,
        "samples_outside_above_2m": [
            {k: s[k] for k in ("fid", "t", "span_px", "R", "product")}
            for s in above2_out[:40]
        ],
    }

    (OUT / "summary.json").write_text(
        json.dumps(bundle, indent=2, default=str), encoding="utf-8")

    with (OUT / "outside_samples.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["fid", "t", "span_px", "R", "product", "ratio_to_512"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for s in samples:
            if s["outside"]:
                w.writerow({k: s[k] for k in fields})

    report = render(bundle)
    (OUT / "cert-inheritance.md").write_text(report, encoding="utf-8")
    (ROOT / "analysis" / "2026-07-20-cert-inheritance.md").write_text(
        report, encoding="utf-8")
    print(json.dumps({
        "n": n, "outside": n_out, "frac": bundle["fraction_outside"],
        "above_2m": bundle["above_2m"],
        "below_1p2m": bundle["below_1p2m"],
    }, indent=2))
    return 0


def render(b: dict) -> str:
    lines = [
        "# Certificate-inheritance audit — span×range honesty (P2)",
        "",
        "Population: unique-exposure `feature` records with "
        "`cert_status=certified`, `mode=BAR_FULL`, believed "
        "`|gate_rel| >= 0.5m`. Fiction test: "
        f"`span_px · R ∉ [{b['product_band'][0]:.0f}, {b['product_band'][1]:.0f}]` "
        "px·m (nominal 512).",
        "",
        "## Verdict",
        "",
        f"- Samples: **{b['n_unique_certified_bar_full_Rge0p5']}** "
        f"across {b['n_logs_scanned']} logs",
        f"- Outside band: **{b['n_outside_300_800']}** "
        f"({100*(b['fraction_outside'] or 0):.1f}%)",
        f"- Below 1.2m outside: "
        f"**{b['below_1p2m']['outside']}/{b['below_1p2m']['n']}** "
        f"({100*(b['below_1p2m']['fraction_outside'] or 0):.1f}%)",
        f"- **Above 2m outside: "
        f"{b['above_2m']['outside']}/{b['above_2m']['n']} "
        f"({100*(b['above_2m']['fraction_outside'] or 0):.1f}%) — "
        f"{'YES, threatens admission' if b['above_2m']['ever_outside_above_2m'] else 'NONE observed'}**",
        f"- Known-case fid hits in outside set: {b['known_case_hits']}",
        "",
        "## Bins by believed range",
        "",
        "| bin (m) | n | outside | frac | prod med | p10 | p90 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in b["bins"]:
        lines.append(
            f"| {row['bin']} | {row['n']} | {row['outside']} | "
            f"{100*row['frac_outside']:.1f}% | {row['product_median']:.0f} | "
            f"{row['product_p10']:.0f} | {row['product_p90']:.0f} |"
        )
    lines += [
        "",
        "## Implication",
        "",
        "The 512 px·m oracle-door gate (e16d506) targets successor-wearing-"
        "the-certificate fiction concentrated at close range. If outside "
        "fraction above 2m is nonzero, admission (not only close tracking) "
        "needs the same honesty check.",
        "",
        "## Worst flights by outside count",
        "",
        "| fid | n | outside | frac | min R_out | max R_out |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for w in b["worst_flights"][:15]:
        lines.append(
            f"| `{w['fid']}` | {w['n']} | {w['outside']} | "
            f"{100*w['frac']:.0f}% | {w['min_R_out']:.2f} | "
            f"{w['max_R_out']:.2f} |"
        )
    lines += [
        "",
        "## Deliverables",
        "",
        "- `cert-inheritance.md`, `summary.json`, `outside_samples.csv`",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
