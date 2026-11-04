"""Reference reply graders (the learner writes these in 4.5; the reference solution lives here).
Each takes the reply text and what the case expects, and returns True or False. No model is called."""
from __future__ import annotations

import json
import re
from pathlib import Path

from evalkit.graders.helpers import grade_reply_amount  # noqa: F401  (shipped, re-exported)

CHECKS = Path(__file__).resolve().parents[2] / "datasets" / "reply_checks.jsonl"


def load_checks() -> dict:
    return {r["id"]: r for r in map(json.loads, CHECKS.read_text(encoding="utf-8").splitlines()) if r}


def normalise(text: str) -> str:
    """Lowercase, straight quotes, no markdown marks, single spaces."""
    text = str(text).replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = text.replace("*", "").replace("`", "")
    return re.sub(r"\s+", " ", text).strip().lower()


def grade_reply_contains(reply: str, must, must_not) -> bool:
    r = normalise(reply)
    return all(normalise(m) in r for m in must) and not any(normalise(n) in r for n in must_not)


def grade_reply_refund_days(reply: str, expected_days: int) -> bool:
    """Exact: the reply writes the number of days as digits next to 'day' or 'days', and it is expected_days.
    'a week' fails (no number is written); 'within 14 days' fails; '7 days' and '7-day window' pass."""
    found = {int(n) for n in re.findall(r"\b(\d+)[- ]days?\b", normalise(reply))}
    return found == {expected_days}


# --- the gate's reply check (shipped): the same facts as 4.5, plus asking for the order number ---------------------------------

ASKS_ORDER = re.compile(r"order (number|id|reference)|which order", re.I)
CHECKS_V2 = Path(__file__).resolve().parents[2] / "datasets" / "reply_checks_v2.jsonl"
_ALL_CHECKS: dict = {}


def all_checks() -> dict:
    """The reply checks of canonical v1 and of the 40 v2 additions, by ticket id."""
    if not _ALL_CHECKS:
        _ALL_CHECKS.update(load_checks())
        if CHECKS_V2.exists():
            _ALL_CHECKS.update({r["id"]: r for r in map(json.loads, CHECKS_V2.read_text(encoding="utf-8").splitlines()) if r})
    return _ALL_CHECKS


def grade_asks_order_number(reply: str) -> bool:
    """The reply asks the customer for the order number or says which order it needs."""
    return bool(ASKS_ORDER.search(reply))


def grade_reply_facts(reply: str, check: dict, contains=None, days=None, amount=None, asks=None) -> bool:
    """All the code checks for one reply: must and must not contain, the exact refund days when the check has them, the amount
    within a cent when it has one, and the order-number ask when the ticket names no order. The four graders can be replaced
    (the capstone passes the learner's)."""
    contains = contains or grade_reply_contains
    days = days or grade_reply_refund_days
    amount = amount or grade_reply_amount
    asks = asks or grade_asks_order_number
    ok = contains(reply, check["must_contain"], check["must_not_contain"])
    if check.get("refund_days") is not None:
        ok = ok and bool(days(reply, check["refund_days"]))
    if check.get("refund_amount") is not None:
        ok = ok and bool(amount(reply, check["refund_amount"], 0.01))
    if check.get("asks_order_number"):
        ok = ok and bool(asks(reply))
    return bool(ok)
