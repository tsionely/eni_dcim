# R2K refined hole-check run 5

- Exact HEAD: `5ffafdd7a5e94b428718fc391f1b4d16baf97ae6`
- Flight ID: `20260731T114024-20d39188`
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
- `[STEP 5] returned to main menu` was not printed. This counted as run 5;
  no retry was attempted. The simulator was relaunched before run 6.
