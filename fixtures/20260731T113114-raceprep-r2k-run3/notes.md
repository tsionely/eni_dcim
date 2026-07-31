# R2K refined hole-check run 3

- Exact HEAD: `4e174ee07796db8c0cd07b0cb7f8de85a87a0af8`
- Flight ID: `20260731T113047-20d39188`
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
- `[STEP 5] returned to main menu` was not printed. This counted as run 3;
  no retry was attempted. The simulator was relaunched before run 4.
