"""Direct motor-RPM backend — future work.

Full control authority (rate loop + mixer in our code). Only worth pursuing
after the attitude-rate backend is competitive and loop-timing headroom is
proven on the target machine.
"""
from __future__ import annotations

from aigp.core.messages import Setpoint, StateEstimate
from aigp.control.interface import ControlBackend


class MotorBackend(ControlBackend):
    def __init__(self, mavlink_io, params) -> None:
        raise NotImplementedError(
            "Direct motor control is future work; use 'velocity' or 'att_rate'."
        )

    def update(self, sp: Setpoint, state: StateEstimate, dt: float) -> None:
        raise NotImplementedError

    def reset(self) -> None:
        raise NotImplementedError
