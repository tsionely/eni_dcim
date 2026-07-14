# RandomSearch - camp-20260714T083434

Flights: 40
Best score: -220.373400
Gates passed: min 0, max 0, total 0
Aborted flights: 40/40
Finished flights: 0/40
Gate clips: total 0
Environment hits: total 40

Score progression by 10-flight window:
- 01-10: avg -220.398, best -220.377, worst -220.509
- 11-20: avg -220.385, best -220.375, worst -220.391
- 21-30: avg -220.392, best -220.383, worst -220.403
- 31-40: avg -220.387, best -220.373, worst -220.400

Abort reasons:
- `environment collision (impulse=1.9)`: 2
- `environment collision (impulse=2.0)`: 1
- `environment collision (impulse=2.1)`: 1
- `environment collision (impulse=2.2)`: 2
- `environment collision (impulse=2.3)`: 1
- `environment collision (impulse=2.5)`: 3
- `environment collision (impulse=2.6)`: 1
- `environment collision (impulse=2.7)`: 4
- `environment collision (impulse=2.8)`: 5
- `environment collision (impulse=2.9)`: 3
- `environment collision (impulse=3.0)`: 1
- `environment collision (impulse=3.1)`: 1
- `environment collision (impulse=3.2)`: 1
- `environment collision (impulse=3.3)`: 1
- `environment collision (impulse=3.7)`: 1
- `environment collision (impulse=3.8)`: 1
- `environment collision (impulse=3.9)`: 3
- `environment collision (impulse=4.1)`: 1
- `environment collision (impulse=4.5)`: 1
- `environment collision (impulse=4.8)`: 1
- `environment collision (impulse=4.9)`: 2
- `environment collision (impulse=6.1)`: 1
- `environment collision (impulse=6.3)`: 1
- `environment collision (impulse=6.7)`: 1

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
