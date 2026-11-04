"""Providers: replay (the default), the seeded fake that fails on purpose, and a live stub.

Every provider has one method, `complete(request, trial, timeout_s=None)`, and returns the recorded
line as a dict. A provider never opens a network connection in this file. `LiveProvider` exists only
to say so: live recording is the author's tool (tools/record.py) and needs `--live` and a key.
"""
from __future__ import annotations

import random
import threading
import time

from evalkit.replay import ReplayMiss, Store  # noqa: F401  (ReplayMiss is re-exported for callers)


class ProviderError(Exception):
    """An error a provider can return. `status` is the HTTP-style code."""

    status = 500

    def __init__(self, message: str = "", retry_after: float | None = None):
        super().__init__(message or self.__class__.__name__)
        self.retry_after = retry_after


class RateLimitError(ProviderError):
    """429: too many calls too fast. Temporary; `retry_after` says how long to wait, in seconds."""

    status = 429


class ServerError(ProviderError):
    """5xx: the provider failed. Temporary."""

    status = 503


class BadRequestError(ProviderError):
    """400: the request itself is wrong. The same request fails the same way every time."""

    status = 400


class RateLimiter:
    """A simulated rate limit: at most `per_second` calls start in any one second of real time."""

    def __init__(self, per_second: float, clock=time.monotonic):
        self.per_second = per_second
        self.clock = clock
        self.stamps: list[float] = []
        self.refused = 0
        self._lock = threading.Lock()

    def check(self) -> None:
        now = self.clock()
        with self._lock:
            self.stamps = [t for t in self.stamps if now - t < 1.0]
            if len(self.stamps) >= self.per_second:
                self.refused += 1
                wait = 1.0 - (now - self.stamps[0])
                raise RateLimitError("simulated rate limit", retry_after=round(max(wait, 0.05), 2))
            self.stamps.append(now)


class ReplayProvider:
    """Answers from the recordings. A request that was never recorded raises ReplayMiss.

    lookup: a function (request, trial) -> recorded line. The default is the Store of the feature;
        the runner passes the learner's CachedProvider.complete here, so a run uses the learner's cache.
    simulate_latency: F > 0 makes each call sleep F times the recorded latency (6.6 uses 0.05).
        Trials 2 to 5 carry no valid latency, so they sleep F times the latency of trial 1 of the same request.
    limiter: a RateLimiter that refuses calls above its rate (simulated).
    The timeout is enforced here, on the call: when the simulated time is longer than `timeout_s`,
    the call sleeps to the limit and raises TimeoutError. A thread cannot be stopped from outside.
    """

    def __init__(self, feature: str, lookup=None, simulate_latency: float = 0.0,
                 limiter: RateLimiter | None = None, sleep=time.sleep):
        self.feature = feature
        self.store = Store.load(feature) if lookup is None else None
        self._lookup = lookup or (lambda request, trial: self.store.lookup(request["key"], trial))
        self.simulate_latency = simulate_latency
        self.limiter = limiter
        self.sleep = sleep
        self.attempts = 0
        self._count_lock = threading.Lock()

    def _recorded_latency_ms(self, request: dict, rec: dict) -> float:
        if rec.get("latency_ms") is not None:
            return rec["latency_ms"]
        try:
            return self._lookup(request, 1).get("latency_ms") or 0
        except ReplayMiss:
            return 0

    def _before(self, request: dict, trial: int) -> None:
        """Hook for subclasses that fail on purpose."""

    def complete(self, request: dict, trial: int, timeout_s: float | None = None) -> dict:
        with self._count_lock:
            self.attempts += 1
        if self.limiter is not None:
            self.limiter.check()
        self._before(request, trial)
        rec = self._lookup(request, trial)
        if self.simulate_latency > 0:
            seconds = self.simulate_latency * self._recorded_latency_ms(request, rec) / 1000.0
            if timeout_s is not None and seconds > timeout_s:
                self.sleep(timeout_s)
                raise TimeoutError(f"call took longer than {timeout_s} s")
            self.sleep(seconds)
        return rec


class FakeProvider(ReplayProvider):
    """Recorded outputs plus failures on FIRST attempts only, so a correct runner makes a known number of retries.

    The first attempts are counted from 0 in the order they arrive. First attempt i raises a rate-limit
    error with a `retry_after` when i mod 5 = 4, and a timeout when i mod 50 = 12 (the two never meet).
    On 400 trials that is 80 + 8 = 88 failures, and every retry succeeds. `seed` picks the retry_after
    values (1 or 2 seconds) so the same seed gives the same run.
    """

    def __init__(self, feature: str, seed: int = 7, **kwargs):
        super().__init__(feature, **kwargs)
        self.seed = seed
        self._seen: set = set()
        self._first_index = 0
        self.rate_limits = 0
        self.timeouts = 0
        self._fake_lock = threading.Lock()

    def _before(self, request: dict, trial: int) -> None:
        ident = (request["key"], trial)
        with self._fake_lock:
            if ident in self._seen:
                return
            self._seen.add(ident)
            i = self._first_index
            self._first_index += 1
            if i % 5 == 4:
                self.rate_limits += 1
                raise RateLimitError("fake rate limit", retry_after=random.Random(self.seed * 1000 + i).choice([1, 2]))
            if i % 50 == 12:
                self.timeouts += 1
                raise TimeoutError("fake timeout")


class LiveProvider:
    """Not available in replay. Live calls need `--live`, a key in .env, a printed cost and a `y`."""

    def __init__(self, *args, **kwargs):
        raise RuntimeError("live calls are not part of the course runner; use tools/record.py with --live (author only)")
