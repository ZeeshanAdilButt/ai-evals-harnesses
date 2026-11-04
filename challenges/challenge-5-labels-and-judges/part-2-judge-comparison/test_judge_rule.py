"""Challenge 5, part 2. Four rule tests and one test per checkpoint. They fail until tpr_tnr and choose_judge are written and the commands have run.
Checkpoint 1 needs runs/judge-dev/ and choice.json (the `judge-eval` and `choose` commands write them)."""
import importlib.util
import json
import re
from pathlib import Path

from evalkit import judges_cli, labels
from judges.parts import ALL_JUDGES

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUNS = ROOT / "runs"
PLACEHOLDER = "(fill in)"


def learner():
    spec = importlib.util.spec_from_file_location("learner_judge_rule_test", HERE / "judge_rule.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def section(title_start):
    text = (HERE / "results.md").read_text(encoding="utf-8")
    for p in re.split(r"^## ", text, flags=re.M):
        if p.startswith(title_start):
            return p
    raise AssertionError(f"results.md has no section that starts with '## {title_start}'")


def dev_files():
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((RUNS / "judge-dev").glob("*.json"))}


def test_tpr_tnr_fail_is_positive():
    m = learner()
    r = m.tpr_tnr(["fail", "fail", "pass", "pass"], ["fail", "pass", "pass", "pass"])
    assert (r["tp"], r["fn"], r["tn"], r["fp"]) == (1, 1, 2, 0), "fail is the positive class: one expert fail was caught, one missed"
    assert abs(r["tpr"] - 0.5) < 1e-9 and abs(r["tnr"] - 1.0) < 1e-9, "the inverted answer would give TPR 1.0 and TNR 0.5"
    r2 = m.tpr_tnr(["fail", "pass", "pass", "pass"], ["pass", "fail", "pass", None])
    assert (r2["tp"], r2["fn"], r2["tn"], r2["fp"]) == (0, 1, 1, 2), "an unreadable verdict is not a pass"


def test_choose_applies_floor_then_tnr():
    m = learner()
    rows = [{"judge": "X", "tpr": 0.90, "tnr": 0.85}, {"judge": "Y", "tpr": 0.80, "tnr": 0.92}]
    assert m.choose_judge(rows) == "X", "Y has the higher TNR but its TPR is under 0.85"
    assert m.choose_judge([{"judge": "a", "tpr": 0.85, "tnr": 0.9}, {"judge": "b", "tpr": 0.95, "tnr": 0.9}]) == "b", "tie on TNR: higher TPR"
    assert m.choose_judge([{"judge": "b", "tpr": 0.9, "tnr": 0.9}, {"judge": "a", "tpr": 0.9, "tnr": 0.9}]) == "a", "tie on both: lower id"
    assert m.choose_judge([{"judge": "Z", "tpr": 0.5, "tnr": 1.0}]) is None


def test_choice_is_allowed():
    choice = json.loads((HERE / "choice.json").read_text(encoding="utf-8"))
    jid = choice["judge"]
    assert jid in ALL_JUDGES and jid != "d1r1e1", "the id must be one of the 14 recorded judges (d1r1e1 is v3)"
    dev = dev_files()
    assert jid in dev and dev[jid]["tpr"] >= 0.85, "the choice must have dev TPR of at least 0.85"


def test_lock_matches_choice():
    choice = json.loads((HERE / "choice.json").read_text(encoding="utf-8"))
    lock = RUNS / "judge-test.lock"
    assert lock.exists(), "run `python -m evalkit judge-eval --split test` once, after `choose`"
    assert lock.read_text(encoding="utf-8").strip() == choice["judge"]


def test_checkpoint_1():
    test_tpr_tnr_fail_is_positive()
    test_choose_applies_floor_then_tnr()
    body = section("Dev")
    assert PLACEHOLDER not in body
    dev = dev_files()
    for j in ("v1", "v2", "v3"):
        assert j in dev, f"run `judge-eval --judge {j} --split dev`"
        assert re.search(rf"^\| {j} \| .*{dev[j]['tp']}.*{dev[j]['tn']}", body, flags=re.M), f"the dev table needs the counts of {j}"
    builder = [j for j in dev if re.fullmatch(r"d[01]r[01]e[123]", j) and j != "d1r1e1"]
    assert builder, "run one builder id other than d1r1e1 (which is v3)"
    assert re.search(rf"^\| {builder[0]} \|", body, flags=re.M)
    rule = learner().choose_judge(list(dev.values()))
    choice = json.loads((HERE / "choice.json").read_text(encoding="utf-8"))
    assert choice["judge"] == rule, f"choice.json must hold the rule's choice over runs/judge-dev/ ({rule})"
    assert re.search(rf"^Choice by the rule: {rule}$", body, flags=re.M)


def test_checkpoint_2():
    test_lock_matches_choice()
    test_choice_is_allowed()
    body = section("Test and probes")
    assert PLACEHOLDER not in body
    choice = json.loads((HERE / "choice.json").read_text(encoding="utf-8"))
    test = json.loads((RUNS / "judge-test.json").read_text(encoding="utf-8"))
    assert test["judge"] == choice["judge"]
    ids, e, j, missing = judges_cli.split_verdicts(choice["judge"], "test")
    assert not missing
    want = learner().tpr_tnr(e, j)
    for k in ("tp", "fn", "tn", "fp"):
        assert test[k] == want[k], f"the test counts must match the recording ({k})"
        assert re.search(rf"^{k}: {want[k]}$", body, flags=re.M), f"write the line '{k}: {want[k]}' in the test section"
    for probe in ("position", "length", "self-preference"):
        line = re.search(rf"^{probe}: (.+)$", body, flags=re.M)
        assert line, f"write a '{probe}:' line with the reading next to the rerun reference"
        if probe == "position" and "not applicable" in line.group(1):
            assert choice["judge"] in ("v1", "v2"), "position may read not applicable only for v1 and v2"
        else:
            assert "rerun" in line.group(1), f"read the {probe} count against the rerun reference"
