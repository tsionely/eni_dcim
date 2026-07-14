# RandomSearch - camp-20260714T092339

Flights: 40
Best score: -200.053100
Worst score: -1541.439100
Gates passed: min 0, max 0, total 0
Aborted flights: 40/40
Finished flights: 0/40
Gate clips: total 0
Environment hits: total 91

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
