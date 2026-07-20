from __future__ import annotations

import csv
import json
import math
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
FIXTURE_ROOTS = [REPO / "fixtures"]
TUNING_ROOT = REPO / "tuning"

EPISODE_GAP_S = 0.35
COMMAND_ACTIVE_MPS = 0.03
STEP_DELTA_MPS = 0.03
SATURATION_FRACTION = 0.95
AUTHORITY_LIMIT_QUALITY = 0.999


def git_head(short: bool = False) -> str:
    args = ["git", "rev-parse"]
    if short:
        args.append("--short=12")
    args.append("HEAD")
    return subprocess.check_output(args, cwd=REPO, text=True).strip()


def load_terminal_vz_max() -> float:
    params_path = REPO / "config" / "params_default.json"
    with params_path.open("r", encoding="utf-8") as f:
        params = json.load(f)
    return float(params["planner"]["terminal"]["vz_max_mps"])


def as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(out):
        return None
    return out


def as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def safe_json(value: Any) -> str:
    if value is None:
        return ""
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def flight_id(path: Path) -> str:
    name = path.name
    if name.endswith("-flight.jsonl"):
        return name[: -len("-flight.jsonl")]
    return path.stem


def cohort_id(path: Path) -> str:
    try:
        return path.parent.relative_to(REPO).as_posix()
    except ValueError:
        return path.parent.as_posix()


def discover_flight_logs() -> list[Path]:
    paths: list[Path] = []
    for root in FIXTURE_ROOTS:
        if root.exists():
            paths.extend(root.rglob("*flight.jsonl"))
    return sorted(paths)


@dataclass
class TermRow:
    flight_id: str
    cohort: str
    path: Path
    mono_ns: int
    ts_ns: int | None
    line_no: int
    engaged: bool
    ready: bool
    e_z: float | None
    vz_up: float | None
    v_bz_applied: float | None
    shadow_vz_up: float | None
    rate_anchor_age_s: float | None
    rate_anchor_quality: float | None
    rate_source: str
    source_mode: str
    phase: str
    transition: str
    rate_anchor_valid: Any
    raw: dict[str, Any]
    owner_provenance_valid: bool = False
    command_source: str = ""
    episode_id: str = ""
    episode_index: int = 0
    episode_elapsed_s: float = 0.0
    delta_vz_up_mps: float | None = None
    command_sign: str = "zero"
    slope_sign: str = "flat"
    up_command_row: bool = False
    down_command_row: bool = False
    up_step_row: bool = False
    down_step_row: bool = False
    saturation_row: bool = False
    authority_limited_row: bool = False
    authority_observable: bool = False
    up_down_slope_triangular_episode: bool = False
    down_up_slope_triangular_episode: bool = False
    up_down_signed_triangular_episode: bool = False
    down_up_signed_triangular_episode: bool = False


@dataclass
class Episode:
    episode_id: str
    flight_id: str
    cohort: str
    path: Path
    rows: list[TermRow] = field(default_factory=list)
    up_down_slope_triangular: bool = False
    down_up_slope_triangular: bool = False
    up_down_signed_triangular: bool = False
    down_up_signed_triangular: bool = False


def term_row_from_record(path: Path, line_no: int, rec: dict[str, Any]) -> TermRow | None:
    if rec.get("topic") != "term_status":
        return None
    data = rec.get("data") or {}
    if data.get("owner") != "term":
        return None
    mono_ns = as_int(rec.get("mono_ns"))
    if mono_ns is None:
        return None

    vz_up = as_float(data.get("vz_up"))
    v_bz_applied = as_float(data.get("v_bz_applied"))
    engaged = data.get("engaged") is True
    ready = data.get("ready") is True
    rate_anchor_valid = data.get("rate_anchor_valid")
    provenance_valid = bool(engaged and ready and vz_up is not None and v_bz_applied is not None)
    if rate_anchor_valid is False:
        provenance_valid = False

    if provenance_valid:
        command_source = "TERM"
    elif vz_up is not None or v_bz_applied is not None:
        command_source = "TERM-status-incomplete"
    else:
        command_source = "TERM-owner-no-physical-command"

    return TermRow(
        flight_id=flight_id(path),
        cohort=cohort_id(path),
        path=path,
        mono_ns=mono_ns,
        ts_ns=as_int(data.get("ts_ns")),
        line_no=line_no,
        engaged=engaged,
        ready=ready,
        e_z=as_float(data.get("e_z")),
        vz_up=vz_up,
        v_bz_applied=v_bz_applied,
        shadow_vz_up=as_float(data.get("shadow_vz_up")),
        rate_anchor_age_s=as_float(data.get("rate_anchor_age_s")),
        rate_anchor_quality=as_float(data.get("rate_anchor_quality")),
        rate_source=str(data.get("rate_source") or ""),
        source_mode=str(data.get("source_mode") or ""),
        phase=str(data.get("phase") or data.get("guidance_phase") or ""),
        transition=str(data.get("transition") or ""),
        rate_anchor_valid=rate_anchor_valid,
        raw=data,
        owner_provenance_valid=provenance_valid,
        command_source=command_source,
    )


def read_flight_log(path: Path) -> tuple[list[TermRow], dict[str, Any]]:
    rows: list[TermRow] = []
    term_status_rows = 0
    shadow_term_rows = 0
    shadow_up_values: list[float] = []
    term_status_owner_values = Counter()
    topics = Counter()

    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            topic = rec.get("topic")
            topics[str(topic)] += 1
            data = rec.get("data") or {}
            if topic == "term_status":
                term_status_rows += 1
                term_status_owner_values[str(data.get("owner") or "")] += 1
                row = term_row_from_record(path, line_no, rec)
                if row is not None:
                    rows.append(row)
            elif topic == "shadow" and data.get("owner") == "term":
                shadow_term_rows += 1
                up = as_float(data.get("up_legacy_mps"))
                if up is not None:
                    shadow_up_values.append(up)

    shadow_min = min(shadow_up_values) if shadow_up_values else None
    shadow_max = max(shadow_up_values) if shadow_up_values else None
    manifest = {
        "flight_id": flight_id(path),
        "cohort": cohort_id(path),
        "path": str(path),
        "term_status_rows": term_status_rows,
        "term_status_owner_term_rows": len(rows),
        "term_status_owner_values": dict(term_status_owner_values),
        "shadow_owner_term_rows": shadow_term_rows,
        "shadow_up_min_mps": shadow_min,
        "shadow_up_max_mps": shadow_max,
        "has_physical_term_rows": bool(rows),
        "has_shadow_only_term": bool(shadow_term_rows and not rows),
        "topics_with_counts": dict(topics),
    }
    return rows, manifest


def sign_name(value: float | None, threshold: float) -> str:
    if value is None:
        return "missing"
    if value >= threshold:
        return "up"
    if value <= -threshold:
        return "down"
    return "zero"


def build_episodes(rows: list[TermRow], vz_max: float) -> list[Episode]:
    episodes: list[Episode] = []
    rows_by_flight: dict[str, list[TermRow]] = defaultdict(list)
    for row in rows:
        if row.owner_provenance_valid:
            rows_by_flight[row.flight_id].append(row)

    for fid, flight_rows in sorted(rows_by_flight.items()):
        flight_rows.sort(key=lambda row: row.mono_ns)
        episode_index = 0
        current: Episode | None = None
        prev_row: TermRow | None = None
        first_ns = 0

        for row in flight_rows:
            gap_s = None
            if prev_row is not None:
                gap_s = (row.mono_ns - prev_row.mono_ns) / 1e9
            if current is None or gap_s is None or gap_s > EPISODE_GAP_S:
                episode_index += 1
                current = Episode(
                    episode_id=f"{fid}:term:{episode_index}",
                    flight_id=fid,
                    cohort=row.cohort,
                    path=row.path,
                )
                episodes.append(current)
                first_ns = row.mono_ns
                prev_in_episode = None
            else:
                prev_in_episode = current.rows[-1] if current.rows else None

            row.episode_id = current.episode_id
            row.episode_index = episode_index
            row.episode_elapsed_s = (row.mono_ns - first_ns) / 1e9
            row.command_sign = sign_name(row.vz_up, COMMAND_ACTIVE_MPS)
            row.up_command_row = row.command_sign == "up"
            row.down_command_row = row.command_sign == "down"
            row.saturation_row = bool(
                (row.vz_up is not None and abs(row.vz_up) >= SATURATION_FRACTION * vz_max)
                or (row.v_bz_applied is not None and abs(row.v_bz_applied) >= SATURATION_FRACTION * vz_max)
            )
            row.authority_observable = row.rate_anchor_quality is not None or row.rate_anchor_valid is not None
            row.authority_limited_row = bool(
                row.rate_anchor_quality is not None and row.rate_anchor_quality < AUTHORITY_LIMIT_QUALITY
            )
            if prev_in_episode is not None and row.vz_up is not None and prev_in_episode.vz_up is not None:
                row.delta_vz_up_mps = row.vz_up - prev_in_episode.vz_up
                row.slope_sign = sign_name(row.delta_vz_up_mps, STEP_DELTA_MPS)
                row.up_step_row = row.slope_sign == "up"
                row.down_step_row = row.slope_sign == "down"
            current.rows.append(row)
            prev_row = row

    for episode in episodes:
        slopes = [row.slope_sign for row in episode.rows if row.slope_sign in {"up", "down"}]
        command_signs = [row.command_sign for row in episode.rows if row.command_sign in {"up", "down"}]
        episode.up_down_slope_triangular = any(
            first == "up" and "down" in slopes[idx + 1 :] for idx, first in enumerate(slopes)
        )
        episode.down_up_slope_triangular = any(
            first == "down" and "up" in slopes[idx + 1 :] for idx, first in enumerate(slopes)
        )
        episode.up_down_signed_triangular = any(
            first == "up" and "down" in command_signs[idx + 1 :] for idx, first in enumerate(command_signs)
        )
        episode.down_up_signed_triangular = any(
            first == "down" and "up" in command_signs[idx + 1 :] for idx, first in enumerate(command_signs)
        )
        for row in episode.rows:
            row.up_down_slope_triangular_episode = episode.up_down_slope_triangular
            row.down_up_slope_triangular_episode = episode.down_up_slope_triangular
            row.up_down_signed_triangular_episode = episode.up_down_signed_triangular
            row.down_up_signed_triangular_episode = episode.down_up_signed_triangular

    return episodes


def fmt_range(values: list[float]) -> str:
    clean = [value for value in values if value is not None and math.isfinite(value)]
    if not clean:
        return ""
    return f"{min(clean):.6f}..{max(clean):.6f}"


def count_true(rows: list[TermRow], attr: str) -> int:
    return sum(1 for row in rows if getattr(row, attr))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def inventory() -> Path:
    head = git_head(short=False)
    head_short = git_head(short=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = TUNING_ROOT / f"r26-command-regime-inventory-{head_short}-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    vz_max = load_terminal_vz_max()

    all_rows: list[TermRow] = []
    manifests: list[dict[str, Any]] = []
    for path in discover_flight_logs():
        rows, manifest = read_flight_log(path)
        all_rows.extend(rows)
        manifests.append(manifest)

    episodes = build_episodes(all_rows, vz_max)

    physical_rows = [row for row in all_rows if row.owner_provenance_valid]
    rows_by_flight: dict[str, list[TermRow]] = defaultdict(list)
    for row in physical_rows:
        rows_by_flight[row.flight_id].append(row)

    manifest_rows = []
    for manifest in manifests:
        source_class = "none"
        if manifest["has_physical_term_rows"]:
            source_class = "physical-term-status"
        elif manifest["has_shadow_only_term"]:
            source_class = "shadow-only-excluded"
        manifest_rows.append(
            {
                "flight_id": manifest["flight_id"],
                "cohort": manifest["cohort"],
                "source_class": source_class,
                "term_status_rows": manifest["term_status_rows"],
                "term_status_owner_term_rows": manifest["term_status_owner_term_rows"],
                "shadow_owner_term_rows": manifest["shadow_owner_term_rows"],
                "shadow_up_range_mps": fmt_range(
                    [
                        value
                        for value in [manifest["shadow_up_min_mps"], manifest["shadow_up_max_mps"]]
                        if value is not None
                    ]
                ),
                "term_status_owner_values": safe_json(manifest["term_status_owner_values"]),
                "path": manifest["path"],
            }
        )

    term_row_dicts = []
    for row in physical_rows:
        term_row_dicts.append(
            {
                "flight_id": row.flight_id,
                "cohort": row.cohort,
                "episode_id": row.episode_id,
                "mono_ns": row.mono_ns,
                "ts_ns": row.ts_ns,
                "line_no": row.line_no,
                "owner_provenance_valid": row.owner_provenance_valid,
                "command_source": row.command_source,
                "engaged": row.engaged,
                "ready": row.ready,
                "phase": row.phase,
                "source_mode": row.source_mode,
                "rate_source": row.rate_source,
                "transition": row.transition,
                "rate_anchor_valid": row.rate_anchor_valid,
                "rate_anchor_age_s": row.rate_anchor_age_s,
                "episode_elapsed_s": f"{row.episode_elapsed_s:.6f}",
                "e_z": row.e_z,
                "vz_up": row.vz_up,
                "v_bz_applied": row.v_bz_applied,
                "shadow_vz_up": row.shadow_vz_up,
                "delta_vz_up_mps": row.delta_vz_up_mps,
                "command_sign": row.command_sign,
                "slope_sign": row.slope_sign,
                "up_command_row": row.up_command_row,
                "down_command_row": row.down_command_row,
                "up_step_row": row.up_step_row,
                "down_step_row": row.down_step_row,
                "up_down_slope_triangular_episode": row.up_down_slope_triangular_episode,
                "down_up_slope_triangular_episode": row.down_up_slope_triangular_episode,
                "up_down_signed_triangular_episode": row.up_down_signed_triangular_episode,
                "down_up_signed_triangular_episode": row.down_up_signed_triangular_episode,
                "saturation_row": row.saturation_row,
                "authority_observable": row.authority_observable,
                "authority_limited_row": row.authority_limited_row,
                "rate_anchor_quality": row.rate_anchor_quality,
                "path": str(row.path),
            }
        )

    episode_dicts = []
    for episode in episodes:
        rows = episode.rows
        episode_dicts.append(
            {
                "episode_id": episode.episode_id,
                "flight_id": episode.flight_id,
                "cohort": episode.cohort,
                "rows": len(rows),
                "owner_provenance_valid": all(row.owner_provenance_valid for row in rows),
                "command_source": ",".join(sorted({row.command_source for row in rows})),
                "age_range_s": fmt_range([row.rate_anchor_age_s for row in rows if row.rate_anchor_age_s is not None]),
                "episode_elapsed_range_s": fmt_range([row.episode_elapsed_s for row in rows]),
                "vz_up_range_mps": fmt_range([row.vz_up for row in rows if row.vz_up is not None]),
                "up_command_rows": count_true(rows, "up_command_row"),
                "down_command_rows": count_true(rows, "down_command_row"),
                "up_step_rows": count_true(rows, "up_step_row"),
                "down_step_rows": count_true(rows, "down_step_row"),
                "up_down_slope_triangular": episode.up_down_slope_triangular,
                "down_up_slope_triangular": episode.down_up_slope_triangular,
                "up_down_signed_triangular": episode.up_down_signed_triangular,
                "down_up_signed_triangular": episode.down_up_signed_triangular,
                "saturation_rows": count_true(rows, "saturation_row"),
                "authority_limited_rows": count_true(rows, "authority_limited_row"),
                "authority_observable_rows": count_true(rows, "authority_observable"),
                "path": str(episode.path),
            }
        )

    flight_dicts = []
    for fid, rows in sorted(rows_by_flight.items()):
        source_counts = Counter(row.command_source for row in rows)
        rate_source_counts = Counter(row.rate_source or "missing" for row in rows)
        source_mode_counts = Counter(row.source_mode or "missing" for row in rows)
        flight_dicts.append(
            {
                "flight_id": fid,
                "cohort": rows[0].cohort,
                "physical_term_rows": len(rows),
                "owner_provenance_valid": all(row.owner_provenance_valid for row in rows),
                "command_source": safe_json(dict(source_counts)),
                "source_mode_counts": safe_json(dict(source_mode_counts)),
                "rate_source_counts": safe_json(dict(rate_source_counts)),
                "age_range_s": fmt_range([row.rate_anchor_age_s for row in rows if row.rate_anchor_age_s is not None]),
                "episode_elapsed_range_s": fmt_range([row.episode_elapsed_s for row in rows]),
                "vz_up_range_mps": fmt_range([row.vz_up for row in rows if row.vz_up is not None]),
                "up_command_rows": count_true(rows, "up_command_row"),
                "down_command_rows": count_true(rows, "down_command_row"),
                "up_step_rows": count_true(rows, "up_step_row"),
                "down_step_rows": count_true(rows, "down_step_row"),
                "up_down_slope_triangular_rows": count_true(rows, "up_down_slope_triangular_episode"),
                "down_up_slope_triangular_rows": count_true(rows, "down_up_slope_triangular_episode"),
                "up_down_signed_triangular_rows": count_true(rows, "up_down_signed_triangular_episode"),
                "down_up_signed_triangular_rows": count_true(rows, "down_up_signed_triangular_episode"),
                "up_down_slope_triangular_episodes": sum(
                    1 for episode in episodes if episode.flight_id == fid and episode.up_down_slope_triangular
                ),
                "down_up_slope_triangular_episodes": sum(
                    1 for episode in episodes if episode.flight_id == fid and episode.down_up_slope_triangular
                ),
                "up_down_signed_triangular_episodes": sum(
                    1 for episode in episodes if episode.flight_id == fid and episode.up_down_signed_triangular
                ),
                "down_up_signed_triangular_episodes": sum(
                    1 for episode in episodes if episode.flight_id == fid and episode.down_up_signed_triangular
                ),
                "saturation_rows": count_true(rows, "saturation_row"),
                "authority_observable_rows": count_true(rows, "authority_observable"),
                "authority_limited_rows": count_true(rows, "authority_limited_row"),
                "path": str(rows[0].path),
            }
        )

    total_by_regime = {
        "up_steps": sum(count_true(rows, "up_command_row") for rows in rows_by_flight.values()),
        "down_steps": sum(count_true(rows, "down_command_row") for rows in rows_by_flight.values()),
        "diagnostic_up_slope_steps": sum(count_true(rows, "up_step_row") for rows in rows_by_flight.values()),
        "diagnostic_down_slope_steps": sum(count_true(rows, "down_step_row") for rows in rows_by_flight.values()),
        "up_command_rows": sum(count_true(rows, "up_command_row") for rows in rows_by_flight.values()),
        "down_command_rows": sum(count_true(rows, "down_command_row") for rows in rows_by_flight.values()),
        "up_down_triangular": sum(1 for episode in episodes if episode.up_down_signed_triangular),
        "down_up_triangular": sum(1 for episode in episodes if episode.down_up_signed_triangular),
        "diagnostic_up_down_slope_triangular": sum(1 for episode in episodes if episode.up_down_slope_triangular),
        "diagnostic_down_up_slope_triangular": sum(1 for episode in episodes if episode.down_up_slope_triangular),
        "saturation": sum(count_true(rows, "saturation_row") for rows in rows_by_flight.values()),
        "authority_limited": sum(count_true(rows, "authority_limited_row") for rows in rows_by_flight.values()),
    }
    required_order = [
        ("up_steps", "physical TERM vz_up >= +0.03 m/s"),
        ("down_steps", "physical TERM vz_up <= -0.03 m/s"),
        ("up_down_triangular", "episode command-sign sequence contains up then later down"),
        ("down_up_triangular", "episode command-sign sequence contains down then later up"),
        ("saturation", f"abs(vz_up or v_bz_applied) >= {SATURATION_FRACTION:.2f} * vz_max ({vz_max:.3f} m/s)"),
        ("authority_limited", f"rate_anchor_quality present and < {AUTHORITY_LIMIT_QUALITY:.3f}"),
    ]
    gap_rows = []
    for regime, definition in required_order:
        evidence_rows = int(total_by_regime[regime])
        gap_rows.append(
            {
                "regime": regime,
                "definition": definition,
                "physical_evidence_count": evidence_rows,
                "covered": evidence_rows > 0,
                "gap": evidence_rows == 0,
                "route_if_gap": "closed-loop simulator fixture required" if evidence_rows == 0 else "",
            }
        )

    excluded_rows = [
        {
            "flight_id": row["flight_id"],
            "cohort": row["cohort"],
            "shadow_owner_term_rows": row["shadow_owner_term_rows"],
            "shadow_up_range_mps": row["shadow_up_range_mps"],
            "term_status_owner_term_rows": row["term_status_owner_term_rows"],
            "exclusion_reason": "shadow TERM rows are unexecuted; R26-3 requires physical term_status owner=term",
            "path": row["path"],
        }
        for row in manifest_rows
        if row["source_class"] == "shadow-only-excluded"
    ]

    write_csv(
        out_dir / "recording_manifest.csv",
        manifest_rows,
        [
            "flight_id",
            "cohort",
            "source_class",
            "term_status_rows",
            "term_status_owner_term_rows",
            "shadow_owner_term_rows",
            "shadow_up_range_mps",
            "term_status_owner_values",
            "path",
        ],
    )
    write_csv(
        out_dir / "physical_term_rows.csv",
        term_row_dicts,
        [
            "flight_id",
            "cohort",
            "episode_id",
            "mono_ns",
            "ts_ns",
            "line_no",
            "owner_provenance_valid",
            "command_source",
            "engaged",
            "ready",
            "phase",
            "source_mode",
            "rate_source",
            "transition",
            "rate_anchor_valid",
            "rate_anchor_age_s",
            "episode_elapsed_s",
            "e_z",
            "vz_up",
            "v_bz_applied",
            "shadow_vz_up",
            "delta_vz_up_mps",
            "command_sign",
            "slope_sign",
            "up_command_row",
            "down_command_row",
            "up_step_row",
            "down_step_row",
            "up_down_slope_triangular_episode",
            "down_up_slope_triangular_episode",
            "up_down_signed_triangular_episode",
            "down_up_signed_triangular_episode",
            "saturation_row",
            "authority_observable",
            "authority_limited_row",
            "rate_anchor_quality",
            "path",
        ],
    )
    write_csv(
        out_dir / "episode_regime_inventory.csv",
        episode_dicts,
        [
            "episode_id",
            "flight_id",
            "cohort",
            "rows",
            "owner_provenance_valid",
            "command_source",
            "age_range_s",
            "episode_elapsed_range_s",
            "vz_up_range_mps",
            "up_command_rows",
            "down_command_rows",
            "up_step_rows",
            "down_step_rows",
            "up_down_slope_triangular",
            "down_up_slope_triangular",
            "up_down_signed_triangular",
            "down_up_signed_triangular",
            "saturation_rows",
            "authority_limited_rows",
            "authority_observable_rows",
            "path",
        ],
    )
    write_csv(
        out_dir / "flight_regime_inventory.csv",
        flight_dicts,
        [
            "flight_id",
            "cohort",
            "physical_term_rows",
            "owner_provenance_valid",
            "command_source",
            "source_mode_counts",
            "rate_source_counts",
            "age_range_s",
            "episode_elapsed_range_s",
            "vz_up_range_mps",
            "up_command_rows",
            "down_command_rows",
            "up_step_rows",
            "down_step_rows",
            "up_down_slope_triangular_rows",
            "down_up_slope_triangular_rows",
            "up_down_signed_triangular_rows",
            "down_up_signed_triangular_rows",
            "up_down_slope_triangular_episodes",
            "down_up_slope_triangular_episodes",
            "up_down_signed_triangular_episodes",
            "down_up_signed_triangular_episodes",
            "saturation_rows",
            "authority_observable_rows",
            "authority_limited_rows",
            "path",
        ],
    )
    write_csv(
        out_dir / "r26_3_gap_list.csv",
        gap_rows,
        ["regime", "definition", "physical_evidence_count", "covered", "gap", "route_if_gap"],
    )
    write_csv(
        out_dir / "shadow_only_excluded.csv",
        excluded_rows,
        [
            "flight_id",
            "cohort",
            "shadow_owner_term_rows",
            "shadow_up_range_mps",
            "term_status_owner_term_rows",
            "exclusion_reason",
            "path",
        ],
    )

    summary = {
        "repo_head": head,
        "vz_max_mps": vz_max,
        "flight_logs_scanned": len(manifests),
        "recordings_with_physical_term_status": len(rows_by_flight),
        "physical_term_rows": len(physical_rows),
        "physical_term_episodes": len(episodes),
        "shadow_only_excluded_recordings": len(excluded_rows),
        "regime_totals": total_by_regime,
        "gaps": [row["regime"] for row in gap_rows if row["gap"]],
        "classification": {
            "physical_row_rule": "topic=term_status, owner=term, engaged=true, ready=true, vz_up and v_bz_applied numeric",
            "step_delta_mps": STEP_DELTA_MPS,
            "command_active_mps": COMMAND_ACTIVE_MPS,
            "episode_gap_s": EPISODE_GAP_S,
            "saturation_fraction": SATURATION_FRACTION,
            "authority_quality_threshold": AUTHORITY_LIMIT_QUALITY,
        },
    }
    with (out_dir / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True)

    covered = [row["regime"] for row in gap_rows if row["covered"]]
    gaps = [row["regime"] for row in gap_rows if row["gap"]]
    md_lines = [
        f"# R26-3 physical command-regime inventory ({head_short})",
        "",
        "Scope: real recorded `flight.jsonl` files under `fixtures/`; shadow-only TERM rows are listed but excluded from closure because R26-3 requires physically realized commands.",
        "",
        "## Method",
        "",
        f"- Physical TERM row: `term_status.owner == term`, `engaged=true`, `ready=true`, and numeric `vz_up` + `v_bz_applied`.",
        f"- Episode split: gap > {EPISODE_GAP_S:.2f}s.",
        f"- R26-3 up/down coverage uses the physical command sign: `vz_up` >= +/- {COMMAND_ACTIVE_MPS:.2f} m/s.",
        f"- Diagnostic slope steps are also recorded: `delta(vz_up)` >= +/- {STEP_DELTA_MPS:.2f} m/s inside an episode.",
        f"- Saturation: `abs(vz_up or v_bz_applied)` >= {SATURATION_FRACTION:.2f} * terminal `vz_max_mps` ({vz_max:.3f}).",
        f"- Authority-limited: `rate_anchor_quality` present and < {AUTHORITY_LIMIT_QUALITY:.3f}; absent authority fields are not counted as evidence.",
        "",
        "## Result",
        "",
        f"- Flight logs scanned: {len(manifests)}",
        f"- Recordings with physical TERM rows: {len(rows_by_flight)}",
        f"- Physical TERM rows: {len(physical_rows)} across {len(episodes)} episodes",
        f"- Shadow-only TERM recordings excluded: {len(excluded_rows)}",
        f"- Covered regimes: {', '.join(covered) if covered else 'none'}",
        f"- R26-3 gaps: {', '.join(gaps) if gaps else 'none'}",
        "",
        "## Regime Totals",
        "",
        "| Regime | Count |",
        "| --- | ---: |",
    ]
    for key, value in total_by_regime.items():
        md_lines.append(f"| {key} | {value} |")
    md_lines.extend(
        [
            "",
            "## Gap List",
            "",
            "| Regime | Covered | Physical evidence count | Route if gap |",
            "| --- | --- | ---: | --- |",
        ]
    )
    for row in gap_rows:
        md_lines.append(
            f"| {row['regime']} | {row['covered']} | {row['physical_evidence_count']} | {row['route_if_gap']} |"
        )
    md_lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "- `recording_manifest.csv`",
            "- `physical_term_rows.csv`",
            "- `episode_regime_inventory.csv`",
            "- `flight_regime_inventory.csv`",
            "- `r26_3_gap_list.csv`",
            "- `shadow_only_excluded.csv`",
            "- `summary.json`",
            "",
        ]
    )
    (out_dir / "summary.md").write_text("\n".join(md_lines), encoding="utf-8")
    print(out_dir)
    return out_dir


if __name__ == "__main__":
    inventory()
