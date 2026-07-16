# Phase 5 Reflight Fix Coverage vs Range

Generated UTC: 2026-07-16T18:15:24.566218+00:00

Scope: all committed `.aigprec` slices in HEAD, crossed with builds `fd9d419`, `54a75a1`, `80c6d44`, and `HEAD`.

Harness note: the stable HEAD `scripts/reflight.py` harness was used for all builds; older worktrees predated the script, so the harness was copied into temporary worktrees while imports resolved against each build's `src/` and `config/`.

SIM guard: checked before CI and before the reflight matrix; no real simulator was launched or controlled.

## Builds

| Build | SHA |
|---|---|
| `fd9d419` | `fd9d41927be014804f82e5c6fe62c035247e7255` |
| `54a75a1` | `54a75a14829235043be472c8c77f0ffe88e4f802` |
| `80c6d44` | `80c6d44f550eaf7f9e0dfa5823a35265b41d849f` |
| `HEAD` | `9fe370237fa1cd57548aadb49f9f20f943b58311` |

## Summary

| Build | runnable slices | skipped no-log | errors | fixes | accepted | closest fix m | <3m fixes | 3-5m fixes | >=5m fixes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `fd9d419` | 45 | 11 | 0 | 12356 | 11950 |  | 0 | 0 | 12356 |
| `54a75a1` | 45 | 11 | 0 | 12356 | 11950 |  | 0 | 0 | 12356 |
| `80c6d44` | 45 | 11 | 0 | 12356 | 11950 |  | 0 | 0 | 12356 |
| `HEAD` | 45 | 11 | 0 | 12356 | 11950 |  | 0 | 0 | 12356 |

## Build `fd9d419`

| slice | status | fixes | accepted | closest m | <3m | 3-5m | >=5m | note |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `fixtures/20260713T203515-phase1e/fixtures_slice.aigprec` | ok | 658 | 642 |  | 0 | 0 | 658 | single-log-dir |
| `fixtures/20260714-analysis-slices/phase1e_countdown_and_gate.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714-analysis-slices/phase2a_countdown_future_start.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714-analysis-slices/phase2b_closest_gate_3p97m.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714-analysis-slices/phase2b_countdown_future_start.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714-analysis-slices/phase2c_closest_gate_6p98m.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714-analysis-slices/phase2c_countdown_future_start.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714T111500-analysis-slices/phase1d-race-vision.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714T111500-analysis-slices/phase1e-inflight.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714T111500-analysis-slices/phase2a-controlled-flight.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714T111500-analysis-slices/phase2b-race-legal.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714T203252-phase3a-r2training/r2_f2_slice_start.aigprec` | ok | 93 | 88 |  | 0 | 0 | 93 | flight-index-f2 |
| `fixtures/20260714T203252-phase3a-r2training/r2_f3_slice_start.aigprec` | ok | 407 | 395 |  | 0 | 0 | 407 | flight-index-f3 |
| `fixtures/20260714T212450-phase3b-r2training/20260714T210518-58cd98ad_r2_slice_start.aigprec` | ok | 355 | 339 |  | 0 | 0 | 355 | direct-prefix |
| `fixtures/20260714T212450-phase3b-r2training/20260714T210844-58cd98ad_r2_slice_start.aigprec` | ok | 368 | 361 |  | 0 | 0 | 368 | direct-prefix |
| `fixtures/20260714T212450-phase3b-r2training/20260714T211404-58cd98ad_r2_slice_start.aigprec` | ok | 351 | 339 |  | 0 | 0 | 351 | direct-prefix |
| `fixtures/20260715T052244-phase3c-r2training/20260715T045100-411f3135_r2c_slice_start.aigprec` | ok | 356 | 350 |  | 0 | 0 | 356 | direct-prefix |
| `fixtures/20260715T052244-phase3c-r2training/20260715T045458-411f3135_r2c_slice_start.aigprec` | ok | 368 | 353 |  | 0 | 0 | 368 | direct-prefix |
| `fixtures/20260715T052244-phase3c-r2training/20260715T051458-6092dbc0_r2c_slice_start.aigprec` | ok | 335 | 326 |  | 0 | 0 | 335 | direct-prefix |
| `fixtures/20260715T135600-phase3d-r2training/20260715T051458-6092dbc0_r2d_slice_start.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260715T135600-phase3d-r2training/20260715T121747-22978559_r2d_slice_start.aigprec` | ok | 305 | 294 |  | 0 | 0 | 305 | direct-prefix |
| `fixtures/20260715T135600-phase3d-r2training/20260715T122040-22978559_r2d_slice_start.aigprec` | ok | 315 | 298 |  | 0 | 0 | 315 | direct-prefix |
| `fixtures/20260715T135600-phase3d-r2training/20260715T122352-22978559_r2d_slice_start.aigprec` | ok | 298 | 286 |  | 0 | 0 | 298 | direct-prefix |
| `fixtures/20260715T190627-phase3e-r2training-slow/20260715T183716-8e6cf1f5_r2e_slice_start.aigprec` | ok | 292 | 279 |  | 0 | 0 | 292 | direct-prefix |
| `fixtures/20260715T190627-phase3e-r2training-slow/20260715T184758-8e6cf1f5_r2e_slice_start.aigprec` | ok | 292 | 282 |  | 0 | 0 | 292 | direct-prefix |
| `fixtures/20260715T190627-phase3e-r2training-slow/20260715T185046-8e6cf1f5_r2e_slice_start.aigprec` | ok | 271 | 253 |  | 0 | 0 | 271 | direct-prefix |
| `fixtures/20260715T190627-phase3e-r2training-slow/20260715T185843-7f28e2fb_r2e_slice_start.aigprec` | ok | 308 | 295 |  | 0 | 0 | 308 | direct-prefix |
| `fixtures/20260715T200734-phase3f-r2training-slow/20260715T195033-8edfeec4_r2f_slice_start.aigprec` | ok | 272 | 270 |  | 0 | 0 | 272 | direct-prefix |
| `fixtures/20260715T200734-phase3f-r2training-slow/20260715T200011-8edfeec4_r2f_slice_start.aigprec` | ok | 276 | 267 |  | 0 | 0 | 276 | direct-prefix |
| `fixtures/20260715T200734-phase3f-r2training-slow/20260715T200142-8edfeec4_r2f_slice_start.aigprec` | ok | 251 | 237 |  | 0 | 0 | 251 | direct-prefix |
| `fixtures/20260715T211420-phase3g-r2training/20260715T203300-8edfeec4_r2g_slice_start.aigprec` | ok | 333 | 320 |  | 0 | 0 | 333 | direct-prefix |
| `fixtures/20260715T211420-phase3g-r2training/20260715T204925-8edfeec4_r2g_slice_start.aigprec` | ok | 268 | 267 |  | 0 | 0 | 268 | direct-prefix |
| `fixtures/20260715T211420-phase3g-r2training/20260715T205124-8edfeec4_r2g_slice_start.aigprec` | ok | 304 | 295 |  | 0 | 0 | 304 | direct-prefix |
| `fixtures/20260715T211420-phase3g-r2training/20260715T205845-fc86a160_r2g_slice_start.aigprec` | ok | 106 | 102 |  | 0 | 0 | 106 | direct-prefix |
| `fixtures/20260716T023148-phase3h-r2training/20260715T213138-8edfeec4_r2h_slice_start.aigprec` | ok | 298 | 283 |  | 0 | 0 | 298 | direct-prefix |
| `fixtures/20260716T023148-phase3h-r2training/20260715T213225-8edfeec4_r2h_slice_start.aigprec` | ok | 302 | 289 |  | 0 | 0 | 302 | direct-prefix |
| `fixtures/20260716T023148-phase3h-r2training/20260715T213406-fc86a160_r2h_slice_start.aigprec` | ok | 318 | 311 |  | 0 | 0 | 318 | direct-prefix |
| `fixtures/20260716T023148-phase3h-r2training/20260716T022502-8edfeec4_r2h_slice_start.aigprec` | ok | 280 | 271 |  | 0 | 0 | 280 | direct-prefix |
| `fixtures/20260716T115732-phase3i-r2training/20260716T031114-8edfeec4_r2i_slice_start.aigprec` | ok | 178 | 176 |  | 0 | 0 | 178 | direct-prefix |
| `fixtures/20260716T115732-phase3i-r2training/20260716T113216-8edfeec4_r2i_slice_start.aigprec` | ok | 189 | 186 |  | 0 | 0 | 189 | direct-prefix |
| `fixtures/20260716T115732-phase3i-r2training/20260716T114244-8edfeec4_r2i_slice_start.aigprec` | ok | 313 | 307 |  | 0 | 0 | 313 | direct-prefix |
| `fixtures/20260716T132549-phase3j-r2training-rerun/20260716T130659-8edfeec4_r2j_rerun_slice_start.aigprec` | ok | 268 | 267 |  | 0 | 0 | 268 | direct-prefix |
| `fixtures/20260716T132549-phase3j-r2training-rerun/20260716T131137-2ca531c3_r2j_rerun_slice_start.aigprec` | ok | 291 | 282 |  | 0 | 0 | 291 | direct-prefix |
| `fixtures/20260716T132549-phase3j-r2training-rerun/20260716T131630-8edfeec4_r2j_rerun_slice_start.aigprec` | ok | 42 | 39 |  | 0 | 0 | 42 | direct-prefix |
| `fixtures/20260716T132549-phase3j-r2training-rerun/20260716T131802-8edfeec4_r2j_rerun_slice_start.aigprec` | ok | 270 | 257 |  | 0 | 0 | 270 | direct-prefix |
| `fixtures/20260716T135229-phase4a-r2training-chain/20260716T133531-927a4c97_r2a_nopass_start_slice.aigprec` | ok | 268 | 259 |  | 0 | 0 | 268 | direct-prefix |
| `fixtures/20260716T135229-phase4a-r2training-chain/20260716T134309-927a4c97_r2a_nopass_start_slice.aigprec` | ok | 60 | 55 |  | 0 | 0 | 60 | direct-prefix |
| `fixtures/20260716T135229-phase4a-r2training-chain/20260716T134842-927a4c97_r2a_nopass_start_slice.aigprec` | ok | 197 | 190 |  | 0 | 0 | 197 | direct-prefix |
| `fixtures/20260716T144305-phase4b-r2training-chain/20260716T143604-927a4c97_r2b_nopass_start_slice.aigprec` | ok | 272 | 264 |  | 0 | 0 | 272 | direct-prefix |
| `fixtures/20260716T144305-phase4b-r2training-chain/20260716T143739-927a4c97_r2b_nopass_start_slice.aigprec` | ok | 217 | 207 |  | 0 | 0 | 217 | direct-prefix |
| `fixtures/20260716T144305-phase4b-r2training-chain/20260716T143915-927a4c97_r2b_nopass_start_slice.aigprec` | ok | 254 | 240 |  | 0 | 0 | 254 | direct-prefix |
| `fixtures/20260716T154946-phase4b-r2training-chain-v2/20260716T153120-927a4c97_r2b_v2_nopass_start_slice.aigprec` | ok | 240 | 232 |  | 0 | 0 | 240 | direct-prefix |
| `fixtures/20260716T154946-phase4b-r2training-chain-v2/20260716T153853-927a4c97_r2b_v2_nopass_start_slice.aigprec` | ok | 264 | 254 |  | 0 | 0 | 264 | direct-prefix |
| `fixtures/20260716T174215-phase4c-r2training-chain/20260716T164931-927a4c97_r2c_commitwindow_slice.aigprec` | ok | 226 | 226 |  | 0 | 0 | 226 | direct-prefix |
| `fixtures/20260716T174215-phase4c-r2training-chain/20260716T165306-927a4c97_r2c_commitwindow_slice.aigprec` | ok | 221 | 220 |  | 0 | 0 | 221 | direct-prefix |
| `fixtures/20260716T174215-phase4c-r2training-chain/20260716T165535-927a4c97_r2c_commitwindow_slice.aigprec` | ok | 206 | 197 |  | 0 | 0 | 206 | direct-prefix |

## Build `54a75a1`

| slice | status | fixes | accepted | closest m | <3m | 3-5m | >=5m | note |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `fixtures/20260713T203515-phase1e/fixtures_slice.aigprec` | ok | 658 | 642 |  | 0 | 0 | 658 | single-log-dir |
| `fixtures/20260714-analysis-slices/phase1e_countdown_and_gate.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714-analysis-slices/phase2a_countdown_future_start.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714-analysis-slices/phase2b_closest_gate_3p97m.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714-analysis-slices/phase2b_countdown_future_start.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714-analysis-slices/phase2c_closest_gate_6p98m.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714-analysis-slices/phase2c_countdown_future_start.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714T111500-analysis-slices/phase1d-race-vision.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714T111500-analysis-slices/phase1e-inflight.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714T111500-analysis-slices/phase2a-controlled-flight.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714T111500-analysis-slices/phase2b-race-legal.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714T203252-phase3a-r2training/r2_f2_slice_start.aigprec` | ok | 93 | 88 |  | 0 | 0 | 93 | flight-index-f2 |
| `fixtures/20260714T203252-phase3a-r2training/r2_f3_slice_start.aigprec` | ok | 407 | 395 |  | 0 | 0 | 407 | flight-index-f3 |
| `fixtures/20260714T212450-phase3b-r2training/20260714T210518-58cd98ad_r2_slice_start.aigprec` | ok | 355 | 339 |  | 0 | 0 | 355 | direct-prefix |
| `fixtures/20260714T212450-phase3b-r2training/20260714T210844-58cd98ad_r2_slice_start.aigprec` | ok | 368 | 361 |  | 0 | 0 | 368 | direct-prefix |
| `fixtures/20260714T212450-phase3b-r2training/20260714T211404-58cd98ad_r2_slice_start.aigprec` | ok | 351 | 339 |  | 0 | 0 | 351 | direct-prefix |
| `fixtures/20260715T052244-phase3c-r2training/20260715T045100-411f3135_r2c_slice_start.aigprec` | ok | 356 | 350 |  | 0 | 0 | 356 | direct-prefix |
| `fixtures/20260715T052244-phase3c-r2training/20260715T045458-411f3135_r2c_slice_start.aigprec` | ok | 368 | 353 |  | 0 | 0 | 368 | direct-prefix |
| `fixtures/20260715T052244-phase3c-r2training/20260715T051458-6092dbc0_r2c_slice_start.aigprec` | ok | 335 | 326 |  | 0 | 0 | 335 | direct-prefix |
| `fixtures/20260715T135600-phase3d-r2training/20260715T051458-6092dbc0_r2d_slice_start.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260715T135600-phase3d-r2training/20260715T121747-22978559_r2d_slice_start.aigprec` | ok | 305 | 294 |  | 0 | 0 | 305 | direct-prefix |
| `fixtures/20260715T135600-phase3d-r2training/20260715T122040-22978559_r2d_slice_start.aigprec` | ok | 315 | 298 |  | 0 | 0 | 315 | direct-prefix |
| `fixtures/20260715T135600-phase3d-r2training/20260715T122352-22978559_r2d_slice_start.aigprec` | ok | 298 | 286 |  | 0 | 0 | 298 | direct-prefix |
| `fixtures/20260715T190627-phase3e-r2training-slow/20260715T183716-8e6cf1f5_r2e_slice_start.aigprec` | ok | 292 | 279 |  | 0 | 0 | 292 | direct-prefix |
| `fixtures/20260715T190627-phase3e-r2training-slow/20260715T184758-8e6cf1f5_r2e_slice_start.aigprec` | ok | 292 | 282 |  | 0 | 0 | 292 | direct-prefix |
| `fixtures/20260715T190627-phase3e-r2training-slow/20260715T185046-8e6cf1f5_r2e_slice_start.aigprec` | ok | 271 | 253 |  | 0 | 0 | 271 | direct-prefix |
| `fixtures/20260715T190627-phase3e-r2training-slow/20260715T185843-7f28e2fb_r2e_slice_start.aigprec` | ok | 308 | 295 |  | 0 | 0 | 308 | direct-prefix |
| `fixtures/20260715T200734-phase3f-r2training-slow/20260715T195033-8edfeec4_r2f_slice_start.aigprec` | ok | 272 | 270 |  | 0 | 0 | 272 | direct-prefix |
| `fixtures/20260715T200734-phase3f-r2training-slow/20260715T200011-8edfeec4_r2f_slice_start.aigprec` | ok | 276 | 267 |  | 0 | 0 | 276 | direct-prefix |
| `fixtures/20260715T200734-phase3f-r2training-slow/20260715T200142-8edfeec4_r2f_slice_start.aigprec` | ok | 251 | 237 |  | 0 | 0 | 251 | direct-prefix |
| `fixtures/20260715T211420-phase3g-r2training/20260715T203300-8edfeec4_r2g_slice_start.aigprec` | ok | 333 | 320 |  | 0 | 0 | 333 | direct-prefix |
| `fixtures/20260715T211420-phase3g-r2training/20260715T204925-8edfeec4_r2g_slice_start.aigprec` | ok | 268 | 267 |  | 0 | 0 | 268 | direct-prefix |
| `fixtures/20260715T211420-phase3g-r2training/20260715T205124-8edfeec4_r2g_slice_start.aigprec` | ok | 304 | 295 |  | 0 | 0 | 304 | direct-prefix |
| `fixtures/20260715T211420-phase3g-r2training/20260715T205845-fc86a160_r2g_slice_start.aigprec` | ok | 106 | 102 |  | 0 | 0 | 106 | direct-prefix |
| `fixtures/20260716T023148-phase3h-r2training/20260715T213138-8edfeec4_r2h_slice_start.aigprec` | ok | 298 | 283 |  | 0 | 0 | 298 | direct-prefix |
| `fixtures/20260716T023148-phase3h-r2training/20260715T213225-8edfeec4_r2h_slice_start.aigprec` | ok | 302 | 289 |  | 0 | 0 | 302 | direct-prefix |
| `fixtures/20260716T023148-phase3h-r2training/20260715T213406-fc86a160_r2h_slice_start.aigprec` | ok | 318 | 311 |  | 0 | 0 | 318 | direct-prefix |
| `fixtures/20260716T023148-phase3h-r2training/20260716T022502-8edfeec4_r2h_slice_start.aigprec` | ok | 280 | 271 |  | 0 | 0 | 280 | direct-prefix |
| `fixtures/20260716T115732-phase3i-r2training/20260716T031114-8edfeec4_r2i_slice_start.aigprec` | ok | 178 | 176 |  | 0 | 0 | 178 | direct-prefix |
| `fixtures/20260716T115732-phase3i-r2training/20260716T113216-8edfeec4_r2i_slice_start.aigprec` | ok | 189 | 186 |  | 0 | 0 | 189 | direct-prefix |
| `fixtures/20260716T115732-phase3i-r2training/20260716T114244-8edfeec4_r2i_slice_start.aigprec` | ok | 313 | 307 |  | 0 | 0 | 313 | direct-prefix |
| `fixtures/20260716T132549-phase3j-r2training-rerun/20260716T130659-8edfeec4_r2j_rerun_slice_start.aigprec` | ok | 268 | 267 |  | 0 | 0 | 268 | direct-prefix |
| `fixtures/20260716T132549-phase3j-r2training-rerun/20260716T131137-2ca531c3_r2j_rerun_slice_start.aigprec` | ok | 291 | 282 |  | 0 | 0 | 291 | direct-prefix |
| `fixtures/20260716T132549-phase3j-r2training-rerun/20260716T131630-8edfeec4_r2j_rerun_slice_start.aigprec` | ok | 42 | 39 |  | 0 | 0 | 42 | direct-prefix |
| `fixtures/20260716T132549-phase3j-r2training-rerun/20260716T131802-8edfeec4_r2j_rerun_slice_start.aigprec` | ok | 270 | 257 |  | 0 | 0 | 270 | direct-prefix |
| `fixtures/20260716T135229-phase4a-r2training-chain/20260716T133531-927a4c97_r2a_nopass_start_slice.aigprec` | ok | 268 | 259 |  | 0 | 0 | 268 | direct-prefix |
| `fixtures/20260716T135229-phase4a-r2training-chain/20260716T134309-927a4c97_r2a_nopass_start_slice.aigprec` | ok | 60 | 55 |  | 0 | 0 | 60 | direct-prefix |
| `fixtures/20260716T135229-phase4a-r2training-chain/20260716T134842-927a4c97_r2a_nopass_start_slice.aigprec` | ok | 197 | 190 |  | 0 | 0 | 197 | direct-prefix |
| `fixtures/20260716T144305-phase4b-r2training-chain/20260716T143604-927a4c97_r2b_nopass_start_slice.aigprec` | ok | 272 | 264 |  | 0 | 0 | 272 | direct-prefix |
| `fixtures/20260716T144305-phase4b-r2training-chain/20260716T143739-927a4c97_r2b_nopass_start_slice.aigprec` | ok | 217 | 207 |  | 0 | 0 | 217 | direct-prefix |
| `fixtures/20260716T144305-phase4b-r2training-chain/20260716T143915-927a4c97_r2b_nopass_start_slice.aigprec` | ok | 254 | 240 |  | 0 | 0 | 254 | direct-prefix |
| `fixtures/20260716T154946-phase4b-r2training-chain-v2/20260716T153120-927a4c97_r2b_v2_nopass_start_slice.aigprec` | ok | 240 | 232 |  | 0 | 0 | 240 | direct-prefix |
| `fixtures/20260716T154946-phase4b-r2training-chain-v2/20260716T153853-927a4c97_r2b_v2_nopass_start_slice.aigprec` | ok | 264 | 254 |  | 0 | 0 | 264 | direct-prefix |
| `fixtures/20260716T174215-phase4c-r2training-chain/20260716T164931-927a4c97_r2c_commitwindow_slice.aigprec` | ok | 226 | 226 |  | 0 | 0 | 226 | direct-prefix |
| `fixtures/20260716T174215-phase4c-r2training-chain/20260716T165306-927a4c97_r2c_commitwindow_slice.aigprec` | ok | 221 | 220 |  | 0 | 0 | 221 | direct-prefix |
| `fixtures/20260716T174215-phase4c-r2training-chain/20260716T165535-927a4c97_r2c_commitwindow_slice.aigprec` | ok | 206 | 197 |  | 0 | 0 | 206 | direct-prefix |

## Build `80c6d44`

| slice | status | fixes | accepted | closest m | <3m | 3-5m | >=5m | note |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `fixtures/20260713T203515-phase1e/fixtures_slice.aigprec` | ok | 658 | 642 |  | 0 | 0 | 658 | single-log-dir |
| `fixtures/20260714-analysis-slices/phase1e_countdown_and_gate.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714-analysis-slices/phase2a_countdown_future_start.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714-analysis-slices/phase2b_closest_gate_3p97m.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714-analysis-slices/phase2b_countdown_future_start.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714-analysis-slices/phase2c_closest_gate_6p98m.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714-analysis-slices/phase2c_countdown_future_start.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714T111500-analysis-slices/phase1d-race-vision.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714T111500-analysis-slices/phase1e-inflight.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714T111500-analysis-slices/phase2a-controlled-flight.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714T111500-analysis-slices/phase2b-race-legal.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714T203252-phase3a-r2training/r2_f2_slice_start.aigprec` | ok | 93 | 88 |  | 0 | 0 | 93 | flight-index-f2 |
| `fixtures/20260714T203252-phase3a-r2training/r2_f3_slice_start.aigprec` | ok | 407 | 395 |  | 0 | 0 | 407 | flight-index-f3 |
| `fixtures/20260714T212450-phase3b-r2training/20260714T210518-58cd98ad_r2_slice_start.aigprec` | ok | 355 | 339 |  | 0 | 0 | 355 | direct-prefix |
| `fixtures/20260714T212450-phase3b-r2training/20260714T210844-58cd98ad_r2_slice_start.aigprec` | ok | 368 | 361 |  | 0 | 0 | 368 | direct-prefix |
| `fixtures/20260714T212450-phase3b-r2training/20260714T211404-58cd98ad_r2_slice_start.aigprec` | ok | 351 | 339 |  | 0 | 0 | 351 | direct-prefix |
| `fixtures/20260715T052244-phase3c-r2training/20260715T045100-411f3135_r2c_slice_start.aigprec` | ok | 356 | 350 |  | 0 | 0 | 356 | direct-prefix |
| `fixtures/20260715T052244-phase3c-r2training/20260715T045458-411f3135_r2c_slice_start.aigprec` | ok | 368 | 353 |  | 0 | 0 | 368 | direct-prefix |
| `fixtures/20260715T052244-phase3c-r2training/20260715T051458-6092dbc0_r2c_slice_start.aigprec` | ok | 335 | 326 |  | 0 | 0 | 335 | direct-prefix |
| `fixtures/20260715T135600-phase3d-r2training/20260715T051458-6092dbc0_r2d_slice_start.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260715T135600-phase3d-r2training/20260715T121747-22978559_r2d_slice_start.aigprec` | ok | 305 | 294 |  | 0 | 0 | 305 | direct-prefix |
| `fixtures/20260715T135600-phase3d-r2training/20260715T122040-22978559_r2d_slice_start.aigprec` | ok | 315 | 298 |  | 0 | 0 | 315 | direct-prefix |
| `fixtures/20260715T135600-phase3d-r2training/20260715T122352-22978559_r2d_slice_start.aigprec` | ok | 298 | 286 |  | 0 | 0 | 298 | direct-prefix |
| `fixtures/20260715T190627-phase3e-r2training-slow/20260715T183716-8e6cf1f5_r2e_slice_start.aigprec` | ok | 292 | 279 |  | 0 | 0 | 292 | direct-prefix |
| `fixtures/20260715T190627-phase3e-r2training-slow/20260715T184758-8e6cf1f5_r2e_slice_start.aigprec` | ok | 292 | 282 |  | 0 | 0 | 292 | direct-prefix |
| `fixtures/20260715T190627-phase3e-r2training-slow/20260715T185046-8e6cf1f5_r2e_slice_start.aigprec` | ok | 271 | 253 |  | 0 | 0 | 271 | direct-prefix |
| `fixtures/20260715T190627-phase3e-r2training-slow/20260715T185843-7f28e2fb_r2e_slice_start.aigprec` | ok | 308 | 295 |  | 0 | 0 | 308 | direct-prefix |
| `fixtures/20260715T200734-phase3f-r2training-slow/20260715T195033-8edfeec4_r2f_slice_start.aigprec` | ok | 272 | 270 |  | 0 | 0 | 272 | direct-prefix |
| `fixtures/20260715T200734-phase3f-r2training-slow/20260715T200011-8edfeec4_r2f_slice_start.aigprec` | ok | 276 | 267 |  | 0 | 0 | 276 | direct-prefix |
| `fixtures/20260715T200734-phase3f-r2training-slow/20260715T200142-8edfeec4_r2f_slice_start.aigprec` | ok | 251 | 237 |  | 0 | 0 | 251 | direct-prefix |
| `fixtures/20260715T211420-phase3g-r2training/20260715T203300-8edfeec4_r2g_slice_start.aigprec` | ok | 333 | 320 |  | 0 | 0 | 333 | direct-prefix |
| `fixtures/20260715T211420-phase3g-r2training/20260715T204925-8edfeec4_r2g_slice_start.aigprec` | ok | 268 | 267 |  | 0 | 0 | 268 | direct-prefix |
| `fixtures/20260715T211420-phase3g-r2training/20260715T205124-8edfeec4_r2g_slice_start.aigprec` | ok | 304 | 295 |  | 0 | 0 | 304 | direct-prefix |
| `fixtures/20260715T211420-phase3g-r2training/20260715T205845-fc86a160_r2g_slice_start.aigprec` | ok | 106 | 102 |  | 0 | 0 | 106 | direct-prefix |
| `fixtures/20260716T023148-phase3h-r2training/20260715T213138-8edfeec4_r2h_slice_start.aigprec` | ok | 298 | 283 |  | 0 | 0 | 298 | direct-prefix |
| `fixtures/20260716T023148-phase3h-r2training/20260715T213225-8edfeec4_r2h_slice_start.aigprec` | ok | 302 | 289 |  | 0 | 0 | 302 | direct-prefix |
| `fixtures/20260716T023148-phase3h-r2training/20260715T213406-fc86a160_r2h_slice_start.aigprec` | ok | 318 | 311 |  | 0 | 0 | 318 | direct-prefix |
| `fixtures/20260716T023148-phase3h-r2training/20260716T022502-8edfeec4_r2h_slice_start.aigprec` | ok | 280 | 271 |  | 0 | 0 | 280 | direct-prefix |
| `fixtures/20260716T115732-phase3i-r2training/20260716T031114-8edfeec4_r2i_slice_start.aigprec` | ok | 178 | 176 |  | 0 | 0 | 178 | direct-prefix |
| `fixtures/20260716T115732-phase3i-r2training/20260716T113216-8edfeec4_r2i_slice_start.aigprec` | ok | 189 | 186 |  | 0 | 0 | 189 | direct-prefix |
| `fixtures/20260716T115732-phase3i-r2training/20260716T114244-8edfeec4_r2i_slice_start.aigprec` | ok | 313 | 307 |  | 0 | 0 | 313 | direct-prefix |
| `fixtures/20260716T132549-phase3j-r2training-rerun/20260716T130659-8edfeec4_r2j_rerun_slice_start.aigprec` | ok | 268 | 267 |  | 0 | 0 | 268 | direct-prefix |
| `fixtures/20260716T132549-phase3j-r2training-rerun/20260716T131137-2ca531c3_r2j_rerun_slice_start.aigprec` | ok | 291 | 282 |  | 0 | 0 | 291 | direct-prefix |
| `fixtures/20260716T132549-phase3j-r2training-rerun/20260716T131630-8edfeec4_r2j_rerun_slice_start.aigprec` | ok | 42 | 39 |  | 0 | 0 | 42 | direct-prefix |
| `fixtures/20260716T132549-phase3j-r2training-rerun/20260716T131802-8edfeec4_r2j_rerun_slice_start.aigprec` | ok | 270 | 257 |  | 0 | 0 | 270 | direct-prefix |
| `fixtures/20260716T135229-phase4a-r2training-chain/20260716T133531-927a4c97_r2a_nopass_start_slice.aigprec` | ok | 268 | 259 |  | 0 | 0 | 268 | direct-prefix |
| `fixtures/20260716T135229-phase4a-r2training-chain/20260716T134309-927a4c97_r2a_nopass_start_slice.aigprec` | ok | 60 | 55 |  | 0 | 0 | 60 | direct-prefix |
| `fixtures/20260716T135229-phase4a-r2training-chain/20260716T134842-927a4c97_r2a_nopass_start_slice.aigprec` | ok | 197 | 190 |  | 0 | 0 | 197 | direct-prefix |
| `fixtures/20260716T144305-phase4b-r2training-chain/20260716T143604-927a4c97_r2b_nopass_start_slice.aigprec` | ok | 272 | 264 |  | 0 | 0 | 272 | direct-prefix |
| `fixtures/20260716T144305-phase4b-r2training-chain/20260716T143739-927a4c97_r2b_nopass_start_slice.aigprec` | ok | 217 | 207 |  | 0 | 0 | 217 | direct-prefix |
| `fixtures/20260716T144305-phase4b-r2training-chain/20260716T143915-927a4c97_r2b_nopass_start_slice.aigprec` | ok | 254 | 240 |  | 0 | 0 | 254 | direct-prefix |
| `fixtures/20260716T154946-phase4b-r2training-chain-v2/20260716T153120-927a4c97_r2b_v2_nopass_start_slice.aigprec` | ok | 240 | 232 |  | 0 | 0 | 240 | direct-prefix |
| `fixtures/20260716T154946-phase4b-r2training-chain-v2/20260716T153853-927a4c97_r2b_v2_nopass_start_slice.aigprec` | ok | 264 | 254 |  | 0 | 0 | 264 | direct-prefix |
| `fixtures/20260716T174215-phase4c-r2training-chain/20260716T164931-927a4c97_r2c_commitwindow_slice.aigprec` | ok | 226 | 226 |  | 0 | 0 | 226 | direct-prefix |
| `fixtures/20260716T174215-phase4c-r2training-chain/20260716T165306-927a4c97_r2c_commitwindow_slice.aigprec` | ok | 221 | 220 |  | 0 | 0 | 221 | direct-prefix |
| `fixtures/20260716T174215-phase4c-r2training-chain/20260716T165535-927a4c97_r2c_commitwindow_slice.aigprec` | ok | 206 | 197 |  | 0 | 0 | 206 | direct-prefix |

## Build `HEAD`

| slice | status | fixes | accepted | closest m | <3m | 3-5m | >=5m | note |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `fixtures/20260713T203515-phase1e/fixtures_slice.aigprec` | ok | 658 | 642 |  | 0 | 0 | 658 | single-log-dir |
| `fixtures/20260714-analysis-slices/phase1e_countdown_and_gate.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714-analysis-slices/phase2a_countdown_future_start.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714-analysis-slices/phase2b_closest_gate_3p97m.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714-analysis-slices/phase2b_countdown_future_start.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714-analysis-slices/phase2c_closest_gate_6p98m.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714-analysis-slices/phase2c_countdown_future_start.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714T111500-analysis-slices/phase1d-race-vision.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714T111500-analysis-slices/phase1e-inflight.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714T111500-analysis-slices/phase2a-controlled-flight.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714T111500-analysis-slices/phase2b-race-legal.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260714T203252-phase3a-r2training/r2_f2_slice_start.aigprec` | ok | 93 | 88 |  | 0 | 0 | 93 | flight-index-f2 |
| `fixtures/20260714T203252-phase3a-r2training/r2_f3_slice_start.aigprec` | ok | 407 | 395 |  | 0 | 0 | 407 | flight-index-f3 |
| `fixtures/20260714T212450-phase3b-r2training/20260714T210518-58cd98ad_r2_slice_start.aigprec` | ok | 355 | 339 |  | 0 | 0 | 355 | direct-prefix |
| `fixtures/20260714T212450-phase3b-r2training/20260714T210844-58cd98ad_r2_slice_start.aigprec` | ok | 368 | 361 |  | 0 | 0 | 368 | direct-prefix |
| `fixtures/20260714T212450-phase3b-r2training/20260714T211404-58cd98ad_r2_slice_start.aigprec` | ok | 351 | 339 |  | 0 | 0 | 351 | direct-prefix |
| `fixtures/20260715T052244-phase3c-r2training/20260715T045100-411f3135_r2c_slice_start.aigprec` | ok | 356 | 350 |  | 0 | 0 | 356 | direct-prefix |
| `fixtures/20260715T052244-phase3c-r2training/20260715T045458-411f3135_r2c_slice_start.aigprec` | ok | 368 | 353 |  | 0 | 0 | 368 | direct-prefix |
| `fixtures/20260715T052244-phase3c-r2training/20260715T051458-6092dbc0_r2c_slice_start.aigprec` | ok | 335 | 326 |  | 0 | 0 | 335 | direct-prefix |
| `fixtures/20260715T135600-phase3d-r2training/20260715T051458-6092dbc0_r2d_slice_start.aigprec` | skipped |  |  |  | 0 |  |  | no unique flight log |
| `fixtures/20260715T135600-phase3d-r2training/20260715T121747-22978559_r2d_slice_start.aigprec` | ok | 305 | 294 |  | 0 | 0 | 305 | direct-prefix |
| `fixtures/20260715T135600-phase3d-r2training/20260715T122040-22978559_r2d_slice_start.aigprec` | ok | 315 | 298 |  | 0 | 0 | 315 | direct-prefix |
| `fixtures/20260715T135600-phase3d-r2training/20260715T122352-22978559_r2d_slice_start.aigprec` | ok | 298 | 286 |  | 0 | 0 | 298 | direct-prefix |
| `fixtures/20260715T190627-phase3e-r2training-slow/20260715T183716-8e6cf1f5_r2e_slice_start.aigprec` | ok | 292 | 279 |  | 0 | 0 | 292 | direct-prefix |
| `fixtures/20260715T190627-phase3e-r2training-slow/20260715T184758-8e6cf1f5_r2e_slice_start.aigprec` | ok | 292 | 282 |  | 0 | 0 | 292 | direct-prefix |
| `fixtures/20260715T190627-phase3e-r2training-slow/20260715T185046-8e6cf1f5_r2e_slice_start.aigprec` | ok | 271 | 253 |  | 0 | 0 | 271 | direct-prefix |
| `fixtures/20260715T190627-phase3e-r2training-slow/20260715T185843-7f28e2fb_r2e_slice_start.aigprec` | ok | 308 | 295 |  | 0 | 0 | 308 | direct-prefix |
| `fixtures/20260715T200734-phase3f-r2training-slow/20260715T195033-8edfeec4_r2f_slice_start.aigprec` | ok | 272 | 270 |  | 0 | 0 | 272 | direct-prefix |
| `fixtures/20260715T200734-phase3f-r2training-slow/20260715T200011-8edfeec4_r2f_slice_start.aigprec` | ok | 276 | 267 |  | 0 | 0 | 276 | direct-prefix |
| `fixtures/20260715T200734-phase3f-r2training-slow/20260715T200142-8edfeec4_r2f_slice_start.aigprec` | ok | 251 | 237 |  | 0 | 0 | 251 | direct-prefix |
| `fixtures/20260715T211420-phase3g-r2training/20260715T203300-8edfeec4_r2g_slice_start.aigprec` | ok | 333 | 320 |  | 0 | 0 | 333 | direct-prefix |
| `fixtures/20260715T211420-phase3g-r2training/20260715T204925-8edfeec4_r2g_slice_start.aigprec` | ok | 268 | 267 |  | 0 | 0 | 268 | direct-prefix |
| `fixtures/20260715T211420-phase3g-r2training/20260715T205124-8edfeec4_r2g_slice_start.aigprec` | ok | 304 | 295 |  | 0 | 0 | 304 | direct-prefix |
| `fixtures/20260715T211420-phase3g-r2training/20260715T205845-fc86a160_r2g_slice_start.aigprec` | ok | 106 | 102 |  | 0 | 0 | 106 | direct-prefix |
| `fixtures/20260716T023148-phase3h-r2training/20260715T213138-8edfeec4_r2h_slice_start.aigprec` | ok | 298 | 283 |  | 0 | 0 | 298 | direct-prefix |
| `fixtures/20260716T023148-phase3h-r2training/20260715T213225-8edfeec4_r2h_slice_start.aigprec` | ok | 302 | 289 |  | 0 | 0 | 302 | direct-prefix |
| `fixtures/20260716T023148-phase3h-r2training/20260715T213406-fc86a160_r2h_slice_start.aigprec` | ok | 318 | 311 |  | 0 | 0 | 318 | direct-prefix |
| `fixtures/20260716T023148-phase3h-r2training/20260716T022502-8edfeec4_r2h_slice_start.aigprec` | ok | 280 | 271 |  | 0 | 0 | 280 | direct-prefix |
| `fixtures/20260716T115732-phase3i-r2training/20260716T031114-8edfeec4_r2i_slice_start.aigprec` | ok | 178 | 176 |  | 0 | 0 | 178 | direct-prefix |
| `fixtures/20260716T115732-phase3i-r2training/20260716T113216-8edfeec4_r2i_slice_start.aigprec` | ok | 189 | 186 |  | 0 | 0 | 189 | direct-prefix |
| `fixtures/20260716T115732-phase3i-r2training/20260716T114244-8edfeec4_r2i_slice_start.aigprec` | ok | 313 | 307 |  | 0 | 0 | 313 | direct-prefix |
| `fixtures/20260716T132549-phase3j-r2training-rerun/20260716T130659-8edfeec4_r2j_rerun_slice_start.aigprec` | ok | 268 | 267 |  | 0 | 0 | 268 | direct-prefix |
| `fixtures/20260716T132549-phase3j-r2training-rerun/20260716T131137-2ca531c3_r2j_rerun_slice_start.aigprec` | ok | 291 | 282 |  | 0 | 0 | 291 | direct-prefix |
| `fixtures/20260716T132549-phase3j-r2training-rerun/20260716T131630-8edfeec4_r2j_rerun_slice_start.aigprec` | ok | 42 | 39 |  | 0 | 0 | 42 | direct-prefix |
| `fixtures/20260716T132549-phase3j-r2training-rerun/20260716T131802-8edfeec4_r2j_rerun_slice_start.aigprec` | ok | 270 | 257 |  | 0 | 0 | 270 | direct-prefix |
| `fixtures/20260716T135229-phase4a-r2training-chain/20260716T133531-927a4c97_r2a_nopass_start_slice.aigprec` | ok | 268 | 259 |  | 0 | 0 | 268 | direct-prefix |
| `fixtures/20260716T135229-phase4a-r2training-chain/20260716T134309-927a4c97_r2a_nopass_start_slice.aigprec` | ok | 60 | 55 |  | 0 | 0 | 60 | direct-prefix |
| `fixtures/20260716T135229-phase4a-r2training-chain/20260716T134842-927a4c97_r2a_nopass_start_slice.aigprec` | ok | 197 | 190 |  | 0 | 0 | 197 | direct-prefix |
| `fixtures/20260716T144305-phase4b-r2training-chain/20260716T143604-927a4c97_r2b_nopass_start_slice.aigprec` | ok | 272 | 264 |  | 0 | 0 | 272 | direct-prefix |
| `fixtures/20260716T144305-phase4b-r2training-chain/20260716T143739-927a4c97_r2b_nopass_start_slice.aigprec` | ok | 217 | 207 |  | 0 | 0 | 217 | direct-prefix |
| `fixtures/20260716T144305-phase4b-r2training-chain/20260716T143915-927a4c97_r2b_nopass_start_slice.aigprec` | ok | 254 | 240 |  | 0 | 0 | 254 | direct-prefix |
| `fixtures/20260716T154946-phase4b-r2training-chain-v2/20260716T153120-927a4c97_r2b_v2_nopass_start_slice.aigprec` | ok | 240 | 232 |  | 0 | 0 | 240 | direct-prefix |
| `fixtures/20260716T154946-phase4b-r2training-chain-v2/20260716T153853-927a4c97_r2b_v2_nopass_start_slice.aigprec` | ok | 264 | 254 |  | 0 | 0 | 264 | direct-prefix |
| `fixtures/20260716T174215-phase4c-r2training-chain/20260716T164931-927a4c97_r2c_commitwindow_slice.aigprec` | ok | 226 | 226 |  | 0 | 0 | 226 | direct-prefix |
| `fixtures/20260716T174215-phase4c-r2training-chain/20260716T165306-927a4c97_r2c_commitwindow_slice.aigprec` | ok | 221 | 220 |  | 0 | 0 | 221 | direct-prefix |
| `fixtures/20260716T174215-phase4c-r2training-chain/20260716T165535-927a4c97_r2c_commitwindow_slice.aigprec` | ok | 206 | 197 |  | 0 | 0 | 206 | direct-prefix |
