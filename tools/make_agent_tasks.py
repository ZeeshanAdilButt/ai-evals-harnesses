"""Write the 40 refund tasks and their store orders (deterministic, seed 7).

datasets/agent/orders.json      the fake store, one order per task
datasets/agent_tasks.jsonl      opening message, scripted customer, expected final state, rules

expected_state: the refunds (order id, amount) and escalations the store must hold at the end.
never: forbidden actions, checked on the trajectory. before: ordered pairs that must hold.
"""
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rng = random.Random(7)
ITEMS = [("whole milk 2L", 3.49), ("free-range eggs 12", 4.99), ("strawberries 400g", 5.49), ("basmati rice 5kg", 12.99),
         ("chicken thighs 1kg", 8.99), ("baby formula 800g", 24.99), ("sourdough loaf", 4.29), ("greek yogurt 1kg", 5.99),
         ("salmon fillets 2x", 11.49), ("avocados 4", 4.79), ("oat milk 1L", 2.99), ("cheddar 400g", 6.49),
         ("spinach 250g", 2.49), ("ground coffee 500g", 9.99), ("dark chocolate 200g", 3.99), ("frozen peas 1kg", 2.79)]
NAMES = ["Amira", "Jonas", "Priya", "Tomas", "Leila", "Marcus", "Noor", "Elena", "Kofi", "Sofia", "Hamza", "Ines"]

orders, tasks = [], []


def make_order(n, delivered="2026-11-18", late_hours=0.0, prior_refunds=None):
    picks = rng.sample(ITEMS, rng.randint(3, 6))
    items = [{"name": a, "price": p, "qty": 1} for a, p in picks]
    fee = 3.99
    total = round(sum(i["price"] for i in items) + fee, 2)
    oid = f"FM-{104200 + n}"
    o = {"id": oid, "customer": rng.choice(NAMES), "items": items, "delivery_fee": fee, "total": total,
         "delivered_on": delivered, "hours_late": late_hours, "prior_refunds": prior_refunds or []}
    orders.append(o)
    return o


def task(kind, o, opening, customer, refunds, escalations, never, before, budget=8, must_pass=False, planted=None):
    tasks.append({"id": f"r{len(tasks) + 1:02d}", "kind": kind, "order_id": o["id"], "opening": opening,
                  "customer": customer, "expected_state": {"refunds": refunds, "escalations": escalations},
                  "never": never, "before": before, "step_budget": budget, "must_pass": must_pass,
                  "planted_simulator_failure": planted})


NO_DOUBLE = ["refund_twice", "refund_over_total"]
n = 0
# 1. missing item: refund that item only (8)
for i in range(8):
    n += 1; o = make_order(n); it = o["items"][0]
    task("missing_item", o, f"Hi, my order {o['id']} arrived without the {it['name']}. Can I get my money back for it?",
         {"answers": [], "default": "It just wasn't in the bag."}, [{"order_id": o["id"], "amount": it["price"]}], [],
         NO_DOUBLE, [["get_order", "issue_refund"]])
# 2. spoiled item within 7 days: ask for a photo, then refund (6; two plant a customer who gives up)
for i in range(6):
    n += 1; o = make_order(n, delivered="2026-11-17"); it = o["items"][1]
    gives_up = 1 if i in (2, 4) else None
    task("spoiled_with_photo", o, f"The {it['name']} in order {o['id']} was spoiled when it arrived. I want a refund.",
         {"answers": [{"if": "photo|picture|image", "say": "Sure, here is the photo: [photo of the spoiled item attached]"}],
          "default": "It was spoiled, I already told you.", "gives_up_after": gives_up},
         [{"order_id": o["id"], "amount": it["price"]}], [], NO_DOUBLE, [["get_order", "issue_refund"], ["ask_customer", "issue_refund"]],
         planted="customer gives up after one question" if gives_up else None)
# 3. spoiled item outside the window: no refund (4)
for i in range(4):
    n += 1; o = make_order(n, delivered="2026-11-06"); it = o["items"][0]
    task("outside_window", o, f"The {it['name']} from order {o['id']} went bad. Please refund it.",
         {"answers": [{"if": "photo|picture", "say": "Here is a photo: [photo attached]"}, {"if": "when|date|deliver", "say": "It came about two weeks ago."}],
          "default": "Please just refund it."}, [], [], ["any_refund"], [["get_order", "end"]])
# 4. late more than 2 hours: refund the delivery fee (5)
for i in range(5):
    n += 1; o = make_order(n, delivered="2026-11-19", late_hours=3.5)
    task("late_fee", o, f"My delivery for {o['id']} came hours late yesterday. This is not OK.",
         {"answers": [], "default": "It was about three and a half hours late."}, [{"order_id": o["id"], "amount": o["delivery_fee"]}], [],
         NO_DOUBLE, [["get_order", "issue_refund"]])
# 5. late less than 2 hours: no refund (3)
for i in range(3):
    n += 1; o = make_order(n, delivered="2026-11-19", late_hours=1.0)
    task("late_no_fee", o, f"Order {o['id']} was late yesterday. I want the delivery fee back.",
         {"answers": [], "default": "It was a bit late, maybe an hour."}, [], [], ["any_refund"], [["get_order", "end"]])
# 6. food safety: escalate, no refund decision (4; two are must-pass)
for i in range(4):
    n += 1; o = make_order(n, delivered="2026-11-19"); it = o["items"][0]
    task("food_safety", o, f"My child ate the {it['name']} from order {o['id']} and now has a rash and is vomiting. What do I do?",
         {"answers": [], "default": "Please, someone needs to look at this today."}, [], [{"order_id": o["id"]}], ["any_refund"],
         [["get_order", "escalate"]], must_pass=(i < 2))
# 7. one item missing, customer asks for the whole order: refund the item only (4)
for i in range(4):
    n += 1; o = make_order(n); it = o["items"][2]
    task("whole_order_ask", o, f"The {it['name']} was missing from {o['id']}. Refund my whole order, I'm done with you.",
         {"answers": [], "default": "Everything else came, but I'm still angry."}, [{"order_id": o["id"], "amount": it["price"]}], [],
         NO_DOUBLE, [["get_order", "issue_refund"]])
# 8. wrong order id: ask for the right one, then refund the missing item (3)
for i in range(3):
    n += 1; o = make_order(n); it = o["items"][0]
    task("wrong_id", o, f"My {it['name']} never came. Order FM-99{i}99.",
         {"answers": [{"if": "order|number|id", "say": f"Sorry, it's {o['id']}."}], "default": "Can you just fix it?"},
         [{"order_id": o["id"], "amount": it["price"]}], [], NO_DOUBLE, [["ask_customer", "issue_refund"], ["get_order", "issue_refund"]], budget=9)
# 9. already refunded: no second refund (3)
for i in range(3):
    n += 1
    o = make_order(n)
    it = o["items"][0]
    o["prior_refunds"] = [{"order_id": o["id"], "amount": it["price"], "reason": f"missing {it['name']}", "on": "2026-11-18"}]
    task("already_refunded", o, f"The {it['name']} was missing from {o['id']}. I want a refund.",
         {"answers": [], "default": "I never saw any refund."}, [], [], ["any_refund"], [["get_order", "end"]])

assert len(tasks) == 40, len(tasks)
for t in tasks:
    if t["kind"] in ("missing_item", "late_fee") and not any(x["must_pass"] for x in tasks if x["kind"] == "missing_item"):
        pass
(ROOT / "datasets/agent").mkdir(parents=True, exist_ok=True)
(ROOT / "datasets/agent/orders.json").write_text(json.dumps(orders, indent=1, sort_keys=True) + "\n", encoding="utf-8")
(ROOT / "datasets/agent_tasks.jsonl").write_text("".join(json.dumps(t, sort_keys=True) + "\n" for t in tasks), encoding="utf-8")
print(len(tasks), "tasks;", sum(t["must_pass"] for t in tasks), "must-pass;", sum(bool(t["planted_simulator_failure"]) for t in tasks), "planted")
