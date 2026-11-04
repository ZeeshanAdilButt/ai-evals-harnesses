"""The refund agent: a tool loop over the fake store with a scripted customer.

`call(request) -> dict` is injected: the recorder passes a live call, every course step passes
replay. The loop is deterministic given the model outputs, because the store and the scripted
customer are deterministic, so a replayed trial asks for exactly the recorded requests.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from evalkit.replay import canonical_request, params_for, request_key
from product.agent.store import POLICY_SECTIONS, TODAY, Store
from product.triage import PRODUCT, VARIANTS

PARAMS = {"max_tokens": 1024, "thinking": {"type": "between_tools"}, "output_config": {"effort": "low"}}

TOOLS = [
    {"name": "get_order", "description": "Look up an order by its id, for example FM-104233. Returns items, prices, delivery details and refunds already issued.",
     "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"], "additionalProperties": False}},
    {"name": "get_policy", "description": "Read one section of the refund policy. Topics: " + ", ".join(POLICY_SECTIONS) + ".",
     "input_schema": {"type": "object", "properties": {"topic": {"type": "string", "enum": list(POLICY_SECTIONS)}}, "required": ["topic"], "additionalProperties": False}},
    {"name": "issue_refund", "description": "Refund an amount in dollars to the original payment method. Use only when the policy allows it.",
     "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}, "amount": {"type": "number"}, "reason": {"type": "string"}}, "required": ["order_id", "amount", "reason"], "additionalProperties": False}},
    {"name": "escalate", "description": "Send the case to a person on the support team today, with a short reason.",
     "input_schema": {"type": "object", "properties": {"order_id": {"type": "string"}, "reason": {"type": "string"}}, "required": ["order_id", "reason"], "additionalProperties": False}},
    {"name": "ask_customer", "description": "Ask the customer one question and wait for the answer, for example for a photo or the order number.",
     "input_schema": {"type": "object", "properties": {"question": {"type": "string"}}, "required": ["question"], "additionalProperties": False}},
]


class ScriptedCustomer:
    """Answers from a rule table. `gives_up_after` ends the conversation after that many questions."""

    def __init__(self, rules: dict):
        self.rules = rules
        self.asked = 0
        self.gave_up = False

    def answer(self, question: str) -> str:
        self.asked += 1
        limit = self.rules.get("gives_up_after")
        if limit is not None and self.asked > limit:
            self.gave_up = True
            return "Forget it, I don't have time for this. I'll call later."
        q = question.lower()
        for rule in self.rules.get("answers", []):
            if re.search(rule["if"], q):
                return rule["say"]
        return self.rules.get("default", "I'm not sure what you need. Can you just help me?")


def system_prompt(variant: str) -> str:
    v = VARIANTS[variant]
    return (PRODUCT / v["agent_prompt"]).read_text(encoding="utf-8").replace("{today}", TODAY)


def build_request(variant: str, messages: list) -> dict:
    v = VARIANTS[variant]
    system = system_prompt(variant)
    canonical = canonical_request(v["model"], system, messages, tools=TOOLS, params=params_for(v["model"], PARAMS))
    return {"key": request_key(canonical), "model": v["model"], "system": system,
            "messages": messages, "tools": TOOLS, "params": params_for(v["model"], PARAMS)}


def run_task(variant: str, task: dict, orders: dict, call, max_steps: int = 10) -> dict:
    """Run one trial. Returns the trajectory, the final store state and the final message."""
    store = Store(orders)
    customer = ScriptedCustomer(task["customer"])
    messages = [{"role": "user", "content": task["opening"]}]
    final_text, steps, stop = "", 0, "max_steps"
    for steps in range(1, max_steps + 1):
        req = build_request(variant, messages)
        resp = call(req)                     # {"content": [...blocks...], "stop_reason": ...}
        blocks = resp["content"]
        messages.append({"role": "assistant", "content": blocks})
        uses = [b for b in blocks if b.get("type") == "tool_use"]
        if not uses:
            final_text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
            stop = "end_turn"
            break
        results = []
        for u in uses:
            name, args = u["name"], u["input"]
            store.calls.append({"step": steps, "tool": name, "input": args})
            if name == "ask_customer":
                out = {"customer": customer.answer(args.get("question", ""))}
            else:
                out = getattr(store, name)(**args)
            results.append({"type": "tool_result", "tool_use_id": u["id"], "content": json.dumps(out, sort_keys=True)})
        messages.append({"role": "user", "content": results})
        if customer.gave_up:
            stop = "customer_gave_up"
            break
    return {"task": task["id"], "variant": variant, "steps": steps, "stop": stop,
            "trajectory": store.calls, "final_state": store.snapshot(), "final_message": final_text,
            "customer_gave_up": customer.gave_up}
