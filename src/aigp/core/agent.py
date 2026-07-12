"""Base class for threaded agents (IO, perception, telemetry writer).

The template inverted thread shutdown (get_thread_for_join flipped a flag and
returned the thread). Here every agent has an explicit lifecycle:

    agent.start()
    ...
    agent.stop(timeout=1.0)

Subclasses implement _run() and are expected to poll self.should_run()
frequently (all sockets use short timeouts so stop() converges quickly).
"""
from __future__ import annotations

import threading


class Agent:
    name = "agent"

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self.error: BaseException | None = None

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError(f"{self.name} already started")
        self._stop.clear()
        self._thread = threading.Thread(target=self._guarded_run, name=self.name, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None

    def should_run(self) -> bool:
        return not self._stop.is_set()

    @property
    def alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def healthy(self) -> bool:
        return self.error is None and (self._thread is None or self.alive)

    def _guarded_run(self) -> None:
        try:
            self._run()
        except BaseException as exc:  # surfaced via healthy() / watchdog
            self.error = exc

    def _run(self) -> None:
        raise NotImplementedError
