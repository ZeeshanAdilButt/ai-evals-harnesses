"""Judge items for the planted break: refund replies of mixed-language tickets on days 5 to 7
(variant A-day5-mixed, trial 1) and the mixed-language refund canary tickets (trials 1 to 3)."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evalkit.replay import Store
from product import reply
st = Store.load("reply")
rows = []
for t in map(json.loads, (ROOT / "datasets/traffic/mixed_day5plus.jsonl").read_text(encoding="utf-8").splitlines()):
    if t["category"] == "refund":
        rows.append({"id": t["id"], "ticket": t["text"], "reply": st.lookup(reply.build_request("A-day5-mixed", t["text"])["key"], 1)["output"]})
for t in map(json.loads, (ROOT / "datasets/traffic/canary_mixed.jsonl").read_text(encoding="utf-8").splitlines()):
    if t["category"] == "refund":
        key = reply.build_request("A-day5-mixed", t["text"])["key"]
        for k in (1, 2, 3):
            rows.append({"id": f"canary-{t['id']}-d{k + 4}", "ticket": t["text"], "reply": st.lookup(key, k)["output"]})
p = ROOT / "datasets/judge_items/break.jsonl"
p.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
print(len(rows))
