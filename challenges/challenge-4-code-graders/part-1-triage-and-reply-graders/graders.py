"""Challenge 4, part 1: the graders. A grader is code that reads one recorded output and says True or False.

Shipped and read, not written (evalkit/graders/helpers.py):
  find_numbers(text)                                   every number in a text
  grade_reply_amount(reply, expected_amount, tolerance) the worked tolerance check: money within a cent
  confusion_matrix(pairs, labels)                      a counting loop (used by grade.py)

Fill the five YOUR TURN gaps (checkpoint 1 is the first three, checkpoint 2 the last two):
  1. normalise(text)
  2. grade_triage_schema(output)
  3. grade_triage_match(output, expected)
  4. grade_reply_contains(reply, must, must_not)
  5. grade_reply_refund_days(reply, expected_days)

The triage output should be one JSON object: {"category": one of billing, delivery, refund, account, product, "urgent": true or false}.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from evalkit.graders.helpers import confusion_matrix, find_numbers, grade_reply_amount  # noqa: E402,F401  (shipped)

CATEGORIES = ("billing", "delivery", "refund", "account", "product")


def normalise(text):
    """Make two strings that mean the same compare equal: lowercase, curly quotes to straight quotes, no '*' or '`'
    marks, every run of white space becomes one space, no white space at either end. Return a str."""
    raise NotImplementedError("YOUR TURN: lower-case, replace the curly quotes, drop * and `, collapse white space, strip")


def _parse(output):
    """The object inside a triage output, or None. One recorded output wraps the JSON in a ```json fence: accept that."""
    text = str(output).strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.S)
    if fence:
        text = fence.group(1)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def grade_triage_schema(output):
    """True when the output is one JSON object with a category from CATEGORIES (after normalise) and urgent that is
    exactly true or false (a JSON boolean, not the string "true"). Prose around the JSON fails."""
    raise NotImplementedError("YOUR TURN: parse; require a dict with both keys; the normalised category is in CATEGORIES; urgent is a bool")


def grade_triage_match(output, expected):
    """`expected` is {"category": "refund", "urgent": False}. True when the schema is valid and the normalised category and the
    urgent flag both equal the labels. Not a string compare of the whole output."""
    raise NotImplementedError("YOUR TURN: schema first, then compare normalise(category) and urgent with expected")


def grade_reply_contains(reply, must, must_not):
    """`must` and `must_not` are lists of phrases. True when every phrase in `must` appears in the reply and no phrase in
    `must_not` does. Compare on normalised text (normalise both sides)."""
    raise NotImplementedError("YOUR TURN: normalise the reply and each phrase; all of must in, none of must_not in")


def grade_reply_refund_days(reply, expected_days):
    """Exact. The reply must write the window as digits next to 'day' or 'days' ('7 days', '7-day window'), and the
    number must be expected_days. 'a week' fails (no number is written); '14 days' fails; saying '7 days' and
    '14 days' in one reply fails. Numbers before other words ('5 working days') are not day counts."""
    raise NotImplementedError("YOUR TURN: collect every N in 'N day(s)' or 'N-day' on normalised text; pass only when that set is {expected_days}")


if __name__ == "__main__":
    print(grade_triage_match('{"category": "Refund", "urgent": false}', {"category": "refund", "urgent": False}))
    print(grade_reply_refund_days("Refunds are open for a week.", 7))
