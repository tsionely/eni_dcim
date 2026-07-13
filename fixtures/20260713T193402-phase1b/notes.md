# Phase 1b — Vision diagnosis + frame re-probe

- **Date (local):** 2026-07-13 ~22:32 Asia/Jerusalem (report timestamps UTC/local mixed; see report.txt)
- **Sim version:** AI-GP Simulator **v1.0.3385**, engine `DCGame-Win64-Shipping.exe`
  - Running exe: `C:\Users\tsion\Downloads\AI-GP Simulator v1.0.3385\FlightSim.exe` (PID 56276; engine PID 49312)
- **Code commit that flew:** see manifest.json `code_commit` (branch `main`, clean `git pull` to 4c74187 before run)
- **Ground rules honored:** no edits to `src/`, `config/`, `simtools/`, `tests/`, `docs/`. Used the updated pushed scripts as-is.

## 1. Vision diagnosis

### vision_probe.py --duration 30 (passive)
- Result: **NO datagrams on any port 5595-5615.**
- Note: port **5601 could not be bound** — already held by another process.

### vision_probe.py --duration 30 --arm (armed flight)
- Armed, gentle climb + hover, disarmed. Result: **NO datagrams on any port 5595-5615.**
- Same 5601 bind failure.

### netstat / socket ownership
- `netstat -ano | findstr 5600` -> **nothing** (no process touches 5600).
- The sim engine `DCGame-Win64-Shipping.exe` **binds UDP `0.0.0.0:5601` and `0.0.0.0:14560`**.
- The pilot/config listens on MAVLink **14550** (works perfectly) and vision **5600** (silent).

**Key inference:** vs sim v1.0.3379 (where vision was udp:5600 and worked), v1.0.3385
has shifted its UDP ports: MAVLink companion 14550 -> engine also binds **14560**,
and vision **5600 -> 5601**. The pilot never receives frames because it listens on
5600 while the sim's vision socket is now **5601**. Because the sim *binds* 5601
(it is the listener/owner), the pilot cannot simply bind 5601 to receive — the
v3385 vision topology likely changed (e.g. pilot must send a subscribe/hello to
`127.0.0.1:5601`, or pull frames differently). This needs the cloud agent to
confirm the v3385 vision handshake.

### sim config files
- Searched the install dir and `%LOCALAPPDATA%\FlightSim\Saved\Config\*` for
  `5600|5601|video|stream|port`: **no port/stream settings found** — only
  `pgos_res\pgos_config.ini` (PGOS backend URLs, no ports). Vision port is
  **baked into the binary**, not user-configurable via ini.
- Interesting: `%LOCALAPPDATA%\FlightSim\Saved\Ghosts\Event\event-ai-gp-r1-qualifier-anduril...ghost.enc`
  confirms the R1 qualifier event is installed.

### firewall
- Windows Firewall is enabled on all profiles (DefaultInboundAction NotConfigured).
- Inbound Allow rules exist for `DCGame-Win64-Shipping.exe` (TCP+UDP) across all sim
  installs, and for the base interpreter `...\pythoncore-3.14-64\python.exe` (TCP+UDP).
- The **venv** interpreter `C:\Users\tsion\Projects\eni_dcim\.venv\Scripts\python.exe`
  has **no explicit rule**, BUT **firewall is NOT the cause**: loopback (127.0.0.1)
  is exempt from Windows Firewall, and MAVLink UDP on 14550 reaches this exact venv
  interpreter fine. So the silence on 5600 is a **port/topology change, not a block**.

## 2. How the R1 run captured its 4 frames (answer to runbook Q)

**Screen capture, NOT the UDP vision stream.** The elyatim R1 tooling
(`run_elyatim_vision.py`) uses `pyautogui.screenshot()` ("sim-window recorder ON,
2 Hz + log overlay") to grab pixels of the on-screen **"AI-GP" game window**, saving
`frame_0000x.png` (~460 KB PNGs) with `manifest.jsonl` tagging `sim_title: "AI-GP"`.
- Sim state: RACE had just been clicked (race running/starting) but that run ended
  almost immediately -> only **4 screenshots**, then reset to menu.
- Implication: those 4 frames say **nothing** about the UDP vision pipeline. They are
  window grabs and would work even with the UDP stream completely dead (as it is here).
  The pilot in this repo needs the real UDP frame stream, which is currently unreachable
  on 5600.

## 3. Frame re-probe (rewritten frame_probe.py)

- Recorded all phases (arm/takeoff/settle1/yaw/settle2/step/stop), 1835 IMU samples.
- **Uncommanded persistent spin:** `gyro_z ~= -0.5 rad/s` in EVERY phase, including
  `arm`/`takeoff`/`settle1` BEFORE any yaw command is sent.
- **Yaw sign flipped:** commanded `+0.79 rad/s`, measured `-0.508 rad/s` -> "YES (SIGN FLIPPED!)".
- Integrated yaw at step start: **-268.8 deg** (commanded ~+90).
- Probe self-flagged: **"WARNING: drone was spinning during step -> frame verdict unreliable,
  investigate the spin first."**
- The BODY-vs-NED estimate it printed (`world_yaw_offset_rad=6.741`, frame='ned') is
  therefore **not trustworthy** — it is contaminated by the uncommanded spin.

## Suggested fixes (for the cloud agent — NOT applied here)

1. **Vision port moved to 5601 in v1.0.3385** (engine binds udp:5601; 5600 dead). Confirm the
   v3385 vision handshake/topology and update the vision RX accordingly. A companion
   port 14560 also appears alongside MAVLink 14550.
2. **Uncommanded yaw spin + yaw sign flip** (~-0.5 rad/s from arm onward). This is the
   priority control bug: investigate the yaw-rate sign in the velocity/attitude backend
   and the source of the baseline spin before trusting any BODY/NED frame verdict.

## Files in this fixture
- `report.txt` — full captured console output (both vision_probe runs, diagnostics, frame_probe)
- `probe.json` — rewritten frame_probe IMU samples (1835 samples, all phases)
- `20260713T190311-db4c58dd-{flight.jsonl,result.json,params.json}` — NOTE: this is the
  **stale Phase-1 fly_once log** (no new fly_once was run in Phase 1b); collect_artifacts
  copies the newest flight-log dir, and none was created this cycle.
- `recording.zip` — empty vision recording (0 datagrams; consistent with the dead UDP stream)
- `manifest.json` — collector manifest (code_commit of the flying code)
