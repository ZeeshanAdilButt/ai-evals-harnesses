"""Challenge 2, part 2. Three tests fail on the starter because my_taxonomy.yaml and criteria/v1.md are empty."""
from pathlib import Path

from evalkit import criteria, taxonomy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PLACEHOLDER = "(fill in)"


def mine():
    text = (HERE / "my_taxonomy.yaml").read_text(encoding="utf-8")
    return taxonomy.parse_taxonomy(text)


def test_rank_modes_tie_break_and_zero_cost():
    """The shipped rank_modes: score = count x weight, ties by name, a mode with no weight is not ranked."""
    a = {"t1": "X", "t2": "X", "t3": "Y", "t4": "Z", "t5": "none"}
    rows = taxonomy.rank_modes(a, {"X": 1, "Y": 2, "Z": 2})
    assert [(r["mode"], r["score"]) for r in rows] == [("X", 2), ("Y", 2), ("Z", 2)]


def test_rank_modes_uses_weights():
    tax = mine()
    assert tax["modes"], "my_taxonomy.yaml is empty: write the modes"
    failure_modes = {n: s for n, s in tax["modes"].items() if not taxonomy.is_no_failure(n)}
    assert failure_modes, "write at least one failure mode"
    for name, spec in failure_modes.items():
        assert spec["weight"] in (1, 2, 3), f"{name}: the cost weight is 1, 2 or 3"
    assignments = dict(tax["traces"])
    costs = {n: s["weight"] for n, s in failure_modes.items()}
    expected = sorted(((sum(1 for m in assignments.values() if m == n) * w, n) for n, w in costs.items()), key=lambda x: (-x[0], x[1]))
    shipped = taxonomy.rank_modes(assignments, costs)
    assert [(r["score"], r["mode"]) for r in shipped] == expected
    for r in shipped:
        assert r["score"] == r["count"] * r["weight"]


def test_saturation_marked():
    tax = mine()
    assert tax["saturation_at"] is not None, "saturation_at is missing from my_taxonomy.yaml"
    assignments = dict(tax["traces"])
    order = [t for t, _ in tax["traces"]]
    assert tax["saturation_at"] == taxonomy.saturation_position(order, assignments), (
        "saturation_at is the position (in the order you listed the traces) of the trace where your last new mode first appears")


def test_taxonomy_and_criteria_pass_checks():
    tax = mine()
    assert not taxonomy.check_taxonomy(tax), taxonomy.check_taxonomy(tax)
    text = (ROOT / "criteria" / "v1.md").read_text(encoding="utf-8")
    crit = criteria.parse_criteria(text)
    assert len(crit) == 3, "criteria/v1.md needs exactly three criteria, each under a '## ' heading"
    for i, c in enumerate(crit, 1):
        assert not criteria.problems(c), f"criterion {i}: {criteria.problems(c)}"


def test_criteria_check_flags_vague_words():
    c = {"title": "t", "question": "Is the reply helpful?", "pass": "a b c d e f", "fail": "a b c d e f"}
    assert any("vague" in p for p in criteria.problems(c))
    c["question"] = "Is the reply good and kind?"
    assert any("vague" in p for p in criteria.problems(c))


def test_results_written():
    body = (HERE / "results.md").read_text(encoding="utf-8")
    assert PLACEHOLDER not in body, "results.md still has '(fill in)'"
    for head in ("Saturation:", "Differences from the shipped criteria", "Differences from the shipped taxonomy"):
        assert head in body, f"results.md needs a line or section '{head}'"
