"""Challenge 11, part 2. One test per checkpoint. They fail on the starter (report.md is the empty template). No model is called.
The report is your own writing; the tests check structure and that every figure equals your 11.2 results (summary.json) and your 5.8 test report."""
import importlib.util
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def checker():
    spec = importlib.util.spec_from_file_location("check_report_mod", HERE / "check_report.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def report():
    return (HERE / "report.md").read_text(encoding="utf-8")


def section(prefix, text=None):
    text = report() if text is None else text
    for p in re.split(r"^## ", text, flags=re.M):
        if p.startswith(prefix):
            return p
    raise AssertionError(f"report.md has no section '## {prefix}...'")


def sub(prefix):
    for p in re.split(r"^### ", section("3."), flags=re.M):
        if p.startswith(prefix):
            return p
    raise AssertionError(f"section 3 has no '### {prefix}'")


def test_checkpoint_1():
    c = checker()
    summary, judge_test = c.load_inputs()
    text = report()
    assert "(fill in" not in section("2.") and "(fill in" not in section("3.") and "(fill in" not in section("4.") and "(fill in" not in section("5.")
    for n in ("1.", "2.", "3.", "4.", "5."):
        section(n)
    problems = c.compare(c.numbers_block(text), c.expected(summary, judge_test), c.SECTIONS_2_TO_5)
    assert not problems, problems
    for name, key in (("3.1", "triage"), ("3.2", "reply")):
        body = sub(name)
        d = summary[key]
        assert "95% interval" in body, f"{name}: a claim about {key} needs the paired difference with its 95% interval"
        pair = re.search(r"\(([+-]?\d+\.\d)(?: to |, )([+-]?\d+\.\d)\)", body)
        assert pair, f"{name}: write the interval as (low, high) in points"
        assert abs(float(pair.group(1)) - 100 * d["lo"]) <= 0.15 and abs(float(pair.group(2)) - 100 * d["hi"]) <= 0.15
        assert re.search(r"better|worse|not proven", body), f"{name}: say better, worse or not proven"
    agent = sub("3.3")
    assert "40 tasks, 5 trials" in agent and "pass^1" in agent and "pass^4" in agent
    assert "interval" not in agent.lower(), "the agent lines give pass^k with the counts and no interval"
    must = section("5.")
    for row in summary["mustpass"]["cases"]:
        assert re.search(rf"^\| {row['case']} \| {row['A']} of 5 \| {row['candidate']} of 5 \|", must, flags=re.M), f"must-pass table: {row['case']} with five trials for A and the candidate"
    slices = section("4.")
    for r in summary["reply_slices"]:
        assert r["slice"] in slices, f"the slice table lists {r['slice']}"


def test_checkpoint_2():
    test_checkpoint_1()
    c = checker()
    summary, judge_test = c.load_inputs()
    assert judge_test, "run `python -m evalkit judge-eval --split test` (5.8) so that the judge section has counts"
    problems = c.compare(c.numbers_block(report()), c.expected(summary, judge_test), c.SECTIONS_6_TO_7)
    assert not problems, problems
    judge = section("6.")
    for k, label in (("tp", "TP"), ("fn", "FN"), ("tn", "TN"), ("fp", "FP")):
        assert re.search(rf"\b{label} {judge_test[k]}\b", judge), f"section 6: the test counts need '{label} {judge_test[k]}'"
    assert "fail is the positive class" in judge.lower() and judge_test["judge"] in judge
    cost = section("7.")
    budget = summary["cost"]
    assert str(budget["budget_p95_ms"]) in cost and f"{budget['budget_cost_per_1k']:g}" in cost, "section 7 compares cost and p95 with the budget"
    assert re.search(r"inside|over", cost)


def test_checkpoint_3():
    test_checkpoint_2()
    text = report()
    for n in ("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9."):
        body = section(n, text)
        assert "(fill in" not in body, f"section {n} still has a placeholder"
    limits = section("8.")
    assert re.search(r"^- Limit", limits, flags=re.M | re.I) and re.search(r"^- Next", limits, flags=re.M | re.I), "section 8: at least one limit and one next step"
    decision = re.search(r"^Decision: (.+)$", section("1."), flags=re.M)
    assert decision, "section 1 starts with a line 'Decision: ...'"
    assert re.search(r"\bship\b|\bno-ship\b", decision.group(1), flags=re.I)
    assert len(re.findall(r"[.!?](?:\s|$)", decision.group(1))) == 1, "the decision line is one sentence"
