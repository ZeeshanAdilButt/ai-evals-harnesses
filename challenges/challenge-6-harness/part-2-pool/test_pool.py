import json
import threading
import time

import pytest

from evalkit.providers import ReplayProvider
from evalkit.replay import Store
from evalkit.suites import read_jsonl


def test_never_more_than_workers_running(impl2):
    lock = threading.Lock()
    state = {"now": 0, "max": 0}

    def task(timeout_s):
        with lock:
            state["now"] += 1
            state["max"] = max(state["max"], state["now"])
        time.sleep(0.02)
        with lock:
            state["now"] -= 1
        return "done"

    results = impl2.run_pool([task] * 12, 3, 5.0)
    assert results == ["done"] * 12
    assert 2 <= state["max"] <= 3  # several run at once, never more than the limit


def test_results_come_back_in_task_order_and_get_the_timeout(impl2):
    tasks = [(lambda t, i=i: (i, t)) for i in range(10)]
    assert impl2.run_pool(tasks, 4, 7.5) == [(i, 7.5) for i in range(10)]


def test_timeout_frees_worker(impl2):
    def slow(timeout_s):
        raise TimeoutError("the call hit its own limit")

    results = impl2.run_pool([slow, lambda t: "next task ran"], 1, 1.0)
    assert isinstance(results[0], TimeoutError)
    assert results[1] == "next task ran"  # one worker only: the second task could run, so the first freed it


def test_the_provider_raises_the_timeout_not_the_waiter(pool_tickets):
    """Shipped behaviour: the call raises TimeoutError at its own limit. Recorded latency 1792 ms x 1 is over 0.5 s."""
    from product import triage

    store = Store.load("triage")
    request = triage.build_request("A", pool_tickets[0]["text"])
    provider = ReplayProvider("triage", simulate_latency=1.0, sleep=lambda s: None)
    started = store.lookup(request["key"], 1)["latency_ms"] / 1000
    assert started > 0.5
    with pytest.raises(TimeoutError):
        provider.complete(request, 1, timeout_s=0.5)
    assert provider.complete(request, 1, timeout_s=60)["trial"] == 1


def test_eight_workers_write_400_whole_lines(impl2, tmp_path):
    path = tmp_path / "trials.jsonl"
    writer = impl2.SafeWriter(path)
    payload = "x" * 3000

    def work(worker):
        for n in range(50):
            writer.write({"id": f"{worker}-{n}", "payload": payload})

    threads = [threading.Thread(target=work, args=(w,)) for w in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    writer.close()
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 400
    ids = {json.loads(l)["id"] for l in lines}  # every line parses: none was cut in two
    assert len(ids) == 400
    assert writer.lines == 400


def test_pool_run_equals_reference_run(impl2, reference, tmp_path):
    from evalkit import engine

    mine = engine.run_suite("pool400", "A", impl=impl2, workers=8, out=tmp_path / "mine")
    ref = engine.run_suite("pool400", "A", impl=reference, workers=1, out=tmp_path / "ref")
    assert mine["records"] == ref["records"] == 400
    assert read_jsonl(tmp_path / "mine" / "trials.jsonl") == read_jsonl(tmp_path / "ref" / "trials.jsonl")
