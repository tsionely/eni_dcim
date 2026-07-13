# Phase 1d — Clean single-instance race validation

- **Date (local):** 2026-07-13 ~23:03-23:10 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385**
- **Code commit that flew:** `83d095497b4f89a614a28e28a097f8fc6adc14a1` (branch `main`, clean pull).
- **Ground rules honored:** no edits to `src/`/`config/`/`simtools/`/`tests/`/`docs/`.
  The race was started by a temp GUI-click script in `%TEMP%` (reuses elyatim's window
  helpers; NOT added to the repo). No second telemetry client was run.

## 1. Single-instance verification (PIDs)
Exactly ONE sim: `FlightSim.exe` **PID 56276** (parent) + engine
`DCGame-Win64-Shipping.exe` **PID 49312** (child, same `v1.0.3385\` install).
**No orphans present** (the phase1c orphan stayed gone). Engine owns `udp:14560`
and `udp:5601`; nothing else on 14550/5600 before the check.

## 2. phase1_check --duration 90 with a REAL race started mid-run

Race start: my click automation fired `event r1 (400,225)` at 23:08:39 and
`RACE clicked` at **23:08:41** (~27 s into the check).

Per-10s liveness windows:
```
 10s  imu=1140 (frozen, std=0.0000)  frames+=0     race_started=True
 20s  imu=2281 (frozen, std=0.0000)  frames+=0     race_started=True
 30s  imu=3426 (ALIVE*, std=0.0000)  frames+=3627  race_started=True   <-- vision ON
 40s  imu=4572 (frozen, std=0.0000)  frames+=5053  race_started=True
 50s  imu=5716 (frozen, std=0.0000)  frames+=4525  race_started=True
 60s  imu=6863 (frozen, std=0.0000)  frames+=4379  race_started=True
 70s  imu=8006 (frozen, std=0.0000)  frames+=2572  race_started=True
 80s  imu=9149 (frozen, std=0.0000)  frames+=0     race_started=True   <-- race ended
```
Final report: imu 114.4 Hz, **frame 224.0 Hz (20156 decoded, 0 failed)**, race 4 Hz,
heartbeat 10 Hz, actuator 93 Hz, timesync std 0.25 ms.
Heartbeat sources: **(1,200,armed=False) AND (1,200,armed=True)** — the drone armed
during the race. IMU final verdict: **FROZEN** (gyro_z std 0.000008).
Recording: `recordings/phase1-20260713T200814.aigprec` — **923,060 datagrams**.

\* the 30s window briefly printed "ALIVE" but std=0.0000 (threshold flicker); the
overall gyro_z std over 90s is 0.000008 -> FROZEN.

### When did the race become active?
**Vision turned on in the 20s->30s window** (frames 0 -> 3627), matching the RACE
click at 23:08:41 (~27 s in). NOTE: `race_started=True` was already reported in the
FIRST window (10s), i.e. the flag is **sticky/stale** from the prior phase1c race —
so the *reliable* "race is live now" signal was the **vision frame onset**, not the
race_started flag.

## 3. Headline findings

1. **Vision on udp:5600 WORKS during an active race.** frames 0 -> 224 Hz the moment
   the race started; 20,156 frames decoded cleanly (0 failures). The earlier
   phase1/1b "no frames" was because there was **no active race** (and/or the orphan
   process). This is our **first real vision capture** (see recording note below).
2. **IMU on udp:14550 stays FROZEN even during an armed, active race** (std ~1e-5),
   despite full 114 Hz message rate and an `armed=True` heartbeat. So live vehicle
   IMU is NOT arriving on the legacy 14550 stream. This is now the key blocker.

## 4. Conditional steps (per runbook)
- Frames appeared -> **let it finish; recording kept** (first real vision fixture).
- IMU did NOT go alive -> **frame_probe SKIPPED** (would read frozen garbage, as the
  cloud already found in 1b).
- Vision was NOT silent -> **pktmon SKIPPED** (only needed if 5601/vision stayed dark).

## 5. RECORDING — needs Google Drive upload (too big to commit)
- File: `recordings/phase1-20260713T200814.aigprec`
- Size: **~1290 MB (1.29 GB)**, 923,060 datagrams, ~60 s of active-race vision @224 Hz.
- Per ground rule 5 it is NOT committed. **Action required:** upload it to Drive
  `AI-GP Simulator/recordings` (I do not have a Drive connector in this session, so
  this needs a human/connector step). Manifest records it as `recording_skipped`.

## 6. Suggested next steps (cloud agent — NOT applied here)
1. **Find live IMU/attitude.** 14550 IMU is frozen even in a live race. Check whether
   live vehicle state is (a) inside the 14550 `ENCAPSULATED_DATA` (4 Hz) payload,
   (b) on the sim's outbound 14560 to a different client port, or (c) only sent to an
   autopilot that actually commands the vehicle. Without live IMU, control is blind.
2. Vision pipeline is GO on 5600 during a race — safe to build the perception path now.
3. Consider a smaller/duration-capped recording option so real vision fixtures fit the
   50 MB commit limit (the current 60 s race = 1.3 GB).

## 7. Files in this fixture
- `report.txt` — full console: preflight PID/port verification + 90s phase1_check with the live liveness windows + click-starter stdout.
- `probe.json` — **STALE** (phase1b frame_probe; no frame_probe run this cycle — IMU was frozen).
- `20260713T190311-db4c58dd-*` — **STALE** phase1 fly_once log (collect copied newest existing flight dir; none created this cycle).
- `manifest.json` — collector manifest; note `recording_skipped` entry (1290 MB -> Drive).
- Recording itself is NOT here (see section 5).
