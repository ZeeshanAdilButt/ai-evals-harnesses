"""Challenge 7, part 1. Each test compares your function with evalkit.stats within 0.005 (a half point), not to four decimals."""
import importlib.util
import random
import re
from pathlib import Path

from evalkit import stats
from evalkit.casegrades import triage_trials

HERE = Path(__file__).resolve().parent
TOL = 0.005
PLACEHOLDER = "(fill in)"


def learner():
    spec = importlib.util.spec_from_file_location("learner_intervals", HERE / "intervals.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def close(a, b):
    return abs(a - b) <= TOL


def score_sets():
    sets = [stats.case_means(list(triage_trials(v).values())) for v in "AB"]
    rng = random.Random(3)
    sets.append([rng.choice([0.0, 0.2, 0.6, 1.0]) for _ in range(37)])
    return sets


def test_se_matches_evalkit_stats():
    m = learner()
    for scores in score_sets():
        p, se, (lo, hi) = m.se_interval(scores)
        rp, rse, (rlo, rhi) = stats.se_interval(scores)
        assert close(p, rp) and close(se, rse), f"p {p:.4f} se {se:.4f}; reference p {rp:.4f} se {rse:.4f}"
        assert close(lo, rlo) and close(hi, rhi)
        assert 0.0 <= lo <= p <= hi <= 1.0


def test_bootstrap_matches_within_tolerance():
    m = learner()
    for scores in score_sets():
        lo, hi = m.bootstrap_interval(scores)
        rlo, rhi = stats.bootstrap(scores)
        assert close(lo, rlo) and close(hi, rhi), f"({lo:.4f}, {hi:.4f}) against ({rlo:.4f}, {rhi:.4f})"


def test_rate_interval_edges_return_pairs():
    m = learner()
    lo, hi = m.rate_interval(41, 41)
    assert close(lo, 1 - 3 / 41) and hi == 1.0, "41 of 41 gives (1 - 3/41, 1), about (0.927, 1)"
    lo, hi = m.rate_interval(0, 12)
    assert lo == 0.0 and close(hi, 0.25), "0 of 12 gives (0, 0.25)"
    for s, n in ((30, 41), (5, 12), (39, 41)):
        got = m.rate_interval(s, n)
        assert isinstance(got, tuple) and len(got) == 2, "return a pair (low, high), never one number"
        ref = stats.rate_interval(s, n)
        assert close(got[0], ref[0]) and close(got[1], ref[1]), f"{s} of {n}: {got} against {ref}"
        assert got[0] < s / n < got[1]


def test_unit_is_case_not_grade():
    m = learner()
    trials = triage_trials("A")
    right = m.run_interval(trials)
    wrong = m.wrong_unit_interval(trials)
    ref = stats.se_interval(stats.case_means(list(trials.values())))
    assert close(right[1], ref[1]), "run_interval must use one score per case"
    assert wrong[1] < right[1], "grades as cases give a smaller SE"
    assert 1.8 < right[1] / wrong[1] < 2.5, "five correlated trials make the grade-level SE about sqrt(5) = 2.24 times too small"


def test_results_written():
    body = (HERE / "results.md").read_text(encoding="utf-8")
    assert PLACEHOLDER not in body, "results.md still has '(fill in)'"
    for v in "AB":
        trials = triage_trials(v)
        p, se, (lo, hi) = stats.se_interval(stats.case_means(list(trials.values())))
        blo, bhi = stats.bootstrap(stats.case_means(list(trials.values())))
        row = re.search(rf"^\| {v} \| (\d+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \|$", body, flags=re.M)
        assert row, f"results.md needs a table row for {v}: | {v} | cases | pass % | SE | lo | hi | boot lo | boot hi |"
        got = [float(x) for x in row.groups()[1:]]
        want = [100 * p, 100 * se, 100 * lo, 100 * hi, 100 * blo, 100 * bhi]
        assert all(abs(g - w) <= 0.5 for g, w in zip(got, want)), f"{v}: your table differs from the reference {[round(x, 1) for x in want]}"
    assert "41 of 41" in body and "0 of 12" in body
