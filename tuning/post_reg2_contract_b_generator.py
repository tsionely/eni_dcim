"""Post-REG2 Contract-B generator core for second-mechanism Step E.

This module intentionally separates the generator mechanics from the Step F
intervention run.  Startup verification is executable and ordered exactly as
REG-1 Section 5 requires; callers must pass that gate before any 23-approach
checkpoint is read or any result directory is created.
"""
from __future__ import annotations

from dataclasses import dataclass
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import subprocess
from typing import Callable, Iterable, Mapping, Sequence

REG2_COMMIT = "9393f9419ab00dabf1bd88ad095088ab984607ad"
REG2_DOC_PATH = Path("docs/criteria/legacy_response_model_registration.md")
CALIBRATION_DIR = Path("tuning/a091-response-model-calibration-0b60e91-20260721T061627Z")
CALIBRATION_DIGESTS = {
    "summary.json": "5b75963dfe127b90625bd942638a12d28c5bc74bb52e805abd049a095e0aecd5",
    "grid_candidate_scores.csv": "aa5f38745271e9e165e7c90f3b891ed68c3f96c27beff7781cae37cad4ffd106",
    "calibration_interval_keys.csv": "1a3526bfed17a7b116c68d340c5807fb454a38633376b432388099baab198c59",
    "sentinel_interval_keys.csv": "f59c7e0b827864c9ecb9fc4e6be338223a0cc6ec667935ad99e560f9950740ed",
    "candidate_windows.csv": "ac66b934c61dc9a933bb5115ad5085e47a4d66752773d95cd9c7eb44f7a78392",
}
SUPPORTED_INTERVENTION_ERA = "phase5c"
DT_S = 0.02
LARGE_B1_MPS2 = 0.35
QUIET_RMS_MPS = 0.05
EST_MIN_UNIQUE_AGES = 4
EST_MIN_SPAN_S = 0.15
EST_MIN_ROWS = 4
TERM_OWNER_TOKENS = ("TERM", "physical_TERM_episode_A091")
EXIT_REASONS = {
    "ABSENT_INPUT", "BURN_IN", "CLIPPED", "OWNERSHIP_SPLIT",
    "AGE_LOSS", "ESTIMABILITY_FAIL", "PENDING_TRANSPORT_PROOF",
}


class StartupContractError(RuntimeError):
    """Fail-fast startup error that records whether checkpoint was touched."""

    def __init__(self, code: str, message: str, checkpoint_touched: bool = False):
        super().__init__(message)
        self.code = code
        self.checkpoint_touched = checkpoint_touched


@dataclass(frozen=True)
class ContractBModel:
    g: float
    tau_s: float
    lag_ticks: int
    dt_s: float = DT_S
    vertical_cap_mps: float = 0.8

    @property
    def burn_in_s(self) -> float:
        return max(3.0 * self.tau_s, self.lag_ticks * self.dt_s)

    def initial_state(self, v_ref_up_mps: float) -> float:
        return self.g * float(v_ref_up_mps)

    def step(self, v_hat: float, v_ref_up_mps: float) -> float:
        alpha = self.dt_s / self.tau_s
        next_v = float(v_hat) + alpha * (self.g * float(v_ref_up_mps) - float(v_hat))
        return max(-self.vertical_cap_mps, min(self.vertical_cap_mps, next_v))


@dataclass(frozen=True)
class StartupAudit:
    reg2_commit: str
    generator_commit: str
    numeric_block_complete: bool
    model: ContractBModel
    calibration_dir: str
    verified_digests: Mapping[str, str]
    calibration_key_count: int
    sentinel_key_count: int
    calibration_sentinel_overlap: int
    checkpoint_touched: bool
    result_dir_created: bool


def _run_git(repo: Path, args: Sequence[str], *, text: bool = True) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=text, check=False
    )
    if completed.returncode != 0:
        stderr = completed.stderr if text else completed.stderr.decode("utf-8", "replace")
        raise StartupContractError("GIT_FAILED", f"git {' '.join(args)} failed: {stderr}")
    return completed.stdout if text else completed.stdout.decode("utf-8", "replace")


def _commit_exists(repo: Path, commit: str) -> bool:
    r = subprocess.run(["git", "cat-file", "-t", commit], cwd=repo, capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == "commit"


def _is_ancestor(repo: Path, older: str, newer: str) -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", older, newer], cwd=repo).returncode == 0


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _numeric_block(text: str) -> str:
    marker = "## 4. NUMERIC BLOCK"
    if marker not in text:
        raise StartupContractError("REG2_NUMERIC_BLOCK_ABSENT", "REG-2 numeric block not found")
    block = text.split(marker, 1)[1]
    for end_marker in ("**REG-2 TYPED FLAGS", "REG-2 TYPED FLAGS", "## 5."):
        if end_marker in block:
            block = block.split(end_marker, 1)[0]
    return block


def parse_reg2_numeric_block(text: str) -> tuple[ContractBModel, Path, dict[str, str]]:
    block = _numeric_block(text)
    if "PENDING" in block or "PENDING_CALIBRATION" in block:
        raise StartupContractError("REG2_PENDING_FIELD", "REG-2 numeric block still contains pending fields")
    g_match = re.search(r"^\s*g\s*=\s*([0-9.]+)\s*$", block, re.MULTILINE)
    tau_match = re.search(r"^\s*tau\s*=\s*([0-9.]+)\s*s\s*$", block, re.MULTILINE)
    lag_match = re.search(r"^\s*L\s*=\s*(\d+)\s*ticks\s*$", block, re.MULTILINE)
    path_match = re.search(r"calibration_artifact_path\s*=\s*\n\s*(tuning/[^\s]+/)", block)
    if not (g_match and tau_match and lag_match and path_match):
        raise StartupContractError("REG2_PARSE_FAILED", "REG-2 numeric block is complete but not parseable")
    digest_pairs: dict[str, str] = {}
    for name in CALIBRATION_DIGESTS:
        pattern = re.escape(name) + r"(?:[^\n]*)\n\s*([0-9a-f]{64})"
        match = re.search(pattern, block)
        if not match:
            raise StartupContractError("REG2_DIGEST_PARSE_FAILED", f"missing digest for {name}")
        digest_pairs[name] = match.group(1)
    return (
        ContractBModel(float(g_match.group(1)), float(tau_match.group(1)), int(lag_match.group(1))),
        Path(path_match.group(1)),
        digest_pairs,
    )


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def verify_calibration_binding(repo: Path, calibration_dir: Path, digests: Mapping[str, str]) -> tuple[int, int, int]:
    for name, expected in digests.items():
        path = repo / calibration_dir / name
        if not path.exists():
            raise StartupContractError("CALIBRATION_ARTIFACT_ABSENT", f"missing {path}")
        got = sha256_file(path)
        if got != expected:
            raise StartupContractError("CALIBRATION_DIGEST_MISMATCH", f"{name} digest {got} != {expected}")
    cal_rows = _read_csv(repo / calibration_dir / "calibration_interval_keys.csv")
    sentinel_rows = _read_csv(repo / calibration_dir / "sentinel_interval_keys.csv")
    cal_keys = {r.get("row_key", "") for r in cal_rows if r.get("row_key")}
    sentinel_keys = {r.get("row_key", "") for r in sentinel_rows if r.get("row_key")}
    if len(cal_keys) != 13:
        raise StartupContractError("CALIBRATION_KEY_COUNT", f"expected 13 calibration row keys, got {len(cal_keys)}")
    if len(sentinel_keys) != 31:
        raise StartupContractError("SENTINEL_KEY_COUNT", f"expected 31 sentinel row keys, got {len(sentinel_keys)}")
    overlap = len(cal_keys & sentinel_keys)
    if overlap != 0:
        raise StartupContractError("CALIBRATION_SENTINEL_OVERLAP", f"calibration/sentinel overlap={overlap}")
    if {r.get("event_id") for r in cal_rows} != {"A091_DOWNSTEP_01"}:
        raise StartupContractError("CALIBRATION_EVENT_BINDING", "calibration rows are not bound to A091_DOWNSTEP_01")
    return len(cal_keys), len(sentinel_keys), overlap


def startup_contract(
    repo: Path,
    *,
    required_reg2_commit: str = REG2_COMMIT,
    generator_commit: str | None = None,
    reg2_text_override: str | None = None,
    checkpoint_loader: Callable[[], object] | None = None,
    result_dir_factory: Callable[[], object] | None = None,
    touch_checkpoint: bool = False,
) -> StartupAudit:
    """Execute REG-1 Section 5 startup ordering.

    The 23-approach checkpoint and result directory hooks are deliberately
    invoked only after REG-2 resolution, ancestry, numeric parsing, digest
    verification, and row-key binding have all succeeded.
    """
    checkpoint_touched = False
    result_dir_created = False
    if not _commit_exists(repo, required_reg2_commit):
        raise StartupContractError("REG2_COMMIT_ABSENT", f"REG-2 commit {required_reg2_commit} does not resolve")
    if generator_commit is None:
        generator_commit = _run_git(repo, ["rev-parse", "HEAD"]).strip()
    if not _is_ancestor(repo, required_reg2_commit, generator_commit):
        raise StartupContractError("REG2_NOT_ANCESTOR", f"{required_reg2_commit} is not ancestor of {generator_commit}")
    text = reg2_text_override
    if text is None:
        text = (repo / REG2_DOC_PATH).read_text(encoding="utf-8")
    model, calibration_dir, parsed_digests = parse_reg2_numeric_block(text)
    if calibration_dir != CALIBRATION_DIR:
        raise StartupContractError("CALIBRATION_PATH_MISMATCH", f"unexpected calibration path {calibration_dir}")
    if set(parsed_digests) != set(CALIBRATION_DIGESTS):
        raise StartupContractError("CALIBRATION_DIGEST_REGISTRY_MISMATCH", "parsed digest file set differs from generator registry")
    cal_n, sentinel_n, overlap = verify_calibration_binding(repo, calibration_dir, parsed_digests)
    if touch_checkpoint:
        if checkpoint_loader is None:
            raise StartupContractError("CHECKPOINT_LOADER_ABSENT", "touch_checkpoint requested without loader")
        checkpoint_loader()
        checkpoint_touched = True
        if result_dir_factory is not None:
            result_dir_factory()
            result_dir_created = True
    return StartupAudit(
        reg2_commit=required_reg2_commit,
        generator_commit=generator_commit,
        numeric_block_complete=True,
        model=model,
        calibration_dir=str(calibration_dir).replace("\\", "/"),
        verified_digests=dict(parsed_digests),
        calibration_key_count=cal_n,
        sentinel_key_count=sentinel_n,
        calibration_sentinel_overlap=overlap,
        checkpoint_touched=checkpoint_touched,
        result_dir_created=result_dir_created,
    )


def world_up_from_body_z(v_body_z: float, level_pitch_rad: float, level_roll_rad: float) -> float:
    return -float(v_body_z) * math.cos(float(level_pitch_rad)) * math.cos(float(level_roll_rad))


def sensitivity_profile_rows(model: ContractBModel) -> list[dict[str, object]]:
    rows = []
    for g in (0.50, 0.55):
        for tau in (0.56, 0.60):
            rows.append({
                "g": g,
                "tau_s": tau,
                "L_ticks": 0,
                "profile_box_corner": True,
                "g_min_face": "OPEN" if g == 0.50 else "CLOSED_PROFILE_EDGE",
                "tau_max_face": "OPEN" if tau == 0.60 else "CLOSED_PROFILE_EDGE",
                "boundary_optimum_flag": "BOUNDARY_OPTIMUM",
                "boundary_open_note": "g-min and tau-max faces are open; sensitivity band understates uncertainty in lower-g/higher-tau directions",
                "active_model_g": model.g,
                "active_model_tau_s": model.tau_s,
                "active_model_L_ticks": model.lag_ticks,
            })
    return rows


def _owner_kind(owner_state: str | None) -> str:
    text = str(owner_state or "")
    if any(tok in text for tok in TERM_OWNER_TOKENS):
        return "TERM"
    return "LEGACY"


def split_mixed_owner_rows(rows: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    grouped: dict[tuple[str, str], list[Mapping[str, object]]] = {}
    for row in rows:
        grouped.setdefault((str(row.get("approach_id")), str(row.get("cut_id"))), []).append(row)
    for (_approach, cut_id), group in grouped.items():
        ordered = sorted(group, key=lambda r: (float(r.get("age_s", 0.0)), str(r.get("row_key", ""))))
        owners = [_owner_kind(str(r.get("owner_state", ""))) for r in ordered]
        mixed = len(set(owners)) > 1
        seg_index = 0
        prev_owner = None
        for row, owner in zip(ordered, owners):
            if owner != prev_owner:
                seg_index += 1
                prev_owner = owner
            new = dict(row)
            new["owner_kind"] = owner
            new["mixed_owner_split"] = mixed
            new["cut_segment_id"] = f"{cut_id}:seg{seg_index:02d}_{owner}" if mixed else cut_id
            new["ownership_segment_index"] = seg_index
            if mixed:
                new["split_exit_reason"] = "OWNERSHIP_SPLIT"
            out.append(new)
    return out


def _num(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    return v


def apply_contract_b_response(rows: Sequence[Mapping[str, object]], model: ContractBModel) -> list[dict[str, object]]:
    """Attach Contract-B correction and corrected residuals to row dicts.

    This is the signal-chain implementation only.  It does not read archive
    checkpoints or create artifacts by itself.
    """
    split_rows = split_mixed_owner_rows(rows)
    groups: dict[str, list[dict[str, object]]] = {}
    for row in split_rows:
        groups.setdefault(str(row.get("cut_segment_id")), []).append(row)
    out: list[dict[str, object]] = []
    for _seg, group in groups.items():
        ordered = sorted(group, key=lambda r: (int(r.get("tick", 0)), float(r.get("age_s", 0.0))))
        v_hat: float | None = None
        clipped_count = 0
        for row in ordered:
            new = dict(row)
            era = str(row.get("era", ""))
            owner = str(row.get("owner_kind") or _owner_kind(str(row.get("owner_state", ""))))
            age = _num(row.get("age_s"))
            v_ref = _num(row.get("v_ref_up_mps"))
            v_ref_oracle = _num(row.get("v_ref_oracle_mps"))
            v_latch = _num(row.get("v_latch_true_mps"))
            feed_forward = _num(row.get("feed_forward_mps"))
            if feed_forward is None:
                feed_forward = 0.0
            before = _num(row.get("r_v_before_mps"))
            if before is None and v_ref_oracle is not None and v_latch is not None:
                before = v_ref_oracle - (v_latch + feed_forward)
            new["r_v_before_mps"] = "" if before is None else before
            new["correction_term_mps"] = ""
            new["support_status"] = "VALID"
            new["input_status"] = "VALID"
            new["exit_reason"] = ""
            new["residual_sign_convention"] = "r_v_corrected = v_ref_oracle - (v_latch_true + feed_forward + v_hat)"
            if era != SUPPORTED_INTERVENTION_ERA:
                new["support_status"] = "OFF_SUPPORT"
                new["input_status"] = "OFF_SUPPORT"
                new["exit_reason"] = "PENDING_TRANSPORT_PROOF"
                out.append(new)
                continue
            if owner == "TERM":
                new["correction_term_mps"] = 0.0
                new["r_v_corrected_mps"] = "" if before is None else before
                new["support_status"] = "VALID_TERM_STRUCTURAL_NOOP"
                new["input_status"] = "VALID_TERM_STRUCTURAL_NOOP"
                out.append(new)
                continue
            if v_ref is None or age is None or v_ref_oracle is None or v_latch is None:
                new["support_status"] = "OFF_SUPPORT"
                new["input_status"] = "OFF_SUPPORT"
                new["exit_reason"] = "ABSENT_INPUT"
                out.append(new)
                continue
            if age < model.burn_in_s:
                new["support_status"] = "OFF_SUPPORT"
                new["input_status"] = "OFF_SUPPORT"
                new["exit_reason"] = "BURN_IN"
                out.append(new)
                if v_hat is None:
                    v_hat = model.initial_state(v_ref)
                continue
            if v_hat is None:
                v_hat = model.initial_state(v_ref)
            else:
                v_hat = model.step(v_hat, v_ref)
            if abs(v_hat) >= model.vertical_cap_mps:
                clipped_count += 1
                new["clip_event"] = True
            else:
                new["clip_event"] = False
            new["correction_term_mps"] = v_hat
            new["r_v_corrected_mps"] = v_ref_oracle - (v_latch + feed_forward + v_hat)
            out.append(new)
        if clipped_count > len(ordered) / 2:
            for row in out:
                if row.get("cut_segment_id") == _seg:
                    row["support_status"] = "OFF_SUPPORT"
                    row["input_status"] = "OFF_SUPPORT"
                    row["exit_reason"] = "CLIPPED"
                    row.pop("r_v_corrected_mps", None)
    return out


def theil_sen_slope(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    slopes: list[float] = []
    for i, xi in enumerate(xs):
        for j in range(i + 1, len(xs)):
            dx = xs[j] - xi
            if dx != 0.0:
                slopes.append((ys[j] - ys[i]) / dx)
    if not slopes:
        return None
    return float(statistics.median(slopes))


def ols_slope_intercept(xs: Sequence[float], ys: Sequence[float]) -> tuple[float | None, float | None]:
    if len(xs) < 2:
        return None, None
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0.0:
        return None, None
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
    return float(my - slope * mx), float(slope)


def fit_cut(points: Sequence[Mapping[str, object]], residual_key: str = "r_v_mps") -> dict[str, object]:
    valid = []
    for point in points:
        age = _num(point.get("age_s"))
        residual = _num(point.get(residual_key))
        if age is not None and residual is not None:
            valid.append((age, residual))
    unique_ages = sorted({a for a, _ in valid})
    if len(valid) < EST_MIN_ROWS or len(unique_ages) < EST_MIN_UNIQUE_AGES:
        return {"estimable": False, "exit_reason": "ESTIMABILITY_FAIL", "n_rows": len(valid), "unique_ages": len(unique_ages), "age_span_s": 0.0}
    age_span = max(unique_ages) - min(unique_ages)
    if age_span < EST_MIN_SPAN_S:
        return {"estimable": False, "exit_reason": "AGE_LOSS", "n_rows": len(valid), "unique_ages": len(unique_ages), "age_span_s": age_span}
    xs = [a for a, _ in valid]
    ys = [r for _, r in valid]
    ts = theil_sen_slope(xs, ys)
    b0_ols, b1_ols = ols_slope_intercept(xs, ys)
    if ts is None or b1_ols is None:
        return {"estimable": False, "exit_reason": "ESTIMABILITY_FAIL", "n_rows": len(valid), "unique_ages": len(unique_ages), "age_span_s": age_span}
    intercept_ts = statistics.median([y - ts * x for x, y in valid])
    ts_large = abs(ts) > LARGE_B1_MPS2
    ols_large = abs(b1_ols) > LARGE_B1_MPS2
    return {
        "estimable": True,
        "exit_reason": "",
        "n_rows": len(valid),
        "unique_ages": len(unique_ages),
        "age_span_s": age_span,
        "b0_theil_sen_mps": float(intercept_ts),
        "b1_theil_sen_mps2": float(ts),
        "b0_ols_mps": b0_ols,
        "b1_ols_mps2": b1_ols,
        "large_theil_sen": ts_large,
        "large_ols": ols_large,
        "theil_sen_ols_boundary_disagreement": ts_large != ols_large,
    }


def points_for_line(slope: float, intercept: float = 0.0, ages: Sequence[float] = (0.0, 0.06, 0.16, 0.24, 0.32)) -> list[dict[str, float]]:
    return [{"age_s": float(a), "r_v_mps": float(intercept + slope * a)} for a in ages]


def rms(values: Iterable[float]) -> float:
    vals = [float(v) for v in values]
    return math.sqrt(sum(v * v for v in vals) / len(vals)) if vals else 0.0


def evaluate_cut_records(records: Sequence[Mapping[str, object]], *, input_validity_ok: bool = True) -> dict[str, object]:
    cut_rows: list[dict[str, object]] = []
    approach_data: dict[str, dict[str, object]] = {}
    for rec in records:
        aid = str(rec["approach_id"])
        cid = str(rec["cut_id"])
        before_fit = fit_cut(rec.get("before_points", []), "r_v_mps")
        after_exit = str(rec.get("after_exit_reason", "") or "")
        after_points = rec.get("after_points")
        after_fit = fit_cut(after_points or [], "r_v_mps") if after_points is not None and not after_exit else {"estimable": False, "exit_reason": after_exit or "ABSENT_INPUT"}
        paired = bool(before_fit.get("estimable") and after_fit.get("estimable") and not after_exit)
        if after_exit and after_exit not in EXIT_REASONS:
            raise ValueError(f"unregistered exit reason {after_exit}")
        activity = rec.get("model_activity_rms_mps")
        if activity is None:
            corrections = rec.get("correction_terms_mps", [])
            activity = rms([float(x) for x in corrections]) if corrections else 0.0
        row = {
            "approach_id": aid,
            "cut_id": cid,
            "before_estimable": bool(before_fit.get("estimable")),
            "after_estimable": bool(after_fit.get("estimable")),
            "paired_support": paired,
            "before_large": bool(before_fit.get("large_theil_sen")),
            "after_large": bool(after_fit.get("large_theil_sen")),
            "after_exit_reason": after_fit.get("exit_reason", ""),
            "model_activity_rms_mps": float(activity),
            "near_zero_activity": float(activity) < QUIET_RMS_MPS,
            "b1_before_theil_sen_mps2": before_fit.get("b1_theil_sen_mps2", ""),
            "b1_before_ols_mps2": before_fit.get("b1_ols_mps2", ""),
            "b1_after_theil_sen_mps2": after_fit.get("b1_theil_sen_mps2", ""),
            "b1_after_ols_mps2": after_fit.get("b1_ols_mps2", ""),
            "boundary_disagreement_before": bool(before_fit.get("theil_sen_ols_boundary_disagreement")),
            "boundary_disagreement_after": bool(after_fit.get("theil_sen_ols_boundary_disagreement")),
        }
        cut_rows.append(row)
        data = approach_data.setdefault(aid, {"before_cuts": [], "after_cuts": [], "paired_cuts": [], "missing": [], "near_zero_after_large": False})
        if before_fit.get("estimable"):
            data["before_cuts"].append(row)
        if after_fit.get("estimable"):
            data["after_cuts"].append(row)
        if paired:
            data["paired_cuts"].append(row)
        elif before_fit.get("estimable"):
            data["missing"].append(row)
        if row["after_large"] and row["near_zero_activity"]:
            data["near_zero_after_large"] = True
    S_B = {aid for aid, data in approach_data.items() if any(c["before_large"] for c in data["before_cuts"])}
    S_A = {aid for aid, data in approach_data.items() if any(c["after_large"] for c in data["after_cuts"])}
    M_RESOLUTION = 0
    M_HARM = 0
    support_losses: list[dict[str, object]] = []
    for aid, data in approach_data.items():
        for cut in data["before_cuts"]:
            if cut not in data["paired_cuts"]:
                reason = str(cut.get("after_exit_reason") or "ABSENT_INPUT")
                support_losses.append({"approach_id": aid, "cut_id": cut["cut_id"], "exit_reason": reason, "baseline_large_cut": cut["before_large"]})
                if cut["before_large"]:
                    M_RESOLUTION += 1
                M_HARM += 1
    R = S_B - S_A
    S = S_B & S_A
    N = S_A - S_B
    Q_ids = {aid for aid, data in approach_data.items() if data["near_zero_after_large"]}
    C_P = {aid for aid, data in approach_data.items() if data["paired_cuts"]}
    summary = {
        "input_validity_ok": input_validity_ok,
        "C_B": sorted(S_B),
        "C_A": sorted(S_A),
        "C_P": sorted(C_P),
        "S_B": sorted(S_B),
        "S_A": sorted(S_A),
        "R": sorted(R),
        "S": sorted(S),
        "N": sorted(N),
        "Q_ids": sorted(Q_ids),
        "B": len(S_B),
        "M_RESOLUTION": M_RESOLUTION,
        "M_HARM": M_HARM,
        "support_losses": support_losses,
        "cut_rows": cut_rows,
    }
    decision = resolve_decision(summary)
    summary["decision"] = decision
    summary.update(decision)
    return summary


def residual_admissibility_for_branch(branch: str) -> str:
    mapping = {
        "INVALID_INPUT": "INADMISSIBLE",
        "NO_REGISTERED_REMAINDER_TO_EXPLAIN": "NO_RESIDUAL_CLAIM",
        "HOLD_INCOMPLETE_INTERVENTION_SUPPORT": "INADMISSIBLE",
        "REFUTED_OR_HARMFUL_INTERVENTION": "INADMISSIBLE",
        "REFUTED": "INADMISSIBLE",
        "HOLD_INCONCLUSIVE_QUIET_BREACH": "DIAGNOSTIC_ONLY",
        "CONFIRMED_SUFFICIENT_FOR_EVALUATOR": "CANDIDATE_EVALUATOR_CORRECTED_STATISTICAL_INPUT",
        "CONTRIBUTORY_NOT_SUFFICIENT": "DIAGNOSTIC_ONLY",
        "REFUTED_AS_REGISTERED_REMAINDER_EXPLANATION": "INADMISSIBLE",
    }
    return mapping[branch]


def resolve_decision(summary: Mapping[str, object]) -> dict[str, object]:
    input_ok = bool(summary.get("input_validity_ok", True))
    B = int(summary.get("B", len(summary.get("S_B", []))))
    M_RESOLUTION = int(summary.get("M_RESOLUTION", 0))
    M_HARM = int(summary.get("M_HARM", 0))
    N = set(summary.get("N", []))
    Q_ids = set(summary.get("Q_ids", []))
    S_B = set(summary.get("S_B", []))
    S_A = set(summary.get("S_A", []))
    R = set(summary.get("R", S_B - S_A))
    if not input_ok:
        branch = "INVALID_INPUT"
        order = 1
    elif B == 0:
        branch = "NO_REGISTERED_REMAINDER_TO_EXPLAIN"
        order = 2
    elif M_RESOLUTION > 0 or M_HARM > 0:
        branch = "HOLD_INCOMPLETE_INTERVENTION_SUPPORT"
        order = 3
    elif N:
        branch = "REFUTED_OR_HARMFUL_INTERVENTION"
        order = 4
    elif len(Q_ids) >= 2:
        branch = "REFUTED"
        order = 5
    elif len(Q_ids) > 0:
        branch = "HOLD_INCONCLUSIVE_QUIET_BREACH"
        order = 6
    elif len(R) >= math.ceil(B / 2):
        branch = "CONFIRMED_SUFFICIENT_FOR_EVALUATOR"
        order = 7
    elif len(R) > 0:
        branch = "CONTRIBUTORY_NOT_SUFFICIENT"
        order = 8
    else:
        branch = "REFUTED_AS_REGISTERED_REMAINDER_EXPLANATION"
        order = 9
    return {
        "branch": branch,
        "branch_order": order,
        "residual_admissibility": residual_admissibility_for_branch(branch),
        "S_ids": sorted(S_B & S_A),
        "N_ids": sorted(N),
    }


def canonical_residual_slice_sha(rows: Sequence[Mapping[str, object]], residual_key: str) -> str:
    payload = [
        {"row_key": str(r.get("row_key", "")), "residual": _num(r.get(residual_key))}
        for r in sorted(rows, key=lambda x: str(x.get("row_key", "")))
    ]
    data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Post-REG2 Contract-B generator startup gate")
    parser.add_argument("--startup-only", action="store_true", help="verify startup contract but do not read checkpoint")
    parser.add_argument("--repo", default=".")
    args = parser.parse_args(argv)
    audit = startup_contract(Path(args.repo).resolve(), touch_checkpoint=False)
    print(json.dumps({
        "status": "STARTUP_CONTRACT_OK",
        "reg2_commit": audit.reg2_commit,
        "generator_commit": audit.generator_commit,
        "model": {"g": audit.model.g, "tau_s": audit.model.tau_s, "L_ticks": audit.model.lag_ticks},
        "checkpoint_touched": audit.checkpoint_touched,
        "result_dir_created": audit.result_dir_created,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
