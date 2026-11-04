"""Reply: one model call that writes the support reply for a ticket, following the policy."""
from __future__ import annotations

from evalkit.replay import canonical_request, params_for, request_key
from product.triage import PRODUCT, VARIANTS

PARAMS = {"max_tokens": 600, "thinking": {"type": "between_tools"}, "output_config": {"effort": "low"}}


def build_request(variant: str, ticket_text: str) -> dict:
    v = VARIANTS[variant]
    policy = (PRODUCT / v.get("policy", "policy.md")).read_text(encoding="utf-8")
    system = (PRODUCT / v["reply_prompt"]).read_text(encoding="utf-8") + "\n" + policy
    messages = [{"role": "user", "content": ticket_text}]
    canonical = canonical_request(v["model"], system, messages, params=params_for(v["model"], PARAMS))
    return {"key": request_key(canonical), "model": v["model"], "system": system,
            "messages": messages, "params": params_for(v["model"], PARAMS)}
