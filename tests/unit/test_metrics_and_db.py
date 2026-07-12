from aigp.core.params import ParamSet
from aigp.learning.metrics import score_flight
from aigp.learning.results_db import ResultsDB


def params():
    return ParamSet.load("config/params_default.json")


def test_more_gates_beats_faster_lap():
    p = params()
    slow_full = {"finished": True, "gates_passed": 5, "lap_time_s": 60.0,
                 "gate_clips": 0, "env_hits": 0, "aborted": False}
    fast_partial = {"finished": False, "gates_passed": 3, "lap_time_s": None,
                    "gate_clips": 0, "env_hits": 0, "aborted": False,
                    "duration_s": 20.0}
    assert score_flight(slow_full, p) > score_flight(fast_partial, p)


def test_faster_lap_wins_at_equal_gates():
    p = params()
    base = {"finished": True, "gates_passed": 5, "gate_clips": 0,
            "env_hits": 0, "aborted": False}
    fast = dict(base, lap_time_s=30.0)
    slow = dict(base, lap_time_s=45.0)
    assert score_flight(fast, p) > score_flight(slow, p)


def test_crashes_and_aborts_penalized():
    p = params()
    clean = {"finished": True, "gates_passed": 5, "lap_time_s": 30.0,
             "gate_clips": 0, "env_hits": 0, "aborted": False}
    crashy = dict(clean, gate_clips=3)
    aborted = dict(clean, aborted=True)
    assert score_flight(clean, p) > score_flight(crashy, p)
    assert score_flight(clean, p) > score_flight(aborted, p)


def test_results_db_roundtrip(tmp_path):
    db = ResultsDB(tmp_path / "results.sqlite")
    p = params()
    db.record_campaign("c1", "CEM", ["planner.commit.distance_m"], "2026-01-01")
    result = {"finished": True, "gates_passed": 5, "lap_time_s": 33.0,
              "gate_clips": 1, "env_hits": 0, "aborted": False, "abort_reason": ""}
    db.record_flight("f1", "2026-01-01", p, result, score=467.0, campaign_id="c1")
    db.record_flight("f2", "2026-01-02", p.patch({"planner.commit.distance_m": 3.0}),
                     dict(result, lap_time_s=30.0), score=470.0, campaign_id="c1")

    best = db.best_flight("c1")
    assert best["flight_id"] == "f2"
    assert best["score"] == 470.0
    flights = db.flights("c1")
    assert [f["flight_id"] for f in flights] == ["f1", "f2"]
    assert flights[0]["param_hash"] == p.hash
    db.close()
