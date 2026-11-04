"""Merge the spec and the written ticket texts into datasets/pool/tickets.jsonl, scrubbed."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from evalkit.scrub import scrub_text

pool = ROOT / "datasets" / "pool"
spec = {r["id"]: r for r in map(json.loads, (pool / "spec.jsonl").read_text(encoding="utf-8").splitlines())}
texts = {}
for f in sorted(pool.glob("text-*.jsonl")):
    for l in f.read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l); texts[r["id"]] = r["raw_text"]
assert set(texts) == set(spec), (len(texts), len(spec))
fixes = {}
fx = pool / "label-fixes.jsonl"
if fx.exists():
    for l in fx.read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l); fixes.setdefault(r["id"], {})[r["field"]] = r["should_be"]
for i, f in fixes.items():
    spec[i].update(f)   # the audit's fixes win over the spec (label-audit.jsonl says why)
out = []
for i in sorted(spec):
    r = dict(spec[i])
    r["easy"] = r["tone"] == "calm" and r["language"] == "english" and r["length"] == "normal" and r["source"] != "edge"
    r["raw_text"] = texts[i]; r["text"] = scrub_text(texts[i])
    r["expected"] = {"category": r["category"], "urgent": r["urgent"]}
    out.append(r)
(pool / "tickets.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in out), encoding="utf-8")
print(len(out))
