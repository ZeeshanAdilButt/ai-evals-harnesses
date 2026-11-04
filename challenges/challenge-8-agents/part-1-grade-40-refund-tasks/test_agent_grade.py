"""Challenge 8, part 1. One test per checkpoint. test_checkpoint_1 needs only the shipped state grader and the state table in results.md;
test_checkpoint_2 and test_checkpoint_3 fail until grade_trajectory is written (it raises NotImplementedError)."""
import importlib.util
import json
import re
from pathlib import Path

from evalkit import stats
from evalkit.graders import agent as ref

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PLACEHOLDER = "(fill in)"


def learner():
    spec = importlib.util.spec_from_file_location("learner_agent_grade", HERE / "agent_grade.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def section(title_start):
    text = (HERE / "results.md").read_text(encoding="utf-8")
    for p in re.split(r"^## ", text, flags=re.M):
        if p.startswith(title_start):
            return p
    raise AssertionError(f"results.md has no section that starts with '## {title_start}'")


def reference_rows(variant):
    """The canonical twin: datasets/reference_grades/agent.jsonl."""
    path = ROOT / "datasets/reference_grades/agent.jsonl"
    return [r for r in map(json.loads, path.read_text(encoding="utf-8").splitlines()) if r["variant"] == variant]


def trial(calls, ledger=(), escalations=(), gave_up=False):
    return {"trajectory": [{"tool": t, "input": i, "step": n + 1} for n, (t, i) in enumerate(calls)],
            "final_state": {"ledger": [dict(x) for x in ledger], "escalations": [dict(x) for x in escalations]}, "customer_gave_up": gave_up}


def task_r01():
    return ref.load_tasks()["r01"]


GET = ("get_order", {"order_id": "FM-104201"})
POLICY = ("get_policy", {"topic": "missing_items"})
REFUND = ("issue_refund", {"order_id": "FM-104201", "amount": 8.99, "reason": "missing"})


# ----- checkpoint 1: the shipped state grader and its table -----------------------------------------------------------

def test_state_grader_is_worked_and_shipped():
    t = task_r01()
    good = trial([GET, REFUND], ledger=[{"order_id": "FM-104201", "amount": 8.99}])
    assert ref.grade_final_state(good, t)["ok"] is True
    assert ref.grade_final_state(trial([GET, REFUND], ledger=[{"order_id": "FM-104201", "amount": 8.5}]), t) == {
        "refund_count": True, "refund_orders": True, "refund_amounts": False, "escalations": True, "ok": False}
    assert ref.grade_final_state(trial([GET]), t)["refund_count"] is False


def test_checkpoint_1():
    test_state_grader_is_worked_and_shipped()
    body = section("Checkpoint 1")
    assert PLACEHOLDER not in body
    want = {}
    for r in reference_rows("A"):
        want[r["task"]] = want.get(r["task"], 0) + int(r["state_ok"])
    got = {m.group(1): int(m.group(2)) for m in re.finditer(r"^\| (r\d\d) \| (\d) \|$", body, flags=re.M)}
    assert got == want, "the state table for A (task | trials of 5 whose final state is right) must equal the reference table"


# ----- checkpoint 2: your trajectory grader ----------------------------------------------------------------------------

def test_good_trial_with_a_different_tool_order_passes():
    m = learner()
    t = task_r01()
    for calls in ([POLICY, GET, REFUND], [GET, POLICY, POLICY, REFUND], [GET, REFUND]):
        r = m.grade_trajectory(trial(calls, ledger=[{"order_id": "FM-104201", "amount": 8.99}]), t)
        assert r["pass"] is True and r["rule"] is None, f"{[c[0] for c in calls]} breaks no rule: {r}"


def test_double_refund_fails_with_r1_named():
    m = learner()
    t = task_r01()
    twice = trial([GET, REFUND, REFUND], ledger=[{"order_id": "FM-104201", "amount": 8.99}] * 2)
    r = m.grade_trajectory(twice, t)
    assert r["pass"] is False and r["rule"] == "R1", f"two refunds for one order break a `never` rule (R1): {r}"
    assert "detail" in r and r["detail"]


def test_each_rule_is_named():
    m = learner()
    t = task_r01()
    assert m.grade_trajectory(trial([REFUND, GET]), t)["rule"] == "R2", "refund before looking up the order breaks `before`"
    assert m.grade_trajectory(trial([POLICY] * 9 + [GET, REFUND]), t)["rule"] == "R3", "over the step budget"
    over = trial([GET, ("issue_refund", {"order_id": "FM-104201", "amount": 99.0, "reason": "x"})])
    assert m.grade_trajectory(over, t)["rule"] == "R1", "refunding more than the order total breaks `never`"
    none_allowed = ref.load_tasks()["r15"]
    assert m.grade_trajectory(trial([("get_order", {"order_id": "FM-104215"}), ("issue_refund", {"order_id": "FM-104215", "amount": 2.99, "reason": "x"})]),
                              none_allowed)["rule"] == "R1", "any_refund"
    assert m.grade_trajectory(trial([("get_policy", {"topic": "refund_window"})]), none_allowed)["rule"] == "R2", "`end` pairs: get_order must be called"
    assert m.grade_trajectory(trial([("get_order", {"order_id": "FM-104215"})]), none_allowed)["pass"] is True


def test_agrees_with_reference_on_every_recorded_trial():
    m = learner()
    tasks = ref.load_tasks()
    n = 0
    for v in "AB":
        for t in ref.load_runs(v):
            task = tasks[t["task"]]
            want = ref.trajectory_violations(task, t["trajectory"], ref.order_total(task))
            got = m.grade_trajectory(t, task)
            assert got["pass"] == (not want), (v, t["task"], t["trial"], got, want)
            n += 1
    assert n == 400


def test_checkpoint_2():
    test_good_trial_with_a_different_tool_order_passes()
    test_double_refund_fails_with_r1_named()
    test_each_rule_is_named()
    test_agrees_with_reference_on_every_recorded_trial()
    body = section("Checkpoint 2")
    assert PLACEHOLDER not in body
    assert re.search(r"^Double refund: fail, rule R1", body, flags=re.M), "write the line 'Double refund: fail, rule R1 ...' from your audit"
    assert re.search(r"^Different tool order: pass", body, flags=re.M)


# ----- checkpoint 3: pass^k, first failing step, the simulator --------------------------------------------------------

def test_pass_hat_k_values():
    assert stats.pass_hat_k(4, 5, 4) == 0.2
    assert stats.pass_hat_k(5, 5, 4) == 1.0
    assert stats.pass_hat_k(3, 5, 4) == 0.0
    assert abs(stats.pass_hat_k(3, 5, 2) - 0.3) < 1e-9


def test_grades_match_reference_file_and_are_byte_stable():
    m = learner()
    for v in "AB":
        rows = m.grade_all(v)
        again = m.grade_all(v)
        assert json.dumps(rows, sort_keys=True) == json.dumps(again, sort_keys=True), "grades must be the same on a re-run"
        want = reference_rows(v)
        assert len(rows) == len(want) == 200
        diff = [(a["task"], a["trial"]) for a, b in zip(rows, want) if (a["state_ok"], a["traj_pass"], a["traj_rule"], a["passed"]) !=
                (b["state_ok"], b["traj_pass"], b["traj_rule"], b["passed"])]
        assert not diff, f"your grades differ from the reference grades for {diff[:5]}"


def test_checkpoint_3():
    test_pass_hat_k_values()
    test_grades_match_reference_file_and_are_byte_stable()
    body = section("Checkpoint 3")
    assert PLACEHOLDER not in body
    m = learner()
    for v in "AB":
        rows = m.grade_all(v)
        for k in (1, 4):
            hit = re.search(rf"^pass\^{k} {v}: ([\d.]+)%", body, flags=re.M)
            assert hit, f"write a line 'pass^{k} {v}: N%' from agent_grade.py or `stats passk`"
            assert abs(float(hit.group(1)) / 100 - m.suite_pass_hat_k(rows, k)) <= 0.005
    labels = {(r.group(1), int(r.group(2))): r.group(3) for r in re.finditer(r"^\| (r\d\d) \| (\d) \| (\w+) \|$", body, flags=re.M)}
    failed = [(r["task"], r["trial"]) for r in reference_rows("A") if not r["passed"]]
    assert set(labels) == set(failed), "label every failed trial of A, and only those, in the table | task | trial | label |"
    sim_task = ref_fact("m8.sim_fail_task_2")
    r13 = [k for k in failed if k[0] == sim_task]
    assert r13 and all(labels[k] == "simulator" for k in r13), f"the failed trials of {sim_task} are the scripted customer giving up: label them simulator"
    worked = ref_fact("m8.sim_fail_task_1")
    others = [k for k, v in labels.items() if v == "simulator" and k[0] not in (sim_task, worked)]
    assert not others, f"no other failure is a simulator failure: {others[:3]}"


def ref_fact(name):
    """The two planted tasks, read from the tasks file (the task whose customer gives up is the planted one)."""
    planted = sorted(t["id"] for t in ref.load_tasks().values() if t["planted_simulator_failure"])
    return {"m8.sim_fail_task_1": planted[0], "m8.sim_fail_task_2": planted[1]}[name]
