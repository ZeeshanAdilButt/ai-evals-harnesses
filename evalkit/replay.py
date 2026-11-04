"""Request hashing and the recording store.

A recording is one JSON line per model call. Its key is the SHA-256 of the canonical request:
model id, system prompt, messages, tools, output schema and request parameters, as JSON with
sorted keys and no whitespace. The trial number is not in the key; it is the second half of the
lookup, so five trials of one request are five lines that share one key.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORDINGS = ROOT / "recordings"


class ReplayMiss(Exception):
    """The request was never recorded. A run records this per trial and goes on."""

    def __init__(self, key: str, feature: str):
        super().__init__(f"no recording for key {key[:12]} in feature {feature}")
        self.key = key
        self.feature = feature


def canonical_request(model: str, system: str, messages: list, tools: list | None = None,
                      output_schema: dict | None = None, params: dict | None = None) -> str:
    body = {
        "model": model,
        "system": system,
        "messages": messages,
        "tools": tools or [],
        "output_schema": output_schema,
        "params": params or {},
    }
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def request_key(canonical: str) -> str:
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class Store:
    """Every recording file of one feature, indexed by (key, trial). The variant is metadata."""

    feature: str
    index: dict = field(default_factory=dict)

    @classmethod
    def load(cls, feature: str, root: Path = RECORDINGS) -> "Store":
        store = cls(feature)
        folder = root / feature
        if folder.exists():
            for path in sorted(folder.glob("*.jsonl")):
                for line in path.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        rec = json.loads(line)
                        store.index[(rec["key"], rec["trial"])] = rec
        return store

    def lookup(self, key: str, trial: int) -> dict:
        try:
            return self.index[(key, trial)]
        except KeyError:
            raise ReplayMiss(key, self.feature) from None


def params_for(model: str, params: dict) -> dict:
    """Request parameters per model. The cheaper model does not accept "between_tools", so its
    thinking is turned off with "disabled" (allowed at low effort). Other models keep `params`."""
    if model.startswith("claude-haiku"):
        p = dict(params)
        p["thinking"] = {"type": "disabled"}
        return p
    return params
