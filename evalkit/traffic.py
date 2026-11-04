"""The traffic week: which reply variant answered which ticket on which day. One function, used everywhere (monitor, the judge
item files, the canary). Shipped and finished.

Days 1 to 4: variant A. Days 5 to 7: English tickets use A-day5, mixed-language tickets use A-day5-mixed (the planted break:
a reply template that lost the policy block).
Canary: days 1 to 4 replay A's pool trials 1 to 4 (trial = day); days 5 to 7 replay trials 1 to 3 (trial = day - 4) of A-day5 for
English tickets and of A-day5-mixed for mixed-language tickets.
"""
from __future__ import annotations

import json
from pathlib import Path


def variant_for(ticket: dict, day: int) -> str:
    if day <= 4:
        return "A"
    return "A-day5-mixed" if ticket.get("language") == "mixed" else "A-day5"


def canary_variant_trial(ticket: dict, day: int) -> tuple[str, int]:
    """(variant, reply trial) of the canary reply for this ticket on this day."""
    return (variant_for(ticket, day), day if day <= 4 else day - 4)


# --- the recorded week, judged (module 10) ---------------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
JUDGE = "v3"


def read_jsonl(path) -> list:
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def tickets() -> list:
    """All 3,500 tickets of the synthetic week (text is scrubbed)."""
    return read_jsonl(ROOT / "datasets" / "traffic" / "tickets.jsonl")


def canary_tickets() -> list:
    return read_jsonl(ROOT / "datasets" / "traffic" / "canary.jsonl")


class Recordings:
    """The reply and judge stores, loaded once. A verdict is looked up by request key, never by item id."""

    def __init__(self):
        from evalkit.replay import Store
        self.reply = Store.load("reply")
        self.judge = Store.load("judge")


def judged_reply(rec: Recordings, ticket: dict, variant: str, reply_trial: int) -> tuple[str | None, str | None]:
    """(reply text, judge v3 verdict) for one ticket; None for what is not recorded yet."""
    from evalkit.replay import ReplayMiss
    from product import reply as reply_feature
    from product.judge import build_request, parse_verdict
    try:
        text = rec.reply.lookup(reply_feature.build_request(variant, ticket["text"])["key"], reply_trial)["output"]
    except ReplayMiss:
        return None, None
    try:
        return text, parse_verdict(rec.judge.lookup(build_request(JUDGE, ticket["text"], text)["key"], 1)["output"])
    except ReplayMiss:
        return text, None


def week(refund_only: bool = True) -> list:
    """One trace per ticket: the ticket fields, the variant that answered, the reply and the judge v3 verdict (refund tickets only are
    judged). `verdict` is "pass", "fail" or None (not judged or not recorded yet)."""
    rec = Recordings()
    out = []
    for t in tickets():
        if refund_only and t["category"] != "refund":
            continue
        variant = variant_for(t, t["day"])
        text, verdict = judged_reply(rec, t, variant, 1) if t["category"] == "refund" else (None, None)
        out.append({"id": t["id"], "day": t["day"], "tone": t["tone"], "language": t["language"], "length": t["length"], "category": t["category"],
                    "urgent": t["urgent"], "text": t["text"], "expected": t["expected"], "variant": variant, "reply": text, "verdict": verdict})
    return out


def judged(rows: list) -> list:
    """The refund traces that have a verdict, in the shape daily_rates reads: the grouping fields and `passed`."""
    return [{"id": r["id"], "day": r["day"], "tone": r["tone"], "language": r["language"], "length": r["length"], "passed": r["verdict"] == "pass"}
            for r in rows if r["verdict"] is not None]


def missing(rows: list) -> list:
    return [r["id"] for r in rows if r["category"] == "refund" and r["verdict"] is None]


def canary_week() -> list:
    """The refund canary tickets on each of the seven days with their judge v3 verdict: one dict per (ticket, day)."""
    rec = Recordings()
    out = []
    for t in canary_tickets():
        if t["category"] != "refund":
            continue
        for day in range(1, 8):
            variant, trial = canary_variant_trial(t, day)
            text, verdict = judged_reply(rec, t, variant, trial)
            out.append({"id": t["id"], "day": day, "language": t["language"], "variant": variant, "verdict": verdict})
    return out
