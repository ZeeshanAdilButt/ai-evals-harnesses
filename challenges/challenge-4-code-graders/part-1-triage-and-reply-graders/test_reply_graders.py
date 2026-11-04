"""Challenge 4, part 1, checkpoint 2: the reply graders. test_checkpoint_2 runs the tests above it and checks results.md."""
import importlib
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PLACEHOLDER = "(fill in)"


def load(name):
    spec = importlib.util.spec_from_file_location(f"learner_{name}_t2", HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def section(title_start):
    text = (HERE / "results.md").read_text(encoding="utf-8")
    for p in re.split(r"^## ", text, flags=re.M):
        if p.startswith(title_start):
            return p
    raise AssertionError(f"results.md has no section that starts with '## {title_start}'")


def test_contains_must_and_must_not():
    g = load("graders")
    r = "Hello,\n\nI'm sorry.  Refunds go back to your **Original Payment Method** within 5 working days."
    assert g.grade_reply_contains(r, ["original payment method", "5 working days"], ["store credit"]) is True
    assert g.grade_reply_contains(r, ["original payment method", "today"], []) is False
    assert g.grade_reply_contains(r + " Or store credit.", ["5 working days"], ["Store  Credit"]) is False
    assert g.grade_reply_contains(r, [], []) is True


def test_refund_days_are_exact():
    g = load("graders")
    assert g.grade_reply_refund_days("You are within our 7 days window.", 7) is True
    assert g.grade_reply_refund_days("Our 7-day refund window is open.", 7) is True
    assert g.grade_reply_refund_days("Refunds are open for a week.", 7) is False, "a week is 7 days, but no number is written"
    assert g.grade_reply_refund_days("Refunds are open for seven days.", 7) is False
    assert g.grade_reply_refund_days("Our refund window is 14 days.", 7) is False
    assert g.grade_reply_refund_days("It is 7 days, or 14 days with a photo.", 7) is False
    assert g.grade_reply_refund_days("Money returns within 5 working days. The window is 7 days.", 7) is True
    assert g.grade_reply_refund_days("Money returns within 5 working days.", 7) is False


def test_shipped_amount_grader_uses_a_tolerance():
    g = load("graders")
    assert g.grade_reply_amount("We refunded $4.99 today.", 4.99, 0.01) is True
    assert g.grade_reply_amount("We refunded $4.98 today.", 4.99, 0.01) is True
    assert g.grade_reply_amount("We refunded $5.10 today.", 4.99, 0.01) is False
    assert g.find_numbers("$1,200.50 in 5-7 days") == [1200.5, 5.0, 7.0]


def test_matches_reference_on_every_recorded_reply():
    """A and B, trial 1 to 5, on canonical v1: the same answers as the reference reply graders."""
    from evalkit.graders import reply as ref
    from evalkit.replay import Store
    from product import reply

    g = load("graders")
    store = Store.load("reply")
    checks = ref.load_checks()
    cases = [json.loads(l) for l in (ROOT / "datasets/canonical/v1/cases.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    n = 0
    for v in "AB":
        for c in cases:
            ck = checks[c["id"]]
            key = reply.build_request(v, c["text"])["key"]
            for t in range(1, 6):
                out = store.lookup(key, t)["output"]
                assert g.grade_reply_contains(out, ck["must_contain"], ck["must_not_contain"]) == ref.grade_reply_contains(out, ck["must_contain"], ck["must_not_contain"]), (v, c["id"], t)
                if ck["refund_days"] is not None:
                    assert g.grade_reply_refund_days(out, ck["refund_days"]) == ref.grade_reply_refund_days(out, ck["refund_days"]), (v, c["id"], t)
                n += 1
    assert n == 1600


def test_checkpoint_2():
    test_contains_must_and_must_not()
    test_refund_days_are_exact()
    test_shipped_amount_grader_uses_a_tolerance()
    test_matches_reference_on_every_recorded_reply()
    body = section("Checkpoint 2")
    assert PLACEHOLDER not in body
    sys.path.insert(0, str(HERE))
    grade = importlib.import_module("grade")
    from evalkit.graders.reference import graders

    for v in "AB":
        ref = grade.reply_numbers(v, graders())
        for label, key in (("Reply must and must not contain", "contains"), ("Reply refund days exact", "days"), ("Reply amount within 0.01", "amount"),
                           ("Reply must-pass cases", "must_pass")):
            m = re.search(rf"^{label} {v}: ([\d.]+)%", body, flags=re.M)
            assert m, f"Checkpoint 2: write a line '{label} {v}: N%' from grade.py --variant {v}"
            assert abs(float(m.group(1)) - ref[key]) <= 0.05, f"{label} {v}: the reference value is {ref[key]}%"
