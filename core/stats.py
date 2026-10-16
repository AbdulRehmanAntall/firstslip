"""Bootstrap intervals and the paired tests of PREREGISTRATION.md §5."""
import numpy as np
from scipy.stats import binomtest


def bootstrap_ci(correct, n_resamples: int = 10_000, seed: int = 0, alpha: float = 0.05):
    x = np.asarray(correct, dtype=float)
    rng = np.random.default_rng(seed)
    means = x[rng.integers(0, len(x), size=(n_resamples, len(x)))].mean(axis=1)
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return float(x.mean()), float(lo), float(hi)


def paired_bootstrap_diff(a, b, n_resamples: int = 10_000, seed: int = 0, alpha: float = 0.05):
    """Mean of a − b on the same items, with a paired bootstrap CI."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    assert a.shape == b.shape
    return bootstrap_ci(a - b, n_resamples, seed, alpha)


def mcnemar(a, b) -> dict:
    """Exact McNemar test on paired 0/1 outcomes (two-sided binomial on discordant pairs)."""
    a, b = np.asarray(a, dtype=bool), np.asarray(b, dtype=bool)
    only_a, only_b = int((a & ~b).sum()), int((~a & b).sum())
    n = only_a + only_b
    p = 1.0 if n == 0 else float(binomtest(only_a, n, 0.5).pvalue)
    return {"only_a": only_a, "only_b": only_b, "p": p}


def holm(pvalues: list[float]) -> list[float]:
    """Holm–Bonferroni adjusted p-values, in the input order."""
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    adj, running = [0.0] * m, 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvalues[i]))
        adj[i] = running
    return adj
