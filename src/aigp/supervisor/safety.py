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
        # Debounce window (s): the physics engine emits a BURST of gate
        # contact events for a SINGLE frame brush — T3 measured 11 events
        # in 0.2s, tripping the 10-clip budget on ONE impact and aborting
        # a flight that was AT the gate. Contacts within this window of the
        # last counted clip fold into that clip (the pooled autopsy's
        # "do not merge repeated contact ticks into independent failures").
        # 0 disables (legacy per-event counting). Config-gated.
        self.gate_clip_debounce_s = float(params.get(
            "safety.gate_clip_debounce_s", default=0.0))
        self.gate_clips = 0
        self.env_hits = 0
        self._last_clip_ns: int | None = None

    def reset(self) -> None:
        self.gate_clips = 0
        self.env_hits = 0
        self._last_clip_ns = None

    def assess(self, event: CollisionEvent) -> CollisionVerdict:
        if event.collision_id == CollisionEvent.ENVIRONMENT:
            self.env_hits += 1
            if event.threat_level >= self.env_abort_threat:
                return CollisionVerdict(True, f"environment collision (impulse={event.impulse:.1f})")
            return CollisionVerdict(False)
        if event.collision_id == CollisionEvent.GATE:
            if (self.gate_clip_debounce_s > 0.0
                    and self._last_clip_ns is not None
                    and (event.ts_ns - self._last_clip_ns)
                    <= self.gate_clip_debounce_s * 1e9):
                # Same impact burst: fold in, do not count or abort.
                self._last_clip_ns = event.ts_ns
                return CollisionVerdict(False)
            self._last_clip_ns = event.ts_ns
            self.gate_clips += 1
            if self.gate_clips > self.max_gate_clips:
                return CollisionVerdict(True, f"gate clip budget exceeded ({self.gate_clips})")
            return CollisionVerdict(False)
        return CollisionVerdict(False)
