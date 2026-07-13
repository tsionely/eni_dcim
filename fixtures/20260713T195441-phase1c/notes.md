# Phase 1c — Port-topology probe

- **Date (local):** 2026-07-13 ~22:48-22:53 Asia/Jerusalem
- **Sim version:** AI-GP Simulator **v1.0.3385**, engine `DCGame-Win64-Shipping.exe`
  (FlightSim PID 56276, engine PID 49312). Single instance.
- **Code commit that flew:** see manifest.json `code_commit` (branch `main`, clean `git pull` to a2d92b1).
- **Ground rules honored:** no edits to `src/`, `config/`, `simtools/`, `tests/`, `docs/`.
  The two `race_probe_1c*.py` used for the race-state test are ad-hoc temp files in
  `%TEMP%` (NOT added to the repo).

## Environment cleanup done first
At the start there were TWO engine processes: my main sim (49312, `v1.0.3385\`,
held 5601) and an **orphaned** `DCGame` (56604) from the `v1.0.3385 (1)\AIGP_3385\`
install — a leftover whose FlightSim parent (26796) I had stopped in the phase1
cycle; it held 14560. I stopped the orphan (56604). Afterwards the **single live
engine (49312) binds BOTH `udp:14560` and `udp:5601`**, confirming the runbook's
"one sim owns both new ports" premise. (Earlier phase1b saw them split only because
of that orphan.)

## topology_probe.py — sim IDLE at qualifier (drone NOT racing)

- **A) legacy udpin:14550:** messages flow — HIGHRES_IMU 115.5 Hz, ACTUATOR_OUTPUT_STATUS
  93.8 Hz, HEARTBEAT 9.9 Hz, **ENCAPSULATED_DATA 4.0 Hz**. Heartbeat source
  `(sys=1, comp=200, armed=False)`. **IMU liveness: gyro_z std = 0.000000 -> FROZEN**
  (mean gyro_z -1.025, accel_z -23.46). Verdict: `14550 alive: no` (frozen values).
- **B) udpout to sim:14560** (proper GCS heartbeat out): **no response**.
- **C) vision poke to sim:5601** (hello datagrams, listen): **0 datagrams**.
- Recommended-config line: "none of the hypotheses confirmed."

New detail vs 1b: `ENCAPSULATED_DATA` at 4 Hz is present on 14550 — MAVLink-tunneled
payload worth decoding (could be the vision/telemetry the connect hypothesis expects).

## Does the drone need to be IN a race for 14560/5601 to respond?

**Tested both states. In my tests 14560/5601 did NOT respond in EITHER state.**

- I started a real **active race** via the GUI RACE automation and confirmed with a
  socket snapshot that the race client was live (`udp:14550` + `udp:5600` owned by the
  race python PID 57128) while the engine (49312) held `udp:14560` + `udp:5601`.
- **Race-state probe v1** (raw byte pokes to 14560 & 5601): **0 replies**.
- **Race-state probe v2** (proper pymavlink GCS heartbeat to 14560 + poke 5601):
  **no response on 14560, 0 datagrams on 5601**.

**Answer:** being in an active race was **not sufficient** to make 14560/5601 answer an
external loopback client. The engine keeps 14560/5601 **bound as listeners at all times**
(idle and racing), but they did not reply to our heartbeats/pokes in any state.

### Caveats (for the cloud agent)
- I could not run the real `topology_probe.py` DURING a race: its part-A binds
  `udpin:14550`, which the race-driving client also holds — they contend for the single
  legacy socket. So the race-state numbers come from ad-hoc 14560/5601-only probes.
- All pokes were over **loopback 127.0.0.1**. The sim binds `0.0.0.0`, and its outbound
  TCP uses the LAN IP `192.168.1.219`; it is possible the live stream targets the LAN
  IP or a specific registered peer rather than replying to an arbitrary loopback sender.
- The race was driven by the legacy 14550 client (elyatim tooling), not by a 14560
  connect-client. If the sim only opens the live channel for a client that HANDSHAKES on
  14560 from the start, that path remains untested (would need code that connects via
  14560, which is the cloud agent's job).
- Per runbook step 3 ("if 14560/5601 respond, rerun phase1_check --duration 30"):
  they did NOT respond, so that step was skipped.

## Suggested next steps (cloud agent — NOT applied here)
1. Decode the `ENCAPSULATED_DATA` (4 Hz) on 14550 — it may already carry the vision or
   live telemetry payload inside the legacy channel.
2. If pursuing the 14560/5601 connect hypothesis, implement a real MAVLink connect on
   14560 (full handshake, request data streams) and a proper vision subscribe on 5601,
   and consider that the sim may stream to the LAN IP rather than 127.0.0.1.
3. Investigate why 14550 IMU is frozen (std 0.000) despite full message rate — this is
   the blocker for any 14550-based control.

## Files in this fixture
- `report.txt` — captured console: idle topology_probe + both race-state probes + socket snapshots
- `probe.json` — NOTE: **stale** frame_probe samples from Phase 1b (no frame_probe run this cycle)
- `20260713T190311-db4c58dd-*` — NOTE: **stale** Phase-1 fly_once log (collect copies newest flight dir; none created this cycle)
- `recording.zip` — empty vision recording (0 datagrams)
- `manifest.json` — collector manifest (code_commit of flying code)
