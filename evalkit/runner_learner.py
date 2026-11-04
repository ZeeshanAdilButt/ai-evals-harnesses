"""The learner's runner: loads the challenge-6 scripts and presents them as one `impl` for the engine.

Shipped and finished. Part 1 gives the registry, the cache and the diff; part 2 the pool and the safe
writer; part 3 the retries and resume. `load_impl(learner=[...])` takes the named parts from the learner's
scripts and everything else from the reference runner, so a test for part 1 can run a whole suite before
parts 2 and 3 exist. `load_impl()` takes all three from the learner (this is what `check-runner` uses).
When a gap is not filled yet, the script raises NotImplementedError("YOUR TURN: ...").
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

from evalkit import engine, runner_reference

HERE = Path(__file__).resolve().parents[1] / "challenges" / "challenge-6-harness"
PARTS = {
    "part-1-registry-cache-diff": "registry_cache_diff",
    "part-2-pool": "pool",
    "part-3-retries-and-resume": "retries_resume",
}


def load_part(folder: str):
    name = PARTS[folder]
    spec = importlib.util.spec_from_file_location(f"learner_{name}", HERE / folder / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_impl(learner=None) -> types.SimpleNamespace:
    """learner: part folder names taken from the learner's scripts (default: all three); "reference": none."""
    if learner == "reference":
        return runner_reference_impl()
    chosen = set(PARTS) if learner is None else set(learner)
    ref = runner_reference
    p1 = load_part("part-1-registry-cache-diff") if "part-1-registry-cache-diff" in chosen else None
    p2 = load_part("part-2-pool") if "part-2-pool" in chosen else None
    p3 = load_part("part-3-retries-and-resume") if "part-3-retries-and-resume" in chosen else None
    if p1:
        p1.register_shipped_graders()
    one, two, three = p1 or ref, p2 or ref, p3 or ref
    return types.SimpleNamespace(
        get_grader=one.get_grader, register_grader=one.register_grader, UnknownGrader=one.UnknownGrader,
        CachedProvider=one.CachedProvider, diff_runs=one.diff_runs,
        SafeWriter=two.SafeWriter, run_pool=two.run_pool,
        is_retryable=three.is_retryable, backoff_delay=three.backoff_delay,
        run_with_retries=three.run_with_retries, resume_skip=three.resume_skip,
        MAX_ATTEMPTS=getattr(three, "MAX_ATTEMPTS", 5),
    )


def runner_reference_impl():
    return runner_reference


def run_suite(suite, variant, **kwargs):
    return engine.run_suite(suite, variant, impl=load_impl(), **kwargs)
