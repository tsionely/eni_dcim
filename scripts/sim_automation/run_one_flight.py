"""One race-prep flight on the running, logged-in sim: select R2-TRAINING, fly, report.

Sequences the two PROVEN helpers as short subprocess steps so the operator
runs a single short command. STOPS at the first failing step. Does NOT launch
the sim and does NOT touch login — the sim must already be running and past
the login screen (owner's manual step or a prior preflight). The SIM LOCK is
the caller's responsibility.

Usage (always the repo venv, never system python):
  .venv\\Scripts\\python.exe scripts\\sim_automation\\run_one_flight.py <label> -- <fly_once patches...>

Example (validation-trio config B on 3390):
  ...python.exe scripts\\sim_automation\\run_one_flight.py raceprep-r1j3390-val-run1 -- \\
    --max-duration 300 --patch planner.commit.speed_mps=1.8 --patch planner.commit.vz_cap_mps=1.2 --patch planner.terminal.enable=false

Exit codes: 0 flew (see result.json for gates/abort); 2 event selection failed
(screenshot written by event_select); 3 fly_once error. On non-zero, no flight
result exists for this label — report the step and its screenshot.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # repo root
PY = sys.executable                                  # the venv python that launched us
EVENT_SELECT = ROOT / "scripts" / "sim_automation" / "event_select.py"
FLY_ONCE = ROOT / "scripts" / "fly_once.py"


def main() -> int:
    argv = sys.argv[1:]
    if not argv or "--" not in argv:
        print("USAGE: run_one_flight.py <label> -- <fly_once patches...>", flush=True)
        return 64
    sep = argv.index("--")
    head = argv[:sep]
    fly_args = argv[sep + 1:]
    if not head:
        print("ERROR: missing <label> before --", flush=True)
        return 64
    label = head[0]

    # Guard: the venv python only. The system 'python'/'py' are broken in this
    # environment ("logon session does not exist") and would fail mid-flight.
    if ".venv" not in PY.replace("/", "\\").lower():
        print(f"REFUSING: not running under the repo venv (sys.executable={PY}). "
              "Invoke with .venv\\Scripts\\python.exe.", flush=True)
        return 65

    # STEP 1 — select the R2-TRAINING event (proven helper; asserts every event
    # row template >= 0.80 before it clicks, and screenshots on failure).
    print(f"[STEP 1] event_select r2training ({label})", flush=True)
    r = subprocess.run([PY, str(EVENT_SELECT), "r2training", label, "dialog"],
                       cwd=str(ROOT))
    if r.returncode != 0:
        print(f"[STOP] event selection failed (exit {r.returncode}) — see the "
              f"{label} screenshots under %TEMP%\\phase5b_r2_shots. Not flown.",
              flush=True)
        return 2

    # STEP 2 — fly. fly_once handles arm -> race GO wait -> logging under logs/.
    print(f"[STEP 2] fly_once {label} :: {' '.join(fly_args)}", flush=True)
    r = subprocess.run([PY, str(FLY_ONCE), *fly_args], cwd=str(ROOT))
    if r.returncode != 0:
        print(f"[STOP] fly_once errored (exit {r.returncode}). Not a clean flight.",
              flush=True)
        return 3

    print(f"[DONE] {label}: flight complete — collect logs/<flight_id>/, write "
          "the run dir + log-header, commit, push.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
