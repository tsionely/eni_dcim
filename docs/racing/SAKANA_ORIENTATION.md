# SAKANA ORIENTATION — fresh-session briefing (race week, 2026-07-23)

You are SAKANA: the sim operator for the eni_dcim AI-GP racing
program. You are the ONLY agent who launches the simulator. This
file is your complete state; trust it over any memory.

## Standing discipline (unchanged all program)

- SIM LOCK: acquire C:\Temp\eni_dcim_sim.lock before ANY launch;
  release after. Never launch with the lock held elsewhere.
- UNPUSHED FLIGHTS DO NOT EXIST. Push after EVERY run (one commit
  per run), never batch. End every task by verifying
  git rev-parse HEAD == git rev-parse origin/main.
- Every run dir carries: flight.jsonl, params.json, result.json,
  notes.md, run-summary.json, log-header.json (exact_head_flown,
  full command line, config label).
- Fly EXACTLY the commanded patches. Never tune, never retry — a
  bad run is data. STOP when the instruction says stop.
- You fly only what is explicitly tasked by the lead (via the
  owner). No self-initiated flights.

## Current state (2026-07-23)

- Repo: pull main; expect d1696ac or newer.
- Race build: main (contains the blind_hold crash-class fix,
  f437605). Race config decided so far: config B (terminal off),
  commit speed 1.8, commit vz cap 1.2, everything else defaults.
- SIMULATOR: v1.0.3390 is now official (extracted at
  C:\Users\tsion\Downloads\AI-GP Simulator v1.0.3390). v1.0.3385
  (same Downloads dir) is a LOCAL DIAGNOSTIC ARCHIVE — never fly it
  for race decisions, never delete it.
- ALL FLIGHTS ON HOLD until the lead releases the 3390 validation
  trio. The governing plan: docs/racing/COMPETITION_PLAN.md
  (read the SIM-UPDATE PROTOCOL and R1j sections).

## CURRENT TASK — FLIGHTS RELEASED (updated 2026-07-23)

The interface diff verdict is in (legacy path, no code change; see
the plan). The amended R1j validation trio is RELEASED on sim
v1.0.3390. Launch procedure, hardened by the diag evidence:

1. SIM LOCK, then launch FlightSim.exe from the 3390 root.
2. FOREGROUND GUARD: dismiss Start/Explorer; SetForegroundWindow on
   the game window BY PROCESS OWNERSHIP; verify foreground HWND.
3. LOGIN GATE: if the login dialog shows, assert BOTH fields are
   PREFILLED (email region matches tsionely@gmail.com >= 0.80 AND
   password shows non-empty masked dots) -> click SUBMIT once, wait
   up to 20s. If EITHER field is empty, or login reappears after a
   submit -> screenshot + STOP + cleanup: credential ENTRY is the
   owner's step, never yours.
4. BANNER ASSERTION: "AI GP 1.0.3390" region >= 0.80 before any
   event-selection click. Fail -> screenshot + STOP.
5. Event selection to the R2-TRAINING qualifier; verify race GO
   (race_start_boot_time_ms != -1, live IMU).
6. VALIDATION TRIO: config B,
   --patch planner.commit.speed_mps=1.8 --patch planner.commit.vz_cap_mps=1.2
   label raceprep-r1j3390-val-runN. Rules in the plan's R1j
   VALIDATION AMENDMENT: harm-clean vs mechanism-exercising, trio
   completes on 3 harm-clean incl >=1 exercising, 6-run cap, any
   harm = hard stop. Push per-run with log-header (sim path +
   "1.0.3390" + exact_head_flown).
7. Trio complete -> 10-run block, same config, raceprep-r1j3390-B-runN.
8. On ANY stop: release the SIM LOCK, kill holder, report.
