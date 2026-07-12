"""Flight-lifecycle FSM.

    IDLE -> ARMING -> TAKEOFF -> RACING -> FINISHED -> DONE
                 \\------------------------> ABORTED -> DONE

Ticked first in every control-loop iteration. Owns arm/reset commands and the
flight verdict; the campaign runner talks only to this class, never to
MAVLink directly. The planner receives a mode ("takeoff" | "race" | "hover")
derived from the FSM state.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from aigp.core.bus import Bus
from aigp.core.messages import (
    CollisionEvent,
    FsmTransition,
    Heartbeat,
    RaceStatus,
    Topic,
)
from aigp.core.params import ParamSet
from aigp.supervisor.safety import CollisionPolicy
from aigp.supervisor.watchdog import Watchdog


class FlightState:
    IDLE = "IDLE"
    ARMING = "ARMING"
    TAKEOFF = "TAKEOFF"
    RACING = "RACING"
    FINISHED = "FINISHED"
    ABORTED = "ABORTED"
    DONE = "DONE"


@dataclass
class FlightResult:
    finished: bool = False
    aborted: bool = False
    abort_reason: str = ""
    gates_passed: int = 0
    lap_time_s: float | None = None
    gate_clips: int = 0
    env_hits: int = 0
    duration_s: float = 0.0
    loop_overrun_frac: float = 0.0

    def as_dict(self) -> dict:
        return {
            "finished": self.finished,
            "aborted": self.aborted,
            "abort_reason": self.abort_reason,
            "gates_passed": self.gates_passed,
            "lap_time_s": self.lap_time_s,
            "gate_clips": self.gate_clips,
            "env_hits": self.env_hits,
            "duration_s": self.duration_s,
            "loop_overrun_frac": self.loop_overrun_frac,
        }


ARM_RETRY_S = 1.0
ARM_TIMEOUT_S = 5.0
FINISH_HOVER_S = 1.0


class RaceManager:
    def __init__(self, mavlink_io, bus: Bus, params: ParamSet, clock) -> None:
        self.io = mavlink_io
        self.bus = bus
        self.clock = clock
        self.collision_policy = CollisionPolicy(params)
        self.takeoff_duration_s = float(params.get("planner.takeoff.duration_s"))
        self.flight_timeout_s = float(params.get("safety.flight_timeout_s"))

        self.watchdog = Watchdog()
        self.watchdog.register("imu", float(params.get("safety.imu_stale_s")))
        self.watchdog.register("frame", float(params.get("safety.frame_stale_s")))

        self.state = FlightState.IDLE
        self.result = FlightResult()
        self._t_state = time.monotonic()
        self._t_flight_start = time.monotonic()
        self._t_last_arm = 0.0
        self._last_gate_index: int | None = None
        self.gate_passed_flag = False    # consumed by the app each tick
        self.collision_flag = False      # consumed by the app each tick

    # ---------------------------------------------------------------- control

    def start_flight(self) -> None:
        self.state = FlightState.IDLE
        self.result = FlightResult()
        self.collision_policy.reset()
        self._last_gate_index = None
        self._t_flight_start = time.monotonic()
        self._transition(FlightState.ARMING, "flight start")
        self.io.arm()
        self._t_last_arm = time.monotonic()

    def reset_sim(self) -> None:
        self.io.sim_reset()

    @property
    def done(self) -> bool:
        return self.state == FlightState.DONE

    def planner_mode(self) -> str:
        if self.state == FlightState.TAKEOFF:
            return "takeoff"
        if self.state == FlightState.RACING:
            return "race"
        return "hover"

    def commands_active(self) -> bool:
        """Whether the control backend should be sending setpoints."""
        return self.state in (FlightState.TAKEOFF, FlightState.RACING,
                              FlightState.FINISHED)

    # ------------------------------------------------------------------- tick

    def tick(self, heartbeat: Heartbeat | None, race: RaceStatus | None,
             collisions: list[CollisionEvent]) -> str:
        """Advance the FSM. Returns the planner mode for this tick."""
        now = time.monotonic()
        self.gate_passed_flag = False
        self.collision_flag = False

        # Track race progress regardless of state.
        if race is not None:
            if self._last_gate_index is None:
                self._last_gate_index = race.active_gate_index
            elif race.active_gate_index > self._last_gate_index:
                self.result.gates_passed += race.active_gate_index - self._last_gate_index
                self._last_gate_index = race.active_gate_index
                self.gate_passed_flag = True

        # Collisions.
        for event in collisions:
            self.collision_flag = True
            verdict = self.collision_policy.assess(event)
            if verdict.abort and self.state in (FlightState.TAKEOFF, FlightState.RACING):
                self._abort(verdict.reason)
        self.result.gate_clips = self.collision_policy.gate_clips
        self.result.env_hits = self.collision_policy.env_hits

        # Watchdogs (only while flying).
        if self.state in (FlightState.TAKEOFF, FlightState.RACING):
            stale = self.watchdog.stale_channels(now)
            if stale:
                self._abort(f"stale channels: {', '.join(stale)}")
            elif now - self._t_flight_start > self.flight_timeout_s:
                self._abort("flight timeout")

        # State transitions.
        if self.state == FlightState.ARMING:
            if heartbeat is not None and heartbeat.armed:
                self._transition(FlightState.TAKEOFF, "armed")
            elif now - self._t_last_arm > ARM_RETRY_S:
                self.io.arm()
                self._t_last_arm = now
            if self.state == FlightState.ARMING and now - self._t_state > ARM_TIMEOUT_S:
                self._abort("arming timeout")

        elif self.state == FlightState.TAKEOFF:
            if now - self._t_state >= self.takeoff_duration_s:
                self._transition(FlightState.RACING, "takeoff complete")

        elif self.state == FlightState.RACING:
            if race is not None and race.finished:
                self.result.finished = True
                if race.started:
                    self.result.lap_time_s = (
                        race.race_finish_time_ns / 1e9
                        - race.race_start_boot_time_ms / 1e3
                    )
                self._transition(FlightState.FINISHED, "race finished")

        elif self.state == FlightState.FINISHED:
            if now - self._t_state >= FINISH_HOVER_S:
                self._finish()

        return self.planner_mode()

    def stop_flight(self, reason: str = "external stop") -> None:
        if self.state not in (FlightState.DONE, FlightState.ABORTED):
            self._abort(reason)

    def set_loop_overrun_frac(self, frac: float) -> None:
        self.result.loop_overrun_frac = frac

    # -------------------------------------------------------------- internals

    def _abort(self, reason: str) -> None:
        self.result.aborted = True
        self.result.abort_reason = reason
        self._transition(FlightState.ABORTED, reason)
        self._finish()

    def _finish(self) -> None:
        self.result.duration_s = time.monotonic() - self._t_flight_start
        self._transition(FlightState.DONE, "flight over")

    def _transition(self, dst: str, reason: str) -> None:
        src = self.state
        self.state = dst
        self._t_state = time.monotonic()
        self.bus.publish_event(
            Topic.FSM,
            FsmTransition(ts_ns=self.clock.sim_now_ns(), src=src, dst=dst, reason=reason),
        )
