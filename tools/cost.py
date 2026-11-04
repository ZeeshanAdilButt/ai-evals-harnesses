"""Sum the recorded tokens and estimate what the recordings cost. Batch trials (latency_valid false) at half price."""
import json
from pathlib import Path

PRICES = {"claude-sonnet-5-5": (2.00, 10.00), "claude-haiku-5-5": (0.10, 0.50)}
ROOT = Path(__file__).resolve().parents[1]
total = 0.0
for f in sorted(p for p in (ROOT / "recordings").rglob("*.jsonl") if "agent-runs" not in p.parts):
    cost = calls = 0
    for line in f.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("tokens_in") is None:
            calls += 1
            continue
        pin, pout = PRICES.get(r["model"], (2.5, 10.0))
        c = (r["tokens_in"] * pin + r["tokens_out"] * pout) / 1e6
        cost += c if r.get("latency_valid", True) else c / 2
        calls += 1
    total += cost
    print(f"{f.relative_to(ROOT)}: {calls} calls, ${cost:.2f}")
print(f"total: ${total:.2f}")
