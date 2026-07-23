# R1j 3390 foreground guard STOP

- date_local: 2026-07-23
- exact_head: 207ee58431d1ece8a0a587afa75a28d22c6a8936
- simulator_exe: C:\Users\tsion\Downloads\AI-GP Simulator v1.0.3390\FlightSim.exe
- lock_holder_pid: 12140
- event-selection clicks: NONE
- flight started: NO

## Foreground guard

1. Sent Esc to dismiss the Start menu.
2. Selected the largest visible window owned by the FlightSim/DCGame process (PID 24116, HWND 62849298), not by title matching.
3. SetForegroundWindow succeeded and the process-owned game HWND was the foreground window.
4. Pre-match banner assertion failed: score **0.7248692513**, below the required **0.80**. The process-owned window title was `AI-GP  `, so the title did not independently expose `1.0.3390`.

## Stop reason

The assertion screenshot shows the simulator **LOGIN** dialog with the account email prefilled and the password masked. Per owner instruction, login is an owner-only step. No Submit, event-row, qualifier, or RACE click was made after the assertion failed.

Evidence:
- `guard-screen-login.png`
- `guard-status.json`
