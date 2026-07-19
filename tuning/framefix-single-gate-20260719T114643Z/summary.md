# Frame-Fix Single-Gate Reliability

Role: QA & MOCK-TUNER.
Scope: mock only. No real simulator was launched, reset, clicked, or commanded.
Test node: `tests/integration/test_mock_closed_loop.py::test_single_gate_pass`.
Runs per build: `10`.
Python: `C:\Temp\eni_dcim_venv\Scripts\python.exe`.

## Pass Rate

| Build | Commit | Passes | Runs | Pass rate |
|---|---:|---:|---:|---:|
| `head-78c8461` | `78c846178155` | 7 | 10 | 70.0% |
| `pre-fix-79d9f76` | `79d9f7693380` | 6 | 10 | 60.0% |

## Attempts

| Build | Run | Verdict | Duration s | Log | Summary |
|---|---:|---|---:|---|---|
| `head-78c8461` | 1 | PASS | 11.006 | `tuning\framefix-single-gate-20260719T114643Z\head-78c8461-run01.txt` | 1 passed in 10.64s |
| `head-78c8461` | 2 | FAIL rc=1 | 37.268 | `tuning\framefix-single-gate-20260719T114643Z\head-78c8461-run02.txt` |         if result["gates_passed"] < 1:            # one retry (see docstring) / >       assert result["gates_passed"] >= 1, f"never passed the gate: {result}" / E       AssertionError: never passed the gate: {'finished': False, 'aborted': T |
| `head-78c8461` | 3 | PASS | 43.074 | `tuning\framefix-single-gate-20260719T114643Z\head-78c8461-run03.txt` | 1 passed in 42.71s |
| `head-78c8461` | 4 | FAIL rc=1 | 31.324 | `tuning\framefix-single-gate-20260719T114643Z\head-78c8461-run04.txt` |         if result["gates_passed"] < 1:            # one retry (see docstring) / >       assert result["gates_passed"] >= 1, f"never passed the gate: {result}" / E       AssertionError: never passed the gate: {'finished': False, 'aborted': T |
| `head-78c8461` | 5 | PASS | 27.665 | `tuning\framefix-single-gate-20260719T114643Z\head-78c8461-run05.txt` | 1 passed in 27.30s |
| `head-78c8461` | 6 | FAIL rc=1 | 37.83 | `tuning\framefix-single-gate-20260719T114643Z\head-78c8461-run06.txt` |         if result["gates_passed"] < 1:            # one retry (see docstring) / >       assert result["gates_passed"] >= 1, f"never passed the gate: {result}" / E       AssertionError: never passed the gate: {'finished': False, 'aborted': T |
| `head-78c8461` | 7 | PASS | 11.245 | `tuning\framefix-single-gate-20260719T114643Z\head-78c8461-run07.txt` | 1 passed in 10.92s |
| `head-78c8461` | 8 | PASS | 10.81 | `tuning\framefix-single-gate-20260719T114643Z\head-78c8461-run08.txt` | 1 passed in 10.44s |
| `head-78c8461` | 9 | PASS | 23.368 | `tuning\framefix-single-gate-20260719T114643Z\head-78c8461-run09.txt` | 1 passed in 23.07s |
| `head-78c8461` | 10 | PASS | 11.067 | `tuning\framefix-single-gate-20260719T114643Z\head-78c8461-run10.txt` | 1 passed in 10.70s |
| `pre-fix-79d9f76` | 1 | PASS | 21.386 | `tuning\framefix-single-gate-20260719T114643Z\pre-fix-79d9f76-run01.txt` | 1 passed in 21.08s |
| `pre-fix-79d9f76` | 2 | FAIL rc=1 | 64.472 | `tuning\framefix-single-gate-20260719T114643Z\pre-fix-79d9f76-run02.txt` |         if result["gates_passed"] < 1:            # one retry (see docstring) / >       assert result["gates_passed"] >= 1, f"never passed the gate: {result}" / E       AssertionError: never passed the gate: {'finished': False, 'aborted': T |
| `pre-fix-79d9f76` | 3 | PASS | 10.653 | `tuning\framefix-single-gate-20260719T114643Z\pre-fix-79d9f76-run03.txt` | 1 passed in 10.28s |
| `pre-fix-79d9f76` | 4 | FAIL rc=1 | 58.152 | `tuning\framefix-single-gate-20260719T114643Z\pre-fix-79d9f76-run04.txt` |         if result["gates_passed"] < 1:            # one retry (see docstring) / >       assert result["gates_passed"] >= 1, f"never passed the gate: {result}" / E       AssertionError: never passed the gate: {'finished': False, 'aborted': T |
| `pre-fix-79d9f76` | 5 | FAIL rc=1 | 56.981 | `tuning\framefix-single-gate-20260719T114643Z\pre-fix-79d9f76-run05.txt` |         if result["gates_passed"] < 1:            # one retry (see docstring) / >       assert result["gates_passed"] >= 1, f"never passed the gate: {result}" / E       AssertionError: never passed the gate: {'finished': False, 'aborted': T |
| `pre-fix-79d9f76` | 6 | PASS | 31.035 | `tuning\framefix-single-gate-20260719T114643Z\pre-fix-79d9f76-run06.txt` | 1 passed in 30.63s |
| `pre-fix-79d9f76` | 7 | FAIL rc=1 | 50.776 | `tuning\framefix-single-gate-20260719T114643Z\pre-fix-79d9f76-run07.txt` |         if result["gates_passed"] < 1:            # one retry (see docstring) / >       assert result["gates_passed"] >= 1, f"never passed the gate: {result}" / E       AssertionError: never passed the gate: {'finished': False, 'aborted': T |
| `pre-fix-79d9f76` | 8 | PASS | 23.931 | `tuning\framefix-single-gate-20260719T114643Z\pre-fix-79d9f76-run08.txt` | 1 passed in 23.58s |
| `pre-fix-79d9f76` | 9 | PASS | 41.853 | `tuning\framefix-single-gate-20260719T114643Z\pre-fix-79d9f76-run09.txt` | 1 passed in 41.49s |
| `pre-fix-79d9f76` | 10 | PASS | 37.759 | `tuning\framefix-single-gate-20260719T114643Z\pre-fix-79d9f76-run10.txt` | 1 passed in 37.39s |
