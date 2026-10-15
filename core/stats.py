"""Bootstrap intervals; paired tests are added in Phase 2."""
import numpy as np


def bootstrap_ci(correct, n_resamples: int = 10_000, seed: int = 0, alpha: float = 0.05):
    x = np.asarray(correct, dtype=float)
    rng = np.random.default_rng(seed)
    means = x[rng.integers(0, len(x), size=(n_resamples, len(x)))].mean(axis=1)
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return float(x.mean()), float(lo), float(hi)
