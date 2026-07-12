"""Flight scoring.

The objective the tuner maximizes. Deliberately lexicographic-by-weighting:
with gate_weight >> typical lap times, early campaigns optimize completion
(pass more gates) and only then shave lap time. Collisions and aborts are
penalized so the optimizer cannot buy speed with crashes.
"""
from __future__ import annotations

from aigp.core.params import ParamSet


def score_flight(result: dict, params: ParamSet) -> float:
    gate_weight = float(params.get("learning.score.gate_weight"))
    collision_penalty = float(params.get("learning.score.collision_penalty"))
    abort_penalty = float(params.get("learning.score.abort_penalty"))

    score = result.get("gates_passed", 0) * gate_weight
    lap_time = result.get("lap_time_s")
    if result.get("finished") and lap_time is not None:
        score -= lap_time
    else:
        # Unfinished flights: duration is a weak time signal so that among
        # equally-progressed flights, faster progress scores higher.
        score -= result.get("duration_s", 0.0) * 0.1
    score -= (result.get("gate_clips", 0) + result.get("env_hits", 0)) * collision_penalty
    if result.get("aborted"):
        score -= abort_penalty
    return score
