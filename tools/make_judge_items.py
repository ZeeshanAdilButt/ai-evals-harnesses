"""Judge item files (seed 21):
devtest.jsonl    the 160 dev and test replies of the label set
padded.jsonl     40 of them (drafted fails first) for the length probe
canonical.jsonl  every A and B reply trial on refund tickets (pool and v2 additions), for judge v3
traffic.jsonl    every refund reply of the traffic week and of the canary
"""
import json, random, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evalkit.replay import Store, ReplayMiss
from evalkit.traffic import canary_variant_trial, variant_for
from product import reply
D = ROOT / "datasets/judge_items"; D.mkdir(parents=True, exist_ok=True)
def w(name, rows):
    (D / name).write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows), encoding="utf-8"); print(name, len(rows))
ls = [json.loads(l) for l in (ROOT / "datasets/labels/label_set.jsonl").read_text(encoding="utf-8").splitlines()]
dt = [{"id": r["id"], "ticket": r["ticket"], "reply": r["reply"], "split": r["split"]} for r in ls if r["split"] in ("dev", "test")]
w("devtest.jsonl", dt)
fails = [r for r in ls if r["split"] in ("dev", "test") and r["draft_verdict"] == "fail"]
passes = [r for r in ls if r["split"] in ("dev", "test") and r["draft_verdict"] == "pass"]
rng = random.Random(21)
pad = rng.sample(fails, 30) + rng.sample(passes, 10)
w("padded.jsonl", [{"id": r["id"], "ticket": r["ticket"], "reply": r["reply"]} for r in pad])
st = Store.load("reply")
can = []
refund_pool = [json.loads(l) for l in (ROOT / "datasets/labels/refund_tickets.jsonl").read_text(encoding="utf-8").splitlines()]
adds = [json.loads(l) for l in (ROOT / "datasets/canonical/v2/additions.jsonl").read_text(encoding="utf-8").splitlines()]
for t in refund_pool + adds:
    for v in ("A", "B"):
        key = reply.build_request(v, t["text"])["key"]
        for k in range(1, 6):
            try:
                can.append({"id": f"{t['id']}-{v}{k}", "ticket": t["text"], "reply": st.lookup(key, k)["output"]})
            except ReplayMiss:
                pass
w("canonical.jsonl", can)
traffic = [json.loads(l) for l in (ROOT / "datasets/traffic/tickets.jsonl").read_text(encoding="utf-8").splitlines()]
tr = []
for t in traffic:
    if t["category"] != "refund":
        continue
    v = variant_for(t, t["day"])
    tr.append({"id": t["id"], "ticket": t["text"], "reply": st.lookup(reply.build_request(v, t["text"])["key"], 1)["output"]})
canary = [json.loads(l) for l in (ROOT / "datasets/traffic/canary.jsonl").read_text(encoding="utf-8").splitlines()]
for t in canary:
    if t["category"] != "refund":
        continue
    for day in range(1, 8):
        v, k = canary_variant_trial(t, day)
        tr.append({"id": f"canary-{t['id']}-d{day}", "ticket": t["text"], "reply": st.lookup(reply.build_request(v, t["text"])["key"], k)["output"]})
w("traffic.jsonl", tr)
