import json

import pytest

from evalkit.replay import ReplayMiss, Store
from evalkit.suites import read_jsonl
from product import triage


def make_store():
    return Store("triage", {("k1", 1): {"key": "k1", "trial": 1, "output": "{}", "latency_ms": 5}})


def test_hit_and_miss(impl1):
    cache = impl1.CachedProvider("triage", store=make_store())
    assert cache.complete({"key": "k1"}, 1)["output"] == "{}"
    assert (cache.hits, cache.misses) == (1, 0)
    with pytest.raises(ReplayMiss):
        cache.complete({"key": "never-recorded"}, 1)
    with pytest.raises(ReplayMiss):
        cache.complete({"key": "k1"}, 2)  # the key is recorded, the trial is not
    assert (cache.hits, cache.misses) == (1, 2)


def test_run_records_replay_miss_and_continues(impl1, make_suite, pool_tickets, tmp_path):
    from evalkit import engine

    cases = [pool_tickets[0], {**pool_tickets[1], "id": "unseen", "text": "A ticket text nobody recorded."}, pool_tickets[2]]
    out = tmp_path / "run"
    summary = engine.run_suite(make_suite(cases), "A", impl=impl1, out=out)
    lines = read_jsonl(out / "trials.jsonl")
    assert [l["status"] for l in lines] == ["ok", "replay_miss", "ok"]
    assert summary["replay_miss"] == 1 and summary["ok"] == 2
    assert lines[1]["case_id"] == "unseen" and lines[1]["passed"] is False


def test_changed_word_misses_every_trial(impl1, monkeypatch, tmp_path):
    from evalkit import engine

    original = (triage.PRODUCT / triage.VARIANTS["A"]["triage_prompt"]).read_text(encoding="utf-8")
    changed = tmp_path / "triage_A_changed.md"
    changed.write_text(original.rstrip() + " Please.\n", encoding="utf-8")
    monkeypatch.setitem(triage.VARIANTS["A"], "triage_prompt", str(changed))
    out = tmp_path / "run"
    summary = engine.run_suite("v1-triage", "A", impl=impl1, out=out)
    assert summary["records"] == 160 and summary["replay_miss"] == 160 and summary["ok"] == 0
    assert all(json.loads(l)["status"] == "replay_miss" for l in (out / "trials.jsonl").read_text(encoding="utf-8").splitlines())
