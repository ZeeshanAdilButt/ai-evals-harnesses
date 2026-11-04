"""Reference triage graders (the learner writes these in 4.5; the reference solution lives here)."""
from __future__ import annotations

import json
import re

CATEGORIES = ("billing", "delivery", "refund", "account", "product")


def parse_triage(output: str) -> dict | None:
    """Return {"category", "urgent"} if the output holds one JSON object with both fields, else None."""
    text = output.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.S)
    if fence:
        text = fence.group(1)
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict) or "category" not in obj or "urgent" not in obj:
        return None
    return obj


def normalise_category(value) -> str:
    return str(value).strip().lower()


def grade_schema(output: str) -> bool:
    obj = parse_triage(output)
    return obj is not None and normalise_category(obj["category"]) in CATEGORIES and isinstance(obj["urgent"], bool)


def grade_category_exact(output: str, expected: str) -> bool:
    obj = parse_triage(output)
    return obj is not None and obj["category"] == expected


def grade_category(output: str, expected: str) -> bool:
    obj = parse_triage(output)
    return obj is not None and normalise_category(obj["category"]) == expected


def predicted(output: str) -> tuple[str | None, bool | None]:
    obj = parse_triage(output)
    if obj is None:
        return None, None
    cat = normalise_category(obj["category"])
    return (cat if cat in CATEGORIES else None), (obj["urgent"] if isinstance(obj["urgent"], bool) else None)
