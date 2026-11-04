"""Write datasets/pool/spec.jsonl: the dimension values each of the 400 pool tickets must show.

The ticket text is written to this spec afterwards (by the author's drafting pass) and checked
against it by tools/check_pool.py. The spec is the source of the expected triage labels.
"""
import json
import random
from pathlib import Path

CATEGORIES = ["billing", "delivery", "refund", "account", "product"]
TONES = ["calm", "angry", "confused"]
LANGUAGES = ["english", "mixed"]
LENGTHS = ["short", "normal", "long"]
SOURCES = ["synthetic", "sampled", "past_failure", "edge"]

rng = random.Random(7)
rows = []
for i in range(400):
    category = CATEGORIES[i % 5]                       # 80 per category
    urgent = rng.random() < 0.12                        # about 48 urgent in the pool
    tone = rng.choices(TONES, weights=[5, 3, 2])[0]
    language = rng.choices(LANGUAGES, weights=[8, 2])[0]
    length = rng.choices(LENGTHS, weights=[3, 5, 2])[0]
    source = rng.choices(SOURCES, weights=[5, 2, 1, 1])[0]
    pii = rng.random() < 0.25                           # raw text carries a fake email or phone
    rows.append({
        "id": f"t{i + 1:03d}",
        "category": category,
        "urgent": urgent,
        "tone": tone,
        "language": language,
        "length": length,
        "source": source,
        "pii": pii,
    })
rng.shuffle(rows)
for n, r in enumerate(rows):
    r["id"] = f"t{n + 1:03d}"
    r["easy"] = r["tone"] == "calm" and r["language"] == "english" and r["length"] == "normal" and r["source"] != "edge"

out = Path(__file__).resolve().parents[1] / "datasets" / "pool" / "spec.jsonl"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in sorted(rows, key=lambda r: r["id"])), encoding="utf-8")
counts = {c: sum(r["category"] == c for r in rows) for c in CATEGORIES}
print(len(rows), counts, "urgent", sum(r["urgent"] for r in rows), "easy", sum(r["easy"] for r in rows), "pii", sum(r["pii"] for r in rows))
