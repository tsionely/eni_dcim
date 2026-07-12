"""Flight-to-flight tuning campaign.

The loop that makes the pilot improve between flights:

    params = base.patch(optimizer.ask())
    reset sim -> fly -> score -> optimizer.tell() -> record in DB

`fly_fn(params) -> result dict` abstracts the actual flight so the campaign
runs identically against the mock sim (CI) and the real sim (the user's
Windows machine, via scripts/run_campaign.py).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from aigp.core.params import ParamSet
from aigp.learning.metrics import score_flight
from aigp.learning.optimizers import Optimizer
from aigp.learning.results_db import ResultsDB


class Campaign:
    def __init__(self, campaign_id: str, base_params: ParamSet,
                 optimizer: Optimizer, db: ResultsDB,
                 fly_fn: Callable[[ParamSet], dict],
                 log_fn: Callable[[str], None] = print) -> None:
        self.campaign_id = campaign_id
        self.base_params = base_params
        self.optimizer = optimizer
        self.db = db
        self.fly_fn = fly_fn
        self.log = log_fn

    def run(self, n_flights: int) -> tuple[dict[str, float], float] | None:
        self.db.record_campaign(
            self.campaign_id,
            type(self.optimizer).__name__,
            self.optimizer.keys,
            datetime.now(timezone.utc).isoformat(),
        )
        for i in range(n_flights):
            overrides = self.optimizer.ask()
            params = self.base_params.patch(overrides)
            started_at = datetime.now(timezone.utc).isoformat()

            result = self.fly_fn(params)

            score = score_flight(result, params)
            self.optimizer.tell(overrides, score)
            flight_id = result.get("flight_id", f"{self.campaign_id}-{i:04d}")
            self.db.record_flight(flight_id, started_at, params, result, score,
                                  campaign_id=self.campaign_id)
            self.log(
                f"[campaign {self.campaign_id}] flight {i + 1}/{n_flights} "
                f"score={score:.1f} gates={result.get('gates_passed', 0)} "
                f"aborted={result.get('aborted')} params={overrides}"
            )
        best = self.optimizer.best
        if best is not None:
            self.log(f"[campaign {self.campaign_id}] best score={best[1]:.1f} params={best[0]}")
        return best
