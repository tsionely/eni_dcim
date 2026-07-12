"""Scalar PID with anti-windup and output clamping."""
from __future__ import annotations


class PID:
    def __init__(self, kp: float, ki: float = 0.0, kd: float = 0.0,
                 i_limit: float = 1.0, out_limit: float = float("inf")) -> None:
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.i_limit = i_limit
        self.out_limit = out_limit
        self._integral = 0.0
        self._last_error: float | None = None

    def reset(self) -> None:
        self._integral = 0.0
        self._last_error = None

    def update(self, error: float, dt: float) -> float:
        if dt <= 0.0:
            dt = 1e-4
        self._integral += error * dt
        self._integral = max(-self.i_limit, min(self.i_limit, self._integral))
        derivative = 0.0
        if self._last_error is not None:
            derivative = (error - self._last_error) / dt
        self._last_error = error
        out = self.kp * error + self.ki * self._integral + self.kd * derivative
        return max(-self.out_limit, min(self.out_limit, out))
