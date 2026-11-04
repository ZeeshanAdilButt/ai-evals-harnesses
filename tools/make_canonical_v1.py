"""Select canonical dataset v1 from the pool: 160 tickets, 32 per category, 2 urgent per
category (10 of 160, about 6%), split 120 dev and 40 held-out per category in the ratio 3 to 1.
Deterministic (seed 7). Writes datasets/canonical/v1/cases.jsonl and its hash."""
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
pool = [json.loads(l) for l in (ROOT / "datasets/pool/tickets.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
rng = random.Random(7)
cases = []
for cat in ["billing", "delivery", "refund", "account", "product"]:
    urgent = sorted([t for t in pool if t["category"] == cat and t["urgent"]], key=lambda t: t["id"])
    calm = sorted([t for t in pool if t["category"] == cat and not t["urgent"]], key=lambda t: t["id"])
    pick = rng.sample(urgent, 2) + rng.sample(calm, 30)
    rng.shuffle(pick)
    for n, t in enumerate(pick):
        cases.append({
            "id": t["id"], "split": "dev" if n % 4 else "heldout",
            "text": t["text"], "expected": t["expected"],
            "dims": {k: t[k] for k in ["tone", "language", "length", "source", "easy"]},
        })
cases.sort(key=lambda c: c["id"])
out = ROOT / "datasets/canonical/v1"
out.mkdir(parents=True, exist_ok=True)
body = "".join(json.dumps(c, ensure_ascii=False, sort_keys=True) + "\n" for c in cases)
(out / "cases.jsonl").write_text(body, encoding="utf-8")
h = hashlib.sha256(body.encode("utf-8")).hexdigest()
(out / "HASH").write_text(h + "\n", encoding="utf-8")
print(len(cases), "urgent", sum(c["expected"]["urgent"] for c in cases),
      "dev", sum(c["split"] == "dev" for c in cases), "heldout", sum(c["split"] == "heldout" for c in cases), h[:12])
