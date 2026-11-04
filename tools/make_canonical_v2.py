"""Canonical dataset v2: canonical v1 plus 40 refund tickets from the broken slice of the traffic
week (mixed language, days 5 to 7), the additions 10.7 asks the learner to select. Seed 9."""
import hashlib, json, random
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
v1 = [json.loads(l) for l in (ROOT / "datasets/canonical/v1/cases.jsonl").read_text(encoding="utf-8").splitlines()]
traffic = [json.loads(l) for l in (ROOT / "datasets/traffic/tickets.jsonl").read_text(encoding="utf-8").splitlines()]
slice_ = sorted([t for t in traffic if t["category"] == "refund" and t["language"] == "mixed" and t["day"] >= 5], key=lambda t: t["id"])
add = random.Random(9).sample(slice_, 40)
cases = v1 + [{"id": t["id"], "split": "v2_addition", "text": t["text"], "expected": t["expected"],
               "dims": {"tone": t["tone"], "language": t["language"], "length": t["length"], "source": "traffic", "easy": False}} for t in add]
cases.sort(key=lambda c: c["id"])
out = ROOT / "datasets/canonical/v2"; out.mkdir(parents=True, exist_ok=True)
body = "".join(json.dumps(c, ensure_ascii=False, sort_keys=True) + "\n" for c in cases)
(out / "cases.jsonl").write_text(body, encoding="utf-8")
(out / "HASH").write_text(hashlib.sha256(body.encode()).hexdigest() + "\n", encoding="utf-8")
(out / "additions.jsonl").write_text("".join(json.dumps(t, ensure_ascii=False, sort_keys=True) + "\n" for t in sorted(add, key=lambda t: t["id"])), encoding="utf-8")
print(len(cases), "cases;", len(slice_), "in the broken slice;", sum(c["expected"]["category"] == "refund" for c in cases), "refund")
