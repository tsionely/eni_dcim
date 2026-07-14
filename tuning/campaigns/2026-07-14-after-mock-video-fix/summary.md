# Mock Tuning Campaigns - 2026-07-14 After Mock Video Fix

Role: QA & MOCK-TUNER.

Context: rerun after pulling `e9b7790` / rebased head `1d27315`, which includes the mock video threading fix expected to address the previous flat 0/80 campaign issue.

Runtime notes:

- Commands were run from `C:\Users\tsion\Projects\eni_dcim_qa`, outside OneDrive.
- Commands used the in-process mock simulator only.
- Runtime logs were redirected through `tuning/mock-sim-config.json` to `tuning/runtime-logs`, then SQLite results were copied into this campaign folder.
- The CLI exposes optimizer selection but not seed selection, so the repeat used a different optimizer (`random`) rather than a different seed.

Campaign commands:

```powershell
& "C:\Users\tsion\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\run_campaign.py --flights 40 --optimizer cem --sim mock --config tuning\mock-sim-config.json
& "C:\Users\tsion\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" scripts\run_campaign.py --flights 40 --optimizer random --sim mock --config tuning\mock-sim-config.json
```

## CEM - `camp-20260714T091523`

- Flights: 40
- Best score: -200.054700
- Worst score: -480.407800
- Gates passed: min 0, max 0, total 0
- Aborted: 40/40
- Finished: 0/40
- Gate clips: 0 total
- Environment hits: 68 total

Score progression by 10-flight window:
- 01-10: avg -231.076, best -200.425, worst -340.381
- 11-20: avg -246.586, best -200.272, worst -360.403
- 21-30: avg -238.580, best -200.055, worst -480.408
- 31-40: avg -223.482, best -200.372, worst -326.730

Abort reasons:
- `environment collision (impulse=1.6)`: 1
- `environment collision (impulse=10.8)`: 1
- `environment collision (impulse=11.8)`: 1
- `environment collision (impulse=14.4)`: 1
- `environment collision (impulse=14.5)`: 1
- `environment collision (impulse=2.0)`: 1
- `environment collision (impulse=2.1)`: 1
- `environment collision (impulse=2.2)`: 1
- `environment collision (impulse=2.5)`: 1
- `environment collision (impulse=2.6)`: 1
- `environment collision (impulse=2.8)`: 4
- `environment collision (impulse=20.4)`: 1
- `environment collision (impulse=24.0)`: 1
- `environment collision (impulse=3.7)`: 1
- `environment collision (impulse=3.9)`: 1
- `environment collision (impulse=4.8)`: 1
- `environment collision (impulse=4.9)`: 1
- `environment collision (impulse=5.4)`: 1
- `environment collision (impulse=5.8)`: 1
- `environment collision (impulse=7.7)`: 1
- `environment collision (impulse=8.6)`: 1
- `environment collision (impulse=9.1)`: 1
- `stale channels: frame`: 15

Best params:

```json
{
  "control": {
    "att_rate": {
      "hover_thrust": 0.6197586890017921,
      "rate_d": 0.05,
      "rate_i": 0.0,
      "rate_p": 8.0,
      "rate_sign_pitch": -1.0,
      "rate_sign_roll": -1.0,
      "rate_sign_yaw": -1.0,
      "tilt_max_rad": 0.34886005833553285,
      "vel_d": 0.0,
      "vel_i": 0.05,
      "vel_p": 0.2846374574150243,
      "vz_i": 0.4,
      "vz_p": 0.7645015196645921
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
      "near_distance_m": 2.7897501162475593,
      "speed_far_mps": 3.120296819685987,
      "speed_near_mps": 2.0034899268567368,
      "yaw_center_gain": 1.5
    },
    "commit": {
      "distance_m": 2.355034179862697,
      "duration_s": 1.3082197817565506,
      "speed_mps": 3.0712106176915
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

## RandomSearch - `camp-20260714T092339`

- Flights: 40
- Best score: -200.053100
- Worst score: -1541.439100
- Gates passed: min 0, max 0, total 0
- Aborted: 40/40
- Finished: 0/40
- Gate clips: 0 total
- Environment hits: 91 total

Score progression by 10-flight window:
- 01-10: avg -366.283, best -200.175, worst -1541.439
- 11-20: avg -213.032, best -200.053, worst -260.506
- 21-30: avg -206.203, best -200.053, worst -260.320
- 31-40: avg -200.171, best -200.053, worst -200.478

Abort reasons:
- `environment collision (impulse=1.7)`: 1
- `environment collision (impulse=2.6)`: 1
- `environment collision (impulse=3.4)`: 1
- `environment collision (impulse=31.0)`: 1
- `environment collision (impulse=32.6)`: 1
- `environment collision (impulse=4.2)`: 1
- `environment collision (impulse=5.2)`: 1
- `environment collision (impulse=6.5)`: 1
- `environment collision (impulse=6.7)`: 1
- `environment collision (impulse=6.9)`: 1
- `environment collision (impulse=8.0)`: 1
- `max duration`: 1
- `stale channels: frame`: 28

Best params:

```json
{
  "control": {
    "att_rate": {
      "hover_thrust": 0.4364992271022733,
      "rate_d": 0.05,
      "rate_i": 0.0,
      "rate_p": 8.0,
      "rate_sign_pitch": -1.0,
      "rate_sign_roll": -1.0,
      "rate_sign_yaw": -1.0,
      "tilt_max_rad": 0.2498218823341134,
      "vel_d": 0.0,
      "vel_i": 0.05,
      "vel_p": 0.5496532442966309,
      "vz_i": 0.4,
      "vz_p": 0.6484563712590569
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
      "near_distance_m": 7.796372484704421,
      "speed_far_mps": 3.0493949046185636,
      "speed_near_mps": 1.7466572102852334,
      "yaw_center_gain": 1.5
    },
    "commit": {
      "distance_m": 2.4055796055711425,
      "duration_s": 0.9624104304393051,
      "speed_mps": 2.3458649993302076
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

The mock video threading fix changed the campaign signal: scores are no longer flat, and both optimizers show meaningful score spread/progression. However, the expected gate-count improvement did not materialize in this rerun: all 80 flights still recorded 0 gates and all 80 aborted.

Best observed scores improved from the old flat ~-220.4 pattern to about -200.1, but the score function is still optimizing abort quality rather than gate completion. This should be treated as a remaining mock/pilot blocker and not as a successful parameter recommendation.
