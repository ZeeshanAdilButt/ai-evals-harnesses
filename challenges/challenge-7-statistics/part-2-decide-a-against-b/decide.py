"""Challenge 7, part 2: decide whether B is better than A, and say why in one sentence.

Shipped and read, not written: triage_trials(variant), case_means, resample_stats, percentile (the seeded loop from part 1).
Fill the four YOUR TURN gaps:
  1. case_differences(a_trials, b_trials)    per-case difference: B's five-trial mean minus A's
  2. paired_bootstrap(diffs)                 (mean, (low, high)) of the differences, 10,000 resamples of cases, seed 7
  3. verdict(lo, hi)                         "better", "worse" or "not proven"
  4. sign_test(x, y)                         exact two-sided p for x flips one way and y the other

Run it:  python challenges/challenge-7-statistics/part-2-decide-a-against-b/decide.py
"""
from __future__ import annotations

import sys
from math import comb
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from evalkit import stats  # noqa: E402
from evalkit.casegrades import triage_trials  # noqa: E402,F401  (shipped)
from evalkit.stats import case_means, percentile, resample_stats  # noqa: E402,F401  (shipped)


def case_differences(a_trials, b_trials):
    """`a_trials` and `b_trials` are {case id: [grades]} (five trials per case). Return a list with one number per case that is in
    both, in case id order: the mean of B's grades minus the mean of A's. A positive number means B did better on that case."""
    raise NotImplementedError("YOUR TURN: for each id in sorted(set(a) & set(b)): mean(b[id]) - mean(a[id])")


def paired_bootstrap(diffs):
    """Resample the per-case differences (cases, not grades) with the shipped resample_stats and the mean as the statistic.
    Return (mean of diffs, (2.5th percentile, 97.5th percentile))."""
    raise NotImplementedError("YOUR TURN: vals = resample_stats(diffs, mean); the interval is percentile(vals, 0.025) and percentile(vals, 0.975)")


def verdict(lo, hi):
    """The rule: "better" if the whole interval is above zero (lo > 0), "worse" if the whole interval is below zero (hi < 0),
    otherwise "not proven". An interval that starts exactly at zero is not proven."""
    raise NotImplementedError("YOUR TURN: lo > 0 is better; hi < 0 is worse; anything else not proven")


def sign_test(x, y):
    """Exact two-sided sign test. Of the x + y cases that flipped, x flipped one way and y the other. If B were no different from A
    each flipped case would go either way with probability 1/2. Return the p value: twice the chance of min(x, y) or fewer in one
    direction among x + y fair coin flips, at most 1. No flips at all gives 1.0."""
    raise NotImplementedError("YOUR TURN: m = x + y; k = min(x, y); p = min(1, 2 * sum(comb(m, i) for i in range(k + 1)) / 2**m)")


def main():
    a, b = triage_trials("A"), triage_trials("B")
    diffs = case_differences(a, b)
    mean, (lo, hi) = paired_bootstrap(diffs)
    v = verdict(lo, hi)
    print(f"{len(diffs)} cases; mean difference B minus A {100 * mean:+.1f} points, 95% interval ({100 * lo:+.1f}, {100 * hi:+.1f}) -> {v}")
    ref_mean, ref_ci = stats.paired_bootstrap(diffs)
    print(f"evalkit stats paired: {100 * ref_mean:+.1f}, ({100 * ref_ci[0]:+.1f}, {100 * ref_ci[1]:+.1f}) -> {stats.verdict(ref_ci)}; verdict class "
          + ("matches" if stats.verdict(ref_ci) == v else "DIFFERS"))
    up = sum(1 for i in a if a[i][0] == 0 and b[i][0] == 1)
    down = sum(1 for i in a if a[i][0] == 1 and b[i][0] == 0)
    print(f"trial 1 alone: {up} flips to pass, {down} flips to fail, exact two-sided p = {sign_test(up, down):.3f}")
    word = "not proven better" if v == "not proven" else v
    print(f"B is {word} than A on triage: {100 * mean:+.1f} points, 95% interval [{100 * lo:+.1f}, {100 * hi:+.1f}], {len(diffs)} cases, five trials.")


if __name__ == "__main__":
    main()
