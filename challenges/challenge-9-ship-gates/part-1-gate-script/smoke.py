"""Challenge 9, part 1: the smoke suite. A subset of `full` that a pull request can run in seconds and that still holds every must-pass case.

    python challenges/challenge-9-ship-gates/part-1-gate-script/smoke.py        writes suites/smoke.toml from select_smoke

Fill the one YOUR TURN gap: select_smoke(full_cases).
Must-pass agent tasks are not in smoke: they need five trials of a tool loop and run in `full` only, so smoke has a triage part and a reply part.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CATEGORIES = ("billing", "delivery", "refund", "account", "product")
PER_CATEGORY = 4


def select_smoke(full_cases):
    """full_cases: the cases of canonical v1 that `full` runs for triage and reply (dicts with id, split, expected, must_pass).
    Return the sorted list of case ids for suites/smoke.toml: every case tagged must_pass, plus the first four dev cases (by id) of each
    category, so each category is still looked at. No agent task ids: those are not canonical v1 cases."""
    raise NotImplementedError("YOUR TURN: every must_pass case, plus four dev cases per category; return sorted ids")


def full_cases() -> list:
    path = ROOT / "datasets" / "canonical" / "v1" / "cases.jsonl"
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def write_smoke(ids: list) -> Path:
    """Write suites/smoke.toml: the triage and reply parts of `full` for these cases, five trials. Given."""
    cases = ", ".join(f'"{i}"' for i in ids)
    body = (f'name = "smoke"\ndescription = "A subset of full: every must-pass case and four dev cases per category, five trials. Built by smoke.py in 9.7."\n\n'
            f'[[part]]\nfeature = "triage"\ndataset = "datasets/canonical/v1/cases.jsonl"\ntrials = 5\ncases = [{cases}]\ngraders = ["schema", "match"]\n\n'
            f'[[part]]\nfeature = "reply"\ndataset = "datasets/canonical/v1/cases.jsonl"\ntrials = 5\ncases = [{cases}]\ngraders = ["reply_facts"]\n')
    out = ROOT / "suites" / "smoke.toml"
    out.write_text(body, encoding="utf-8")
    return out


def main():
    ids = select_smoke(full_cases())
    try:
        out = write_smoke(ids)
    except OSError as err:
        print(err)
        return 1
    print(f"smoke: {len(ids)} cases written to {out.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
