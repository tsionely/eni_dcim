# R2K refined hole-check run 8

- Exact HEAD: `5bdf408184b9ea29ec57b00cc29aaea166bc803f`
- Flight ID: `20260731T120829-20d39188`
- Relaunched before run: `False`
- Gates: 0
- Duration: 0.604 s
- Abort: `stale channels: imu(0.604s)`
- Detection records: 0
- IBVS setpoints: 0
- Phase counts: `{'hover': 31}`
- Commit exits: `{}`
- Command typos corrected to `planner.commit.*`.
- Orchestrator exited with status 1 before the RACE click.
- Exact console stop: `[STOP] fly_once exited before the RACE click (exit 0).`
- `[STEP 5] returned to main menu` was not printed. This counted as run 8;
  no retry was attempted. The simulator was relaunched after the run.
