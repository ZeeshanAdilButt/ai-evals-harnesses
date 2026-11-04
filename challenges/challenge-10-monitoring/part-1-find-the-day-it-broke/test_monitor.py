"""Challenge 10, part 1. One test per checkpoint. They fail on the starter (the functions raise NotImplementedError). Replay only.

Checkpoint 1 compares your week table with the shipped one (datasets/reference_grades/monitor.json) within 0.005. Checkpoint 2 uses two small
constructed weeks and then the recorded week. Checkpoint 3 needs the files `select-traces` and `dataset freeze --name my-v2` write."""
import hashlib
import importlib.util
import json
import re
from pathlib import Path

from evalkit import traffic

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PLACEHOLDER = "(fill in)"


def load(name):
    spec = importlib.util.spec_from_file_location(f"learner_{name}", HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def shipped():
    return json.loads((ROOT / "datasets" / "reference_grades" / "monitor.json").read_text(encoding="utf-8"))


def section(title_start):
    text = (HERE / "results.md").read_text(encoding="utf-8")
    for p in re.split(r"^## ", text, flags=re.M):
        if p.startswith(title_start):
            return p
    raise AssertionError(f"results.md has no section that starts with '## {title_start}'")


_WEEK = []


def the_week():
    if not _WEEK:
        rows = traffic.week(refund_only=False)
        gone = traffic.missing(rows)
        assert not gone, f"not recorded yet: {len(gone)} refund traces have no judge verdict; ask the author to run the recording commands"
        _WEEK.append(rows)
    return _WEEK[0]


def fixture_week(mixed_day6, n_mixed=40, n_english=100):
    judged = []
    for day in range(1, 8):
        for i in range(n_english):
            judged.append({"id": f"e{day}-{i}", "day": day, "tone": "calm", "language": "english", "length": "normal", "passed": i % 10 != 0})
        p_mixed = mixed_day6 if day == 6 else 0.9
        k = round(p_mixed * n_mixed)
        for i in range(n_mixed):
            judged.append({"id": f"m{day}-{i}", "day": day, "tone": "calm", "language": "mixed", "length": "normal", "passed": i < k})
    return judged


def test_checkpoint_1():
    m = load("monitor")
    judged = traffic.judged(the_week())
    table = m.daily_rates(judged, ["day"])
    want = shipped()["by_day"]
    assert [r["cell"] for r in table] == [(int(d),) for d in sorted(want, key=int)]
    for r in table:
        w = want[str(r["cell"][0])]
        assert r["n"] == w["n"], f"day {r['cell'][0]}: n"
        assert abs(r["rate"] - w["rate"]) <= 0.005 and abs(r["lo"] - w["lo"]) <= 0.005 and abs(r["hi"] - w["hi"]) <= 0.005
    body = section("Checkpoint 1")
    assert PLACEHOLDER not in body
    assert (HERE / "chart.svg").exists(), "save the chart as chart.svg"
    for r in table:
        assert re.search(rf"^\| {r['cell'][0]} \| {r['n']} \|", body, flags=re.M), f"the week table in results.md needs the row for day {r['cell'][0]}"


def test_planted_break_is_flagged_on_the_right_cell():
    m = load("monitor")
    table = m.daily_rates(fixture_week(mixed_day6=0.3), ["day", "language"])
    assert m.flag_cells(table, [1, 2, 3, 4], m.RULE) == [(6, "mixed")]


def test_quiet_week_with_small_samples_flags_nothing():
    m = load("monitor")
    table = m.daily_rates(fixture_week(mixed_day6=0.5, n_mixed=6, n_english=8), ["day", "language"])
    assert m.flag_cells(table, [1, 2, 3, 4], m.RULE) == [], "six replies is too few to call a drop (10.5)"


def test_daily_rates_is_a_plain_count():
    m = load("monitor")
    rows = [{"day": 1, "passed": True}, {"day": 1, "passed": False}, {"day": 2, "passed": True}]
    t = m.daily_rates(rows, ["day"])
    assert [(r["cell"], r["n"], r["passes"]) for r in t] == [((1,), 2, 1), ((2,), 1, 1)]
    assert abs(t[0]["rate"] - 0.5) < 1e-9 and t[0]["lo"] <= 0.5 <= t[0]["hi"]
    assert t[1]["hi"] == 1.0, "one pass of one: the shipped interval helper applies the rule of three at the edge"


def test_checkpoint_2():
    test_planted_break_is_flagged_on_the_right_cell()
    test_quiet_week_with_small_samples_flags_nothing()
    m = load("monitor")
    judged = traffic.judged(the_week())
    cells = m.flag_cells(m.daily_rates(judged, ["day", "language"]), [1, 2, 3, 4], m.RULE)
    want = [tuple(x) for x in shipped()["flagged_language"]]
    assert cells == want, f"on the recorded week the flagged cells must equal the shipped ones {want}"
    body = section("Checkpoint 2")
    assert PLACEHOLDER not in body
    assert re.search(r"^Flagged: ", body, flags=re.M) and re.search(r"^Rule: ", body, flags=re.M)
    assert re.search(rf"^Break: day {shipped()['break_day']}, slice {shipped()['break_slice']}", body, flags=re.M)


def test_checkpoint_3():
    rule = load("rule")
    week = the_week()
    flagged = {(d, v) for d, v in shipped()["flagged_language"]}
    chosen = [r for r in week if rule.select_rule(dict(r))]
    assert chosen, "the rule selects nothing"
    assert all(r["category"] == "refund" and (r["day"], r["language"]) in flagged for r in chosen), "select refund traces of the flagged cells only"
    assert all("@" not in r["text"] for r in chosen), "selected traces must be the scrubbed text"
    sel = [json.loads(l) for l in (ROOT / "datasets" / "mine" / "trace_selection.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert {r["id"] for r in sel} == {r["id"] for r in chosen}, "run `python -m evalkit select-traces --rule ...` with this rule.py"
    out = ROOT / "datasets" / "mine" / "my-v2"
    body = (out / "cases.jsonl").read_bytes()
    assert hashlib.sha256(body).hexdigest() == (out / "HASH").read_text(encoding="utf-8").strip(), "the hash must match the frozen file"
    assert {json.loads(l)["id"] for l in body.decode("utf-8").splitlines()} == {r["id"] for r in chosen}, "the frozen file holds only the selected ids"
    text = section("Checkpoint 3")
    assert PLACEHOLDER not in text
    canon = {json.loads(l)["id"] for l in (ROOT / "datasets/canonical/v2/additions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    ids = {r["id"] for r in chosen}
    for label, value in (("Selected", len(ids)), ("In both", len(ids & canon)), ("Missed", len(canon - ids)), ("Extra", len(ids - canon))):
        assert re.search(rf"^{label}: {value}\b", text, flags=re.M), f"write the line '{label}: {value}' from `dataset compare --name my-v2`"
    assert re.search(r"^Hash: " + hashlib.sha256(body).hexdigest()[:12], text, flags=re.M)
