"""The fake FreshMarket store the refund agent acts on. Loaded fresh for every trial."""
from __future__ import annotations

import copy
import json
from pathlib import Path

POLICY_SECTIONS = {
    "refund_window": "Refund window: 7 days from delivery for any item. Damaged or spoiled food needs a photo before a refund.",
    "missing_items": "Missing items: refunded in full, no return needed. Refund only the missing items, never the whole order.",
    "late_delivery": "Late delivery (more than 2 hours after the promised window): the delivery fee is refunded. Less than 2 hours late: no refund.",
    "food_safety": "Food safety concerns (allergic reaction, contaminated or spoiled food that someone ate): escalate to a person the same day. Do not decide a refund yourself.",
    "refund_method": "Refunds go back to the original payment method within 5 working days. Never refund more than the order total, and never refund the same thing twice.",
}
TODAY = "2026-11-20"


class Store:
    def __init__(self, orders: dict):
        self.orders = copy.deepcopy(orders)
        self.ledger: list[dict] = []        # refunds issued in this trial
        self.escalations: list[dict] = []
        self.calls: list[dict] = []          # every tool call, in order (the trajectory)

    def snapshot(self) -> dict:
        return {"ledger": copy.deepcopy(self.ledger), "escalations": copy.deepcopy(self.escalations)}

    # tools -----------------------------------------------------------------
    def get_order(self, order_id: str) -> dict:
        o = self.orders.get(order_id.strip().upper())
        if o is None:
            return {"error": f"no order {order_id}"}
        out = copy.deepcopy(o)
        out["refunds_already_issued"] = [r for r in o.get("prior_refunds", [])] + [r for r in self.ledger if r["order_id"] == o["id"]]
        out.pop("prior_refunds", None)
        return out

    def get_policy(self, topic: str) -> dict:
        return {"topic": topic, "text": POLICY_SECTIONS.get(topic, "Unknown topic. Topics: " + ", ".join(POLICY_SECTIONS))}

    def issue_refund(self, order_id: str, amount: float, reason: str) -> dict:
        o = self.orders.get(order_id.strip().upper())
        if o is None:
            return {"error": f"no order {order_id}"}
        entry = {"order_id": o["id"], "amount": round(float(amount), 2), "reason": reason}
        self.ledger.append(entry)
        return {"ok": True, "refund": entry}

    def escalate(self, order_id: str, reason: str) -> dict:
        entry = {"order_id": order_id.strip().upper(), "reason": reason}
        self.escalations.append(entry)
        return {"ok": True, "escalation": entry}


def load_orders(path: Path) -> dict:
    return {o["id"]: o for o in json.loads(path.read_text(encoding="utf-8"))}
