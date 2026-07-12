"""Flight identity and log directory layout.

    logs/<flight_id>/
        params.json     exact ParamSet snapshot (reproducibility)
        flight.jsonl    every bus message (written by TelemetryLogger)
        result.json     FlightResult verdict
        frames/         optional decimated JPEGs

flight_id = <utc timestamp>-<params hash8>.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from aigp.core.params import ParamSet


def new_flight_id(params: ParamSet) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"{stamp}-{params.hash8}"


def prepare_flight_dir(log_root: str | Path, flight_id: str, params: ParamSet) -> Path:
    flight_dir = Path(log_root) / flight_id
    flight_dir.mkdir(parents=True, exist_ok=True)
    params.save(flight_dir / "params.json")
    return flight_dir


def write_result(flight_dir: str | Path, result: dict) -> None:
    with open(Path(flight_dir) / "result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)


def iter_log(flight_dir: str | Path) -> Iterator[dict]:
    with open(Path(flight_dir) / "flight.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            yield json.loads(line)


def read_result(flight_dir: str | Path) -> dict:
    with open(Path(flight_dir) / "result.json", "r", encoding="utf-8") as f:
        return json.load(f)
