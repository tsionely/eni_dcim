"""Collision policy.

Gate clips (id 1001, low threat) are part of racing: logged, counted,
tolerated up to a budget. Environment impacts (id 1002) at high threat abort
the flight. Thresholds live in the ParamSet (safety.*).
"""
from __future__ import annotations

from dataclasses import dataclass

from aigp.core.messages import CollisionEvent
from aigp.core.params import ParamSet


@dataclass
class CollisionVerdict:
    abort: bool
    reason: str = ""


class CollisionPolicy:
    def __init__(self, params: ParamSet) -> None:
        self.env_abort_threat = int(params.get("safety.env_collision_abort_threat"))
        self.max_gate_clips = int(params.get("safety.max_gate_clips"))
        self.gate_clips = 0
        self.env_hits = 0

    def reset(self) -> None:
        self.gate_clips = 0
        self.env_hits = 0

    def assess(self, event: CollisionEvent) -> CollisionVerdict:
        if event.collision_id == CollisionEvent.ENVIRONMENT:
            self.env_hits += 1
            if event.threat_level >= self.env_abort_threat:
                return CollisionVerdict(True, f"environment collision (impulse={event.impulse:.1f})")
            return CollisionVerdict(False)
        if event.collision_id == CollisionEvent.GATE:
            self.gate_clips += 1
            if self.gate_clips > self.max_gate_clips:
                return CollisionVerdict(True, f"gate clip budget exceeded ({self.gate_clips})")
            return CollisionVerdict(False)
        return CollisionVerdict(False)
