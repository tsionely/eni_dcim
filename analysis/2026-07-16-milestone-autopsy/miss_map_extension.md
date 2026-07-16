# Crossing-miss map extension (phase3i + phase3j-rerun + PASS)

PASS flight: `20260716T131137-2ca531c3` (green star). Convention unchanged from `analysis/2026-07-15-crossing-miss-map`.

## Phase summary (ok, dist ≤ 5 m)

| phase | n | mean |lat| | mean lat | mean vert | mean |vert| | rms | n_pass_flights |
|---|---:|---:|---:|---:|---:|---:|---:|
| phase3c | 3 | 0.07 | +0.04 | +0.94 | 0.94 | 1.16 | 0 |
| phase3d | 4 | 0.12 | -0.01 | -0.07 | 0.23 | 0.35 | 0 |
| phase3e | 4 | 0.23 | -0.05 | +0.24 | 0.42 | 0.60 | 0 |
| phase3f | 3 | 0.11 | -0.10 | +0.34 | 0.34 | 0.39 | 0 |
| phase3g | 5 | 0.15 | +0.05 | +0.10 | 0.12 | 0.26 | 0 |
| phase3h | 5 | 0.29 | -0.28 | -0.20 | 0.22 | 0.52 | 0 |
| phase3i | 3 | 0.03 | -0.03 | +0.14 | 0.14 | 0.16 | 0 |
| phase3j_rerun | 5 | 0.07 | -0.03 | +0.06 | 0.21 | 0.25 | 1 |

## PASS crossing vector (ground-truth success)

- Flight `20260716T131137-2ca531c3` attempt 1: dist=0.103 m, **lateral=+0.006 m**, **vertical=+0.100 m**, age=1.08s, cycle=`approach+commit+approach+commit+retreat`.
- Sign convention: vert+ = aircraft HIGH. This PASS is the calibration anchor — prior phases that cluster near this point were geometrically close.

## Table

Full rows: `miss_table.csv`. Scatter: `plots/miss_scatter_with_pass.png`.
