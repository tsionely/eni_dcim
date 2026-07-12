import numpy as np
import pytest

from aigp.learning.optimizers import CEM, CMAES, RandomSearch

BOUNDS = {"a": (-5.0, 5.0), "b": (-5.0, 5.0)}


def sphere_score(params):
    # Maximum 0 at (1, -2).
    return -((params["a"] - 1.0) ** 2 + (params["b"] + 2.0) ** 2)


@pytest.mark.parametrize("cls,budget,tol", [
    (RandomSearch, 300, 1.0),
    (CEM, 200, 0.3),
    (CMAES, 200, 0.3),
])
def test_optimizers_improve_on_sphere(cls, budget, tol):
    opt = cls(BOUNDS, seed=1)
    for _ in range(budget):
        x = opt.ask()
        assert set(x) == {"a", "b"}
        assert BOUNDS["a"][0] <= x["a"] <= BOUNDS["a"][1]
        opt.tell(x, sphere_score(x))
    best_params, best_score = opt.best
    assert best_score > -tol
    assert abs(best_params["a"] - 1.0) < 1.5
    assert abs(best_params["b"] + 2.0) < 1.5


def test_ask_respects_bounds_always():
    opt = CEM(BOUNDS, seed=0)
    for _ in range(100):
        x = opt.ask()
        assert -5.0 <= x["a"] <= 5.0 and -5.0 <= x["b"] <= 5.0
        opt.tell(x, 0.0)


def test_history_and_best():
    opt = RandomSearch(BOUNDS, seed=0)
    scores = []
    for _ in range(10):
        x = opt.ask()
        s = sphere_score(x)
        scores.append(s)
        opt.tell(x, s)
    assert opt.best[1] == max(scores)
    assert len(opt.history) == 10
