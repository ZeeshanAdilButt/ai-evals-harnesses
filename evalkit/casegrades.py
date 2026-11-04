"""Shipped: the recorded triage grades per case, for the module 7 scripts and tools.

A trial passes when category and urgent flag are both right (the `match` grader), read from the recordings
with `evalkit.replay`. Nothing here calls a model; a request with no recording raises ReplayMiss."""
from __future__ import annotations

import json
from pathlib import Path

from evalkit.graders.triage import predicted
from evalkit.replay import Store
from product import triage

ROOT = Path(__file__).resolve().parents[1]
CANON = ROOT / "datasets" / "canonical" / "v1" / "cases.jsonl"


def canonical_cases() -> list[dict]:
    return [json.loads(l) for l in CANON.read_text(encoding="utf-8").splitlines() if l.strip()]


def grade_output(output: str, expected: dict) -> int:
    cat, urgent = predicted(output)
    return 1 if (cat == expected["category"] and urgent is expected["urgent"]) else 0


_STORE = None
_CACHE: dict = {}


def triage_store() -> Store:
    global _STORE
    if _STORE is None:
        _STORE = Store.load("triage")
    return _STORE


def triage_trials(variant: str, trials=(1, 2, 3, 4, 5), cases=None, store=None) -> dict:
    """{case_id: [grade for each trial]} for canonical v1 (or the given cases), grades 1 or 0.
    The default call is remembered for the life of the process (the recordings do not change while it runs)."""
    memo = (variant, tuple(trials)) if cases is None and store is None else None
    if memo and memo in _CACHE:
        return {k: list(v) for k, v in _CACHE[memo].items()}
    store = store or triage_store()
    out = {}
    for c in cases or canonical_cases():
        key = triage.build_request(variant, c["text"])["key"]
        out[c["id"]] = [grade_output(store.lookup(key, t)["output"], c["expected"]) for t in trials]
    if memo:
        _CACHE[memo] = {k: list(v) for k, v in out.items()}
    return out
