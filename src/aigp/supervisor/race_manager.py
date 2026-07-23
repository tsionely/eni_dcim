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
    THROTTLE_DOWN = "THROTTLE_DOWN"
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
        # The real sim gates motor release behind a "THROTTLE DOWN please"
        # handshake (phase1e finding): hold zero thrust after arming before
        # commanding anything else.
        self.throttle_down_s = float(params.get("control.throttle_down_s", default=1.5))
        # Early-start protection (phase2a: "Disqualified - Early Start"): stay
        # at zero thrust until the race actually STARTS — detected as a CHANGE
        # in race_start_boot_time_ms (the flag itself is sticky across races).
        self.go_timeout_s = float(params.get("control.go_timeout_s", default=45.0))

        self.watchdog = Watchdog()
        self.watchdog.register("imu", float(params.get("safety.imu_stale_s")))
        self.watchdog.register("frame", float(params.get("safety.frame_stale_s")))

        self.state = FlightState.IDLE
        self.result = FlightResult()
        self._t_state = time.monotonic()
        self._t_flight_start = time.monotonic()
        self._t_last_arm = 0.0
        self._last_gate_index: int | None = None
        self._initial_race_start_ms: int | None = None
        self.gate_passed_flag = False    # consumed by the app each tick
        self.collision_flag = False      # consumed by the app each tick

    # ---------------------------------------------------------------- control

    def start_flight(self) -> None:
        self.state = FlightState.IDLE
        self.result = FlightResult()
        self.collision_policy.reset()
        self._last_gate_index = None
        self._initial_race_start_ms = None
        # Capture the GO baseline BEFORE sending the arm command: the sim can
        # stamp race_start within the same tick as the arm-ack, and a baseline
        # taken from the first post-arm status then equals the fresh value —
        # the "changed since flight start" test never fires and the flight
        # hangs in THROTTLE_DOWN until timeout (seen on the mock, 1ms window).
        cached = self.bus.cell(Topic.RACE).get()[0]
        if cached is not None:
            self._initial_race_start_ms = cached.race_start_boot_time_ms
        self._t_flight_start = time.monotonic()
        # Arm ONLY the imu channel here: a dead launch has no IMU at all
        # (imu flows from connect on any live session). Frames legitimately
        # start only when the operator clicks RACE — seconds after we enter
        # THROTTLE_DOWN — so the frame channel is armed at the GO transition
        # instead (arming it here killed every real launch in that gap).
        self.watchdog.feed("imu")
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

        # Baseline for GO detection: the first race status seen this flight.
        if race is not None and self._initial_race_start_ms is None:
            self._initial_race_start_ms = race.race_start_boot_time_ms

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
        if self.state in (FlightState.TAKEOFF, FlightState.RACING,
                          FlightState.THROTTLE_DOWN):
            stale = self.watchdog.stale_channels(now)
            if stale:
                # Carry the measured gap in the reason: T2a's six stale-imu
                # aborts sat over logs with a CONTINUOUS imu stream — the
                # number the watchdog saw is the discriminating evidence.
                detail = ", ".join(
                    f"{n}({self.watchdog.gap_s(n, now):.3f}s)" for n in stale)
                self._abort(f"stale channels: {detail}")
            elif now - self._t_flight_start > self.flight_timeout_s:
                self._abort("flight timeout")

        # State transitions.
        if self.state == FlightState.ARMING:
            # Hold throttle at zero through the arming handshake.
            self.io.send_attitude_rates(0.0, 0.0, 0.0, 0.0)
            if heartbeat is not None and heartbeat.armed:
                self._transition(FlightState.THROTTLE_DOWN, "armed")
            elif now - self._t_last_arm > ARM_RETRY_S:
                self.io.arm()
                self._t_last_arm = now
            if self.state == FlightState.ARMING and now - self._t_state > ARM_TIMEOUT_S:
                self._abort("arming timeout")

        elif self.state == FlightState.THROTTLE_DOWN:
            self.io.send_attitude_rates(0.0, 0.0, 0.0, 0.0)
            if now - self._t_state >= self.throttle_down_s:
                # GO has two conditions (phase2b lesson: race_start updates at
                # COUNTDOWN start with a *future* timestamp — launching on the
                # change alone earned a 2688ms early-start DSQ):
                #   1. race_start changed since flight start (fresh race), and
                #   2. the sim clock has actually reached it.
                if race is not None and self._initial_race_start_ms is not None \
                        and race.race_start_boot_time_ms >= 0 \
                        and race.race_start_boot_time_ms != self._initial_race_start_ms \
                        and race.sim_boot_time_ms >= race.race_start_boot_time_ms:
                    self.watchdog.arm_all()   # race live: frames must flow now
                    self._transition(FlightState.TAKEOFF, "race GO")
                elif now - self._t_state >= self.go_timeout_s:
                    # No fresh race start observed (e.g. free-flight testing):
                    # proceed anyway rather than deadlock.
                    self.watchdog.arm_all()
                    self._transition(FlightState.TAKEOFF, "GO timeout — proceeding")

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
