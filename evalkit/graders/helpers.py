"""Shipped helpers for chapter 4.5: the learner reads these and calls them, never edits them."""
from __future__ import annotations

import re

NUMBER = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")


def find_numbers(text: str) -> list[float]:
    """Every number written in a text, as floats, in order: '$12.50 back in 5 days' gives [12.5, 5.0]. Commas inside a
    number are dropped ('1,200' is 1200). A regex, so '5-7 days' gives [5.0, 7.0]."""
    return [float(n.replace(",", "")) for n in NUMBER.findall(text)]


def cents(amount: float) -> int:
    """A money amount in whole cents (12.5 gives 1250). Compare money as cents: abs(12.51 - 12.50) is a little over 0.01 as floats."""
    return round(amount * 100)


def grade_reply_amount(reply: str, expected_amount: float, tolerance: float = 0.01) -> bool:
    """The worked example of a tolerance check: pass when the reply writes a number within `tolerance` of the amount.
    Money is compared in whole cents, never with == on floats (chapter 4.2)."""
    return any(abs(cents(n) - cents(expected_amount)) <= cents(tolerance) for n in find_numbers(reply))


def confusion_matrix(pairs, labels) -> dict:
    """Count (true, predicted) pairs. Rows are the true label, columns the predicted one. A prediction that is not
    one of `labels` (an invalid output) is counted under 'invalid'. Returns {true: {predicted: count}}.
    A row's recall is its diagonal cell over its row sum; a column's precision is the diagonal over the column sum."""
    cols = list(labels) + ["invalid"]
    m = {t: {p: 0 for p in cols} for t in labels}
    for true, pred in pairs:
        m[true][pred if pred in labels else "invalid"] += 1
    return m
