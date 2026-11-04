"""The reference graders of 4.5 as one namespace with the same names as the learner's graders.py.
Tests and `tools/` use it to compute the numbers a correct solution must reproduce."""
from __future__ import annotations

import types

from evalkit.graders import helpers, reply, triage


def graders() -> types.SimpleNamespace:
    def match(output, expected):
        cat, urgent = triage.predicted(output)
        return cat == expected["category"] and urgent is expected["urgent"]

    return types.SimpleNamespace(
        CATEGORIES=triage.CATEGORIES,
        normalise=reply.normalise,
        _parse=triage.parse_triage,
        grade_triage_schema=triage.grade_schema,
        grade_triage_match=match,
        grade_reply_contains=reply.grade_reply_contains,
        grade_reply_refund_days=reply.grade_reply_refund_days,
        grade_reply_amount=helpers.grade_reply_amount,
    )
