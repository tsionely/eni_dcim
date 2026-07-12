"""In-process communication bus.

Two primitives:

- LatestValue: a one-slot cell for high-rate streams (IMU, frames, detections,
  state). Writers replace the value; readers grab the newest and can detect
  freshness via a monotonically increasing sequence number. The control loop
  never waits on these and never processes a backlog.

- EventQueue: a bounded queue for discrete events (collisions, FSM
  transitions) where every occurrence matters. Drained fully each supervisor
  tick. Overflow drops the oldest and counts the drop instead of blocking.

Every publish is also offered to an optional tap (the telemetry logger).
The tap must never block the publisher: it is invoked inline and is expected
to enqueue with drop-on-full semantics.
"""
from __future__ import annotations

import queue
import threading
from typing import Any, Callable


class LatestValue:
    """Thread-safe one-slot cell with a sequence number."""

    __slots__ = ("_lock", "_value", "_seq")

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._value: Any = None
        self._seq = 0

    def set(self, value: Any) -> int:
        with self._lock:
            self._value = value
            self._seq += 1
            return self._seq

    def get(self) -> tuple[Any, int]:
        """Return (value, seq). value is None if never set."""
        with self._lock:
            return self._value, self._seq

    def get_if_newer(self, last_seq: int) -> tuple[Any, int] | None:
        """Return (value, seq) only if a newer value than last_seq exists."""
        with self._lock:
            if self._seq > last_seq and self._value is not None:
                return self._value, self._seq
            return None


class EventQueue:
    """Bounded FIFO. put() never blocks: on overflow the oldest is dropped."""

    __slots__ = ("_q", "drops")

    def __init__(self, maxsize: int = 256) -> None:
        self._q: queue.Queue = queue.Queue(maxsize=maxsize)
        self.drops = 0

    def put(self, item: Any) -> None:
        while True:
            try:
                self._q.put_nowait(item)
                return
            except queue.Full:
                try:
                    self._q.get_nowait()
                    self.drops += 1
                except queue.Empty:
                    pass

    def drain(self) -> list[Any]:
        items = []
        while True:
            try:
                items.append(self._q.get_nowait())
            except queue.Empty:
                return items


class Bus:
    """Topic registry over LatestValue cells and EventQueues."""

    def __init__(self) -> None:
        self._cells: dict[str, LatestValue] = {}
        self._queues: dict[str, EventQueue] = {}
        self._lock = threading.Lock()
        self._tap: Callable[[str, Any], None] | None = None

    # -- registry -----------------------------------------------------------

    def cell(self, topic: str) -> LatestValue:
        with self._lock:
            c = self._cells.get(topic)
            if c is None:
                c = self._cells[topic] = LatestValue()
            return c

    def events(self, topic: str, maxsize: int = 256) -> EventQueue:
        with self._lock:
            q = self._queues.get(topic)
            if q is None:
                q = self._queues[topic] = EventQueue(maxsize)
            return q

    # -- publishing ---------------------------------------------------------

    def publish_latest(self, topic: str, msg: Any) -> None:
        self.cell(topic).set(msg)
        tap = self._tap
        if tap is not None:
            tap(topic, msg)

    def publish_event(self, topic: str, msg: Any) -> None:
        self.events(topic).put(msg)
        tap = self._tap
        if tap is not None:
            tap(topic, msg)

    # -- tap ----------------------------------------------------------------

    def set_tap(self, tap: Callable[[str, Any], None] | None) -> None:
        """tap(topic, msg) is called on every publish; it must not block."""
        self._tap = tap
