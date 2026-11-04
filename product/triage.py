"""Triage: one model call that files a ticket under a category and says whether it is urgent."""
from __future__ import annotations

import tomllib
from pathlib import Path

from evalkit.replay import canonical_request, params_for, request_key

PRODUCT = Path(__file__).resolve().parent
VARIANTS = tomllib.loads((PRODUCT / "variants.toml").read_text(encoding="utf-8"))

# Request parameters are part of the recorded request, so changing them changes the key.
# Thinking is off for this one-line classification; no sampling parameters are sent
# (the current API version rejects temperature, top_p and top_k).
PARAMS = {"max_tokens": 256, "thinking": {"type": "between_tools"}, "output_config": {"effort": "low"}}


def build_request(variant: str, ticket_text: str) -> dict:
    v = VARIANTS[variant]
    system = (PRODUCT / v["triage_prompt"]).read_text(encoding="utf-8")
    messages = [{"role": "user", "content": ticket_text}]
    canonical = canonical_request(v["model"], system, messages, params=params_for(v["model"], PARAMS))
    return {
        "key": request_key(canonical),
        "model": v["model"],
        "system": system,
        "messages": messages,
        "params": params_for(v["model"], PARAMS),
    }
