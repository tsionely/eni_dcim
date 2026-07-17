# Phase 5b Reflight: HEAD vs 9fe3702

Generated UTC: 2026-07-17T10:43:56.491050+00:00

Scope: all committed `.aigprec` slices in HEAD, including `fixtures/20260716T212744-phase5-closerange-frames` and the three full-approach slices under `fixtures/20260717T092008-phase5b-confirm`.

Harness: fixed HEAD `scripts/reflight.py` for both builds (frame dedupe + frame timing from flight log). For `9fe3702`, the fixed harness was copied into a temporary worktree while imports resolved against the old detector/config.

SIM guard: checked before the matrix and between slices; no real simulator was launched or controlled.

## Builds

| Label | SHA |
|---|---|
| `old-9fe3702` | `9fe370237fa1cd57548aadb49f9f20f943b58311` |
| `new-HEAD` | `34d4f6b6b4476162dff0a9d7ee1f798528fe90e0` |

## Summary

| Build | runnable | skipped no-log | errors | unique frames | fixes | fix rate | accepted | <5m fixes | >=5m fixes | close-tracker fixes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `old-9fe3702` | 52 | 11 | 0 | 3233 | 2706 | 0.837 | 2407 | 0 | 2605 | 0 |
| `new-HEAD` | 52 | 11 | 0 | 3233 | 2842 | 0.879 | 2676 | 0 | 2726 | 11 |

## Per-Slice Old/New Detector

| slice | unique frames | old fixes/rate | new fixes/rate | old accepted | new accepted | old closest | new closest | old tracker | new tracker | note |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `fixtures/20260713T203515-phase1e/fixtures_slice.aigprec` | 38 | 38/1.000 | 38/1.000 | 37 | 37 |  |  | 0 | 0 |  |
| `fixtures/20260714-analysis-slices/phase1e_countdown_and_gate.aigprec` |  | / | / |  |  |  |  |  |  | skipped: no unique flight log |
| `fixtures/20260714-analysis-slices/phase2a_countdown_future_start.aigprec` |  | / | / |  |  |  |  |  |  | skipped: no unique flight log |
| `fixtures/20260714-analysis-slices/phase2b_closest_gate_3p97m.aigprec` |  | / | / |  |  |  |  |  |  | skipped: no unique flight log |
| `fixtures/20260714-analysis-slices/phase2b_countdown_future_start.aigprec` |  | / | / |  |  |  |  |  |  | skipped: no unique flight log |
| `fixtures/20260714-analysis-slices/phase2c_closest_gate_6p98m.aigprec` |  | / | / |  |  |  |  |  |  | skipped: no unique flight log |
| `fixtures/20260714-analysis-slices/phase2c_countdown_future_start.aigprec` |  | / | / |  |  |  |  |  |  | skipped: no unique flight log |
| `fixtures/20260714T111500-analysis-slices/phase1d-race-vision.aigprec` |  | / | / |  |  |  |  |  |  | skipped: no unique flight log |
| `fixtures/20260714T111500-analysis-slices/phase1e-inflight.aigprec` |  | / | / |  |  |  |  |  |  | skipped: no unique flight log |
| `fixtures/20260714T111500-analysis-slices/phase2a-controlled-flight.aigprec` |  | / | / |  |  |  |  |  |  | skipped: no unique flight log |
| `fixtures/20260714T111500-analysis-slices/phase2b-race-legal.aigprec` |  | / | / |  |  |  |  |  |  | skipped: no unique flight log |
| `fixtures/20260714T203252-phase3a-r2training/r2_f2_slice_start.aigprec` | 61 | 55/0.902 | 61/1.000 | 54 | 61 |  |  | 0 | 0 |  |
| `fixtures/20260714T203252-phase3a-r2training/r2_f3_slice_start.aigprec` | 60 | 59/0.983 | 60/1.000 | 58 | 60 |  |  | 0 | 0 |  |
| `fixtures/20260714T212450-phase3b-r2training/20260714T210518-58cd98ad_r2_slice_start.aigprec` | 42 | 39/0.929 | 42/1.000 | 38 | 42 |  |  | 0 | 0 |  |
| `fixtures/20260714T212450-phase3b-r2training/20260714T210844-58cd98ad_r2_slice_start.aigprec` | 47 | 45/0.957 | 47/1.000 | 44 | 47 |  |  | 0 | 0 |  |
| `fixtures/20260714T212450-phase3b-r2training/20260714T211404-58cd98ad_r2_slice_start.aigprec` | 51 | 47/0.922 | 51/1.000 | 46 | 51 |  |  | 0 | 0 |  |
| `fixtures/20260715T052244-phase3c-r2training/20260715T045100-411f3135_r2c_slice_start.aigprec` | 50 | 48/0.960 | 50/1.000 | 47 | 50 |  |  | 0 | 0 |  |
| `fixtures/20260715T052244-phase3c-r2training/20260715T045458-411f3135_r2c_slice_start.aigprec` | 50 | 48/0.960 | 50/1.000 | 47 | 50 |  |  | 0 | 0 |  |
| `fixtures/20260715T052244-phase3c-r2training/20260715T051458-6092dbc0_r2c_slice_start.aigprec` | 50 | 46/0.920 | 50/1.000 | 45 | 50 |  |  | 0 | 0 |  |
| `fixtures/20260715T135600-phase3d-r2training/20260715T051458-6092dbc0_r2d_slice_start.aigprec` |  | / | / |  |  |  |  |  |  | skipped: no unique flight log |
| `fixtures/20260715T135600-phase3d-r2training/20260715T121747-22978559_r2d_slice_start.aigprec` | 39 | 37/0.949 | 39/1.000 | 36 | 39 |  |  | 0 | 0 |  |
| `fixtures/20260715T135600-phase3d-r2training/20260715T122040-22978559_r2d_slice_start.aigprec` | 41 | 40/0.976 | 41/1.000 | 38 | 41 |  |  | 0 | 0 |  |
| `fixtures/20260715T135600-phase3d-r2training/20260715T122352-22978559_r2d_slice_start.aigprec` | 42 | 40/0.952 | 42/1.000 | 39 | 42 |  |  | 0 | 0 |  |
| `fixtures/20260715T190627-phase3e-r2training-slow/20260715T183716-8e6cf1f5_r2e_slice_start.aigprec` | 37 | 34/0.919 | 37/1.000 | 33 | 37 |  |  | 0 | 0 |  |
| `fixtures/20260715T190627-phase3e-r2training-slow/20260715T184758-8e6cf1f5_r2e_slice_start.aigprec` | 50 | 49/0.980 | 50/1.000 | 48 | 50 |  |  | 0 | 0 |  |
| `fixtures/20260715T190627-phase3e-r2training-slow/20260715T185046-8e6cf1f5_r2e_slice_start.aigprec` | 50 | 48/0.960 | 50/1.000 | 46 | 50 |  |  | 0 | 0 |  |
| `fixtures/20260715T190627-phase3e-r2training-slow/20260715T185843-7f28e2fb_r2e_slice_start.aigprec` | 45 | 42/0.933 | 45/1.000 | 41 | 45 |  |  | 0 | 0 |  |
| `fixtures/20260715T200734-phase3f-r2training-slow/20260715T195033-8edfeec4_r2f_slice_start.aigprec` | 46 | 42/0.913 | 46/1.000 | 42 | 46 |  |  | 0 | 0 |  |
| `fixtures/20260715T200734-phase3f-r2training-slow/20260715T200011-8edfeec4_r2f_slice_start.aigprec` | 44 | 41/0.932 | 44/1.000 | 40 | 44 |  |  | 0 | 0 |  |
| `fixtures/20260715T200734-phase3f-r2training-slow/20260715T200142-8edfeec4_r2f_slice_start.aigprec` | 49 | 44/0.898 | 49/1.000 | 43 | 49 |  |  | 0 | 0 |  |
| `fixtures/20260715T211420-phase3g-r2training/20260715T203300-8edfeec4_r2g_slice_start.aigprec` | 40 | 39/0.975 | 40/1.000 | 38 | 40 |  |  | 0 | 0 |  |
| `fixtures/20260715T211420-phase3g-r2training/20260715T204925-8edfeec4_r2g_slice_start.aigprec` | 46 | 42/0.913 | 46/1.000 | 42 | 46 |  |  | 0 | 0 |  |
| `fixtures/20260715T211420-phase3g-r2training/20260715T205124-8edfeec4_r2g_slice_start.aigprec` | 47 | 44/0.936 | 47/1.000 | 43 | 47 |  |  | 0 | 0 |  |
| `fixtures/20260715T211420-phase3g-r2training/20260715T205845-fc86a160_r2g_slice_start.aigprec` | 55 | 48/0.873 | 53/0.964 | 48 | 53 |  |  | 0 | 0 |  |
| `fixtures/20260716T023148-phase3h-r2training/20260715T213138-8edfeec4_r2h_slice_start.aigprec` | 45 | 43/0.956 | 45/1.000 | 41 | 45 |  |  | 0 | 0 |  |
| `fixtures/20260716T023148-phase3h-r2training/20260715T213225-8edfeec4_r2h_slice_start.aigprec` | 40 | 38/0.950 | 40/1.000 | 37 | 40 |  |  | 0 | 0 |  |
| `fixtures/20260716T023148-phase3h-r2training/20260715T213406-fc86a160_r2h_slice_start.aigprec` | 42 | 39/0.929 | 42/1.000 | 38 | 42 |  |  | 0 | 0 |  |
| `fixtures/20260716T023148-phase3h-r2training/20260716T022502-8edfeec4_r2h_slice_start.aigprec` | 51 | 49/0.961 | 51/1.000 | 48 | 51 |  |  | 0 | 0 |  |
| `fixtures/20260716T115732-phase3i-r2training/20260716T031114-8edfeec4_r2i_slice_start.aigprec` | 82 | 76/0.927 | 82/1.000 | 75 | 82 |  |  | 0 | 0 |  |
| `fixtures/20260716T115732-phase3i-r2training/20260716T113216-8edfeec4_r2i_slice_start.aigprec` | 85 | 81/0.953 | 85/1.000 | 80 | 85 |  |  | 0 | 0 |  |
| `fixtures/20260716T115732-phase3i-r2training/20260716T114244-8edfeec4_r2i_slice_start.aigprec` | 25 | 17/0.680 | 25/1.000 | 17 | 25 |  |  | 0 | 0 |  |
| `fixtures/20260716T132549-phase3j-r2training-rerun/20260716T130659-8edfeec4_r2j_rerun_slice_start.aigprec` | 41 | 39/0.951 | 41/1.000 | 39 | 41 |  |  | 0 | 0 |  |
| `fixtures/20260716T132549-phase3j-r2training-rerun/20260716T131137-2ca531c3_r2j_rerun_slice_start.aigprec` | 46 | 44/0.957 | 46/1.000 | 43 | 46 |  |  | 0 | 0 |  |
| `fixtures/20260716T132549-phase3j-r2training-rerun/20260716T131630-8edfeec4_r2j_rerun_slice_start.aigprec` | 33 | 29/0.879 | 33/1.000 | 28 | 33 |  |  | 0 | 0 |  |
| `fixtures/20260716T132549-phase3j-r2training-rerun/20260716T131802-8edfeec4_r2j_rerun_slice_start.aigprec` | 44 | 42/0.955 | 44/1.000 | 41 | 44 |  |  | 0 | 0 |  |
| `fixtures/20260716T135229-phase4a-r2training-chain/20260716T133531-927a4c97_r2a_nopass_start_slice.aigprec` | 42 | 40/0.952 | 42/1.000 | 39 | 42 |  |  | 0 | 0 |  |
| `fixtures/20260716T135229-phase4a-r2training-chain/20260716T134309-927a4c97_r2a_nopass_start_slice.aigprec` | 41 | 37/0.902 | 41/1.000 | 36 | 41 |  |  | 0 | 0 |  |
| `fixtures/20260716T135229-phase4a-r2training-chain/20260716T134842-927a4c97_r2a_nopass_start_slice.aigprec` | 53 | 52/0.981 | 53/1.000 | 51 | 53 |  |  | 0 | 0 |  |
| `fixtures/20260716T144305-phase4b-r2training-chain/20260716T143604-927a4c97_r2b_nopass_start_slice.aigprec` | 47 | 46/0.979 | 47/1.000 | 45 | 47 |  |  | 0 | 0 |  |
| `fixtures/20260716T144305-phase4b-r2training-chain/20260716T143739-927a4c97_r2b_nopass_start_slice.aigprec` | 45 | 42/0.933 | 45/1.000 | 41 | 45 |  |  | 0 | 0 |  |
| `fixtures/20260716T144305-phase4b-r2training-chain/20260716T143915-927a4c97_r2b_nopass_start_slice.aigprec` | 44 | 41/0.932 | 44/1.000 | 40 | 44 |  |  | 0 | 0 |  |
| `fixtures/20260716T154946-phase4b-r2training-chain-v2/20260716T153120-927a4c97_r2b_v2_nopass_start_slice.aigprec` | 44 | 42/0.955 | 44/1.000 | 41 | 44 |  |  | 0 | 0 |  |
| `fixtures/20260716T154946-phase4b-r2training-chain-v2/20260716T153853-927a4c97_r2b_v2_nopass_start_slice.aigprec` | 45 | 44/0.978 | 45/1.000 | 43 | 45 |  |  | 0 | 0 |  |
| `fixtures/20260716T174215-phase4c-r2training-chain/20260716T164931-927a4c97_r2c_commitwindow_slice.aigprec` | 34 | 30/0.882 | 34/1.000 | 30 | 34 |  |  | 0 | 0 |  |
| `fixtures/20260716T174215-phase4c-r2training-chain/20260716T165306-927a4c97_r2c_commitwindow_slice.aigprec` | 32 | 28/0.875 | 32/1.000 | 28 | 32 |  |  | 0 | 0 |  |
| `fixtures/20260716T174215-phase4c-r2training-chain/20260716T165535-927a4c97_r2c_commitwindow_slice.aigprec` | 33 | 26/0.788 | 33/1.000 | 26 | 33 |  |  | 0 | 0 |  |
| `fixtures/20260716T212744-phase5-closerange-frames/20260716T203450-2ca531c3_range3m_to_collision.aigprec` | 33 | 26/0.788 | 24/0.727 | 5 | 4 | 1.5 | 1.5 | 0 | 1 |  |
| `fixtures/20260716T212744-phase5-closerange-frames/20260716T203450-2ca531c3_range5m_to_3m.aigprec` | 36 | 33/0.917 | 36/1.000 | 25 | 28 |  |  | 0 | 0 |  |
| `fixtures/20260716T212744-phase5-closerange-frames/20260716T212408-2ca531c3_close_to_collision.aigprec` | 36 | 31/0.861 | 35/0.972 | 1 | 34 |  |  | 0 | 0 |  |
| `fixtures/20260716T212744-phase5-closerange-frames/20260716T212408-2ca531c3_initial_to_5m.aigprec` | 22 | 21/0.955 | 22/1.000 | 20 | 22 |  |  | 0 | 0 |  |
| `fixtures/20260717T092008-phase5b-confirm/20260717T090941-debf3ec1_takeoff_to_end_full.aigprec` | 344 | 254/0.738 | 261/0.759 | 185 | 212 |  |  | 0 | 0 |  |
| `fixtures/20260717T092008-phase5b-confirm/20260717T091107-debf3ec1_takeoff_to_end_full.aigprec` | 367 | 270/0.736 | 269/0.733 | 196 | 233 |  | 2.14 | 0 | 7 |  |
| `fixtures/20260717T092008-phase5b-confirm/20260717T091239-debf3ec1_takeoff_to_end.aigprec` | 321 | 131/0.408 | 123/0.383 | 75 | 72 | 1.06 | 1.03 | 0 | 3 |  |
