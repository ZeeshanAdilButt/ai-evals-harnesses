"""Pick the 60 reply traces of module 2 from the traffic week (seed 3): 30 from days 1 to 4 and
30 from days 5 to 7, two in three of them refund or delivery tickets. Writes
datasets/traces/traces.jsonl with the ticket, the reply, the variant, tokens and latency."""
import json, random, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evalkit.replay import Store
from product import reply
traffic = [json.loads(l) for l in (ROOT / "datasets/traffic/tickets.jsonl").read_text(encoding="utf-8").splitlines()]
st = Store.load("reply")
rng = random.Random(3)
def pick(rows, n):
    focus = [t for t in rows if t["category"] in ("refund", "delivery")]
    rest = [t for t in rows if t["category"] not in ("refund", "delivery")]
    return rng.sample(focus, n * 2 // 3) + rng.sample(rest, n - n * 2 // 3)
early = pick([t for t in traffic if t["day"] <= 4], 30)
late = pick([t for t in traffic if t["day"] >= 5 and t["language"] == "mixed"], 20) + pick([t for t in traffic if t["day"] >= 5 and t["language"] == "english"], 10)
out = []
for n, t in enumerate(sorted(early + late, key=lambda t: t["id"]), 1):
    v = "A-day5" if t["day"] >= 5 else "A"  # module 2 traces were frozen before A-day5-mixed existed; do not regenerate
    rec = st.lookup(reply.build_request(v, t["text"])["key"], 1)
    out.append({"trace_id": f"tr{n:02d}", "ticket_id": t["id"], "day": t["day"], "category": t["category"], "language": t["language"],
                "tone": t["tone"], "variant": v, "ticket": t["text"], "reply": rec["output"], "tokens_in": rec["tokens_in"], "tokens_out": rec["tokens_out"]})
p = ROOT / "datasets/traces/traces.jsonl"; p.parent.mkdir(parents=True, exist_ok=True)
p.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in out), encoding="utf-8")
print(len(out), sum(r["day"] >= 5 for r in out), "after day 5")
