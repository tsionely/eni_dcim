# AI-GP Autonomous Pilot (`eni_dcim`)

Autonomous drone racing pilot for the [AI Grand Prix](https://www.theaigrandprix.com)
competition: a quadcopter flying through gates with **no GPS and no absolute
coordinates** — IMU + FPV camera only.

Hebrew design documentation lives in [`docs/`](docs/) (architecture, control &
state estimation, perception, the flight-to-flight learning loop, milestones,
testing strategy).

## Layout

```
src/aigp/       the pilot package
  core/         bus, typed messages, ParamSet, sim clock, 250Hz RateLoop
  io/           MAVLink RX/TX, vision UDP reassembly, timesync, raw recording
  perception/   gate detection (Round-1 classical detector) + pinhole/PnP
  estimation/   Mahony attitude filter + VIO-lite state estimator
  planning/     race behaviors: search / approach / commit / recover
  control/      ControlBackend ladder: velocity (default) / attitude-rate
  supervisor/   flight FSM, watchdogs, collision policy
  learning/     flight logs, SQLite results, optimizers, tuning campaigns
  telemetry/    async JSONL logger, post-flight plots
simtools/       mock simulator, UDP recorder (Windows), replay server
scripts/        fly_once, run_campaign, frame_probe, plot_flight
config/         sim endpoints + the default ParamSet
tests/          unit tests + closed-loop integration tests vs. the mock sim
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .        # optional; scripts/ also work without it
```

Python 3.11+ (the official dev kit targets 3.14).

## Running

**Against the mock sim** (no real simulator needed — works anywhere):

```bash
python -m aigp.main --mode mock --max-duration 30
```

**Against the real sim** (on the Windows machine, with FlightSim.exe running
and the pilot endpoints at their defaults — MAVLink UDP 14550, video UDP 5600):

```bash
python scripts/phase1_check.py --duration 60   # passive connectivity check first
python scripts/fly_once.py                     # then a real flight
```

**Tuning campaign** (flight-to-flight improvement loop):

```bash
python scripts/run_campaign.py --flights 20 --optimizer cem --sim mock
```

Results land in `logs/<flight_id>/` (params snapshot, JSONL telemetry,
verdict) and `logs/results.sqlite` (queryable summary; best parameters per
campaign).

**Phase-1 probe** (real sim only — resolves the velocity-frame question, see
`docs/02`):

```bash
python scripts/frame_probe.py
```

**Record / replay real-sim sessions** (see `docs/06`):

```bash
# on the Windows machine, between sim and pilot:
python simtools/record.py --out recordings/flight1.aigprec
# anywhere, later:
python simtools/replay_server.py recordings/flight1.aigprec
python -m aigp.main --mode replay --recording recordings/flight1.aigprec
```

## Tests

```bash
pytest tests/unit          # pure logic, no sockets
pytest tests/integration   # full closed loop against the mock sim
```
