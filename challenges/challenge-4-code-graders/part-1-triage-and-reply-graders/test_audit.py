"""Challenge 4, part 1, checkpoint 3: the audit, the matrices and the weak class. test_checkpoint_3 runs test_audit and test_results_matrices."""
import importlib
import importlib.util
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PLACEHOLDER = "(fill in)"


def load(name):
    spec = importlib.util.spec_from_file_location(f"learner_{name}_t3", HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def section(title_start):
    text = (HERE / "results.md").read_text(encoding="utf-8")
    for p in re.split(r"^## ", text, flags=re.M):
        if p.startswith(title_start):
            return p
    raise AssertionError(f"results.md has no section that starts with '## {title_start}'")


def test_run_audit_reports_disagreements():
    a = load("audit")
    r = a.run_audit(lambda o: o.startswith("ok"), ["ok 1", "ok 2", "nope"], ["bad 1", "ok but wrong"])
    assert (r["good_n"], r["bad_n"], r["ok"]) == (3, 2, False)
    assert {(d["kind"], d["output"]) for d in r["disagreements"]} == {("good_failed", "nope"), ("bad_passed", "ok but wrong")}
    assert a.run_audit(lambda o: True, ["x"], [])["ok"] is True
    always_yes = a.run_audit(lambda o: True, ["x"], ["y"])
    assert always_yes["ok"] is False and always_yes["disagreements"][0]["kind"] == "bad_passed", "a grader that passes everything fails the audit"


def test_audit_set_is_valid_and_your_grader_passes_it():
    a, g = load("audit"), load("graders")
    from evalkit.graders.reference import graders as ref_graders

    ref = ref_graders()
    good, bad = a.audit_set()
    assert len(good) >= 8 and len(bad) >= 8, "write at least 8 known-good and 8 known-bad outputs"
    assert len(set(good)) == len(good) and len(set(bad)) == len(bad), "no repeated outputs"
    for o in good:
        assert ref.grade_triage_match(o, a.EXPECTED), f"known-good output is not good by the reference grader: {o!r}"
    for o in bad:
        assert not ref.grade_triage_match(o, a.EXPECTED), f"known-bad output is not bad by the reference grader: {o!r}"
    result = a.run_audit(lambda o: g.grade_triage_match(o, a.EXPECTED), good, bad)
    assert result["ok"], f"your grader disagrees with your audit set: {result['disagreements']}"
    assert result["good_n"] == len(good) and result["bad_n"] == len(bad)


def test_audit():
    test_run_audit_reports_disagreements()
    test_audit_set_is_valid_and_your_grader_passes_it()


def parse_block(body, variant):
    """Read the numbers grade.py printed for one variant out of results.md."""
    m = re.search(rf"^Variant {variant}, canonical v1.*?(?=^Variant [AB], canonical v1|^### |\Z)", body, flags=re.M | re.S)
    assert m, f"Checkpoint 3: paste the output of grade.py --variant {variant} in a code block"
    block = m.group(0)
    u = re.search(r"Urgent \(positive class\): TP (\d+), FP (\d+), FN (\d+), TN (\d+)", block)
    assert u, f"variant {variant}: the 2 by 2 line 'Urgent (positive class): TP ...' is missing"
    urgent = dict(zip(("tp", "fp", "fn", "tn"), map(int, u.groups())))
    rows = re.findall(r"^\| (billing|delivery|refund|account|product) \| ([\d |]+)\|$", block, flags=re.M)
    cols = ["billing", "delivery", "refund", "account", "product", "invalid"]
    cat = {t: dict(zip(cols, map(int, vals.replace("|", " ").split()))) for t, vals in rows}
    assert len(cat) == 5, f"variant {variant}: the 5 by 5 matrix is missing rows"
    return urgent, cat


def test_results_matrices():
    body = section("Checkpoint 3")
    sys.path.insert(0, str(HERE))
    grade = importlib.import_module("grade")
    from evalkit.graders.reference import graders

    for v in "AB":
        ref = grade.triage_numbers(v, graders())
        urgent, cat = parse_block(body, v)
        assert sum(urgent.values()) == ref["n"], f"variant {v}: the 2 by 2 matrix must sum to {ref['n']} cases"
        assert sum(sum(r.values()) for r in cat.values()) == ref["n"], f"variant {v}: the 5 by 5 matrix must sum to {ref['n']} cases"
        assert urgent == ref["urgent"], f"variant {v}: the 2 by 2 matrix differs from the reference {ref['urgent']}"
        assert cat == ref["category"], f"variant {v}: the 5 by 5 matrix differs from the reference, cell by cell"
        recall = {t: cat[t][t] / sum(cat[t].values()) for t in cat}
        weak = re.search(rf"^Weak class {v}: (\w+)", body, flags=re.M)
        assert weak, f"write a line 'Weak class {v}: <category>' and one sentence on why"
        assert weak.group(1) == min(recall, key=lambda t: (recall[t], t)) == ref["weak_class"], f"Weak class {v}: the row with the lowest recall"


def test_checkpoint_3():
    test_audit()
    test_results_matrices()
    body = section("Checkpoint 3")
    assert PLACEHOLDER not in body
    m = re.search(r"^Audit: (\d+) known-good, (\d+) known-bad, (\d+) disagreements", body, flags=re.M)
    assert m and m.group(3) == "0", "paste the audit line with 0 disagreements"
    answer = body.split("### Interview answer", 1)[-1] if "### Interview answer" in body else ""
    assert len(answer.strip()) > 80, "write your interview answer under '### Interview answer'"
