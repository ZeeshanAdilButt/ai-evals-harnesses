"""Writes datasets/reply_checks.jsonl (canonical v1) and datasets/reply_checks_v2.jsonl (the 40 v2 additions): what the
code graders check for each ticket's reply.

The rules are the author's, written from product/policy.md and applied by this script so they are repeatable:
  must_not_contain (every reply): a window, a time or a refund method the policy contradicts.
  must_contain, urgent tickets: the food safety hand-off says it goes to a person "today".
  must_contain, refund tickets: the refund time, "5 working days".
  refund_days = 7: refund tickets that ask for a refund of a delivered item (not a status chaser): the reply states the 7 day window.
  refund_amount: billing tickets that quote one charge (a number with cents): the reply names that amount.
  asks_order_number: a refund, billing or delivery ticket that names no order (no FM- number): the reply must ask for the order number,
      because the prompt tells the writer to ask for what the policy needs from the customer (used by the ship gate in chapter 9).
  must_pass: the refund-window tickets (refund_days is set), tagged by the author in chapter 4. The gate's own must-pass tag is
      `must_pass` on the canonical cases (tools/tag_must_pass.py): the refund-window tickets that variant A passes on all five trials.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHASER = re.compile(r"\b(where|when|kab|still|on the way|processed|confirm|has been|ten days|two weeks|a week ago|returned)\b", re.I)
AMOUNT = re.compile(r"(?<![\d.])(\d{1,4}\.\d{2})(?![\d])")
ORDER_ID = re.compile(r"FM-\d+")
NOT = ["14 days", "30 days", "24 hours", "48 hours", "store credit"]


def checks_for(c: dict) -> dict:
    cat, urgent, text = c["expected"]["category"], c["expected"]["urgent"], c["text"]
    must = []
    if urgent:
        must.append("today")
    if cat == "refund":
        must.append("5 working days")
    days = 7 if cat == "refund" and not CHASER.search(text) else None
    amounts = AMOUNT.findall(text)
    amount = float(amounts[0]) if cat == "billing" and amounts else None
    asks = cat in ("refund", "billing", "delivery") and not ORDER_ID.search(text)
    return {"id": c["id"], "must_contain": must, "must_not_contain": NOT, "refund_days": days, "refund_amount": amount,
            "asks_order_number": asks, "must_pass": days is not None}


def write(name: str, cases: list) -> list:
    out = [checks_for(c) for c in cases]
    (ROOT / "datasets" / name).write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in out), encoding="utf-8")
    return out


def main():
    cases = [json.loads(l) for l in (ROOT / "datasets/canonical/v1/cases.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    out = write("reply_checks.jsonl", cases)
    adds = [json.loads(l) for l in (ROOT / "datasets/canonical/v2/additions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    out2 = write("reply_checks_v2.jsonl", adds)
    print(len(out), "rows;", sum(r["refund_days"] is not None for r in out), "refund-window;", sum(r["refund_amount"] is not None for r in out),
          "amount;", sum(bool(r["must_contain"]) for r in out), "must_contain;", sum(r["asks_order_number"] for r in out), "ask the order number;",
          len(out2), "v2 additions")


if __name__ == "__main__":
    main()
