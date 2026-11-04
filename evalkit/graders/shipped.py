"""The graders the runner ships by name. Each takes (output, case) and returns True or False."""
from __future__ import annotations

from evalkit.graders import reply as reply_graders
from evalkit.graders.triage import grade_category, grade_category_exact, grade_schema, predicted


def schema(output, case):
    """The output is one JSON object with a valid category and a true or false urgent."""
    return grade_schema(output)


def exact(output, case):
    """The category equals the label exactly, letter for letter."""
    return grade_category_exact(output, case["expected"]["category"])


def category(output, case):
    """The category equals the label after trimming and lower-casing."""
    return grade_category(output, case["expected"]["category"])


def match(output, case):
    """Normalised category and urgent flag both equal the labels."""
    cat, urgent = predicted(output)
    return cat == case["expected"]["category"] and urgent == case["expected"]["urgent"]


def reply_nonempty(output, case):
    """Placeholder for the reply feature until the module 4 graders: the reply has text."""
    return bool(output and output.strip())


def reply_facts(output, case):
    """The reply code checks of 4.5 and 9.7 for one case: must and must not contain, exact refund days, the amount, and the order-number ask."""
    return reply_graders.grade_reply_facts(output, reply_graders.all_checks()[case["id"]])


SHIPPED = {"schema": schema, "exact": exact, "category": category, "match": match, "reply_nonempty": reply_nonempty, "reply_facts": reply_facts}
