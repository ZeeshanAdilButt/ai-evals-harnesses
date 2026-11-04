"""Challenge 7, part 1: put an interval on every score. The case is the unit.

Shipped and read, not written (evalkit/stats.py and evalkit/casegrades.py):
  triage_trials(variant)               {case id: [five grades]} for canonical v1, from the recordings
  case_means(trials)                   one score per case: the mean of its trials
  sample_sd(values)                    the sample standard deviation (n - 1)
  resample_stats(values, statistic)    the seeded loop: 10,000 resamples of the values, seed 7, returns the sorted statistics
  percentile(sorted_values, q)         nearest rank

One worked interval is given: normal_interval. Fill the three YOUR TURN gaps:
  1. se_interval(case_scores)          p, SE = s / sqrt(n), and p plus or minus 1.96 SE (clipped to 0 and 1)
  2. bootstrap_interval(case_scores)   the 2.5th and 97.5th percentiles of the resampled means
  3. rate_interval(successes, n)       a pair (low, high) for a judge's TPR or TNR, with the rule of three at the edges

Run it:  python challenges/challenge-7-statistics/part-1-intervals/intervals.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from evalkit.casegrades import triage_trials  # noqa: E402,F401  (shipped)
from evalkit.stats import case_means, percentile, resample_stats, sample_sd  # noqa: E402,F401  (shipped)


def normal_interval(p, se, z=1.96):
    """The worked interval (given): p plus or minus z standard errors, clipped to 0 and 1. A score cannot leave [0, 1], so the
    clip is a note to the reader, not a correction of the maths."""
    return max(0.0, p - z * se), min(1.0, p + z * se)


def se_interval(case_scores):
    """`case_scores` holds one number per case (its five-trial mean). Return (p, se, (low, high)):
    p the mean, se = sample_sd(case_scores) / sqrt(n), and the interval from normal_interval(p, se)."""
    raise NotImplementedError("YOUR TURN: p = mean; se = sample_sd(case_scores) / sqrt(n); interval = normal_interval(p, se)")


def bootstrap_interval(case_scores):
    """The 95% bootstrap interval of the mean of `case_scores`: (low, high). Resample the cases (not the grades) with the shipped
    resample_stats, passing the statistic you want, and read the 2.5th and 97.5th percentiles with the shipped percentile."""
    raise NotImplementedError("YOUR TURN: the statistic is the mean; call resample_stats(case_scores, mean); percentile(vals, 0.025) and percentile(vals, 0.975)")


def rate_interval(successes, n):
    """A rate like a judge's TPR (expert fails the judge caught) or TNR: `successes` of `n`, one verdict per reply.
    Return a PAIR (low, high), never one number. Between the edges: the bootstrap interval of n verdicts (successes ones, the rest zeros).
    At the edges the bootstrap collapses to a point, which is not believable: with successes = n return (1 - 3/n, 1);
    with successes = 0 return (0, 3/n). That is the rule of three."""
    raise NotImplementedError("YOUR TURN: edges by the rule of three; otherwise bootstrap_interval of the list of ones and zeros")


def run_interval(trials_by_case):
    """The right unit (given): one score per case, then se_interval. `trials_by_case` is {case id: [grades]}."""
    return se_interval(case_means(list(trials_by_case.values())))


def wrong_unit_interval(trials_by_case):
    """The wrong unit (given, for comparison): every grade as if it were a case. 5 x n rows, an interval far too narrow."""
    return se_interval([g for grades in trials_by_case.values() for g in grades])


def main():
    for v in "AB":
        trials = triage_trials(v)
        scores = case_means(list(trials.values()))
        p, se, (lo, hi) = se_interval(scores)
        blo, bhi = bootstrap_interval(scores)
        print(f"{v}: {len(scores)} cases, pass {100 * p:.1f}%, SE {100 * se:.2f} points, interval ({100 * lo:.1f}, {100 * hi:.1f}), "
              f"bootstrap ({100 * blo:.1f}, {100 * bhi:.1f})")
        w = wrong_unit_interval(trials)
        print(f"   wrong unit (grades as cases): SE {100 * w[1]:.2f} points, interval ({100 * w[2][0]:.1f}, {100 * w[2][1]:.1f})")
    lo, hi = rate_interval(41, 41)
    print(f"41 of 41 expert fails caught: TPR 100%, interval ({100 * lo:.1f}, {100 * hi:.1f})")
    lo, hi = rate_interval(0, 12)
    print(f"0 of 12: interval ({100 * lo:.1f}, {100 * hi:.1f})")


if __name__ == "__main__":
    main()
