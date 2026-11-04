"""Shipped statistics (seeded, so results are byte-stable). The case is the unit."""
from __future__ import annotations

import math
import random
from math import comb


def mean(xs):
    return sum(xs) / len(xs)


def sample_sd(xs):
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def se_interval(case_scores, z=1.96):
    """Standard error of the mean of per-case scores, s / sqrt(n), and the normal interval."""
    n = len(case_scores)
    m = mean(case_scores)
    se = sample_sd(case_scores) / math.sqrt(n)
    return m, se, (max(0.0, m - z * se), min(1.0, m + z * se))


def percentile(sorted_xs, q):
    """Nearest rank: the value at rank ceil(q * n)."""
    k = max(1, math.ceil(q * len(sorted_xs)))
    return sorted_xs[k - 1]


def resample_stats(values, statistic, b=10000, seed=7):
    """The shipped resampling loop (7.4): draw n values with replacement, apply `statistic`, repeat b times.
    Returns the sorted statistics. The unit passed in is the unit resampled, so pass one value per case."""
    rng = random.Random(seed)
    n = len(values)
    return sorted(statistic([values[rng.randrange(n)] for _ in range(n)]) for _ in range(b))


def case_means(trials):
    """One score per case: the mean of its trials. `trials` is a list of per-trial lists, one list per case."""
    return [mean(t) for t in trials]


def bootstrap(case_scores, b=10000, seed=7, stat=mean):
    vals = resample_stats(case_scores, stat, b=b, seed=seed)
    return percentile(vals, 0.025), percentile(vals, 0.975)


def rate_interval(successes, n):
    """Interval for a rate such as a judge's TPR or TNR: a pair (low, high). The bootstrap of the n verdicts, or
    the rule of three at the edges: (1 - 3/n, 1) when successes = n, (0, 3/n) when successes = 0."""
    if successes >= n:
        return (1 - 3 / n, 1.0)
    if successes <= 0:
        return (0.0, 3 / n)
    return bootstrap([1.0] * successes + [0.0] * (n - successes))


def rule_of_three(n):
    return 3 / n


def paired_bootstrap(diffs, b=10000, seed=7):
    """diffs: per-case score of B minus A. Returns the mean and the 95% interval."""
    lo, hi = bootstrap(diffs, b=b, seed=seed)
    return mean(diffs), (lo, hi)


def verdict(interval):
    lo, hi = interval
    return "better" if lo > 0 else "worse" if hi < 0 else "not proven"


def sign_test(x, y):
    """Exact two-sided binomial test on x flips one way and y the other."""
    m = x + y
    if m == 0:
        return 1.0
    k = min(x, y)
    return min(1.0, 2 * sum(comb(m, i) for i in range(k + 1)) / 2 ** m)


def pass_hat_k(c, n, k):
    """pass^k for one task from c passes in n trials: comb(c, k) / comb(n, k)."""
    return comb(c, k) / comb(n, k)
