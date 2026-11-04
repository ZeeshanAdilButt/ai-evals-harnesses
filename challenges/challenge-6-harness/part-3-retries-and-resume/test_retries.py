import pytest

from evalkit.providers import BadRequestError, ProviderError, RateLimitError, ServerError
from evalkit.replay import ReplayMiss
from evalkit.suites import read_jsonl


class AuthError(ProviderError):
    status = 401


def flaky(failures, then="ok"):
    """A call that raises each error in `failures` in turn, then returns `then`. calls.count is the number of attempts."""
    queue = list(failures)

    def call():
        call.count += 1
        if queue:
            raise queue.pop(0)
        return then
    call.count = 0
    return call


def test_only_retryable_errors_retried(impl3):
    for error in (BadRequestError("invalid request"), AuthError("bad key"), ReplayMiss("k" * 12, "triage")):
        call = flaky([error])
        with pytest.raises(type(error)):
            impl3.run_with_retries(call, lambda s: None)
        assert call.count == 1, f"{type(error).__name__} must not be retried"
    for error in (RateLimitError("slow down", retry_after=2), TimeoutError("slow"), ServerError("503")):
        call = flaky([error])
        value, errors = impl3.run_with_retries(call, lambda s: None)
        assert value == "ok" and call.count == 2 and errors == [error]


def test_is_retryable(impl3):
    assert impl3.is_retryable(RateLimitError()) and impl3.is_retryable(TimeoutError()) and impl3.is_retryable(ServerError())
    assert not impl3.is_retryable(BadRequestError()) and not impl3.is_retryable(AuthError()) and not impl3.is_retryable(ValueError())


def test_backoff_doubles_and_caps(impl3):
    assert [impl3.backoff_delay(a) for a in range(7)] == [1, 2, 4, 8, 16, 30, 30]
    assert impl3.backoff_delay(0, retry_after=20) == 20  # never below what the provider asked
    assert impl3.backoff_delay(3, retry_after=3) == 8  # the backoff is already longer


def test_five_attempts_then_the_last_error(impl3):
    waits = []
    call = flaky([TimeoutError("t")] * 9)
    with pytest.raises(TimeoutError):
        impl3.run_with_retries(call, waits.append)
    assert call.count == 5 and waits == [1, 2, 4, 8]


def test_waits_follow_retry_after(impl3):
    waits = []
    value, errors = impl3.run_with_retries(flaky([RateLimitError("a", retry_after=5), RateLimitError("b", retry_after=1)]), waits.append)
    assert value == "ok" and len(errors) == 2 and waits == [5, 2]


def test_resume_skip(impl3):
    tasks = [("t1", "A", 1), ("t1", "A", 2), ("t2", "A", 1)]
    assert impl3.resume_skip({("t1", "A", 1)}, tasks) == [("t1", "A", 2), ("t2", "A", 1)]
    assert impl3.resume_skip(set(), tasks) == tasks


def fake_run(impl, out, **kw):
    from evalkit import engine

    return engine.run_suite("pool400", "A", impl=impl, provider="fake", workers=4, out=out, sleep=lambda s: None, **kw)


def test_fake_provider_retry_counts_match_seed(impl3, tmp_path):
    s = fake_run(impl3, tmp_path / "run")
    assert s["records"] == 400 and s["ok"] == 400 and s["failed"] == 0
    assert s["retries"] == 88 and s["attempts"] == 488
    assert s["retry_kinds"] == {"rate_limit": 80, "timeout": 8}


def test_resume_after_stop_at_312(impl3, tmp_path):
    from evalkit import engine

    out = tmp_path / "run"
    with pytest.raises(engine.SimulatedCrash):
        fake_run(impl3, out, stop_after=312)
    assert len(read_jsonl(out / "trials.jsonl")) == 312
    assert not (out / "report.md").exists()  # a crash writes no summary
    s = fake_run(impl3, out, resume=True)
    assert s["written_now"] == 88 and s["records"] == 400


def test_no_duplicate_keys_in_results(impl3, tmp_path):
    from evalkit import engine

    out = tmp_path / "run"
    with pytest.raises(engine.SimulatedCrash):
        fake_run(impl3, out, stop_after=312)
    fake_run(impl3, out, resume=True)
    keys = [(r["case_id"], r["variant"], r["trial"]) for r in read_jsonl(out / "trials.jsonl")]
    assert len(keys) == 400 and len(set(keys)) == 400
