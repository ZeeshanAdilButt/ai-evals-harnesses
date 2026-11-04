"""Challenge 5, part 1. One test per checkpoint. The kappa tests fail until cohen_kappa and needs_reread are written."""
import importlib.util
import json
import re
from pathlib import Path

from evalkit import judges_cli, labels

HERE = Path(__file__).resolve().parent
PLACEHOLDER = "(fill in)"


def learner():
    spec = importlib.util.spec_from_file_location("learner_kappa_test", HERE / "kappa.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def from_cells(both_pass, mine_pass_expert_fail, mine_fail_expert_pass, both_fail):
    mine = ["pass"] * both_pass + ["pass"] * mine_pass_expert_fail + ["fail"] * mine_fail_expert_pass + ["fail"] * both_fail
    expert = ["pass"] * both_pass + ["fail"] * mine_pass_expert_fail + ["pass"] * mine_fail_expert_pass + ["fail"] * both_fail
    return mine, expert


def section(title_start):
    text = (HERE / "results.md").read_text(encoding="utf-8")
    for p in re.split(r"^## ", text, flags=re.M):
        if p.startswith(title_start):
            return p
    raise AssertionError(f"results.md has no section that starts with '## {title_start}'")


def test_known_table():
    m = learner()
    assert abs(m.cohen_kappa(*from_cells(88, 5, 5, 2)) - 0.232) <= 0.005
    assert abs(m.cohen_kappa(*from_cells(45, 5, 5, 45)) - 0.80) <= 0.005
    assert abs(m.cohen_kappa(*from_cells(14, 1, 1, 4)) - 0.73) <= 0.005
    assert abs(m.cohen_kappa(*from_cells(17, 1, 1, 1)) - 0.44) <= 0.005


def test_undefined_when_pe_is_one():
    m = learner()
    assert m.cohen_kappa(["pass"] * 6, ["pass"] * 6) is None, "everyone said pass: chance agreement is 1, kappa is undefined"
    assert m.cohen_kappa(["fail"] * 4, ["fail"] * 4) is None


def test_needs_reread_rule():
    m = learner()
    assert m.needs_reread(0.59) is True and m.needs_reread(0.6) is False and m.needs_reread(0.9) is False
    assert m.needs_reread(None) is True


def test_reconcile_never_overwrites(tmp_path):
    m = learner()
    expert_ids = [r["id"] for r in labels.split_items("blind")]
    verdicts = labels.expert_labels()[0]
    expert = [verdicts[i] for i in expert_ids]
    mine = list(expert)
    mine[0] = "pass" if expert[0] == "fail" else "fail"          # one planted disagreement
    assert m.cohen_kappa(mine, expert) is not None
    path = tmp_path / "my_labels_blind.jsonl"
    path.write_text("".join(json.dumps({"id": i, "label": l}) + "\n" for i, l in zip(expert_ids, mine)), encoding="utf-8")
    before = path.read_bytes()
    notes = tmp_path / "reconcile.jsonl"
    dis = m.disagreement_ids(expert_ids, mine, expert)
    assert dis == [expert_ids[0]]
    for i in dis:
        judges_cli.add_note(notes, i, "I read the refund time as 7 days; the policy says 5 working days.")
    assert path.read_bytes() == before, "adding a note must not touch the label file"
    assert json.loads(notes.read_text(encoding="utf-8").splitlines()[0])["id"] == expert_ids[0]


def test_the_sets_have_enough_expert_fails():
    cal, blind = labels.split_items("calibration"), labels.split_items("blind")
    v = labels.expert_labels()[0]
    assert (len(cal), len(blind)) == (10, 20)
    assert sum(v[r["id"]] == "fail" for r in cal) >= 3 and sum(v[r["id"]] == "fail" for r in blind) >= 6


def test_checkpoint_1():
    """Calibration done: the file holds the 10 labels and results.md says how many you matched."""
    body = section("Calibration")
    assert PLACEHOLDER not in body
    mine = {r["id"]: r["label"] for r in labels.read_jsonl(HERE / "my_labels_calibration.jsonl")}
    assert set(mine) == {r["id"] for r in labels.split_items("calibration")}
    v = labels.expert_labels()[0]
    matched = sum(mine[i] == v[i] for i in mine)
    hit = re.search(r"^Matched the expert on (\d+) of 10", body, flags=re.M)
    assert hit and int(hit.group(1)) == matched, f"write the line 'Matched the expert on {matched} of 10 calibration labels'"


def test_checkpoint_2():
    """Blind labels scored: the cells and kappa in results.md equal your cohen_kappa on your labels."""
    test_known_table()
    test_undefined_when_pe_is_one()
    test_needs_reread_rule()
    m = learner()
    body = section("Blind labels and kappa")
    assert PLACEHOLDER not in body
    items = labels.split_items("blind")
    ids = [r["id"] for r in items]
    v = labels.expert_labels()[0]
    mine = {r["id"]: r["label"] for r in labels.read_jsonl(HERE / "my_labels_blind.jsonl")}
    a, e = [mine[i] for i in ids], [v[i] for i in ids]
    k = m.cohen_kappa(a, e)
    hit = re.search(r"^Kappa: (-?[\d.]+)", body, flags=re.M)
    assert hit and k is not None and abs(float(hit.group(1)) - k) <= 0.005, "write the line 'Kappa: N' from the kappa command"
    cells = m.agreement_cells(a, e)
    got = re.search(r"^Cells: (\d+), (\d+), (\d+), (\d+)", body, flags=re.M)
    assert got and tuple(map(int, got.groups())) == (cells["both_pass"], cells["mine_pass_expert_fail"], cells["mine_fail_expert_pass"], cells["both_fail"])
    notes = {json.loads(l)["id"] for l in (HERE / "reconcile.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    assert set(m.disagreement_ids(ids, a, e)) <= notes, "write a reconciliation note for each disagreement (label --note ID TEXT)"
    assert "practice size" in body, "say in one sentence why 30 labels is a practice size and not a production one"
