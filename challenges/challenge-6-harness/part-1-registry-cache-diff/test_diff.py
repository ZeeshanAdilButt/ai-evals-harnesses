from evalkit.suites import read_trials


def rec(case, passed, trial=1, variant="A"):
    return {"feature": "triage", "case_id": case, "variant": variant, "trial": trial, "passed": passed,
            "grades": {"match": passed}, "output": f"out-{case}-{variant}"}


def test_flips_listed(impl1):
    a = [rec("c1", False), rec("c2", True), rec("c3", True), rec("c4", False)]
    b = [rec("c1", True, variant="B"), rec("c2", False, variant="B"), rec("c3", True, variant="B"), rec("c4", False, variant="B")]
    rows = impl1.diff_runs(a, b)
    assert [(r["case_id"], r["direction"]) for r in rows] == [("c1", "to_pass"), ("c2", "to_fail")]
    assert rows[0]["grades_a"] == {"match": False} and rows[0]["grades_b"] == {"match": True}
    assert rows[0]["a_score"] == 0.0 and rows[0]["b_score"] == 1.0


def test_case_score_is_the_mean_of_its_trials(impl1):
    a = [rec("c1", t <= 3, trial=t) for t in range(1, 6)]
    b = [rec("c1", True, trial=t, variant="B") for t in range(1, 6)]
    rows = impl1.diff_runs(a, b)
    assert len(rows) == 1 and rows[0]["a_score"] == 0.6 and rows[0]["b_score"] == 1.0 and rows[0]["direction"] == "to_pass"


def test_equal_scores_are_not_a_flip(impl1):
    assert impl1.diff_runs([rec("c1", True), rec("c2", False)], [rec("c1", True, variant="B"), rec("c2", False, variant="B")]) == []


def test_real_runs_flip_both_ways(impl1, reference, tmp_path):
    from evalkit import engine

    ra = engine.run_suite("m1-triage", "A", impl=impl1, out=tmp_path / "a")
    rb = engine.run_suite("m1-triage", "B", impl=impl1, out=tmp_path / "b")
    a, b = read_trials(ra["out"]), read_trials(rb["out"])
    rows = impl1.diff_runs(a, b)
    assert ra["passed"] == rb["passed"]
    assert {r["direction"] for r in rows} == {"to_pass", "to_fail"}
    assert rows == reference.diff_runs(a, b)
