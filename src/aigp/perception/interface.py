"""Pluggable gate detector interface.

Round 1 (high-contrast desaturated environment) is served by the classical
detector in gate_detector_hsv.py. Round 2 (visually complex 3D-scanned
environments) plugs in behind the same ABC — e.g. a learned detector — without
touching planner or estimator code.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from aigp.core.messages import CameraFrame, GateDetection


class GateDetector(ABC):
    @abstractmethod
    def detect(self, frame: CameraFrame) -> GateDetection | None:
        """Return the best gate detection in the frame, or None."""
