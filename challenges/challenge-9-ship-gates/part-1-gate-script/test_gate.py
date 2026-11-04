"""Challenge 9, part 1. Fails on the starter (the checks raise NotImplementedError). Replay only: the runs are made from the recordings
with the shipped reference runner, so this test does not depend on your challenge 6 code."""
import importlib.util
import json
import re
import tomllib
from pathlib import Path

import pytest

from evalkit import engine, runner_reference, stats

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASELINE = "baselines/full-A"


def load(name):
    spec = importlib.util.spec_from_file_location(f"learner_{name}", HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    base = tmp_path_factory.mktemp("gate-runs")
    out = {}
    for variant in ("ci-regression", "ci-harmless"):
        engine.run_suite("full", variant, impl=runner_reference, out=base / variant)
        out[variant] = base / variant
    return out


def rec(feature, case, passes, must=False, **kw):
    base = {"feature": feature, "case_id": case, "status": "ok", "must_pass": must, "model": "claude-sonnet-5-5",
            "tokens_in": 400, "tokens_out": 200, "latency_ms": 1000, "latency_valid": True}
    base.update(kw)
    return [dict(base, trial=i + 1, passed=p) for i, p in enumerate(passes)]


def small_baseline():
    out = []
    for i in range(10):
        out += rec("reply", f"c{i}", [True] * 5)
    return out


CFG = {"floor": {"triage": 0.5, "reply": 0.5, "agent": 0.5}, "margin": {"triage": 0.2, "reply": 0.2, "agent": 0.2},
       "budget": {"cost_per_1k": 5.0, "p95_ms": 4000}}


def test_margins_were_initialised():
    gate = load("gate")
    cfg = gate.load_config()
    base = gate.load_records(BASELINE)
    want = {}
    q = gate.quarantined_cases(base)
    run = gate.Run(base, q)
    for f in gate.FEATURES:
        xs = [run.score(k) for k in sorted(run.cases) if k[0] == f and k not in q]
        lo, hi = stats.bootstrap(xs)
        want[f] = (hi - lo) / 2
    assert set(cfg["margin"]) == set(gate.FEATURES), "run `python -m evalkit gate --init-margin --baseline baselines/full-A` once"
    for f, v in want.items():
        assert abs(cfg["margin"][f] - v) <= 0.005


def test_regression_run_exits_1_and_names_the_must_pass_case(runs, capsys):
    gate = load("gate")
    code = gate.main([str(runs["ci-regression"]), "--baseline", BASELINE])
    out = capsys.readouterr().out
    assert code == 1, out
    assert re.search(r"^BLOCK must-pass reply case t\d+ passed \d of 5 trials", out, flags=re.M), "name the failing must-pass reply case"
    assert "t164" in out


def test_harmless_run_exits_0_and_prints_the_budget_lines(runs, capsys):
    gate = load("gate")
    code = gate.main([str(runs["ci-harmless"]), "--baseline", BASELINE])
    out = capsys.readouterr().out
    assert code == 0, out
    assert "budget cost per 1,000 requests" in out and "budget p95 latency" in out
    assert "BLOCK" not in out


def test_replay_miss_exits_1_through_check_misses(capsys):
    gate = load("gate")
    records = small_baseline()
    records[3] = dict(records[3], status="replay_miss", passed=False, tokens_in=None, tokens_out=None, latency_ms=None, latency_valid=False)
    run = gate.Run(records)
    lines = gate.check_misses(run)
    assert lines and lines[0][0] == "BLOCK" and "replay miss" in lines[0][1]
    lines, code = gate.gate(records, small_baseline(), CFG)
    assert code == 1


def test_drop_inside_the_margin_warns_and_exits_0():
    gate = load("gate")
    records = small_baseline()
    records[0:5] = rec("reply", "c0", [True, True, True, True, False])
    lines, code = gate.gate(records, small_baseline(), CFG)
    assert code == 0, lines
    assert any(level == "WARN" and "c0" in text for level, text in lines), lines


def test_a_drop_over_the_margin_blocks():
    gate = load("gate")
    records = small_baseline()
    for i in range(4):
        records[i * 5:(i + 1) * 5] = rec("reply", f"c{i}", [False] * 5)
    lines, code = gate.gate(records, small_baseline(), CFG)
    assert code == 1 and any(level == "BLOCK" and "margin" in text for level, text in lines)


def test_a_feature_under_its_floor_blocks():
    gate = load("gate")
    lines = gate.check_floor(gate.Run(small_baseline()), {"reply": 0.99})
    assert lines == []
    records = small_baseline()
    for i in range(6):
        records[i * 5:(i + 1) * 5] = rec("reply", f"c{i}", [False] * 5)
    lines = gate.check_floor(gate.Run(records), {"reply": 0.5})
    assert len(lines) == 1 and lines[0][0] == "BLOCK" and "floor" in lines[0][1]


def test_one_failed_trial_of_a_must_pass_case_blocks():
    gate = load("gate")
    records = small_baseline()
    records[0:5] = rec("reply", "c0", [True, True, True, True, False], must=True)
    lines = gate.check_must_pass(gate.Run(records))
    assert lines == [("BLOCK", "must-pass reply case c0 passed 4 of 5 trials")]
    lines, code = gate.gate(records, small_baseline(), CFG)
    assert code == 1


def test_over_the_cost_budget_exits_1():
    gate = load("gate")
    records = []
    for i in range(10):
        records += rec("reply", f"c{i}", [True] * 5, tokens_in=40000, tokens_out=8000)
    lines, code = gate.gate(records, small_baseline(), CFG)
    assert code == 1 and any(level == "BLOCK" and "cost" in text for level, text in lines)


def test_budget_line_uses_the_nearest_rank_p95():
    gate = load("gate")
    assert gate.p95_ms(list(range(100, 2001, 100))) == 1900, "20 values: rank ceil(0.95 x 20) = 19, the 19th is 1900"
    records = []
    for i in range(4):
        records += rec("reply", f"c{i}", [True] * 5)
    for r, ms in zip(records, range(100, 2001, 100)):
        r["latency_ms"] = ms
    lines = gate.check_budget(gate.Run(records), {"cost_per_1k": 99.0, "p95_ms": 1900})
    assert any("1900 ms" in text and level == "INFO" for level, text in lines), lines
    lines = gate.check_budget(gate.Run(records), {"cost_per_1k": 99.0, "p95_ms": 1800})
    assert any(level == "BLOCK" for level, _ in lines)


def test_batched_latency_is_left_out_of_the_p95():
    gate = load("gate")
    records = rec("reply", "c0", [True] * 5)
    records[1]["latency_ms"], records[1]["latency_valid"] = 99999, False
    assert gate.budget_numbers(gate.Run(records))["p95_ms"] == 1000


def test_results_md_records_the_expected_exit_codes():
    body = (HERE / "results.md").read_text(encoding="utf-8")
    assert "(fill in)" not in body
    assert re.search(r"^ci-regression: exit 1", body, flags=re.M) and re.search(r"^ci-harmless: exit 0", body, flags=re.M)


def test_smoke_is_subset_of_full_and_holds_every_must_pass_triage_and_reply_case():
    smoke = load("smoke")
    cases = smoke.full_cases()
    ids = smoke.select_smoke(cases)
    full_ids = {c["id"] for c in cases}
    assert set(ids) <= full_ids and ids == sorted(set(ids))
    must = {c["id"] for c in cases if c.get("must_pass")}
    assert must and must <= set(ids), "every must-pass case must be in smoke (its triage and its reply)"
    assert len(ids) < len(cases)


def test_smoke_has_no_agent_tasks():
    smoke = load("smoke")
    ids = smoke.select_smoke(smoke.full_cases())
    assert not [i for i in ids if i.startswith("r")]
    suite = tomllib.loads((ROOT / "suites" / "smoke.toml").read_text(encoding="utf-8"))
    assert {p["feature"] for p in suite["part"]} == {"triage", "reply"}
    assert all(p["cases"] == ids for p in suite["part"]), "run smoke.py so that suites/smoke.toml holds select_smoke's list"
