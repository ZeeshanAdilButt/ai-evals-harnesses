"""Pick the daily canary set: 20 fixed pool tickets (6 mixed-language refund, 4 English refund,
10 others). Days 1 to 4 replay variant A's pool recordings (trial = day); days 5 to 7 use the
day 5 prompt (variant A-day5, trial = day - 4)."""
import json, random
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
pool = [json.loads(l) for l in (ROOT / "datasets/pool/tickets.jsonl").read_text(encoding="utf-8").splitlines()]
rng = random.Random(5)
mixed_ref = sorted([t for t in pool if t["category"] == "refund" and t["language"] == "mixed"], key=lambda t: t["id"])
eng_ref = sorted([t for t in pool if t["category"] == "refund" and t["language"] == "english"], key=lambda t: t["id"])
others = sorted([t for t in pool if t["category"] != "refund"], key=lambda t: t["id"])
pick = rng.sample(mixed_ref, 6) + rng.sample(eng_ref, 4) + rng.sample(others, 10)
out = ROOT / "datasets/traffic/canary.jsonl"
out.write_text("".join(json.dumps(t, ensure_ascii=False, sort_keys=True) + "\n" for t in sorted(pick, key=lambda t: t["id"])), encoding="utf-8")
print(len(pick), "mixed refund available", len(mixed_ref))
