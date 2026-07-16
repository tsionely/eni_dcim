# Phase 4b safemode

Command requested:
python scripts/fly_once.py --max-duration 300 --patch safety.flight_timeout_s=300 --patch planner.retreat.enabled=false

## Result
- Flight ID: 20260716T150432-a9b6f4bb
- Result: flight timeout, gates_passed=0, env_hits=0.
- Telemetry shows this was not a valid race comparison: frames=0, detections=0, IMU=0, race_start=-1, phase sequence hover -> takeoff -> search -> hover.
- Visual one-liner: I saw the helper click R2/RACE, but the drone did not produce a real FPV/race telemetry stream; it sat through GO timeout and searched until the 300s timeout.

## Interpretation
This safemode run is ALSO bad, but specifically as an environmental/launch/session no-race failure rather than a valid retreat-disabled flight. It does not look like the milestone flight and cannot bisect planner behavior without a valid frame/IMU/race stream.

## Contents
- report.txt
- phase4b_safemode_analysis.txt
- flight.jsonl / result.json / params.json
- screenshots/
