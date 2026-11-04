"""The reference runner: the solved version of everything the learner builds in challenge 6.

`python -m evalkit run --runner reference ...` uses this file. The learner's own runner is the three
scripts under challenges/challenge-6-harness/, loaded by evalkit.runner_learner. Both are checked by the
same tests (`python -m evalkit check-runner`).
"""
from __future__ import annotations

import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from evalkit import engine
from evalkit.graders.shipped import SHIPPED
from evalkit.replay import ReplayMiss, Store

MAX_ATTEMPTS = 5
MAX_WAIT_S = 30.0


class UnknownGrader(Exception):
    """A suite names a grader that was never registered."""


# --- part 1: registry, cache, diff ------------------------------------------------------------

_GRADERS: dict = {}


def register_grader(name):
    def decorator(fn):
        _GRADERS[name] = fn
        return fn
    return decorator


def get_grader(name):
    try:
        return _GRADERS[name]
    except KeyError:
        raise UnknownGrader(f"no grader named {name}") from None


for _name, _fn in SHIPPED.items():
    register_grader(_name)(_fn)


class CachedProvider:
    """The replay cache: a hit returns the recorded line, a miss raises ReplayMiss. Never a live call."""

    def __init__(self, feature, store=None):
        self.feature = feature
        self.store = store if store is not None else Store.load(feature)
        self.hits = 0
        self.misses = 0
        self._lock = threading.Lock()

    def complete(self, request, trial):
        try:
            line = self.store.lookup(request["key"], trial)
        except ReplayMiss:
            with self._lock:
                self.misses += 1
            raise
        with self._lock:
            self.hits += 1
        return line


def diff_runs(run_a, run_b):
    """Per-case diff of two runs (lists of trial records). Returns the cases whose score changed.

    A case's score is the mean of its trial passes. Each row: feature, case_id, a_score, b_score,
    direction ("to_pass" when B scores higher, "to_fail" when lower), and the first trial's grades.
    """
    def collect(records):
        by_case = {}
        for r in records:
            by_case.setdefault((r["feature"], r["case_id"]), []).append(r)
        return by_case

    a, b = collect(run_a), collect(run_b)
    rows = []
    for key in sorted(set(a) & set(b)):
        sa = sum(bool(r.get("passed")) for r in a[key]) / len(a[key])
        sb = sum(bool(r.get("passed")) for r in b[key]) / len(b[key])
        if sa != sb:
            first_a = min(a[key], key=lambda r: r["trial"])
            first_b = min(b[key], key=lambda r: r["trial"])
            rows.append({"feature": key[0], "case_id": key[1], "a_score": sa, "b_score": sb,
                         "direction": "to_pass" if sb > sa else "to_fail",
                         "grades_a": first_a.get("grades", {}), "grades_b": first_b.get("grades", {}),
                         "output_a": first_a.get("output"), "output_b": first_b.get("output")})
    return rows


# --- part 2: the pool ---------------------------------------------------------------------------

class SafeWriter:
    """Appends one JSON line per record. Many threads may call write; each line stays whole."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self.path, "a", encoding="utf-8")
        self._lock = threading.Lock()
        self.lines = 0

    def write(self, record):
        line = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
        with self._lock:
            self._file.write(line)
            self._file.flush()
            self.lines += 1

    def close(self):
        with self._lock:
            if not self._file.closed:
                self._file.close()


def run_pool(tasks, workers, timeout_s):
    """Run task(timeout_s) for every task with at most `workers` at once.

    The timeout is passed to the call, which raises TimeoutError at its own limit and so frees its worker;
    future.result(timeout=...) would only stop waiting while the thread kept running.
    Returns one item per task, in task order: the return value, or the exception the task raised.
    """
    def guarded(task):
        try:
            return task(timeout_s)
        except Exception as error:  # noqa: BLE001  (an error is a result; the caller decides)
            return error

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(guarded, t) for t in tasks]
        return [f.result() for f in futures]


# --- part 3: retries and resume -----------------------------------------------------------------

def is_retryable(error):
    """A retry can fix a rate limit (429), a timeout and a 5xx error. It cannot fix a 400, an auth error or a miss."""
    if isinstance(error, TimeoutError):
        return True
    if isinstance(error, ReplayMiss):
        return False
    status = getattr(error, "status", None)
    return status == 429 or (status is not None and status >= 500)


def backoff_delay(attempt, retry_after=None):
    """Seconds to wait before retry number `attempt` (0 for the first retry): 1, 2, 4, 8 ... capped at 30,
    and never less than the provider's retry_after."""
    return max(min(MAX_WAIT_S, 1.0 * 2 ** attempt), retry_after or 0)


def run_with_retries(call, sleep):
    """Call `call()` up to five times. Returns (value, errors): errors are the retried failures, in order.
    A non-retryable error is raised at once; after the fifth failed attempt the last error is raised."""
    errors = []
    for attempt in range(MAX_ATTEMPTS):
        try:
            return call(), errors
        except Exception as error:  # noqa: BLE001
            if not is_retryable(error) or attempt == MAX_ATTEMPTS - 1:
                raise
            errors.append(error)
            sleep(backoff_delay(attempt, getattr(error, "retry_after", None)))
    raise AssertionError("unreachable")


def resume_skip(done_keys, tasks):
    """Tasks start with their key (case_id, variant, trial). Keep the ones not finished yet, in order."""
    return [t for t in tasks if tuple(t[:3]) not in done_keys]


def run_suite(suite, variant, **kwargs):
    return engine.run_suite(suite, variant, impl=sys.modules[__name__], **kwargs)
