"""Challenge 7, part 2. Your paired bootstrap is compared with evalkit.stats within 0.005; the verdict class must match."""
import importlib.util
import re
from pathlib import Path

from evalkit import stats
from evalkit.casegrades import triage_trials

HERE = Path(__file__).resolve().parent
TOL = 0.005
PLACEHOLDER = "(fill in)"


def learner():
    spec = importlib.util.spec_from_file_location("learner_decide", HERE / "decide.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_diffs_are_per_case():
    m = learner()
    a = {"c1": [1, 1, 0, 1, 1], "c2": [0, 0, 0, 0, 0], "c3": [1, 1, 1, 1, 1], "only_a": [1, 1, 1, 1, 1]}
    b = {"c1": [1, 1, 1, 1, 1], "c2": [1, 0, 0, 0, 0], "c3": [1, 1, 0, 0, 1], "only_b": [0, 0, 0, 0, 0]}
    d = m.case_differences(a, b)
    assert len(d) == 3, "one number per case that is in both runs"
    assert [round(x, 4) for x in d] == [0.2, 0.2, -0.4], "B's mean minus A's mean, in case id order"
    ta, tb = triage_trials("A"), triage_trials("B")
    diffs = m.case_differences(ta, tb)
    assert len(diffs) == 160
    assert abs(sum(diffs) / 160 - (sum(sum(g) / 5 for g in tb.values()) - sum(sum(g) / 5 for g in ta.values())) / 160) < 1e-9


def test_paired_bootstrap_matches_within_tolerance():
    m = learner()
    diffs = m.case_differences(triage_trials("A"), triage_trials("B"))
    mean, (lo, hi) = m.paired_bootstrap(diffs)
    rmean, (rlo, rhi) = stats.paired_bootstrap(diffs)
    assert abs(mean - rmean) <= TOL and abs(lo - rlo) <= TOL and abs(hi - rhi) <= TOL, f"({lo:.4f}, {hi:.4f}) against ({rlo:.4f}, {rhi:.4f})"
    assert m.verdict(lo, hi) == stats.verdict((rlo, rhi)), "the verdict class must match"


def test_verdict_rule():
    m = learner()
    assert m.verdict(0.01, 0.09) == "better"
    assert m.verdict(-0.09, -0.01) == "worse"
    assert m.verdict(-0.004, 0.049) == "not proven"
    assert m.verdict(0.0, 0.05) == "not proven", "an interval that starts at zero is not proven"
    assert m.verdict(-0.05, 0.0) == "not proven"
    assert m.verdict(-0.02, 0.02) == "not proven"


def test_sign_test_known_split():
    m = learner()
    assert abs(m.sign_test(9, 3) - 0.146) <= TOL
    assert abs(m.sign_test(6, 0) - 0.031) <= TOL
    assert abs(m.sign_test(3, 9) - 0.146) <= TOL, "the test is two-sided"
    assert m.sign_test(0, 0) == 1.0
    assert m.sign_test(5, 5) == 1.0
    assert abs(m.sign_test(15, 10) - stats.sign_test(15, 10)) <= TOL


def test_results_written():
    body = (HERE / "results.md").read_text(encoding="utf-8")
    assert PLACEHOLDER not in body, "results.md still has '(fill in)'"
    diffs = stats.paired_bootstrap([stats.mean(triage_trials("B")[c]) - stats.mean(triage_trials("A")[c]) for c in sorted(triage_trials("A"))])
    mean, (lo, hi) = diffs
    m = re.search(r"^Paired difference: ([+-][\d.]+) points, interval \(([+-][\d.]+), ([+-][\d.]+)\), verdict: (.+)$", body, flags=re.M)
    assert m, "write the line 'Paired difference: +3.8 points, interval (-1.5, +9.1), verdict: not proven'"
    assert abs(float(m.group(1)) - 100 * mean) <= 0.5 and abs(float(m.group(2)) - 100 * lo) <= 0.5 and abs(float(m.group(3)) - 100 * hi) <= 0.5
    assert m.group(4).strip() == stats.verdict((lo, hi))
    assert re.search(r"^B is .+ than A on triage: .+ cases, five trials\.$", body, flags=re.M), "write the one sentence"
