"""Shared by the challenge 6 tests.

Each part's tests use the learner's script for that part and the reference runner for the other two parts, so a
part can be tested before the next one is written. `python -m evalkit check-runner` runs all three parts together.
Set EVALKIT_RUNNER=reference to run every test against the reference runner (the tests must pass there too).
"""
import json
import os
from pathlib import Path

import pytest

from evalkit.runner_learner import load_impl

ROOT = Path(__file__).resolve().parents[2]
P1, P2, P3 = "part-1-registry-cache-diff", "part-2-pool", "part-3-retries-and-resume"


def impl_for(parts):
    if os.environ.get("EVALKIT_RUNNER") == "reference":
        return load_impl("reference")
    return load_impl(learner=parts)


@pytest.fixture
def impl1():
    return impl_for([P1])


@pytest.fixture
def impl2():
    return impl_for([P2])


@pytest.fixture
def impl3():
    return impl_for([P3])


@pytest.fixture
def impl_all():
    return impl_for([P1, P2, P3])


@pytest.fixture
def reference():
    return load_impl("reference")


@pytest.fixture
def pool_tickets():
    rows = [json.loads(l) for l in (ROOT / "datasets/pool/tickets.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    return rows


@pytest.fixture
def make_suite(tmp_path):
    """make_suite(cases, trials=1) writes a tiny triage suite over the given cases and returns it as a dict."""
    def build(cases, trials=1):
        data = tmp_path / "cases.jsonl"
        data.write_text("".join(json.dumps(c) + "\n" for c in cases), encoding="utf-8")
        return {"name": "tiny", "part": [{"feature": "triage", "dataset": str(data), "trials": trials, "graders": ["schema", "match"]}]}
    return build
