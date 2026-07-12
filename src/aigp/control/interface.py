"""Control backend interface — the control-authority ladder.

The pilot climbs from velocity setpoints (sim's inner loop stabilizes) to
attitude rates (Phase 6) to raw motor RPM (future), all behind this ABC so
the planner and supervisor never change.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from aigp.core.messages import Setpoint, StateEstimate


class ControlBackend(ABC):
    @abstractmethod
    def update(self, sp: Setpoint, state: StateEstimate, dt: float) -> None:
        """Track the setpoint: compute and SEND the MAVLink command."""

    @abstractmethod
    def reset(self) -> None:
        """Clear integrators / slew state between flights."""
