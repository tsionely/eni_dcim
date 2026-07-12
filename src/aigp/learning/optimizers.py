"""numpy-only black-box optimizers for flight-to-flight tuning.

The Optimizer ABC (ask/tell) is also the future RL hook: a policy-learning
component would consume the same per-flight (params, score) records.

All optimizers work on a dict of dot-keys with (low, high) bounds and
maximize the score.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

Bounds = dict[str, tuple[float, float]]


class Optimizer(ABC):
    def __init__(self, bounds: Bounds, seed: int = 0) -> None:
        self.bounds = dict(bounds)
        self.keys = list(bounds.keys())
        self.lo = np.array([bounds[k][0] for k in self.keys])
        self.hi = np.array([bounds[k][1] for k in self.keys])
        self.rng = np.random.default_rng(seed)
        self.history: list[tuple[dict[str, float], float]] = []

    @abstractmethod
    def ask(self) -> dict[str, float]:
        """Propose the next parameter values to fly."""

    def tell(self, params: dict[str, float], score: float) -> None:
        self.history.append((dict(params), score))
        self._tell(np.array([params[k] for k in self.keys]), score)

    def _tell(self, x: np.ndarray, score: float) -> None:
        pass

    @property
    def best(self) -> tuple[dict[str, float], float] | None:
        if not self.history:
            return None
        return max(self.history, key=lambda h: h[1])

    def _clip(self, x: np.ndarray) -> np.ndarray:
        return np.clip(x, self.lo, self.hi)

    def _to_dict(self, x: np.ndarray) -> dict[str, float]:
        return {k: float(v) for k, v in zip(self.keys, x)}


class RandomSearch(Optimizer):
    """Uniform sampling inside the bounds. The baseline everything must beat."""

    def ask(self) -> dict[str, float]:
        x = self.rng.uniform(self.lo, self.hi)
        return self._to_dict(x)


class CEM(Optimizer):
    """Cross-entropy method: sample a Gaussian, refit it to the elite set."""

    def __init__(self, bounds: Bounds, seed: int = 0, population: int = 8,
                 elite_frac: float = 0.3, min_std_frac: float = 0.05) -> None:
        super().__init__(bounds, seed)
        self.population = population
        self.n_elite = max(1, int(round(population * elite_frac)))
        self.mean = (self.lo + self.hi) / 2.0
        self.std = (self.hi - self.lo) / 4.0
        self.min_std = (self.hi - self.lo) * min_std_frac
        self._batch: list[tuple[np.ndarray, float]] = []

    def ask(self) -> dict[str, float]:
        x = self._clip(self.rng.normal(self.mean, self.std))
        return self._to_dict(x)

    def _tell(self, x: np.ndarray, score: float) -> None:
        self._batch.append((x, score))
        if len(self._batch) < self.population:
            return
        self._batch.sort(key=lambda b: b[1], reverse=True)
        elite = np.stack([x for x, _ in self._batch[: self.n_elite]])
        self.mean = elite.mean(axis=0)
        self.std = np.maximum(elite.std(axis=0), self.min_std)
        self._batch = []


class CMAES(Optimizer):
    """Compact (mu/mu_w, lambda) CMA-ES. Enough for the ~10-dim tuning
    problems here; swap in a library implementation if dimensionality grows."""

    def __init__(self, bounds: Bounds, seed: int = 0, population: int | None = None,
                 sigma0_frac: float = 0.25) -> None:
        super().__init__(bounds, seed)
        n = len(self.keys)
        self.n = n
        self.lam = population or (4 + int(3 * np.log(n)))
        self.mu = self.lam // 2
        weights = np.log(self.mu + 0.5) - np.log(np.arange(1, self.mu + 1))
        self.weights = weights / weights.sum()
        self.mu_eff = 1.0 / np.sum(self.weights ** 2)

        # Strategy parameters (standard Hansen defaults).
        self.cc = (4 + self.mu_eff / n) / (n + 4 + 2 * self.mu_eff / n)
        self.cs = (self.mu_eff + 2) / (n + self.mu_eff + 5)
        self.c1 = 2 / ((n + 1.3) ** 2 + self.mu_eff)
        self.cmu = min(1 - self.c1,
                       2 * (self.mu_eff - 2 + 1 / self.mu_eff) / ((n + 2) ** 2 + self.mu_eff))
        self.damps = 1 + 2 * max(0.0, np.sqrt((self.mu_eff - 1) / (n + 1)) - 1) + self.cs
        self.chi_n = np.sqrt(n) * (1 - 1 / (4 * n) + 1 / (21 * n ** 2))

        # Dynamic state. Internally normalized: search space is [0, 1]^n.
        self.mean = np.full(n, 0.5)
        self.sigma = sigma0_frac
        self.pc = np.zeros(n)
        self.ps = np.zeros(n)
        self.C = np.eye(n)
        self._batch: list[tuple[np.ndarray, float]] = []
        self._gen = 0

    def _decode(self, z: np.ndarray) -> np.ndarray:
        return self._clip(self.lo + z * (self.hi - self.lo))

    def _encode(self, x: np.ndarray) -> np.ndarray:
        return (x - self.lo) / np.where(self.hi > self.lo, self.hi - self.lo, 1.0)

    def ask(self) -> dict[str, float]:
        z = self.rng.multivariate_normal(self.mean, (self.sigma ** 2) * self.C)
        z = np.clip(z, 0.0, 1.0)
        return self._to_dict(self._decode(z))

    def _tell(self, x: np.ndarray, score: float) -> None:
        self._batch.append((self._encode(x), score))
        if len(self._batch) < self.lam:
            return
        self._batch.sort(key=lambda b: b[1], reverse=True)
        selected = np.stack([z for z, _ in self._batch[: self.mu]])
        old_mean = self.mean.copy()
        self.mean = self.weights @ selected

        try:
            inv_sqrt_c = np.linalg.inv(np.linalg.cholesky(self.C)).T
        except np.linalg.LinAlgError:
            self.C = np.eye(self.n)
            inv_sqrt_c = np.eye(self.n)

        y = (self.mean - old_mean) / max(self.sigma, 1e-12)
        self.ps = (1 - self.cs) * self.ps + np.sqrt(
            self.cs * (2 - self.cs) * self.mu_eff) * (inv_sqrt_c @ y)
        self._gen += 1
        hsig = (np.linalg.norm(self.ps)
                / np.sqrt(1 - (1 - self.cs) ** (2 * self._gen)) / self.chi_n) < (
                    1.4 + 2 / (self.n + 1))
        self.pc = (1 - self.cc) * self.pc + hsig * np.sqrt(
            self.cc * (2 - self.cc) * self.mu_eff) * y

        artmp = (selected - old_mean) / max(self.sigma, 1e-12)
        self.C = ((1 - self.c1 - self.cmu) * self.C
                  + self.c1 * (np.outer(self.pc, self.pc)
                               + (not hsig) * self.cc * (2 - self.cc) * self.C)
                  + self.cmu * (artmp.T @ np.diag(self.weights) @ artmp))
        self.sigma *= float(np.exp((self.cs / self.damps)
                                   * (np.linalg.norm(self.ps) / self.chi_n - 1)))
        self.sigma = float(np.clip(self.sigma, 1e-4, 1.0))
        self._batch = []


OPTIMIZERS = {
    "random": RandomSearch,
    "cem": CEM,
    "cmaes": CMAES,
}
