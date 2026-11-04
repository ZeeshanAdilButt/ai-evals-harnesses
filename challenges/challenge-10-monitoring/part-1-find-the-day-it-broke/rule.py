"""Challenge 10, part 1: the selection rule. Which traces of the week should become test cases?

    python -m evalkit select-traces --rule challenges/challenge-10-monitoring/part-1-find-the-day-it-broke/rule.py
    python -m evalkit dataset freeze --name my-v2          freezes the selected traces as your v2 additions
    python -m evalkit dataset compare --name my-v2         against the 40 additions of canonical dataset v2

A trace is a dict: id, day, tone, language, length, category, urgent, text (already scrubbed), expected, variant, reply, and verdict (the
judge's "pass" or "fail" for refund replies, None for the other categories).

Fill the one YOUR TURN gap: select_rule(trace). Return True for a trace to add to dataset v2. Add only scrubbed refund traces from the
cell you flagged; a trace from the wrong cell teaches the dataset nothing about the break.
"""
from __future__ import annotations


def select_rule(trace) -> bool:
    raise NotImplementedError("YOUR TURN: True for the judge-failed refund traces of the flagged days and slice")
