"""Collect refund replies for labelling: every refund ticket in the pool, trial 1 of A, trials 1
and 2 of B (B's brief prompt fails more often, so the set holds enough fails). Writes
datasets/labels/candidates.jsonl with {id, ticket_id, variant, trial, ticket, reply}."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evalkit.replay import Store  # noqa: E402
from product import reply  # noqa: E402

pool = [json.loads(l) for l in (ROOT / "datasets/pool/tickets.jsonl").read_text(encoding="utf-8").splitlines()]
store = Store.load("reply")
out = []
for t in pool:
    if t["category"] != "refund":
        continue
    for v, trials in (("A", [1]), ("B", [1, 2])):
        key = reply.build_request(v, t["text"])["key"]
        for k in trials:
            rec = store.lookup(key, k)
            out.append({"id": f"{t['id']}-{v}{k}", "ticket_id": t["id"], "variant": v, "trial": k,
                        "ticket": t["text"], "reply": rec["output"]})
p = ROOT / "datasets/labels/candidates.jsonl"
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in out), encoding="utf-8")
print(len(out), "candidates from", sum(t["category"] == "refund" for t in pool), "refund tickets")
