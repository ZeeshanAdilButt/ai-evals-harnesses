"""Challenge 6, part 2: a bounded pool, a timeout on the call, and a writer that keeps every line whole.

Fill the two YOUR TURN gaps:
  1. run_pool(tasks, workers, timeout_s)   at most `workers` calls at once
  2. SafeWriter.write(record)              one whole JSON line per record, from any thread

Run it:  python challenges/challenge-6-harness/part-2-pool/pool.py
"""
from __future__ import annotations

import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


class SafeWriter:
    """Appends records to a JSONL file. Several threads may call write at the same time."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self.path, "a", encoding="utf-8")
        self._lock = threading.Lock()  # a lock lets one thread at a time through
        self.lines = 0

    def write(self, record):
        """Write `record` as one JSON line (sorted keys) and flush it. Count it in self.lines."""
        raise NotImplementedError("YOUR TURN: build the line, then write and flush it while holding self._lock")

    def close(self):
        with self._lock:
            if not self._file.closed:
                self._file.close()


def run_pool(tasks, workers, timeout_s):
    """Run `task(timeout_s)` for every task in `tasks`, never more than `workers` at once.

    The timeout is not a wait on the future. A Python thread cannot be stopped from outside, so
    future.result(timeout=...) would only stop waiting while the thread kept its worker. The call itself
    (the provider) raises TimeoutError at its limit; that frees the worker for the next task.

    Return one item per task, in task order: what the task returned, or the exception it raised.
    """
    raise NotImplementedError("YOUR TURN: a ThreadPoolExecutor(max_workers=workers); submit each task with timeout_s; collect in order")


def main():
    """Run the 400-ticket pool suite with 1 worker and with 8, simulated latency 0.05, and check the lines."""
    from evalkit import engine
    from evalkit.replay import Store
    from evalkit.runner_learner import load_impl
    from evalkit.suites import load_cases, load_suite, read_jsonl
    from product import triage

    impl = load_impl(learner=["part-2-pool"])
    cases = load_cases(load_suite("pool400")["part"][0])
    store = Store.load("triage")
    lat = [store.lookup(triage.build_request("A", c["text"])["key"], 1)["latency_ms"] for c in cases]
    mean_s = sum(lat) / len(lat) / 1000
    print(f"calls {len(cases)}, mean recorded latency {mean_s:.3f} s")
    for w in (1, 8):
        s = engine.run_suite("pool400", "A", impl=impl, workers=w, simulate_latency=0.05)
        whole = len(read_jsonl(s["out"] + "/trials.jsonl"))
        est = len(cases) * mean_s * 0.05 / w
        print(f"workers {w}: {whole} whole lines, measured {s['elapsed_s']:.1f} s, formula {est:.1f} s")


if __name__ == "__main__":
    main()
