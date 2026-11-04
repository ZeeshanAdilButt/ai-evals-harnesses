"""Challenge 1, part 1. test_checkpoint_1 to test_checkpoint_3 are the three checkpoints of results.md.
If you stop, start again at the first checkpoint whose test fails."""
import json
import re
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PLACEHOLDER = "(fill in)"


def expected():
    """The truth, from the recordings: the ten cases, trial 1, A and B (does not use first_eval.py)."""
    from evalkit.graders.shipped import match, schema
    from evalkit.replay import Store
    from product import triage

    suite = tomllib.loads((ROOT / "suites" / "m1-triage.toml").read_text(encoding="utf-8"))["part"][0]
    cases = {}
    for line in (ROOT / suite["dataset"]).read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        cases[row["id"]] = row
    store = Store.load("triage")
    result = {}
    for cid in suite["cases"]:
        c = cases[cid]
        result[cid] = {v: (lambda out: schema(out, c) and match(out, c))(store.lookup(triage.build_request(v, c["text"])["key"], 1)["output"])
                       for v in "AB"}
    return result


def section(title_start):
    text = (HERE / "results.md").read_text(encoding="utf-8")
    parts = re.split(r"^## ", text, flags=re.M)
    for p in parts:
        if p.startswith(title_start):
            return p
    raise AssertionError(f"results.md has no section that starts with '## {title_start}'")


def test_checkpoint_1():
    body = section("Checkpoint 1")
    for prefix in ("OK python", "OK packages", "OK git", "OK replay"):
        assert re.search(rf"^{prefix}", body, flags=re.M), f"Checkpoint 1: paste the doctor line that starts with '{prefix}'"
    branch = re.search(r"^Branch: (.+)$", body, flags=re.M)
    assert branch and branch.group(1).strip() not in ("", PLACEHOLDER, "main"), "Checkpoint 1: write the name of your branch (not main)"


def test_checkpoint_2():
    body = section("Checkpoint 2")
    run_id = re.search(r"^Run id: (\S+)$", body, flags=re.M)
    passed = re.search(r"^Passed: (\d+) of (\d+)$", body, flags=re.M)
    assert run_id and run_id.group(1) == "m1-triage-A", "Checkpoint 2: write 'Run id: m1-triage-A'"
    truth = expected()
    pass_a = sum(v["A"] for v in truth.values())
    assert passed, "Checkpoint 2: write 'Passed: N of 10' from report.md"
    assert (int(passed.group(1)), int(passed.group(2))) == (pass_a, len(truth)), f"Checkpoint 2: A passes {pass_a} of {len(truth)}"


def test_flipped_list():
    path = HERE / "my_flips.json"
    flips = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    assert flips, "my_flips.json is empty: list the flipped case ids"
    truth = expected()
    want = {cid: ("to_pass" if v["B"] else "to_fail") for cid, v in truth.items() if v["A"] != v["B"]}
    assert {f["case_id"] for f in flips} == set(want), f"my_flips.json must list exactly the flipped cases ({len(want)} of them)"
    for f in flips:
        assert f["direction"] == want[f["case_id"]], f"{f['case_id']}: A to B goes {want[f['case_id']]}"
        assert f["grader_type"] in ("code", "judge", "person"), f"{f['case_id']}: grader_type is code, judge or person"


def test_checkpoint_3():
    test_flipped_list()
    body = section("Checkpoint 3")
    answer = body.split("### Interview answer", 1)[-1] if "### Interview answer" in body else ""
    assert len(answer.strip()) > 60 and PLACEHOLDER not in answer, "Checkpoint 3: write your interview answer under '### Interview answer'"
