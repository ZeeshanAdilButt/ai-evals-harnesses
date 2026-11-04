"""The judge feature: one call that grades one refund reply against the criterion."""
from __future__ import annotations

import json
import re

from evalkit.replay import canonical_request, request_key
from judges.parts import judge_prompt
from product.triage import PRODUCT

JUDGE_MODEL = "claude-sonnet-5-5"
PARAMS = {"max_tokens": 300, "thinking": {"type": "between_tools"}, "output_config": {"effort": "low"}}
PAD = (" Thank you so much for being a valued FreshMarket customer; we truly appreciate your patience and your kind"
       " understanding, and we are always here to help you with anything else you might need, any day of the week.")


def build_request(judge_id: str, ticket: str, reply: str, reverse: bool = False, padded: bool = False,
                  model: str = JUDGE_MODEL) -> dict:
    policy = (PRODUCT / "policy.md").read_text(encoding="utf-8")
    body = reply + PAD if padded else reply
    user = f"Policy:\n{policy}\nCustomer ticket:\n{ticket}\n\nReply to grade:\n{body}"
    system = judge_prompt(judge_id, reverse=reverse)
    messages = [{"role": "user", "content": user}]
    canonical = canonical_request(model, system, messages, params=PARAMS)
    return {"key": request_key(canonical), "model": model, "system": system, "messages": messages, "params": PARAMS}


def parse_verdict(output: str) -> str | None:
    text = output.strip()
    # A judge sometimes writes a verdict, then corrects itself with a second JSON object: the last complete object with a verdict wins.
    decoder, last, i = json.JSONDecoder(), None, 0
    while True:
        j = text.find("{", i)
        if j < 0:
            break
        try:
            obj, end = decoder.raw_decode(text, j)
        except json.JSONDecodeError:
            i = j + 1
            continue
        if isinstance(obj, dict) and obj.get("verdict") in ("pass", "fail"):
            last = obj["verdict"]
        i = end
    if last:
        return last
    low = text.lower()
    if re.fullmatch(r"\W*(pass|fail)\W*", low):
        return low.strip(" .!\n\"'")
    return None
