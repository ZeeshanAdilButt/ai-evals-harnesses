"""Challenge 6, part 1: the grader registry, the replay cache and the diff report.

Read the shells first (they are finished), then fill the three YOUR TURN gaps:
  1. register_grader / get_grader   the dictionary behind the decorator
  2. CachedProvider.complete        a hit returns the recorded line, a miss raises ReplayMiss
  3. diff_runs                      the per-case table of cases whose result changed

Run it:  python challenges/challenge-6-harness/part-1-registry-cache-diff/registry_cache_diff.py
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from evalkit.graders.shipped import SHIPPED  # noqa: E402
from evalkit.replay import ReplayMiss, Store  # noqa: E402


class UnknownGrader(Exception):
    """A suite names a grader that was never registered. An exception is an error with a name."""


# ---- 1. the registry -------------------------------------------------------------------------
# A decorator such as @register_grader("exact") adds a function to a dictionary under a name.
_GRADERS: dict = {}


def register_grader(name):
    def decorator(fn):
        raise NotImplementedError("YOUR TURN: store fn in _GRADERS under name")
        return fn
    return decorator


def get_grader(name):
    raise NotImplementedError("YOUR TURN: return the grader called name, or raise UnknownGrader('no grader named <name>')")


def register_shipped_graders():
    """Register the shipped graders by name. The line `register_grader("exact")(fn)` does what
    the decorator form `@register_grader("exact")` above a function does."""
    for name, fn in SHIPPED.items():
        register_grader(name)(fn)


# ---- 2. the cache ----------------------------------------------------------------------------
class CachedProvider:
    """A class groups a method with the data it uses. This one is the replay cache of one feature."""

    def __init__(self, feature, store=None):
        self.feature = feature
        self.store = store if store is not None else Store.load(feature)
        self.hits = 0
        self.misses = 0
        self._lock = threading.Lock()  # many workers share one cache (part 2)

    def complete(self, request, trial):
        """Return the recorded line for (request["key"], trial). Count a hit or a miss.
        A request that was never recorded raises ReplayMiss; nothing here ever calls a model."""
        raise NotImplementedError("YOUR TURN: look the key and trial up in self.store; count hits and misses under self._lock")


# ---- 3. the diff -----------------------------------------------------------------------------
def diff_runs(run_a, run_b):
    """Compare two runs. Each run is a list of trial records (the lines of trials.jsonl).

    A case's score is the mean of its trial passes. Return one dict per case whose score differs, sorted by
    (feature, case_id), with the keys: feature, case_id, a_score, b_score, direction ("to_pass" when B
    scores higher, "to_fail" when B scores lower), grades_a, grades_b (the first trial's grades),
    output_a, output_b.
    """
    raise NotImplementedError("YOUR TURN: group each run by (feature, case_id), average 'passed', keep the cases that differ")


# ---- the runnable part ------------------------------------------------------------------------
def main():
    """Run v1-triage for A and B with your registry and cache, then diff them."""
    from evalkit import engine
    from evalkit.runner_learner import load_impl
    from evalkit.suites import read_trials

    impl = load_impl(learner=["part-1-registry-cache-diff"])
    ra = engine.run_suite("v1-triage", "A", impl=impl)
    rb = engine.run_suite("v1-triage", "B", impl=impl)
    print(f"A: {ra['passed']} of {ra['records']} passed;  B: {rb['passed']} of {rb['records']} passed")
    rows = diff_runs(read_trials(ra["out"]), read_trials(rb["out"]))
    to_pass = sum(r["direction"] == "to_pass" for r in rows)
    print(f"flipped cases: {len(rows)} (to pass under B: {to_pass}, to fail under B: {len(rows) - to_pass})")
    for r in rows:
        print(f"  {r['case_id']}  {r['direction']}")


if __name__ == "__main__":
    main()
