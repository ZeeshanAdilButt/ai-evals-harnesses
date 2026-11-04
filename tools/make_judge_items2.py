"""More judge items: the CI branch refund replies (canonical v1 refund tickets, five trials, both
branches) and the capstone set (trial 1 of A and the candidate on every canonical v2 refund ticket),
plus every trial of A and the candidate for judge v3."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evalkit.replay import Store
from product import reply
D = ROOT / "datasets/judge_items"
st = Store.load("reply")
def w(name, rows):
    (D / name).write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows), encoding="utf-8"); print(name, len(rows))
v1 = [json.loads(l) for l in (ROOT / "datasets/canonical/v1/cases.jsonl").read_text(encoding="utf-8").splitlines()]
v2 = [json.loads(l) for l in (ROOT / "datasets/canonical/v2/cases.jsonl").read_text(encoding="utf-8").splitlines()]
ci = []
for c in v1:
    if c["expected"]["category"] != "refund":
        continue
    for v in ("ci-regression", "ci-harmless"):
        key = reply.build_request(v, c["text"])["key"]
        for k in range(1, 6):
            ci.append({"id": f"{c['id']}-{v}-{k}", "ticket": c["text"], "reply": st.lookup(key, k)["output"]})
w("ci.jsonl", ci)
cap1, cap5 = [], []
for c in v2:
    if c["expected"]["category"] != "refund":
        continue
    for v in ("A", "candidate"):
        key = reply.build_request(v, c["text"])["key"]
        for k in range(1, 6):
            row = {"id": f"{c['id']}-{v}-{k}", "ticket": c["text"], "reply": st.lookup(key, k)["output"]}
            cap5.append(row)
            if k == 1:
                cap1.append(row)
w("capstone_trial1.jsonl", cap1)
w("capstone_all.jsonl", cap5)
