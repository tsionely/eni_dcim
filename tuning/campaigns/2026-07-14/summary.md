# Mock Tuning Campaigns - 2026-07-14

Role: QA & MOCK-TUNER.

Runtime notes:

- Commands were run against the in-process mock simulator only.
- A tuning-local config (`tuning/mock-sim-config.json`) redirected runtime logs to `tuning/runtime-logs` so the role only writes under `tuning/`.
- Consolidated SQLite results were copied to `tuning/campaigns/2026-07-14/results.sqlite`; per-run copies are in the optimizer folders.
- The CLI exposes optimizer selection but not seed selection, so the repeat was done with a different optimizer rather than a different seed.

Campaign commands:

```powershell
& "C:\Users\tsion\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\run_campaign.py --flights 40 --optimizer cem --sim mock --config tuning\mock-sim-config.json
& "C:\Users\tsion\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\run_campaign.py --flights 40 --optimizer random --sim mock --config tuning\mock-sim-config.json
```

## CEM - `camp-20260714T082947`

- Flights: 40
- Best score: -220.381200
- Gates passed: min 0, max 0, total 0
- Aborted: 40/40
- Finished: 0/40
- Gate clips: 0 total
- Environment hits: 40 total

Score progression by 10-flight window:
- 01-10: avg -220.391, best -220.384, worst -220.411
- 11-20: avg -220.394, best -220.381, worst -220.453
- 21-30: avg -220.388, best -220.381, worst -220.403
- 31-40: avg -220.386, best -220.383, worst -220.391

Best params:

```json
{
  "control": {
    "att_rate": {
      "hover_thrust": 0.3587950592229695,
      "rate_d": 0.05,
      "rate_i": 0.0,
      "rate_p": 8.0,
      "rate_sign_pitch": -1.0,
      "rate_sign_roll": -1.0,
      "rate_sign_yaw": -1.0,
      "tilt_max_rad": 0.24819402282861402,
      "vel_d": 0.0,
      "vel_i": 0.05,
      "vel_p": 0.47437037778000263,
      "vz_i": 0.4,
      "vz_p": 1.165359512410346
    },
    "backend": "att_rate",
    "throttle_down_s": 3.0,
    "velocity": {
      "frame": "ned",
      "max_climb_mps": 2.0,
      "max_speed_mps": 4.0,
      "slew_mps2": 6.0,
      "world_yaw_offset_rad": 0.0,
      "yaw_rate_max_rps": 1.5
    }
  },
  "estimation": {
    "gate_rel_max_age_s": 1.5,
    "gyro_bias_calib_s": 1.0,
    "mahony_kp": 0.5,
    "vel_leak": 0.05,
    "vision_blend": 0.6,
    "vision_vel_blend": 0.35
  },
  "learning": {
    "score": {
      "abort_penalty": 200.0,
      "collision_penalty": 20.0,
      "gate_weight": 100.0
    }
  },
  "perception": {
    "camera": {
      "fov_deg": 90.0
    },
    "detector": {
      "approx_eps_frac": 0.04,
      "max_area_frac": 0.7,
      "min_area_frac": 0.0008,
      "min_confidence": 0.3,
      "mode": "red_hsv",
      "red_hue_high_min": 168,
      "red_hue_low_max": 12,
      "red_sat_min": 90,
      "red_val_min": 70,
      "threshold": 180
    },
    "gate": {
      "height_m": 1.6,
      "width_m": 1.6
    }
  },
  "planner": {
    "approach": {
      "center_gain": 1.2,
      "near_distance_m": 5.788635899135133,
      "speed_far_mps": 3.1394394684421916,
      "speed_near_mps": 1.1933475997480767,
      "yaw_center_gain": 1.5
    },
    "commit": {
      "distance_m": 2.069476679601632,
      "duration_s": 1.1460043004204974,
      "speed_mps": 3.8362305446085654
    },
    "recover": {
      "brake_s": 0.8
    },
    "search": {
      "climb_mps": 0.0,
      "yaw_rate_rps": 0.6
    },
    "takeoff": {
      "climb_mps": 1.0,
      "duration_s": 1.5
    }
  },
  "safety": {
    "env_collision_abort_threat": 2,
    "flight_timeout_s": 120.0,
    "frame_stale_s": 0.5,
    "imu_stale_s": 0.05,
    "loop_overrun_abort_frac": 0.2,
    "max_gate_clips": 10
  }
}
```

## RandomSearch - `camp-20260714T083434`

- Flights: 40
- Best score: -220.373400
- Gates passed: min 0, max 0, total 0
- Aborted: 40/40
- Finished: 0/40
- Gate clips: 0 total
- Environment hits: 40 total

Score progression by 10-flight window:
- 01-10: avg -220.398, best -220.377, worst -220.509
- 11-20: avg -220.385, best -220.375, worst -220.391
- 21-30: avg -220.392, best -220.383, worst -220.403
- 31-40: avg -220.387, best -220.373, worst -220.400

Best params:

```json
{
  "control": {
    "att_rate": {
      "hover_thrust": 0.4216831135073842,
      "rate_d": 0.05,
      "rate_i": 0.0,
      "rate_p": 8.0,
      "rate_sign_pitch": -1.0,
      "rate_sign_roll": -1.0,
      "rate_sign_yaw": -1.0,
      "tilt_max_rad": 0.3366970600824541,
      "vel_d": 0.0,
      "vel_i": 0.05,
      "vel_p": 0.4721630311164724,
      "vz_i": 0.4,
      "vz_p": 1.3912189027651203
    },
    "backend": "att_rate",
    "throttle_down_s": 3.0,
    "velocity": {
      "frame": "ned",
      "max_climb_mps": 2.0,
      "max_speed_mps": 4.0,
      "slew_mps2": 6.0,
      "world_yaw_offset_rad": 0.0,
      "yaw_rate_max_rps": 1.5
    }
  },
  "estimation": {
    "gate_rel_max_age_s": 1.5,
    "gyro_bias_calib_s": 1.0,
    "mahony_kp": 0.5,
    "vel_leak": 0.05,
    "vision_blend": 0.6,
    "vision_vel_blend": 0.35
  },
  "learning": {
    "score": {
      "abort_penalty": 200.0,
      "collision_penalty": 20.0,
      "gate_weight": 100.0
    }
  },
  "perception": {
    "camera": {
      "fov_deg": 90.0
    },
    "detector": {
      "approx_eps_frac": 0.04,
      "max_area_frac": 0.7,
      "min_area_frac": 0.0008,
      "min_confidence": 0.3,
      "mode": "red_hsv",
      "red_hue_high_min": 168,
      "red_hue_low_max": 12,
      "red_sat_min": 90,
      "red_val_min": 70,
      "threshold": 180
    },
    "gate": {
      "height_m": 1.6,
      "width_m": 1.6
    }
  },
  "planner": {
    "approach": {
      "center_gain": 1.2,
      "near_distance_m": 5.539763555897184,
      "speed_far_mps": 5.656854108188316,
      "speed_near_mps": 1.1344173855495816,
      "yaw_center_gain": 1.5
    },
    "commit": {
      "distance_m": 2.7405377652586416,
      "duration_s": 0.7911607800212406,
      "speed_mps": 2.5940847648540997
    },
    "recover": {
      "brake_s": 0.8
    },
    "search": {
      "climb_mps": 0.0,
      "yaw_rate_rps": 0.6
    },
    "takeoff": {
      "climb_mps": 1.0,
      "duration_s": 1.5
    }
  },
  "safety": {
    "env_collision_abort_threat": 2,
    "flight_timeout_s": 120.0,
    "frame_stale_s": 0.5,
    "imu_stale_s": 0.05,
    "loop_overrun_abort_frac": 0.2,
    "max_gate_clips": 10
  }
}
```

## Overall finding

Across the two 40-flight mock campaigns, all 80 flights recorded 0 gates and aborted. Scores were nearly flat around -220.4, so the current mock campaign objective did not provide a useful tuning gradient for the active failure mode.

This should be treated as a QA signal rather than a good parameter recommendation: before trusting more tuning runs, the pilot/mock path likely needs inspection of the common abort condition and why gates remain at zero in every mock flight.
