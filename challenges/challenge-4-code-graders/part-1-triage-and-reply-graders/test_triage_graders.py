"""Challenge 4, part 1, checkpoint 1: the triage graders. test_checkpoint_1 runs the tests above it and checks results.md."""
import importlib.util
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PLACEHOLDER = "(fill in)"


def load(name):
    spec = importlib.util.spec_from_file_location(f"learner_{name}_t1", HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def section(title_start):
    text = (HERE / "results.md").read_text(encoding="utf-8")
    for p in re.split(r"^## ", text, flags=re.M):
        if p.startswith(title_start):
            return p
    raise AssertionError(f"results.md has no section that starts with '## {title_start}'")


def test_normalise():
    g = load("graders")
    assert g.normalise("  Refund \n") == "refund"
    assert g.normalise("It’s  **Fine**") == "it's fine"
    assert g.normalise("a\t\tb\n\nc") == "a b c"
    assert g.normalise("`code`") == "code"


def test_schema_grader():
    g = load("graders")
    ok = ['{"category": "refund", "urgent": false}', '{"category":"billing","urgent":true}', '```json\n{"category": "product", "urgent": false}\n```',
          '{"category": "Delivery", "urgent": true}']
    bad = ['{"category": "refund"}', '{"category": "refunds", "urgent": false}', '{"category": "refund", "urgent": "false"}', 'refund', '',
           'Here you go: {"category": "refund", "urgent": false}', '[1, 2]', '{"category": 7, "urgent": false}']
    assert all(g.grade_triage_schema(o) for o in ok)
    assert not any(g.grade_triage_schema(o) for o in bad)


def test_match_grader():
    g = load("graders")
    exp = {"category": "refund", "urgent": False}
    assert g.grade_triage_match('{"category": "Refund", "urgent": false}', exp) is True
    assert g.grade_triage_match('{"category":"refund","urgent":false}', exp) is True
    assert g.grade_triage_match('{"category": "refund", "urgent": true}', exp) is False
    assert g.grade_triage_match('{"category": "billing", "urgent": false}', exp) is False
    assert g.grade_triage_match("I think this is a refund", exp) is False


def test_matches_reference_on_every_recorded_output():
    """All five trials of A and B on canonical v1 (1,600 outputs): same answer as the reference grader."""
    from evalkit.graders import triage as ref
    from evalkit.replay import Store
    from product import triage

    g = load("graders")
    store = Store.load("triage")
    cases = [json.loads(l) for l in (ROOT / "datasets/canonical/v1/cases.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    checked = 0
    for v in "AB":
        for c in cases:
            key = triage.build_request(v, c["text"])["key"]
            for t in range(1, 6):
                out = store.lookup(key, t)["output"]
                cat, urg = ref.predicted(out)
                assert g.grade_triage_schema(out) == ref.grade_schema(out), (v, c["id"], t, out[:60])
                assert g.grade_triage_match(out, c["expected"]) == (cat == c["expected"]["category"] and urg is c["expected"]["urgent"]), (v, c["id"], t)
                checked += 1
    assert checked == 1600


def reference_values(variant):
    import sys

    sys.path.insert(0, str(HERE))
    import importlib

    grade = importlib.import_module("grade")
    from evalkit.graders.reference import graders

    return grade.triage_numbers(variant, graders()), grade.compact


def test_checkpoint_1():
    test_normalise()
    test_schema_grader()
    test_match_grader()
    test_matches_reference_on_every_recorded_output()
    body = section("Checkpoint 1")
    assert PLACEHOLDER not in body
    for v in "AB":
        ref, _ = reference_values(v)
        for label, key in (("Schema pass", "schema"), ("Whole-string match", "compact"), ("Normalised match", "normalised_category")):
            m = re.search(rf"^{label} {v}: ([\d.]+)%", body, flags=re.M)
            assert m, f"Checkpoint 1: write a line '{label} {v}: N%' from grade.py --variant {v}"
            assert abs(float(m.group(1)) - ref[key]) <= 0.05, f"{label} {v}: the reference value is {ref[key]}%"
