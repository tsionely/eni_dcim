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
    def detect(self, frame: CameraFrame,
               prior_range_m: float | None = None) -> GateDetection | None:
        """Return the best gate detection in the frame, or None.

        prior_range_m: the estimator's believed range to the LOCKED gate,
        when one exists. At terminal range the next gate shows through the
        near gate's opening (with the racing line threading it), and pure
        area/cyan scoring hands the frame to the WRONG gate — the F3
        autopsy: honest 1.8m fixes of the near gate lost the candidate
        contest to gate 2, the lock followed, and the drone clipped the
        near frame chasing the far center. Detectors may use the prior to
        prefer prediction-consistent candidates; None = acquisition mode.
        """
