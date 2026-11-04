"""Assemble the 190 expert-label items from the drafted labels (seed 13).

practice 30 (10 calibration with at least 3 fails, 20 blind with at least 6 fails), dev 80 and
test 80 (40 pass and 40 fail each). A ticket's replies stay in one split, so no split leaks into
another. Subtle fails (from A, B and the day 5 prompt) are spread over dev and test first; the
rest of the fails come from the older prompt with last year's policy. Writes
datasets/labels/label_set.jsonl with the drafted verdict and reason, for the author's review.
"""
import json
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
L = ROOT / "datasets/labels"
items = {}
for f in ["candidates.jsonl", "candidates2.jsonl"]:
    for r in map(json.loads, (L / f).read_text(encoding="utf-8").splitlines()):
        items[r["id"]] = r
drafts = {}
for f in sorted(L.glob("drafts*.jsonl")):
    for r in map(json.loads, f.read_text(encoding="utf-8").splitlines()):
        drafts[r["id"]] = r
rows = [dict(items[i], draft=drafts[i]) for i in items if i in drafts]
rng = random.Random(13)
by_ticket = defaultdict(list)
for r in rows:
    by_ticket[r["ticket_id"]].append(r)
tickets = sorted(by_ticket)
rng.shuffle(tickets)
target = {"calibration": (7, 3), "blind": (14, 6), "dev": (40, 40), "test": (40, 40)}  # (pass, fail)
chosen = {k: [] for k in target}
need = {k: list(v) for k, v in target.items()}
subtle = lambda r: r["variant"] != "A-2025" and r["draft"]["verdict"] == "fail"
order = ["dev", "test", "blind", "calibration"]
# give each ticket to one split, round robin, taking the replies that split still needs
for n, t in enumerate(sorted(tickets, key=lambda t: -sum(subtle(r) for r in by_ticket[t]))):
    for s in order[n % 4:] + order[: n % 4]:
        reps = sorted(by_ticket[t], key=lambda r: (not subtle(r), r["id"]))
        took = []
        for r in reps:
            idx = 0 if r["draft"]["verdict"] == "pass" else 1
            if need[s][idx] > 0:
                need[s][idx] -= 1
                took.append(r)
        if took:
            chosen[s].extend(took)
            break
for s, (p, f) in need.items():
    if p or f:
        print("short", s, p, f)
out = []
for s, rs in chosen.items():
    for r in sorted(rs, key=lambda r: r["id"]):
        out.append({"id": r["id"], "split": s, "ticket_id": r["ticket_id"], "source_variant": r["variant"], "trial": r["trial"],
                    "ticket": r["ticket"], "reply": r["reply"], "draft_verdict": r["draft"]["verdict"],
                    "draft_reason": r["draft"]["reason"], "draft_confidence": r["draft"].get("confidence", "high")})
(L / "label_set.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in out), encoding="utf-8")
for s in target:
    rs = [r for r in out if r["split"] == s]
    print(s, len(rs), "fail", sum(r["draft_verdict"] == "fail" for r in rs), "subtle fail",
          sum(r["draft_verdict"] == "fail" and r["source_variant"] != "A-2025" for r in rs),
          "low conf", sum(r["draft_confidence"] == "low" for r in rs))
splits = defaultdict(set)
for r in out:
    splits[r["ticket_id"]].add(r["split"])
print("tickets in two splits:", sum(len(v) > 1 for v in splits.values()))
