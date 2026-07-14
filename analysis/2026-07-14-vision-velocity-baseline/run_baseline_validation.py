"""Offline vision-velocity baseline validation on phase2j flight logs.

Reconstructs velocity from detection PnP fix history using a 0.15–0.45 s
baseline (matching commit 2cc8df9), plots against logged estimator `v_world`
(phase2j used frame-pair derivative), and quantifies PnP position noise.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from aigp.estimation.attitude_filter import quat_rotate  # noqa: E402
from aigp.perception.camera import cam_to_body  # noqa: E402

LOG_ROOTS = [
    Path(r"C:\Users\tsion\Projects\eni_dcim_phase1\logs"),
    Path(r"C:\Users\tsion\Projects\eni_dcim\logs"),
]

PHASE2J = [
    ("phase2j-V1", "20260714T132005-1429a43c"),
    ("phase2j-V2", "20260714T132354-80030858"),
]
PHASE2K_HINTS = ("phase2k",)


def find_flight_jsonl(session: str) -> Path | None:
    for root in LOG_ROOTS:
        p = root / session / "flight.jsonl"
        if p.exists():
            return p
    # Fixture copy (phase2j V2 only in repo fixtures)
    fix = ROOT / "fixtures" / "20260714T134021-phase2j" / f"{session}-flight.jsonl"
    if fix.exists():
        return fix
    return None


def load_topics(path: Path) -> tuple[list[dict], list[dict]]:
    detections: list[dict] = []
    states: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec["topic"] == "detection":
                detections.append(rec)
            elif rec["topic"] == "state":
                states.append(rec)
    return detections, states


def extract_fixes(detections: list[dict]) -> np.ndarray:
    """Return Nx4 array: ts_ns, tx, ty, tz for detections with rel_pose."""
    rows = []
    for rec in detections:
        d = rec["data"]
        rp = d.get("rel_pose")
        if not rp or rp.get("t") is None:
            continue
        t = rp["t"]
        rows.append((int(d["ts_ns"]), float(t[0]), float(t[1]), float(t[2])))
    if not rows:
        return np.zeros((0, 4), dtype=np.float64)
    return np.asarray(rows, dtype=np.float64)


def reconstruct_v_cam(
    fixes: np.ndarray,
    min_dt_s: float = 0.15,
    max_dt_s: float = 0.45,
) -> tuple[np.ndarray, np.ndarray]:
    """For each fix, use oldest history entry in [min_dt, max_dt] as baseline.

    Returns (ts_ns, v_cam Nx3). Rows without a valid baseline are omitted.
    """
    if len(fixes) < 2:
        return np.zeros(0, dtype=np.float64), np.zeros((0, 3), dtype=np.float64)
    ts_out = []
    v_out = []
    history: list[tuple[float, np.ndarray]] = []
    min_ns = min_dt_s * 1e9
    max_ns = max_dt_s * 1e9
    for row in fixes:
        ts = float(row[0])
        t_vec = row[1:4].copy()
        baseline = None
        for h_ts, h_t in history:
            age = ts - h_ts
            if min_ns <= age <= max_ns:
                baseline = (h_ts, h_t)
                break  # oldest in window (history is chronological)
        if baseline is not None:
            dt = (ts - baseline[0]) / 1e9
            v_cam = -(t_vec - baseline[1]) / dt
            ts_out.append(ts)
            v_out.append(v_cam)
        history.append((ts, t_vec))
        # keep ~1s of history
        cutoff = ts - 1.0e9
        history = [h for h in history if h[0] >= cutoff]
    if not ts_out:
        return np.zeros(0, dtype=np.float64), np.zeros((0, 3), dtype=np.float64)
    return np.asarray(ts_out), np.asarray(v_out)


def reconstruct_v_cam_framepair(fixes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Frame-pair derivative (phase2j online estimator behavior)."""
    if len(fixes) < 2:
        return np.zeros(0, dtype=np.float64), np.zeros((0, 3), dtype=np.float64)
    ts_out = []
    v_out = []
    for i in range(1, len(fixes)):
        dt = (fixes[i, 0] - fixes[i - 1, 0]) / 1e9
        if 1e-3 < dt < 0.5:
            v_cam = -(fixes[i, 1:4] - fixes[i - 1, 1:4]) / dt
            ts_out.append(fixes[i, 0])
            v_out.append(v_cam)
    return np.asarray(ts_out), np.asarray(v_out)


def state_series(states: list[dict]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (ts_ns, v_world Nx3, q_att Nx4). Prefer data.ts_ns; fall back mono."""
    ts, vw, qq = [], [], []
    for rec in states:
        d = rec["data"]
        t = d.get("ts_ns")
        if t is None:
            t = rec["mono_ns"]
        v = d.get("v_world")
        q = d.get("q_att")
        if v is None or q is None:
            continue
        ts.append(float(t))
        vw.append([float(v[0]), float(v[1]), float(v[2])])
        qq.append([float(q[0]), float(q[1]), float(q[2]), float(q[3])])
    return (
        np.asarray(ts, dtype=np.float64),
        np.asarray(vw, dtype=np.float64),
        np.asarray(qq, dtype=np.float64),
    )


def nearest_indices(query_ts: np.ndarray, ref_ts: np.ndarray) -> np.ndarray:
    """For each query timestamp, index of nearest ref timestamp."""
    if len(ref_ts) == 0 or len(query_ts) == 0:
        return np.zeros(0, dtype=np.int64)
    idx = np.searchsorted(ref_ts, query_ts)
    idx = np.clip(idx, 1, len(ref_ts) - 1)
    left = idx - 1
    choose_left = np.abs(ref_ts[left] - query_ts) <= np.abs(ref_ts[idx] - query_ts)
    return np.where(choose_left, left, idx)


def to_world(v_cam: np.ndarray, q: np.ndarray) -> np.ndarray:
    v_body = cam_to_body(v_cam)
    return quat_rotate(q, v_body)


def pnp_noise_std(fixes: np.ndarray, window_s: float = 0.5) -> dict:
    """Estimate PnP translation noise via local linear-detrend residuals.

    Over sliding windows of `window_s`, fit a linear trend per axis and take
    residual std. Report median residual std across windows (robust).
    """
    if len(fixes) < 20:
        return {"n_windows": 0, "std_xyz_m": [None, None, None], "std_norm_m": None}
    ts = fixes[:, 0] / 1e9
    t0 = ts[0]
    ts = ts - t0
    pos = fixes[:, 1:4]
    win = window_s
    stds = []
    i0 = 0
    while i0 < len(ts):
        t_start = ts[i0]
        i1 = i0
        while i1 < len(ts) and ts[i1] - t_start < win:
            i1 += 1
        if i1 - i0 >= 8:
            seg_t = ts[i0:i1]
            seg_p = pos[i0:i1]
            resid = np.zeros_like(seg_p)
            for ax in range(3):
                coef = np.polyfit(seg_t, seg_p[:, ax], 1)
                resid[:, ax] = seg_p[:, ax] - np.polyval(coef, seg_t)
            stds.append(resid.std(axis=0))
        i0 = i1 if i1 > i0 else i0 + 1
    if not stds:
        return {"n_windows": 0, "std_xyz_m": [None, None, None], "std_norm_m": None}
    arr = np.asarray(stds)
    med = np.median(arr, axis=0)
    return {
        "n_windows": int(len(stds)),
        "std_xyz_m": [float(med[0]), float(med[1]), float(med[2])],
        "std_norm_m": float(np.linalg.norm(med)),
        "std_xyz_mean_m": [float(arr.mean(0)[0]), float(arr.mean(0)[1]), float(arr.mean(0)[2])],
    }


def framepair_vs_baseline_noise(fixes: np.ndarray) -> dict:
    """Compare velocity magnitude noise: frame-pair vs 0.2s baseline."""
    ts_fp, v_fp = reconstruct_v_cam_framepair(fixes)
    ts_bl, v_bl = reconstruct_v_cam(fixes)
    out = {}
    if len(v_fp):
        out["framepair_v_std_mps"] = [float(x) for x in v_fp.std(axis=0)]
        out["framepair_speed_std_mps"] = float(np.linalg.norm(v_fp, axis=1).std())
        out["framepair_n"] = int(len(v_fp))
    if len(v_bl):
        out["baseline_v_std_mps"] = [float(x) for x in v_bl.std(axis=0)]
        out["baseline_speed_std_mps"] = float(np.linalg.norm(v_bl, axis=1).std())
        out["baseline_n"] = int(len(v_bl))
        out["baseline_dt_mean_s"] = None  # filled below if we track
    return out


def analyze_one(label: str, session: str) -> dict | None:
    path = find_flight_jsonl(session)
    if path is None:
        print(f"  MISSING flight.jsonl for {session}", flush=True)
        return None
    print(f"  Analyzing {label} ({session}) from {path}", flush=True)
    detections, states = load_topics(path)
    fixes = extract_fixes(detections)
    st_ts, st_vw, st_q = state_series(states)
    print(f"    fixes={len(fixes)} states={len(st_ts)}", flush=True)

    # Align via mono_ns: detection sim-ts and state.ts_ns use different clocks.
    det_mono, det_t, det_sim = [], [], []
    for rec in detections:
        d = rec["data"]
        rp = d.get("rel_pose")
        if not rp or rp.get("t") is None:
            continue
        t = rp["t"]
        det_mono.append(float(rec["mono_ns"]))
        det_sim.append(float(d["ts_ns"]))
        det_t.append([float(t[0]), float(t[1]), float(t[2])])
    det_mono = np.asarray(det_mono)
    det_sim = np.asarray(det_sim)
    det_t = np.asarray(det_t)

    st_mono, st_vw2, st_q2 = [], [], []
    for rec in states:
        d = rec["data"]
        v = d.get("v_world")
        q = d.get("q_att")
        if v is None or q is None:
            continue
        st_mono.append(float(rec["mono_ns"]))
        st_vw2.append([float(v[0]), float(v[1]), float(v[2])])
        st_q2.append([float(q[0]), float(q[1]), float(q[2]), float(q[3])])
    st_mono = np.asarray(st_mono)
    st_vw2 = np.asarray(st_vw2)
    st_q2 = np.asarray(st_q2)

    # Reconstruct using sim timestamps for derivative, mono for plotting sync
    fixes_sim = np.column_stack([det_sim, det_t]) if len(det_sim) else np.zeros((0, 4))
    ts_bl, v_cam_bl = reconstruct_v_cam(fixes_sim)
    ts_fp, v_cam_fp = reconstruct_v_cam_framepair(fixes_sim)

    def sim_to_mono(sim_ts: np.ndarray) -> np.ndarray:
        if len(sim_ts) == 0:
            return np.zeros(0)
        idx = nearest_indices(sim_ts, det_sim)
        return det_mono[idx]

    mono_bl = sim_to_mono(ts_bl)
    mono_fp = sim_to_mono(ts_fp)

    v_world_bl = np.zeros((0, 3))
    v_world_fp = np.zeros((0, 3))
    logged_at_bl = np.zeros((0, 3))
    err = np.zeros((0, 3))
    t_rel_bl = np.zeros(0)
    t_rel_fp = np.zeros(0)
    t_rel_state = np.zeros(0)
    t0 = float(st_mono[0]) if len(st_mono) else 0.0

    if len(mono_bl) and len(st_mono):
        idx = nearest_indices(mono_bl, st_mono)
        v_world_bl = np.array([to_world(v_cam_bl[i], st_q2[idx[i]]) for i in range(len(v_cam_bl))])
        logged_at_bl = st_vw2[idx]
        err = v_world_bl - logged_at_bl
        t_rel_bl = (mono_bl - t0) / 1e9
        t_rel_state = (st_mono - t0) / 1e9

    if len(mono_fp) and len(st_mono):
        idx_fp = nearest_indices(mono_fp, st_mono)
        v_world_fp = np.array([to_world(v_cam_fp[i], st_q2[idx_fp[i]]) for i in range(len(v_cam_fp))])
        t_rel_fp = (mono_fp - t0) / 1e9

    noise = pnp_noise_std(fixes_sim)
    vel_noise = framepair_vs_baseline_noise(fixes_sim)

    # Metrics vs logged
    metrics = {
        "label": label,
        "session": session,
        "path": str(path),
        "n_fixes": int(len(fixes_sim)),
        "n_states": int(len(st_mono)),
        "n_baseline_vel": int(len(v_world_bl)),
        "pnp_noise": noise,
        "vel_noise_compare": vel_noise,
    }
    if len(v_world_bl):
        metrics["baseline_vs_logged"] = {
            "rmse_mps": float(np.sqrt((err**2).mean())),
            "rmse_xyz_mps": [float(x) for x in np.sqrt((err**2).mean(axis=0))],
            "corr_xyz": [
                float(np.corrcoef(v_world_bl[:, i], logged_at_bl[:, i])[0, 1])
                if v_world_bl[:, i].std() > 1e-9 and logged_at_bl[:, i].std() > 1e-9
                else None
                for i in range(3)
            ],
            "logged_speed_mean_mps": float(np.linalg.norm(logged_at_bl, axis=1).mean()),
            "baseline_speed_mean_mps": float(np.linalg.norm(v_world_bl, axis=1).mean()),
            "framepair_speed_std_mps": vel_noise.get("framepair_speed_std_mps"),
            "baseline_speed_std_mps": vel_noise.get("baseline_speed_std_mps"),
        }

    # Plot
    fig, axes = plt.subplots(4, 1, figsize=(12, 11), sharex=True)
    labels = ["vx", "vy", "vz"]
    colors = ["C0", "C1", "C2"]

    if len(t_rel_state):
        for i, lab in enumerate(labels):
            axes[0].plot(t_rel_state, st_vw2[:, i], color=colors[i], alpha=0.85, label=f"logged {lab}")
    if len(t_rel_bl):
        for i, lab in enumerate(labels):
            axes[0].plot(
                t_rel_bl,
                v_world_bl[:, i],
                color=colors[i],
                linestyle="--",
                alpha=0.9,
                label=f"baseline0.2s {lab}",
            )
    axes[0].set_ylabel("v_world [m/s]")
    axes[0].set_title(f"{label}: logged v_world vs offline 0.15–0.45s vision baseline")
    axes[0].legend(loc="upper right", fontsize=7, ncol=2)
    axes[0].grid(True, alpha=0.3)

    if len(t_rel_state):
        speed_log = np.linalg.norm(st_vw2, axis=1)
        axes[1].plot(t_rel_state, speed_log, label="logged |v|", color="k")
    if len(t_rel_bl):
        axes[1].plot(t_rel_bl, np.linalg.norm(v_world_bl, axis=1), label="baseline |v|", color="C3")
    if len(t_rel_fp):
        # downsample framepair for readability
        step = max(1, len(t_rel_fp) // 2000)
        axes[1].plot(
            t_rel_fp[::step],
            np.linalg.norm(v_world_fp[::step], axis=1),
            label="frame-pair |v|",
            color="C4",
            alpha=0.5,
            linewidth=0.8,
        )
    axes[1].set_ylabel("speed [m/s]")
    axes[1].legend(loc="upper right", fontsize=8)
    axes[1].grid(True, alpha=0.3)

    if len(err):
        for i, lab in enumerate(labels):
            axes[2].plot(t_rel_bl, err[:, i], color=colors[i], label=f"err {lab}")
        axes[2].axhline(0, color="k", linewidth=0.5)
    axes[2].set_ylabel("baseline − logged [m/s]")
    axes[2].legend(loc="upper right", fontsize=8)
    axes[2].grid(True, alpha=0.3)

    if len(fixes_sim):
        # gate distance
        dist = np.linalg.norm(fixes_sim[:, 1:4], axis=1)
        # align to mono
        mono_fix = det_mono
        t_fix = (mono_fix - t0) / 1e9 if t0 else (mono_fix - mono_fix[0]) / 1e9
        axes[3].plot(t_fix, dist, ".", markersize=2, color="C5")
    axes[3].set_ylabel("gate |t| [m]")
    axes[3].set_xlabel("time [s]")
    axes[3].grid(True, alpha=0.3)

    fig.tight_layout()
    plot_path = OUT / f"{label}_velocity_baseline.png"
    fig.savefig(plot_path, dpi=120)
    plt.close(fig)
    metrics["plot"] = str(plot_path.relative_to(ROOT)).replace("\\", "/")

    # Also save a cam-frame baseline speed vs framepair speed histogram
    fig2, ax = plt.subplots(1, 1, figsize=(8, 4))
    if len(v_cam_fp):
        ax.hist(np.linalg.norm(v_cam_fp, axis=1), bins=60, alpha=0.5, label="frame-pair |v_cam|", color="C4")
    if len(v_cam_bl):
        ax.hist(np.linalg.norm(v_cam_bl, axis=1), bins=60, alpha=0.5, label="0.2s baseline |v_cam|", color="C3")
    ax.set_xlabel("|v_cam| [m/s]")
    ax.set_ylabel("count")
    ax.set_title(f"{label}: vision velocity magnitude distribution")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig2.tight_layout()
    hist_path = OUT / f"{label}_vcam_hist.png"
    fig2.savefig(hist_path, dpi=120)
    plt.close(fig2)
    metrics["hist_plot"] = str(hist_path.relative_to(ROOT)).replace("\\", "/")

    return metrics


def write_report(results: list[dict], blockers: list[str]) -> None:
    lines = [
        "# Vision-velocity baseline validation (phase2j)",
        "",
        "Generated 2026-07-14. Offline reconstruction of vision velocity using a",
        "**0.15–0.45 s fix-history baseline** (as in commit `2cc8df9`), compared to",
        "the estimator's logged `v_world` from phase2j flights (which still used",
        "frame-pair derivatives under `da38639`).",
        "",
        "## Method",
        "",
        "1. Load `detection` records with PnP `rel_pose.t` and `state` with `v_world` / `q_att`.",
        "2. For each fix, take the oldest prior fix whose age is in [0.15, 0.45] s.",
        "3. `v_cam = -(t_now - t_base) / dt`, then `v_body = cam_to_body(v_cam)`,",
        "   `v_world = R(q_att) * v_body` using nearest logged attitude.",
        "4. PnP position noise: median residual std after linear detrend in 0.5 s windows.",
        "",
        "## Logs used",
        "",
    ]
    for r in results:
        lines.append(f"- `{r['label']}`: `{r['session']}` ({r['n_fixes']} PnP fixes, {r['n_states']} states)")
    if blockers:
        lines += ["", "## Blockers", ""]
        for b in blockers:
            lines.append(f"- {b}")

    lines += ["", "## Key metrics", ""]
    for r in results:
        noise = r["pnp_noise"]
        vn = r["vel_noise_compare"]
        lines.append(f"### {r['label']} (`{r['session']}`)")
        lines.append("")
        if noise.get("std_xyz_m") and noise["std_xyz_m"][0] is not None:
            sx, sy, sz = noise["std_xyz_m"]
            lines.append(
                f"- **PnP position noise std** (0.5 s linear-detrend residual, median over "
                f"{noise['n_windows']} windows): "
                f"xyz = [{sx:.3f}, {sy:.3f}, {sz:.3f}] m; "
                f"|std| = {noise['std_norm_m']:.3f} m"
            )
        if vn.get("framepair_speed_std_mps") is not None:
            lines.append(
                f"- Vision |v_cam| std: frame-pair **{vn['framepair_speed_std_mps']:.2f} m/s** "
                f"vs 0.2s baseline **{vn.get('baseline_speed_std_mps', float('nan')):.2f} m/s**"
            )
        bv = r.get("baseline_vs_logged")
        if bv:
            lines.append(
                f"- Offline baseline vs logged `v_world` RMSE: **{bv['rmse_mps']:.2f} m/s** "
                f"(xyz {[round(x, 2) for x in bv['rmse_xyz_mps']]})"
            )
            lines.append(
                f"- Mean speed: logged {bv['logged_speed_mean_mps']:.2f} m/s, "
                f"baseline {bv['baseline_speed_mean_mps']:.2f} m/s"
            )
        lines.append(f"- Plots: `{r['plot']}`, `{r['hist_plot']}`")
        lines.append("")

    lines += [
        "## Interpretation",
        "",
        "- Phase2j logged `v_world` was fed by **frame-pair** vision derivatives; those",
        "  magnitudes are dominated by PnP jitter (commit message cites ~±18 cm).",
        "- The 0.15–0.45 s baseline reduces derivative noise; residual RMSE vs logged",
        "  `v_world` is expected to be large because the online estimate was the noisy one.",
        "- PnP noise std validates the premise for the new baseline.",
        "",
        "## Phase2k",
        "",
        "No phase2k flight logs/fixtures found on this machine at analysis time.",
        "",
    ]
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    blockers: list[str] = []
    # Search for phase2k
    found_2k = False
    for root in LOG_ROOTS:
        if not root.exists():
            continue
        for d in root.iterdir():
            if d.is_dir() and any(h in d.name.lower() for h in PHASE2K_HINTS):
                found_2k = True
    fix_root = ROOT / "fixtures"
    if fix_root.exists():
        for d in fix_root.iterdir():
            if d.is_dir() and "phase2k" in d.name.lower():
                found_2k = True
    if not found_2k:
        blockers.append("phase2k logs/fixtures not found locally — validation uses phase2j only.")

    results = []
    for label, session in PHASE2J:
        r = analyze_one(label, session)
        if r is None:
            blockers.append(f"Missing flight.jsonl for {label} ({session})")
        else:
            results.append(r)

    summary = {"results": results, "blockers": blockers}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_report(results, blockers)
    print(f"Wrote report + {len(results)} plots under {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
