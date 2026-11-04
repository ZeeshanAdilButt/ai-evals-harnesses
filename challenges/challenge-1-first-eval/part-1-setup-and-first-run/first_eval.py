"""Challenge 1, part 1: read three small functions, call them, and say which cases flipped.

Nothing here is a gap. The functions are finished; you read them, run them, and write what you find in
my_flips.json and results.md.

Run it (after you have run variants A and B):
    python challenges/challenge-1-first-eval/part-1-setup-and-first-run/first_eval.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from evalkit.suites import read_trials  # noqa: E402


def case_passed(trial_record):
    """A trial passes when it ran (status ok) and every grader said yes."""
    return trial_record["status"] == "ok" and all(trial_record["grades"].values())


def flipped_cases(trials_a, trials_b):
    """Case ids whose pass result differs between the two runs (one trial per case in this suite)."""
    a = {r["case_id"]: case_passed(r) for r in trials_a}
    b = {r["case_id"]: case_passed(r) for r in trials_b}
    return sorted(c for c in a if c in b and a[c] != b[c])


def flip_direction(case_id, trials_a, trials_b):
    """Going from A to B: "to_pass" if the case failed under A and passes under B, else "to_fail"."""
    a = {r["case_id"]: case_passed(r) for r in trials_a}
    b = {r["case_id"]: case_passed(r) for r in trials_b}
    if a[case_id] == b[case_id]:
        raise ValueError(f"{case_id} did not flip")
    return "to_pass" if b[case_id] else "to_fail"


def main():
    a, b = read_trials("m1-triage-A"), read_trials("m1-triage-B")
    print(f"A passes {sum(map(case_passed, a))} of {len(a)}, B passes {sum(map(case_passed, b))} of {len(b)}")
    flips = flipped_cases(a, b)
    print(f"flipped cases: {len(flips)}")
    for case_id in flips:
        print(f"  {case_id}: {flip_direction(case_id, a, b)}")


if __name__ == "__main__":
    main()
