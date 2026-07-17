# Closed-Loop Arbitration: HEAD vs 116b27e

Generated UTC: 2026-07-17T10:59:20.101206+00:00

Command shape: each test node was run solo, three times per build.

## Builds

| Label | SHA |
|---|---|
| `HEAD-34d4f6b` | `34d4f6b6b4476162dff0a9d7ee1f798528fe90e0` |
| `old-116b27e` | `116b27e6c1fbe4f46da0cf35c9765cd72ca80fde` |

## Pass Rates

| Build | Test | Passed | Runs | Pass rate |
|---|---|---:|---:|---:|
| `HEAD-34d4f6b` | `single_gate` | 1 | 3 | 0.333 |
| `HEAD-34d4f6b` | `first_gate_with_second_visible` | 3 | 3 | 1.000 |
| `old-116b27e` | `single_gate` | 1 | 3 | 0.333 |
| `old-116b27e` | `first_gate_with_second_visible` | 3 | 3 | 1.000 |

## Runs

| Build | Test | Run | Result | Output |
|---|---|---:|---|---|
| `HEAD-34d4f6b` | `single_gate` | 1 | PASS | `tuning/closed-loop-arbitration-34d4f6b-vs-116b27e/HEAD-34d4f6b-single_gate-run1.txt` |
| `HEAD-34d4f6b` | `single_gate` | 2 | FAIL rc=1 | `tuning/closed-loop-arbitration-34d4f6b-vs-116b27e/HEAD-34d4f6b-single_gate-run2.txt` |
| `HEAD-34d4f6b` | `single_gate` | 3 | FAIL rc=1 | `tuning/closed-loop-arbitration-34d4f6b-vs-116b27e/HEAD-34d4f6b-single_gate-run3.txt` |
| `HEAD-34d4f6b` | `first_gate_with_second_visible` | 1 | PASS | `tuning/closed-loop-arbitration-34d4f6b-vs-116b27e/HEAD-34d4f6b-first_gate_with_second_visible-run1.txt` |
| `HEAD-34d4f6b` | `first_gate_with_second_visible` | 2 | PASS | `tuning/closed-loop-arbitration-34d4f6b-vs-116b27e/HEAD-34d4f6b-first_gate_with_second_visible-run2.txt` |
| `HEAD-34d4f6b` | `first_gate_with_second_visible` | 3 | PASS | `tuning/closed-loop-arbitration-34d4f6b-vs-116b27e/HEAD-34d4f6b-first_gate_with_second_visible-run3.txt` |
| `old-116b27e` | `single_gate` | 1 | FAIL rc=1 | `tuning/closed-loop-arbitration-34d4f6b-vs-116b27e/old-116b27e-single_gate-run1.txt` |
| `old-116b27e` | `single_gate` | 2 | FAIL rc=1 | `tuning/closed-loop-arbitration-34d4f6b-vs-116b27e/old-116b27e-single_gate-run2.txt` |
| `old-116b27e` | `single_gate` | 3 | PASS | `tuning/closed-loop-arbitration-34d4f6b-vs-116b27e/old-116b27e-single_gate-run3.txt` |
| `old-116b27e` | `first_gate_with_second_visible` | 1 | PASS | `tuning/closed-loop-arbitration-34d4f6b-vs-116b27e/old-116b27e-first_gate_with_second_visible-run1.txt` |
| `old-116b27e` | `first_gate_with_second_visible` | 2 | PASS | `tuning/closed-loop-arbitration-34d4f6b-vs-116b27e/old-116b27e-first_gate_with_second_visible-run2.txt` |
| `old-116b27e` | `first_gate_with_second_visible` | 3 | PASS | `tuning/closed-loop-arbitration-34d4f6b-vs-116b27e/old-116b27e-first_gate_with_second_visible-run3.txt` |
