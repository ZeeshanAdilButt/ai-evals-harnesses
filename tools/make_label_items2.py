"""Second batch of refund replies for labelling: the older prompt with last year's policy (A-2025,
trials 1 and 2, every refund ticket) and 60 day 5 to 7 mixed-language refund replies from the
traffic week (A-day5). Writes datasets/labels/candidates2.jsonl."""
import json, random, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evalkit.replay import Store
from product import reply
st = Store.load("reply")
out = []
for t in map(json.loads, (ROOT / "datasets/labels/refund_tickets.jsonl").read_text(encoding="utf-8").splitlines()):
    key = reply.build_request("A-2025", t["text"])["key"]
    for k in (1, 2):
        out.append({"id": f"{t['id']}-O{k}", "ticket_id": t["id"], "variant": "A-2025", "trial": k, "ticket": t["text"], "reply": st.lookup(key, k)["output"]})
traffic = [json.loads(l) for l in (ROOT / "datasets/traffic/tickets.jsonl").read_text(encoding="utf-8").splitlines()]
late = sorted([t for t in traffic if t["category"] == "refund" and t["language"] == "mixed" and t["day"] >= 5], key=lambda t: t["id"])
for t in random.Random(4).sample(late, 60):
    out.append({"id": f"{t['id']}-D1", "ticket_id": t["id"], "variant": "A-day5", "trial": 1, "ticket": t["text"],
                "reply": st.lookup(reply.build_request("A-day5", t["text"])["key"], 1)["output"]})
p = ROOT / "datasets/labels/candidates2.jsonl"
p.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in out), encoding="utf-8")
rows = out
for i in range(3):
    part = rows[i * 77:(i + 1) * 77] if i < 2 else rows[154:]
    (ROOT / f"datasets/labels/candidates2-{i+1}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in part), encoding="utf-8")
print(len(out))
